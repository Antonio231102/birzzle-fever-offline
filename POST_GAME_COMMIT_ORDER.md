# Birzzle Fever post-game persistence order

## Scope

This document maps the observed and disassembled write order for one completed game, its quest updates, and the subsequent main-menu refresh. It distinguishes response-pool commits from local manager-profile saves.

## Response-pool transaction order

`CResponsePool::SetRequest` at `libef2d.so:0x131D58` has two independent `FileWorker::WriteContent` calls. Their effective order is version-sensitive:

- the original/intended and current v23 order writes the numbered request record `MD5(UID + "REQUESTPOOL_" + next_index)` first, then commits `MD5(UID + "REQUESTPOOLINDEX")`;
- v22's atomic-index integration wired the existing data/path register pairs in the opposite order, committing the index before the numbered record;
- v23 swaps four two-byte Thumb register moves so the numbered record is durable before the index advertises it.

Under v23, a crash between the writes creates an orphan request beyond the previous valid index. Stage E proved that the next launch can safely adopt that complete record. The two writes are still not one filesystem transaction; v23 makes their failure order safe rather than making them atomic as a pair.

## Natural level-8 sequence

Captured log chronology:

| Time | Operation | Pool index/record consequence |
|---|---|---|
| `22:38:21.891` | `pocket.set`, `GameStart` | request 112 |
| `22:39:55.482` | `pocket.set`, `UploadPocket`, `coin=60`, `exp=170` | request 113 |
| `22:39:56.173` | completed-game pocket response | reconstructed `coin=983470`, `gem=99870`, `exp=2670` |
| `22:40:18.725` | `quest.update.status`, quest 30 | request 114 |
| `22:40:21.758` | `quest.update.status`, quest 50 | request 115 |
| `22:41:05.110` | menu `POCKET.GET` | first zero-history response |
| `22:41:20.865` | next `GameStart` | original code overwrote request 0 and index as `-1,0` |

## Local-profile write chronology

The regressed stopped archive records these filesystem mtimes:

| Time | Local profile | Meaning |
|---|---|---|
| `22:39:55` | `UPI.dat` | user-pattern state saved during game completion |
| `22:39:55` | `classic_stage_save.dat` | classic history/progress counter advanced to 20 |
| `22:40:21` | `quest_progress.dat_<UID>` | local quest slots saved after the final quest update |
| `22:41:05` | `bMarket.dat` | black-market state refreshed while the menu consumed zero history |
| `22:41:05` | `new2profile.dat` | general profile saved during zero-history menu processing |
| `22:41:20` | `exp.dat` | local safe experience saved as 2670 at the next GameStart |
| `22:41:21` | `bonus.dat` | mystery-box bonus state saved |
| `22:41:21` | `select.dat` | power-up selection state saved |

This ordering explains the hybrid result:

- response-pool history had already collapsed;
- `exp.dat` still preserved 2670;
- general/tutorial/local profiles continued to be rewritten at different transition points;
- some state regressed while other state survived.

## Healthy checkpoint ordering

At the healthy level-7 checkpoint:

```text
22:03:24  UPI.dat and classic_stage_save.dat
22:10:35  quest_progress.dat
22:10:36  bMarket.dat, exp.dat, new2profile.dat
```

At the post-bonus checkpoint:

```text
22:18:16  select.dat and bonusgame.dat
22:23:20  quest_progress.dat
22:23:22  bMarket.dat, exp.dat, new2profile.dat
```

The same grouping recurs across sessions, showing that these writes are tied to distinct transition stages rather than one all-or-nothing save operation.

## Effective post-game commit phases

The observed order is:

```text
1. GameStart request record + index
2. gameplay
3. UploadPocket request record + index
4. reconstructed completed-game pocket response
5. UPI/classic local profile writes
6. quest update request(s), each with record + index
7. quest_progress local profile write
8. return-to-main POCKET.GET / ranking requests
9. bMarket / exp / new2profile local refresh writes
10. power-up selection / bonus profiles on the next play transition
```

Some phases can be absent depending on quests, bonus mode, tutorials, and scene path.

## Crash-consistency implications

Process death can leave several coherent but mutually inconsistent states:

- numbered request written but index not advanced, producing a recoverable orphan under v23;
- under the superseded v22 ordering, index advanced while the numbered request was absent;
- pocket completion persisted but quest requests absent;
- response pool advanced while local quest profile is stale;
- local EXP/profile saved after a bad reconstructed response;
- selection/bonus state from the following transition combined with prior-game history.

No global transaction coordinates all these files.

## Evidence

```text
device-snapshots/2026-08-29-level8-progression/regression.log
save-analysis/profiles-level7.json
save-analysis/profiles-post-bonus-level7.json
save-analysis/profiles-regressed.json
PROGRESS_REGRESSION_ROOT_CAUSE.md
BIRZZLE_PROPRIETARY_PROFILES.md
native-patches/v23-request-first-index/stage-e-interrupted-writes/RESULTS.md
```
