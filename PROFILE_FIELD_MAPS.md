# `new2profile.dat` and quest-profile field maps

## `quest_progress.dat_<UID>`

### Container

```text
load size: 180 bytes
cipher size: 192 bytes
cipher: SEED-128 ECB
key: 3a333b3637373937393841484f454b46
```

`CQuestManager::LoadCurrentQuestAtFile` is at `libbirzzle.so:0x11463C`; `SaveQuestInfos` begins at `0x114848`.

### Three fixed slots

The 180-byte plaintext is three consecutive 56-byte quest slots plus 12 bytes of final structure data/padding within the loaded size:

```text
slot 0 base: 0x00
slot 1 base: 0x38
slot 2 base: 0x70
slot size:   0x38
```

Slot 0 begins with the profile integrity header:

```text
+0x00 char[8] "Birzzle\0"
+0x08 uint32  filesystem timestamp
```

The loader iterates three slots. For each slot:

```text
+0x0C uint32 quest ID
+0x20 uint32 value copied into live quest object offset +0x24
+0x2C uint32 value copied into live quest object offset +0x30
```

It searches the live quest table for an entry whose quest ID equals slot `+0x0C`, then restores the two progress/status fields.

The remaining words are raw `CQuestManager`/quest-entry structure data. Several captured values look like old process pointers. They are persisted by a raw 56-byte copy but are not all dereferenced after restoration.

### Differential quest IDs

| Checkpoint | Slot 0 `+0x0C` | Slot 1 `+0x0C` | Slot 2 `+0x0C` |
|---|---:|---:|---:|
| Level 3 | 30 | 70 | 80 |
| Level 4 | 60 | 70 | 90 |
| Level 5 | 100 | 110 | 120 |
| Level 6 | 80 | 70 | 90 |
| Level 7 | 140 | 150 | 155 |
| Regressed capture | 60 | 70 | 155 |

The regressed combination shows that local quest slots changed independently of the now-empty response-pool quest history.

### Other observed scalar transitions

Offsets are absolute plaintext offsets:

| Offset | Level 3 | Level 4 | Level 5 | Level 6 | Level 7 | Regressed |
|---:|---:|---:|---:|---:|---:|---:|
| `0x10` | 5 | 1 | 1 | 4 | 4 | 1 |
| `0x14` | 0 | 0 | 0 | 54 | 55 | 0 |
| `0x1C` | 30 | 70000 | 100000 | 5 | 2 | 70000 |
| `0x48` | 2 | 2 | 2 | 2 | 1 | 2 |
| `0x54` | 3000 | 3000 | 600 | 3000 | 150000 | 3000 |
| `0x80` | 4 | 6 | 13 | 6 | 11 | 11 |
| `0x8C` | 5 | 3 | 6 | 3 | 10 | 10 |
| `0x90` | 0 | 0 | 5 | 0 | 2 | 2 |

These are candidate type, target, status, and progress fields. Exact user-facing names require correlating each quest ID with the game's quest definition table. They should not be renamed or normalized without that table.

## `new2profile.dat`

### Container

```text
load size: 752 bytes (0x2F0)
cipher size: 768 bytes
signature: "Birzzle\0" at 0x00
mtime field: uint32 at 0xD8
```

Loader:

```text
CGameHistory::LoadProfile at libbirzzle.so:0x159BBC
```

### Confirmed source-to-live mappings

The loader explicitly reads these plaintext offsets:

| Plain offset | Width | Live destination/use |
|---:|---:|---|
| `0x08` | byte | boolean restored to live profile byte 0 |
| `0x09` | byte | boolean restored to live profile byte 2 |
| `0x1F` | byte | boolean restored to live profile byte 1 |
| `0x20` | byte | boolean restored to live profile byte 5 |
| `0x21` | byte | boolean restored to live profile byte 4 |
| `0x22` | byte | boolean restored to live profile byte 6 |
| `0x0C` | 32 bytes | Safe32 value reconstructed into live SafeNumber words around `+0x90`–`+0xAC` |
| `0x24` | uint32 | copied to live profile `+0x0C` |
| `0x30` | 40 bytes | copied to live profile block beginning `+0x18` |
| `0x58` | 80 bytes | copied to live profile block beginning `+0x40` |
| `0xB8` | 8 bytes | copied to live block `+0xB8` |
| `0xC0` | 8 bytes | copied to live block `+0xC0` |
| `0xC8` | 8 bytes | copied to live block `+0xD0` |
| `0xD0` | 8 bytes | copied to live block `+0xD8` |
| `0xD8` | uint32 | compared with filesystem mtime; tolerance 10 seconds |
| `0xDC` | string area | validated as a URL before use |
| `0x2E0` | uint32 | copied to a later live profile field |
| `0x2E4` | byte | boolean restored to live profile byte 3 |
| `0x2E8` | uint32 | copied to live profile `+0x14` |
| `0x2EC` | byte | boolean restored to live profile byte 7 |

Several values are transformed from persisted `1/-1` conventions into C++ booleans rather than copied verbatim.

### Differential monotonic field

Plain offset `0xB0` (`176`) changed as follows:

```text
level 3:   6
level 4:   8
level 5:  11
level 6:  15
level 7:  19
regressed: 22
```

It behaves like a cumulative game/profile counter. The classic-history counter evolved in parallel as `5, 7, 10, 14, 18, 20`, so `new2profile +0xB0` is consistently one or two units ahead in these captures. Its exact semantic name is not exported.

### Profile behavior

`new2profile.dat` is not a self-describing object. It is a raw ABI-specific C++ profile image. It contains:

- boolean/tutorial/unlock flags;
- one Safe32-protected value;
- copied fixed arrays;
- profile counters;
- URL/config text;
- timestamp metadata;
- unknown/reserved bytes.

The loader copies selected ranges and ignores or validates others. External tools should preserve unknown bytes and use differential edits rather than reconstructing the structure from zero.

## Mapping method and evidence

The map combines:

- SEED-decrypted snapshots from original, levels 3–7, and regression;
- direct `LoadProfile`/`SaveProfile` disassembly;
- differential byte/u32 comparisons;
- runtime key diagnostics;
- user-observed hybrid backup behavior.

Artifacts:

```text
save-analysis/profiles-original-2016/
save-analysis/profiles-level3/
save-analysis/profiles-level4/
save-analysis/profiles-level5/
save-analysis/profiles-level6/
save-analysis/profiles-level7/
save-analysis/profiles-regressed/
BIRZZLE_PROPRIETARY_PROFILES.md
decode_birzzle_profiles.py
```

## Remaining semantic names

The structural maps and loader behavior are established. These names remain provisional until quest/config tables are correlated:

- quest slot fields other than ID and the two restored values;
- the exact meaning of `new2profile +0xB0`;
- the Safe32 value at `new2profile +0x0C`;
- user-facing names for the copied fixed profile blocks.
