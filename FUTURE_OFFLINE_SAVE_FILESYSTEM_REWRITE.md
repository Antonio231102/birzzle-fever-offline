# Tentative post-release offline save filesystem rewrite

## Status

**Tentative post-public-release idea. Not a V25 release requirement, committed feature, or approved migration design.**

This proposal arose from a personal concern about Birzzle Fever's append-only offline response pool. Normal play continually increases both the request index and the number of save-related files. V25 protects the known destructive index-reset paths, but it intentionally preserves the game's original replay model rather than redesigning persistence.

The immediate priority remains publishing and validating the conservative V25 lineage. Any save rewrite would be a separate later update with its own format version, migration plan, rollback strategy, fault matrix, and prolonged testing.

## Motivation

The offline backend persists a small encrypted file for every state-changing request.

The authoritative index is:

```text
MD5(UID + "REQUESTPOOLINDEX")
```

Its decrypted `DATA` field contains a range such as:

```text
-1,156
```

Request record `n` is stored as:

```text
MD5(UID + "REQUESTPOOL_" + decimal(n))
```

The index file itself does not grow materially with play. What grows without an existing compaction mechanism is:

- the last numeric index;
- the number of encrypted request files;
- the amount of history replayed by offline calculators;
- the work required for backup, restore, validation, and directory traversal.

The history reconstructs pocket totals, inventory and pets, quests, missions, and ranking state. Old files therefore cannot be deleted merely because newer files exist.

## Current measured baseline

The mature `-1,156` checkpoint contains 157 numbered requests:

| Measurement | Value |
|---|---:|
| Encrypted request count | 157 |
| Total logical request bytes | 64,296 |
| Mean encrypted record size | 409.5 bytes |
| Median encrypted record size | 448 bytes |
| Minimum record size | 256 bytes |
| Maximum record size | 556 bytes |

Command distribution:

| Command | Count |
|---|---:|
| `pocket.set` | 88 |
| `quest.update.status` | 52 |
| `inventory.update` | 11 |
| `inventory.buy` | 3 |
| `inventory.use` | 2 |
| `custom.post` | 1 |

Small files generally consume at least one filesystem block each. Assuming approximately 4 KiB per request plus directory metadata, illustrative scaling is:

| Requests | Approximate logical payload | Approximate block allocation |
|---:|---:|---:|
| 157 | 64 KiB | 0.6–1 MiB |
| 1,000 | 0.4 MiB | 4–6 MiB |
| 10,000 | 4 MiB | 40–60 MiB |
| 100,000 | 40 MiB | 400–600 MiB |

These are estimates, not measured device guarantees. Filesystem block size, metadata, compression, and backup representation affect the actual values.

## Risk assessment

### Numeric index overflow

The native format uses signed decimal integer formatting. A probable 32-bit signed limit would be approximately:

```text
2,147,483,647
```

Even at five new records per game, reaching that value would require roughly 429 million games. Numeric overflow is not a practical concern.

There is no evidence that 4,096 is a game limit. That value currently belongs to project tooling:

- `analyze_birzzle_save.py` precomputes request names for indices `0..4095`;
- `reconstruct_response_pool.py` defaults to a 4,096-range scan, although callers can request a larger scan.

A save can plausibly exceed the default diagnostic range before it approaches any native integer limit. Tooling must be made dynamic before a scale test beyond that point.

### Startup and response-calculation cost

The offline calculators replay subsets of the append-only history. Replay work is therefore expected to grow approximately with record count.

Potential long-term symptoms:

- slower cold startup;
- longer pocket, inventory, quest, mission, or ranking calculation;
- increased memory use;
- increased file-open and directory-lookup activity;
- loading-dialog timeouts, ANRs, or softlocks at a sufficiently large pool.

The exact complexity and memory behavior have not been benchmarked beyond the current low hundreds of records. This risk is credible but not yet quantified.

### Backup and restore fragility

Each record has:

- a UID-derived hashed filename;
- a CCrypt2 envelope and digest;
- an embedded timestamp;
- a matching filesystem mtime;
- package ownership and permissions.

