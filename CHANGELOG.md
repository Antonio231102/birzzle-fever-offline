# Changelog

This chronology was reconstructed from preserved patch scripts, milestone directories, checkpoint notes, and validation summaries. Git was initialized after the research; this file records milestone history without fabricating retroactive commits.

Labels:

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
