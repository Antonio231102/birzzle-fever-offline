# Birzzle Fever Offline Preservation

Source code, patch research, save-format analysis, and validation records for making **Birzzle Fever 1.1.2** usable after its original servers were retired.

The current development milestone is **V25**. On the tested 32-bit ARM Galaxy S4 running Android 4.4.2, V25 starts without a network interface, initializes from a sanitized local seed, preserves progression, reconstructs the personal leaderboard, permits play at zero displayed lives, and requires neither Xposed nor Titanium Backup for a fresh installation.

## Release status

V25 passed the project's single-device functional qualification:

- fresh APK-only initialization;
- offline and connected multi-session play;
- ten mature cold launches;
- nine first-read response-index fault cases;
- repeated power-up cancellation, mid-game quit, and completed-game return paths;
- response-pool continuity and byte-preservation checks;
- personal-score leaderboard refreshes without the historical crash or softlock.

This is **not yet a public binary release**. Remaining gates:

1. decide whether distribution may include a modified APK or must use a user-supplied-original patcher;
2. complete a reproducible V25 build from a user-supplied original APK;
3. sign the release with a dedicated key;
4. test another supported ARMv7 device before claiming broad compatibility.

See [V25_PROJECT_STATUS.md](V25_PROJECT_STATUS.md) for exact evidence and limitations.

## Repository contents

- Root `patch_*.py` and `build_*.py`: historical binary patch and packaging scripts.
- `native-patches/`: authored ARM/Thumb assembly, milestone notes, aggregate results, and the V25 release-evidence manifest.
- `xposed-birzzle-id-spoof/`: source for the earlier identity-spoofing research module. V25 does not require it.
- Save research: format, cryptography, state precedence, profile maps, response-pool reconstruction, and diagnostic tools.
- Device harnesses: targeted cold-launch, corruption, interrupted-write, and soak-checkpoint automation.
- `checkpoints/`: Markdown records for the principal V4, V7, and V11 device checkpoints. Their binary payloads remain local.
- `docs/`: architecture, building, testing, publication policy, and installation guidance.
- [CHANGELOG.md](CHANGELOG.md): accepted, investigative, and rejected milestones from V1 through V25.

## Deliberately excluded

This repository does not contain:

- original or modified APKs;
- extracted native libraries or decompiled game contents;
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
