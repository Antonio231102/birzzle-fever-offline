# Birzzle Fever proprietary profile files

## Scope

This document describes the non-CCrypt2 game-local files loaded through `CProfileHandler` and the EF engine's encrypted file API. It covers their purpose, cipher, key derivation, block framing, common headers, safe-number encoding, decoded structures, tooling, and on-device validation.

These files are separate from:

- CCrypt2 Base64/AES files documented in `BIRZZLE_SAVE_FORMAT.md`;
- the response-pool index and numbered history;
- OLE/Excel compound files such as `highscore` and `profile`;
- SQLite databases and analytics preferences.

## Executive result

The files are no longer opaque. The recovered format is:

```text
fixed-size manager structure
    -> fill padded buffer with byte 0x0C
    -> copy structure bytes over the beginning
    -> SEED-128 ECB encrypt each 16-byte block
    -> write raw ciphertext
```

The effective SEED key is:

```text
hex:   3a333b3637373937393841484f454b46
ASCII: :3;6779798AHOEKF
```

It is derived as:

```text
default engine key: 0b01080202010e0f0008000a0c010e00
XOR game key:       31323334353637383930414243444546  ("1234567890ABCDEF")
                    --------------------------------
effective key:      3a333b3637373937393841484f454b46
```

OpenSSL's standard `SEED-ECB` implementation decrypts the files correctly with that effective key.

## Relevant native code

### Game-side wrapper in `libbirzzle.so`

| Function | Offset | Purpose |
|---|---:|---|
| `CProfileHandler::CheckProfile` | `0x160FB8` | Opens a profile and confirms that it exists and has nonzero size. |
| `CProfileHandler::DeleteProfile` | `0x161010` | Deletes a profile path. |
| `CProfileHandler::LoadProfile` | `0x161048` | Allocates the requested structure size and calls `FILE_EncryptRead`. |
| `CProfileHandler::SaveProfile` | `0x1610CC` | Calls `FILE_EncryptWrite` with structure bytes, game key, and size. |

`LoadProfile` accepts:

```text
filename
optional 16-byte XOR key pointer
exact plaintext byte count
```

It succeeds only when `FILE_EncryptRead` returns the exact requested byte count.

### EF engine in `libef2d.so`

| Function | Offset | Purpose |
|---|---:|---|
| `CFile::GetPaddedSize` | `0x09CC5C` | Computes `(floor(size / 16) + 1) * 16`. |
| `CFile::DecryptFile` | `0x09CCA8` | Derives the key schedule and decrypts every 16-byte block. |
| `CFile::ReadFile` | `0x09CD44` | Reads padded ciphertext, decrypts, and copies only the requested byte count. |
| `CFile::EncryptFile` | `0x09CDF8` | Creates filler/key schedule and encrypts every block. |
| `CFile::WriteFile` | `0x09CEB8` | Encrypts and writes the padded buffer. |
| `SeedEncrypt` | `0x142EB0` | SEED block encryption. |
| `SeedDecrypt` | `0x143C5C` | SEED block decryption. |
| `SeedRoundKey` | `0x144A08` | SEED key schedule. |

Exported bridge functions used by `libbirzzle.so` include:

```text
FILE_EncryptWrite
FILE_EncryptRead
FILE_Create
FILE_Close
FILE_Delete
FILE_GetModifiedTimet
```

## Cipher and key derivation

### Default engine key

At `libef2d.so` offset `0x220950`, the engine contains the 16-byte default key:

```text
0b 01 08 02 02 01 0e 0f 00 08 00 0a 0c 01 0e 00
```

`EncryptFile`/`DecryptFile` copy this into a temporary key buffer.

### Optional XOR key

If the optional key pointer is non-null and its first byte is nonzero, the engine XORs all 16 default-key bytes with the supplied 16 bytes before calling `SeedRoundKey`.

A diagnostic v20 APK hooked `FILE_EncryptRead` at `0x098538` and logged the key pointer for every successfully loaded profile. All observed game profile reads supplied the same memory bytes:

```text
31 32 33 34 35 36 37 38 39 30 41 42 43 44 45 46
```

