# Building and provenance

## Current boundary

This repository is a curated source import of the completed research workspace. It deliberately excludes every APK, extracted native library, decompiled game tree, embedded save archive, generated object/blob, toolchain, and signing key.

The historical builders remain auditable milestone specifications. `rebuild_v42.py` rebuilds all 1,140 V42 application payload entries from the pinned original APK, authored patch sources, and a separately supplied sanitized offline seed. It does not consume V41 or other historical APKs, prebuilt patched libraries, or a historical decompiled tree. The complete signed APK has now been reproduced byte-for-byte using a freshly regenerated signature from the authorized original release key; direct reference comparison and strict JAR verification passed.

## Required local inputs

Supply these outside Git:

- a lawfully obtained Birzzle Fever 1.1.2 APK (`com.halfbrick.birzzlefever`, version code 13);
- the historical standalone patchers accept extracted ARMv7 libraries; the clean V42 builder extracts them itself from the pinned original APK;
- the separately preserved sanitized offline seed ZIP for self-seeding builds; this server/bootstrap data is not recoverable from the original APK alone;
- apktool 2.12.1 or a validated compatible version;
- Android SDK Build Tools providing `zipalign` and `apksigner`, or a compatible JDK `jarsigner` for development builds;
- an ARMv7-capable LLVM/Clang toolchain for the authored Thumb assembly.

Keep all inputs under ignored local paths. Never weaken a script's source-hash or expected-byte checks to accept an unknown binary.

## Clean original APK to V42

The current verified host is Windows with Python 3.14, Temurin JDK 21.0.9, apktool 2.12.1, and the local LLVM-mingw 20260826 toolchain. `v42_rebuild_layout.json` pins the original APK, seed-independent release payload hashes, archive order/timestamps, signing timestamp, and tool hashes. The metadata file contains no replacement game payloads or stored signatures.

- Original APK SHA-256: `9bdfd11afd542265dbbc228a0205336806a77e59c739cbefd2b6f22e8741088c`.
- Separately supplied sanitized seed ZIP SHA-256: `654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c`.
- Target signed APK SHA-256: `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`.

Place the lawfully supplied inputs under ignored local paths, then run:

```powershell
python rebuild_v42.py --original analysis_extract/birzzlefever.apk --seed local-inputs/birzzle_seed_v1.zip --output native-patches/v42-clean-rebuild/my-build
```

The output directory must not already exist. This command regenerates both native libraries, applies the existing `reverse-engineering/smali` specifications and authored `SaveBootstrap`, normalizes original resources through a clean apktool roundtrip, and rebuilds DEX/resources. Historical directory names within the new workspace are freshly generated native stages, not reused binaries or APK inputs. The `--native-only` mode of the historical builders retains native source-hash and expected-byte checks while omitting APK packaging/signing.

The builder checks all 1,140 payload hashes and regenerates `MANIFEST.MF`, the signature file, and CMS signed attributes to their exact published hashes. JDK ZIP output preserves the release's compression and metadata; Python's zlib-ng compression does not reproduce those bytes. The frozen signing timestamp is intentional reproduction metadata, not a claim about the new build's wall-clock execution time.

### Regenerate the release signature privately

The operator selected fresh signing with the original private key, **not** reuse of the published signature block. Run the following in your own local terminal:

```powershell
python rebuild_v42.py --sign-build native-patches/v42-clean-rebuild/my-build --prompt-signing --reference native-patches/v42-binary-safe-tokens/release-signed/BirzzleFever-1.1.2-v42-release-signed.apk
```

The prompts read the private keystore path, alias, and passwords without saving them. Do not post credentials in chat or put them in repository files. Alternatively configure `BIRZZLE_KEYSTORE`, `BIRZZLE_KEY_ALIAS`, `BIRZZLE_STORE_PASSWORD`, and optionally `BIRZZLE_KEY_PASSWORD` privately in the local process environment. `BIRZZLE_SIGNATURE_NAME` is an optional private override only when the original JAR signature basename differs from the key alias.

