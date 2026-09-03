# Birzzle Fever progress-regression root-cause analysis

## Purpose and confidence levels

This document explains why Birzzle Fever could suddenly revert pocket values, pets, quests, missions, and other progression even though the individual save files and later request records were still present.

It complements `PROGRESS_REGRESSION_PATCHES.md`, which documents the binary changes. This file concentrates on the original failure mechanism.

Claims are separated into three confidence levels:

- **Observed:** captured directly from device data, decrypted persistence files, logs, or deterministic fault tests.
- **Established:** follows directly from disassembly plus observed state transitions.
- **Not fully established:** the exact condition present during the uncaptured 22:41:05 natural read. A modification-time mismatch is now a proven sufficient lower-level cause, but the predecessor index metadata was overwritten before capture.

## Executive conclusion

The regression was not primarily a coin, experience, gem, pet, mission, or leaderboard bug. Those were downstream symptoms.

Birzzle Fever's offline backend treats an encrypted request history as its authoritative event log. A single encrypted index tells `libef2d.so` which numbered request files to replay. During the natural regression, the index changed from a mature value to `-1,0`, while the later numbered request records remained intact. From that point onward, the offline backend replayed only the new request-zero history and reconstructed every domain from an effectively fresh account.

The immediate destructive sequence was:

```text
mature response pool
    -> an index read is treated as empty
    -> SetRequest follows its new-pool path
    -> request zero is created
    -> the encrypted index is written as -1,0
    -> every calculator replays the truncated history
    -> pocket, inventory, pets, quests, and missions regress together
```

The v19 clamps operate after responses have been calculated. They can stop selected pocket or inventory objects from being overwritten, but they cannot preserve the underlying event log. The v20 patch operates at the shared index-read layer and prevents the destructive transition for a mature pool.

## Offline-backend architecture

### Two native libraries with different responsibilities

The current APK contains two relevant ARM libraries:

- `libbirzzle.so`: game logic, scenes, UI consumers, pocket objects, pet objects, leaderboard handling, and the v19 defensive guards.
- `libef2d.so`: the offline Hangame-compatible response generator, request persistence, response-pool replay, and domain calculators.

The important architectural boundary is:

```text
game action/UI
    -> request sent to offline Hangame wrapper
    -> CResponsePool persists or reads request history
    -> calc* function reconstructs a response
    -> response delivered to libbirzzle/game objects
    -> scene or UI consumes reconstructed state
```

The response delivered to `libbirzzle.so` is already the result of replaying the request history. A consumer-side clamp therefore cannot correct missing historical events such as pet acquisition or quest completion.

### Event-log model

The offline implementation does not maintain one independent authoritative file per domain. Instead, it stores numbered requests and recalculates state by replaying relevant requests.

Examples of persisted events include:

- `pocket.set` with `GameStart`;
- completed-game `UploadPocket` deltas;
- coin and experience rewards;
- quest status updates;
- pet purchases and upgrades;
- ranking-affecting score updates.

Different calculators select different events from the same numbered pool:

| Calculator | Library-relative offset | Reconstructed domain |
|---|---:|---|
| `calcInventory` | `0x1345F4` | Inventory and pets |
| `calcPocketLogin` | `0x134EE8` | Login profile and quest status |
| `calcQuestUpdateStatus` | `0x135774` | Quest state |
| `calcPocketGet` | `0x135E68` | Coin, gem, experience, heart, unlocks, and related pocket state |
| `calcRanking` | `0x136630` | Offline ranking response |

A bad shared boundary therefore affects several apparently unrelated systems at once.

## Persistence layout

### Historical identity

The restored 2016 state is keyed by the historical UID:

```text
3c8bb7308c3fcb60c439224bd595c794d8f31501
```

The index filename is derived as:

```text
MD5(uid + "REQUESTPOOLINDEX")
= 5f7d50ff681a65b10550a631e11a2ded
```

Each numbered request filename is derived as:

```text
MD5(uid + "REQUESTPOOL_" + decimal_index)
```

Because numbered filenames are hashes, the directory cannot be sorted by request number without knowing the UID and regenerating each expected name.

### Encryption envelope

The files use the game's `CCrypt::Decrypt2` format:

1. outer Base64 decoding;
2. AES-128-ECB decryption;
3. game envelope fields including `KEY`, `DATA`, and `TIMESTAMP`;
4. another Base64 value inside `DATA` for the application payload.

The AES key recovered from the binary is:

```text
miaeHgpdskiinerS
```

For the pool index, decoded `DATA` is a comma-separated first/last pair such as:

```text
-1,102
```

The effective iteration begins after the first value and includes numbered records through the last value.

### Observed healthy progression

The index grew monotonically as requests accumulated:

| Captured checkpoint | Decrypted index |
|---|---:|
| Level 3 | `-1,35` |
| Level 4 | `-1,44` |
| Level 5 | `-1,60` |
| Level 6 | `-1,78` |
| Level 7 | `-1,99` |
| Post-bonus level 7 | `-1,102` |

This progression is consistent with an append-only request log.

## Evidence from the natural regression

### Last valid state

Immediately before the natural failure, logs showed a valid completed-game response containing:

```text
coin = 983470
gem  = 99870
exp  = 2670
```

The later request files also contained coherent game and quest events.

### First visible reset

A subsequent `POCKET.GET` returned:

```text
coin = 0
gem  = 0
exp  = 0
```

The v18-era guards logged pocket clamps for coin and experience. The original v18 gem source offset was incorrect, so that version did not clamp the actual gem field.

Relevant evidence:

```text
device-snapshots/2026-08-29-level8-progression/regression.log
```

### Regression was global, not pocket-only

The captured regressed state was later restored under matching conditions and inspected:

- `POCKET.LOGIN` returned `queststatus: []`;
- `INVENTORY.LIST` returned only the sentinel entry;
- previously acquired Suri, Popo, and Polo pets were absent;
- the pet picker showed the pets as unowned;
- missions returned to the initial Rookie state;
- buying a new Suri produced a new TID rather than finding the prior pet;
- later requests were calculated from zero values.

Relevant evidence:

```text
device-snapshots/2026-08-29-level8-regression-state-verification/verification.log
```

This rules out a narrow display bug and rules out a failure confined to the leaderboard UI.

### Index collapse with request records retained

The healthy post-bonus index decrypted to:

```text
-1,102
```

The regressed archive's index decrypted to:

```text
-1,0
```

However, request files corresponding to indices 103 through 115 were still present and decryptable. They contained coherent events:

- 103: game start;
- 104: completed-game upload;
- 105–106: quest updates;
- 107: game start;
- 108: completed-game upload;
- 109: quest update;
- 110: reward;
- 111: quest update;
- 112: game start;
- 113: completed-game upload;
- 114–115: quest updates.

The data had not been comprehensively erased. The index stopped the backend from discovering and replaying it.

The live and stopped regression archives were byte-identical:

```text
SHA-256: 6b408aea174ccc92fdaf93208a68b17c0bb545cca543eab4b82f3b528b1bd37c
```

That stability after stopping the process shows that the bad state had already been persisted; it was not merely a transient UI object.

## Disassembly findings

### Relevant response-pool functions

| Function | Offset |
|---|---:|
| `CResponsePool::clearRequestQueue` | `0x12BB4C` |
| `CResponsePool::ResetIndex` | `0x130828` |
| `CResponsePool::GetRequestSuite` | `0x130F10` |
| `CResponsePool::GetRequestAll` | `0x1314C0` |
| `CResponsePool::SetRequest` | `0x131D58` |
| `CResponsePool` constructor | `0x1321E0` |

`clearRequestQueue` was not the natural regression mechanism identified here. Its only direct caller found during analysis was the timeout-generation path. The destructive behavior was reproduced through ordinary index handling without calling the queue-clearing function.

### Shared index read

`GetRequestSuite`, `GetRequestAll`, and `SetRequest` all:

1. obtain the platform/historical UID;
2. append `REQUESTPOOLINDEX`;
3. hash that string into the index filename;
4. call `FileWorker::ReadContent`;
5. test whether the returned string is empty;
6. parse the first/last pair when non-empty.

The relevant support routines include:

| Routine | Offset |
|---|---:|
| string copy constructor | `0x0A08AC` |
| `FileWorker::instance` | `0x1210D4` |
| `FileWorker::ReadContent` | `0x1215A8` |

### Original empty paths

For `GetRequestSuite` and `GetRequestAll`, an empty string means there is nothing to replay. For a genuinely new pool, this is reasonable.

For `SetRequest`, the same empty result is more dangerous. Its original path initializes first/last state for a new pool and computes request index zero. It then writes the current request and writes the index describing that new history.

There is no distinction between:

```text
A. this installation has no response-pool index yet
```

and:

```text
B. a mature index exists, but this particular ReadContent returned empty
```

That ambiguity is the software defect.

### Why one bad write has global consequences

After `SetRequest` writes an index ending at zero, subsequent calculators follow the new index. They no longer iterate the orphaned mature records. The result is deterministic from that point:

```text
index says only request 0 exists
    -> pocket calculator sees no accumulated rewards
    -> inventory calculator sees no acquisitions
    -> quest calculator sees no updates
    -> ranking calculator sees incomplete score history
```

Later actions append to the new zero-based history, making the regression self-reinforcing. Restarting the game does not restore the old progression because the bad index is already encrypted and persisted on disk.

## Why the failure appeared intermittent

### Established timing dependency

The destructive branch is only taken when the index read is empty. Normal reads parse the mature index and work correctly. This binary branch explains why the same backup could work repeatedly and then regress during a later menu or gameplay transition.

The v20 fault test demonstrated the timing dependency directly: after a valid index had been read, physically hiding the index for three seconds during `GameStart` caused the request to wait; restoring the file let the same request complete with the full history.

### Newly established lower-level rejection path

Further disassembly found that `FileWorker::ReadContent` compares the filesystem `st_mtime` with the encrypted envelope's `TIMESTAMP`. It rejects the file and returns the same empty string when:

```text
abs(st_mtime - embedded_timestamp) > 10 seconds
```

A controlled test changed only the healthy index mtime by +60 seconds. The bytes remained cryptographically valid and still decoded to `-1,102`, but the original v19 build returned empty quests, sentinel-only inventory, zero pocket values, and zero ranking values. This is an exact sufficient lower-level mechanism for the observed empty-history reconstruction.

The specific natural condition at 22:41:05 is still not recoverable because the later 22:41:20 `GameStart` overwrote the predecessor index and request zero. Modification-time rejection is now the strongest concrete candidate, not the only possible one. Other `ReadContent` paths also collapse `access`, `fopen`, short-read, Base64, AES, padding, MD5, and malformed-envelope failures into the same empty result.

Normal in-process `FileWorker` read/write overlap is unlikely: both functions hold `g_fileworkermutex` at `0x291ACC` across their complete operations. Writes are nevertheless non-atomic, use the final path with mode `"w"`, and do not check `fwrite`; external metadata changes, process death, storage errors, and tools bypassing the mutex remain possible.

Full disassembly, the timestamp experiment, ranked alternatives, and evidence paths are documented in `READCONTENT_EMPTY_ROOT_CAUSE.md`.

The v20 design intentionally does not depend on one specific lower-level cause. It treats any empty read as non-authoritative after the process has already observed a valid mature index.

### Why airplane mode did not eliminate it

The response-pool and calculators are local native code operating on files under the app's data directory. Airplane mode affects remote networking but does not serialize local response-pool reads and writes. Therefore the regression could occur with Wi-Fi off or airplane mode enabled.

### Why the leaderboard looked responsible

The leaderboard is automatically requested while the main menu initializes. It was frequently the first UI that consumed inconsistent reconstructed state, so crashes or loading softlocks appeared there.

The file `09d531fd0dc2a818e49efec1d5548a78` also changed leaderboard behavior when renamed. It is now identified as `MD5("submarinevariable.dat")`; its payload is Base64-encoded gzip JSON plus revision suffix `_20`, containing feature and tuning variables. Removing it changes configuration availability and initialization timing, which can alter leaderboard symptoms, but it is not the response-pool index or global progression history.

The leaderboard was therefore a sensitive observer of bad state and had its own duplicate-callback problems, but it was not the shared root of the global progression regression.

## Role of the v16–v19 clamps

### Why they were added

Before the shared index failure was understood, the first reliable symptom was a lower or empty response reaching already-populated game objects. The defensive patches progressively protected that consumer boundary:

- v16 guarded selected `POCKET.SET` and inventory responses;
- v17 added `POCKET.GET` protection;
- v18 made `POCKET.SET` handling experience-aware to avoid blocking legitimate transactions;
- v19 corrected the authoritative gem member and finalized the pocket/inventory guard behavior.

### What they can protect

The final v19 guard can:

- replace lower coin, gem, or experience fields with already-loaded authoritative safe-number values;
- reject an inventory response whose non-sentinel row count is smaller than the existing pet count;
- log when either correction is required.

This is useful for an isolated malformed response delivered after valid state is already loaded.

### What they cannot protect

The clamps cannot:

- repair `5f7d50ff681a65b10550a631e11a2ded`;
- cause orphaned request files to be replayed;
- reconstruct missing quest events;
- reconstruct missing pet-acquisition events after startup;
- preserve missions that are calculated from an empty history;
- recover a process that began with already-regressed authoritative objects.

The regressed-state verification showed exactly this limitation: experience could still be clamped from an in-memory safe number while quests and inventory remained empty.

## Are the clamps still required with v20?

### For the reproduced response-pool bug: no

The v20 production fault test is the key evidence.

During a real `GameStart` request:

1. the index was physically unavailable for three seconds;
2. the v20 `libef2d.so` retry path waited;
3. the index was restored;
4. `POCKET.SET` returned `982920` coins, `99870` gems, and `2200` experience;
5. the index advanced correctly from `-1,102` to `-1,103`;
6. no `BirzzleGuard: POCKET CLAMP` line occurred.

The correct response existed before the v19 consumer guard had anything to correct. Therefore the clamp routines were not required to survive the reproduced index-loss scenario.

The five corrected cold launches add supporting evidence: all five loaded the same correct pocket values and inventory, reached `SCORE.RANKING`, and produced no clamp or fatal condition attributable to the regression.

### Unclamped v20 control result

The conclusion was tested directly with a separate control APK. It retained the v20 `libef2d.so` but replaced the v19 guarded `libbirzzle.so` with the v15 library, which has no pocket or inventory clamps:

```text
native-patches/v20-request-index-retention/unclamped-control/BirzzleFever-1.1.2-v20-unclamped-control.apk
APK SHA-256:          c93a81945662f933531e39bb5ece18bc25f3005b630cf3866f257dd48ec336ec
libbirzzle SHA-256:   bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae
libef2d SHA-256:      291247fa42e11070ad30b4c6c0f4554535ba24d1252b88b635929343c29c21e2
```

The clean `-1,102` checkpoint was restored under this control. After the main menu loaded, the index was physically hidden for three seconds during a real `GameStart`, then restored. Results:

```text
process alive:       yes
coin:                982920
gem:                 99870
experience:          2200
fatal condition:     none
clamp code present:  no
post-request index:  -1,103
```

This is direct confirmation that the clamps are not required to correct the reproduced response-pool bug. The v20 response-pool layer independently retained and replayed the full history.

Evidence:

```text
native-patches/v20-request-index-retention/unclamped-control/unclamped-live-index-fault.log
native-patches/v20-request-index-retention/unclamped-control/post-fault-index.bin
build_v20_unclamped_control.py
test_v20_unclamped_control.py
```

After the control test, the production v20 APK and clean checkpoint were restored. The restored process reached `SCORE.RANKING` with the expected inventory and pocket values. Evidence is in `native-patches/v20-request-index-retention/production-restore-verification.log`.

### For the release build: optional defense in depth

Removing the clamps would simplify `libbirzzle.so` and eliminate the possibility that an old in-memory value masks a legitimate decrease. Keeping them protects against a different class of malformed response that v20 does not address, including an independently truncated inventory response after valid pets have loaded.

The current recommendation is:

- **v20 is required** for the established shared-index regression.
- **v19 clamps are not required** for that established failure mode; both the production no-clamp log and the dedicated unclamped control prove this.
- **Keep v19 in the public checkpoint for now** as defense in depth because it stayed inactive during successful v20 tests, while its inventory guard covers a separate consumer-side failure class.
- Consider removing v19 only after the unclamped control also passes extended legitimate spending, pet, quest, multi-game, and cold-restart testing. The completed control proves root-cause independence, not every unrelated consumer-side edge case.

## How v20 resolves the ambiguity

### High-water state

v20 adds one process-local word at `libef2d.so` address `0x294624`:

```text
request_highwater = next valid request index
```

After a valid parse:

```text
request_highwater = last + 1
```

After `SetRequest` computes a new append:

```text
request_highwater = new_last + 1
```

The value is not a replacement persistent index. It is evidence that the current process has already observed a mature pool.

### Patched decision

The original decision was:

```text
if ReadContent(index).empty:
    use empty/new-pool path
```

The production v20 decision is equivalent to:

```text
content = ReadContent(index)

if content is non-empty:
    parse normally
elif request_highwater == 0:
    use original empty/new-pool path
else:
    repeat ReadContent(index) until non-empty
    parse normally
```

This preserves legitimate first initialization while refusing to reinterpret a known mature pool as new.

