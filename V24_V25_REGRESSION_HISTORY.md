# Birzzle Fever V24–V25 regression history

## Purpose

This document records two issues encountered while converting the V23 development build into the connectivity-independent, sanitized-seed V24/V25 lineage:

1. startup failed with network error 12 when no Android network interface was available;
2. the V24 leaderboard became responsive and crash-free but stopped displaying the player's saved high score.

The chronology matters: **network error 12 was inherited from V23, not introduced by V24**. The accepted network fix landed during V24 and was carried unchanged into V25. The missing-score regression was introduced by the interaction between V24's direct offline route and its one-entry sanitized ranking seed; V25 corrected that seed contract. V25 is the first consolidated candidate containing both accepted solutions.

## Relevant artifacts

| Build or asset | SHA-256 | Role |
|---|---|---|
| `native-patches/v24-connectivity-independent/BirzzleFever-1.1.2-v24-connectivity-independent.apk` | `f475e6c0e5e7819bb536df800507eba285cf0f0be11e7292b2e9d5186aeba0c5` | Final preserved V24 development APK |
| `native-patches/v25-ranking-template/BirzzleFever-1.1.2-v25-ranking-template.apk` | `66006ed20a308d52660bea5154a513a64d07f4d7f8d725bd5f02077c70168b05` | Current V25 development candidate |
| V24 `assets/birzzle_seed_v1.zip` | `4687362618ddfab6e94b9ca13c04e6ea17c87a5109fb5d5f773f1ae661be6007` | Sanitized seed with one ranking entry |
| V25 `assets/birzzle_seed_v1.zip` | `654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c` | Sanitized seed with stable two-entry ranking template |
| V24/V25 `libef2d.so` | `6f2b88586c798b924e612d14e26a18e0367101fdb29a8bd05c97b4131edaee9e` | Identical connectivity-independent response backend |
| V24/V25 `libbirzzle.so` | `bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae` | Identical gameplay, identity, ranking/menu, and unlimited-play library |

The identical native-library hashes establish that the accepted V25 ranking correction did not replace or weaken the V24 network and response-pool patches.

## Regression 1: network error 12 without an active interface

### Symptom

V23 could replay cached Hangame responses without reaching the defunct game servers, but a cold launch with Wi-Fi and mobile data unavailable still displayed:

```text
Network
Failed to connect to the game server.
[code:12]
```

Evidence: `native-patches/v23-request-first-index/stage-a-virgin-initialization/connected-retry.png`.

Associating Wi-Fi allowed the same local save and local response backend to initialize. This established an important distinction:

- server independence was already working;
- zero-network-interface startup was not.

### Root cause

Startup had two separate connectivity decisions:

1. Java-facing methods `BirzzleFever.Network_GetState()` and `BirzzleFever.Network_IsReachable()` represented Android connectivity to the application layer;
2. native `Enfeel::CRequestQueue::NetworkStatusSync()` returned `HangameWrapper::prevNetworkStatus()` and selected the request-queue route.

Changing only one layer was insufficient. The Java gate could accept startup while the native queue still selected behavior based on stale or unavailable network state.

The V23 native implementation at `libef2d.so` address/file offset `0x12b858` was:

```asm
push {r4, lr}
bl   HangameWrapper::instance()
bl   HangameWrapper::prevNetworkStatus()
pop  {r4, pc}
```

### Rejected V24 approaches

#### Java-only optimistic connectivity

The Java methods were changed to constant success values:

```smali
Network_GetState()     -> 1
Network_IsReachable()  -> true
```

This bypassed the obsolete Java availability check but did not control native request routing. The build is preserved under:

`native-patches/v24-connectivity-independent/rejected-java-only-network-gate/`

#### Forcing the native connected route

A second experiment made the native status appear connected. That selected the connected request path, which was the wrong invariant for a game whose servers no longer exist. The preservation goal was not to fabricate a usable network; it was to select the built-in local response calculator deterministically.