`V42Reproducible.java` uses standard JDK APIs to generate deterministic RSA/SHA-256 CMS, validates the pinned public certificate, and never exports the private key. The completed signer must match the signature-block hash, signed APK hash, optional direct reference comparison, and strict JAR verification against a temporary public-certificate-only truststore. The reference APK is comparison-only; it supplies no bytes to the build. `rebuild-verification.json` is written only after those checks pass. Add `--sign --prompt-signing` to the initial build command to perform both phases in one invocation.

Verified signed output: `native-patches/v42-clean-rebuild/verified-build/BirzzleFever-1.1.2-v42-release-signed.apk`, SHA-256 `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`. `rebuild-verification.json` in that directory records original-key signature regeneration, exact whole-APK reference equality, and strict signature verification. No published signature block was reused.

## V43 offline Christmas test build

`build_v43_offline_christmas.py` takes the exact frozen V42 release APK and produces a separate development-signed test artifact. It does not modify the release or checkpoint. This is a hash-gated incremental build; use the verified clean-original V42 pipeline above to regenerate its base when needed.

```powershell
python build_v43_offline_christmas.py
python -m unittest test_offline_christmas test_eve_cooldown test_index_diagnostics test_binary_safe_tokens -v
```

Inputs: the pinned V42 APK at the builder's default path, LLVM-mingw's ARMv7-capable `clang`, `ld.lld`, and `llvm-objcopy` under `tools/llvm-mingw-20260826-ucrt-x86_64/bin/`, Python dependencies, JDK `jarsigner`, and the existing standard Android debug keystore under ignored `xposed-birzzle-id-spoof/build/`. No private release key is used.

The builder compiles the freestanding mission and Eve cooldown C helpers plus Thumb entry/syscall trampolines, checks every original hook, and appends a file-backed RX ELF segment without moving the original load segments or sections. It changes only `libbirzzle.so` and 15 localization assets; every other non-signature APK payload is checked against V42. JAR signature verification is strict against the debug keystore. Generated libraries, objects, APKs, command logs, and the hash report remain ignored.

External native calls use generated typed function bindings (`bindings.inc` / `bindings.o`), not linker `--defsym` assignments. ARM engine PLT entries require `STT_FUNC` with an even address so Thumb callers emit `BLX`; native Thumb targets use `.thumb_set`. The event-dialog regression executes the real PLT/GOT path and catches the original first-game `SIGILL` caused by untyped bindings.

The stage-texture adapter disables Thumb-to-ARM tail-call optimization: an ordinary call interworks through the ARM PLT without the absolute linker veneer produced by the tail call. Artwork regressions execute the packaged native code at a nonzero load bias.

Eve's mission presentation reuses complete Rudy actors through the engine's native copy API, retaining their styles and the existing event actor IDs. Copies are created once per dialog image load; subsequent openings update only the remaining amounts. Removing the old progress-bar animation still commits pending progress through the original save routine. The former 12-point font patches are no longer applied.

The event stays active until the original inventory ownership checks succeed for both Rudy and Eve. Mission counters alone never close it. Activity, queued dialog opens, banner hiding, and loaded-image cleanup handle the final-claim transition without changing catalog identity or Eve's timer. The date caption reads “Until both claimed.” See [event completion](SEASONAL_PETS.md#event-completion).

Seasonal artwork reconciles on the inventory-ready main-menu and post-claim inventory transitions. The existing background-only repaint receives theme-appropriate texture names through five scoped call-site hooks; native crop/tile geometry is retained. A transient theme byte uses existing event-manager padding, and the constructor initializes it without increasing the allocation or changing save serialization. The existing V41 scene-rearm hook is preserved.

Eve's reward cooldown uses `v43_eve.c` and `CLOCK_BOOTTIME`, not wall/server time. It retains the first immediately available gift and six-hour interval, stores remaining time with a boot UUID, and migrates the original reward profile. See [cooldown semantics](SEASONAL_PETS.md#eve-reward-cooldown), especially the conservative phone-reboot policy. Encrypted-profile regressions also require an OpenSSL installation with SEED-ECB support, located by the existing profile decoder.

