# Changelog

This chronology was reconstructed from preserved patch scripts, milestone directories, checkpoint notes, and validation summaries. Git was initialized after the research; this file records milestone history without fabricating retroactive commits.

Labels:

- **Candidate**: behavior verified on its target device; broader regression qualification remains pending.
- **Pending**: built and statically verified; device behavior not yet qualified.
- **Accepted**: retained directly or by lineage in V25.
- **Superseded**: useful milestone replaced by a later implementation.
- **Investigative**: diagnostic/fault-injection build, never intended for release.
- **Rejected**: behavior failed or violated an invariant.

## Unreleased public-source import

- Curated development and research sources for GitHub.
- Excluded APKs, extracted libraries, complete decompiled trees, bulk assets, saves, logs, screenshots, device captures, toolchains, and keys without deleting local copies; retained only the reviewed decompiled code excerpts used by the reverse-engineering work.
- Added source-only legal notice, repository policy, architecture, build boundary, installation model, validation matrix, contribution guide, and automated tracked-file audit.
- Replaced fixed private ADB serial defaults with operator-supplied configuration.
- Recorded that the initial repository is not yet a one-command reproducible V25 build.
- Created the private `Antonio231102/birzzle-fever-offline` GitHub repository; public visibility remains gated on a fresh history/content audit.

## V43 — offline Christmas event until both pets claimed — Pending

