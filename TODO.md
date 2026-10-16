# Release roadmap

V42 is the last two-device-qualified release milestone; the newest signed technical checkpoint is V43 (`checkpoints/2026-09-26-v43-normal-goals-fruitspy-fdc05ae28a20/`). All eight named V42 functional release checks passed on the Galaxy S4/Android 4.4.2 and Galaxy S20 Plus/Android 13 by operator report. Those empirical runs intentionally collected no logs or save backups. The V43 normal-goal APK is FruitSpy-signed but not installed or physically qualified on either device; independent distribution, build, and publication tasks remain below.

## Distribution decision

- [ ] Complete legal review of modified-APK redistribution.
- [ ] If redistribution is not approved, ship only a user-supplied-original patcher.
- [ ] Document provenance requirements for the sanitized bootstrap seed.
- [x] Use the `birzzle-fever-offline` repository name with private visibility under the authenticated GitHub account.

## Reproducible build

- [ ] Convert the V1–V23 historical chain into a clean transform from a validated user-supplied Birzzle Fever 1.1.2 APK.
- [ ] Express V24 Java/manifest/GCM/network changes as narrow expected-input patches rather than publishing a decompiled tree.
- [ ] Reproduce `SaveBootstrap` and the V25 two-slot ranking template without committing save archives.
- [ ] Rebuild every ARM/Thumb blob from tracked `.S` sources with pinned commands.
- [ ] Verify every input range, output library, seed, APK, and signing certificate hash.
- [ ] Produce the same functional V25 result without depending on prior milestone APKs.

## Release signing

- [x] Sign V42 with the operator-selected protected external release key; record signature verification and artifact checksums without publishing private key details.
- [ ] Store at least two encrypted offline key backups and keep the password separately.
- [ ] Publish only the certificate and fingerprint.
- [ ] Record alignment, signature schemes, and `apksigner` verification in the release manifest.

## Compatibility

- [x] Fresh APK-only initialization — passed on both reported devices.
- [x] Fresh-player progression — passed on both reported devices.
- [x] Offline gameplay session — passed on both reported devices.
- [x] Connected gameplay session — passed on both reported devices.
- [x] Rewards and mutations — passed on both reported devices.
- [x] Leaderboard — passed on both reported devices.
- [x] Unlimited-life behavior — passed on both reported devices; lives do not decrease, so displayed-zero starts are not applicable.
- [x] Mature-save cold starts — passed on both reported devices.
- [x] Record empirical acceptance and limitations in `docs/TESTING.md`: no observed progress loss, crashes, freezes, or softlocks; no logs/save backups; review undiscovered issues as users report them.

These are operator-reported functional passes, not new evidence of exact iteration counts, save-byte invariants, destructive fault coverage, or support for every Android device.

## Instrumented S4 integrity validation

- [x] Ten V42 read-fault preservation/recovery cases — captured logs, snapshots, and prior-record hash checks.
- [x] Three V42-derived process-interruption boundaries — pause location verified; production recovery and second-restart idempotence checked.
- [x] Restore and verify the original save and production native library; remove temporary device staging and stop capture.

Scope and observations are recorded in `docs/TESTING.md`. These passes do not claim physical power-loss durability. All three boundary recoveries added one heart without repeating the adjustment on a second restart; intended gameplay semantics and the earlier kernel SIGKILL causes remain unconfirmed.

## V42 final checkpoint before Christmas-event development

Preserve all accepted two-device functional passes and the completed S4 integrity/purchase evidence. Do not repeat those matrices or treat the inactive Christmas pets as V42 failures. Focused closure results and remaining checks:

- [x] Installed APK identity verified on both devices against release SHA-256 `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`; packaged and extracted native libraries also match production. Evidence: `device-snapshots/v42-two-device-release-closure-20260922T234302Z/identity-verification.json`.
- [x] Background, screen-lock, and device-reboot recovery — passed empirically on both S4 and S20. The operator reports graceful automatic pausing in the first two scenarios, no observed progress loss, and correct progress loading after a full device reboot. Accepted without requiring repetition; this does not assert instrumented save comparisons or a scene-by-scene matrix.
- [x] Same-signature in-place reinstall passed on both devices without uninstall or data clearing. S4: all 155 original regular-file contents/metadata preserved before launch; index and all 100 records unchanged after launch; normal menu observed. S20: all 171 backed-up app-data files preserved byte-for-byte with metadata before launch, including index and all 85 records; only Android's backup manifest installer field changed. Its normal menu returned at level 6, 620 coins, and score 813,844. Android backup excludes some private-directory areas, and no complete post-launch byte comparison is claimed for S20. Both installed APK/native identities still match production.
- S20 repetition of the Penny/Holly/Pow purchase matrix is not required for this checkpoint, per operator decision. Retain the instrumented S4 purchase passes and accepted S20 functional results without labeling the specific S20 purchases as tested. Reopen only if concrete evidence implicates a device/Android-specific purchase, callback, or persistence problem; device difference alone is not a sufficient reason.
- [x] Reviewed closure results: no unresolved release-blocking defect established. Initial S20 backup failures were resolved by ordinary background-process termination without force-stop. Retain the non-blocking daily-bonus timing observation, one-time interrupted-start Heart adjustment, and limits on power-loss/device coverage explicitly.
- [x] Archived V42 as the stable pre-Christmas technical checkpoint: `checkpoints/2026-09-23-v42-stable-pre-christmas-766ecc422f81/`. The write-once archive contains the exact signed APK, native libraries, public certificate, 142 source-file snapshots, build provenance, qualification matrix/limitations, and device-specific rollback evidence. All 174 payload entries were hash-verified; archive, manifest, and checksums are read-only. Archive SHA-256: `7d165ab7fd3e785d1633b5983371fa5216466a04b1abd19e5253a4d3933e81e6`. Legal/publication and reproducible-build gates remain separate.
- [x] Implement the approved offline Christmas event from the frozen checkpoint, now active until both pets are claimed. Rudy: 100,000,000 score / 50 opened Mystery Boxes / 50,000 collected coins. Eve: 200,000,000 / 100 / 100,000. Shared cumulative counters, no reset on Rudy claim, no Friendship Point requirement.
- [x] Build a separate debug-signed V43 test APK; pass eight native event regressions and all nine existing index/token regressions after the interworking and mission-presentation updates.
- [x] Preserve a verified Galaxy S4 rollback backup and deploy the initial V43 artifact as a fresh installation. Both package-manager operations succeeded, and the pulled installed APK matched the test artifact exactly. Initial evidence: `device-snapshots/v43-fresh-install-20260923T023001Z/`.
- [x] Diagnose the first-game `SIGILL`, correct ARM/Thumb external-call bindings, and install the corrected debug-signed build in place. All 54 current app-data files retained their bytes and metadata; the app is stopped pending retest. Evidence: `device-snapshots/v43-first-game-crash-20260923T023920Z/`.
- [x] Capture Eve's small-text layout and install the matching-Rudy presentation: native styles, icons, separators, row order, and remaining/completed wording. Preserve all 54 current app-data files. The operator confirmed matching icons/text/font size and both pets' remaining requirements updating after each game.
- [x] Fresh-install a separate reduced-goal unlock-test build without backing up the replaced save, as requested. Rudy: 500,000 / 1 / 1,000; Eve: 1,000,000 / 2 / 2,000. Restore the existing 924,800-coin / 99,810-gem fixture; verify all 224 restored regular files, directory metadata, installed APK, and native libraries. Normal source goals and canonical APK remain unchanged.
- [x] Confirm Rudy's free claim, 29 upgrades, and equipped state from the valid journal; verify level-30 ownership/equipping and Eve's progress across cold restart. Operator visually confirmed those results and subsequently unlocked Eve.
- [x] Reproduce Eve's 497,282-hour clock-domain defect in actual ARM code and replace its timer with a persistent six-hour boot-time cooldown, first-gift migration, clock-change resistance, and conservative reboot handling. All 27 focused regressions and signed-APK native smoke pass.
- [x] Install the strict cooldown correction in place on the S4; verify installed APK and extracted libraries, preserve the previous APK/save backup, and confirm all 448 regular app-data files unchanged. Evidence: `device-snapshots/v43-eve-cooldown-20260924T041305Z/deployment-verification.json`.
- [x] Qualify Eve's first corrected reward on the S4: operator received two hearts, saw the six-hour cooldown begin, and confirmed no second claim. Runtime replies confirm hearts increasing from five to seven with one two-heart request and no captured fatal markers.
- [x] Accept operator-confirmed cooldown persistence across app/device restarts and resistance to a manual date change; record without repeating those checks.
- [x] Prepare gated `stress_eve_cooldown.py` and pass host CLI/native-oracle smoke. Physical attempts exposed and resolved KitKat parsing/export issues, but automated navigation did not complete. Retain the failed-run evidence; the operator prohibits further direct game UI interaction.
- [x] Recheck Eve's original selector through native payout construction: correct the swapped labels to 50% coins (200–500), 40% hearts (1–3), and 10% one gem. Two consecutive heart outcomes are nominally 16%; reward code is unchanged.
- [x] Complete six operator-controlled clock/lifecycle checks on S4: ±6-hour offsets, +1 day, future-date app restart, reboot then +365 days, and full shutdown then −365 days. Verify a 60.034-second disconnected hold and restore original clock/automatic settings. Evidence: `device-snapshots/eve-manual-clock-20260924T235029Z/manual-stress-summary.json`.
- [x] Accept operator-confirmed natural six-hour gift renewal, one available gift after waiting 12 or more hours (no stacking), and continued rewards after both pets are claimed and the Christmas event closes. This closes the outstanding functional expiry/payout check without repeating it. Evidence is manual observation, not an instrumented timing trace or completion of the original three-cycle automated campaign; keep all game UI operator-controlled.
- [x] End event activity only after both pets are owned, not merely mission-complete. Preserve catalog identity and Eve's cooldown; handle queued popups, stale banners, and inactive image cleanup. All 32 focused regressions and both signed-artifact native smokes pass.
- [x] Deploy the reduced-goal claim-completion APK in place on the S4, preserving the previous APK and readable save backup. Verify installed APK/native libraries, unchanged app UID, and exact contents/metadata of all 460 regular app-data files. Evidence: `device-snapshots/v43-claim-completion-20260925T003523Z/deployment-verification.json`.
- [x] Accept operator-confirmed event-entry closure on the claim-completion build; diagnose retained winter artwork without repeating the physical observation.
- [x] Reconcile seasonal artwork at inventory-ready main-menu and post-claim inventory transitions, retaining native geometry and V41's scene guard. Five pre-fix failing transition cases now pass; all 34 focused regressions and both signed-APK artwork/cooldown/goal-boundary checks pass.
- [x] Deploy the reduced-goal artwork correction in place on S4. Verify installed APK/native libraries, unchanged app UID, and exact contents/metadata of all 461 current regular files. Preserve the previous APK and readable full save archive. Evidence: `device-snapshots/v43-artwork-transition-20260925T010842Z/deployment-verification.json`.
- [x] Accept operator-confirmed return of ordinary artwork after event closure on the corrected S4 build, without repeating the physical check.
- [x] Fresh-install the same reduced-goal build on S20 without backing up its replaced installation, as explicitly requested. Verify APK/native hashes and the pre-unlock high-currency restore payload. Android reported restoration complete, but the subsequent splash-screen network error invalidates the earlier functional deployment pass.
- [x] Diagnose S20 restoration failure after explicit readiness: all 189 encrypted caches exist at expected sizes with mtimes divided by 1,000; actual native guard execution rejects the startup cache at its observed timestamp. Error 9001 also occurs in successful startup and is incidental. Evidence: `device-snapshots/v43-s20-fresh-20260925T012143Z/startup-error-9001/diagnosis.json`.
- [x] Repair the S20 save through a temporary manifest-only debug update: correct 213 mtimes, preserve all 225 current files byte-for-byte, and recover four missing profiles from the requested fixture. Verify all 229 resulting hashes/metadata and native acceptance of the repaired startup-cache timestamp. Reinstall the exact reduced APK, verify APK/native hashes, unchanged UID, disabled debugging, and 222 accessible post-update metadata entries. No save backup or integrity-check bypass. Evidence: `device-snapshots/v43-s20-fresh-20260925T012143Z/timestamp-repair/repair-verification.json`.
- [x] Accept operator-confirmed S20 startup recovery and Rudy unlock/upgrade after timestamp repair. The equip capture confirms level 2; the original pre-unlock wallet totals were not visually requalified, and subsequent legitimate gameplay changed them.
- [x] Diagnose and correct inherited inventory-ID narrowing without changing Christmas expiry: preserve string IDs in selection/update matching, retain existing IDs and save formats, and verify captured failure recovery plus large-ID upgrade isolation. All 39 focused regressions and both signed-APK replay checks pass.
- [x] Update S20 in place to the reduced inventory correction. Verify installed APK/native hashes, unchanged UID, disabled debugging, and metadata of 222 known private files. No backup, restore, or launch. Evidence: `device-snapshots/v43-s20-rudy-equip/correction-deployment.json`.
- [x] Diagnose the subsequent S20 startup regression from Android's recorded exception; describe the relocated ELF table with explicit `PT_PHDR`. New layout regression rejects the failed APK; all 40 focused host regressions and both corrected signed-APK selection replays pass. Shell-context Android loading passes header discovery but stops at legacy text-relocation memory protection, so this is not full startup qualification.
- [x] Install the rebuilt reduced APK from `inventory-id-fix/loader-corrected/reduced/` in place on S20. Verify installed APK/native hashes, unchanged UID, disabled debugging, and 222 known private-file metadata entries. No backup, restoration, or launch. Evidence: `device-snapshots/v43-s20-rudy-equip/loader-correction-deployment.json`.
- [x] Accept operator-confirmed S20 app-context startup, Rudy selection persistence, switching pets, gameplay with Rudy, and upgrade isolation on the corrected build. Eve was claimed successfully and the Christmas event disappeared immediately. Do not repeat these passed checks or the full V42 campaign for this patch. S4 remains on the prior artwork build.
- New equippable-pet acquisition is unavailable on the current save: Eve is not equippable and all other pets are unlocked. Record host purchase/equip/upgrade coverage without claiming a physical pass for that scenario; do not reset or restore the current save to manufacture it.

