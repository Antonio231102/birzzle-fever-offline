# Stage E: interrupted writes

## Result

Stage E passed with the v23 request-first index candidate on the Galaxy S4.

Testing exposed an unsafe ordering in v22: `CResponsePool::SetRequest` committed the atomic index before writing the numbered request. Killing at that boundary produced a valid `-1,157` index with request 157 absent. V23 preserves every v22 patch and swaps the two existing data/path register pairs, so the numbered request is written first and the atomic index is committed second.

All four accepted cases cold-launched to a consistent response pool. Request zero remained byte-identical. No clamp marker was observed.

## Candidate

- APK: `../../BirzzleFever-1.1.2-v23-request-first-index.apk`
- APK SHA-256: `4c679deadd186016ad8d25eeb9b213724d3f43b52f9e7e6285576ea8bf703297`
- `libef2d.so` SHA-256: `a66f91a1e498c325d4f9ef8e78df5bd4f71d4fce44b6fbcb5d51425eb3e83145`
- Parent v22 `libef2d.so` SHA-256: `64c083f7d3b614b77f09cdf38259577eccca8fc2276d67e6ba04209116ede0ae`
- Final installed package UID/GID: 10234.

V23 changes four two-byte Thumb register moves in `CResponsePool::SetRequest`; the request and index serialization logic, v22 first-read guards, atomic temporary-file writer, leaderboard fixes, device-ID patch, and unlimited-lives patch are unchanged.

## Baseline

```text
classification:     CONSISTENT
index:              -1,156
valid records:      157
index SHA-256:       c75e925c83ce92d7157f77306b123eb0e7e5944f3926e0d623edb55ed8813d07
request 0 SHA-256:   5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2
```

## Matrix

| Termination boundary | State at termination | Cold-launch result |
|---|---|---|
| Numbered request complete, before index write | Request 157 valid `GameStart`; live index remained `-1,156`; no temporary index | `-1,157`, `CONSISTENT` |
| Temporary index complete, before rename | Request 157 valid; live index `-1,156`; temporary index valid `-1,157` | `-1,157`, `CONSISTENT` |
| Immediately after rename, before directory `fsync` | Live index `-1,157`; request 157 valid; no temporary index | `-1,158`, `CONSISTENT` after normal interrupted-game recovery append |
| Shutdown after completed game | Pool `-1,158`, `CONSISTENT` before shutdown | `-1,158`, `CONSISTENT` |

The first two interrupted snapshots are classified `INDEX_STALE_OR_COLLAPSED` because a complete orphan request 157 exists beyond the still-valid previous index `-1,156`. This is the intended previous-valid-index side of the acceptance criterion. The next launch safely advances the index to include the durable record.

## Invariants

Every accepted boundary case satisfied the applicable invariants:

- the process was alive and paused at the exact intended boundary;
- request 157 was complete and decoded as `pocket.set` with `extradata=GameStart`;
- the active index was either the previous valid `-1,156` or new valid `-1,157`;
- the next launch produced a `CONSISTENT` pool;
- request zero retained SHA-256 `5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2`;
- no invalid records or semantic warnings remained after recovery;
- no `POCKET CLAMP` or `INVENTORY CLAMP` marker appeared.

## Excluded diagnostics

The first v22 ordering probe is preserved under the v22 Stage E directory. It proved that v22 wrote the index first: the snapshot contained index `-1,157` but no request 157. This run drove the v23 ordering fix and is not an accepted v23 result.

An initial v23 pause stub used an infinite Thumb branch. It saturated the diagnostic game thread and, together with repeated rooted file polling, made the Galaxy S4 unresponsive; the user force-rebooted it. Evidence is retained in `kill-before-index-write-invalid-spin-freeze/`. Accepted diagnostics instead execute the ARM `pause` syscall directly, blocking without consuming CPU.

A later accepted pre-index run could not perform its final rollback because the first v23 package was signed with an Android-4.4-incompatible JAR digest. It is retained in `kill-before-index-write-invalid-production-signature/`. Production v23 was re-signed with SHA-256 and the complete case was rerun successfully.

## Evidence

- Production builder: `../../../build_v23_request_first.py`
- Diagnostic builder: `../../../build_stage_e_boundary_diagnostics.py`
- Harness: `../../../test_stage_e_interrupted_writes.py`
- Aggregate results: `results.json`
- Pool analysis: `matrix-analysis.json`
- Final restored device pool: `final-device-pool.json`
- Diagnostic manifest: `diagnostics/manifest.json`
- Per-case boundary proof: `<case>/boundary-state.json`
- Per-case interrupted and recovery pools: `<case>/interrupted-pool.json`, `<case>/recovery-pool.json`
- Completed-game pools: `shutdown-after-completed-game/completed-before-shutdown-pool.json`, `shutdown-after-completed-game/recovery-pool.json`

The Galaxy S4 is left with production v23 installed, the mature `-1,156` baseline restored, the original 30-second screen timeout restored, and Birzzle Fever force-stopped.