- Based on the exact frozen V42 release without changing that release or its checkpoint.
- Set Rudy's three goals to 100,000,000 score, 50 opened Mystery Boxes, and 50,000 collected coins; set Eve's to 200,000,000, 100, and 100,000.
- Share persistent cumulative event counters, continue beyond Rudy's goals, and require all three goals independently for each pet. Ignore the legacy Friendship Point event mission.
- Replace Eve's social-action instructions with current/target objective rows and the expiry date with “Always active.” Preserve free native event claims and both pet abilities.
- Build a separate development-signed APK. Six ARM/Thumb event regressions and nine existing index/token regressions passed; a native UI-adapter smoke passed without invoking the original renderer.
- Preserved the S4's installed V42 APK and a readable 155-file rollback backup, then successfully uninstalled and fresh-installed V43. The pulled installed APK matched the initial test artifact exactly.
- The first manual game-to-menu transition crashed with `SIGILL`: the new Thumb UI helper called ARM PLT code through untyped linker bindings. Replaced `--defsym` with typed function-symbol objects so LLD emits interworking `BLX` calls.
- Added a regression that fails on the original invalid instruction and passes through the real ARM PLT/GOT path after the fix; all 16 focused regressions pass. The earlier UI-boundary smoke had masked the transition error.
- Installed the corrected debug-signed APK in place, verified installed-byte equality, and preserved all 54 app-data files with their contents and metadata. The app is stopped; physical retest and remaining event qualification await the readiness gate.
- The operator subsequently reached the main menu and automatic event popup with correct objectives; a requested screenshot documented Eve's small text.
- Matched Eve's mission row order and native heading/icon/separator/label styles to Rudy's. Reused localized remaining/completed text and the existing comma formatter; removed small two-line counters and the separate progress bar while retaining progress application.
- All 17 host regressions passed. Installed the matching-presentation revision in place, verified installed-byte equality and preservation of all 54 app-data files. The operator confirmed matching mission icons/text/font size and both pets' remaining requirements updating after each game.
- Prepared a separate reduced-goal unlock test: Rudy 500,000 score / 1 box / 1,000 coins; Eve 1,000,000 / 2 / 2,000. Fresh-installed without backing up the replaced save, as requested, and restored the existing 924,800-coin / 99,810-gem fixture with all 224 regular files verified. Normal goals and the canonical APK remain unchanged. Physical claims and restart persistence await the readiness-gated test.
- Confirmed Rudy's zero-cost claim, upgrades to level 30, equipping, and persistence through cold restart; all 316 request records remained valid and unchanged. The operator confirmed the same state and continued Eve progress, then unlocked Eve.
- Diagnosed Eve's 497,282-hour reward wait: its unlock callback used device wall time while its getter subtracted offline server time. Reproduced the exact displayed duration in original ARM code.
- Replaced reward timing with persistent `CLOCK_BOOTTIME` plus boot UUID. Preserve the immediately due first gift, then six hours per reward; calendar changes cannot accelerate it. Phone reboot conservatively resumes saved remaining time without crediting untrusted elapsed time. Migrate legacy reward profiles without changing ownership, levels, mission progress, or the request journal.
- Guard reward handoff with verified cooldown persistence; retain original reward selection and cache invalidation. All 27 focused host regressions pass, including ten cooldown cases. Signed normal/reduced-goal artifacts and native smoke are complete; installation and physical reward qualification remain pending.
- Deployed the strict boot-time cooldown build in place on the S4 after preserving the previous APK and a readable save archive. Verified installed APK/native-library equality and exact preservation of all 448 regular app-data files and app UID. No uninstall, restore, launch, or log capture; physical reward testing awaits readiness. The discussed hybrid alternative was not implemented.
- Passed the first physical Eve reward test on the S4: the operator received two hearts, saw the six-hour countdown begin, and could not claim again immediately. Scoped runtime evidence confirms one two-heart request and wallet progression from five to seven, with no captured fatal markers. Restart, clock-change, phone-reboot, and actual-expiry checks remain pending.
- Accepted operator-confirmed cooldown persistence across app/device restarts and resistance to a manual date change without rerunning those checks.
- Prepared `stress_eve_cooldown.py`: gated navigation calibration, forward/backward minute/hour/six-hour/day/year changes, app restarts, device reboots, and graceful shutdown/off-hold/manual power-on. Includes save backup, encrypted-checkpoint assertions, no-payout checks, scoped evidence, and clock/settings recovery. CLI and signed-native oracle smoke pass; physical stress remains unexecuted.
- Corrected the earlier Eve reward research: the heart/gem labels were swapped. Actual selector and payout execution yields 50% coins (200–500), 40% hearts (1–3), and 10% one gem, using `lrand48`. Two consecutive heart rewards are nominally 16%, assuming independent draws. Verified cache invalidation and unchanged original reward code; no APK or rate changes made.
- Corrected the physical runner's KitKat output framing while retaining linker diagnostics, and split rooted profile export/chmod operations. Actual package/clock/settings reads and profile exports exercised the fixes. Automated navigation remained unqualified and was discontinued at the operator's instruction.
- Passed six operator-controlled Eve clock/lifecycle checks: ±6-hour offsets, +1 day, future-date app restart, reboot then +365 days, and full shutdown then −365 days. A read-only monitor recorded 60.034 seconds of ADB disconnection after operator-confirmed shutdown. Restored the original clock and automatic time/time-zone settings without touching the game UI. This is not completion of the original repeated automated campaign or an actual six-hour-expiry test.
- Replace forced event activity with the original ownership check for both Rudy and Eve. Completed objectives alone do not close the event; either claim order and previously owned inventories work without a new save flag.
- Preserve catalog identity and Eve's cooldown/gifts while suppressing completed-event dialog opens, hiding stale banner actors through the original native hide path, and cleaning up event images even after activity ends. Replace the date caption with “Until both claimed.”
- Passed 32 focused regressions and native smoke of both newly signed normal/reduced-goal APKs, including original owned-pet roster filtering and future Eve gift handoff after closure. Strict signature/payload checks passed. No device installation or UI interaction; physical qualification remains pending.
- Deployed the reduced-goal claim-completion build on the S4 with `adb install -r`, after preserving the previous APK and readable full save archive. Verified the installed APK and both native libraries, unchanged app UID, and exact contents/metadata of all 460 regular app-data files. No uninstall, data clearing, save restoration, or game launch; closure UI qualification awaits an operator-controlled test.
- Accepted operator-confirmed event-entry closure and diagnosed retained winter artwork: startup loads images before inventory arrives, the inactive scene branch skips repainting, and the native repaint hardcodes winter textures.
- Reconcile seasonal artwork at the inventory-ready main menu and post-claim inventory transition, preserving V41's scene rearm and original crop/tile geometry. Select ordinary textures after closure and remove winter overlays without rebuilding gameplay controls or adding save fields. Five pre-fix transition failures now pass; all 34 focused regressions and packaged artwork/cooldown/goal-boundary checks on both signed builds pass.
- Deployed the reduced-goal artwork correction (`ca385c0b4879d6259462cd3b88c8e07c1f7630c6879def29e5833ea231d5b32a`) in place on S4 after a fresh APK/save backup. Verified installed APK/native libraries and exact preservation of all 461 regular app-data files. No game launch or UI interaction; physical artwork qualification remains pending.
- Diagnosed the S20's empty pet selection as an inherited inventory-ID narrowing bug, not event expiry. Native purchase code formats a 64-bit server-adjusted timestamp with `%lld`; the offline reducer reads it with ARM32 `atoi`, turning Rudy's `2147486133` into `2147483647`. The previous engine is byte-identical to V42.
- Preserve transaction IDs as strings in offline selection and inventory-update matching. Keep purchase IDs, save formats, journal history, currency, integrity guards, and Christmas gameplay unchanged. Five native replay regressions cover the captured failure, colliding large IDs, replay recovery, nonmatching IDs, and purchase/equip/upgrade with a full-width ID; all 39 focused regressions pass.
- Built and verified signed normal/reduced artifacts under `inventory-id-fix/`; only `libef2d.so` differs from the previous reduced APK. Installed the reduced correction (`4d9c8cb483cb5b103ec0158f2c521ced3b8d39e762faf81a5619aea3b1118095`) in place on S20 without a save backup or restoration. APK/native hashes and UID verified; metadata of 222 known private files is unchanged. Private contents are inaccessible without debugging. No game launch; manual equip qualification remains pending.
- The subsequent S20 launch exposed a packaging regression: Android rejected the relocated engine program-header table (`loaded phdr ... not in loadable segment`) before inventory code ran. Add an explicit `PT_PHDR` describing its mapped address. A new loader-layout regression rejects the failed build; all 40 focused regressions and both signed-APK selection replays pass.
- Installed the rebuilt reduced APK (`3f7d144e342438d49110e219854939d946c7d17d5d9fbce29520a8524a3a3c5e`) in place on S20 without backup or restoration; installed hashes, UID, disabled debugging, and 222 known file metadata entries match. Corrected artifacts are under `inventory-id-fix/loader-corrected/`. Standalone Android probes advance past header discovery but cannot finish legacy text-relocation protection in shell context. Full startup and equip qualification remain pending; the game is stopped.
- Accepted operator-confirmed S20 startup recovery and all four focused inventory checks: selection persistence, switching pets, gameplay with Rudy, and upgrade isolation. Eve's claim succeeded and the Christmas event disappeared immediately. Eve is not equippable and every other pet is already unlocked, so new equippable-pet acquisition remains host-tested only; no save reset or full V42 rerun is required.
- Accepted operator-confirmed natural six-hour Eve gift renewal, non-stacking after waits of 12 or more hours, and continued rewards after both pets are claimed and the Christmas event disappears. Closed the remaining functional expiry/payout check without repeating it; no instrumented timing trace or completed automated stress campaign is claimed.
- Built a revised **normal-goal development candidate**: Rudy 100,000,000 score / 25 opened boxes / 25,000 collected coins; Eve 200,000,000 / 50 / 50,000. The reduced S20 test build remains unchanged. All 40 focused host regressions pass; packaged ARM execution verifies the embedded goals, closure only after both claims, ordinary artwork after closure, and full-width Rudy inventory selection. FruitSpy release signing, a distinct pet array-index bounds patch (if intended), physical testing of the new normal-goal APK, and final checkpoint declaration remain unresolved.
- Signed the revised normal-goal APK with the operator-supplied external FruitSpy PKCS#12 key, using the same public certificate as frozen V42. APK SHA-256 `fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`; strict pinned-certificate signature verification, ZIP integrity, and all 1,140 non-signature payload bytes pass. Signed-library ARM smoke covers both claim orders, ordinary artwork after final claim, Android program headers, Rudy's exact transaction ID, and selection/isolated upgrade with different pets on another valid inventory shape. No distinct array-index bounds guard is claimed. Neither device was modified; physical normal-goal qualification and public release gates remain separate.
- Created the newest local, read-only V43 technical checkpoint at `checkpoints/2026-09-26-v43-normal-goals-fruitspy-fdc05ae28a20/`, retaining frozen V42 unchanged. Its privacy-scrubbed archive SHA-256 is `b7c3dd0c46fc95eb65549179ebfbbbb498d765c55d6ce18995fec5fce957c02d`; all 22 members have verified SHA-256/size records. No private signer material, personal save, device install, or new physical qualification is included.
- Began the operator-requested fresh FruitSpy-signed normal-goal deployment **without save preservation**. Both existing app packages were uninstalled without `-k`, and their private app-data directories were confirmed absent; no backups or restorations were performed. S4 successfully installed the new APK, and its installed APK SHA-256 matches `fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`. S20 remains uninstalled: both standard ADB installation modes returned `INSTALL_FAILED_VERIFICATION_FAILURE: Install not allowed`, with a Play Protect dialog focused. No security setting was changed or game launched; operator review is required before retrying S20. Evidence: `device-snapshots/v43-fruitspy-normal-goals-fresh-install/deployment.json`.
- Retried S20's standard non-streaming install with the operator prepared to handle Play Protect; it returned `Success` without changing security settings. Both devices now have the freshly installed FruitSpy-signed normal-goal APK, with installed SHA-256 `fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`. New private app-data directories were created after the verified uninstalls. No backup, restoration, log capture, or game launch occurred. Manual startup qualification remains pending on both devices; see the updated deployment record.

