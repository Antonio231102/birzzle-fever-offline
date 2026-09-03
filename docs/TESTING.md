# Validation and test results

## Evidence policy

This repository publishes test definitions, aggregate results, hashes, and technical conclusions. Raw logcat captures, screenshots, app-data archives, decrypted profiles, and response-pool records remain local because they can contain device-specific or user-state data and add little review value.

Statements below are observations from the named test environment unless explicitly marked as inference.

## Primary environment

| Field | Value |
|---|---|
| Device | Samsung Galaxy S4 SGH-I337M |
| Android | 4.4.2 |
| Application | Birzzle Fever 1.1.2, package version code 13 |
| ABI | 32-bit ARM |
| Identity module | Disabled for V25 |
| V25 development APK SHA-256 | `66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05` |

The Android package UID varied across reinstalls and was not a compatibility requirement. V25 uses the historical application identity internally.

## V25 qualification summary

| Area | Exercise | Result |
|---|---|---|
| Fresh initialization | Uninstall, clean install, no private files or seed marker | Pass |
| Offline startup | Wi-Fi and mobile data unavailable | Pass |
| First progression | Suri acquisition, three games, missions, level 2, bonus game, upgrade | Pass |
| Ranking | Initial `No Score`, later earned score, one `My Score` identity | Pass |
| Mature cold launch | 10 consecutive launches from pool `-1,156` | 10/10 pass |
| First-read fault matrix | mtime +10/+11/+60, missing, empty, truncated, bad padding, bad MD5, missing referenced record | 9/9 pass |
| Offline lifetime | 3 completed games, 1 mid-game quit, multiple power-up cancellations | Pass |
| Connected lifetime | 7 completed games, 1 mid-game quit, Wi-Fi disconnect/reconnect | Pass |
| Final cold restart | No new records; progression and ranking retained | Pass |
| Unlimited start | Starting games after displayed lives reached zero | Pass in earlier accepted interactive testing |

No exercised V25 path produced the historical ranking crash, an infinite loading dialog, a main-menu softlock, or a destructive response-pool collapse.

Machine-readable aggregate: `native-patches/v25-ranking-template/release-evidence.json`.

## Persistence invariants

The qualification repeat captured four logical checkpoints:

| Checkpoint | Pool | Records | Added | Classification |
|---|---:|---:|---:|---|
| Baseline | `-1,179` | 180 | — | `CONSISTENT` |
| Offline session | `-1,196` | 197 | 17 | `CONSISTENT` |
| Connected session | `-1,231` | 232 | 35 | `CONSISTENT` |
| Final cold restart | `-1,231` | 232 | 0 | `CONSISTENT` |

Across transitions:

- request zero remained byte-identical;
- every pre-existing numbered request remained byte-identical;
- indices were valid and contiguous;
- no semantic analyzer warning or fatal marker occurred;
- final ranking score was retained after cold restart.

## Historical checkpoints

### V4 dedicated-BSS ranking gate

Several games and repeated menu returns completed in one process. Two cold-start ranking responses did not crash. The lives timer remained unresolved.

Source record: `checkpoints/2026-08-23-v4-dedicated-bss-multigame/CHECKPOINT.md`.

### V7 level-8 checkpoint

Repeated ranking/menu flows and unlimited-play behavior passed. One transient post-game level rollback was observed and recovered after another game. This later led to response-pool investigation.

Source record: `checkpoints/2026-08-23-v7-level8-titanium/CHECKPOINT.md`.

### V11 hybrid data checkpoint

Approximately 15 games advanced level 1 to level 6. The run observed 51 ranking events with no fatal signal, exception, or ANR. It identified two compatibility files, but later APK-only self-seeding superseded manual hybrid restoration.

Source record: `checkpoints/2026-08-23-v11-original2016-two-file-hybrid-success/README.md`.

### V20–V23 persistence hardening

- V20 reproduced and mitigated transient empty-index collapse after a valid in-process read.
- V21 added persistent maturity and referenced-record checks.
- V22 exercised first-read and mid-session corruption cases plus interrupted-write boundaries.
- V23 changed commit order so numbered request data becomes durable before the index advertises it.

Detailed results remain in `PROGRESS_REGRESSION_PATCHES.md`, `POST_GAME_COMMIT_ORDER.md`, and milestone `RESULTS.md` files under `native-patches/`.

### V24/V25 connectivity and ranking template

V24 removed the active-network-interface dependency and obsolete GCM retry, but its single-entry sanitized ranking seed displayed no personal score. V25 restored the calculator's two-slot contract with distinct sentinel scores. See `V24_V25_REGRESSION_HISTORY.md`.

## Running safe repository checks

These checks do not contact a device:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest -v test_index_diagnostics.py
python scripts/validate_repository.py
```

The validator checks tracked-file policy, required documentation, forbidden binary/media types, large files, signing material, and known private device identifiers.

## Running device harnesses

Warning: the `stress_*` and several `test_*` scripts intentionally force-stop the package, replace private files, inject corrupt indices, alter mtimes, and restore checkpoints. Use only an authorized rooted test device with a verified backup.

General preparation:

1. Place `adb` at the documented local path or adapt the script locally.
2. Set `ADB_SERIAL` to the authorized test device, or pass `--serial` where supported.
3. Place required APK/native/checkpoint inputs under ignored paths.
4. Verify hashes before the first destructive action.
5. Disable unrelated backup, sync, cleaner, and test processes.
6. Read the target script; historical harnesses are not a uniform command-line interface.
7. Never point a fault harness at a device containing the only copy of wanted progress.

Raw output belongs under an ignored evidence or device-snapshot directory. Publish only a reviewed aggregate result.

## Known limitations

- Only one ARMv7 device has completed the exact V25 qualification matrix.
- The natural trigger for the original transient empty-index read was not captured directly; controlled fault injection reproduced the destructive mechanism.
- Permanent root-induced index removal can deliberately hold the app in a non-destructive wait until repaired.
- One daily-bonus timing observation remains unclassified and non-blocking.
- The public source tree does not yet reproduce the final V24/V25 package delta from a clean user-supplied APK.
