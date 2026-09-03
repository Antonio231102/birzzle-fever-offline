# Why `FileWorker::ReadContent` can return empty

## Scope

This document continues the investigation in:

```text
PROGRESS_REGRESSION_ROOT_CAUSE.md
PROGRESS_REGRESSION_PATCHES.md
```

The earlier work established that an empty response-pool index read can eventually replace the mature pool index with `-1,0`. This document analyzes the lower-level file reader, identifies every major path that is collapsed into an empty string, and reports a new controlled reproduction using a valid but timestamp-skewed index.

## Updated conclusion

A concrete lower-level condition is now established:

> `FileWorker::ReadContent` rejects an otherwise valid encrypted file when the filesystem modification time differs from the encrypted `TIMESTAMP` field by more than 10 seconds.

A controlled 60-second modification-time skew, with no content changes, caused the original v19 build to reconstruct exactly the same empty-history state seen during the natural regression:

- `POCKET.LOGIN` returned `queststatus: []`;
- `INVENTORY.LIST` returned only the sentinel row;
- `POCKET.GET` returned zero coin, gem, and experience;
- `SCORE.RANKING` returned zero scores.

The skewed index itself remained cryptographically valid and still decoded to `-1,102`. This isolates the failure to `ReadContent` metadata validation, rather than missing bytes, wrong identity, bad AES data, or an already-reset index.

This makes a modification-time mismatch a proven sufficient cause and a strong candidate for the natural failure. It does not prove that the natural event was specifically caused by modification time, because the pre-collapse index was overwritten by the later `GameStart` before it could be captured.

## Relevant functions and state

All addresses in this section are relative to the original `libef2d.so` image.

| Function/state | Offset | Role |
|---|---:|---|
| `FileWorker::GetModifiedTime` | `0x120F88` | Calls `stat` and returns the file's `st_mtime`. |
| `FileWorker::WriteContent` | `0x121280` | Builds, encrypts, and directly writes a save file. |
| `FileWorker::ReadContent` | `0x1215A8` | Opens, decrypts, validates, and returns a payload. |
| `CCrypt::Decrypt2` | `0x119220` | Outer Base64 decode, AES-128-ECB decryption, padding and MD5-envelope validation. |
| `CCrypt::Encrypt2` | `0x119818` | Constructs and encrypts the `C+<md5><body>` representation. |
| `g_fileworkermutex` | `0x291ACC` | Shared mutex used by both `ReadContent` and `WriteContent`. |
| `g_pFileWorker` | `0x291AD0` | Singleton `FileWorker` pointer. |

The diagnostic string embedded at `0x2301EC` is:

```text
FileWorker::readFile Verify ModifiedTime Fail!!!!!
```

## `ReadContent` control flow

### 1. Serialize access

At entry, `ReadContent` locks `g_fileworkermutex`. The same mutex is locked by `WriteContent`.

This rules out a normal in-process race where one `FileWorker` reader observes the middle of another `FileWorker` write. Reads and writes through this class are serialized for the complete operation.

The mutex is not a filesystem lock. Root tools, Titanium Backup, another process, or native code bypassing `FileWorker` can still modify the file independently.

### 2. Build the hardcoded app-data path

The binary contains:

```text
/data/data/com.halfbrick.birzzlefever/files
/data/data/com.halfbrick.birzzlefever/files/%s
```

The requested logical filename is formatted into this directory.

### 3. Existence check

At approximately `0x1215FC`, the function calls:

```c
access(path, F_OK)
```

If `access` fails, the mutex is unlocked and an empty C++ string is returned. No structured error reaches `CResponsePool`.

### 4. Capture filesystem modification time

For an existing file, `GetModifiedTime` calls `stat` and reads `st_mtime`. A failed `stat` yields zero.

### 5. Open and read the complete file

The file is opened directly with `fopen(path, "r")`.

The implementation then:

1. seeks to the end;
2. gets the length with `ftell`;
3. rewinds/seeks to the beginning;
4. allocates `length + 1` bytes;
5. zero-fills the allocation;
6. calls `fread` for the expected length;
7. closes the stream.

The `fread` return value is not checked. A short read leaves part of the zero-filled buffer in place and is passed to the decryptor. That normally becomes a Base64, AES, padding, or envelope failure and is eventually represented as an empty result.

If `fopen` fails, `ReadContent` also returns an empty string.

### 6. `CCrypt::Decrypt2`

The file bytes are passed to `CCrypt::Decrypt2`, which performs:

1. outer Base64 decoding;
2. AES-128-ECB decryption with the fixed key `miaeHgpdskiinerS`;
3. PKCS#7 padding removal;
4. `C+` prefix validation;
5. extraction of a 32-character MD5 string;
6. MD5 verification of the remaining envelope body.

Failure in the OpenSSL initialization/update/final paths, invalid padding, a bad prefix, or an MD5 mismatch produces an empty or invalid result. `ReadContent` does not return a distinct decrypt error to its caller.

