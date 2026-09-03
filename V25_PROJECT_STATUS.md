# Birzzle Fever offline mode: v25 project status

## Executive status

The exact V25 development APK, SHA-256 `66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05`, is functionally qualified for public release on the tested Galaxy S4 SGH-I337M running Android 4.4.2. It is an APK-only, self-seeding build that:

- needs no Xposed module, Titanium Backup, root, or manual package-UID repair for a fresh installation;
- launches with Wi-Fi and mobile data unavailable;
- hardcodes the historical application identity used by the 2016 save;
- routes game-server requests through the local offline backend;
- preserves the response-pool crash-consistency hardening;
- preserves the leaderboard/menu-transition and unlimited-play patches;
- embeds only the sanitized 26-file seed;
- reconstructs the player's leaderboard score without the historical duplicate-entry crash.

Functional release readiness is **PASS** on that tested device, cumulative with the already accepted exact-V25 fresh self-seed, 10/10 mature launches, 9/9 first-read fault cases, ranking coverage, and earlier zero-life evidence. This does not make the current debug-signed development APK the final public artifact. Dedicated public signing, the legal distribution choice, and second-device breadth validation remain separate distribution gates.

“Offline” means independent of the defunct Birzzle Fever servers and fully playable without Wi-Fi or mobile data. Blocking every analytics or operating-system network API is not a project requirement.

## Current artifacts

| Artifact | SHA-256 | Status |
|---|---|---|
| `native-patches/v25-ranking-template/BirzzleFever-1.1.2-v25-ranking-template.apk` | `66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05` | Current signed development APK |
| `native-patches/v25-ranking-template/BirzzleFever-1.1.2-v25-ranking-template-unsigned.apk` | `4f020ad389da88fe9cd007a970c9cd9401fe564d27225910930e72878ef13f6f` | Unsigned build output |
| `native-patches/v25-ranking-template/libef2d-v25-ranking-template.so` | `6f2b88586c798b924e612d14e26a18e0367101fdb29a8bd05c97b4131edaee9e` | Connectivity-independent response backend |
| `native-patches/v25-ranking-template/apktool/lib/armeabi/libbirzzle.so` | `bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae` | Gameplay, identity, ranking/menu, and unlimited-play library |
| `native-patches/v25-ranking-template/apktool/assets/birzzle_seed_v1.zip` | `654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c` | Sanitized 26-file embedded seed |
| `native-patches/v25-ranking-template/release-evidence.json` | Generated release evidence | Canonical machine-readable artifact and validation manifest |

The APK is development-signed with the existing Android debug key. Its certificate SHA-256 fingerprint is:

```text
87:B0:89:6F:00:D6:2D:61:52:4A:07:26:03:3F:C6:FC:55:36:31:61:BF:3F:70:28:83:23:35:FB:4B:E3:25:3B
```

This is not the intended public-release identity. `RELEASE_SIGNING_KEY.md` documents the release-key cutover.

The historical game identity remains:

```text
3c8bb7308c3fcb60c439224bd595c794d8f31501
```

This identity determines hashed save filenames and offline-backend identity. It is unrelated to Android's installation-specific Linux UID. A fresh self-seeded installation naturally creates files with the assigned package UID.

## Patch composition

### `libbirzzle.so`

V25 inherits the validated v15 gameplay and portability lineage:

- hardcoded historical identity, eliminating Xposed;
- ranking callback protection and common main-menu transition re-arming;
- loading-dialog cleanup for startup and return-to-menu paths;
- zero-heart `GameStart`, allowing play after the displayed life count reaches zero;
- embedded-save bootstrap support.

The main-menu life display can still show the historical count. The power-up screen and game-start path remain functional with five available lives.

### `libef2d.so`

V25 inherits the v23 response-pool lineage:

- request-zero maturity detection;
- cryptographically validated index-only mtime tolerance;
- non-destructive waiting for rejected mature indices;
- guards against an index that references a missing numbered request;
- atomic temporary index replacement;
- request-first commit ordering.

V25 additionally makes `CRequestQueue::NetworkStatusSync()` return false. This selects the game's local `CResponsePool::RequestOffline` path without requiring an associated Android network interface.

### Java and package changes

- Android network state/reachability compatibility methods report an available interface to bypass the obsolete Java startup gate.
- Birzzle Fever's GCM registration is skipped.
- The package's GCM receiver and service are removed, preventing delayed registration retries from reinitializing the game mid-session.
- `SaveBootstrap` restores exact Unix mtimes from ZIP extended timestamp field `0x5455`, including timestamps not representable by DOS ZIP's two-second resolution.
- The bootstrap asset contains exactly 26 sanitized runtime files.