## V42 — binary-safe persistence tokens — Two-device manual functional checks passed

- Diagnosed V41's mission-claim/startup stall: `GenerateToken()` used `strlen()` on binary MD5 output, allowing an empty `KEY:` in a correctly encrypted response index.
- Replaced that length calculation with 16 at `libef2d.so:0x122ca6`. All other APK payloads and fail-closed pool guards remain unchanged from exact V41.
- Corrected analyzer field parsing so empty-key indices and numbered records cannot be reported as valid; retained compatibility with legacy nonempty short tokens.
- Added archive-only, index-only recovery with preserved progression bytes, index bounds, timestamps, ownership, and modes.
- Built and verified the development-signed candidate; nine focused regressions passed. ARM emulation of its token call site covers every zero-byte position.
- Installed exact V42 in place and repaired only the live index after archiving and verifying the failure state. Preserved all 19 prior request records and the other 68 save files.
- Passed recovered startup, three mission claims including two back-to-back, and restart persistence on the Galaxy S4. The pool advanced from `-1,18` to `-1,26` with all prior records unchanged and no semantic warnings.
- Verified all 17 new/changed encrypted envelopes have full 16-byte tokens; the new index token includes an internal zero byte without truncation. Package-scoped logs had no detected fatal, ANR, or request-timeout markers.
- Archived the instrumented S4 token/recovery regression separately; its log and save evidence applies only to that earlier session.
- The operator subsequently reported all eight functional release checks passed on the Galaxy S4/Android 4.4.2 and Galaxy S20 Plus/Android 13: fresh APK-only initialization, fresh-player progression, offline gameplay, connected gameplay, rewards/mutations, leaderboard, unlimited-life behavior, and mature-save cold starts.
- Those later tests were intentionally empirical, with no logs or save backups. No progress loss, crashes, freezes, or softlocks were observed. Counts and installed-device hashes were not independently recorded.
- Clarified that the current unlimited-hearts patch prevents the visible counter from decreasing; zero lives are never displayed, so zero-displayed-life starts are not an applicable acceptance criterion.
- The operator accepts residual undiscovered issues for review through user reports. These manual passes do not assert unperformed fault-injection tests or complete independent legal/build/publication gates.
- Started a separate instrumented destructive run on the release-signed S4 build on 2026-09-22. Index mtime +10/+11/+60, missing index, and empty index passed preservation/recovery checks against a 93-record baseline.
- Initially paused after a kernel SIGKILL during restored startup in the truncated-index case. Preserved that inconclusive attempt and restored the original save exactly before the user rebooted.
- Resumed with verified clean startup. Truncated index, invalid padding, wrong checksum, empty-key regression, and missing referenced record all passed, completing ten read-fault preservation/recovery cases against the unchanged 93-record history.
- The first actual write boundary passed data-preservation and recovery-idempotence checks. The intentionally paused `GameStart` produced the reported `code:13`; all committed records survived. Recovery wrote one `UploadPocket heart=1` adjustment, which did not repeat on a second restart. Its gameplay semantics remain a separate observation.
- Two attempts ended in kernel SIGKILL and were paused with the original state restored. The operator later reported device-wide launcher crashes/restarts that persisted after game termination and resolved after reboot, supporting likely device-related instability; the exact kill mechanism remains unconfirmed. Both events and the corrected verifier/PID-discovery limitations are retained in the evidence.
- The pre-rename boundary passed: old and temporary indices were captured separately at the verified pause, prior history survived production recovery, and a second restart made no further change.
- The post-rename/pre-directory-fsync boundary passed: all 94 committed records, including the interrupted `GameStart`, survived byte-for-byte; recovery appended one upload and a second restart preserved all 95 records.
- Completed ten read-fault cases and three controlled process-interruption boundaries. Each boundary recovery included one `UploadPocket heart=1` that did not repeat; this observation is separate from the data-integrity verdict. Physical power-loss/storage-cache-loss durability was not tested.
- Restored and verified the exact production library and original save: 148 regular files byte-identical, 155 members with expected post-reboot metadata, and the original 93-record pool at `-1,92`. Removed temporary device staging, stopped logging, and left the game stopped with no diagnostic active. Final evidence is recorded in `docs/TESTING.md`.
- Added `rebuild_v42.py`, deterministic JDK signing/ZIP support, and a release metadata recipe. Clean original-APK builds regenerate every one of the 1,140 release payloads without historical APK or prebuilt patched-library inputs; the sanitized offline seed remains a separate supplied input.
- Reused existing smali patch specifications, rebuilt native assembly, and added hash-checked native-only modes to the historical patch stages. Regenerated the manifest/signature-file/signed-attribute bytes exactly and verified real signing with a disposable key.
- Completed original protected-key signature regeneration and strict JAR verification. The complete clean-original signed APK is byte-identical to the frozen V42 release, SHA-256 `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`. Neither historical APK payloads nor the published signature block were reused.

