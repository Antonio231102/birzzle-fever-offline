# Response-index diagnostics and staged recovery

## Failure classifier

`diagnose_response_index.py` conservatively classifies captured `REQUESTPOOLINDEX` records using envelope integrity, nested encoding, timestamp, range, and native field-parsing checks. It accepts a local file or pulls the live record through ADB and emits JSON; it does not replace runtime diagnosis of patched builds.

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
| `FIELD_MISSING_KEY` / `FIELD_MISSING_DATA` / `FIELD_MISSING_TIMESTAMP` | Required field absent under native parsing, including a trailing-empty field such as `KEY:` |
| `KEY_BASE64_INVALID` / `DATA_BASE64_INVALID` | Nested field encoding invalid |
| `TIMESTAMP_INVALID` | Embedded timestamp is not an integer |
| `MTIME_MISMATCH` | Filesystem mtime differs from the embedded timestamp by more than 10 seconds |
| `INDEX_PAYLOAD_INVALID` | Decoded `DATA` is not two decimal integers |
| `INDEX_RANGE_INVALID` | First/last indices violate the pool range invariant |
| `ACCEPT` | File passes all checks and yields a usable range |

`test_index_diagnostics.py` constructs and verifies every classification. This external classifier diagnoses a captured file; it cannot observe a transient short read after a later write has already repaired the same pathname.

Field parsing matches the native `std::getline` delimiter behavior and `map::insert`: trailing empty values do not create two-token fields, extra delimiters can invalidate a field, and the first duplicate field wins. Legacy nonempty tokens shorter than 16 bytes remain readable; only newly written V42 tokens must always contain the full digest.

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

## V42 empty-token prevention and narrow recovery

V41's `MathUtility::GenerateToken()` measured a binary MD5 digest with `strlen()`. A leading zero byte generated an empty token; an interior zero truncated it. The index could therefore retain valid encryption/checksum/mtime while becoming unreadable to native code. Existing mature-pool guards then retried indefinitely rather than discarding progression.

V42 replaces that length calculation at `libef2d.so:0x122ca6` with the constant 16. Existing integrity guards remain fail-closed; they are not redirected to the destructive virgin-pool fallback.

```text
python build_v42_binary_safe_tokens.py
python -m unittest test_index_diagnostics test_binary_safe_tokens -v
python repair_empty_index_token.py <original-app-data.tar.gz> <new-recovery.tar.gz>
```

The repair tool has no ADB access. It accepts only the checksum-valid exact empty-token envelope format, verifies all numbered records, replaces only the index token, and recomputes the envelope encryption/checksum. It preserves index bounds, timestamp/mtime, UID/GID, permissions, and all other archived data. A separate JSON report records hashes and preservation checks. Existing output files and other pool defects are refused.

Install the fixed APK before deploying a recovery. Prefer copying only the repaired index into a quiesced, freshly archived device save after confirming the live index/history still match the source. Map ownership to the installed package UID and preserve exact mtime. Do not reset the seed marker, delete numbered records, or grant the uncommitted reward. Device verification requires a fresh readiness handoff, recovered startup, legitimate mission claims, and cold restart; a host `CONSISTENT` report alone is not qualification.

### Archived S4 failure and V42 verification status

`ARCHITECTURE_HANDOFF.md` is frozen by operator instruction. Record subsequent findings in this document or the relevant existing topic documentation; create a new topic document only when needed. Do not update the handoff, including to remove previously added findings.

The September 2026 failure evidence is preserved under `device-snapshots/2026-09-20-s4-v41-mission-claim-failure/`:

- `failure_state/app-data.tar.gz` is the original pre-launch archive, SHA-256 `3846ba8d0ccadc47d1f3e47c551d631007301237219b5fa101e50d701dc66d94`.
- `failure_state/diagnosis.json`, `native-evidence.txt`, and `startup-backtrace.txt` document native rejection of the empty `KEY:` and the request worker sleeping inside `suite_retry_guard` at `libef2d.so+0x27bcc5`. Startup delivered `SERVER.INIT`, but no `POCKET.LOGIN` response followed.
- Records `0..18` remained intact. Quest claims 40 and 50 were persisted as records 17 and 18; quest 60 remained completed locally without a persisted claim. The original claim-time sequence is inferred from that state, not from a retained incident log.
- Both installed native libraries matched the exact V41 APK. The failure was local index rejection, not evidence of an online-backend switch.
- Historical `ACCEPT`/`CONSISTENT` analyzer reports are retained as evidence of the analyzer defect; use the corrected reports below instead.
- `post_startup_diagnostic/` preserves the state after the V41 diagnostic launch. The app was force-stopped; the index and all numbered requests remained unchanged. Startup changed `new2profile.dat` and analytics files. The later V42 pre-install capture below supersedes this historical device-state observation.

The replacement candidate is `native-patches/v42-binary-safe-tokens/BirzzleFever-1.1.2-v42-binary-safe-tokens.apk`, SHA-256 `72e02bf723969d857616b90520a0bfc6e877446dddac6c9316706be43e461506`. Its source is exact V41, SHA-256 `5a1ed5e21b5709c305251eb7b83340d7beb941f27f97ac9db1070fc13146cf88`.

