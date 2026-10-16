## Core Project Objective

Birzzle Fever 1.1.2 is being converted into a deterministic, self-contained offline Android game that no longer depends on its retired servers, Xposed, Titanium Backup, or a device-specific Linux UID. The production path combines a patched ARMv7 APK, a sanitized embedded save seed, a connectivity-independent response backend, and native fixes for leaderboard delivery, scene returns, persistent progression, and unlimited play. V41 subsequently failed manual mission-claim testing because its token generator could persist an empty index `KEY`. V42 fixes binary token encoding and is built, signed, and host-verified; installation and recovered-save device qualification remain gated on explicit readiness. Prior exact-V41 qualification results do not qualify V42.

## Architectural & Design Decisions

- **Exact package and candidate:** Android package `com.halfbrick.birzzlefever`; new APK is `native-patches/v42-binary-safe-tokens/BirzzleFever-1.1.2-v42-binary-safe-tokens.apk`, SHA-256 `72e02bf723969d857616b90520a0bfc6e877446dddac6c9316706be43e461506`. V41 (`5a1ed5e21b5709c305251eb7b83340d7beb941f27f97ac9db1070fc13146cf88`) remains the last captured installed build. Any binary change creates a new candidate and invalidates exact-build qualification evidence.
- **Target architecture:** Original 32-bit ARM/Thumb native code is preserved and patched surgically. Galaxy S4/Android 4.4.2 is the primary qualification device; newer ARMv7 Android coverage remains a separate gate.
- **Historical game identity:** `BirzzleFever.GetUniqueDeviceID()` resolves to historical identity `3c8bb7308c3fcb60c439224bd595c794d8f31501`. This identity selects hashed save/response filenames and offline profile data; it is unrelated to Android’s installation-specific package UID.
- **Linux ownership:** Every fresh install may receive a different UID. Self-seeding naturally creates data under the assigned UID, and manual/Titanium restores must remap ownership; ten V41 fresh installs passed under UIDs `10250` through `10259`.
- **APK-only self-seeding:** V42 retains V41's sanitized `assets/birzzle_seed_v1.zip`, SHA-256 `654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c`. A missing `.birzzle_seed_v1` marker triggers extraction; the marker prevents repeat initialization. The embedded seed is the public deployment path, not the untouched 2016 Titanium bundle.
- **Timestamp invariant:** CCrypt2 and proprietary profiles authenticate or compare embedded timestamps against filesystem `mtime`; extraction/restoration must preserve exact Unix modification times. Ownership, modes, traversal permissions, and timestamps are independent invariants.
- **Offline routing:** Java startup reports compatible reachability, obsolete GCM startup is removed, and native `CRequestQueue::NetworkStatusSync()` selects the local response backend. “Offline” means playable without revival servers or network access; blocking every analytics/OS network call is not required.
- **Response-pool model:** The authoritative local pool uses an index shaped `-1,N` plus numbered encrypted response records. Valid state is monotonic, contiguous, warning-free, cryptographically readable, and accepted by native field parsing; request zero and all prior numbered records must remain byte-identical across ordinary progression. An empty `KEY:` is native-unreadable even when its checksum and timestamp are valid.
- **Persistence ordering:** Request data is committed before the response index. The later writer derives temporary/index paths from the same authoritative runtime directory and uses same-mount atomic operations, avoiding the `/data/data` versus `/data/user/0` `EXDEV` failure seen on newer Android.
- **Ranking template:** The sanitized seed contains the required two-slot `SCORE.RANKING` template using the historical identity in both slots with distinct sentinel scores `-1` and `0`. Equal duplicate entries and one-slot templates are invalid because they caused native leaderboard crashes, missing personal scores, or dummy-player UI behavior.
- **Ranking dispatch gate:** Only one ranking delivery may be in flight for a generation. Startup protection remains closed until the current leaderboard UI consumes its response; later deliberate main-menu refreshes re-arm the generation instead of dropping or duplicating callbacks.
- **V41 scene re-arm:** V41 preserves the accepted V37 lineage and updates `CStoryManager::SetCurrentScene()` so both legacy scene `0x0A` and observed power-up scene `0x1A` arm the pending ranking generation. This covers normal completion, mid-game quit, power-up cancellation, bonus/tutorial, and pet-flow routes through the shared scene transition. V41 contains no V38–V40 diagnostic trace writes.
- **V42 binary-safe tokens:** `MathUtility::GenerateToken()` now encodes exactly 16 binary MD5 bytes instead of calling `strlen()` on them. The only native delta is four bytes at `libef2d.so:0x122ca6`; every other APK payload is unchanged from V41. The existing mature-pool fail-closed retry guards are intentionally retained: returning a rejected mature index as empty could overwrite progression.
- **Pet tutorial behavior:** The free-pet/BuyPet completion path must deliver its response and allow the subsequent ranking/menu flow. The former pet-tutorial softlock is a required manual regression check on every virgin-install qualification.
- **Unlimited play:** The accepted native path bypasses heart gating at game start and supplies five usable lives to the power-up/start flow. The main menu may still display the stored life count; the observable contract is that play remains startable at zero without a purchase prompt.
- **No Xposed dependency:** Xposed identity-spoof modules v1/v2 are preserved only as historical rollback/research artifacts. V41 hardcodes the historical identity and must pass with `com.example.birzzleid` absent and no module enabled.
- **No Titanium dependency:** Untouched and checkpoint Titanium bundles remain recovery/research inputs. Public fresh installation is APK-only; restoring the original APK over V41 is prohibited.
- **Qualification boundary:** The user exclusively performs taps, swipes, Back presses, game actions, network toggles, and visual judgments. ADB may verify the package, clear/start log capture, launch the exact activity, inspect the process, force-stop after “hands off,” and capture read-only checkpoints; it must never drive the game UI.
- **Evidence model:** Checkpoint manifests use schema version `1`. Every checkpoint contains a full app-data tar, bounded logs, response-pool report, profile report, generic-save report, artifact hashes, exact APK hash, process state, and fatal-marker result. Adjacent comparisons reconstruct data rather than trusting summaries.
- **Stop policy:** A crash, native fatal signal, ANR, freeze, softlock, stuck loading overlay, duplicate/missing own-score row, identity change, first-run reset, unexplained progression regression, invalid/noncontiguous pool, changed request zero, changed prior record, analyzer warning, or evidence hash failure ends the qualification; evidence is captured without repair or retry.
- **Release separation:** Primary-device functional qualification, second-device compatibility, reproducible user-supplied-original build, legal distribution choice, dedicated release-key signing, immutable artifact freeze, and publication documentation are independent gates.

