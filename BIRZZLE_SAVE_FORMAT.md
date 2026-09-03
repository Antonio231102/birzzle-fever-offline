# Birzzle Fever save-file format and structure

## Scope

This document describes the Android application data used by Birzzle Fever 1.1.2, with emphasis on the 2016 Titanium Backup and the later working/regressed checkpoints.

It covers:

- Titanium Backup container files;
- the app-data directory layout;
- the `CCrypt::Encrypt2`/`Decrypt2` envelope;
- filename derivation;
- cached offline responses;
- the append-only response pool;
- nested payload formats;
- proprietary game-local binary files;
- SQLite and shared-preference data;
- ownership, permissions, and especially modification-time requirements;
- safe inspection and reconstruction rules.

Related documents:

```text
PROGRESS_REGRESSION_PATCHES.md
PROGRESS_REGRESSION_ROOT_CAUSE.md
READCONTENT_EMPTY_ROOT_CAUSE.md
PSALM23_CRYPTO_KEY.md
BIRZZLE_PROPRIETARY_PROFILES.md
```

## Titanium Backup bundle

The original public source material consists of:

```text
com.halfbrick.birzzlefever-a626a1d45ccbedeb6dee1e6805dd0916.apk.gz
com.halfbrick.birzzlefever-20160501-111000.properties
com.halfbrick.birzzlefever-20160501-111000.tar.gz
```

### APK component

The `.apk.gz` member is the gzip-compressed application APK. The metadata identifies:

```text
package:          com.halfbrick.birzzlefever
label/version:    Birzzle Fever 1.1.2
version code:     13
APK MD5:          a626a1d45ccbedeb6dee1e6805dd0916
```

### Properties component

The `.properties` file is Titanium Backup metadata. It records the version, label, APK codec/location, source device model/build, and icon.

It is not the game's own save format.

### Data archive

The `.tar.gz` archive stores paths under:

```text
data/data/com.halfbrick.birzzlefever/
```

The original archive contains:

- `files/`;
- `shared_prefs/`;
- `databases/`.

Later direct device snapshots also contain cache, Chromium WebView, a `lib` symlink, and the portable seed marker.

The original tar records ownership as `u0_a125` and mode `0600` for most private files. The restored app on the Galaxy S4 currently uses a different package UID (`u0_a217`). Titanium Backup or a root restore must map/chown the files to the installed package UID. The numeric UID embedded in an old tar does not need to equal the newly assigned package UID as long as the final files are owned and accessible by the installed app.

## Directory-level inventory

### Original 2016 archive

The analyzer classified 44 regular files:

| Family | Count |
|---|---:|
| CCrypt2 encrypted envelope | 22 |
| Proprietary binary | 7 |
| OLE Compound File Binary/Excel workbook | 5 |
| Android XML preferences | 8 |
| SQLite database | 2 |

### Healthy post-bonus checkpoint

The later level-7 checkpoint contains 162 regular files:

| Family | Count |
|---|---:|
| CCrypt2 encrypted envelope | 126 |
| Proprietary binary | 18 |
| OLE Compound File Binary/Excel workbook | 5 |
| Java serialized object | 1 |
| Android XML preferences | 8 |
| SQLite database | 3 |
| Empty marker | 1 |

The increase is dominated by numbered response-pool request records.

Machine-readable reports:

```text
save-analysis/original-2016.json
save-analysis/post-bonus-level7.json
save-analysis/regressed-level8.json
```

Analyzer:

```text
analyze_birzzle_save.py
```

## CCrypt2 outer representation

### On-disk layers

A `FileWorker` file written through `WriteContent` has these layers:

```text
outer Base64 text
    -> AES-128-ECB ciphertext
        -> PKCS#7-padded plaintext
            -> C+ prefix
            -> 32 ASCII hex MD5 characters
            -> newline-delimited envelope body
```

The fixed AES key recovered from `libef2d.so` is:

```text
miaeHgpdskiinerS
```

This is exactly 16 bytes and is used with AES-128 in ECB mode.

The key is not stored contiguously in the original binary. `CCrypt::Encrypt2`/`Decrypt2` select 16 characters from eight embedded Psalm 23 strings referenced by `g_crypto_key_for_birzzle` at `0x28AF84`. Those characters concatenate to `miaeHgpdskiinerS`. The strings, pointer arrays, exact character coordinates, and derivation code are documented in `PSALM23_CRYPTO_KEY.md`.

### Plaintext structure

A decrypted index example is:

```text
C+b2775c453426bf5886961536d6d75ec8KEY:2IFPjD+ZDgenCckuzAl2lg==
DATA:LTEsMTAy
TIMESTAMP:1788060200
```

Logically:

```text
C+<md5(body)><body>
```

where:

```text
body = KEY:<token>\nDATA:<base64 payload>\nTIMESTAMP:<unix time>
```

For the example:

```text
MD5(body) = b2775c453426bf5886961536d6d75ec8
Base64Decode(DATA) = -1,102
```

### `KEY`

`KEY` is an opaque generated token stored as Base64, usually decoding to 16 bytes in the observed files. It is not the AES key. The AES key is the fixed binary key shown above.

The token is created by `MathUtility::GenerateToken` during `WriteContent`. The analyzed files do not require the token to derive the AES key.

### `DATA`

`DATA` is always a Base64 representation of the caller's payload. The decoded payload may itself be:

- plain JSON;
- a comma-separated list;
- a command plus query-string parameters;
- another Base64 string;
- Base64-encoded gzip data plus a revision suffix;
- empty.

### `TIMESTAMP`

`TIMESTAMP` is decimal Unix time generated by `time(NULL)` before encryption and file output.

`FileWorker::ReadContent` compares it to the filesystem `st_mtime` and accepts only:

```text
abs(st_mtime - TIMESTAMP) <= 10 seconds
```

This metadata is part of the effective save format. Copying valid bytes while changing only mtime can make the game treat the file as empty.

### Integrity and security properties

The format provides accidental-corruption detection, not modern authenticated encryption:

- MD5 is unkeyed;
- AES-ECB exposes repeated-block structure;
- the AES key is fixed in the executable;
- anyone with the key can modify `DATA`, regenerate MD5, encrypt, and set a matching mtime.

## Filename derivation

The restored identity used by the offline data is:

```text
UID = 3c8bb7308c3fcb60c439224bd595c794d8f31501
```

There are four major naming schemes.

### 1. Literal filename hashed with MD5

Several static objects use:

```text
MD5(literal_filename)
```

| Logical name | On-disk filename |
|---|---|
| `pocket.dat` | `f610517ac55e2e13002f926c0b2c8ac3` |
| `stage.dat` | `152d2465929052196ca910ebd27913f1` |
| `social.dat` | `db970d8a77424f1c389fa61a4e828b70` |
| `messagecount.dat` | `93dd6b8b1d96123948a8e514c2db86f0` |
| `friendlist.dat` | `9ad4313e3931ef722ed37c48488d4d4d` |
| `localtime.dat` | `b6e1cfd3545c3b38db18a44d3f400b63` |
| `variable.dat` | `8dd6bfa11a897f797273a1480c80f94e` |
| `submarinevariable.dat` | `09d531fd0dc2a818e49efec1d5548a78` |

### 2. UID plus response command

Cached offline API responses use:

```text
MD5(UID + UPPERCASE_COMMAND)
```

| Command | On-disk filename |
|---|---|
| `SERVER.INIT` | `db43d855af5a463eed20d12a8389a70b` |
| `POCKET.LOGIN` | `e8ed33784fc8f8d72f0d173b64ce66c1` |
| `INVENTORY.LIST` | `2760236875bbd7abd2c69ece34c57b2f` |
| `INVENTORY.USE` | `587461b71691f5fa8860b571ddf43ea4` |
| `INVENTORY.UPDATE` | `bca34a120b7dc9a4d995b1e8506134c6` |
| `INVENTORY.BUY` | `5e05ca89754e38ab6bde4c3a0ae5a36e` |
| `CUSTOM.GET` | `578208ad94e0e63bff1e7a39959d8113` |
| `CUSTOM.POST` | `872ff8d1759901fae843abcf6d7bddb6` |
| `POCKET.GET` | `9313956a09c41cb888d050760c2dfe9c` |
| `POCKET.SET` | `228ef384a2311a4c15c85ad880e125fa` |
| `GLOBAL.GET.NAME` | `66f609beead9929097a429787bce71ca` |
| `GIFT.GET.COUNT` | `55ada64f1d095066ed08173868ef51ce` |
| `SCORE.RANKING` | `d1fbe32e12b1a9d5fda79abf89e747f2` |

These payloads are normally JSON responses.

### 3. UID plus API-list marker

The supported-command list uses:

```text
MD5(UID + "APIFILE")
= 38fea61783913e4c14f8d948da706343
```

Its decoded payload is:

```text
SERVER.INIT,POCKET.LOGIN,INVENTORY.LIST,INVENTORY.USE,
INVENTORY.UPDATE,INVENTORY.BUY,CUSTOM.GET,CUSTOM.POST,
POCKET.GET,POCKET.SET,GLOBAL.GET.NAME,GIFT.GET.COUNT,SCORE.RANKING
```

### 4. Response-pool names

The index is:

```text
MD5(UID + "REQUESTPOOLINDEX")
= 5f7d50ff681a65b10550a631e11a2ded
```

Request record `n` is:

```text
MD5(UID + "REQUESTPOOL_" + decimal(n))
```

Examples:

| Index | Filename in healthy pool | Decoded command |
|---:|---|---|
| 0 | `3ec79b0f1529e3fda4242b59a97d2123` | `inventory.buy` |
| 1 | `9e88879937d5588d483a3bd2913efa88` | `inventory.use` |
| 2 | `21d1df9b4e6d190360d748e3c95418dc` | `pocket.set` |
| 100 | `9d10784cb323bdff6665ecf8b237a0ea` | `pocket.set` |
| 101 | `159acee746ea8d30d5e81f9e0d68680f` | `pocket.set` |
| 102 | `9f5d2aba1b2fea63db26ccbe2ffaeaa3` | `pocket.set` |

The healthy level-7 index contains:

```text
-1,102
```

and all request filenames for indices 0 through 102 are present.

## Original backup versus evolved response pool

The original 2016 archive contains cached responses and static state, but no `REQUESTPOOLINDEX` and no numbered `REQUESTPOOL_n` files.

This is a legitimate new-pool condition. The first offline write after restoration initializes request zero.

The portable patches preserve this behavior by allowing the original empty-pool path until a process has successfully observed a mature index.

Later checkpoints contain an append-only request history. Calculators replay subsets of this history to reconstruct:

- pocket totals;
- inventory/pets;
- quests and missions;
- ranking state.

The request payload format is generally:

```text
<lowercase.command>,<key=value&key=value&...>
```

Example:

```text
pocket.set,timeout=10&heart=0&gem=0&coin=0&exp=0&
tropy=0&unlockitem=0&extradata=GameStart&...&
```

Quest example:

```text
quest.update.status,questlevel=44&questid=30&
queststatus=2&questvalue=30&key=&timeout=27&
```

The index does not enumerate filenames. It stores only the first/last range. Filenames are regenerated from UID and each decimal index.

## The regression's structural change

Healthy archive:

```text
index DATA: -1,102
request 0:  inventory.buy
records 103–115: not yet present
```

Regressed archive:

```text
index DATA: -1,0
request 0:  later GameStart, replacing the old request 0
records 1–115: still present
```

Records 103–115 remained decryptable and contained completed games, rewards, and quest updates. The index prevented them from being replayed.

This is why deleting unrelated UI caches cannot reliably repair progression: the history files may be intact while the single range pointer is wrong.

## Representative static payloads

### `pocket.dat`

`f610517ac55e2e13002f926c0b2c8ac3` contains a nested Base64 payload. The original 2016 inner text is:

```text
HEART:5
TIMETOLASTCHARGED:1462097303
COIN:0
GEM:0
LEVEL:0
TROPHY:0
UNLOCKITEM:0
TIMESTAMP:95820008779779
EXTRA:
BLACKMARKET:
```

The inner `TIMESTAMP` belongs to the serialized pocket object and is distinct from the outer FileWorker Unix timestamp.

Later checkpoints update coin, gem, level/experience, heart timing, and other pocket fields here, while the response pool remains the replay source for subsequent reconstruction.

### `variable.dat`

After the outer `DATA` decode, another Base64 decode yields a comma-separated server configuration:

```text
900,1000,1000,100,1462186800,
http://birzzlefever.enfeelcdn.com/game/,
http://birzzlefever.enfeelcdn.com/game/download.php,-
```

These include values such as heart regeneration interval, limits, ranking reset time, and content URLs.

### `submarinevariable.dat`

`09d531fd0dc2a818e49efec1d5548a78` is not a score or ranking record. Its decoded payload has the form:

```text
<Base64(gzip(JSON))>_20
```

The suffix is revision `20`. Decompression yields a JSON object with 6,310 bytes of feature/configuration fields, including pet-event, bonus-key, friendship, premium-heart, and other game-tuning values.

Renaming this file changed ranking/menu behavior during early experiments because it changes configuration availability and initialization timing. Its contents do not make it the response-pool index or the root progression history.

### Other nested static records