### 7. Parse envelope fields

The decrypted body is split into newline-separated `name:value` pairs. Expected fields are:

```text
KEY:<base64 token>
DATA:<base64 payload>
TIMESTAMP:<decimal Unix time>
```

Missing or malformed required entries can also lead to the common empty return.

### 8. Validate modification time

The `TIMESTAMP` value is converted with `atol`. Around `0x121BD2`–`0x121BE8`, the function computes:

```text
absolute_value(filesystem_mtime - embedded_timestamp)
```

The response is accepted only when:

```text
absolute_value(filesystem_mtime - embedded_timestamp) <= 10
```

A difference of 11 seconds or more is rejected. The function unlocks the mutex and returns an empty string.

This check is independent of the outer AES/MD5 integrity check. A file can be cryptographically perfect and still be treated as nonexistent because its metadata differs.

### 9. Decode `DATA`

After validation, `DATA` is Base64-decoded and copied into the returned C++ string. Some serializers put another Base64 or gzip layer inside this payload; that inner encoding is domain-specific and is not part of `FileWorker` itself.

## `WriteContent` control flow

`WriteContent` holds the same `g_fileworkermutex` from before serialization until after `fclose`.

Its sequence is:

1. Base64-encode the caller's payload.
2. Generate an opaque token for `KEY`.
3. Call `time(NULL)` around `0x121310`.
4. Build the newline-delimited envelope body.
5. Call `CCrypt::Encrypt2` around `0x12139A`.
6. Open the final target path directly with `fopen(path, "w")` around `0x1213C4`.
7. Call `fwrite` around `0x1213D4`.
8. Call `fclose` around `0x1213DA`.
9. Unlock the mutex around `0x1213E4`.

### Write-path weaknesses

#### Timestamp is captured before encryption and I/O

The embedded timestamp is generated before encryption and before opening the file. Normally the resulting filesystem mtime differs by zero or one second. If the thread is suspended for more than 10 seconds between `time(NULL)` and the actual write, the game can create a file that its own reader later rejects.

This is possible in principle during process suspension, long scheduling stalls, or unusual storage blocking. The natural regression logs do not show a greater-than-10-second request-processing delay immediately before the first zero response, so this mechanism is not established for that event.

#### The write is not atomic

The final path is opened with mode `"w"`, which truncates it immediately. There is no temporary sibling file followed by an atomic `rename`.

A process death, storage failure, or short write can leave a zero-length or partial file at the authoritative path.

#### Write results are not checked

The code does not check the `fwrite` return count. There is no explicit `fflush`, `fsync`, or post-write verification. `fclose` provides normal stdio flushing but not an application-level guarantee that the full encrypted payload reached storage.

#### No redundant index

There is only one response-pool index. Request records may remain recoverable, but a rejected or overwritten index removes the map required to replay them.

## Controlled modification-time experiment

### Input

The experiment used the clean post-bonus checkpoint:

```text
index filename:       5f7d50ff681a65b10550a631e11a2ded
embedded TIMESTAMP:   1788060200
filesystem mtime:     1788060200
index DATA:           -1,102
MD5 envelope:         valid
```

Only the filesystem mtime was changed:

```text
new filesystem mtime: 1788060260
metadata delta:        +60 seconds
file content:          unchanged
```

The original v19 APK was then cold-launched.

### Result

The captured findings were:

```text
embedded timestamp:        1788060200
filesystem mtime:          1788060260
delta:                      +60 seconds
envelope MD5 valid:         yes
index payload still:        -1,102
POCKET.LOGIN queststatus:   empty
INVENTORY.LIST:             sentinel only
POCKET.GET values:          zero
SCORE.RANKING values:       zero
```

The controlled run proves that `ReadContent` converted a valid mature index into an empty logical result solely because of mtime metadata.

Evidence:

```text
device-snapshots/2026-08-30-response-index-timestamp-skew/v19-cold-skew.log
device-snapshots/2026-08-30-response-index-timestamp-skew/v19-cold-skew-index.bin
device-snapshots/2026-08-30-response-index-timestamp-skew/findings.json
test_v19_timestamp_skew_cold.py
```

The test's `finally` block reinstalled the production v20 APK and restored the pristine checkpoint.

### Relation to the natural event

The natural transition was:

```text
22:39:56  valid UploadPocket response: coin 983470, gem 99870, exp 2670
22:40:18  quest request 114 persisted
22:40:21  quest request 115 persisted
22:41:05  first zero POCKET.GET
22:41:20  zero-based GameStart persisted as new request 0
```

The regression archive later contained:

```text
index:      -1,0
request 0:  the 22:41:20 GameStart
records 103 through 115: still present and valid
```

Therefore two phases occurred:

1. At 22:41:05, reads already treated the mature pool as empty.
2. At 22:41:20, `SetRequest` persisted the empty interpretation by overwriting request zero and the index.

