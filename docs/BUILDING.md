# Building and provenance

## Current boundary

This repository is a curated source import of the completed research workspace. It deliberately excludes every APK, extracted native library, decompiled game tree, embedded save archive, generated object/blob, toolchain, and signing key.

Consequently, the committed historical scripts are auditable patch specifications, but a clean clone does **not yet produce V25 with one command**. Several scripts consume the output of the previous milestone, and the final V24/V25 package work was performed in a local apktool tree that also contains proprietary game material. Do not represent the repository as reproducible until a user-supplied-original patcher covers that delta.

## Required local inputs

Supply these outside Git:

- a lawfully obtained Birzzle Fever 1.1.2 APK (`com.halfbrick.birzzlefever`, version code 13);
- its ARMv7 native libraries extracted from the APK;
- the sanitized seed created under the policy documented in `MINIMAL_PUBLIC_SAVE.md`, if building the self-seeding variant;
- apktool 2.12.1 or a validated compatible version;
- Android SDK Build Tools providing `zipalign` and `apksigner`, or a compatible JDK `jarsigner` for development builds;
- an ARMv7-capable LLVM/Clang toolchain for the authored Thumb assembly.

Keep all inputs under ignored local paths. Never weaken a script's source-hash or expected-byte checks to accept an unknown binary.

## Python environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
```

Dependencies:

- `pycryptodome`: save and response-index cryptography;
- `pyelftools`: ELF metadata validation and patching;
- `capstone`: ARM/Thumb disassembly research;
- `Pillow`: image-state checks in interactive device harnesses.

## Historical native lineage

The root scripts encode the chronological patch chain. They generally:

1. hash the exact source library;
2. compile or load an authored Thumb stub;
3. validate expected bytes at every hook/cave/ELF field;
4. write a new native library under `native-patches/<milestone>/`;
5. rebuild and development-sign an APK.

Important production lineage:

```text
V1–V3   ranking crash experiments and hardcoded historical identity
V4–V14  ranking in-flight/generation/menu transition work
V15     accepted no-heart-deduction boundary
V20     response-index retention root fix
V21     persistent maturity and missing-record validation
V22     first-read recovery and timestamp tolerance
V23     request-first atomic index ordering
V24     deterministic local route, GCM removal, exact-time bootstrap
V25     stable two-slot ranking seed template
```

V16–V19 include valuable defensive and fault-injection experiments. The final gameplay lineage returns to the unclamped V15 library; it does not carry the rejected broad economy clamps.

## Assembly

Authored assembly is retained under `native-patches/` as `.S` source. Generated `.o`, `.elf`, and `.bin` files are ignored. Rebuild generated blobs with an ARMv7 Thumb target, then verify their hashes and placement using the matching root patch script.

The exact compiler/linker flags used by each late milestone should remain beside its assembly or patch script. Where a historical script expects a prebuilt `.bin`, the missing source-to-blob command is a reproducibility gap, not permission to commit the blob.

## V24/V25 package delta

A public patcher must apply the following changes to a freshly decoded user-supplied APK:

1. install the accepted V15 `libbirzzle.so` lineage containing identity, ranking/menu, and no-heart-deduction patches;
2. install the V23 `libef2d.so` lineage and patch `NetworkStatusSync()` to `movs r0,#0; bx lr` at the validated function offset;
3. replace Java reachability methods with compatibility-success returns;
4. skip GCM registration and remove the Birzzle-specific GCM receiver/service declarations;
5. add `SaveBootstrap` and call it from `MyApplication` before normal native initialization;
6. include the sanitized 26-file seed and preserve exact Unix mtimes from ZIP field `0x5455`;
7. use the V25 two-slot ranking template rather than V24's one-slot template;
8. rebuild, align, sign, verify, and compare every retained native library and seed hash with `native-patches/v25-ranking-template/release-evidence.json`.

The local decoded tree remains available in the research workspace but is excluded because it contains the original application's code and assets. The next build-system milestone is to express the delta above as narrow, validated transforms without redistributing that tree.

## Signing

Development builds historically used an Android debug key. Public releases must use a dedicated protected key; see [RELEASE_SIGNING_KEY.md](../RELEASE_SIGNING_KEY.md).

Never commit:

- the private keystore;
- passwords or unattended password arguments;
- unsigned/signed APK outputs;
- extracted game libraries;
- apktool output directories.

## Verification before release

A release build is acceptable only when all of the following are recorded:

- input APK package/version and cryptographic hash;
- every applied patch and expected-byte check;
- native library and seed hashes;
- APK hash and signing-certificate fingerprint;
- `apksigner verify --verbose --print-certs` output;
- clean-install self-seed result;
- the behavioral matrix in [TESTING.md](TESTING.md);
- confirmation that `python scripts/validate_repository.py` passes before committing release metadata.