## Modified & Created Files

- `build_v42_binary_safe_tokens.py`, `native-patches/v42-binary-safe-tokens/`
  - Exact-V41 hash-gated builder; signed V42 APK, patched `libef2d`, `build-report.json`, and `host-verification.json`. Host proof exercises the real Thumb call site with external libc/Base64 hooks, including zero bytes at every digest position; it is not device qualification.
- `test_binary_safe_tokens.py`, `test_index_diagnostics.py`, `requirements-dev.txt`
  - Nine targeted native-token, analyzer, and lossless-recovery regression tests passed. Unicorn is the ARM emulation dependency.
- `repair_empty_index_token.py`
  - Offline archive-to-archive repair restricted to the authenticated empty-token writer defect. Preserves index bounds, timestamp/mtime, ownership/modes, and all unrelated file bytes; refuses other pool defects. Never accesses ADB.
- `device-snapshots/2026-09-20-s4-v41-mission-claim-failure/`
  - Original failure archive and post-diagnostic capture; request range `0..18`, index `-1,18`, claims 40/50 persisted, claim 60 absent. `failure_state/diagnosis.json` and native backtrace document the empty-key rejection and retry stall. Historical analyzer outputs are preserved but superseded by corrected analysis.
- `device-snapshots/2026-09-20-s4-v42-token-recovery/`
  - `recovered-app-data.tar.gz`: staged recovery, not deployed. Only the index envelope changes; all 19 request records and the other 68 regular files are unchanged. `original-pool-corrected-analysis.json` reports `INDEX_REJECTED`; `recovered-pool-analysis.json` reports `CONSISTENT`.
- `build_v41_dual_powerup_scene_rearm.py`
  - Rebuilds V41 from the exact V37 source APK/library, verifies source/library/classes/seed hashes, applies the trace-free dual-scene marker, repackages, and signs with the existing development key.
