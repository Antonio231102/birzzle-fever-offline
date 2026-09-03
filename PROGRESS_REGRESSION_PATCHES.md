# Birzzle Fever progress-regression patches

## Scope

This document is the historical implementation record for the v19 consumer guards and v20 response-pool index-retention patch. It covers:

- the defensive state guards finalized in v19;
- the response-pool index retention fix added in v20;
- the v19/v20 binaries and ELF metadata;
- exact library-relative offsets and replacement bytes;
- why those modifications address the observed global state reset;
- the device and fault-injection results available at the v20 milestone.

The artifact documented in detail here is the historical v20 build:

```text
native-patches/v20-request-index-retention/BirzzleFever-1.1.2-v20-request-index-retention.apk
SHA-256: 81810c075f6c330e1823dce8f40b82d7a9a96376a7ef1a9310b9c4270728b17d
```

The current development candidate is v25. It retains the unclamped v15 `libbirzzle.so`, v23's response-pool and request-first atomic-index hardening, and adds the connectivity-independent local route, sanitized exact-timestamp seed, GCM removal, and stable two-slot ranking template. See `V25_PROJECT_STATUS.md` for current artifacts, exact-candidate validation, remaining risks, and release work.

Offsets below are relative to the corresponding ELF image. In these library layouts, the first executable `PT_LOAD` has matching file and virtual offsets, so the listed hook offsets are also the patcher's file offsets. Runtime addresses are relocated by Android's loader and therefore differ by the library load base.

## V20 APK composition and patch lineage

The v20 APK builder starts from the signed v19 APK, removes its old `META-INF` signatures, replaces both native libraries, and signs the result with the existing Android debug key.

| APK entry | Final source | SHA-256 | Role |
|---|---|---|---|
| `lib/armeabi/libbirzzle.so` | `native-patches/v20-request-index-retention/libbirzzle.so` | `7f1ac005cf17355c29a4dca4668b233322c0f2e18b9e94ebced1ca7359971884` | v19 pocket and inventory guards, on top of the existing v15 gameplay/portability patch set |
| `lib/armeabi/libef2d.so` | `native-patches/v20-request-index-retention/libef2d.so` | `291247fa42e11070ad30b4c6c0f4554535ba24d1252b88b635929343c29c21e2` | v20 response-pool index retention and retry fix |
| `assets/birzzle_seed_v1.zip` | retained from the preceding portable APK | `3199dd10257d553c22b7b83e9ca1d7075210b8a1a5f57221206726d87f120176` | self-seeding save payload; unchanged by this work |

Relevant builders and patchers:

```text
patch_authoritative_gem_guard_v19.py
build_v19_portable_apk.py
patch_request_index_retention_v20.py
build_v20_portable_apk.py
```

The v16, v17, and v18 libraries were investigative iterations. The production APK does not layer all three intermediate guard binaries. Its `libbirzzle.so` is the finalized v19 guard implementation, built directly from the v15 library.

## Observed regression and root cause

### User-visible failure

During a natural level-8 session, the last valid completed-game response reported:

```text
coin = 983470
gem  = 99870
exp  = 2670
```

A later `POCKET.GET` unexpectedly returned all three values as zero. The v18/v19 pocket guards could preserve selected in-memory values, but subsequent inspection proved that the event was not merely a pocket-field problem:

- `POCKET.LOGIN` returned `queststatus: []`;
- `INVENTORY.LIST` contained only its sentinel row;
- acquired pets were gone;
- mission state returned to the initial Rookie state;
- subsequent requests were calculated from the zero-history state.

Evidence:

```text
device-snapshots/2026-08-29-level8-progression/regression.log
device-snapshots/2026-08-29-level8-regression-state-verification/verification.log
device-snapshots/2026-08-29-level8-progression/regression-live-data.tar.gz
device-snapshots/2026-08-29-level8-progression/regression-stopped-data.tar.gz
```

### Response-pool persistence format

The offline server implemented by `libef2d.so` persists requests in a shared response pool. The index filename is:

```text
MD5(historical_uid + "REQUESTPOOLINDEX")
= 5f7d50ff681a65b10550a631e11a2ded
```

The historical UID is:

```text
3c8bb7308c3fcb60c439224bd595c794d8f31501
```

Individual request filenames are:

```text
MD5(historical_uid + "REQUESTPOOL_" + decimal_request_index)
```

The index payload is Base64-wrapped AES-128-ECB data using the game's key `miaeHgpdskiinerS`. Its `DATA` field contains the first and last replay indices.

Observed index evolution was internally consistent during normal progression:

| Checkpoint | Decrypted index |
|---|---:|
| Level 3 | `-1,35` |
| Level 4 | `-1,44` |
| Level 5 | `-1,60` |
| Level 6 | `-1,78` |
| Level 7 | `-1,99` |
| Post-bonus level 7 | `-1,102` |
| Regressed state | `-1,0` |

The request records beyond index zero were not deleted. In the captured regression, orphaned indices 103 through 115 still decrypted correctly and contained the later game starts, completions, quest updates, and rewards. Only the authoritative index had been replaced with `-1,0`.

### Failure mechanism

The relevant original `libef2d.so` functions are:

| Function | Offset |
|---|---:|
| `CResponsePool::clearRequestQueue` | `0x12BB4C` |
| `CResponsePool::ResetIndex` | `0x130828` |
| `CResponsePool::GetRequestSuite` | `0x130F10` |
| `CResponsePool::GetRequestAll` | `0x1314C0` |
| `CResponsePool::SetRequest` | `0x131D58` |
| `CResponsePool` constructor | `0x1321E0` |
| `calcInventory` | `0x1345F4` |
| `calcPocketLogin` | `0x134EE8` |
| `calcQuestUpdateStatus` | `0x135774` |
| `calcPocketGet` | `0x135E68` |
| `calcRanking` | `0x136630` |

`GetRequestSuite`, `GetRequestAll`, and `SetRequest` each read and parse the same encrypted index. Their original empty-content paths treat an empty `ReadContent` result as a genuinely new pool. If a mature index is transiently read as empty, `SetRequest` creates request zero and writes an index ending at zero. Every reconstructed domain then replays only that truncated pool. This explains why pocket, inventory, pets, quests, missions, and ranking-related state could regress together.

The v20 fix therefore protects the shared index read rather than adding more field-specific clamps.

## v19: defensive pocket and inventory guards

### Modified binary

```text
APK entry: lib/armeabi/libbirzzle.so
Output:    native-patches/v19-authoritative-gem-guard/libbirzzle.so
Source:    native-patches/v15-portable-no-heart-deduction/libbirzzle.so
Source SHA-256: bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae
Output SHA-256: 7f1ac005cf17355c29a4dca4668b233322c0f2e18b9e94ebced1ca7359971884
```

Implementation sources:

```text
native-patches/v19-authoritative-gem-guard/guards.S
native-patches/v19-authoritative-gem-guard/guards.bin
patch_authoritative_gem_guard_v19.py
```

`guards.bin` is 302 bytes and occupies `0x2ACEC0` through `0x2ACFED` inclusive.

### Hook modifications

| Offset | Original bytes | Final bytes | Destination | Purpose |
|---:|---|---|---:|---|
| `0x16B04A` | `FE F7 BB FE` | `41 F1 39 BF` | `pocket_guard` at `0x2ACEC0` | Guard parsed `POCKET.SET` responses before normal state consumption. |
| `0x16F51E` | `FA F7 51 FC` | `3D F1 E6 BC` | `get_pocket_guard` at `0x2ACEEE` | Strictly guard every `POCKET.GET` response. |
| `0x16D7A2` | `A1 F7 2D FD` | `3F F1 03 BC` | `inventory_guard` at `0x2ACFAC` | Reject a parsed inventory snapshot that is shorter than the already-owned pet set. |
| `0x2ACEC0` | 302 zero bytes | `guards.bin` | executable cave | Store the Thumb guard routines and diagnostic strings. |

### Pocket guard behavior

The guard compares parsed response values with the game's already-authoritative safe-number storage:

| Value | Parsed pocket field | Existing authoritative source |
|---|---:|---|
| Coin | pocket object `+0x2C` | `safe_get(ccash_get() + 0x40)` |
| Gem | pocket object `+0x30` | `safe_get(ccash_get() + 0x20)` |
| Experience | pocket object `+0x34` | `safe_get(exp_get())` |

If an incoming value is below the authoritative value, the guard writes the authoritative value back into the parsed response and emits:

```text
BirzzleGuard: POCKET CLAMP <authoritative> <incoming>
```

`POCKET.GET` is always strict. `POCKET.SET` uses the response's `extradata` to avoid blocking legitimate spending or ordinary state transitions:

- values beginning with `G` use strict clamping;
- values beginning with `U` whose third character is `l` use strict clamping;
- values beginning with `U` whose third character is `d` first compare experience; all three fields are clamped only when experience itself regresses;
- other response types continue through the original path.

The gem source was corrected in v19 to `ccash_get() + 0x20`. The earlier v18 experiment used the wrong safe-number member and therefore did not protect the actual gem balance.

### Inventory guard behavior

The inventory guard:

1. gets the current owned-pet count;
2. gets the number of parsed inventory-table rows;
3. subtracts the mandatory sentinel row;
4. allows the response when the parsed count is at least the existing pet count;
5. otherwise logs `INVENTORY REJECT <existing> <parsed>` and branches to the response-rejection cleanup path.

This prevents an empty or truncated inventory response from immediately deleting an already-loaded pet collection.

### Contribution and limitation

The v19 guards prevent selected bad responses from overwriting already-loaded pocket and pet state. They are valuable defense in depth and provide diagnostics. They do not protect mission/quest history, do not repair the response-pool index, and cannot recover state that was already lost before the authoritative objects were populated. The regressed-state verification demonstrated this limitation and motivated v20.

## v20: response-pool index retention and retry

### Modified binary

```text
APK entry: lib/armeabi/libef2d.so
Original:  native-patches/v20-request-index-retention/libef2d-source.so
Output:    native-patches/v20-request-index-retention/libef2d.so
Original SHA-256: cfd0c07ee435afcf07d827acd2ae5d3774bc4e6cc0a24a4e4e96e3663eb9d91b
Output SHA-256:   291247fa42e11070ad30b4c6c0f4554535ba24d1252b88b635929343c29c21e2
```

Implementation sources:

```text
patch_request_index_retention_v20.py
native-patches/v20-request-index-retention/index_retention.S
native-patches/v20-request-index-retention/index_retention.bin
native-patches/v20-request-index-retention/index_retry.S
native-patches/v20-request-index-retention/index_retry.bin
```

The original library and final library are both 2,701,512 bytes. Existing zero padding was converted into executable code, so the file did not need to grow.

### Hook modifications

| Offset | Original bytes | Final bytes | Active destination | Purpose |
|---:|---|---|---:|---|
| `0x13107A` | `00 D1 40 E1` | `4A F1 4D BE` | `suite_retry_guard` at `0x27BD18` | Intercept the empty/non-empty decision in `GetRequestSuite`; retry mature-pool reads instead of accepting a transient empty result. |
| `0x1310BE` | `05 9B 0D 98` | `4A F1 E4 BD` | `suite_valid_guard` at `0x27BC8A` | Capture `last + 1` after a valid suite-index parse, then reproduce the overwritten loads/comparison and resume at `0x1310C4`. |
| `0x1315A2` | `00 D1 D5 E1` | `4A F1 E8 BB` | `all_retry_guard` at `0x27BD76` | Apply the same mature-pool retry rule in `GetRequestAll`. |
| `0x1315E4` | `08 99 00 23` | `4A F1 70 BB` | `all_valid_guard` at `0x27BCC8` | Capture `last + 1` after a valid all-request index parse and reproduce the overwritten setup instructions before resuming at `0x1315E8`. |
| `0x131E52` | `9A 42 00 D1 55 E1` | `49 F1 BF BF 00 BF` | `set_retry_guard` at `0x27BDD4` | Intercept `SetRequest` index emptiness. A mature pool waits for a readable index rather than entering the original create-index-zero path. |
| `0x131E94` | `63 1C DA 43` | `49 F1 36 BF` | `set_compute_guard` at `0x27BD04` | Update the remembered next index to `new_last + 1`, reproduce the overwritten arithmetic, and resume at `0x131E98`. |

The `GetRequestSuite` and `GetRequestAll` hooks deliberately replace only the two original branch instructions. Their first normal-path instructions at `0x13107E` and `0x1315A6` remain intact.

### Injected code and state

