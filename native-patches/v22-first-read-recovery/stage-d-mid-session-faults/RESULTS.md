# Stage D: mid-session fault injection

## Result

Stage D passed with the v22 first-read hardening candidate for short, recoverable mid-session faults.

Each accepted case began from the mature `-1,156` level-9 checkpoint, loaded the main menu, entered the power-up screen, applied the fault before the final **Let's Play** confirmation, and confirmed that `OFFLINE REQUEST: pocket.set` began while the fault was active. The harness restored the affected index approximately two seconds after that request marker.

All four cases delivered the real `GameStart` `POCKET.SET` response without a fatal signal, Java exception, ANR, or clamp. Request 157 was appended atomically and the live pool became `-1,157`. A forced stop while the game scene was active caused the game's normal next-launch `UploadPocket` refund; this produced request 158 and a valid cold-restart pool `-1,158`.

## Candidate

- APK: `../BirzzleFever-1.1.2-v22-first-read-recovery.apk`
- APK SHA-256: `cb929cf772067b270da9f5e050e34b32156b92ad5fc21100bae57d92ccfbe848`
- `libef2d.so` SHA-256: `64c083f7d3b614b77f09cdf38259577eccca8fc2276d67e6ba04209116ede0ae`
- Installed package UID/GID: 10218.

No binary change was required during Stage D.

## Baseline

```text
classification:     CONSISTENT
index:              -1,156
valid records:      157
coins:               980800
gems:                99870
EXP:                 3810
index SHA-256:       c75e925c83ce92d7157f77306b123eb0e7e5944f3926e0d623edb55ed8813d07
request 0 SHA-256:   5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2
```

## Matrix

| Fault during real `GameStart` | Injection proof | Restoration | Live result | Cold result |
|---|---|---|---|---|
| Index removed | Index absent; original 152-byte index held as `.stage-d-good` | Original moved back | `-1,157`, consistent | `-1,158`, consistent |
| Index mtime `+60` seconds | Index mtime changed from `1788127049` to `1788127109` | Atomic writer had already replaced the skewed index | `-1,157`, consistent | `-1,158`, consistent |
| Index access denied | Existing index mode changed from `600` to `000` | Mode restored to `600` | `-1,157`, consistent | `-1,158`, consistent |
| Zero-length index | Active index size was zero; original held as `.stage-d-good` | Original moved back | `-1,157`, consistent | `-1,158`, consistent |

The checkpoint had the 300-coin **Bonus Booster Box** selected. Consequently, the tested `GameStart` request contained `coin=-300`, and the correct live response contained 980,500 coins, 99,870 gems, 3,810 EXP, and five lives. This is normal game behavior, not a clamp or progression loss.

Request 157 was a valid, contiguous `pocket.set` record with `extradata=GameStart`. After the harness force-stopped the active game, request 158 was a valid `pocket.set` record with `extradata=UploadPocket` that refunded the interrupted game's 300-coin booster selection. Both index files had an embedded-timestamp/mtime delta of zero.

## Invariants

Every accepted case satisfied all of the following:

- main menu and power-up screen visually confirmed before injection;
- real `GameStart` invoked while the fault was active;
- expected 980,500-coin, 99,870-gem, 3,810-EXP response delivered;
- process remained alive through live recovery;
- no `FATAL EXCEPTION`, fatal signal, SIGSEGV, or ANR;
- no `POCKET CLAMP` or `INVENTORY CLAMP` marker;
- live response pool `CONSISTENT`, contiguous `0..157`, with 158 valid records;
- cold response pool `CONSISTENT`, contiguous `0..158`, with 159 valid records;
- no invalid records or semantic warnings;
- request zero remained byte-identical before and after cold restart.

## Boundaries discovered

An early diagnostic run accidentally left a missing index active for roughly 17 seconds because the harness waited for `SAVE REQUEST` rather than the earlier `OFFLINE REQUEST` marker. Restoring at that late point produced the `GameStart` response and valid request 157, but the surrounding request queue then crashed with SIGSEGV. This agrees with the Stage C finding: v22 safely handles a short transient, but long in-process repair after the request queue has waited is not supported.

That diagnostic run is not counted as an accepted Stage D case and is preserved at:

```text
temporary-index-removal-invalid-long-fault-window/
```

Two other non-product harness runs were excluded because the Galaxy S4 keyguard or an ignored confirmation tap prevented `GameStart` from occurring. The final harness polls keyguard state, visually classifies the main-menu and power-up frames, and retries a confirmation tap only while the power-up screen is still visibly present. Those excluded artifacts are retained with `invalid-` names.

## Evidence

- Harness: `../../../test_v22_mid_session_faults.py`
- Aggregate results: `results.json`
- Pool analysis: `matrix-analysis.json`
- Final restored device pool: `final-device-pool.json`
- Per-case injection proof: `<case>/fault-state.json`
- Per-case main-menu and power-up frames: `<case>/main-menu.png`, `<case>/power-up*.png`
- Fault-window log: `<case>/fault-window.log`
- Live recovery log: `<case>/live-recovery.log`
- Live pool: `<case>/live-recovered-pool.json`
- Cold-restart log and pool: `<case>/cold-restart.log`, `<case>/cold-restart-pool.json`

The Galaxy S4 is left with v22 installed, the mature `-1,156` baseline restored, the original 30-second screen timeout restored, and Birzzle Fever force-stopped.
