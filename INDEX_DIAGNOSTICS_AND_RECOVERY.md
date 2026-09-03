# Response-index diagnostics and read-only recovery

## Failure classifier

`diagnose_response_index.py` reproduces every gate in the game's `FileWorker::ReadContent` path for the `REQUESTPOOLINDEX` record. It accepts a local file or pulls the live record through ADB and emits JSON.

```text
python diagnose_response_index.py <index-file> --output save-analysis/index.json
python diagnose_response_index.py --adb --output save-analysis/live-index-diagnostic.json
```

Classifications:

| Result | Meaning |
|---|---|
| `ACCESS_NOT_FOUND` | Path absent or inaccessible during ADB acquisition |
| `EMPTY_FILE` | Read returned zero bytes |
| `OUTER_BASE64_INVALID` | File is not valid outer Base64 |
| `AES_BLOCK_SIZE_INVALID` | Decoded ciphertext length is not a positive multiple of 16 |
| `PKCS7_PADDING_INVALID` | AES plaintext padding is invalid |
| `PREFIX_INVALID` | Decrypted envelope does not begin with the CCrypt2 prefix |
| `ENVELOPE_TOO_SHORT` | Envelope cannot contain prefix, digest, and body |
| `ENVELOPE_MD5_MISMATCH` | Stored digest differs from the envelope-body MD5 |
| `FIELD_MISSING_KEY` / `FIELD_MISSING_DATA` / `FIELD_MISSING_TIMESTAMP` | Required envelope field absent |
| `KEY_BASE64_INVALID` / `DATA_BASE64_INVALID` | Nested field encoding invalid |
| `TIMESTAMP_INVALID` | Embedded timestamp is not an integer |
| `MTIME_MISMATCH` | Filesystem mtime differs from the embedded timestamp by more than 10 seconds |
| `INDEX_PAYLOAD_INVALID` | Decoded `DATA` is not two decimal integers |
| `INDEX_RANGE_INVALID` | First/last indices violate the pool range invariant |
| `ACCEPT` | File passes all checks and yields a usable range |

`test_index_diagnostics.py` constructs and verifies every classification. This external classifier diagnoses a captured file; it cannot observe a transient short read after a later write has already repaired the same pathname.

## Read-only pool reconstruction

`reconstruct_response_pool.py` derives all filenames from the supplied historical UID, validates every numbered request record, compares the observed range with the authoritative index, and writes a reconstruction report without modifying the source.

```text
python reconstruct_response_pool.py <archive-or-directory> --output save-analysis/pool.json
python reconstruct_response_pool.py --adb --output save-analysis/pool-live-device.json
python reconstruct_response_pool.py <archive> --uid <historical-UID> --output save-analysis/pool.json
```

Classifications:

- `VIRGIN_NO_POOL`: no index and no numbered records; valid for the original 2016 backup.
- `MATURE_INDEX_MISSING`: numbered records exist but the index is absent.
- `INDEX_REJECTED`: index exists but fails `ReadContent` validation.
- `INDEX_STALE_OR_COLLAPSED`: valid records extend beyond the index's last value.
- `INDEX_REFERENCES_MISSING_OR_INVALID_RECORDS`: the index advertises records that cannot form a valid contiguous prefix.
- `CONSISTENT`: the accepted index agrees with the valid contiguous record range.

The tool reports candidate bounds but never writes a repair. A numerically contiguous pool is not necessarily semantically safe: request zero can have been overwritten after an index collapse. `REQUEST_0_NEWER_THAN_REQUEST_1_POSSIBLE_OVERWRITE` and `INDEX_ZERO_WITH_ORPHANED_HIGHER_RECORDS` require a known-good request zero before any repair is attempted.

## Observed fixtures

| Source | Classification | Range / evidence |
|---|---|---|
| Original May 2016 backup | `VIRGIN_NO_POOL` | No index or numbered requests |
| Known-good post-bonus level-7 checkpoint | `CONSISTENT` | `0..102`, index `-1,102` |
| Regressed level-8 snapshot | `INDEX_STALE_OR_COLLAPSED` | Valid `0..115`, index collapsed to `-1,0`, request zero newer than request one |
| Restored live clean checkpoint | `CONSISTENT` | `0..102`, index `-1,102` |

Reports are in `save-analysis/pool-*.json`. The write ordering and transaction implications are documented in `POST_GAME_COMMIT_ORDER.md`.
