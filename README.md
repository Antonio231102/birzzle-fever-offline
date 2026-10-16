# Birzzle Fever Offline

Source code, patch research, save-format analysis, and validation records for making **Birzzle Fever 1.1.2** usable after its original servers were retired.

The newest signed **technical checkpoint is V43**, with revised Rudy/Eve normal goals. The operator-requested **fresh installation without preserving saves** is now complete on the Galaxy S4 and S20 Plus; both installed APKs match the FruitSpy-signed checkpoint. Startup of the new normal-goal APK has not yet been manually tested on either device. **V42 remains the last two-device-qualified release milestone**, including the binary-safe save-token fix. The operator reports that all eight V42 functional release checks passed on the Galaxy S4 running Android 4.4.2 and the Galaxy S20 Plus running Android 13. The unlimited-hearts patch prevents the visible lives counter from decreasing.

## Release status

The GitHub repository is intentionally private during reproducibility and legal review. Private visibility does not relax the tracked-file policy: complete extracted packages, bulk assets, device captures, and private signing material remain excluded.

Newest technical checkpoint: `checkpoints/2026-09-26-v43-normal-goals-fruitspy-fdc05ae28a20/`; signed APK SHA-256 `fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`. The release certificate matches V42, but normal-goal V43 device qualification and independent public-distribution gates remain open. This checkpoint does not replace the frozen V42 qualified base.

V42 passed the following checks on both devices by operator report:

- fresh APK-only initialization;
- fresh-player progression;
- offline gameplay session;
- connected gameplay session;
- rewards and mutations;
- leaderboard;
- unlimited-life behavior;
- mature-save cold starts.

No progress loss, crashes, freezes, or softlocks were observed. These runs were deliberately empirical: no logs or save backups were collected. Zero lives are never displayed under the current patch, so starts from a displayed zero are not an applicable test. Potential undiscovered issues will be reviewed as users report them.

A release-signed V42 APK has been prepared locally. This does not by itself complete the independent distribution and build gates:

1. decide whether distribution may include a modified APK or must use a user-supplied-original patcher;
2. complete a reproducible current build from a user-supplied original APK;
3. complete the public-content/history audit and applicable release-material checks.

See [docs/TESTING.md](docs/TESTING.md) for the accepted V42 manual results and evidence limits, and [RELEASE_SIGNING_KEY.md](RELEASE_SIGNING_KEY.md) for the signed artifact and upgrade constraints. [V25_PROJECT_STATUS.md](V25_PROJECT_STATUS.md) is historical evidence, not the current release status.

## Repository contents

- Root `patch_*.py` and `build_*.py`: historical binary patch and packaging scripts.
- `reverse-engineering/`: narrow decompiled Smali excerpts actually analyzed during the project; complete decompiled trees are excluded.
- `native-patches/`: authored ARM/Thumb assembly, milestone notes, aggregate results, and the V25 release-evidence manifest.
- `xposed-birzzle-id-spoof/`: source for the earlier identity-spoofing research module. V25 does not require it.
- Save research: format, cryptography, state precedence, profile maps, response-pool reconstruction, and diagnostic tools.
- Device harnesses: targeted cold-launch, corruption, interrupted-write, and soak-checkpoint automation.
- `checkpoints/`: Markdown records for the principal V4, V7, and V11 device checkpoints. Their binary payloads remain local.
- `docs/`: architecture, building, testing, publication policy, and installation guidance.
- [CHANGELOG.md](CHANGELOG.md): accepted, investigative, and rejected milestones through V42.

## Deliberately excluded
This repository does not contain:

- original or modified APKs;
- extracted native libraries;
- complete extracted/decompiled game trees or bulk game assets; only reviewed code excerpts used by the reverse-engineering work are retained;
- save backups or embedded save archives;
- device logs, screenshots, or raw app-data captures;
- Android SDK/platform tools, apktool, LLVM toolchains, or vendored Python packages;
- debug or release signing keys.

Those files remain in the local research workspace and were not deleted. See [docs/REPOSITORY_POLICY.md](docs/REPOSITORY_POLICY.md).

## Research tools

Python 3.10 or later is recommended.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m unittest -v test_index_diagnostics.py
python scripts/validate_repository.py
```

Representative read-only analysis:

```powershell
python analyze_birzzle_save.py PATH_TO_DATA_OR_TAR
python diagnose_response_index.py PATH_TO_INDEX
python reconstruct_response_pool.py PATH_TO_DATA_OR_TAR
python decode_birzzle_profiles.py PATH_TO_DATA_OR_TAR
```

Device fault harnesses are destructive to app data by design. Read [docs/TESTING.md](docs/TESTING.md) before using them and supply your own authorized device serial through `ADB_SERIAL` or the script's `--serial` option.

## Building

The historical patch chain uses exact input hashes and stops on unknown binaries. It expects a locally supplied Birzzle Fever 1.1.2 APK and external tools that are intentionally not committed. The final V24/V25 package delta is documented, but the source-only repository does not yet claim a one-command reproducible V25 build.

See [docs/BUILDING.md](docs/BUILDING.md) and [RELEASE_SIGNING_KEY.md](RELEASE_SIGNING_KEY.md).

## Legal and project scope

This is an independent preservation and interoperability project. It is not affiliated with or endorsed by Enfeel, Halfbrick, Hangame, or other rights holders. Birzzle Fever and its original assets remain the property of their respective owners.

The repository license applies only to the original scripts, patch sources, and documentation contained here. It does not grant rights to the game, its assets, or locally held APK/save material. Obtain and use any original game copy lawfully, and comply with the law applicable in your jurisdiction.

## Documentation index

- [Architecture](docs/ARCHITECTURE.md)
- [Build and provenance](docs/BUILDING.md)
- [Installation model](docs/INSTALLATION.md)
- [Validation and test results](docs/TESTING.md)
- [Repository inclusion policy](docs/REPOSITORY_POLICY.md)
- [Contributing](CONTRIBUTING.md)
- [Save format](BIRZZLE_SAVE_FORMAT.md)
- [Response-pool root cause](PROGRESS_REGRESSION_ROOT_CAUSE.md)
- [Progression patch history](PROGRESS_REGRESSION_PATCHES.md)
- [V24/V25 regression history](V24_V25_REGRESSION_HISTORY.md)