## V37 — global power-up scene marker — Pending

- Reproduced V36's non-crashing empty-leaderboard softlock on the first power-up-selection return after 10/10 settled cold launches.
- Confirmed `POCKET.GET` and `GIFT.GET.COUNT` completed but no `SCORE.RANKING` followed; the live power-up marker was clear while the request gate remained closed.
- Found that V14 marked only one of seven constant scene-`0x0A` calls, allowing tutorial/progression routes to enter the same power-up screen without arming a later ranking generation.
- Moved marking to `CStoryManager::SetCurrentScene()` itself, restored the old single-callsite hook, and preserved the original scene store for all values.
- Built and statically verified the signed APK and exact four-range native delta. Device deployment is intentionally pending.

## V36 — BuyPet-response ranking generation — Superseded candidate

- Replaced untraversed tutorial-state guesses with the deterministic `POCKET.SET BuyPet` completion path.
- Passed the fresh-save free-pet tutorial, its forced first game, a normal Polo purchase, and 10/10 settled Galaxy S4 cold launches.
- Failed final power-up-return stress because its inherited V14 marker did not cover every route into the power-up scene.

## V35 — tutorial state-`0x41` marker — Rejected

- Tested the alternate tutorial state callback after V32's state-`0x42` hook was not traversed.
- Live state showed that this callback also did not arm the post-purchase ranking generation.