### Why retry rather than synthetic parsing

An early prototype attempted to synthesize first/last integers and jump past the original string parser. Device testing exposed invalid native object cleanup because that shortcut skipped normal string/vector lifetimes.

The production implementation instead retries `FileWorker::ReadContent` and rejoins the original non-empty branch. The original parser, vector constructors, destructors, loop setup, and cleanup remain responsible for their own objects. This is both safer and closer to the original control flow.

The final hook boundaries also preserve the first normal-path instructions at `0x13107E` and `0x1315A6`. An intermediate test accidentally replaced those instructions and produced a deterministic invalid-free crash. Correcting the hook width removed that instrumentation defect. Those failed-development logs are not evidence of a game regression.

## Deterministic validation of the causal model

### Fault injection

The strongest test used the production v20 APK, not a mock backend:

1. restore a clean checkpoint with index `-1,102`;
2. launch through the main-menu ranking response, ensuring a valid index was observed;
3. enter the power-up screen;
4. rename the index file out of the app files directory;
5. tap the final `Let's Play` button;
6. leave the index unavailable for three seconds;
7. restore the same file;
8. observe the pending `GameStart` response.

Result:

```text
POCKET.SET extradata=GameStart
coin=982920
gem=99870
exp=2200
heart=5
process remained alive
no POCKET CLAMP
post-request index=-1,103
```

This proves all of the following at once:

- the empty-index condition was exercised during a real request;
- v20 did not take the original request-zero path;
- the retry rejoined normal parsing correctly;
- the complete prior history was used;
- v19 was not needed to repair the returned pocket fields;
- the subsequent persistent append remained coherent.

Evidence:

```text
native-patches/v20-request-index-retention/verified-live-empty-index.log
native-patches/v20-request-index-retention/post-fault-index.bin
```

### Restart persistence

After restoring the clean checkpoint again, five cold launches each reached the main-menu `SCORE.RANKING` response with:

```text
coin=982920
gem=99870
exp=2200
expected inventory present
no native fatal signal
no Java fatal exception
```

The index after all five launches remained byte-identical to the clean checkpoint and decrypted to `-1,102`.

Evidence:

```text
native-patches/v20-request-index-retention/cold-launch-stress-complete/
native-patches/v20-request-index-retention/final-stress-index.bin
```

## Remaining limitations and follow-up tests

The established bug is corrected, but the following are separate concerns:

1. **Permanent pre-start index loss:** if the index is missing before a new process observes any valid history, `request_highwater` is zero and the original initialization path remains available. Reconstructing an already-deleted index would require a persistent redundant index or an enumeration strategy for hashed request filenames.
2. **Permanent in-session read failure:** once a mature pool is known, v20 waits rather than destroys history. A permanently unreadable index can therefore produce a wait/softlock. That failure is intentionally non-destructive and can be resolved by restoring the file and restarting.
3. **Natural lower-level trigger not captured in situ:** a greater-than-10-second mtime/encrypted-timestamp mismatch is now proven to cause the same empty-history response, but the predecessor metadata from 22:41:05 was overwritten at 22:41:20. Instrumenting access/open/read/decrypt and timestamp results remains the only way to distinguish timestamp rejection from another transient failure during a future natural event.
4. **Independent application bugs:** leaderboard callback duplication, scene-transition softlocks, life regeneration, and the earlier tutorial behavior are separate paths. Their existence does not contradict the response-pool diagnosis.
5. **Extended unclamped coverage:** the unclamped control passed the decisive three-second missing-index `GameStart` test. It has not yet been exercised through prolonged multi-game progression, legitimate coin/gem spending, pet operations, quest completion, and repeated cold restarts. Those tests determine whether the optional v19 defense should be removed from a public build; they are not needed to establish v20's independence for the reproduced root cause.

## Final technical conclusion

The game regressed because its offline persistence format had a single point of authority—the encrypted response-pool index—but its native readers represented both “new pool” and “failed/empty read” with the same empty string. `SetRequest` was allowed to turn that ambiguous empty result into a new persistent index ending at zero. Once written, the truncated index caused every domain calculator to ignore the intact later request files.

The v20 patch adds the missing state distinction: after a valid mature index has been observed, an empty read is treated as a retryable I/O condition, not as permission to initialize a new pool. That is the source-level correction for the reproduced progression regression.

The v19 clamps are no longer necessary for this specific bug. They remain optional consumer-side protection against different malformed responses and are retained in the production APK as defense in depth.