The second phase destroyed evidence about the first phase's exact file condition. The captured `-1,0` index has a valid timestamp and MD5 because it is the replacement file, not the rejected predecessor.

## Ranked lower-level explanations

### 1. Modification-time rejection — proven sufficient, natural occurrence unconfirmed

Strengths:

- Explicitly present in disassembly.
- Exact threshold recovered.
- Controlled metadata-only reproduction produces the same empty-history responses.
- The game's other local profile formats also contain “Verify ModifiedTime Fail” paths and use the same 10-second tolerance.
- Explains why timestamp preservation mattered during backup restoration.

Limitation:

- The pre-collapse index metadata from 22:41:05 no longer exists.

Possible origins of an mtime mismatch include:

- a restore/copy tool changing mtime without regenerating the encrypted timestamp;
- a root utility touching the file;
- a greater-than-10-second suspension between timestamp creation and final write;
- a system-clock adjustment during that narrow write interval;
- another code path rewriting metadata without rewriting the envelope.

### 2. Temporary `access` or `fopen` failure — plausible

A transient permission, descriptor, or filesystem error is converted directly to empty. No errno is returned to `CResponsePool`.

The device had correct stable ownership when inspected, and the failure happened after multiple successful reads, so a persistent UID problem is unlikely. A temporary open failure remains possible.

### 3. Short read or non-atomic write — plausible

`fread` and `fwrite` counts are unchecked, and writes truncate the authoritative path before producing the new bytes. A transient partial file would fail Base64/decrypt/integrity validation and be returned as empty.

The in-process mutex prevents an ordinary FileWorker reader/writer overlap, but it cannot protect against process death, storage errors, or external modification.

### 4. AES/Base64/MD5 validation failure — possible downstream result

Corruption, a partial read, or malformed padding can cause `Decrypt2` to return invalid content. No corrupt predecessor was preserved, so this cannot be confirmed or excluded for the natural event.

### 5. Normal in-process FileWorker race — unlikely and largely ruled out

Both read and write functions lock the same global `g_fileworkermutex` at `0x291ACC` across their full file and crypt operations. A standard concurrent call through these functions should not observe the target while another such call is truncating or writing it.

## Why captured healthy files all pass

The analyzer checked CCrypt2 files in three archives:

| Archive | CCrypt2 files | mtime deltas | Maximum absolute delta |
|---|---:|---|---:|
| Original 2016 backup | 22 | 21 at `0`, 1 at `+1` | 1 second |
| Healthy post-bonus checkpoint | 126 | 121 at `0`, 3 at `-1`, 2 at `+1` | 1 second |
| Captured regressed archive | 139 | 134 at `0`, 3 at `-1`, 2 at `+1` | 1 second |

The regressed archive passes because its bad index was newly and consistently rewritten as `-1,0`. Passing metadata does not mean its history pointer is semantically correct.

Reports:

```text
save-analysis/original-2016.json
save-analysis/post-bonus-level7.json
save-analysis/regressed-level8.json
```

## What v20 does and does not do

After the process has successfully parsed a mature index, v20 records a high-water value. A later empty result is treated as retryable, not as permission to create request zero.

This protects against every lower-level cause above when it is temporary:

- missing path;
- failed open;
- short read/decrypt failure;
- temporary metadata mismatch;
- temporary external file replacement.

If a condition is permanent, v20 waits instead of destroying history. That can produce a non-destructive softlock until the file or metadata is repaired.

If the index is invalid before the process has ever read it successfully, the high-water value is still zero and the original new-pool behavior remains available. This is necessary for the original 2016 backup, which legitimately contains no request-pool index.

## Additional instrumentation for a future natural event

The remaining uncertainty can only be eliminated by recording the first failed read before a later `SetRequest` overwrites evidence.

A diagnostic build should log, for the index filename only:

```text
access result and errno
stat result, st_size, and st_mtime
fopen result and errno
ftell length
requested and actual fread counts
outer Base64 success/failure
AES init/update/final success/failure
PKCS#7/prefix/MD5 validation status
presence of KEY, DATA, TIMESTAMP
embedded timestamp and mtime delta
current thread ID
request-pool caller: GetRequestSuite, GetRequestAll, or SetRequest
```

It should also copy the rejected bytes and stat metadata to a separate diagnostic filename before returning. That copy must not use the production index name.

Until such a natural capture exists, the correct conclusion is:

- **Established immediate mechanism:** a lower-level empty result reaches the response pool and is later persisted as a new zero-based pool.
- **Newly established sufficient lower condition:** an mtime/encrypted-timestamp difference greater than 10 seconds.
- **Best current candidate for the natural trigger:** timestamp rejection or another transient read/open/decrypt failure collapsed into the same empty return.
- **Not yet proven:** which one occurred at 22:41:05 in the natural session.