## V34 — isolated retryable tutorial generation — Superseded

- Separated the tutorial/BuyPet pending byte from V14's power-up byte and corrected for the legacy Thumb ADD-PC address shift.
- Kept a pending generation retryable until `GetRanking()` accepted it.
- The dispatch behavior was retained, but the speculative tutorial marker source was not traversed.

## V33 — retryable tutorial ranking marker — Rejected

- Avoided consuming a tutorial marker when an early ranking dispatch could not accept a request.
- Did not fix the free-pet flow because the underlying state-`0x42` marker never became active.

## V32 — tutorial state-`0x42` ranking re-arm — Rejected

- Added a tutorial-specific marker intended to preserve the post-free-pet main-menu ranking.
- Device state proved the selected tutorial callback was not part of the observed purchase path.

## V31 — corrected ranking lineage — Superseded

- Rebased the unlimited-play changes onto the actual V14 ranking lineage instead of the accidental V11 lineage used by V15.
- Restored startup and established menu-return protections while retaining the V26 package's Java and seed payloads.
- Exposed the separate free-pet post-purchase generation gap addressed by V36.

## V30 — transaction boundary fault injection — Investigative

- Added private one-shot controls and logging wrappers around record, index, flush, rename, directory-sync, and cleanup boundaries.
- Exercised deterministic interrupted-write recovery without shipping diagnostic behavior in a release candidate.

