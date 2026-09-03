# Contributing

## Scope

Contributions should improve preservation, reproducibility, compatibility, diagnostics, or documentation without adding original game payloads.

Useful work includes:

- converting historical patch steps into exact validated transforms;
- documenting ARM/Thumb hooks and control-flow invariants;
- making device harnesses configurable and safer;
- adding deterministic analyzers for save and response-pool formats;
- reproducing V25 on another lawfully controlled ARMv7 device;
- reducing raw evidence to privacy-safe aggregate results;
- implementing a user-supplied-original patcher.

## Do not submit

- APKs, native game libraries, assets, or decompiled game trees;
- save backups, seed archives, response-pool records, or profiles;
- logs, screenshots, device serials, Android IDs, tokens, or personal data;
- signing keys or passwords;
- toolchain and SDK downloads;
- compatibility claims not backed by an exercised scenario.

The automated repository validator rejects common forbidden extensions and known private identifiers, but review remains mandatory.

## Development setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m unittest -v test_index_diagnostics.py
python scripts/validate_repository.py
```

Historical device harnesses require separate ignored inputs and may be destructive. Do not run them as ordinary unit tests.

## Patch requirements

A binary patch must:

1. identify the exact source artifact by SHA-256;
2. validate the original bytes at every modified range;
3. document architecture state, file/virtual offsets, and resumed control flow;
4. fail closed on any mismatch;
5. avoid expanding the patch beyond the stated invariant;
6. record the output hash;
7. include a behavioral test plan that would fail under the original defect.

Generated `.bin`, `.o`, `.elf`, `.so`, and APK outputs remain local. Commit the assembly and deterministic generation instructions instead.

## Test reports

State facts, not expectations:

- exact device model, Android version, ABI, package version, and build hash;
- initial data state and network state;
- precise sequence exercised;
- observed pass/failure condition;
- response-pool or save invariants checked;
- known exclusions and interrupted/invalid runs.

Do not publish raw whole-device logcat. A reviewed aggregate should contain only events necessary to support the result.

## Change discipline

- Preserve accepted patch lineage unless the change explicitly replaces it.
- Keep rejected experiments labeled; do not silently promote them.
- Update `CHANGELOG.md`, affected architecture/build notes, and the validation matrix for behavior changes.
- Do not alter hashes to fit an unexplained output.
- Do not claim broad Android support from one device.
