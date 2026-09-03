# Stage C: first-read fault injection

## Result

Stage C passed with the v22 first-read hardening candidate.

The original v21 candidate passed all three index-mtime cases, but Stage C exposed two gaps:

1. restoring a permanently bad index into a process that had already waited for roughly 35 seconds could resume into stale request-queue state and crash;
2. an index referencing absent request 156 replayed only records `0..155`, reached the main menu with 50 fewer coins and 175 fewer EXP, and therefore violated the no-partial-replay invariant.

v21 remains preserved. v22 adds retry-state restoration at the index hooks and wait guards around numbered-record replay. The public recovery contract for a permanent first-read fault is intentionally conservative: force-stop the waiting process, repair the file, then cold-launch. Long in-process recovery is not accepted by this test matrix and remains work for the later mid-session-fault stage.

## Candidate

- APK: `../../BirzzleFever-1.1.2-v22-first-read-recovery.apk`
- APK SHA-256: `cb929cf772067b270da9f5e050e34b32156b92ad5fc21100bae57d92ccfbe848`
- `libef2d.so` SHA-256: `64c083f7d3b614b77f09cdf38259577eccca8fc2276d67e6ba04209116ede0ae`
- `libbirzzle.so` SHA-256: `bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae`
- Installed package UID/GID: 10218.

The final build preserves the historical identity, leaderboard/menu-transition, unlimited-lives, cold-start maturity, index-mtime, and atomic-index-write changes. Its added path table is position-independent and stored in an existing zero-filled executable-segment cave; the executable stub ends at `0x27bfee`, before the writable segment at `0x27c000`.

## Baseline

Every case began from the final level-9 checkpoint:

```text
classification:     CONSISTENT
index:              -1,156
records:            0..156
record count:       157
semantic warnings:  none
coins:               980800
gems:                99870
EXP:                 3810
ranking score:       1017964
```

Authoritative hashes:

```text
index:
  c75e925c83ce92d7157f77306b123eb0e7e5944f3926e0d623edb55ed8813d07
request 0:
  5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2
request 156:
  0c7bddb7768b4a42cb2507a1cc7c4c3683767dd9be013b8f441f219c4d274506
```

## Matrix

| Fault before first process read | Fault behavior | Recovery | Result |
|---|---|---|---|
| Index mtime `+10` seconds | Cryptographically valid index accepted directly | None | Pass |
| Index mtime `+11` seconds | v22 index-only tolerance accepted it directly | None | Pass |
| Index mtime `+60` seconds | v22 index-only tolerance accepted it directly | None | Pass |
| Missing index | Mature request zero caused a controlled wait | Force-stop, restore index, cold-launch | Pass |
| Zero-length index | Controlled wait | Force-stop, restore index, cold-launch | Pass |
| Truncated Base64/ciphertext | AES block-size rejection and controlled wait | Force-stop, restore index, cold-launch | Pass |
| Invalid AES/PKCS#7 padding | Controlled wait | Force-stop, restore index, cold-launch | Pass |
| Wrong envelope MD5 | Controlled wait | Force-stop, restore index, cold-launch | Pass |
| Index referencing missing request 156 | Numbered-record guard caused a controlled wait | Force-stop, restore request 156, cold-launch | Pass |

The truncated fixture removes four Base64 characters. Removing only one character was not a valid fault injection for this game because its legacy decoder accepted that form; removing four produces a validly identified `AES_BLOCK_SIZE_INVALID` input.

## Safety invariants

During every controlled wait:

- the process remained alive;
- no empty quest response appeared;
- no sentinel-only inventory response appeared;
- no zero-pocket `POCKET.GET` appeared;
- no `SAVE REQUEST:` occurred;
- request zero remained byte-identical;
- no replacement `-1,0` index was created.

After repair and a cold launch, every case restored:

- 980,800 coins;
- 99,870 gems;
- 3,810 EXP;
- Suri at ability 10;
- Polo ownership/selection history;
- non-empty quests;
- ranking score 1,017,964;
- a live main-menu process without a Java fatal exception, native fatal signal, or ANR.

Each post-recovery pool was `CONSISTENT`, `-1,156`, with 157 valid records, no invalid records, and no semantic warning. The index, request zero, and request 156 matched their baseline SHA-256 values.

## Execution note

A continuous early batch destabilized the old Android 4.4 test device and it rebooted, taking ADB down with it. The six permanent-fault cases were therefore rerun independently after the reboot, with a full baseline restore before and after each case. Only those isolated successful runs are included in the aggregate result.

## Evidence

- Aggregate results: `results.json`
- Safety analysis: `matrix-analysis.json`
- Final live pool: `final-device-pool.json`
- Per-case injected state: `<case>/injected.json`
- Controlled-wait log: `<case>/before-recovery.log`
- Recovered launch log: `<case>/launch.log`
- Per-case result: `<case>/result.json`
- Per-case reconstructed pool: `<case>/recovered-pool.json`

The device is left with the corrected v22 APK installed, the healthy level-9 baseline restored, and Birzzle Fever force-stopped.