Output: `native-patches/v43-offline-christmas/BirzzleFever-1.1.2-v43-offline-christmas-test.apk`; build evidence: `build-report.json` in the same directory. This signature requires a fresh installation over a release-signed installation; preserve and verify a rollback backup before uninstalling unless explicitly waived. Updates over the existing debug-signed V43 use an in-place installation and must retain the current save. Device launch/testing retains the explicit readiness gate.

The previous normal/reduced test artifacts are under `native-patches/v43-offline-christmas/inventory-id-fix/loader-corrected/normal/` and `inventory-id-fix/loader-corrected/reduced/`. Reduced goals remain Rudy 500,000 / 1 / 1,000 and Eve 1,000,000 / 2 / 2,000, built with an in-memory override rather than changing normal defaults. The builder also compiles `v43_inventory.c` and `v43_inventory.S` into the engine: preserve opaque transaction IDs in selection and update matching instead of narrowing 64-bit purchase IDs through `atoi`. Its appended ELF segment includes an explicit `PT_PHDR` so Android locates the relocated program-header table. Original IDs, save formats, crypto guards, and event gameplay remain unchanged. Each directory has its signed artifact and `build-report.json`; `inventory-id-fix/loader-corrected/native-verification.json` records packaged replay and loader-layout checks. Do not deploy the superseded APKs directly under `inventory-id-fix/{normal,reduced}`: their missing `PT_PHDR` caused immediate startup failure.

The newest **normal-goal signed artifact** is `native-patches/v43-offline-christmas/normal-goals-25-50/BirzzleFever-1.1.2-v43-normal-goals-FruitSpy-signed.apk`, SHA-256 `fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`: Rudy 100,000,000 score / 25 Mystery Boxes / 25,000 coins; Eve 200,000,000 / 50 / 50,000. Its external FruitSpy public certificate SHA-256 is `7e9ad31c19d7ee447c8e1a58bc7ca4be51acf4489f55cf2258124c45d7213417`, identical to frozen V42. `FruitSpy-signing-report.json` records strict pinned signature, ZIP integrity, and unchanged bytes for all 1,140 non-signature entries; `signed-verification.json` records packaged ARM smoke for both claim orders, restored ordinary artwork, goals, Android-mapped engine headers, Rudy's exact transaction ID, and a second valid save with full-width IDs on other pets. All 40 focused regressions pass. The older `inventory-id-fix/loader-corrected/normal/` still embeds superseded 50/50,000 and 100/100,000 box/coin thresholds. The inventory transaction-ID correction applies to any pet with a valid inventory structure; no independent array-index bounds guard is claimed.

**Historical reduced-build S20 qualification:** before the operator-requested fresh install, the reduced APK had installed hashes, unchanged UID, disabled debugging, and metadata of 222 known private files verified. Operator testing confirmed Rudy selection persistence, switching pets, gameplay, upgrade isolation, and Eve's gift/event behavior. Eve is not equippable and all other pets had already been unlocked, so a new equippable-pet acquisition was host-tested only. The prior S4 artwork build showed ordinary backgrounds after closure. The **current** status differs: both devices' old packages and app data were erased without backups; both now have the FruitSpy-signed normal APK, with installed hashes matching the checkpoint. S20's initial Play Protect denial was resolved by a subsequent standard install with the operator ready to respond; no security setting was changed. Neither device has launched the new installation. Evidence: `device-snapshots/v43-fruitspy-normal-goals-fresh-install/deployment.json`. Do not reuse the faulty `.ab` timestamp restoration method. See [inventory verification scope](TESTING.md#inventory-transaction-id-correction--s20-focused-checks-passed); game UI remains operator-controlled.

The **newest signed technical checkpoint** is `checkpoints/2026-09-26-v43-normal-goals-fruitspy-fdc05ae28a20/`. Its `manifest.json`, `SHA256SUMS.txt`, and read-only `checkpoint.zip` record 22 verified members: the signed normal-goal APK, exact native libraries, authored sources, public signing certificate, and host qualification evidence. Archive SHA-256: `b7c3dd0c46fc95eb65549179ebfbbbb498d765c55d6ce18995fec5fce957c02d`. The archived development build report replaces its machine-local path with a relative name; the original output report remains unchanged. This checkpoint references the frozen V42 checkpoint by hash rather than modifying or duplicating it. No private key, passwords, device save, or personal capture is bundled. This checkpoint is signed and host-verified, **not** a public release or device-qualified APK; the FruitSpy signer cannot update the installed debug-signed V43 in place.

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
- `unicorn`: host ARM/Thumb execution of token-generation regression paths.

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