## V29 — V26 transaction diagnostic — Investigative

- Wrapped V26's compatibility writer operations without changing their return values.
- Recorded the exact open, sync, rename, directory, and cleanup outcomes used to isolate persistence failures.

## V28 — response-index mtime diagnostic — Investigative

- Instrumented the V26 mtime guard to report its basename match and accept/reject path.
- Used only for distinguishing timestamp selection failures from transaction-order failures.

## V27 — V25 mtime-guard control — Investigative

- Restored V25's mtime guard in the V26 package while leaving V26's modern writer changes intact.
- Served as an A/B control for separating modern syscall behavior from response-index timestamp selection.

## V26 — modern data-path atomic writer — Candidate

- Reproduced the first-pet softlock on Android 13: `inventory.buy` was saved but never delivered an `INVENTORY.BUY` callback.
- Instrumentation identified `renameat` returning `-18` (`EXDEV`) because the temporary index used `/data/data/...` while the authoritative path used `/data/user/0/...`.
- Derived the temporary index and parent directory from the authoritative runtime path, keeping both sides of the atomic rename on the same mount.
- Replaced legacy direct filesystem syscalls with ARM EABI `openat`, `renameat`, and `unlinkat`.
- Made response-index mtime identification compare the basename rather than assuming a 44-byte data-directory prefix.
- On the Galaxy S20 running Android 13, passed fresh Suri acquisition and the follow-on `INVENTORY.USE`, `POCKET.SET BuyPet`, ranking refresh, and `POCKET.SET GameStart` callbacks without a crash or softlock.
- Galaxy S4 Android 4.4.2 regression qualification remains pending.

## V25 — ranking-template correction — Accepted

- Retained V24's connectivity-independent backend and V15/V23 native lineages byte-for-byte.
- Corrected the sanitized ranking seed to the offline calculator's undocumented two-slot contract.
- Used the historical identity in both slots with distinct sentinel scores: `-1` and `0`.
- Restored personal-score reconstruction while avoiding the historical equal-entry crash condition and dummy-player heart button.
- Passed clean APK-only progression, 10/10 mature cold starts, 9/9 first-read fault cases, and multi-session offline/connected qualification on the Galaxy S4 test device.

