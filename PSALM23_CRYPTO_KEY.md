# Psalm 23 as Birzzle Fever cryptographic key material

## Finding

Birzzle Fever's `libef2d.so` contains the complete text of Psalm 23 split across eight null-terminated strings. These strings are not dialogue, localization text, or an Easter egg displayed by the game. They are referenced by global crypto-key arrays and are used to construct the AES key for the game's `CCrypt`/CCrypt2 save-file encryption.

The text observed in the console:

```text
Surely goodness and love will follow me all the days of my life, and I will dwell in the house of the LORD forever.
```

is the eighth and final string. It is Psalm 23:6 in an older NIV-style wording.

## Source binary

The strings are present in:

```text
native-patches/v20-request-index-retention/libef2d-source.so
```

They remain present at the same offsets in the patched `libef2d.so`; v20 does not alter this region.

## Embedded text and offsets

| Line index | Offset | Embedded text |
|---:|---:|---|
| 0 | `0x2215F8` | `The LORD is my shepherd, I shall not be in want.` |
| 1 | `0x22162C` | `He makes me lie down in green pastures, he leads me beside quiet waters` |
| 2 | `0x221674` | `he restores my soul.` |
| 3 | `0x22168C` | `He guides me in paths of righteousness for his name's sake.` |
| 4 | `0x2216C8` | `Even though I walk through the valley of the shadow of death,` |
| 5 | `0x221708` | `I will fear no evil, for you are with me; your rod and your staff, they comfort me.` |
| 6 | `0x22175C` | `You prepare a table before me in the presence of my enemies. You anoint my head with oil; my cup overflows.` |
| 7 | `0x2217C8` | `Surely goodness and love will follow me all the days of my life, and I will dwell in the house of the LORD forever.` |

The split follows the content of Psalm 23 but does not preserve verse numbering as separate metadata.

## Global pointer arrays

Two exported data symbols contain pointers to the same eight strings:

| Symbol | Offset | Range occupied by eight ARM pointers |
|---|---:|---:|
| `g_crypto_key` | `0x28AEA4` | `0x28AEA4`–`0x28AEC3` |
| `g_crypto_key_for_birzzle` | `0x28AF84` | `0x28AF84`–`0x28AFA3` |

Each array is eight 32-bit pointers in line-index order. Both arrays resolve to the offsets listed above.

The binary also contains the related symbols:

```text
SECURE_ROUNDKEY                    0x097420
SECURE_ENCRYPT                     0x097424
SECURE_DECRYPT                     0x097428
EF::CAES::MakeKey                  0x0BEA5C
EF::CAES::Encrypt                  0x0BEF04
EF::CAES::Decrypt                  0x0BF134
CCrypt::Decrypt2                   0x119220
CCrypt::Encrypt2                   0x119818
```

The exported `SECURE_*` functions at `0x097420`–`0x097428` are no-op stubs in this Android build. The substantive AES and CCrypt routines are elsewhere in the library.

## AES-key derivation

`CCrypt::Decrypt2` and the corresponding encryption path do not store the final 16-byte AES key as one contiguous plaintext constant. Instead, they load `g_crypto_key_for_birzzle`, select individual characters from the Psalm strings, and assemble the key byte by byte.

String and character indices below are zero-based.

| Key byte | Result | Psalm line | Character index | Nearby source text |
|---:|:---:|---:|---:|---|
| 0 | `m` | 0 | 12 | `D is my she` |
| 1 | `i` | 1 | 21 | `down in gre` |
| 2 | `a` | 5 | 9 | `ll fear no ` |
| 3 | `e` | 2 | 9 | `estores my ` |
| 4 | `H` | 3 | 0 | `He gui` |
| 5 | `g` | 4 | 9 | ` though I w` |
| 6 | `p` | 6 | 7 | `u prepare a` |
| 7 | `d` | 7 | 18 | `ss and love` |
| 8 | `s` | 2 | 15 | `s my soul.` |
| 9 | `k` | 4 | 17 | `I walk thro` |
| 10 | `i` | 1 | 13 | ` me lie dow` |
| 11 | `i` | 5 | 17 | `no evil, fo` |
| 12 | `n` | 4 | 3 | `Even thou` |
| 13 | `e` | 3 | 7 | ` guides me ` |
| 14 | `r` | 2 | 3 | `he restor` |
| 15 | `S` | 7 | 0 | `Surely` |