- `native-patches/v41-dual-powerup-scene-rearm/`
  - `BirzzleFever-1.1.2-v41-dual-powerup-scene-rearm.apk`: last captured installed candidate; superseded for further qualification by V42.
  - `BirzzleFever-1.1.2-v41-dual-powerup-scene-rearm-unsigned.apk`: unsigned intermediate.
  - `libbirzzle-v41-dual-powerup-scene-rearm.so`: patched gameplay/ranking native library.
- `native-patches/v37-global-powerup-scene-marker/`
  - Immediate production ancestor carrying the global scene-store hook and accepted ranking lineage.
- `native-patches/v31-ranking-lineage-correction/` through `native-patches/v40-scene1a-rearm-trace/`
  - Preserved pet tutorial, ranking-generation, scene-tracing, and dispatch investigations. V38–V40 are diagnostic evidence, not release artifacts.
- `native-patches/v25-ranking-template/`
  - Accepted sanitized two-entry ranking seed and earlier APK-only offline baseline. Its `assets/birzzle_seed_v1.zip` contract is retained by the later lineage.
- `build_v26_modern_syscalls.py`, `build_v23_request_first.py`, `patch_first_read_recovery_v22.py`, `patch_response_index_hardening_v21.py`
  - Persistence lineage for modern same-mount writes, request-first commit order, controlled first-read recovery, and response-index validation.
- `build_v15_portable_apk.py`, `patch_no_heart_deduction_v15.py`, `build_hardcoded_identity_apk.py`
  - Historical integration points for portable packaging, unlimited-play behavior, and native identity hardcoding retained by later builds.
- `xposed-birzzle-id-spoof/`
  - `BirzzleIdentitySpoof-v1.apk` and source: historical identity-only module.
  - `BirzzleIdentitySpoof-v2.apk` and source: historical identity/offline experiment.
  - No module is required or installed for V41 qualification.
- `reconstruct_response_pool.py`, `diagnose_response_index.py`
  - Decode and validate `-1,N`, numbered responses, record hashes, contiguity, cryptographic validity, native required-field parsing, and recovery state. Empty tokens are rejected; legacy nonempty short tokens remain accepted.
- `analyze_birzzle_save.py`, `decode_birzzle_profiles.py`, `PROFILE_FIELD_MAPS.md`, `STATE_PRECEDENCE.md`
  - Generic save/profile decoders and documented precedence needed to identify real progression versus stale cache values.
- `capture_v25_soak_checkpoint.py`
  - Version-neutral schema-1 quiesced capture logic despite its historical filename: force-stop, tar, pull, log scan, pool/profile/save analysis, hashing, and manifest emission.
- `compare_v25_soak_checkpoints.py`
  - Version-neutral schema-1 adjacent comparison logic: artifact verification, exact APK compatibility, monotonic pool/index checks, request-zero preservation, and prior-record byte preservation.
- `stress_v21_first_read_faults.py`, `stress_v22_first_read_faults.py`, `test_v23_mid_session_faults.py`, `test_stage_e_interrupted_writes.py`
  - Existing destructive/recovery harnesses to be adapted to exact V41 only after a mature checkpoint is secured.
- `device-snapshots/2026-09-06-s4-v41-self-seed-ten-manual-first-launches/`
  - Ten independent fresh-install runs; `aggregate-results.json` records 10/10 leaderboard and pet-tutorial passes, 20 ranking responses, zero fatal markers/ANRs, and ten distinct UIDs.
- `device-snapshots/2026-09-06-s4-v41-cumulative-qualification/`
  - `qualification-config.json`: exact V41/seed hashes and test boundary.
  - `00_baseline/manifest.json`: schema-1 quiesced baseline, response index `-1,4`.
  - `01_offline_session/manifest.json`: schema-1 post-session checkpoint, response index `-1,22`.
  - `comparisons/00_baseline_to_01_offline_session.json`: passed comparison; 18 contiguous added records, unchanged request zero and prior records.
  - `operator-output/00_preflight.json`, `00_baseline-validation.json`, `01_offline-ledger.json`, `01_offline-summary.json`: exact preflight, user report, and qualification disposition.
  - `raw-logs/`: bounded baseline and full offline-session logcat inputs.