| Logical file | Inner representation |
|---|---|
| `localtime.dat` | `0,0` in the original backup |
| `social.dat` | nested Base64 comma-separated state |
| `messagecount.dat` | nested Base64 comma-separated counts |
| `friendlist.dat` | nested Base64 friend ID/region lines |
| `stage.dat` | empty payload in the original backup |

## Proprietary game-local binary profiles

Not every file uses CCrypt2. The game-side `CProfileHandler` and EF engine use a second, fully recovered format for files such as:

```text
bMarket.dat
exp.dat
new2profile.dat
tuto.dat_<UID>
UPI.dat
bonus.dat
classic_stage_save.dat
quest_progress.dat_<UID>
select.dat
bonusgame.dat_<UID>
eventNotice.dat
friendship.dat_<UID>
rating.bat
```

The format uses:

```text
SEED-128 ECB
default key: 0b01080202010e0f0008000a0c010e00
XOR key:     1234567890ABCDEF
final key:   3a333b3637373937393841484f454b46
```

The engine pads to `(floor(size / 16) + 1) * 16`, fills ignored bytes with constant `0x0C`, and encrypts every block independently. Many structures include `Birzzle\0`, a filesystem-matching timestamp, raw manager fields, and 32-byte safe-number objects whose logical integer is distributed across eight decoy-filled words.

Recovered examples include:

- `exp.dat`: accumulated experience;
- `select.dat`: persistent power-up selection IDs, flags, and counters;
- `bonusgame.dat_<UID>`: bonus-game key count;
- `friendship.dat_<UID>`: current/daily friendship points;
- `classic_stage_save.dat`: fixed classic-mode history records;
- `tuto.dat_<UID>`: tutorial flags;
- `quest_progress.dat_<UID>`: current quest structures;
- `new2profile.dat`: general profile and progression flags.

The exact cipher implementation, key capture, headers, every known file/manager mapping, safe-number formula, decoded layouts, OpenSSL procedure, editing rules, runtime validation, and decoder tool are documented in:

```text
BIRZZLE_PROPRIETARY_PROFILES.md
decode_birzzle_profiles.py
```

## OLE Compound File Binary files

The following files begin with:

```text
D0 CF 11 E0 A1 B1 1A E1
```

which is the Microsoft OLE Compound File Binary signature:

```text
clearbox
highscore
order
profile
test
```

Their directory streams include:

```text
Workbook
\x05SummaryInformation
\x05DocumentSummaryInformation
\x01CompObj
```

They are Excel-compatible workbook containers, despite lacking `.xls` extensions. The same five files are byte-identical between the original 2016 archive and the progressed level-7 checkpoint. No progression dependency was observed during the response-pool investigation.

They should not be confused with the encrypted `SCORE.RANKING` cache or the request history merely because one file is named `highscore`.

## Java serialized and analytics files

`AppEventsLogger.persistedevents` begins with:

```text
AC ED 00 05
```

and contains a Java-serialized `HashMap`. It belongs to Facebook event logging, not the offline request pool.

Tracking-related files and preferences include:

```text
Kontagent.xml
kontagentCheck_v2_2.dat
mat_id.xml
mat_queue.xml
mat_log_id_open.xml
mat_log_id_last_open.xml
OL_Prefs_Keys.xml
com.google.android.gcm.xml
AppEventsLogger.persistedevents
```

They contain installation IDs, tracking IDs, push registration tokens, event queues, and analytics state. They are not authoritative gameplay history.

Removing tracking data may be desirable for distribution, but earlier sanitization experiments demonstrated that broad deletion without preserving game/config files can change initialization behavior. Sanitize by identified family, not by filename shape alone.

## SQLite databases

### `e30b431a9b2d47948fed9f6a5602fa91`

Tables:

```text
android_metadata(locale)
api_calls(id, url, name, session_id, timestamp, msg_id)
```

The captured `api_calls` table is empty. This database belongs to the Kontagent/API queue layer.

### `webview.db`

Contains legacy Android WebView form, HTTP-auth, and password tables. The captured tables are empty except `android_metadata`.

### `app_webview/Web Data`

Later Android WebView metadata with autofill/profile/card tables. The captured user-data tables are empty.

These databases are not the request-pool event log.

Journal files are SQLite rollback journals. They may appear as binary and are meaningful only with their corresponding database and transaction state.

## Ownership, modes, and modification times

### Ownership

After restore, every private app file must be accessible to the installed package UID. The old archive UID is historical metadata. Titanium Backup can remap it; a manual root extraction should run an appropriate recursive `chown` after installation.

### Modes

Typical modes:

```text
app data directory: 0711/0751-style Android private directory
files directory:    0771
private files:      0600
shared preferences: 0600 or 0660
```