Concatenating those characters produces:

```text
miaeHgpdskiinerS
```

That exact 16-byte result is the AES-128 key used to decrypt and encrypt CCrypt2 records documented in `BIRZZLE_SAVE_FORMAT.md`.

A direct derivation is equivalent to:

```python
coordinates = [
    (0, 12), (1, 21), (5, 9), (2, 9),
    (3, 0),  (4, 9),  (6, 7), (7, 18),
    (2, 15), (4, 17), (1, 13), (5, 17),
    (4, 3),  (3, 7),  (2, 3), (7, 0),
]
key = "".join(psalm_lines[line][column] for line, column in coordinates)
assert key == "miaeHgpdskiinerS"
```

## Why the text was used

The implementation is a form of static-key obfuscation:

- the final AES key does not appear as one obvious contiguous ASCII constant;
- a casual `strings` inspection shows a familiar passage rather than an apparent 16-byte password;
- the code selects characters from different positions to reconstruct the actual key at runtime.

This does not provide meaningful cryptographic secrecy against reverse engineering. The strings, pointer arrays, character-selection instructions, and final key derivation are all present in the same binary. It only raises the effort needed to identify the key.

The use of Psalm 23 was a developer choice. The binary contains no comment explaining why that passage was selected, so any personal or religious motivation would be speculation. Its technical role, however, is established by the symbol names, pointer arrays, and byte-selection code.

## Relationship to save formats

The derived key is used by the CCrypt/CCrypt2 layer that protects:

- cached offline API responses;
- `pocket.dat` and other hashed static records;
- the response-pool index;
- numbered response-pool requests.

The on-disk CCrypt2 pipeline is:

```text
Psalm strings
    -> select 16 characters
    -> AES key: miaeHgpdskiinerS
    -> AES-128-ECB encrypt/decrypt
    -> C+MD5 envelope
    -> outer Base64 file
```

The separate proprietary EF profile format uses `SeedRoundKey`, `SeedEncrypt`, and `SeedDecrypt`, default key `0b01080202010e0f0008000a0c010e00`, and XOR material `1234567890ABCDEF`, producing effective SEED key `3a333b3637373937393841484f454b46`. It is documented in `BIRZZLE_PROPRIETARY_PROFILES.md`. The presence of Psalm-backed crypto symbols should not be taken to mean that every binary `.dat` file uses the CCrypt2 AES key.

## Why it appeared in the console

During native-library research, the `strings` utility was used to extract printable sequences from `libef2d.so`. `strings` prints any sufficiently long printable bytes without knowing their semantics.

Because the complete Psalm text is embedded as ordinary null-terminated ASCII, the console printed it alongside function names, URLs, error messages, and other constants. The game itself did not emit the verse as a runtime log message.

## Reproduction commands

Locate the final line:

```text
strings -t x libef2d.so | findstr /I /C:"Surely goodness"
```

Expected offset:

```text
2217c8
```

Locate the crypto symbols:

```text
llvm-nm -D -n libef2d.so | findstr "CAES SECURE_ g_crypto_key"
```

The pointer arrays can also be confirmed by reading eight little-endian 32-bit values starting at `0x28AEA4` and `0x28AF84`.

## Conclusion

The Psalm passage is a load-bearing implementation detail of Birzzle Fever's persistence system. Its practical importance is not the text's religious content but its use as a character reservoir from which the game reconstructs the fixed AES-128 key `miaeHgpdskiinerS`.