- [x] Build a separate revised normal-goal development candidate (Rudy 100,000,000 / 25 boxes / 25,000 coins; Eve 200,000,000 / 50 / 50,000) under `native-patches/v43-offline-christmas/normal-goals-25-50/`. All 40 focused regressions pass. Packaged native smoke verifies the goals, both-owned event closure, ordinary artwork after closure, and exact inventory-ID selection. The previously deployed S20 reduced-goal APK is unchanged.
- [x] Verify that the included inventory transaction-ID correction is pet-independent for the observed failure: signed-library ARM replay preserves a full-width selection ID for an ordinary pet on a second valid inventory and isolates another pet's upgrade. No independent array-index bounds guard or malformed-save protection is claimed.
- [x] Sign the revised normal-goal APK using the operator-supplied external FruitSpy key, without persisting passwords; verify the APK certificate equals frozen V42 and run strict pinned-public-certificate signature, ZIP, 1,140-payload, and packaged native-path checks. Signed APK SHA-256: `fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`.
- [x] Archive the newest FruitSpy-signed V43 normal-goal **technical** checkpoint at `checkpoints/2026-09-26-v43-normal-goals-fruitspy-fdc05ae28a20/`, without changing the frozen V42 checkpoint. All 22 archived members match their per-entry SHA-256/size inventory; archive ZIP integrity and external manifest checksums pass. The archived build report has its machine-local path sanitized. `checkpoint.zip` SHA-256: `b7c3dd0c46fc95eb65549179ebfbbbb498d765c55d6ce18995fec5fce957c02d`. The archive includes the signed APK, exact native libraries, authored sources, public certificate, and host evidence, but no private key/save. No device action was performed; the revised normal build remains physically unqualified.
- [x] Finish the operator-requested **fresh two-device installation without save preservation**. Both old packages/private app-data directories were removed without backups; the FruitSpy-signed normal APK is installed on both S4 and S20, with each installed APK SHA-256 matching the checkpoint. S20 initially hit Play Protect denial; a standard retry succeeded with the operator ready to respond, without changing security settings. No game launch yet. Evidence: `device-snapshots/v43-fruitspy-normal-goals-fresh-install/deployment.json`.
- [ ] Run operator-readiness-gated startup checks on the fresh normal-goal build on S20 and S4. Watch for successful main-menu rendering, Christmas event availability on a new save, ordinary gameplay, and severe app-process exceptions. Do not claim previous reduced-goal/older-artwork physical results qualify these new installations.