| Range/address | Size | Contents |
|---|---:|---|
| `0x27BC50`–`0x27BD15` | 198 bytes | `index_retention.bin`: position-independent high-water accessor, valid-index capture routines, and `SetRequest` high-water update routine. |
| `0x27BD18`–`0x27BE31` | 282 bytes | `index_retry.bin`: safe retry paths for suite, all-request, and set-request index reads. |
| `0x294624` | 4 bytes | New zero-initialized `request_highwater` word in `.bss`. It stores the next valid request index. |

The first blob also contains earlier synthetic empty-index helpers at `0x27BC64`, `0x27BCA2`, and `0x27BCE0`. The production hook table does not target those routines. They are inert. Production empty-index handling uses the later retry routines so that the original string parsing, vector construction, destruction, and cleanup paths remain intact.

Active helper addresses:

| Helper | Offset |
|---|---:|
| `get_highwater` | `0x27BC50` |
| `suite_valid_guard` | `0x27BC8A` |
| `all_valid_guard` | `0x27BCC8` |
| `set_compute_guard` | `0x27BD04` |
| `suite_retry_guard` | `0x27BD18` |
| `all_retry_guard` | `0x27BD76` |
| `set_retry_guard` | `0x27BDD4` |

The retry routines reuse the game's existing implementations:

| Routine | Offset |
|---|---:|
| string copy constructor | `0x0A08AC` |
| `FileWorker::instance` | `0x1210D4` |
| `FileWorker::ReadContent` | `0x1215A8` |
| node deallocator | `0x209FF4` |
| `operator delete` | `0x1ED7B4` |

### ELF metadata modifications

The injected code and new state must be covered by loadable segments:

| ELF field | Original | Final | Reason |
|---|---:|---:|---|
| Executable `PT_LOAD.p_filesz` | `0x27BC4C` | `0x27BE32` | Include both injected Thumb blobs in the executable mapping. |
| Executable `PT_LOAD.p_memsz` | `0x27BC4C` | `0x27BE32` | Map the injected bytes at runtime. |
| Read/write `PT_LOAD.p_memsz` | `0x18624` | `0x18628` | Reserve four additional bytes for `request_highwater`. |
| `.bss` section size | `0x4084` | `0x4088` | Describe the new zero-initialized word at `0x294624`. |

The read/write segment ends at `0x294628` after this change.

### Runtime invariant

The production invariant is:

1. A successful index parse records `highwater = last + 1`.
2. A successful `SetRequest` updates it to the next index after the newly appended request.
3. A non-empty read follows the original parser unchanged.
4. An empty read with `highwater == 0` follows the original empty-pool behavior. This preserves legitimate first initialization.
5. An empty read with `highwater > 0` cannot be treated as a fresh pool. The code preserves registers, constructs a temporary filename string, and retries `FileWorker::ReadContent` until the existing index becomes readable. It then frees the temporary string and rejoins the original non-empty parse path.

The high-water word is process-local by design. It distinguishes a mature pool from a genuinely new pool after at least one valid read in the current process. The persistent index remains the cross-restart source of truth. The patch prevents a transient in-session read failure from replacing that source of truth with index zero.

This trades a possible temporary wait during persistent I/O failure for preservation of save history. If the index is permanently missing before any valid read in a new process, the original initialization behavior remains; the patch does not attempt to reverse hashed filenames or reconstruct an already-deleted index across a restart.

## Why the combined patch achieves the goal

The two libraries defend different layers:

1. **v20 protects the source of reconstructed state.** It prevents the common response-pool index from being reset to zero after a transient empty read. Because pocket, inventory, pets, quests, missions, and ranking all replay from this pool, preserving the index protects the complete progression history rather than individual symptoms.
2. **v19 protects consumers of reconstructed state.** If an anomalously lower pocket or truncated inventory response still reaches the game, loaded coin/gem/experience and pets are not blindly overwritten.
3. **Existing v15 and earlier patches remain present.** The current `libbirzzle.so` still includes the preceding portability, leaderboard-flow, historical-device-ID, and unlimited-life behavior. The regression work did not replace those fixes.

The desired state transition is therefore:

```text
valid encrypted index
        |
        v
record high-water mark
        |
        +-- normal read ----------------------> original replay path
        |
        +-- transient empty read
                  |
                  v
             retry same index
                  |
                  v
        original replay path, full history retained
```

The destructive transition is no longer allowed for a mature in-process pool:

```text
transient empty read -X-> create request 0 -X-> overwrite index as -1,0
```

## V20 validation record

### Production-APK live disappearance test

The final production v20 APK was installed over a clean post-bonus checkpoint whose index decrypted to `-1,102`. After the main menu and high-water capture completed:

1. the index file was physically renamed out of the files directory;
2. the final `Let's Play` action issued a real `pocket.set` with `extradata=GameStart`;
3. the index remained absent for three seconds;
4. the file was restored while the request was pending;
5. the process remained alive and completed the response.

The returned `POCKET.SET` contained:

```text
coin  = 982920
gem   = 99870
exp   = 2200
heart = 5
```

No `POCKET CLAMP` was needed, proving that `libef2d.so` reconstructed the authoritative values itself rather than relying on the v19 symptom guard. The encrypted index then decrypted to `-1,103`, the correct append after the original `-1,102`; it did not become `-1,0`.

Evidence:

```text
native-patches/v20-request-index-retention/verified-live-empty-index.log
native-patches/v20-request-index-retention/post-fault-index.bin
```

### Full-domain forced-reread test

A separate test-only APK forced mature `SetRequest` calls through the reread path even when the first read was valid. The process remained alive and loaded:

- `POCKET.LOGIN` with quest history;
- the expected `INVENTORY.LIST` pet rows;
- pocket values `982920 / 99870 / 2200`;
- the normal `SCORE.RANKING` response.

Evidence:

```text
native-patches/v20-request-index-retention/final-forced-reread.log
```

The test-only APK and `force_retry_after_capture.S` are fault-injection artifacts, not production components.

### Five corrected cold launches

After the live fault test, the clean checkpoint was restored and the production APK was left installed. A menu-aware runner performed five cold launches. Each launch was allowed to continue until the `SCORE.RANKING` response proved that the main menu and leaderboard had loaded.

Results:

| Check | Result |
|---|---:|
| Process alive at main menu | 5/5 |
| `SCORE.RANKING` reached | 5/5 |
| Pocket values `982920 / 99870 / 2200` preserved | 5/5 |
| `INVENTORY.LIST` loaded | 5/5 |
| Fatal native signals | 0/5 |
| Java fatal exceptions | 0/5 |

After all five launches, the index file was byte-identical to the clean checkpoint:

```text
SHA-256: 6bbdcb0b6ef5de72adc5fcc14bb188e734cf4daf0b7190209e62a89472858e6a
Decrypted DATA: -1,102
```

Evidence:

```text
native-patches/v20-request-index-retention/cold-launch-stress-complete/launch-1.log
native-patches/v20-request-index-retention/cold-launch-stress-complete/launch-2.log
native-patches/v20-request-index-retention/cold-launch-stress-complete/launch-3.log
native-patches/v20-request-index-retention/cold-launch-stress-complete/launch-4.log
native-patches/v20-request-index-retention/cold-launch-stress-complete/launch-5.log
native-patches/v20-request-index-retention/final-stress-index.bin
stress_v20_cold_launch.py
```

An earlier fixed-delay runner stopped three processes after 14 seconds, before the Galaxy S4 had reached the main menu. Those terminations were caused by the runner's own `am force-stop`, not by a game crash, and the logs under `cold-launch-stress/` are not valid stability results. The corrected runner waits for the main-menu ranking response before beginning the next cold launch.

## V20 milestone conclusion

The v20 tests established that:

- the shared response-pool index was the mechanism behind the observed global progression reset;
- v19 alone could mask selected pocket values but could not protect quests, pets, or the underlying history;
- the v20 retry path survived a real three-second disappearance of the index during `GameStart`;
- the resulting response contained the full authoritative state without v19 clamping;
- the next request index advanced correctly instead of resetting to zero;
- five clean cold launches preserved the checkpoint and reached the main menu without crashes.

Later v21-v25 work retained this root fix, removed the v19 clamps from the production lineage, added persistent maturity and missing-record guards, tested first-read and mid-session faults, corrected atomic write ordering, reconciled post-restart progression, removed the obsolete network-interface dependency, and validated APK-only self-seeding. The current defensible conclusion is documented in `V25_PROJECT_STATUS.md`: the reproduced destructive reset is mitigated for every tested trigger, while long in-process index unavailability and the uncaptured exact natural trigger remain caveats.