- `build_v42_binary_safe_tokens.py` gates the source hashes, changes four bytes at the token-length call site, signs the APK, verifies its development signature, and checks that every other APK payload is unchanged.
- `native-patches/v42-binary-safe-tokens/build-report.json` and `host-verification.json` record the candidate hashes and host proof.
- Nine targeted regressions in `test_binary_safe_tokens.py` and `test_index_diagnostics.py` passed. ARM/Thumb emulation of the signed candidate's token call site, with external libc/Base64 hooks, covered zero bytes at every digest position plus all-zero and all-`FF` digests. This is not physical-device qualification.
- V42 retains V41's sanitized embedded seed, SHA-256 `654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c`, and the existing mature-pool fail-closed guards.

Recovery artifacts are under `device-snapshots/2026-09-20-s4-v42-token-recovery/`:

- `recovered-app-data.tar.gz` changes only the index envelope. All 19 numbered request records and the other 68 regular files are unchanged.
- The index payload remains `-1,18`; embedded timestamp and filesystem mtime remain `1789693266`. Ownership and permissions are preserved in the staged archive.
- `original-pool-corrected-analysis.json` reports `INDEX_REJECTED`; `recovered-pool-analysis.json` reports `CONSISTENT`.
- The adjacent repair report records archive/index hashes and preservation checks; `device-test-plan.json` pins the candidate, expected live history, deployment safeguards, and acceptance criteria.
- V42 and the repaired index were deployed after explicit readiness on 2026-09-20. `pre_install_failure_state/` preserves the freshly archived live failure; its index and all 19 records matched the original. Installation used `adb install -r`, retained UID 10269, and verified the installed APK and both native-library hashes.
- The index was replaced by a same-directory atomic rename, preserving timestamp/mtime `1789693266`, UID/GID 10269, and mode `0600`; `restorecon` was applied under enforcing SELinux. No other live save file was restored.
- `00_repaired_baseline/manifest.json` captures the quiesced, pre-first-launch V42 state: `CONSISTENT`, index `-1,18`, 19 valid records, and all other 68 files byte-identical to the fresh pre-install archive. This is a storage baseline, not a gameplay pass.
- `deployment-report.json` and `launch-report.json` record installation and launch. Service `birzzle-v42-manual-log` captured `.omp/current_test_log.txt` and `manual-session.log` throughout the manual test, then was stopped after evidence preservation. Android 4.4.2 has no separate `/dev/log/crash`; the mandatory bootstrap's crash-buffer clear reports that absence, while main-buffer clearing and launch succeed.

The targeted V42 recovery/mission/restart regression passed on 2026-09-20. The user's verbatim report is preserved in `01_mission_claim_restart/operator-report.json`: successful main-menu startup, the previously pending claim, a completed game and two further claims back-to-back, then a restart with progression retained. The game was force-stopped only after the user returned control for capture.

The user alone performs taps and visual judgments. Verify recovered startup, retained progression, the remaining claim, successive legitimately earned mission claims, and cold restart. At the first anomaly, preserve the report and failure evidence without retrying, resetting, or repairing further. Maintain the `.omp/current_test_log.txt` capture; inspect package-scoped messages and relevant severe failures, and remind the user to run `/shake` after log analysis.

`targeted-device-verification.json` records the evidence:

- The exact installed V42 APK hash remained unchanged. The post-test archive is `01_mission_claim_restart/app-data.tar.gz`, SHA-256 `9fc9916ee1d1a94baa35d5c7b063707b72c1491122911eaa53fe7525f1724957`.
- The response pool advanced from `-1,18` to `-1,26`: 27 valid contiguous records, no invalid records or semantic warnings, and all original records `0..18` byte-identical.
- Eight records were added: four `pocket.set`, one `custom.post`, and three `quest.update.status`. The claims are quest 60 at record 19, quest 80 at record 25, and quest 20 at record 26.
- All 17 newly created or changed CCrypt2 envelopes contain full 16-byte tokens, valid envelope digests, and matching timestamp/mtime checks. The new index token contains a zero byte at offset 1, and request 21's token contains one at offset 7; neither was truncated. This exercises the binary-length fix on the physical device.
- The optional `stage.dat` cache has empty `DATA` both before and after this test. This pre-existing empty payload is not a token defect; its new `KEY` is 16 bytes. All actual response-pool records and the index pass native field validation.
- Package-scoped lifetime logs cover both app processes across the restart. No fatal, ANR, or request-timeout markers were detected.
- The existing comparator's artifact, pool, tar-hash, summary, and adjacent-record validators were reused. This is a storage-only baseline comparison, not a claim that the full comparator CLI passed: `00_repaired_baseline` predates the first V42 launch and intentionally has no runtime log artifact. No missing log was fabricated.