The rejected build is preserved under:

`native-patches/v24-connectivity-independent/rejected-native-connected-gate/`

### Accepted V24 solution

The accepted build kept the Java compatibility values but changed native `CRequestQueue::NetworkStatusSync()` to return false:

```asm
0x12b858: movs r0, #0
0x12b85a: bx   lr
```

Replacement bytes:

```text
00 20 70 47
```

In `CRequestQueue::requestStart()`, false selects `CResponsePool::RequestOffline`, which serves `SERVER.INIT`, `POCKET.LOGIN`, `POCKET.GET`, `SCORE.RANKING`, and the other supported commands from the local response system.

Evidence from the final V24 offline launch:

- local `SERVER.INIT` response at `native-patches/v24-connectivity-independent/evidence/fresh-apk-only-offline-launch.log`;
- local `POCKET.LOGIN` response in the same log;
- local `SCORE.RANKING` responses in the same log;
- no network-error-12 path.

This network fix is already present in final V24. V25 inherits the same `libef2d.so` byte-for-byte.

### Related V24 GCM retry issue

An obsolete GCM registration retry later caused a separate mid-tutorial reinitialization while testing the new offline startup path. The retry produced `SERVICE_NOT_AVAILABLE`, restarted the platform initialization sequence, and left a loading dialog active.

The accepted V24 package therefore also:

- supplies an empty GCM registration ID during `PostInitialize()`;
- skips registration;
- removes Birzzle Fever's GCM receiver and service declarations from `AndroidManifest.xml`.

The rejected intermediate build and log are preserved under:

`native-patches/v24-connectivity-independent/rejected-gcm-retry-midgame-reinit/`

This was a separate asynchronous initialization bug, not the cause of either network error 12 or the missing leaderboard score.

## Regression 2: V24 leaderboard displayed no saved score

### Symptom

After the connectivity-independent V24 build reached the main menu:

- the loading animation cleared;
- the UI remained responsive;
- no leaderboard crash or softlock occurred;
- the leaderboard displayed no personal high score despite completed games and valid `POCKET.SET.tropy` records.

The captured V24 cold-restart response contained only one zero-score ranking item:

```json
{
  "message": "SCORE.RANKING",
  "ranking": [
    {
      "scorecurrent": "0",
      "scorehighest": "0",
      "uid": "3c8bb7308c3fcb60c439224bd595c794d8f31501"
    }
  ]
}
```

Evidence: `native-patches/v24-connectivity-independent/evidence/fresh-manual-cold-restart.log`.

The response pool itself was valid and contained score-bearing requests, including `POCKET.SET` records with `tropy=230` and `tropy=4810`. The missing display was therefore not progression loss.

### How V24 introduced the regression

The historical ranking cache had duplicate zero-score entries. Earlier testing connected those identical entries with the old intermittent leaderboard crash, so seed sanitization reduced the cache to one entry.

That change appeared reasonable when viewing the response as ordinary JSON, but V24's direct `CResponsePool::RequestOffline` route exposed an undocumented contract in `COfflineResponseCalc::calcRanking()`:

1. ranking item zero is retained as a sentinel/template item;
2. ranking processing begins with item one;
3. item one is updated from the highest recorded `POCKET.SET.tropy` value.

V23 evidence shows the expected calculated shape after a score of 2,580:

```text
item 0: scorecurrent=0
item 1: scorecurrent=2580
```

Evidence: `native-patches/v23-request-first-index/stage-a-virgin-initialization/restart.log`.

With only item zero in the sanitized V24 seed, the calculator had no writable second slot. It returned a valid but permanently zero ranking response. Thus the regression required both V24 conditions:

- deterministic direct-offline ranking calculation;
- removal of the second template item.

The V24 ranking cache entry was:

```text
files/d1fbe32e12b1a9d5fda79abf89e747f2
size: 728 bytes
SHA-256: b12cfb2554a4eb1fc60f02489b7ff9d9b326d74323c3ac2da5755139e0819800
```

