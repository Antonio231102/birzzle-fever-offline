# Birzzle Fever persistence-layer precedence

## Core model

Birzzle Fever does not load progression from one canonical save object. It combines four layers:

```text
1. cached 2016 offline responses
2. numbered response-pool replay
3. local SEED-encrypted manager profiles
4. live scene/manager objects and SafeNumbers
```

The winning source depends on domain and lifecycle stage.

## Startup order

Runtime profile diagnostics show local CProfile files being read before the main offline pocket/inventory/ranking responses. The broad startup sequence is:

```text
load local profiles
    -> initialize local managers/SafeNumbers/tutorial flags
    -> SERVER.INIT / POCKET.LOGIN
    -> INVENTORY.LIST
    -> POCKET.GET
    -> SCORE.RANKING
    -> scene consumes resulting state
```

This permits local state to validate or override selected incoming fields after the response pool has calculated them.

## Domain precedence

### Experience

Sources:

```text
exp.dat Safe32
response-pool pocket.set replay
cached POCKET.GET/SET response
live CExpLevelManager
```

Observed precedence with v19 guards:

1. `exp.dat` loads into the local authoritative manager.
2. response-pool replay calculates incoming experience.
3. the pocket guard compares incoming experience with the loaded local SafeNumber.
4. a lower incoming value is replaced with the local value.

Natural regression evidence:

```text
exp.dat:                  2670
response-pool POCKET.GET: 0
consumer result with guard: clamped toward 2670
```

Without the v19 clamp, a zero response can overwrite the live pocket object even though `exp.dat` still contains the older value.

### Coin and gem

Primary accumulated source is response-pool `pocket.set` replay. Local authoritative SafeNumbers in the cash manager provide consumer-side guard values after startup.

`pocket.dat` is an additional serialized snapshot/seed, but later request deltas determine reconstructed totals.

### Pets and inventory

Pet ownership is reconstructed from response-pool inventory requests:

```text
inventory.buy
inventory.update
inventory.use
```

The v19 inventory guard only protects an already-loaded pet set from a shorter incoming table. It cannot reconstruct pets if startup itself begins with an empty pool.

No decoded local proprietary profile has been shown to contain the complete pet-acquisition history.

### Quests and missions

Two layers coexist:

```text
POCKET.LOGIN queststatus / response-pool quest.update.status
quest_progress.dat_<UID> local three-slot quest profile
```

Response-pool history determines server-style quest status and quest level. The local quest profile retains current quest slot selection and selected progress fields.

When they disagree, the game can enter a hybrid state: server-style quest history may reset while local mission choices/tutorial presentation remain from a later session.

### Tutorial state

Tutorial state is primarily local:

```text
tuto.dat_<UID>
new2profile.dat
scene-local one-shot flags
```

These files survived several response-pool experiments, explaining why completed tutorial flags could coexist with reset account progression.

### Classic/game history

`classic_stage_save.dat` retains a fixed 18-slot local history and cumulative counter. It is updated at game completion independently of later quest and menu response requests.

### Bonus and selection state

```text
bonusgame.dat_<UID>
bonus.dat
select.dat
```

These are local manager profiles written on bonus/power-up transitions. They can survive or advance independently of pocket/quest replay.

### Ranking

Ranking uses cached response data plus calculated response-pool score history. UI callback state is an additional independent layer. This is why ranking crashes/softlocks could occur without being the source of the global regression.

## Original 2016 bootstrap precedence

The untouched 2016 backup has:

- static cached responses;
- `pocket.dat` and local profiles;
- no response-pool index;
- no numbered response records.

Therefore initial startup legitimately uses cached/static data. The first persisted offline action initializes the response pool. Later progression increasingly depends on the numbered history.

## Hybrid-backup observations

Earlier bisection tests combined 2016 and level-8 data. The observed state retained:

- later tutorial flags;
- bonus-mode state;
- later mission selection/progress;

while much of the account progression resembled the 2016 state.

This is expected when local profiles come from the later save but cached responses or response-pool authority come from the earlier save.

## Practical precedence table

| Domain | Primary reconstruction source | Local/profile fallback or override |
|---|---|---|
| Coin/gem | response-pool pocket replay | cash-manager SafeNumbers; `pocket.dat` seed |
| Experience | response-pool pocket replay | `exp.dat` Safe32; v19 clamp |
| Hearts | pocket replay and local heart timing | `pocket.dat`; unlimited-life patch affects permission to start |
| Pets | response-pool inventory records | already-loaded inventory protected by v19 guard |
| Quest status | response-pool quest records / login | `quest_progress.dat` slot state |
| Tutorials | local profiles | `tuto.dat`, `new2profile.dat` |
| Classic history | local profile | `classic_stage_save.dat` |
| Power-up selection | local profile | `select.dat` |
| Bonus keys | local profile | `bonusgame.dat` |
| Ranking | cached/calculated score response | scene/callback generation state |

## Remaining precedence questions

Still requiring targeted mutation tests:

- whether `pocket.dat` ever overrides a valid mature response pool after startup;
- exact quest field precedence for each of the three local slots;
- which `new2profile.dat` flags are copied before or after login;
- whether local profile saves occur before every corresponding response callback;
- pet state behavior when a valid local inventory is paired with missing acquisition requests;
- exact behavior without v19 consumer guards.

## Evidence

```text
BIRZZLE_PROPRIETARY_PROFILES.md
POST_GAME_COMMIT_ORDER.md
device-snapshots/2026-08-29-level8-regression-state-verification/verification.log
analysis-backup-compare/trial-*.tar.gz
native-patches/v20-request-index-retention/profile-diagnostic/profile-load.log
```