- `checkpoints/2026-09-06-v41-production-pre-clean/`
  - Preserved V41 release artifacts/checksums, signing-key copy, prior Titanium bundle, V40 diagnostic artifacts, and clean-deployment evidence.
- `device-snapshots/2026-09-06-s4-v41-production/` and `device-snapshots/2026-09-06-s4-v40-scene1a-rearm-trace/`
  - Production startup evidence and immediate diagnostic predecessor evidence.
- `com.halfbrick.birzzlefever-20160501-111000.properties`, `com.halfbrick.birzzlefever-20160501-111000.tar.gz`, `com.halfbrick.birzzlefever-a626a1d45ccbedeb6dee1e6805dd0916.apk.gz`
  - Untouched May 1, 2016 Titanium Backup source retained for forensic/recovery testing, not the public installation path.
- `BIRZZLE_SAVE_FORMAT.md`, `BIRZZLE_PROPRIETARY_PROFILES.md`, `MINIMAL_PUBLIC_SAVE.md`, `PROGRESS_REGRESSION_ROOT_CAUSE.md`, `POST_GAME_COMMIT_ORDER.md`
  - Save cryptography, profile schemas, minimal seed, regression cause, and persistence-order documentation.
- `V21_ROADMAP.md`, `V25_PROJECT_STATUS.md`, `V25_PROLONGED_SOAK_PLAN.md`, `CHANGELOG.md`, `docs/ARCHITECTURE.md`, `docs/TESTING.md`, `docs/INSTALLATION.md`, `docs/BUILDING.md`
  - Historical acceptance criteria and publication/build guidance. They still name V25 in places and require a later documentation cutover only after V41 qualification is final.

## Immediate Next Steps & Manual Testing Scope

- **Exact pending task:** wait for explicit device readiness before installation, repair, launch, or log capture. Then preserve a fresh hands-off snapshot, verify the current APK/save identity, install exact V42 with data retained, and deploy only the repaired index if the current index and all 19 numbered records still match the captured failure. Stop rather than overwrite newer user progress.
- **Last captured device state:** V41 was force-stopped after the startup diagnostic. Request history and the malformed index were unchanged; startup modified `new2profile.dat` and analytics. No V42 APK or repaired index has been installed. Do not infer that the device has remained unchanged since that capture.
- **Recovery boundary:** retain the original failure archive (SHA-256 `3846ba8d0ccadc47d1f3e47c551d631007301237219b5fa101e50d701dc66d94`). Preserve index payload `-1,18`, timestamp/mtime `1789693266`, current app ownership, and file mode. Do not reset the seed marker, replace the whole live save, or award the outstanding mission automatically.
- **Manual scope:** verify recovered startup reaches the menu without a connection error or stuck loading; confirm retained progression; claim the remaining completed mission; exercise successive legitimately earned mission claims and a cold restart. The user alone performs all taps and visual judgments. Stop at the first anomaly.
- **User report format:** preserve the report verbatim before interpretation. Record network state, action order, visible scene, loading behavior, mission/reward state, leaderboard, and any progression discrepancy.
- **UI/ADB handoff:** print the exact readiness prompt before device testing. Once ready, prepare the fixed candidate/recovery, clear/start logs, launch the package using the mandated bootstrap, then release the UI. Do not run ADB commands while the user owns the UI.
- **Log integration:** retain a persistent package-test capture and the `.omp/current_test_log.txt` buffer. Inspect package-scoped messages, relevant runtime exceptions, and severe failures; remind the user to run `/shake` after log analysis.
- **Failure integration:** on a failure report, preserve the exact symptom and capture the failure state without retry, relaunch, reset, or further repair.
- **Checkpoint integration:** establish a new exact-V42 baseline and compare only adjacent V42 checkpoints. Require valid hashes, stopped process, no relevant fatal markers, a `CONSISTENT` pool, unchanged previous records, and contiguous additions. Never compare V41/V42 as an ordinary same-build qualification transition.
- **Historical plan:** the V41 `02_connected_session` and subsequent durability/fault gates are suspended. The preserved V41 fresh-install/offline passes remain historical evidence, not V42 acceptance. A full V42 qualification plan follows only after the targeted token/recovery regression passes.