## V24 — connectivity-independent startup — Accepted into V25

- Made the Java startup gate report compatible reachability.
- Made native `CRequestQueue::NetworkStatusSync()` return false, deterministically selecting `CResponsePool::RequestOffline`.
- Skipped obsolete GCM registration and removed the application's GCM receiver/service declarations.
- Added exact-Unix-mtime restoration to the save bootstrap.
- Reduced the seed to 26 sanitized runtime files.
- Rejected Java-only connectivity, forced-native-connected routing, duplicate-ranking seed, dummy-UID ranking, wrong bootstrap asset, and delayed GCM retry variants.
- Exposed a missing-score regression caused by reducing the ranking cache to one slot; corrected in V25.

## V23 — request-first index commit — Accepted into V25

- Reordered response-pool persistence so a numbered request is durable before the atomic index replacement advertises it.
- Exercised kill boundaries before index write, after numbered write, and around rename.
- Reconciled post-restart progression behavior and retained V22 first-read protection.

## V22 — first-read recovery — Accepted into V25

- Extended response-index hardening to the first read in a new process.
- Added cryptographic validation before accepting an index affected by timestamp skew.
- Entered a non-destructive wait for missing, empty, truncated, bad-padding, bad-envelope, or missing-record mature indices.
- Exercised first-read, mid-session, and interrupted-write fault matrices.
- Rejected an early absolute-rodata implementation before the position-safe correction.

## V21 — response-index hardening — Accepted into V25

- Replaced purely process-local maturity assumptions with persistent pool evidence.
- Guarded against indices that reference absent numbered records.
- Added mature cold-start and first-read fault harnesses.
- Preserved normal virgin initialization and progression.

## V20 — request-index retention — Accepted and later strengthened

- Identified transient empty index reads as the shared cause of pocket, inventory, quest, mission, pet, and ranking rollback.
- Added an in-process high-water mark and retry path so a mature pool cannot be mistaken for a new pool after a valid read.
- Preserved legitimate first initialization when no mature state has been observed.
- Added forced-empty, unclamped control, timestamp-skew, cold-launch, and profile diagnostic variants.
- V21/V22 later closed first-process-read and persistent-corruption gaps.

## V19 — authoritative gem/pocket guard — Investigative defense in depth

- Corrected the authoritative gem safe-number source used by the V18 experiment.
- Guarded anomalously lower pocket values and truncated inventory responses after authoritative state was loaded.
- Demonstrated that consumer clamps cannot protect quest/mission history or recover a pool already truncated to request zero.
- Not retained in the final V25 gameplay lineage; the root response-index fix superseded broad economy clamps.

## V18 — XP-aware pocket guard — Investigative

- Narrowed pocket-response clamping using experience and response `extradata`.
- Helped distinguish legitimate spending from global rollback.
- Used the wrong gem safe-number member; corrected in V19.
- Not retained in V25.

## V17 — defensive-state and economy experiments — Investigative/Rejected for production

- Built inventory-truncation and pocket-regression fault injectors.
- Added temporary economy-grant variants for accelerating progression tests.
- Tested set-only and broader consumer guards.
- Preserved assembly and patch sources; excluded test APKs and generated payloads.
- No test-economy grant is part of V25.

## V16 — defensive state guards — Investigative

- Added initial pocket and inventory response guards after observing progression rollback.
- Established hook locations and cleanup paths used by later diagnostics.
- Replaced by the narrower V18/V19 experiments and ultimately by response-pool hardening.

## V15 — portable no-heart-deduction — Accepted into V25

- Moved unlimited-play behavior to the safe life-consumption boundary.
- Allowed `GameStart` after the displayed life count reached zero without forcing unrelated economy values.
- Retained the established hardcoded identity and ranking/menu behavior.