## Ranking-template correction

The direct offline ranking calculator has an undocumented two-slot contract:

1. it leaves ranking item zero unchanged;
2. it updates ranking item one from the highest `POCKET.SET.tropy` request.

The first sanitized V24 seed retained only one zero-score item. The UI stayed responsive, but the calculator had no second slot and therefore displayed no score.

Adding a dummy UID was rejected: the UI correctly treated it as another player and exposed a heart-send button.

The accepted V25 template uses the historical UID for both slots, with deliberately distinct sentinel scores:

```text
item 0: scorecurrent=-1, scorehighest=-1
item 1: scorecurrent=0,  scorehighest=0
```

This preserves the calculator's second slot while avoiding the equal-score initial condition associated with the old duplicate-entry crash. On a progressed pool, item one was reconstructed as `4810` across seven ranking refreshes. The UI showed one `My Score` row, no heart button, no crash, and no softlock.

## Exact V25 validation

### Fresh APK-only self-seeding

The previous package was uninstalled before installing V25. Before first launch, neither `.birzzle_seed_v1` nor the ranking cache existed.

The user then completed:

- free Suri acquisition;
- the first normal game;
- a second game;
- three missions and a mission-class reward;
- EXP level 2 and its reward;
- the tutorial bonus game, including all coin tiles;
- the free Suri level-2 upgrade.

Observed result:

- no infinite loading animation, softlock, crash, or visual progress regression;
- initial leaderboard displayed one `My Score` row with `No Score`;
- later ranking responses displayed the earned high score;
- no heart-send button;
- response pool `-1,16`, records `0..16`;
- pool classification `CONSISTENT`;
- no semantic warnings or fatal markers;
- ranking score `257680` persisted across an automated cold restart.

Evidence:

- `native-patches/v25-ranking-template/evidence/fresh-v25-progression.log`
- `native-patches/v25-ranking-template/evidence/fresh-v25-progression-pool.json`
- `native-patches/v25-ranking-template/evidence/fresh-v25-cold-restart.log`

### Mature cold starts

The exact V25 APK passed ten of ten cold launches from the mature `-1,156` checkpoint. Every launch reached `SCORE.RANKING` and preserved:

- 980,800 coins;
- 99,870 gems;
- 3,810 EXP;
- Suri ability 10;
- Polo ownership;
- ranking score 1,017,964;
- index SHA-256 `c75e925c83ce92d7157f77306b123eb0e7e5944f3926e0d623edb55ed8813d07`;
- request-zero SHA-256 `5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2`.

No fatal marker occurred, and the response pool remained `CONSISTENT`.

Evidence: `native-patches/v25-ranking-template/evidence/mature-cold-starts/results.json`.

### First-read fault matrix

The exact V25 APK passed all nine cases:

- index mtime `+10`, `+11`, and `+60` seconds;
- missing index;
- zero-length index;
- truncated Base64/ciphertext;
- invalid AES padding;
- wrong envelope MD5;
- index referencing missing request 156.

The three mtime cases loaded directly. Every permanent/corrupt case entered a non-destructive controlled wait; force-stop, file repair, and cold launch restored the mature state. No case produced zero pocket data, sentinel-only inventory, empty quests, a request-zero overwrite, or an index collapse.

The last five cases were rerun independently after a diagnostic reboot left the phone on its keyguard. The earlier paused launches were excluded; their pools had remained intact.

Evidence: `native-patches/v25-ranking-template/evidence/first-read-faults/accepted-results.json`.

### Multi-session progression qualification

The public-release qualification repeat exercised the exact APK above on the Galaxy S4 SGH-I337M running Android 4.4.2, with package UID `10243` and no Xposed identity module:

- The offline lifetime completed three games and quit one game mid-session. Multiple power-up cancellation paths returned normally, as did every exercised UI and ranking transition. The pool advanced by 17 records, from baseline `-1,179` (180 records) to `-1,196` (197 records), with eight ranking responses.
- The connected lifetime completed seven games and quit one game mid-session. It tolerated a Wi-Fi disconnect and reconnect; upgraded Popo to level 3 with an exact `-250`-coin change; applied Extra Time and Bonus Bombs, each on the next game; progressed missions and rewards; and moved the ranking from `1017964` to `1107760` to `1192515`. Every exercised UI and ranking transition remained normal. The pool advanced by 35 records to `-1,231` (232 records), with 12 ranking responses.
- Across both lifetimes, the result was ten completions and two midgame quits. Baseline, offline, connected, and final checkpoints were all `CONSISTENT`, valid, contiguous, and warning-free. Request zero remained byte-identical at SHA-256 `5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2`; all pre-existing records remained byte-identical; and no fatal marker occurred.
- A final cold restart produced two ranking responses but added zero records. It retained 985,140 coins, 99,870 gems, EXP 6,503 at level 11 (91%), Popo level 3, Expert II with 2/6 missions, five lives on both the menu and power-up screen, and one leaderboard entry at `1192515`. Return flows remained responsive. The final index SHA-256 is `2e5b0984ddd1fdb5efa9be782ac74c6cb4045a5841ae9b9626f89309c54f5a37`; the final tail SHA-256 is `2923c49f8fc6640b81932622438802847350db16e666dd5f250835dd9f13d82a`.

The run consistently displayed five lives and successfully started games, so it did not itself reach zero displayed lives. Unlimited start at zero remains covered by accepted earlier user testing rather than by this repeat.

One daily bonus day 2 award of 200 coins appeared after a game during the connected process. The user recalls a prior bonus during an abandoned/restarted run on the same host date, but no second bonus appeared in the same connected process and none appeared merely on the final cold launch. This is recorded as a non-blocking observation, not a proven bug.

## Current device checkpoint

The final captured Galaxy S4 SGH-I337M checkpoint records:

- Android 4.4.2 with exact V25 installed;
- package UID `10243` and no Xposed identity module;
- response pool `-1,231`, containing 232 valid contiguous records;
- index SHA-256 `2e5b0984ddd1fdb5efa9be782ac74c6cb4045a5841ae9b9626f89309c54f5a37`;
- tail SHA-256 `2923c49f8fc6640b81932622438802847350db16e666dd5f250835dd9f13d82a`;
- unchanged request-zero SHA-256 `5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2`;
- 985,140 coins, 99,870 gems, EXP 6,503 at level 11 (91%), and Popo level 3;
- Expert II mission class with 2/6 missions;
- five lives on the menu and power-up screen; and
- one leaderboard entry at `1192515`.

The final cold restart added no response-pool records and preserved a `CONSISTENT`, warning-free checkpoint. Package UID `10243` is device state, not a distribution constant.

## Remaining release work

1. Test a second supported 32-bit ARM device before claiming broad device support.
2. Choose the legal distribution model: redistributable APK or user-supplied-original patcher.
3. Generate and retain a dedicated release signing key, then rebuild/re-sign the immutable public artifact.
4. Publish installation, checksum, troubleshooting, rollback, and provenance material.

The root-induced 17-second missing-index diagnostic remains outside the ordinary-use release gate. It requires external root interference that the app's mutex-serialized, atomic writer does not create.

## Evidence index

- Machine-readable V25 manifest: `native-patches/v25-ranking-template/release-evidence.json`
- Public-release qualification repeat: `native-patches/v25-ranking-template/evidence/public-release-qualification-repeat-20260901T231648Z/`
- Qualification operator ledger: `native-patches/v25-ranking-template/evidence/public-release-qualification-repeat-20260901T231648Z/operator-ledger.json`
- Qualification checkpoint comparisons: `native-patches/v25-ranking-template/evidence/public-release-qualification-repeat-20260901T231648Z/comparisons/`
- Final qualification manifest: `native-patches/v25-ranking-template/evidence/public-release-qualification-repeat-20260901T231648Z/03_final_cold_restart/manifest.json`
- Roadmap: `V21_ROADMAP.md`
- V24–V25 regression history: `V24_V25_REGRESSION_HISTORY.md`
- Tentative post-release save rewrite: `FUTURE_OFFLINE_SAVE_FILESYSTEM_REWRITE.md`
- Root cause: `PROGRESS_REGRESSION_ROOT_CAUSE.md`
- Patch history: `PROGRESS_REGRESSION_PATCHES.md`
- Minimal data contract: `MINIMAL_PUBLIC_SAVE.md`
- Signing procedure: `RELEASE_SIGNING_KEY.md`
- V25 mature harness: `stress_v25_mature_cold_launch.py`
- V25 first-read harness: `stress_v25_first_read_faults.py`
- Response-pool analyzer: `reconstruct_response_pool.py`
- Save analyzer: `analyze_birzzle_save.py`