An incomplete restore can leave a valid index advertising a missing or rejected numbered request. V25 fails closed rather than collapsing the pool, but the game then requires repair before loading can complete.

The probability of one omitted, damaged, or metadata-mismatched file increases as a backup contains thousands of independently restored files.

### Storage exhaustion and interrupted writes

V25's request-first commit order makes an interrupted append safer:

```text
write complete request N
    -> commit index advertising N
```

A failure between those operations leaves an orphan request beyond the previous index rather than an index that references an absent request. This ordering does not eliminate low-storage and filesystem failures; it constrains their damage.

Large-pool behavior under near-full storage has not been tested.

### Large-directory behavior

All hashed files share the application `files` directory with other state. ext4 supports large directories, but tens of thousands of files increase the cost of:

- startup replay;
- backup and restore;
- tar or ZIP creation;
- integrity scanning;
- manual inspection and recovery.

### Undocumented calculator assumptions

The V24 ranking regression exposed an undocumented positional contract in `COfflineResponseCalc::calcRanking()`. Similar assumptions may exist for record count, ordering, allocation, or timeout behavior.

No specific high-index defect is known. Absence of current evidence is not evidence that arbitrary history sizes are safe.

## Why simple deletion or index reset is unsafe

The request pool is an event history, not a cache of redundant snapshots.

Deleting old records can remove:

- coin, gem, EXP, and heart deltas;
- pet purchases, selections, and upgrades;
- quest and mission transitions;
- bonus-mode state;
- ranking history.

The index stores only replay bounds. It does not store a canonical reconstructed snapshot.

The following are explicitly unsafe without a replacement snapshot design:

- deleting records below an arbitrary threshold;
- changing `-1,N` to a shorter range;
- resetting the pool to `-1,0`;
- copying request zero over another record;
- retaining only the newest request of each command;
- deduplicating requests by textual similarity;
- relying on local profile files to fill every removed domain.

These operations can recreate the same partial or global regression that the V20–V25 lineage was built to prevent.

## Goals of a future rewrite

A successful rewrite should:

1. bound the number of live save files;
2. bound startup replay work;
3. retain crash consistency and request-first safety;
4. preserve every observable pocket, inventory, quest, mission, tutorial, bonus, and ranking value;
5. support deterministic integrity checks;
6. migrate existing V25 pools without modifying the source until validation succeeds;
7. fail back to the legacy reader when migration is absent or incomplete;
8. support backup and restore without timestamp-sensitive thousands-file payloads;
9. remain compatible with Android 4.4 and 32-bit ARM;
10. permit future format upgrades through an explicit version field.

## Non-goals

A first rewrite should not also attempt to:

- redesign gameplay progression;
- change the historical application identity;
- revive online services;
- add cloud synchronization;
- merge unrelated profile formats without evidence;
- remove V25's network, leaderboard, unlimited-play, or response-index protections;
- silently repair an already-corrupt legacy pool without a known-good request zero;
- claim cryptographic secrecy from a key embedded in the executable.

## Candidate architecture options

### Option A: packed legacy request container

Store the existing encrypted request records in one container with a lookup table:

```text
request-pool.pack
request-pool.manifest
```

The manifest maps request index or derived filename to offset, length, mtime, and digest. Existing calculators would continue consuming the same logical CCrypt2 records through a patched file-access layer.

Advantages:

- greatly reduces file count;
- preserves current event semantics;
- easier to compare packed and unpacked pools byte-for-byte;
- lower semantic migration risk than synthesizing state.

Disadvantages:

- replay time remains proportional to total history;
- the logical index still grows indefinitely;
- random access and crash-safe append require a carefully designed container index;
- patching every relevant file-access path may be difficult.

This addresses filesystem clutter but not unbounded replay.

### Option B: canonical snapshot plus bounded delta journal

Persist a complete canonical state snapshot and only recent requests:

```text
save.manifest
snapshot.A
snapshot.B
journal.A
journal.B
```

The active snapshot represents all supported state through sequence `S`. The journal stores requests `S+1..N`. When the journal reaches a threshold, the application builds a new snapshot in the inactive slot and atomically switches the manifest.