At the end of this archived instrumented regression, the game was force-stopped, log capture was stopped, and the original failure archive was unchanged. That evidence remains limited to the recovered-save regression. The operator subsequently reported all eight V42 functional release checks passed on the Galaxy S4/Android 4.4.2 and Galaxy S20 Plus/Android 13, without observed progress loss, crashes, freezes, or softlocks. Those later sessions intentionally collected no logs or save backups and must not be conflated with these earlier captures. See [docs/TESTING.md](docs/TESTING.md) for the accepted manual results, non-decreasing lives-counter behavior, evidence limits, and user-report follow-up policy. No new fault-injection coverage is asserted.

### V42 destructive integrity follow-up — 2026-09-22

The release-signed APK was verified on the S4 and the then-current `-1,92` save was backed up before faults. Timestamp offsets +10/+11/+60, missing index, and empty index passed preservation and backend-recovery checks; all 93 prior records remained unchanged.

The initial truncated-index injection reached `SERVER.INIT` and held without writing/resetting the pool. Its restored recovery process received a kernel SIGKILL before offline initialization completed, so that attempt was retained as inconclusive and further faults were paused.

The original save was restored exactly across all 155 archive members before the user rebooted. On resumption, clean startup and all five remaining read-fault cases passed: truncated index, invalid padding, wrong checksum, valid-envelope empty key, and missing referenced record. All 93 prior records and stable progression values were preserved. The combined read-fault matrix now has ten passes.

The first interrupted-write boundary passed data-preservation and recovery-idempotence checks: a complete but unindexed `GameStart` record was captured at the verified pause, all 93 committed records survived, and production recovery reused the uncommitted slot for a new `UploadPocket heart=1` request. Hearts increased once from 5 to 6; a second restart made no further request or change. This life adjustment is recorded separately, not silently treated as an unchanged pocket or adjudicated as intended gameplay behavior.

The second diagnostic was armed before atomic rename, but its process received a kernel SIGKILL before the manual trigger. No new request 93 or save request was present; the second boundary was not reached. Evidence was captured before the harness's force-stop. The operator subsequently reported repeated launcher crashes/restarts and broader instability that continued after the game was terminated and resolved after reboot. This supports a likely device-wide explanation; the exact trigger remains unconfirmed. The recorded events were process SIGKILLs, not confirmed kernel crashes.

At that stop, the production native library and original save were restored and verified. After another operator-authorized reboot, the pre-rename case passed: old committed index `-1,92`, complete temporary index `-1,93`, valid request 93, and the diagnostic pause were captured before interruption. Production recovery preserved all prior records, removed the temporary index, wrote one `UploadPocket heart=1`, and remained stable on a second restart. This life adjustment is recorded separately from the data-integrity verdict.

The final post-rename/pre-directory-fsync boundary also passed. At interruption, the index was valid at `-1,93`, the temporary file was absent, and the native backtrace confirmed the intended pause. Production recovery retained all 94 committed records, including `GameStart` record 93, byte-for-byte. It appended one `UploadPocket heart=1` at record 94 and remained stable on a second restart with all 95 recovered records unchanged. Evidence: `09_after_rename_result.json`.

The completed matrix contains ten read-fault cases and three controlled process-interruption boundaries. This is not power-loss or storage-cache-loss testing. All three boundary recoveries included a one-time life increase (5 to 6) that did not repeat; its intended unlimited-heart semantics remain a separate observation. Earlier kernel-kill and verifier limitations remain preserved.

Final restoration is complete: exact production library and metadata verified, signed APK unchanged, all 148 original regular save files byte-identical, and all 155 members matching expected post-reboot metadata. The pool is restored to `CONSISTENT`, `-1,92`, with all 93 original records unchanged. The game is force-stopped, logging is stopped, temporary device staging is removed, and no diagnostic library is active. See [docs/TESTING.md](docs/TESTING.md) and `device-snapshots/v42-destructive-integrity-20260922T010140Z/resume-20260922T012755Z/final-integrity-verification.json` for the final evidence and scope.

## Observed fixtures

| Source | Classification | Range / evidence |
|---|---|---|
| Original May 2016 backup | `VIRGIN_NO_POOL` | No index or numbered requests |
| Known-good post-bonus level-7 checkpoint | `CONSISTENT` | `0..102`, index `-1,102` |
| Regressed level-8 snapshot | `INDEX_STALE_OR_COLLAPSED` | Valid `0..115`, index collapsed to `-1,0`, request zero newer than request one |
| Restored live clean checkpoint | `CONSISTENT` | `0..102`, index `-1,102` |
| September 2026 V41 mission-claim failure | `INDEX_REJECTED` | Intact records `0..18`; index `-1,18` has empty `KEY:` |
| V42 index-only recovered baseline | `CONSISTENT` | Pre-launch `0..18`; unchanged history and preserved index timestamp |
| V42 mission-claim/restart regression | `CONSISTENT` | `0..26`, three successful claim records, prior records unchanged, new tokens all 16 bytes |

Reports are in `save-analysis/pool-*.json`. The write ordering and transaction implications are documented in `POST_GAME_COMMIT_ORDER.md`.