Public distribution/legal review, signing-key custody, packaging verification, and reproducible-build work remain separate from this technical checkpoint. No Android test or event modification is authorized by merely recording this plan; manual runs retain the readiness gate and save-protection protocol.

## V42 clean-original rebuild

- [x] Verify pristine APK provenance against the untouched Titanium APK archive.
- [x] Rebuild both native libraries from original bytes and authored patch/assembly sources without historical APK or patched-library inputs.
- [x] Reconstruct Java/resources and verify all 1,140 payload entries against the frozen V42 release; retain the sanitized seed as an explicit external input.
- [x] Regenerate exact manifest/signature-file/signed-attribute metadata and verify deterministic private-key signing with a disposable key; do not reuse the release signature block.
- [x] Complete original protected-key signature regeneration, strict JAR verification, and direct whole-APK byte comparison. The rebuilt signed APK at `native-patches/v42-clean-rebuild/verified-build/` exactly matches release SHA-256 `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`; `rebuild-verification.json` records the pass. No published signature block was reused.

## Public release material

- [x] Add repository inclusion/exclusion policy.
- [x] Add architecture, build, installation, validation, contribution, and legal documentation.
- [x] Preserve milestone patch sources, checkpoint notes, and aggregate V25 evidence.
- [x] Add GitHub validation workflow and local repository-policy checker.
- [ ] Add final patcher usage, checksum, troubleshooting, rollback, and provenance instructions after the build is reproducible.
- [x] Create, push, and verify the private GitHub remote.