ASCII:

```text
1234567890ABCDEF
```

Diagnostic log representation:

```text
READ len=36    key=34333231383736354241303946454443
READ len=752   key=34333231383736354241303946454443
...
```

The printed 32-bit words appear byte-reversed within each word because ARM loads little-endian words before `%08x` formatting. Interpreted as memory bytes, the string is `1234567890ABCDEF`.

Evidence:

```text
native-patches/v20-request-index-retention/profile-diagnostic/profile-load.log
native-patches/v20-request-index-retention/profile_key_diagnostic.S
build_v20_profile_diagnostic.py
```

### Effective key

Bytewise XOR gives:

```text
0b01080202010e0f0008000a0c010e00
XOR 31323334353637383930414243444546
=   3a333b3637373937393841484f454b46
```

### Algorithm and mode

The engine's `SeedRoundKey`, `SeedEncrypt`, and `SeedDecrypt` match the standard 128-bit Korean SEED block cipher. Each block is processed independently; there is no IV or chaining operation. The profile format is therefore SEED-128 ECB.

## Padding/framing

For requested plaintext size `N`, the ciphertext size is:

```text
(floor(N / 16) + 1) * 16
```

This always allocates one more block boundary, even when `N` is already divisible by 16.

Before copying the structure, `EncryptFile` fills the complete padded buffer with constant byte:

```text
0x0C
```

It then copies exactly `N` structure bytes over the beginning and encrypts every block.

This is not PKCS#7 padding: the filler value is always `0x0C`, while the number of ignored bytes varies. `ReadFile` does not inspect the filler. It decrypts the padded size and copies only the caller's requested `N` bytes.

External tooling should preserve the complete decrypted padded image. Editing only the first `N` bytes and re-encrypting the unchanged padded image guarantees byte-for-byte compatibility.

## Common integrity header

Many manager profiles begin with:

| Offset | Size | Meaning |
|---:|---:|---|
| `0x00` | 8 | ASCII `Birzzle\0` signature |
| `0x08` | 4 | Little-endian filesystem modification timestamp |
| `0x0C` | varies | Manager-specific payload |

The manager-specific loader usually checks:

```text
signature == "Birzzle"
abs(filesystem_mtime - stored_timestamp) <= 10
```

The timestamp rule is the same fragile metadata coupling found in `FileWorker::ReadContent`.

Exceptions exist:

- `classic_stage_save.dat` stores timestamp first and `Birzzle\0` at offset `0x04`.
- `UPI.dat` has no `Birzzle` signature and stores its timestamp at the end of the 36-byte structure.
- `new2profile.dat` starts with the signature but its matching timestamp is at offset `0xD8` rather than `0x08`.
- tutorial and Kontagent records have signatures but no filesystem-matching timestamp in the captured structure.
- `eventNotice.dat` and `rating.bat` contain custom embedded substructures and nonstandard signature positions.

## File inventory and purpose

### Present in the original 2016 backup

| File | Loader/manager | Load bytes | Cipher bytes | Purpose |
|---|---|---:|---:|---|
| `new2profile.dat` | `CGameHistory::LoadProfile` (`0x159BBC`) | 752 | 768 | General game-history profile, mode/progress flags, and persistent profile state. |
| `bMarket.dat` | `CBlackMarketManager::LoadBlackMarketInfo` (`0x10CB40`) | 40 | 48 | Black-market availability/state. |
| `exp.dat` | `CExpLevelManager::LoadExpInfo` (`0x0FD164`) | 44 | 48 | Experience stored as one 32-byte safe number. |
| `tuto.dat_<UID>` | `CTutorialManager::LoadTutorialInfo` (`0x0FF108`) | 208 | 224 | Tutorial completion flags. |
| `kontagentCheck_v2_2.dat` | `CKontagentWrapper::LoadFirstCheckInfo` (`0x179754`) | 208 | 224 | Kontagent first-check/analytics flags; not gameplay progression. |

### Added during later gameplay

