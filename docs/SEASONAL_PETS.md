# Rudy and Eve: offline Christmas event and original research

## V43 offline implementation

The offline event is available without a calendar deadline until **both Rudy and Eve have been claimed**, based on the frozen V42 release.

| Pet | Cumulative score | Mystery Boxes opened | Coins collected |
|---|---:|---:|---:|
| **Rudy, ID 8** | **100,000,000** | **25** | **25,000** |
| **Eve, ID 9** | **200,000,000** | **50** | **50,000** |

All three goals are required for each pet. Both pets share the existing persistent event counters; earning Rudy does not reset progress toward Eve, and Eve does not require Rudy's ownership. Counters continue beyond Rudy's thresholds and saturate at Eve's. Pending and applied progress contribute consistently. Friendship Points no longer contribute to Eve's event eligibility; unrelated friendship functionality is unchanged.

The revised normal-goal APK is FruitSpy-signed under `native-patches/v43-offline-christmas/normal-goals-25-50/`, with the same release certificate as frozen V42. Its embedded ARM goals, claim-completion behavior in both orders, post-claim ordinary artwork, and exact inventory transaction-ID selection were exercised against the signed packaged libraries. A second legitimate inventory shape with another pet and two distinct full-width IDs also passed native replay. The former reduced-goal S20 test APK retained separate thresholds; no distinct array-index bounds guard is asserted. **Fresh-install deployment without preserving saves is now complete on S4 and S20:** both installed APK hashes match the checkpoint, and the old private app-data directories were removed before installation. Startup testing of this normal-goal build remains pending on both devices; see `device-snapshots/v43-fruitspy-normal-goals-fresh-install/deployment.json`.

V43 retains event ID 1 and both catalog entries, but activity now depends on claimed ownership. The date caption is **“Until both claimed.”** Eve uses Rudy's mission presentation: Mystery Boxes, score, then coins; the same heading, icons, separators, fonts, colors, and alignment; comma-formatted remaining amounts or the original localized completion message. The small current/target counters and separate progress bar are retired. Free native claims, Rudy's ability, and Eve's reward distribution remain unchanged. The original event-mission profile layout and save/apply routines are retained; Eve's reward timer is corrected separately below.