### Rejected repair: dummy UID

The first controlled repair restored two ranking slots but assigned item zero a dummy UID while leaving item one on the historical UID.

Result:

- both entries remained at score zero in the observed response;
- the UI treated the dummy entry as another player;
- it displayed an unnamed ranking row and exposed a button to send that “player” a heart;
- the personal score still did not appear.

Evidence: `native-patches/v24-connectivity-independent/evidence/ranking-two-distinct-uids.log`.

This proved that ranking-item identity is part of the UI contract. A structurally valid two-item array was not sufficient.

### Accepted V25 solution

The accepted template retains two entries with the historical UID but prevents the unsafe identical-zero initial state:

```text
item 0:
    uid          = historical UID
    scorecurrent = -1
    scorehighest = -1

item 1:
    uid          = historical UID
    scorecurrent = 0
    scorehighest = 0
```

The distinct sentinel scores avoid an initially equal pair while preserving the calculator's second writable slot and the UI's `My Score` identity.

On the progressed test pool, every observed ranking refresh produced:

```text
item 0: scorecurrent=-1
item 1: scorecurrent=4810
```

Observed behavior:

- correct `My Score` label;
- score displayed;
- no heart-send button;
- loading animation cleared;
- UI remained responsive;
- no crash or softlock across seven observed ranking responses.

Evidence: `native-patches/v24-connectivity-independent/evidence/ranking-two-same-uid-distinct-score.log`.

The corrected encrypted ranking entry is:

```text
size: 1088 bytes
SHA-256: cf8510fa76cd64cb9576fca733714561f07b67bf4a134293f8461d0c516c280f
```

V25 embeds it in the sanitized 26-file seed. No native-library change was required between final V24 and V25.

## V25 validation of the combined solution

A clean V25 installation began without a seed marker or pre-existing ranking cache. The user completed:

- Suri acquisition;
- three games;
- three missions and a mission-class reward;
- EXP level 2 and its reward;
- tutorial bonus mode;
- Suri's free level-2 upgrade.

Results:

- offline startup succeeded;
- initial leaderboard displayed one `My Score` row with `No Score`;
- earned scores subsequently populated the same personal row;
- no heart-send button appeared;
- no loading softlock, crash, or visual progress regression occurred;
- response pool remained `CONSISTENT` at `-1,16`;
- ranking score `257680` persisted across cold restart.

The exact V25 APK subsequently passed:

- ten of ten mature cold starts;
- all nine first-read fault cases.

Canonical evidence:

- `native-patches/v25-ranking-template/evidence/fresh-v25-progression-pool.json`
- `native-patches/v25-ranking-template/evidence/fresh-v25-cold-restart.log`
- `native-patches/v25-ranking-template/evidence/mature-cold-starts/results.json`
- `native-patches/v25-ranking-template/evidence/first-read-faults/accepted-results.json`
- `native-patches/v25-ranking-template/release-evidence.json`

## Lessons and preserved invariants

1. **Server independence and interface independence are different properties.** Cached responses do not help if an earlier Java or native gate refuses startup.
2. **Select the offline path directly.** Pretending the dead service is connected chooses the wrong control flow and obscures fallback behavior.
3. **Cached response arrays may be executable templates.** Removing apparent duplicates can violate undocumented positional contracts.
4. **Ranking UID and slot position both matter.** A dummy identity changes UI semantics even when the JSON remains structurally valid.
5. **Use distinct sentinels rather than identical invalid entries.** V25 preserves both required slots without restoring the old equal-zero condition.
6. **Keep network and ranking fixes independently verifiable.** V24 and V25 have identical native-library hashes; the V25 fix is isolated to the ranking seed template.
7. **Preserve rejected builds and logs.** The Java-only, forced-connected, duplicate-ranking, dummy-UID, and GCM-retry experiments explain why the final implementation is intentionally narrow.