| File | Loader/manager | Load bytes | Cipher bytes | Purpose |
|---|---|---:|---:|---|
| `UPI.dat` | `CGameHistory::LoadUserPattern` (`0x158F64`) | 36 | 48 | User-pattern configuration/state. `UPI` is associated with user pattern here, not the response-pool UID. |
| `bonus.dat` | `CMysteryBox::LoadMysteryBoxBonusInfo` (`0x0F8240`) | 32 | 48 | Mystery-box bonus state. |
| `classic_stage_save.dat` | game-history/classic stage loader | 520 | 528 | Classic-game stage/history ring with 18 fixed record slots. |
| `quest_progress.dat_<UID>` | `CQuestManager::LoadCurrentQuestAtFile` (`0x11463C`) | 180 | 192 | Current quest selection and progress structures. |
| `select.dat` | `CEggShopDialog::LoadItemSelectInfo` (`0x088E88`) | 604 | 608 | Selected power-ups/items, flags, and 16 safe-number counters. |
| `bonusgame.dat_<UID>` | `CBonusGameManager::LoadBonusGameInfo` (`0x11ACF8`) | 44 | 48 | Current bonus-game key count as one safe number. |
| `friendship.dat_<UID>` | `CFriendshipPointManager::LoadFriendshipPointInfo` (`0x119E04`) | 80 | 96 | Current and daily friendship points plus trailing state. |
| `eventNotice.dat` | `CEventWebViewManager::LoadEventNoticeInfo` (`0x115D28`) | 20,640 | 20,656 | Large fixed event-notice/WebView state table. |
| `rating.bat` | `CRatingEvent::FileLoadRatingEventInfo` (`0x171200`) | 28 | 32 | Rating-event state and timestamps. |

Other loaders exist for profiles not present in the tested checkpoint:

```text
agreement.dat   CAgreementDialog::LoadAgreementInfo       16 bytes
iap.dat         CGameHistory::LoadIAPInfo                 50 bytes
gameinfo.dat    CGameHistory::LoadGameCostInfo            16 bytes
tbEvent.bat     CRatingEvent::FileLoadTeamBattleEventInfo  2 bytes
```

## Safe-number encoding

Several profiles do not store important integers as ordinary little-endian words. They use an eight-word, 32-byte structure with decoy bits.

Let the words be `w[0]` through `w[7]`. The logical unsigned 32-bit value is:

```text
(w[0] & 0x0000000F) |
(w[1] & 0x000000F0) |
(w[5] & 0x00000F00) |
(w[7] & 0x0000F000) |
(w[4] & 0x000F0000) |
(w[6] & 0x00F00000) |
(w[2] & 0x0F000000) |
(w[3] & 0xF0000000)
```

The meaningful nibble order is therefore:

```text
value bits  0–3   <- word 0
value bits  4–7   <- word 1
value bits  8–11  <- word 5
value bits 12–15  <- word 7
value bits 16–19  <- word 4
value bits 20–23  <- word 6
value bits 24–27  <- word 2
value bits 28–31  <- word 3
```

Every other bit is decoy material. Re-saving the same logical value can change the file hash because the decoy bits may be regenerated.

To edit safely, preserve each word and replace only its meaningful nibble. `decode_birzzle_profiles.py` provides `safe32_decode` and `safe32_encode`.

### Confirmed safe-number fields

| File | Offset | Meaning | Healthy level-7 value |
|---|---:|---|---:|
| `exp.dat` | `0x0C` | Experience | 2200 |
| `bonusgame.dat_<UID>` | `0x0C` | Bonus-game key count | 0 in post-bonus capture |
| `friendship.dat_<UID>` | `0x0C` | Current friendship points | 0 |
| `friendship.dat_<UID>` | `0x2C` | Daily friendship points | 0 |
| `select.dat` | `0x5C` onward | 16 item/power-up counters | all 0 in the tested checkpoint |

## Decoded profile structures

### `exp.dat`

```text
0x00  char[8]  "Birzzle\0"
0x08  uint32   timestamp
0x0C  Safe32   accumulated experience
```

Decoded progression captures:

| Checkpoint | Decoded experience |
|---|---:|
| Original 2016 | 0 |
| Level 3 | 410 |
| Level 4 | 650 |
| Level 5 | 1080 |
| Level 6 | 1620 |
| Level 7 | 2200 |
| Natural regression archive | 2670 |

The natural response-pool regression returned zero experience, but `exp.dat` still contained 2670. This explains why the earlier v18/v19 experience guard could recover an authoritative in-memory value even after response-pool replay failed.

### `bonusgame.dat_<UID>`

```text
0x00  char[8]  "Birzzle\0"
0x08  uint32   timestamp
0x0C  Safe32   current bonus-game key count
```

### `friendship.dat_<UID>`

```text
0x00  char[8]  "Birzzle\0"
0x08  uint32   timestamp
0x0C  Safe32   current friendship points
0x2C  Safe32   daily friendship points
0x4C  uint32   trailing friendship/date state
```

### `select.dat`

```text
0x000  char[8]   "Birzzle\0"
0x008  uint32    timestamp
0x00C  int32[12] selected item identifiers
0x03C  byte[32]  selection/availability flags
0x05C  Safe32[16] item or power-up counters
```

The healthy post-bonus checkpoint has `-1` for all 12 selected IDs and zero for all 16 decoded safe counters. Selection UI state can also be held in live scene objects; this file is the persistent profile representation, not necessarily a frame-by-frame mirror of the visible UI.

### `classic_stage_save.dat`

```text
0x000  uint32      timestamp
0x004  char[8]     "Birzzle\0"
0x00C  uint32      cumulative progress/game counter
0x010  uint32[7]   record slot 0
...                18 fixed slots total
```

The structure contains 18 slots of 28 bytes each. The counter can exceed 18; the slots are fixed storage, likely a rolling or mode-specific history rather than a variable-length array.

Observed counter progression:

```text
level 3:  5
level 4:  7
level 5: 10
level 6: 14
level 7: 18
regressed capture: 20
```

### `tuto.dat_<UID>`

The first eight bytes are `Birzzle\0`. The remaining 200 bytes are dominated by byte-valued flags.

Observed count of value `1`:

```text
original 2016: 1
healthy level 7: 29
```

This aligns with the observed persistence of tutorial-completion state during hybrid-backup experiments.

### `new2profile.dat`

A 752-byte raw game-history/profile structure:

- starts with `Birzzle\0`;
- contains many byte flags and fixed arrays;
- contains a filesystem-matching timestamp at offset `0xD8` in the captured builds;
- is loaded directly into `CGameHistory`-related state;
- contains raw structure data rather than a self-describing schema.

Exact field names beyond the statically identified loaders remain partially unmapped. Edits should preserve unknown bytes and use differential captures to identify individual flags.

### `quest_progress.dat_<UID>`

A 180-byte raw quest-manager structure:

- standard signature/timestamp at offsets 0 and 8;
- scalar quest identifiers/status values;
- copied raw C++ substructures that include pointer-looking values from the original process;
- fixed-position data consumed selectively by `CQuestManager`.

Pointer-like words are serialized implementation artifacts. They must not be dereferenced by external tools. The loader ignores or replaces fields that are not safe to reuse.

### `eventNotice.dat`

A 20,640-byte fixed event-notice table. It contains nested manager records rather than one standard header. In the tested level-7 capture:

- `Birzzle\0` occurs at offset 19,956;
- a matching timestamp occurs at offset 20,172;
- early words describe counts/state for event entries;
- most unused table capacity is zero-filled.

### `rating.bat`

A compact 28-byte custom event structure. It contains:

- timestamps at offsets 8 and 24 in the tested capture;
- `Birzzle\0` beginning at offset 13;
- rating-event flags/state at the remaining positions.

It is not a Windows batch script despite its extension.

## Decryption and re-encryption tool

Tool:

```text
decode_birzzle_profiles.py
```

It requires an OpenSSL build with the legacy SEED provider. On the current Windows workstation it uses:

```text
C:\Program Files\Git\mingw64\bin\openssl.exe
C:\Program Files\Git\mingw64\lib\ossl-modules\legacy.dll
```

Generate a report and plaintext dumps:

```text
python decode_birzzle_profiles.py \
  device-snapshots/2026-08-29-bonus-mode-test/post-bonus-v18-data.tar.gz \
  --output save-analysis/profiles-post-bonus-level7.json \
  --dump-plaintext save-analysis/profiles-post-bonus-level7
```

For each known file the tool:

1. validates the ciphertext size against the manager's exact load size;
2. decrypts all blocks with SEED-ECB;
3. separates the bytes loaded by the game from the ignored padded tail;
4. identifies signatures and matching timestamp offsets;
5. decodes known safe-number fields;
6. reports known arrays/headers;
7. re-encrypts the complete padded image and requires a byte-identical ciphertext round trip.

Machine-readable reports include:

```text
save-analysis/profiles-original-2016.json
save-analysis/profiles-level3.json
save-analysis/profiles-level4.json
save-analysis/profiles-level5.json
save-analysis/profiles-level6.json
save-analysis/profiles-level7.json
save-analysis/profiles-post-bonus-level7.json
save-analysis/profiles-regressed.json
save-analysis/profiles-live-device.json
```

## Manual OpenSSL decryption

Effective key:

```text
3a333b3637373937393841484f454b46
```

Conceptual command:

```text
openssl enc -d -seed-ecb \
  -K 3a333b3637373937393841484f454b46 \
  -nopad -provider legacy \
  -in exp.dat -out exp.dat.decrypted-padded.bin
```

After decryption, use only the exact load size for that file. The remaining bytes are ignored engine filler, normally `0x0C`.

To re-encrypt, preserve the complete block-aligned decrypted image and run SEED-ECB encryption with `-nopad`. Do not let OpenSSL add PKCS#7 padding.

## Safe editing rules

1. Work on a copy and preserve the original ciphertext.
2. Use the exact manager load size from the table.
3. Preserve the complete padded decrypted image.
4. Preserve unknown raw-structure bytes.
5. For Safe32, change only meaningful nibbles; retain decoy bits.
6. Update manager timestamps only when the loader validates them.
7. Set filesystem mtime to the embedded timestamp, within 10 seconds.
8. Re-encrypt every 16-byte block with the effective SEED key and no additional padding.
9. Restore mode and current package UID ownership.
10. Confirm decrypt/encrypt round-trip before deploying.
11. Validate behavior on a disposable checkpoint before public distribution.

## On-device validation

A diagnostic APK recorded every loaded profile's optional XOR key. The captured key was consistently `1234567890ABCDEF` across load sizes including:

```text
36, 40, 44, 80, 180, 208, 520, 604, 752, 20640
```

A stopped live-device `files/` snapshot was pulled and decoded successfully. `exp.dat` decoded to 2200, matching the subsequent production `POCKET.GET` response.

After diagnostics:

- the diagnostic APK was replaced with the production v20 APK;
- the original clean checkpoint data remained installed;
- inventory loaded correctly;
- pocket values were 982920 coins, 99870 gems, and 2200 experience;
- `SCORE.RANKING` completed;
- no fatal error occurred.

Evidence:

```text
native-patches/v20-request-index-retention/profile-diagnostic/profile-load.log
native-patches/v20-request-index-retention/profile-diagnostic/live-profiles.tar.gz
native-patches/v20-request-index-retention/profile-diagnostic/production-restored.log
save-analysis/profiles-live-device.json
```

## Relationship to the progress regression

These profiles are parallel/local state, not the shared response-pool history.

The natural regression archive demonstrates the distinction:

```text
response-pool replayed experience: 0
exp.dat Safe32 experience:         2670
```

The response-pool failure still removed quests, pets, and other replayed history. Local profiles retained selected values and flags, which produced the hybrid/limbo behavior and allowed some defensive clamps to recover individual fields.

A complete public save therefore needs both:

- coherent response-pool/cached-response data;
- coherent proprietary manager profiles with valid SEED encryption, signatures, and mtimes.

Detailed `bonus.dat` field offsets, reward probabilities, spawn rules, and one-game consumption behavior are documented in `MYSTERY_BOX_REWARDS.md`.