Build with `python build_v43_offline_christmas.py`; authored native sources are under `native-patches/v43-offline-christmas/`. The latest inventory-ID correction passes **40 focused host regressions**, including five native replay cases and a loader-layout regression; both signed normal/reduced APKs replay the captured Rudy equip request correctly. The purchase generator uses a 64-bit server-adjusted timestamp, but the inherited offline consumer narrowed it through ARM32 `atoi`. Selection and inventory-update matching now preserve exact IDs as strings, without changing Christmas logic or saved IDs. The first correction exposed an immediate Android startup failure from its relocated ELF header table; the builder now emits the required explicit `PT_PHDR`. The rebuilt reduced APK is installed in place on S20 with APK/native hashes, unchanged UID, disabled debugging, and 222 known file metadata entries verified. **Operator-confirmed S20 startup, selection persistence, switching pets, gameplay with Rudy, and upgrade isolation pass.** Eve was claimed successfully and the Christmas event disappeared immediately. Eve is not equippable; all other pets are already unlocked, so acquisition followed by equipping a newly owned pet is unavailable on this save and remains host-tested only. No save reset is required. No S20 backup or restoration was performed for these corrections. S4 remains on the previous artwork build, where ordinary backgrounds after closure were confirmed. Earlier S4 tests qualified both unlocks, Rudy's level-30/equipped persistence, Eve's first payout/countdown, and six operator-controlled clock/lifecycle checks. The latest-build operator report additionally confirms natural six-hour gift renewal, non-stacking after waits of 12 or more hours, and continued rewards after both claims and event closure. These manual passes close the functional expiry/payout check without claiming instrumented timing. See [build instructions](BUILDING.md#v43-offline-christmas-test-build) and [inventory verification scope](TESTING.md#inventory-transaction-id-correction--s20-focused-checks-passed).

### Event completion

- Meeting the mission goals only enables a claim. Closure requires the original `CPet::IsMyPet()` check to succeed for **both** IDs 8 and 9; positive inventory levels are the ownership authority. Either claim order works.
- The event remains active while either pet is absent/unclaimed, including during inventory loading. Existing saves with both pets owned close it without requiring retained mission counters or a new completion flag.
- The normal successful-claim callback hides the dialog and opens pet inventory. Subsequent activity checks disable event presentation/progress; queued dialog opens are suppressed, existing banner actors are hidden, and loaded event images still receive cleanup after closure.
- Catalog classification is kept separate from activity. Both owned pets remain available, and closing the event neither resets Eve's cooldown nor blocks future gifts. No ownership, mission, journal, or timer profile is rewritten by the activity check.
- Seasonal background, stage, landscape side textures, and winter overlays reconcile at the inventory-ready main-menu handoff and post-claim pet-inventory transition. The native background-only repaint now selects ordinary textures after closure; gameplay/UI controls are not reconstructed. A transient byte in the event manager's existing padding tracks the loaded theme, avoiding repeated repainting and adding no save field. V41's scene-rearm hook remains in the call chain.

### Eve reward cooldown

The original unlock callback stores `time(NULL) - 60` to make Eve's first gift immediately available. The getter subtracts `CHSPManager::GetCurrentTime()`, a different, server-adjusted clock that can be zero offline. Actual original ARM execution reproduced **497,282 hours**. This is a clock-domain error, not an intended reward interval.

`v43_eve.c` replaces the reward timer's load/save, initialization, remaining-time, and claim transitions:

- The first gift is immediately available. Each successful handoff to the original payout starts a **21,600-second / six-hour** cooldown; rewards do not accumulate into multiple pending gifts.
- Eligibility uses Linux **`CLOCK_BOOTTIME`**, including suspend. App closure/relaunch in the same phone boot preserves elapsed time. Device calendar and offline server time are not used.
- A persisted boot UUID detects phone reboots even when the new uptime exceeds the old uptime. On a different boot, resume the last saved remaining duration. Powered-off time and unobserved elapsed time after the previous boot's last checkpoint are not credited. While the timer is queried, checkpoints occur at most once per minute.
- The cooldown is written and read back before the original payout is allowed. Unavailable trusted-clock/boot identity, failed storage, or corrupted state must not yield an extra reward. The original reward selection and cache invalidation remain in use.
- Manual date/time changes cannot advance this timer. This is **not** protection against root, executable modification, save editing/restoration, or app-data deletion; securely crediting powered-off time requires an external trusted clock.

The existing `petPresent.dat_9` path now stores an **EVE1** SEED-encrypted profile: 52 plaintext bytes / 64 ciphertext bytes. Fields are little-endian magic `0x31455645`, sampled boot seconds, remaining seconds, 36 ASCII boot-UUID bytes, and an FNV-1a integrity checksum over the preceding 48 bytes. No wall-clock mtime gate is used. Legacy 24-byte profiles migrate once: the original `saved timestamp - 60` first-gift marker remains due; other legacy/invalid deadlines conservatively start one six-hour cooldown. Pet ownership, levels, mission counters, and the response journal are not rewritten by migration.

The sections below describe the **original/V42 implementation**, not V43's approved requirements.

## Finding

Rudy and Eve are implemented **Christmas-event pets**, not ordinary shop purchases and not merely unused names. Rudy is pet ID **8**; Eve is ID **9**. The client has event missions, claim buttons, ownership handling, abilities, and artwork for them. Eve nevertheless has an unfinished description: `PET_DESC_TYPE_EVE` is Korean `제작 중` (“in production / under construction”). That placeholder does not erase her implemented gift logic, but the evidence does not establish a fully polished or historically released experience.

The earlier purchase-test plan incorrectly treated five localization names as five ordinary purchasable pets. The normal roster ends at ID **5**. Starting from owned IDs 0–2, Penny (4), Holly (3), and Pow (5) were the three missing normal pets. Their purchases passed; Rudy and Eve's event acquisition remains untested. See [purchase-test results](TESTING.md#v42-legitimate-remaining-pet-purchases--three-normal-purchases-passed-seasonal-claims-blocked).

## Why they are absent from the menu

The high-currency test fixture's cached `submarinevariable.dat` contains:

| Field | Value | Meaning established by the client |
|---|---:|---|
| `PetEventID` | `0` | Event disabled |
| `PetEventEndDate_YYMMDD` | `150104` | Configured end-date display: 2015-01-04 |

`CConfigInfo::LoadServerValues()` loads these into safe-number fields at offsets `0x740` and `0x760`. `CPetEventManager::GetEventPetCount()` returns two pets for event ID **1**, otherwise zero. `IsEventInProgress()` tests whether the event ID is nonzero; it does not compare the current date in that function. The historical end-date field must not be mistaken for proof that changing the device clock would enable the event.

When the event is inactive, `CPetManager::SetMyPetData()` removes **unowned event pets** from its in-memory list. Already-owned event pets are retained. With event ID zero, `IsEventPet()` classifies IDs greater than 7 as event pets. This explains the operator's report that neither Rudy nor Eve appears in the selection menu; it is not evidence that the pet-tutorial fix blocked a normal purchase.

Nine relevant functions, including event gating, roster filtering, claim handling, and both abilities, are byte-identical between V42 and the untouched original Titanium APK. IDs **6 and 7** are separate entries explicitly removed by `InitPetInfo()`; they are not Rudy and Eve.

## Unlock criteria and acquisition cost

These are the **implemented client requirements for an active Christmas event**, not an assertion that the event can currently be completed through the offline build.

| Pet | Requirements | Acquisition charge |
|---|---|---|
| **Rudy, ID 8** | Accumulate **20,000,000 score**, open **10 Mystery Boxes**, and collect **3,000 coins** in the event's mission counters; all three required | **0 coins / 0 gems** through the event claim button |
| **Eve, ID 9** | Accumulate **300 qualifying Friendship Points** in the event's mission counter | **0 coins / 0 gems** through the event claim button |

Rudy's Mystery Box counter is incremented by `CMysteryBoxOpenDialog::ShowDialog()`. His score and coin counters are updated by post-game processing, with bonus-game coins also feeding the coin mission. These are cumulative event objectives, not a requirement to spend 3,000 coins or reach 20 million in one game.

Eve's qualifying Friendship Points come from **inviting friends, sending Hearts, and receiving Hearts**. `CFriendshipPointManager::AddPoint()` feeds mission type 3 only for these three action types; level-up sharing and ranking-change sharing do not feed it. This is an **earn-points** requirement, not a 300-point purchase. Her completion predicate does not require Rudy to be owned.

Mission types 0–3 have thresholds `[20000000, 10, 3000, 300]`. Rudy's completion predicate includes pending mission progress; Eve's predicate checks applied progress. The claim buttons depend on mission completion or existing ownership. Both unowned-pet claim branches call `CHSPManager::BuyInventory()` with item ID 8 or 9, ability `"1"`, both currency amounts zero, and the direct-request flag set.

**Do not quote 99,999 coins or gems as their unlock cost.** `CPet::GetBuyCost()` returns 99,999 for either pet in either ordinary-shop currency mode, but that is the ordinary-shop fallback. The actual event claim path does not use that price and passes zero currency amounts.

## Abilities

### Rudy

- Attribute type **11**, localized as **“Bonus Items!”**
- In-game explanation: **“Collect Bonus Keys and Mystery Boxes faster!”**
- Native attribute rate: **+15% at level 1**, increasing to **+100% at level 30**.
- The gameplay initializer reads this equipped-pet attribute, converts the percentage to a fraction, and passes it to `CFortuneManager::ChangeForturnRate()`.
- These are bonus-rate values, **not a guarantee that a box/key drops on every action**.
- Flavor text: “Rudy, Rudolph’s cousin, likes to give out more presents when Santa’s not watching.”

### Eve

- Attribute type **12**, localized as **“Get rewards!”**
- In-game explanation: **“Collect Gems, Coins or Hearts every %d hours!”**
- `SettingPresentInfo()` enables presents for ID 9 and sets the interval to **21,600 seconds: six hours**.
- `GetPresentInfo()` selects and caches one reward; `ReceivePresent()`, `ReceivedPresent()`, and load/save methods implement collection and timer state.

| Random selector (`lrand48() % 100`) | Reward | Nominal share |
|---|---|---|
| 0–49 | **200–500 coins**, inclusive | **50%** |
| 50–89 | **1–3 hearts**, inclusive | **40%** |
| 90–99 | **1 gem** | **10%** |

**Correction:** the earlier research swapped the heart and gem labels and incorrectly called the generator `rand`. Native enum values are `0 = heart`, `1 = gem`, `2 = coin`. The recheck executed all 100 selector outcomes in the installed APK's ARM code and followed the original payout into its `MESSAGE_Post(10068, ...)` packet, whose first three fields are heart, coin, and gem. `OnMessageHandler` → `CHSPManager::SetHeartCount` → `CPocket` serialization independently establishes those field names. Quantity checks cover every coin amount 200–500, hearts 1–3, and the fixed one-gem outcome.

Two consecutive heart rewards have nominal probability **0.40 × 0.40 = 16%** (about 1 in 6.25 pairs), assuming approximately uniform independent draws. Once one heart reward has occurred, the nominal chance that the next reward also contains hearts is **40%**. The reported two-heart gift and subsequent heart reward are consistent with these rates.

The main-loading path contains `srand48(time(NULL) + getpid())`; gameplay and animation routines share the generator. The percentages describe selector ranges, not an empirical frequency guarantee for two device samples. A displayed reward is cached, repeated preview does not reroll it, and successful claim clears that cache. The recheck verified cache invalidation and found the selector plus original payout body byte-identical to frozen V42; no reward-rate code was changed. Evidence: `native-patches/v43-offline-christmas/cooldown-test/eve-reward-research.json` and `reward-wallet-mapping.txt`. Gifts remain non-stacking.

## Appearance

- **Rudy:** rounded golden-orange bird with green eyes, a bright red nose, pale head tuft, and red/pink reindeer antlers. Separate **C, B, A, and S** portraits show increasingly developed antlers and changes in expression.
- **Eve:** white/cream bird with orange eyes and a small brown curl, a large **red bow with gold trim**, and a red gift-box lower body with multicolored ribbons. One dedicated Eve portrait is present.

The APK assets are `rudy_C_RETINA.png`, `rudy_B_RETINA.png`, `rudy_A_RETINA.png`, `rudy_S_RETINA.png`, and `eve_RETINA.png`. Their decoded contents were visually inspected. The Christmas event also has its own banner/icon atlas.

[Open the locally extracted artwork contact sheet](../device-snapshots/v42-legitimate-pet-purchases-20260922T041904Z/rudy-eve-research/rudy-eve-artwork.png). These extracted assets remain local evidence, not newly distributed game assets.

## Evidence and verification limits

Primary source: the actual ARM/Thumb binary, localization, artwork, and saved configuration—not guesses from names or generic web descriptions. Public searches did not provide reliable Rudy/Eve-specific release documentation; **historical server availability is not established** by this investigation.

Key `libbirzzle.so` virtual addresses:

| Function | Address |
|---|---|
| `GetLastNormalPetId` / `GetEventPetType` | `0x11b6a8` / `0x11b6ac` |
| `GetMissionObjectiveRate` / `IsAllMissionClear` | `0x11b6e8` / `0x11b724` |
| `GetEventPetCount` / `IsEventPet` / `IsEventInProgress` | `0x11b9dc` / `0x11ba88` / `0x11bb30` |
| `CPetManager::SetMyPetData` | `0x10f7e4` |
| `CPet::SettingAttribute` / `SettingPresentInfo` | `0x110da8` / `0x110434` |
| `CPet::GetPresentInfo` / `GetBuyCost` | `0x1114a0` / `0x111624` |
| `OnEventDialogButtonClicked` | `0x0bab6c` |
| `CFriendshipPointManager::AddPoint` | `0x11a8d0` |
| `CConfigInfo::LoadServerValues` | `0x17790c` |

Off-device Unicorn execution of the actual native instructions verified event IDs and gates, mission thresholds and completion boundaries, the 99,999 shop fallback, Rudy's level-dependent attribute, Eve's six-hour interval, and reward-selector boundaries. Only external dependencies needed for those original calls were supplied: a synthetic configuration-object pointer, deterministic `lrand48`, integer division/remainder, and IEEE-754 float addition. The later reward recheck additionally executes payout construction with allocation/formatting/message-post boundaries supplied. This is native-function evidence, not a statistical device-frequency study; subsequent physical qualification is recorded above and in `TESTING.md`.

Local evidence root: `device-snapshots/v42-legitimate-pet-purchases-20260922T041904Z/rudy-eve-research/`. It contains `native-probe-results.json`, `original-comparison.json`, `event-config.json`, `localization-evidence.json`, `event-call-sites.json`, disassembly, and extracted artwork.

- V42 APK SHA-256: `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`
- V42 `libbirzzle.so` SHA-256: `087f0742624d3e57ba4277adf16685193556bc02ff3a6adf4904726e51879d56`
- Untouched original compressed APK SHA-256: `223743309397fc35bcedfe45ffc8891e6a1f2787481745390dbb524b876c9a15`
- Examined configuration cache SHA-256: `02312d46dccf48eb3249eb11dc9563f29fe0a2e2265006b24d9714429d9c514c`

No event flag, mission counter, ownership entry, price, APK, or native library was modified on the device. The original save was restored and verified before this research; capture is stopped and the game is force-stopped. The separate checkpoint after Penny/Holly/Pow retains all six normal pets, 924,800 coins, 99,810 gems, and the consistent 166-record pool `-1,165`.
