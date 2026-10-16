# Validation and test results

## Evidence policy

This repository publishes test definitions, aggregate results, hashes, and technical conclusions. Raw logcat captures, screenshots, app-data archives, decrypted profiles, and response-pool records remain local when collected because they can contain device-specific or user-state data.

Evidence types are stated per result. An operator-reported manual pass is an accepted empirical observation, not a claim of log analysis, save comparison, or automated verification. Historical instrumented results retain their original scope.
 
## V43 offline Christmas — host verified, device test pending

The development-signed test APK implements the [approved offline event and objectives](SEASONAL_PETS.md#v43-offline-implementation) on the exact frozen V42 base. The latest revision closes the event only after both pets are claimed.

- **32 focused host regressions pass:** eleven Eve cooldown cases, twelve native Christmas cases, and nine existing index/token cases. Actual patched ARM/Thumb code runs at a nonzero load bias with real PLT/GOT instructions and clock-syscall ABI; external engine/file services are supplied.
- Christmas coverage includes ownership-based activity without server/calendar dependence, mission completion before claims, either claim order, missing/restored inventory, closed-event popup/banner handling and image cleanup, exact goal boundaries, shared progress, pending/applied consistency, saturation, and rejection of Friendship Points.
- The initial throwaway UI-adapter smoke intercepted engine PLT entry points. It checked text/rectangle requests but masked an instruction-set transition bug; it did **not** qualify native interworking or the renderer. The replacement regression traverses the original ARM PLT instructions and resolved GOT slots before supplying external engine services.
- The relocated program-header table falls inside its file-backed load segment at the address selected by Android 4.4's `ElfReader::FindPhdr`/`CheckPhdr` rules. The original label/actor calling conventions were checked against the engine binary.
- The APK build verifies the debug signature and every unchanged payload. Only `libbirzzle.so` and 15 localization assets differ from V42; the V42 release/checkpoint remain unchanged.

**Fresh deployment passed on the Galaxy S4 / Android 4.4.2.** Before uninstalling, the installed V42 APK was preserved and matched the frozen release hash. The readable rollback archive retained 162 members, including 155 regular files whose complete contents were hashed; restoration was not exercised. Uninstall and fresh install both returned `Success`. Pulling the installed V43 APK confirmed exact equality with the debug-signed test artifact, SHA-256 `f154823fb14435f4a4344cd8367338088e5283ccfc9ac9d54006474985916c97`.

Immediately after that initial deployment, the package was `stopped=true`, `notLaunched=true`; no game launch or log capture had occurred yet. Initial evidence and rollback files are under `device-snapshots/v43-fresh-install-20260923T023001Z/`; `deployment-verification.json` and `rollback-verification.json` record those checks.

**Manual status:** event access, matching mission presentation/progress, both pet unlocks, Rudy's level-30/equipped persistence, and Eve's first payout/countdown are operator-confirmed. Six later operator-controlled clock/lifecycle checks passed on the S4, including cold app restart, reboot, and full shutdown under altered dates. Clock restoration and original automatic settings are verified. The subsequent latest-build operator report confirms natural six-hour gift renewal, only one available gift after waiting 12 or more hours, and continued rewards after both pets are claimed and the Christmas event disappears. This closes the outstanding functional expiry/payout check. These are accepted manual observations, not an instrumented timing trace; the original three-cycle UI-automated campaign did not complete. **All game UI must remain operator-controlled; do not restart automated taps/navigation.**

### Seasonal artwork reconciliation — host verified, reduced build deployed

The operator confirmed that the previous claimed-pet build removed the event entry but retained festive artwork. Native startup loads background/stage images before the owned inventory arrives; the inactive main-scene branch then skipped repainting. The existing `ReloadStageBG()` also hardcodes winter filenames, so calling it unchanged would not restore ordinary artwork.

The correction reconciles artwork when entering the inventory-ready main menu or post-claim pet inventory. It retains V41's scene-rearm hook, changes only background actors, selects ordinary stage/landscape side textures after closure, and removes winter overlays. The original native crop/tile geometry is shared between themes. Transient loaded-theme state uses existing event-manager padding; unchanged menu visits do not rebuild graphics. Ownership, mission profiles, and Eve's cooldown are unchanged.

All **34 focused regressions pass**. The two new artwork regressions produce five failing transition cases on the previous installed library and pass after the correction: cold owned-inventory startup in portrait and both landscape aspect branches, plus final claims in either order. Both signed APKs additionally pass **13 packaged-native checks and eight goal-boundary checks each**, including all 11 cooldown regressions. Cold-constructor initialization was exercised separately.

| Current artifact | SHA-256 |
|---|---|
| Normal goals; canonical V43 output, not deployed | `d3dd0452551a54ba2da4046c3b36a17c77d316c9cf22f34b68aa60a58e2d7f19` |
| Reduced goals; `artwork-transition-test/`, installed on S4 and S20 | `ca385c0b4879d6259462cd3b88c8e07c1f7630c6879def29e5833ea231d5b32a` |

Strict debug signatures and payload checks passed. `native-patches/v43-offline-christmas/artwork-transition-test/native-artwork-verification.json` records both signed builds. The native background selector and complete stage repaint execute at nonzero load bias, with inventory arrays, background actor construction, and external rendering/file/clock services supplied. This is **not physical rendering or wallet qualification**.

**In-place deployment passed on S4 (`4b53e568`).** A fresh stopped-app backup preserved the previous `beb8dc8a…` APK and readable full save archive before `adb install -r`. The pulled installed APK and both extracted native libraries match the new artifact. All **461 regular files / 468 archive members** were retained; regular-file bytes, modes, UID/GID, sizes, and mtimes are identical. Only the package-root mtime and installer-managed `lib` symlink target/mtime changed. App UID remains 10272; automatic clock settings are unchanged.

Evidence and rollback backup: `device-snapshots/v43-artwork-transition-20260925T010842Z/`, including `deployment-verification.json`. Backup SHA-256: `38147587f17888fb7011e7ae249fb8197bae32c6d8e12b7ba45fc337e48cef93`. No uninstall, data clearing, save restoration, game launch, UI interaction, or log capture occurred during deployment. The operator subsequently confirmed: **“The normal background now appears, as expected.”** This confirms the reported S4 artwork defect is resolved, without claiming a physical matrix of every orientation or claim order.

**S20 fresh installation and save repair verified; startup subsequently recovered (`R5CN305NZTW`, SM-G986U / Android 13).** At the operator's explicit instruction, the previous installation was uninstalled without any S20 backup. The same reduced-goal APK was freshly installed; on-device hashes of the APK and both native libraries match the verified artifact. New app UID: 10455.

The requested fixture is the post-Pow archive with SHA-256 `02c21163b53b32bdf1c80bc3deecaedececc7ebb667e022d1505ff60f589890a`: 924,800 coins, 99,810 gems, all six normal pets, and Rudy/Eve unowned. A debug-certificate-matched Android restore payload preserves all 223 transferable regular files byte-for-byte; only the device-specific GPU cache and installer-managed library symlink are excluded. The app root is created by Android.

`adb restore` finished with exit code 0, and the operator confirmed **Android reported successful restoration**. That report did not establish a usable save: the operator subsequently encountered a network error at the splash screen followed by closure after dismissing it. The initial deployment was incorrectly marked passed without verifying restored timestamps. Evidence: `device-snapshots/v43-s20-fresh-20260925T012143Z/deployment-verification.json`.

After explicit readiness, a clean, app-scoped startup capture reproduced the reported failure. No Java/native fatal marker or normal `SERVER.INIT` response was captured. Error 9001 originates from Facebook's disconnected-profile callback and also appears before successful initialization in the earlier S20 log; it is not the root-cause signal.

**Restore timestamp corruption is confirmed directly on the S20.** Although private file hashing is denied, `stat` can read metadata: all **189 encrypted cache files** exist with fixture-matching sizes, but every mtime is the original Unix-seconds timestamp divided by 1,000. The `SERVER.INIT` cache has mtime **1462100**, not **1462100890**. Android 13's tar reader passes the seconds value through to `FullBackup.restoreFile()`, which calls Java's millisecond-based `File.setLastModified()`. Execution of the installed native timestamp guard accepts the fixture time and rejects the observed restored time.

No installation/save changes or backups were made during diagnosis. App-scoped logs, observed metadata, source references, and native execution proof are recorded under `device-snapshots/v43-s20-fresh-20260925T012143Z/startup-error-9001/`. Android's completion screen alone is not save verification.

**Authorized repair completed without a save backup or native-code changes.** A same-signature temporary update changed only the binary manifest to enable app-UID access. All 189 encrypted cache files were byte-identical to the requested fixture. The repair corrected **213 corrupted mtimes**, preserved the contents of all **225 currently present files**, and recovered four missing local profiles (`bMarket.dat`, `bonusgame.dat_…`, `classic_stage_save.dat`, and `exp.dat`) from that same fixture. The current, rewritten `new2profile.dat` was not replaced. Hashes and metadata of all **229 resulting files** were verified; existing ownership, modes, and sizes were preserved. Execution of the unchanged native timestamp guard accepts the repaired startup-cache timestamp.

The exact reduced-goal APK was then reinstalled in place: APK and both native hashes match, UID remains 10455, `DEBUGGABLE` is absent, and `run-as` is rejected again. Direct metadata checks after that update confirmed **222 files** unchanged; seven WebView files were inaccessible after debugging was disabled. Private contents were hashed before the final update, not after it. Evidence: `device-snapshots/v43-s20-fresh-20260925T012143Z/timestamp-repair/repair-verification.json`. The operator subsequently reached gameplay, unlocked Rudy, and upgraded him; the later capture confirms Rudy at level 2. This establishes recovered startup, not a fresh visual check of the original wallet totals. Do not reuse the faulty `.ab` timestamp path or weaken the native integrity guard.

### Inventory transaction-ID correction — S20 focused checks passed

The gated capture records `inventory.use` requesting Rudy's ID `2147486133`, followed by a successful response with the selected marker changed to `2147483647`. Native `calcInventory()` reads the request through `GetInt()`/ARM32 `atoi` and writes the selected marker through `UpdateInt()`. The original purchase path generates IDs from the **64-bit server-adjusted clock**, formatted with `%lld`; the narrower consumer is inconsistent with that producer. The exact historical clock adjustments that produced this value were not recovered. Device-libc execution confirms saturation, and original `CPetManager::UsePet()` returns null for the truncated marker but Rudy for the complete ID. The event remains active in both cases. The defective engine is byte-identical to frozen V42.

`v43_inventory.c` and its assembly entry bridges preserve the full string for selection and compare exact IDs in the shared inventory-update path. No saved ID regeneration, save migration, clock changes, event rollback, or integrity bypass is involved. Existing journal replay can recover a truncated selected marker from the original full-ID requests. Five regressions execute the real ARM reducer with its unchanged JSON/STL service boundaries supplied; old-code controls reproduce both empty selection and an upgrade targeting the wrong large-ID pet. The first corrected APK passed these host checks but **crashed at startup on S20**, before inventory execution: Android's DropBox records `UnsatisfiedLinkError: loaded phdr ... not in loadable segment`. The relocated engine program-header table lacked an explicit `PT_PHDR`; Android's fallback computed the wrong mapped address.

The builder now emits `PT_PHDR` with the actual table mapping. A sixth inventory-suite regression rejects the failed layout and accepts the corrected packaged libraries; **all 40 focused regressions pass**, as do exact Rudy selection replays from both newly signed APKs. Strict signatures pass; only `libef2d.so` differs from the previous artwork APK. Evidence: `native-patches/v43-offline-christmas/inventory-id-fix/loader-corrected/native-verification.json`. Actual S20 standalone loader probes advance past the header rejection, but full `dlopen` stops at legacy text-relocation memory protection (`Permission denied`) in shell context. This is **not a full app-startup pass**; no Android security policy was changed.

The rebuilt reduced APK was installed **only on S20**, in place without backup, restoration, or game launch during deployment. APK SHA-256: `3f7d144e342438d49110e219854939d946c7d17d5d9fbce29520a8524a3a3c5e`. Installed APK/native hashes match, UID remains 10455, debugging remains disabled, and metadata of **222 known private files** was unchanged across this update. Complete private content hashes were not accessible. Deployment evidence: `device-snapshots/v43-s20-rudy-equip/loader-correction-deployment.json`; the previous deployment report remains historical evidence for the failed build. S4 remains on its previously qualified artwork build.

**Subsequent operator-confirmed S20 qualification passed:** Rudy is selectable; selection persists through menu transitions and app relaunch; switching between ordinary pets and Rudy works; gameplay with Rudy completes normally; and the upgrade-isolation check passes. These physical results establish recovered app-context startup despite the standalone shell probe's limitation. The operator also successfully claimed Eve and observed the Christmas event disappear immediately. These results are accepted without repeating the checks.

**Eve cooldown qualification subsequently passed by operator report:** a new gift becomes available every six hours; waiting 12 or more hours still yields only one gift, rather than accumulated gifts; and rewards continue after both pets have been claimed and the Christmas event has disappeared. Natural renewal, non-stacking, and post-event reward availability are accepted without repeating the tests. This report does not claim instrumented timing or new wallet-delta traces.

**Remaining acquisition coverage limit:** Eve is not equippable, and all other pets are already unlocked on this save. Her successful claim verifies that claim and event closure, not acquisition followed by equipping a newly owned pet. That additional physical scenario is unavailable on the current save, not a failed check or a blocker to the focused S20 qualification; purchase/equip/upgrade with a full-width ID remains covered by the native host regression. Do not reset or restore the current save to manufacture another acquisition. A full V42 retest is not required for this inventory-ID patch; unrelated outstanding V43 qualification remains separate.

### Revised normal goals — FruitSpy-signed technical checkpoint

The FruitSpy-signed normal-goal APK (`fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`) embeds Rudy's 100,000,000 score / 25 opened boxes / 25,000 collected coins and Eve's 200,000,000 / 50 / 50,000. Its public signing certificate matches frozen V42; strict signature and payload checks pass. Forty focused regressions pass. Executing the packaged signed native libraries at a nonzero ARM load bias verified event closure only after both claims (either order), ordinary Christmas-background restoration after closure, valid engine program headers, and exact Rudy equip selection. A second valid inventory shape verified full-width transaction-ID selection on an ordinary pet and upgrade isolation on another. The fix compares opaque IDs independent of pet type; it is **not** a general bounds guard for unrelated malformed inventories or a separate pet array-index failure.

At checkpoint creation, the normal-goal APK had not been installed or physically qualified. The operator subsequently authorized **fresh installs without preserving saves**: both older packages were uninstalled without `-k`, with private app-data directories confirmed absent afterward. Both S4 and S20 then installed the FruitSpy-signed APK; their installed APK hashes match the checkpoint, and new private app-data directories were created. S20 initially returned `INSTALL_FAILED_VERIFICATION_FAILURE` twice with a Play Protect dialog focused; a standard non-streaming retry succeeded with the operator ready to respond. No security setting was changed or game launched. Evidence: `device-snapshots/v43-fruitspy-normal-goals-fresh-install/deployment.json`. Manual startup checks remain pending on both devices; do not repeat already accepted historical operator checks merely because this checkpoint was signed.

Checkpoint archive: `checkpoints/2026-09-26-v43-normal-goals-fruitspy-fdc05ae28a20/checkpoint.zip`, SHA-256 `b7c3dd0c46fc95eb65549179ebfbbbb498d765c55d6ce18995fec5fce957c02d`. Its 22 member hashes/sizes, ZIP integrity, public certificate, and signed APK are verified; machine-local paths were removed from archived textual evidence. The frozen V42 checkpoint is unchanged; no device saves were included in the archive, and the later operator-requested uninstalls intentionally removed the old installed saves. Archive checks establish artifact integrity and scoped native behavior, not a physical-device startup pass for the new normal-goal build.

### Claimed-pet event closure — previous deployment

`IsEventInProgress()` now checks the original inventory ownership API for Rudy and Eve rather than returning a constant true. Mission completion alone does not close the event. The catalog retains both event-pet types so ownership, claim routing, and ordinary pet behavior are not reclassified. The getter writes no save data.

The original successful claim completion posts message 10160; its existing handler hides the event dialog and prepares pet inventory after Eve's unlock initialization. That order is unchanged. Queued opens of a completed event now use the dialog's normal hide path. Banner show requests after closure use the original banner hide body instead of returning with stale visible actors. Event-image cleanup no longer depends on event activity.

Both signed artifacts passed native smoke covering ownership states, the original `SetMyPetData` roster-filter block retaining both owned pets byte-identically, popup suppression, the actual native banner-hide body, inactive image teardown, preserved encrypted cooldown data, a future gift handoff after expiry, and cooldown resumption with both pets owned:

| Artifact | SHA-256 |
|---|---|
| Previous normal-goal claim-completion artifact | `f0f926ecc40ccd790e48bfd424b6374131801fe6618eec2d88a2a8d117282eb8` |
| Matching reduced goals; `claim-completion-test/` | `beb8dc8a46b685e20808db93a3f4e1015371a15aea551fca4f9824fdb1197b2d` |

Historical `claim-completion-smoke.json` files record this earlier revision. Strict debug-signature and unchanged-payload checks passed. The smoke supplies external engine/file services, the original dialog-rendering boundary, and the unchanged payout handoff; it is **not physical rendering or wallet qualification**. The operator subsequently confirmed event-entry closure but reported retained winter artwork, addressed by the revision above.

**In-place deployment passed on S4 (`4b53e568`).** After stopping the app for a consistent snapshot, the previous installed cooldown APK (`29929b466b5cb33d9eff463a85b19c67924e116591c45ec8e579272e20bcc719`) and a readable full data archive were preserved. `adb install -r` installed the reduced-goal claim-completion APK (`beb8dc8a46b685e20808db93a3f4e1015371a15aea551fca4f9824fdb1197b2d`) successfully. The pulled installed APK and both extracted native libraries match the requested artifact.

All **460 regular app-data files** retained their exact bytes, modes, UID/GID, sizes, and mtimes; no archive members were added or removed. App UID remained 10272. Only the package-root mtime and installer-managed `lib` symlink target/mtime changed. No uninstall, data clearing, save restoration, game launch, or log capture occurred during this earlier deployment; the game was left stopped for the operator.

Deployment evidence and previous APK/save backup: `device-snapshots/v43-claim-completion-20260925T003523Z/`; result: `deployment-verification.json`. Backup SHA-256: `5006e950a3f338937296ab5e28ad0ef4eb4601c25d8d27f75b875bf5d28a98bf`. The normal-goal artifact remains undeployed.

### First-game crash and ARM/Thumb correction

The operator reported a crash after the first game while returning to the main menu. The app-scoped native trace records `SIGILL` on the event UI path: the new helper's call at `libbirzzle.so:0x2c826a` used Thumb `BL` to the ARM `ACTOR_FindWithID` PLT entry at `0x732d4`. Execution stayed in Thumb state and faulted at `0x73d20`.

Root cause: linker `--defsym` bindings were `STT_NOTYPE`; LLD did not generate ARM interworking calls. The builder now supplies typed absolute function symbols in a generated object: `.set` for ARM and `.thumb_set` for Thumb. This produces the required `BLX` calls without changing the event goals, save format, or abilities.

The new native UI regression failed before the fix with `UC_ERR_INSN_INVALID` and passes after it, traversing the real ARM PLT/GOT path. All 16 focused tests pass. A separate smoke of the signed APK's actual library rendered partial and completed objective text through those same real trampolines. Neither check executes the original renderer.

The corrected debug-signed APK has SHA-256 `7dd5c25b93ac1dcc017651ada354ca0a756425aab9ffda4983a76da7583a2f6b`. It was installed on the S4 with `adb install -r`, without uninstalling or clearing data. The pulled installed APK matches exactly. All **54 regular app-data files** retained their contents, ownership, modes, sizes, and mtimes across the update. The failed save and crashing APK were preserved first; canonical build outputs now contain the corrected artifact.

Local evidence: `device-snapshots/v43-first-game-crash-20260923T023920Z/`, including `diagnosis.json`, failed/before/after save archives, and `corrected-deployment.json`. The scoped trace was also written to `.omp/current_test_log.txt`. Temporary device archives and the host linker probe were removed. That update was left stopped for the readiness-gated retest.

### Eve mission presentation parity

After confirming readiness, the operator reported reaching the main menu and automatic event popup with correct objectives. The requested screenshot, `device-snapshots/v43-eve-ui-20260923T025544Z/event-before.png`, confirms the event screen and the small, two-line Eve counters. This establishes startup/event access after the interworking correction, not an independently reported repeat of the entire game-to-menu test.

The new presentation copies Rudy's native heading, icons, separators, and label styles into Eve's existing actor IDs once per dialog image load. Both columns use Mystery Boxes / score / coins order and localized remaining-goal text. The original comma formatter is reused. The obsolete bar animation is replaced by the original pending-progress apply/save routine, so it cannot resize the reused row actors.

All 17 host regressions pass, including remaining amounts through real ARM PLT/GOT calls and completion after committing pending progress. A signed-library smoke checked the captured progress's expected Eve rows (`100 times left`, `199,893,170 points left`, `99,980 Coins left`), translated row geometry, close/reopen behavior without recreating actors, and completed rows. External engine services were supplied; this is **not a screenshot of the updated renderer**.

The debug-signed revision, SHA-256 `cb624ec40400743417c47e7b3d3199beeacdfecf23293e37597cb5027ad1a307`, was installed in place and pulled back for exact byte comparison. All 54 regular app-data files retained their contents and metadata. The previous APK, screenshot, before/after backups, native smoke, and deployment report remain under the same evidence directory. The operator subsequently confirmed matching mission icons, text strings, and font size for both pets, with each pet's remaining requirements updating after every game.

### Reduced-goal unlock-flow test

At the operator's request, a separate test-only APK was built under `native-patches/v43-offline-christmas/unlock-test/`, with Rudy requiring **500,000 score / 1 opened Mystery Box / 1,000 collected coins**, and Eve **1,000,000 / 2 / 2,000**. The builder's goals were overridden only in memory for this build; normal source defaults and the canonical normal-goal APK remain unchanged.

The signed test APK has SHA-256 `622d9bc6d9ee4ef084eff2e1727891439662d0fca4cebb5bd6b10aef92cefd25`. Its actual native code passed exact-boundary, one-below-each-objective, shared-progress, apply/save-boundary, and remaining/completed-text smoke checks. This does not qualify physical claims.

Fresh uninstall/install succeeded on the S4 **without backing up the replaced save**, as explicitly authorized. The existing post-Pow high-currency fixture was restored: 924,800 coins, 99,810 gems, all six normal pets owned, and Rudy/Eve unowned. All **224 restored regular files** matched the fixture's bytes, modes, sizes, and mtimes, with ownership remapped to the fresh app UID; five directories' metadata was also verified. The fresh installer library symlink was preserved. The installed APK and both native libraries matched the test artifact. No event mission profile exists, so event progress starts fresh.

Initial evidence: `device-snapshots/v43-unlock-test-20260924T010409Z/deployment-verification.json`; host smoke: `native-patches/v43-offline-christmas/unlock-test/native-smoke.json`. At deployment the package was `stopped=true`, `notLaunched=true`; subsequent operator-authorized testing followed.

### Rudy restart and Eve reward-timer correction

The persisted journal confirms Rudy's free claim at record 244, a zero-currency `BuyPet` pocket update at 245, all 29 upgrades to level 30, and equipping. A cold restart returned Rudy owned at ability 30 and equipped, Eve unowned, all six prior normal pets, 863,629 coins, 99,796 gems, and 5,300 XP. All 316 records and their index remained byte-identical and valid. Event totals remained 1,000,000 score / 1 box / 1,449 coins; the event profile was re-saved with a new timestamp without changing those counters. Evidence: `device-snapshots/v43-rudy-restart-20260924T015251Z/restart-verification.json`. Pre-restart logcat no longer contained the claim/upgrade messages; journal and post-restart runtime replies supplied that evidence. The operator subsequently confirmed the same state visually and unlocked Eve.

Eve then displayed over 497,282 hours until a reward. The native unlock callback at `0x168294` used wall time minus 60; the getter at `0x11143c` subtracted offline Hangame time. Executing the original instructions with deadline 1,790,215,200 and offline time zero reproduced exactly 497,282 hours.

The fix uses a persistent six-hour `CLOCK_BOOTTIME` cooldown and boot UUID, with conservative reboot handling and one-time legacy profile migration. See [cooldown semantics and limitations](SEASONAL_PETS.md#eve-reward-cooldown). Ten native regressions cover first/repeated gifts, exact expiry, app restart/suspend, forward/backward calendar/server changes, phone reboot, legacy migration, corruption, short encrypted writes, unavailable clock/boot identity, and exclusion of unowned/ordinary pets. All 27 focused tests pass.

Both new artifacts passed strict debug-signature and unchanged-payload verification:

- Normal-goal APK: SHA-256 `1bb0ec189c864938cb06ecfe971fcb821135aff48b4d31231116591d8eecce9b`.
- Reduced-goal APK in `native-patches/v43-offline-christmas/cooldown-test/`: SHA-256 `29929b466b5cb33d9eff463a85b19c67924e116591c45ec8e579272e20bcc719`. Its signed-library smoke migrated the broken first gift to due, reset to 21,600 seconds after claim handoff, retained 18,000 seconds after an hour closed, allowed the next gift at expiry, and blocked immediate duplicates and clock-based acceleration. Evidence: `native-smoke.json` in that directory.

The smoke supplies external filesystem and unchanged payout boundaries; it does **not** verify the on-device renderer or actual wallet reward. No device save was changed during the implementation phase.

The operator subsequently authorized deployment of the created strict boot-time fix, without implementing the discussed hybrid alternative. `adb install -r` succeeded on the S4 (`4b53e568`). The pulled installed APK matched SHA-256 `29929b466b5cb33d9eff463a85b19c67924e116591c45ec8e579272e20bcc719`; both extracted native libraries matched the APK. Before installation, the previous APK and a readable full app-data archive were preserved. All **448 regular files** retained their exact bytes, modes, UID/GID, sizes, and mtimes. The only other changes were the package-root directory mtime and installer-managed native-library symlink/mtime. App UID remained 10272. No uninstall, save restoration, launch, or log capture occurred; the package is `stopped=true`. Evidence: `device-snapshots/v43-eve-cooldown-20260924T041305Z/deployment-verification.json`. Physical reward qualification awaits the manual readiness gate.

The operator then confirmed readiness; the required buffer-clear/launcher sequence succeeded. Android 4.4's absent crash buffer emitted its expected warning. Scoped capture recorded process 2375 and was stopped after the operator reported a successful **two-heart** gift, a **six-hour countdown**, and no second claim. Runtime evidence contains one `pocket.set` request with `heart=2`, `gem=0`, and `coin=0`; successful wallet replies show **5 → 7 hearts**. No fatal exception/signal markers were present in the captured log. Evidence: `eve-first-gift-verification.json` and `eve-first-gift-log.txt` in the same deployment directory. This qualifies the first physical payout, countdown initialization, and immediate duplicate-claim exclusion—not app-restart persistence, calendar changes, phone reboot, or real six-hour expiry.

Subsequent operator results: cooldown survived app restart and device restart and did not advance after a manual date change. Two consecutive heart rewards were reported; the second amount and exact interval were not specified. Evidence: `eve-restart-date-operator-report.json` in the same deployment directory. The reward recheck corrected the prior heart/gem label swap: 50% coins (200–500), 40% hearts (1–3), 10% one gem. See [Eve's corrected reward table](SEASONAL_PETS.md#eve).

### Prepared Eve clock and power stress runner

`stress_eve_cooldown.py` passed host preparation, but its physical UI-automated campaign did not complete. Initial attempts exposed KitKat response framing and root-command export issues; both were corrected and exercised on-device. Calibration reached Eve's blocked-gift notice, but PTY multiline input was concatenated, and the subsequent replay failed to establish a fresh checkpoint. The failed run restored the clock and settings. The operator then prohibited further direct game UI interaction. **Do not run `--calibrate` or `--run` under that instruction.** Plan-only invocation remains non-mutating:

```powershell
python stress_eve_cooldown.py
```

The original calibration/run modes print the exact readiness gate before contacting the phone, but readiness alone does not override the operator-only UI requirement. Their retained implementation records bounded tap/swipe/wait actions and requires a fresh checkpoint after relaunch; the descriptions below document that attempted runner, not completed physical coverage. The later successful checks used ADB clock changes/read-only measurements with every game UI action performed by the operator.

Default campaign: three cycles of forward/backward **one-minute, one-hour, six-hour, one-day, and one-year** calendar changes, probing both a running app and cold app startup; **three device reboots**; and **one full graceful shutdown with a 60-second off hold**. It also changes the calendar after boot but before the game's first new-boot initialization. Full shutdown requires the operator to confirm Android is off, leave it off for the measured hold, then physically power on/unlock. ADB cannot power on a fully shut-down S4; disconnection alone is not treated as shutdown proof. No external power controller is assumed.

Safeguards and acceptance:

- Require the exact installed debug APK, explicit target serial, root, Android 4.4, and at least one hour of existing cooldown. Preserve and read/hash a quiesced full save backup before clock changes. Never install, edit/restore app data, shorten the interval, or reset eligibility.
- Decode the actual encrypted EVE1 checkpoint, verify its checksum/bounds, and compare boot UUID plus deadline. Same-boot calendar/app restarts must preserve `sampled + remaining`; a new boot must resume the exact saved remainder. A fresh native write is required after relaunch. Navigation must expose the first new-boot checkpoint before it is superseded by a minute checkpoint; otherwise the runner fails rather than inferring success.
- Require an active cooldown before each UI action and abort below three minutes remaining, before a legitimate reward can become due. Unexpected currency/heart mutations or scoped fatal logs fail the run. Save per-case screenshots, encrypted timer snapshots, observations, scoped logs, and `results.json`; latest scoped log goes to `.omp/current_test_log.txt`.
- Persist `clock-recovery.json` before disabling automatic time/time-zone. Restore the original device-calendar offset relative to elapsed host time and original automatic settings in `finally`, and force-stop the game. Keep the host clock stable. If interrupted/disconnected and restoration cannot complete, the run fails and prints the explicit `--restore ... --serial ...` recovery command. Full app-data restoration is never automatic.
- Clock changes affect the whole phone, including alarms, certificates, and other apps. Use the dedicated test device. Graceful shutdown does not qualify sudden battery removal, power-cut/write-tearing, or actual six-hour expiry.

Host preparation proof: the actual CLI printed its plan with a deliberately nonexistent ADB path; actual signed-APK ARM execution passed the runner's oracle across **160 calendar changes, 40 app restarts, and 16 changed-boot transitions**, and three deliberately shifted deadlines were rejected. External services and boot changes were supplied in Unicorn; this is **not physical stress evidence**. Artifact: `native-patches/v43-offline-christmas/cooldown-test/stress-runner-smoke.json`. The KitKat numeric clock command follows [AOSP toolbox/date.c](https://android.googlesource.com/platform/system/core/+/android-4.4.2_r2/toolbox/date.c); the runner reads the device clock back after setting it.

### Completed operator-controlled clock and power checks

Evidence: `device-snapshots/eve-manual-clock-20260924T235029Z/manual-stress-summary.json`, with per-case observations, kernel boot IDs, encrypted timer snapshots, and restoration records beside it. Baseline display: **3h44m**.

| Case | Operator-reported display | Result |
|---|---|---|
| Six hours ahead of original timeline | 3h39m | Passed |
| Six hours behind original timeline; twelve-hour reversal from previous case | 3h37m | Passed |
| One day ahead | 3h36m | Passed |
| Operator force-stop/relaunch with future date retained | 3h34m | Passed; new PID observed |
| Phone reboot, then +365 days before first game initialization | 3h32m | Passed; new boot UUID and closed game verified before clock change |
| Full shutdown, then −365 days before first game initialization | 3h31m | Passed; new boot UUID and closed game verified before clock change |

The operator confirmed full shutdown. A read-only monitor then observed ADB absence across **31 samples over 60.034 seconds** before manual power-on. ADB absence alone is not electrical power-off proof; the physical shutdown observation is operator-supplied. The pre-launch persisted remainders were 12,774 seconds after the reboot and 12,686 seconds after full shutdown; the reported rounded displays match conservative resumption, not a fresh six-hour period.

Original clock progression was restored and read back within two seconds of its host-anchored expected value. `auto_time=1` and `auto_time_zone=1` were restored/verified. Restoration issued no game UI action, force-stop, restart, or launch. `clock-recovery.json` is marked `restored=true`; `clock-restoration.json` records the device readings.

These six checks establish observed countdown resistance/persistence, not the originally proposed repeated three-cycle campaign. No new payout, exact real-time expiry boundary, battery-removal/write-tearing, full-save byte comparison, or manual-phase wallet/crash-log qualification is claimed. No APK or game-code changes were made during the physical campaign.

Runner compatibility fixes: parse nonempty KitKat records separately from retained `WARNING: linker:` diagnostics; use that parser for package paths, boot-clock readings, and automatic-time settings. Export a profile with separate rooted `cp` and `chmod` invocations—the legacy shell did not keep the compound command's second operation rooted. Real package/clock/settings reads, readable backups/profile exports, and subsequent clock restoration exercised those corrected paths.

## V42 manual release-test results

On 2026-09-20, the operator reported the following tests **passed on both devices**:

| Test | Galaxy S4 — Android 4.4.2 | Galaxy S20 Plus — Android 13 |
|---|---|---|
| Fresh APK-only initialization | Passed — manual report | Passed — manual report |
| Fresh-player progression | Passed — manual report | Passed — manual report |
| Offline gameplay session | Passed — manual report | Passed — manual report |
| Connected gameplay session | Passed — manual report | Passed — manual report |
| Rewards and mutations | Passed — manual report | Passed — manual report |
| Leaderboard | Passed — manual report | Passed — manual report |
| Unlimited-life behavior | Passed — manual report | Passed — manual report |
| Mature-save cold starts | Passed — manual report | Passed — manual report |

The operator observed no progress loss, crashes, freezes, or softlocks on either device. These tests were intentionally empirical to save time: **no logs or save-file backups were collected for these runs**. Exact action counts, duration, and installed-device APK hashes were not recorded here; do not infer the repetition counts or checkpoint guarantees of an older scripted protocol.

The V42 release artifact reference is SHA-256 `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`. This identifies the produced APK, not an independently captured hash from either empirical run.

### Unlimited hearts

The current patch prevents the displayed lives counter from decreasing. Zero lives are therefore never displayed during ordinary play. The reported unlimited-life pass covers continued play with the non-decreasing counter; a requirement to start games from a displayed zero is **not applicable to this implementation**, not a failed or omitted test.

### Acceptance scope and residual risk

All eight named functional checks are accepted as passed on both reported environments. There is no retrospective claim of clean logs, byte-identical saves, measured token lengths, or corruption/interrupted-write coverage for these empirical sessions. The operator accepts that undiscovered issues may remain and will review them as users report them.

These results are separate from the earlier instrumented V42 Galaxy S4 token/recovery regression, which retains its own logs, snapshots, and verification report in [INDEX_DIAGNOSTICS_AND_RECOVERY.md](../INDEX_DIAGNOSTICS_AND_RECOVERY.md). They do not create new evidence for unreported destructive fault tests, a separately defined inspection-only final restart, or unrelated legal/build/publication gates.

### Additional two-device lifecycle closure

The operator subsequently reported these empirical passes on both the Galaxy S4 and Galaxy S20 Plus:

| Scenario | S4 | S20 Plus | Reported behavior |
|---|---|---|---|
| Leave the running game in the background, then return | Passed | Passed | Game pauses itself gracefully; no progress loss observed |
| Lock the screen while the game is running, then return | Passed | Passed | Game pauses itself gracefully; no progress loss observed |
| Full device reboot, then launch | Passed | Passed | Saved progress loads correctly |

These observations close the lifecycle/reboot item in the final V42 checkpoint plan. No repeat is required to confirm the operator's report. They do not establish exact durations, iteration counts, individual scene coverage, installed APK hashes, or byte-identical save comparisons; no instrumented evidence was supplied with this report. Installed-artifact identification and same-signature in-place reinstall preservation remain separate closure items.

The operator excludes repeating the Penny/Holly/Pow purchase matrix on S20 unless concrete evidence indicates a device-specific risk. No such failure has been established in the recorded results. The instrumented S4 purchase passes and accepted S20 functional coverage remain the release evidence; the specific three-pet sequence is not claimed as tested on S20. A purchase/callback/persistence failure linked to the S20 or its Android environment would reopen that targeted check.

### Installed-artifact and in-place reinstall closure

The operator authorized both tests with both devices connected and ready. Both installed APKs were pulled and matched release SHA-256 `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`. Both packaged native libraries and the extracted installed libraries matched production on S4 and S20. This establishes installed-artifact identity independently of the earlier empirical reports.

**S4 reinstall passed.** A fresh, readable app-data backup had a consistent 100-record pool at `-1,99`. The exact release APK was installed with `adb install -r`, without uninstalling or clearing data. Before launch, all 155 original regular files retained their bytes and metadata, with no added or removed archive members. Only the app-root directory mtime and the package-manager `lib` symlink metadata/target changed; the installed APK/libraries still matched production.

After launch, the index and all 100 request records remained identical. The ranking response completed, and no fatal marker was found in the captured app-scoped log. A settled screenshot showed the normal menu at level 6, 2,910 coins, zero gems, five Hearts, and `My Score` 692,750, without a first-run tutorial. Fourteen other files changed during startup, so complete post-launch archive byte identity is not claimed. The initial log-state comparison had an empty pre-launch response baseline and was retained as inconclusive, not a game regression.

**S20 reinstall passed.** The device has no `su`, and `run-as` rejects this non-debuggable package. Initial backup attempts were unusable: zero bytes, a full-agent binding timeout, and a force-stopped package rejected as ineligible. After the operator opened/backgrounded the game, ordinary `am kill` terminated its process while preserving `stopped=false`. The resulting readable backup contained a consistent 85-record pool at `-1,84`, with no semantic warnings. The exact release APK was installed with `adb install -r`, which returned `Success`; the pulled installed APK and both extracted native-library hashes still match production. No uninstall, data clearing, or restore was performed.

A second user-confirmed backup, captured before normal launch, preserved all 171 backed-up app-data files byte-for-byte with metadata: 127 files-domain entries, six shared-preference entries, four database entries, and 34 root-domain entries. No archive member was added or removed. Only Android's `_manifest` changed: its installer-package field became empty after the ADB reinstall. The index and all 85 request records were identical. A subsequent screenshot showed the normal menu at level 6 (37%), 620 coins, zero gems, five Hearts, and score 813,844, without a first-run tutorial. No fatal marker appeared in the captured current-app-process log. This is an Android-backup-scope comparison before launch, not a complete private-directory or post-launch byte-identity claim; restore was not exercised.

Local evidence: `device-snapshots/v42-two-device-release-closure-20260922T234302Z/closure-status.json`, `identity-verification.json`, and the per-device archives, comparisons, filtered logs, and screenshots. Both focused closure items passed; the stable pre-Christmas checkpoint below is now declared.

### Stable pre-Christmas checkpoint

On 2026-09-23, V42 was frozen as `2026-09-23-v42-stable-pre-christmas-766ecc422f81`. The local archive is [checkpoint.zip](../checkpoints/2026-09-23-v42-stable-pre-christmas-766ecc422f81/checkpoint.zip), with [manifest.json](../checkpoints/2026-09-23-v42-stable-pre-christmas-766ecc422f81/manifest.json) and `SHA256SUMS.txt` beside it.

- Archive SHA-256: `7d165ab7fd3e785d1633b5983371fa5216466a04b1abd19e5253a4d3933e81e6`.
- All 174 payload entries were reread and verified against their recorded hashes and sizes. The uniquely created archive, manifest, and checksum file have read-only attributes; this is not hardware-enforced immutable storage.
- Preserved: exact release APK and native libraries, public certificate, exact V41 input APK, 142 current source files, historical build/signing evidence, qualification matrix, known limitations, and device-specific pre-reinstall rollback archives.
- The bundle is **local-only**: it includes proprietary binaries and personal device evidence. It contains no private signing key. Backups were validated as readable; restoration was not exercised in this closure.
- This is a stable technical base, not legal/distribution approval or a reproducible clean-clone build. Existing daily-bonus, one-time interrupted-start Heart adjustment, and device/power-loss coverage limitations remain explicit.

The offline Christmas patch starts from this exact release. The operator subsequently approved the permanent event and both sets of objectives recorded in the V43 section above. No event modification is included in the frozen checkpoint.

### Clean-original V42 rebuild verification

The original APK matched the untouched Titanium APK archive at SHA-256 `9bdfd11afd542265dbbc228a0205336806a77e59c739cbefd2b6f22e8741088c`. Fresh-workspace builds using `rebuild_v42.py` regenerated both native libraries from original bytes and authored assembly/patch scripts, rebuilt Java and resources from a clean decode, and included the separately supplied sanitized seed. All **1,140 non-signature entries** matched the qualified V42 release byte-for-byte; there were no missing, extra, or changed payloads. No historical APK or prebuilt patched library was an input.

The release manifest, signature file, and signed-attribute DER were also regenerated to their exact published hashes, without copying those bytes from V42. A disposable private-key smoke run proved deterministic repeated RSA signing, rejection of the wrong pinned certificate, successful OpenSSL CMS verification, and strict JAR verification against its public certificate. Its generated APK reproduced every application payload's compressed bytes and ZIP entry metadata, plus both manifest/signature-file compressed streams. Credentials were absent from command logs, and no alias sidecar was created. The temporary private key and test-key APK were removed. This smoke run did **not** use the release key.

The existing nine index-diagnostics/binary-token regressions passed. Negative smoke checks rejected unknown original/seed hashes before creating output and rejected duplicate payload entries. Local evidence is under `native-patches/v42-clean-rebuild/verified-build/`, `native-patches/v42-clean-rebuild/signing-smoke-report.json`, and `native-patches/v42-clean-rebuild/reproduction-status.json`. Exploratory trees and copied reference-signature inspection artifacts were removed; the verified build and compact earlier-run reports remain. No device action occurred, and the frozen release/checkpoint was not modified.

**Completed:** the operator authorized the original protected release key, and its signature was regenerated locally without reusing the published signature block. The complete rebuilt signed APK matched the frozen release in a direct byte comparison and at SHA-256 `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`. Strict JAR verification against the pinned public certificate passed. `native-patches/v42-clean-rebuild/verified-build/rebuild-verification.json` records this full signed-artifact result; `signature-verification.json` preserves verifier output. Private credentials were supplied only through the signing process environment, not command arguments or repository files. See [BUILDING.md](BUILDING.md#regenerate-the-release-signature-privately) for repeatable signing instructions.

## V42 destructive integrity run — completed with observations

On 2026-09-22, the release-signed V42 APK (`766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`) was independently verified on the Galaxy S4 before fault injection. The current save, index `-1,92` with 93 valid records, and installed APK were backed up. An off-target restore proved file bytes, ownership, modes, and mtimes before any live mutation.

| Case | Result |
|---|---|
| Index mtime +10 seconds | Passed — startup/recovery and preserved history |
| Index mtime +11 seconds | Passed — startup/recovery and preserved history |
| Index mtime +60 seconds | Passed — startup/recovery and preserved history |
| Missing index | Passed — non-destructive wait, then recovery after restoration |
| Empty index | Passed — non-destructive wait, then recovery after restoration |
| Truncated index | Passed on resumed run — original interrupted attempt retained |
| Invalid AES padding | Passed — non-destructive wait and recovery |
| Wrong envelope checksum | Passed — non-destructive wait and recovery |
| Empty `KEY:` with valid envelope | Passed — non-destructive wait and recovery |
| Missing referenced record | Passed — non-destructive wait and recovery |
| Numbered record written, before index update | Passed — committed history preserved; recovery stable on second restart |
| Temporary index complete, before rename | Passed — old index preserved; recovery stable on second restart |
| Rename complete, before directory fsync | Passed — newly committed record retained; recovery stable on second restart |

During the initial attempt, the truncated-index process reached `SERVER.INIT`, then waited without issuing save requests or changing prior history. After restoration, the recovery process was killed before `SERVER.INIT`; the kernel recorded `send sigkill` for that exact PID. No application crash stack was captured. Memory pressure is a possible cause, not established by that line alone. Further injection was stopped until the user rebooted the device and confirmed readiness.

At that initial stop, the original save was restored and independently recaptured: all 155 archive-member names, types, owners, modes, mtimes, symlink targets, and regular-file contents matched the original baseline; all 93 request records were unchanged. The APK and native library were unchanged. The game was left force-stopped, with no post-stop visual-startup claim. No taps, network changes, APK replacement, or native-library modification were performed during that initial attempt.

These are instrumented data-preservation/backend results, not user-observed UI passes. The raw `CUSTOM.GET` response trailer varied between clean reads; an initial verifier false-negative was retained and corrected using stable pocket/inventory/ranking fields plus persisted history. A launch-PID discovery race was corrected by reanalyzing retained logs against snapshot PIDs and library-load records; the five completed passes were confirmed.

Initial-attempt evidence: `device-snapshots/v42-destructive-integrity-20260922T010140Z/integrity-results.json`. Original backup SHA-256: `eaa0c08e95aabeea865e09ceb3d6d528c08fca0ebd070806c5ff3b72fa4af838`.

### Completed read-fault and process-interruption qualification

After reboot, the exact release APK/native library and every regular save file matched the protected baseline. Clean startup completed with matching pocket, inventory, ranking, and all 93 request records. The five remaining read-fault cases above then passed, bringing the read-fault matrix to ten passes across the original and resumed runs. Each damaged state preserved history without save requests, and each restored state recovered with the baseline index and records unchanged. The earlier SIGKILL evidence remains retained, not erased by the successful retry.

Evidence: `device-snapshots/v42-destructive-integrity-20260922T010140Z/resume-20260922T012755Z/resume-results.json`.

Actual interrupted writes require a manual game-start operation. Three minimal diagnostic libraries were derived from the verified V42 native library: pause after the numbered record but before index update; after temporary-index completion but before rename; and immediately after rename before directory fsync. Each changes only the selected branch, an eight-byte `pause` syscall loop, and the ELF executable-range metadata. These are explicitly instrumented derivatives, not production binaries.

The first boundary (numbered record complete, before index update) passed data-preservation and recovery-idempotence checks. The user reported a loading wait followed by `code:13` after Play. A native backtrace confirmed the intentional pause; request 93 was a complete `GameStart`, the committed index remained `-1,92`, no temporary index existed, and no success response had been delivered. After force-stop and restoration of the production library, all 93 committed records remained byte-identical.

Production startup issued a distinct `UploadPocket` with `heart=1`, reused the uncommitted slot 93, and produced a `CONSISTENT` `-1,93` pool. Coins, gems, EXP, identity, inventory, and ranking matched the baseline; hearts changed from 5 to 6. A second production restart issued no additional request and preserved all 94 recovered records and the heart count. The one-time life adjustment is an observation, not a claim that it is the intended unlimited-heart gameplay behavior. The initial verifier incorrectly demanded a frozen index/pocket after startup; its failed result is retained separately from the corrected transaction-aware verdict.

Evidence: `04_after_numbered_result.json` and the interrupted/recovered snapshots under the resumed run. The original baseline was restored, including its original life count, before preparing each subsequent diagnostic. Both remaining boundary cases subsequently passed as described below.

The kernel log, captured before the harness's force-stop, records SIGKILL for that exact startup PID (1480). No new request 93 was present, no save requests were logged, and the pool remained `CONSISTENT` at `-1,92`: the second boundary was not reached. No application fatal marker was captured. The precise reason for the kernel kill is not established; memory pressure remains a possibility rather than a confirmed diagnosis.

The operator subsequently reported device-wide erratic behavior: the launcher repeatedly crashed and restarted, the instability continued after the game process was terminated, and rebooting resolved it. This supports device-wide instability as the likely explanation for the interrupted attempts rather than treating the SIGKILLs as isolated game failures. The observation is operator-reported context, not a new captured system trace; it does not establish the exact kill mechanism or confirm a kernel crash.

`05_unexpected_close_result.json` and its snapshots preserve this event. At that stop, the production native library was restored and hash-verified, the original save was restored byte-for-byte with expected metadata, and the signed APK remained unchanged. All 93 original records were intact. The game was intentionally left force-stopped pending another operator-authorized attempt.

After that closure, the diagnostic was removed and log capture stopped. The operator subsequently rebooted/reconnected the S4 and explicitly requested resumption. All 148 regular save files, the production library, and release APK matched the protected baseline before rearming. The pre-rename diagnostic then completed startup with no save requests and index `-1,92`.

The pre-rename boundary was reached and captured: committed index `-1,92`, complete valid temporary index `-1,93`, valid `GameStart` request 93, and the diagnostic pause in the native backtrace. No success response had been delivered. After interruption and restoration of the production library, all 93 prior records remained unchanged. Startup reused the uncommitted slot for a distinct `UploadPocket heart=1`, removed the temporary index, and produced a `CONSISTENT` pool. A second restart preserved all 94 recovered records and the resulting life count without another upload. This is a process-interruption/data-integrity pass with the same one-time life adjustment observation, not a power-loss durability claim. Evidence: `07_before_rename_result.json`.

The final boundary was reached after rename and before parent-directory fsync: the committed index was valid at `-1,93`, request 93 was complete, the temporary file was absent, and the native backtrace confirmed the diagnostic pause. After process interruption and restoration of the production library, **all 94 committed records, including `GameStart` record 93, remained byte-identical**. Startup appended `UploadPocket heart=1` as record 94, yielding a `CONSISTENT` `-1,94` pool. A second restart preserved all 95 recovered records and the life count without another upload. Evidence: `09_after_rename_result.json`.

All ten read-fault cases and all three controlled process-interruption boundaries passed their stated data-preservation/recovery checks. Fourteen captured index/request-envelope checks also confirmed full 16-byte tokens and valid envelope integrity. These results **do not simulate electrical power loss, battery removal, lost storage-cache contents, or a hardware reset at the write boundary**. The temporary diagnostics were verified derivatives of V42; production-library recovery was verified separately.

The one-time `heart=1` recovery upload occurred in all three boundary cases (5 to 6, remaining 6 on the second startup). Coins, gems, EXP, identity, inventory, and ranking were preserved. This is not a claim of completely side-effect-free rollback or approval of the unlimited-heart adjustment semantics. The two earlier kernel SIGKILL events, varying raw response trailer, and corrected verifier/PID-discovery issues remain documented rather than erased by successful reruns.

### Final restoration and evidence

The exact production native library and its metadata were restored and verified; the release-signed APK remained unchanged. All **148 original regular save files** are byte-identical, all **155 archive members** match the expected post-reboot metadata, and the original pool is `CONSISTENT` at `-1,92` with all 93 records unchanged. Temporary device staging was removed, log capture stopped, and the game was left force-stopped with **no diagnostic library active**.

Final report: `device-snapshots/v42-destructive-integrity-20260922T010140Z/resume-20260922T012755Z/final-integrity-verification.json`.

Final restored snapshot: `10_final_restored_baseline/app-data.tar.gz`, SHA-256 `132535a3798ea1064ea92f9674401557fa1af25358a3cfe79397e179f60f0338`. The original backup remains unchanged. `pending-write-boundary.json` now records completion, not an armed test. Read-only memory/low-memory-killer settings were recorded for context; no memory configuration was changed.

The only baseline metadata change introduced by reboot was the system-managed `lib` symlink's mtime; its target and ownership were unchanged. Restoration leaves that reboot-created link untouched. No automated taps or network changes were performed.

## Historical V25 environment

| Field | Value |
|---|---|
| Device | Samsung Galaxy S4 SGH-I337M |
| Android | 4.4.2 |
| Application | Birzzle Fever 1.1.2, package version code 13 |
| ABI | 32-bit ARM |
| Identity module | Disabled for V25 |
| V25 development APK SHA-256 | `66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05` |

The Android package UID varied across reinstalls and was not a compatibility requirement. V25 uses the historical application identity internally.

## Historical V25 qualification summary

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

## Historical V25 persistence invariants

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

- V42's eight functional release checks passed by operator report on the Galaxy S4/Android 4.4.2 and Galaxy S20 Plus/Android 13. No logs or save backups exist for those empirical runs; compatibility beyond these reported environments is not established by them.
- The natural trigger for the original transient empty-index read was not captured directly; controlled fault injection reproduced the destructive mechanism.
- Permanent root-induced index removal can deliberately hold the app in a non-destructive wait until repaired.
- One daily-bonus timing observation remains unclassified and non-blocking.
- Clean-original V42 reproduction requires the separately supplied sanitized seed, pinned external toolchains, and original release-signing credentials; those private/proprietary inputs are not distributed with the source tree.

## V42 legitimate remaining-pet purchases — three normal purchases passed; seasonal claims blocked

The operator requested acquisition of the five remaining named pets using the historical high-currency save, specifically to check that the pet-tutorial softlock fix does not block normal purchases. Research subsequently established that only Penny, Holly, and Pow are missing normal-shop pets; Rudy and Eve are Christmas-event rewards. The original five-normal-purchase assumption was incorrect. This run uses the unchanged release-signed V42 APK and production `libef2d.so`/`libbirzzle.so`; no diagnostic hooks, inventory overrides, price changes, or new currency grants were installed.

The current save was archived and its restore payload proved off-target before replacement. The historical fixture is `device-snapshots/2026-08-30-unclamped-11-game-longrun/final-data.tar.gz`, SHA-256 `9011057332cac5bf5f4b8372d66612956850af06f5e3b5a7b1d04ea47a97c3f2`. Its 157-record pool is `CONSISTENT` at `-1,156`. Linux ownership was mapped to the current application UID while all fixture file bytes and mtimes were preserved; the package-manager library symlink was left untouched.

Production startup completed without save requests or fatal markers. Logged baseline: 980,800 coins, 99,870 gems, and owned pet IDs 0, 1, and 2 (Suri, Popo, Polo). Each normal purchase requires a manual UI action, visual outcome/price observation, transaction and balance accounting, and ownership persistence across restart. Penny (4), Holly (3), and Pow (5) passed, leaving all six normal pets owned in the retained test checkpoint. Rudy (8) and Eve (9) have a separate event-claim path; neither has been acquired or runtime-qualified by this test.

| Purchase target | Status |
|---|---|
| Penny | Passed — 24,000 coins; ownership and equip marker persisted after restart |
| Holly | Passed — 60 gems; ownership and equip marker persisted after restart |
| Pow | Passed — 32,000 coins; ownership and equip marker persisted after restart |
| Rudy | Blocked — unowned Christmas-event pet, absent with `PetEventID=0`; not a normal shop purchase |
| Eve | Blocked — unowned Christmas-event pet, absent with `PetEventID=0`; event acquisition untested |

Penny was confirmed acquired and equipped by the operator. The save appended exactly `inventory.buy` (item ID 4), `pocket.set coin=-24000` with no other currency/stat delta, and `inventory.use` for that purchase's transaction ID. All three successful callbacks were captured. After cold restart, the pocket was exactly 956,800 coins and 99,870 gems; the previous three pets were unchanged, Penny was owned at ability 1, and the equipped marker referenced Penny. All 160 request records and the index remained byte-identical to the post-purchase snapshot, with no additional save request on restart. No fatal marker was captured. Evidence: `penny-result.json` in the run directory.

Holly was confirmed acquired for 60 gems and equipped by the operator. Records 160–162 contain one `inventory.buy` (item ID 3), one `pocket.set gem=-60` with no other pocket delta, and one `inventory.use` for Holly. All three callbacks succeeded. Cold restart preserved exactly 956,800 coins and 99,810 gems, all prior pets, Holly's ownership/equipped marker, ranking, and all 163 records plus the index; no new request or fatal marker occurred. Evidence: `resume-20260922T223300Z/holly-result.json`.

Pow was confirmed acquired for 32,000 coins and equipped by the operator. Records 163–165 contain one `inventory.buy` (item ID 5), one `pocket.set coin=-32000` with no other pocket delta, and one `inventory.use` for Pow. All three callbacks succeeded. Cold restart preserved exactly 924,800 coins and 99,810 gems, all prior pets, Pow's ownership/equipped marker, ranking, and all 166 records plus the index; no new request or fatal marker occurred. Evidence: `resume-20260922T223300Z/pow-result.json`.

The operator requested a pause after Penny was verified. The resumable test checkpoint is `device-snapshots/v42-legitimate-pet-purchases-20260922T041904Z/05_paused_after_penny/app-data.tar.gz`: its `CONSISTENT` pool remains `-1,159`, all 160 verified records and the index are unchanged, and no additional purchase was recorded. Last verified test balances are 956,800 coins and 99,870 gems.

At the pause, the original current save was restored byte-for-byte with all archived metadata, returning its pool to `-1,92` with 93 records. Both production native libraries and the unchanged release APK were verified. Capture was stopped, temporary device staging removed, and the game left force-stopped. The historical test checkpoint was retained locally rather than left active during the pause.

The operator subsequently confirmed readiness, stated that the save had not been played, and explicitly waived a new save backup. The retained original backup and restore payload were verified instead; no new live-save backup was created. All 218 files in the Penny checkpoint matched after restoration, and production startup preserved its 956,800 coins, 99,870 gems, inventory, equipped marker, and ranking without a new save request. Holly and Pow were then verified as described above. The operator reported that Rudy and Eve were absent from the menu, so further purchase instructions were stopped.

The test was checkpointed again after Pow at `resume-20260922T223300Z/06_checkpoint_after_pow/app-data.tar.gz`, SHA-256 `02c21163b53b32bdf1c80bc3deecaedececc7ebb667e022d1505ff60f589890a`. It retains 924,800 coins, 99,810 gems, all normal pets, and the consistent pool `-1,165` with 166 records; no new purchase occurred after Pow. The original current save was then restored byte-identically with its archived metadata except for the preserved current package-manager library symlink, returning the pool to `-1,92`. Production libraries/APK were verified, capture stopped, staging removed, and the game left force-stopped.

[Rudy/Eve research](SEASONAL_PETS.md) identifies the implemented event requirements, zero-cost claim path, abilities, artwork, and inactive configuration. Nine relevant native functions are unchanged from the original APK. Off-device native-function probes are not a substitute for acquiring the event pets through an active event and verifying persistence; five-pet aggregate qualification remains unclaimed.

State and evidence: `device-snapshots/v42-legitimate-pet-purchases-20260922T041904Z/purchase-test-state.json`, the historical `pause-report.json`, `resume-20260922T223300Z/resume-verification.json`, and `resume-20260922T223300Z/pause-for-pet-research.json`. The historical test checkpoint is retained locally; it is not the save currently installed.