Exact parent traversal permissions matter as much as the file mode.

### Modification times

For CCrypt2 and several proprietary profiles, mtime is logically part of the record. Preserve it.

Across captured CCrypt2 data:

| Archive | Maximum absolute mtime/envelope difference |
|---|---:|
| Original 2016 | 1 second |
| Healthy post-bonus | 1 second |
| Captured regressed archive | 1 second |

A difference greater than 10 seconds causes rejection.

The regressed archive passes the check because its bad `-1,0` index was newly written consistently. The rejected predecessor was already overwritten.

## Safe CCrypt2 editing procedure

To modify one CCrypt2 record correctly:

1. Read the outer Base64 bytes.
2. Base64-decode to AES ciphertext.
3. AES-128-ECB decrypt with `miaeHgpdskiinerS`.
4. Remove and validate PKCS#7 padding.
5. Verify the `C+` prefix.
6. Split the next 32 ASCII characters as the stored MD5.
7. Verify `MD5(body)`.
8. Parse `KEY`, `DATA`, and `TIMESTAMP`.
9. Base64-decode `DATA` and edit the domain payload.
10. Base64-encode the edited domain payload into `DATA`.
11. Retain or deliberately regenerate `KEY`.
12. Choose a Unix `TIMESTAMP` value.
13. Rebuild the body exactly.
14. Compute lowercase hexadecimal `MD5(body)`.
15. Build `C+<md5><body>`.
16. Apply PKCS#7 padding to a 16-byte boundary.
17. AES-128-ECB encrypt.
18. Outer Base64-encode.
19. Write via a temporary file and atomic rename where possible.
20. Set filesystem mtime to the embedded `TIMESTAMP`, or within 10 seconds.
21. Set the installed package UID and private mode.

The game itself does not use an atomic temporary-file strategy, but external tooling should.

## Safe response-pool reconstruction

When adding or repairing a numbered request:

1. Confirm the historical UID.
2. Derive the record name with `MD5(UID + "REQUESTPOOL_" + index)`.
3. Encode the request command/query payload in CCrypt2.
4. Give the record a matching mtime.
5. Decode and validate the current index.
6. Update the last index without discarding the existing first/last semantics.
7. Rebuild the index CCrypt2 envelope.
8. Give the index a matching mtime.
9. Verify every filename in the declared range exists and passes digest/time validation.

Never change only the index to reference nonexistent records. Never copy valid encrypted bytes and then leave them with the copy operation's current mtime.

## Inspection tool

Generate a machine-readable report with:

```text
python analyze_birzzle_save.py \
  com.halfbrick.birzzlefever-20160501-111000.tar.gz \
  --output save-analysis/original-2016.json
```

The analyzer reports:

- path, size, mtime, UTC time, and SHA-256;
- detected file family;
- inferred logical role and request index;
- CCrypt2 envelope fields;
- MD5 validity;
- decoded `DATA`;
- nested Base64/gzip layers;
- embedded timestamp and mtime delta;
- whether the record passes the game's 10-second check.

It can analyze a tar archive, a directory tree, or one file.

## Practical distribution guidance

For a public package/save checkpoint:

- distribute the patched APK and one known-good data archive as a matched pair;
- preserve all CCrypt2 mtimes from the archive;
- preserve the UID-derived filenames and historical UID-dependent content;
- let the restore tool map filesystem ownership to the installed app UID;
- for mature saves, retain the request index and every numbered record in its range; for the original 2016 save, preserve the legitimate absent-index virgin state;
- avoid restoring stale SQLite journals unless they belong to the same captured transaction state;
- exclude verified analytics/tracking tokens and caches as classified in `OLE_ANALYTICS_ARTIFACTS.md`;
- retain configuration records such as `submarinevariable.dat` unless deliberately replacing their behavior;
- verify the restored index cryptographically and by mtime before first launch.

The essential distinction is:

```text
filesystem owner UID -> must match the currently installed Android package
historical game UID   -> must remain the value used to derive encrypted/cache filenames
```

Those are different identities and serve different purposes.

Related operational documents:
- `INDEX_DIAGNOSTICS_AND_RECOVERY.md`
- `READCONTENT_EMPTY_ROOT_CAUSE.md`
- `POST_GAME_COMMIT_ORDER.md`
- `STATE_PRECEDENCE.md`
- `PROFILE_FIELD_MAPS.md`
- `MINIMAL_PUBLIC_SAVE.md`
- `OLE_ANALYTICS_ARTIFACTS.md`
- `MYSTERY_BOX_REWARDS.md`