Advantages:

- bounded file count;
- bounded replay time;
- bounded journal size;
- natural generation and checksum model;
- efficient backup and restore.

Disadvantages:

- requires a complete canonical schema for every authoritative domain;
- missing one state field can cause delayed progression regression;
- requires new reader, writer, migration, and compaction logic;
- hardest option to prove equivalent to the legacy calculators.

This is the best long-term shape but has the highest semantic risk.

### Option C: transactional SQLite store

Use an Android-compatible SQLite database containing:

- metadata and format version;
- canonical domain snapshots;
- ordered request journal;
- generation and integrity information.

Advantages:

- transactions and indexed lookup;
- mature crash-recovery behavior;
- one primary database plus normal journal files;
- straightforward schema versioning.

Disadvantages:

- native integration or a Java/native bridge is required;
- Android 4.4 SQLite behavior and journaling mode constrain the design;
- database corruption and migration need separate recovery tooling;
- introducing a new dependency boundary increases implementation risk.

SQLite does not remove the need to define complete state semantics.

### Option D: packed container first, snapshot later

Use two post-release stages:

1. migrate thousands of files into a byte-preserving packed container;
2. after that format is proven, add optional canonical snapshots and a bounded delta tail.

Advantages:

- separates file-count reduction from semantic compaction;
- enables exact record-level comparison during the first migration;
- reduces the scope of each release.

Disadvantages:

- requires two format transitions;
- first stage does not solve replay growth;
- temporary compatibility code remains longer.

This is the conservative recommended research sequence.

## Proposed on-disk invariants

Regardless of implementation, the new format should define:

```text
magic
format_version
generation
historical_uid
snapshot_sequence
journal_first_sequence
journal_last_sequence
payload_length
payload_sha256
commit_state
```

Required invariants:

- generations increase monotonically;
- active manifest points only to a complete, validated snapshot/container;
- journal begins exactly after the snapshot sequence;
- journal entries are contiguous;
- writes target an inactive temporary generation;
- payload is flushed and fsynced before manifest replacement;
- manifest replacement is atomic;
- previous generation remains available until the new generation passes a cold restart;
- unsupported versions fail closed without modifying legacy data.

Checksums provide corruption detection, not secret authentication. If authenticity is required, the design needs a keyed MAC and a key-management decision; the existing embedded game key alone does not create a strong hostile-device security boundary.

## Migration requirements

Migration is the highest-risk component.

### Preconditions

Before migration:

- force-stop or otherwise quiesce game persistence;
- confirm the legacy index decrypts and validates;
- confirm request zero is known-good;
- confirm every advertised request exists;
- validate every CCrypt2 digest and mtime;
- confirm the pool is contiguous;
- verify sufficient free storage for old and new representations simultaneously;
- create an external immutable backup when possible.

### Two-phase migration

A safe migration should follow this order:

```text
1. Read and validate legacy data without modifying it.
2. Build inactive new-format generation.
3. Verify new-format checksums and structural invariants.
4. Replay old and new representations independently.
5. Compare every supported observable state field.
6. Atomically publish the new-format manifest.
7. Cold-restart and compare again.
8. Retain rollback generation and legacy archive until an acceptance window passes.
9. Remove or externally archive legacy files only after explicit success.
```

A crash before step 6 must leave V25's original files authoritative. A crash after step 6 must select either the previous complete generation or the new complete generation.

### Required state comparison

Migration validation must compare at minimum:

- coins, gems, EXP, hearts, level, and unlocks;
- inventory ownership, selected pet, and every ability level;
- quests, missions, progress values, and claimed rewards;
- bonus-mode and key state;
- tutorial and feature-unlock flags;
- ranking high score;
- stage and per-mode progress;
- timestamps that affect rewards or replenishment;
- response sequence/generation metadata.

A UI smoke test alone is insufficient because earlier regressions could remain hidden until a later transition.

## Rollback model

A public rewrite must define rollback before migration ships.

Possible model:

- retain the last complete V25 legacy pool as a packed, immutable rollback archive;
- retain the previous new-format generation;
- expose a diagnostic exporter that reconstructs a legacy-compatible checkpoint when possible;
- never allow an older APK to open and partially rewrite an unrecognized new-format directory;
- require a verified backup before intentionally downgrading.

An in-place downgrade is not automatically safe. An older APK knows nothing about the new manifest and could initialize a separate pool or overwrite profiles.

## Scale-test plan before implementation

Before choosing a format, measure the current V25 design using disposable data copies at approximately:

```text
1,000 requests
5,000 requests
10,000 requests
```

The existing diagnostic limit must be raised first.

At each size:

1. validate every record and mtime;
2. record logical and allocated storage;
3. run ten cold launches;
4. measure time to `SERVER.INIT`, `POCKET.GET`, and `SCORE.RANKING`;
5. record application RSS and peak memory;
6. verify pocket, inventory, quests, missions, and ranking;
7. complete a real game and append the next request;
8. cold-restart and verify the new index;
9. create and restore a complete backup;
10. repeat missing-index and interrupted-write tests.

Synthetic records must be semantically valid and used only in disposable test data. Blind duplication of arbitrary requests can create rewards, quest transitions, heart changes, or ranking changes and does not constitute a valid scale test.

## Rewrite validation matrix

Any implementation must pass more than the existing V25 matrix.

### Format and migration

- virgin V25 pool;
- low-index progressed pool;
- mature `-1,156` pool;
- synthetic 1,000/5,000/10,000-record pools;
- migration interrupted at every write/rename boundary;
- insufficient storage before and during migration;
- corrupt inactive generation;
- corrupt active manifest;
- missing journal entry;
- unsupported future format version;
- repeated migration attempt after a prior crash.

### Gameplay

- completed games;
- mid-game exits;
- power-up cancellation;
- bonus mode;
- quest and mission completion/reward;
- pet buy, use, and upgrade;
- spending and level-ups;
- zero-lives unlimited-play boundary;
- every return-to-main-menu route;
- leaderboard startup and later refresh;
- multiple process and device restarts.

### Equivalence

For every checkpoint, the legacy and rewritten backends must produce equivalent observable responses for:

```text
SERVER.INIT
POCKET.LOGIN
INVENTORY.LIST
INVENTORY.USE
INVENTORY.UPDATE
INVENTORY.BUY
CUSTOM.GET
CUSTOM.POST
POCKET.GET
POCKET.SET
GLOBAL.GET.NAME
GIFT.GET.COUNT
SCORE.RANKING
```

Differences must be explained and approved; silent divergence is a failed migration.

### Performance

A rewrite should establish explicit budgets, for example:

- cold-start replay time remains bounded after compaction;
- compaction does not block the UI beyond an accepted window;
- peak temporary storage is known;
- peak memory is safe on the Galaxy S4;
- backup size and duration are materially reduced.

Exact budgets should be based on pre-rewrite measurements rather than selected arbitrarily.

## Operational protection before a rewrite

Until a replacement format exists, retain V25's append-only pool and add monitoring rather than deleting history.

Recommended checkpoints:

```text
1,000 requests: record performance baseline
4,000 requests: raise and verify diagnostic scan limits
10,000 requests: mandatory scale, backup, and restore test
```

At meaningful progression milestones:

1. force-stop the game;
2. archive complete application data;
3. record index text and SHA-256;
4. record request-zero SHA-256;
5. validate the full contiguous range;
6. retain at least two prior known-good checkpoints.

A checkpoint is acceptable only when every advertised request validates and the analyzer reports no semantic warning.

## Decision gate

Do not begin implementation solely because the directory contains many files. First determine through scale testing whether the current design reaches an unacceptable limit during plausible real-world play.

Proceed with a rewrite only when all are true:

- V25 has already shipped and its conservative format is stable;
- measured replay, storage, or backup behavior justifies the migration risk;
- every authoritative state domain is mapped;
- an independent equivalence oracle exists;
- migration and rollback are designed before code changes;
- disposable large-pool fixtures are available;
- the project accepts a new extended validation cycle.

Until then, this document is a research proposal and risk register, not a promise of a future rewrite.