## V14 — power-up scene pending state — Superseded

- Moved ranking re-arm logic closer to the power-up-to-menu scene transition.
- Improved one return path but did not yet provide the final common-transition behavior.

## V13 — power-up pending generation — Superseded

- Added pending-generation state for returns from the power-up selection screen.
- Reduced transition races but did not consistently eliminate the softlock.

## V12 — power-up dispatch and self-seeding branches — Superseded

- Tested dispatch-side ranking re-arm variants.
- Added the first portable self-seeding package branch and bootstrap verification.
- Demonstrated that a single package could replace the Xposed-plus-Titanium setup.
- Later persistence, connectivity, exact-time, and seed-template work superseded the V12 package.

## V11 — ranking dispatch re-arm — Superseded checkpoint

- Re-armed ranking delivery around return-to-menu dispatch.
- A hybrid original-2016-plus-two-file save completed approximately 15 games and 51 ranking events without crash, exception, or ANR.
- Retained as an important data-compatibility checkpoint; manual hybrid restoration was later replaced by self-seeding.
- Diagnostic dispatch A/B variants were not release builds.

## V10 — rejected-ranking cleanup — Rejected

- Attempted to clean UI/loading state after suppressing a ranking callback.
- Cleared the animation but left the main menu noninteractive and without the personal score.
- Preserved as evidence that hiding the spinner is not equivalent to completing the response lifecycle.

## V9 — post-restore re-arm — Superseded

- Re-armed ranking after restoration of menu state.
- Addressed completed-game behavior but did not cover every power-up and mid-game return path.

## V8 — menu-return re-arm — Superseded

- Moved or duplicated gate re-arm at a broader main-menu transition.
- Fixed mid-game and completed-game returns, but power-up cancellation remained intermittent.

## V7 — ranking generation gate — Superseded checkpoint

- Kept the startup ranking guard closed until the active leaderboard UI consumed its response.
- Introduced explicit generation-based re-arm behavior for later refreshes.
- Passed repeated games/menu returns with the level-8 checkpoint.
- A transient progress rollback remained and motivated later persistence research.

## V6 — safe heart setter — Superseded by V15

- Replaced the ineffective V5 constant getter with a patch at a safe-number/life boundary.
- Allowed play beyond the persisted life count in interactive testing.
- Ranking behavior still depended on the current gate implementation.

## V5 — constant unlimited-lives attempt — Rejected

- Forced an apparent life value at an unsafe layer.
- The main menu could still count down to zero and show the purchase prompt.
- A launch also reproduced the leaderboard crash, confirming that the life patch did not preserve the ranking fix correctly.

## V4 — dedicated-BSS ranking in-flight state — Superseded checkpoint

- Added dedicated writable state instead of repurposing an unrelated game function.
- Allowed only the first ranking callback during initialization.
- Passed several games and menu returns plus a two-response cold-start test.
- Exposed later re-arm and life-replenishment requirements.

## V3 — hardcoded historical identity — Accepted into V25

- Patched `BirzzleFever.GetUniqueDeviceID()` to return the 2016 save's historical application identity.
- Removed the runtime requirement for the Xposed identity module.
- Retained early ranking deduplication work.

## V2 — response-delivery ranking deduplication — Superseded

- Moved deduplication closer to `SCORE.RANKING` response delivery.
- Reduced duplicate initialization callbacks but did not model later legitimate refreshes.

## V1 — disable global ranking — Superseded

- Initial native experiment to avoid the duplicated historical global-ranking path.
- Established the leaderboard crash connection but did not yet solve full local-score lifecycle handling.

## Pre-native Xposed milestones

### Identity Spoof V1

- Hooked `GetUniqueDeviceID()` only in `com.halfbrick.birzzlefever`.
- Proved that application identity, not Android package UID ownership, determined restored-save compatibility.

### Identity Spoof V2

- Added Java connectivity hooks reporting offline.
- Retained for research; later native/package work made Xposed unnecessary.