## V42 binary-safe token candidate

The local builder requires exact V41 at `native-patches/v41-dual-powerup-scene-rearm/BirzzleFever-1.1.2-v41-dual-powerup-scene-rearm.apk` plus the existing development keystore and JDK `jarsigner`. It is a hash-gated incremental builder, not a clean-clone original-APK pipeline.

```powershell
python build_v42_binary_safe_tokens.py
python -m unittest test_index_diagnostics test_binary_safe_tokens -v
```

The builder changes only the binary-digest length calculation in `libef2d.so`, verifies the signature, and compares every other APK payload against V41. Outputs and a hash report are under `native-patches/v42-binary-safe-tokens/`. The tests run without ADB; native instruction tests hook external libc/Base64 boundaries, so they do not replace physical-device qualification.

### Qualified pre-Christmas base

The stable technical checkpoint is `checkpoints/2026-09-23-v42-stable-pre-christmas-766ecc422f81/`; qualification, archive checksums, and limitations are recorded in [TESTING.md](TESTING.md#stable-pre-christmas-checkpoint). Its release APK SHA-256 is `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`, and its public certificate DER SHA-256 is `7e9ad31c19d7ee447c8e1a58bc7ca4be51acf4489f55cf2258124c45d7213417`.

The archive preserves the exact V41 input APK and 142 tracked/nonignored untracked source files as they existed at qualification, individually hashed. Git base commit `facc165afc5fc7ac03ca7d14e91e400257952f03` identifies repository ancestry, not a claim that the working tree was clean. Historical build reports retain their original development-signing hashes and pre-qualification flags; the checkpoint manifest identifies the qualified release. No private signing key is bundled, and this snapshot does not remove the clean-clone reproducibility boundary.

## Assembly

Authored assembly is retained under `native-patches/` as `.S` source. Generated `.o`, `.elf`, and `.bin` files are ignored. Rebuild generated blobs with an ARMv7 Thumb target, then verify their hashes and placement using the matching root patch script.

The exact compiler/linker flags used by each late milestone should remain beside its assembly or patch script. Where a historical script expects a prebuilt `.bin`, the missing source-to-blob command is a reproducibility gap, not permission to commit the blob.

## V24/V25 package delta

The original V24/V25 package work required these changes:

1. install the accepted V15 `libbirzzle.so` lineage containing identity, ranking/menu, and no-heart-deduction patches;
2. install the V23 `libef2d.so` lineage and patch `NetworkStatusSync()` to `movs r0,#0; bx lr` at the validated function offset;
3. replace Java reachability methods with compatibility-success returns;
4. skip GCM registration and remove the Birzzle-specific GCM receiver/service declarations;
5. add `SaveBootstrap` and call it from `MyApplication` before normal native initialization;
6. include the sanitized 26-file seed and preserve exact Unix mtimes from ZIP field `0x5455`;
7. use the V25 two-slot ranking template rather than V24's one-slot template;
8. rebuild, align, sign, verify, and compare every retained native library and seed hash with `native-patches/v25-ranking-template/release-evidence.json`.

The historical decoded tree remains excluded because it contains proprietary game material. The clean V42 builder now expresses these Java/package changes using the existing authored snippets, retains the later corrected native lineage, and reconstructs resources from the original APK rather than copying this tree. The sanitized offline seed remains an explicit external input.

## Signing

Development builds historically used an Android debug key. Public updates must retain the selected protected release-signing identity; see [RELEASE_SIGNING_KEY.md](../RELEASE_SIGNING_KEY.md). Private key locations, internal aliases, and unrelated project associations do not belong in public build documentation.

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
- the evidence category for each behavioral result; V42's two-device manual passes are empirical reports with no logs or save backups, not automated or snapshot-backed passes;
- confirmation that `python scripts/validate_repository.py` passes before committing release metadata.
