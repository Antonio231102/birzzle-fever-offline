# Birzzle Fever v21-v25 regression-hardening roadmap

## Established state

The unclamped v20 control passed an eleven-game progression session covering spending, pet upgrades and selection, quests, two level-ups, completed games, an aborted game, power-up cancellation, Mystery Boxes, and repeated main-menu transitions.

The response pool remained contiguous from `0..102` through `0..156`. The pocket cache and proprietary profiles agreed at shutdown. No crash, ANR, softlock, or UI-visible progression regression occurred.

This establishes that the v19 pocket/inventory clamps are not required for the reproduced response-pool regression. The v21-v25 production lineage therefore uses the successful unclamped `libbirzzle.so` while preserving the historical identity, leaderboard, common menu-transition, and unlimited-play patches.

## Validation status

- **Stage A — legitimate virgin initialization: passed on exact V25.** A clean APK-only installation self-seeded the sanitized 26-file bundle with no root, Titanium Backup, pre-existing ranking cache, or manual UID repair. The user acquired Suri, completed three games, missions, level 2, bonus mode, and the pet-upgrade tutorial. The pool remained consistent at `-1,16`; ranking advanced to `257680` and persisted across a cold restart without fatal markers. Evidence: `native-patches/v25-ranking-template/evidence/fresh-v25-progression-pool.json`.
- **Stage B — healthy mature cold starts: passed on exact V25.** Ten of ten launches loaded 980,800 coins, 99,870 gems, 3,810 EXP, Suri ability 10, Polo, and ranking score 1,017,964. The pool remained `-1,156`; the index and request zero stayed byte-identical. Evidence: `native-patches/v25-ranking-template/evidence/mature-cold-starts/results.json`.
- **Stage C — first-read fault injection: passed on exact V25.** Mtime deltas `+10`, `+11`, and `+60` loaded directly. Missing, zero-length, truncated, invalid-padding, wrong-MD5, and missing-numbered-record faults entered a non-destructive controlled wait; force-stop, repair, and cold launch restored the exact mature state. Evidence: `native-patches/v25-ranking-template/evidence/first-read-faults/accepted-results.json`.
- **Stage D — mid-session faults: passed on v23 for short transients.** During real `GameStart`, temporary index removal, mtime `+60`, mode `000`, and zero-length replacement recovered after approximately two seconds and appended request 157 without clamps. Cold restart appended the normal interrupted-game refund as request 158; both pools were consistent and request zero remained unchanged. The root-induced 17-second missing-index diagnostic remains outside ordinary operation. Evidence: `native-patches/v23-request-first-index/stage-d-mid-session-faults/`.
- **Stage E — interrupted writes: passed on v23.** Request-first commit ordering cold-recovered to the previous or new valid index at every tested write boundary. Every recovery pool was consistent, request zero remained byte-identical, and no clamp ran. Evidence: `native-patches/v23-request-first-index/stage-e-interrupted-writes/`.
- **Stage F — post-restart progression: passed on v23, with additional fresh progression on V25.** V23 reconciled pocket, EXP, inventory, quest progress, and pool after restart. V25 additionally preserved its three-game fresh-install progression and ranking across a cold restart. Evidence: `native-patches/v23-request-first-index/stage-f-post-restart-progression/` and `native-patches/v25-ranking-template/evidence/fresh-v25-cold-restart.log`.

All six roadmap stages have accepted results, and the version-sensitive A-C matrices now pass on exact V25. `V25_PROJECT_STATUS.md` is the canonical current status, caveat, and release-readiness document.

The network-interface startup failure, rejected V24 routing experiments, one-slot leaderboard regression, and V25 two-slot ranking correction are documented in `V24_V25_REGRESSION_HISTORY.md`.

## Historical v20 weaknesses

### First invalid read after cold start

v20's high-water evidence is process-local. Before the process has parsed a mature index, an absent, empty, corrupt, inaccessible, or timestamp-rejected index is indistinguishable from the legitimate virgin May 2016 state. The original request-zero path can therefore remain reachable during a mature cold start.

### Permanent failure after a valid read

After high-water initialization, v20 retries an empty index read instead of destroying progression. This is data-safe but can wait indefinitely if the failure is permanent.

## v21 implementation

### Cold-start mature-pool detection

Use numbered request zero as the maturity witness:

```text
index read succeeds:
    parse normally

index is empty/rejected and REQUESTPOOL_0 does not exist:
    legitimate virgin pool
    allow original initialization

index is empty/rejected and REQUESTPOOL_0 exists:
    mature pool fault
    never create or overwrite request zero
```

Mature retries must include a small sleep rather than a hot loop. Permanent faults fail closed instead of erasing history.

### Index-only mtime tolerance

For `REQUESTPOOLINDEX` only, accept a payload that passes Base64, AES, padding, prefix, MD5, required-field, and index-range validation even when filesystem mtime differs from the encrypted timestamp. This removes the only lower-level trigger proven experimentally without weakening every CCrypt2 record.

### Atomic response-index writes

Keep the existing request-before-index commit order, but write the response index as:

```text
encrypt complete payload
write sibling temporary file
verify complete fwrite
fflush
fsync temporary file
close
atomic rename over authoritative index
fsync parent directory when supported
```

On failure, retain the previous authoritative index. An orphaned newest request is safer than a truncated index.

### No blind reconstruction

Do not automatically adopt every numerically contiguous set of records. The captured regressed snapshot has higher records but an overwritten request zero. A pool that cannot prove its original request zero must fail closed and be repaired offline with known-good evidence.

## v21 test matrix

### A. Legitimate virgin initialization

Using the minimal May 2016 bundle:

1. verify no index and no numbered requests;
2. launch and reach the main menu;
3. enter power-up selection and start a game;
4. complete a game and return to the main menu;
5. verify request zero and a valid index were created;
6. restart and verify progress persists.

This is also the first end-to-end gameplay validation that the minimal public bundle contains every runtime dependency.

### B. Healthy mature cold starts

Using the final level-9 checkpoint, perform at least ten cold launches. Every launch must preserve 980,800 coins, 99,870 gems, 3,810 EXP, Suri level 10, Polo selection, missions, keys, and a monotonic response pool.

### C. First-read fault injection

Before process launch, test:

- index mtime `+10`, `+11`, and `+60` seconds;
- missing index;
- zero-length index;
- truncated Base64;
- invalid AES/padding;
- wrong envelope MD5;
- index referencing a missing record.

No case may produce a zero pocket, sentinel-only inventory, empty quests, request-zero overwrite, or new `-1,0` index. Recovery or a non-destructive controlled wait are acceptable depending on fault permanence.

### D. Mid-session faults

After a valid mature index is loaded, temporarily remove it, skew mtime, deny access, and replace it with a zero-length file during a real `GameStart`. Restoration must allow a normal monotonic append without clamps.

### E. Interrupted writes

Terminate at these boundaries:

- numbered request complete, before index write;
- temporary index complete, before rename;
- immediately after rename;
- shutdown after a completed game.

The next launch must see either the previous or new valid index. Request zero must remain unchanged.

### F. Post-restart progression

After the fault matrix, complete a game, spend coins, advance a quest, restart, and confirm agreement among the pocket cache, `exp.dat`, inventory, quest profile, and response pool.

## Distribution gate

The APK-only workflow has passed on the Galaxy S4 with exact V25: uninstall, normal install, automatic 26-file seed extraction, offline launch, three-game progression, ranking reconstruction, cold restart, progressed-data capture, ten mature cold starts, and nine first-read fault cases.

The remaining public distribution gates are:

1. pass the deferred prolonged V25 progression soak;
2. run on a second supported 32-bit ARM device before claiming broad support;
3. choose the legal distribution model;
4. generate and retain the dedicated release key, then re-sign the immutable public build;
5. publish installation, checksum, troubleshooting, rollback, and provenance material.

The root-induced 17-second missing-index diagnostic is not part of the public distribution gate. Blocking all possible network traffic is also not required; the candidate must simply remain fully playable without revival servers, Wi-Fi, or mobile data.

## Optional diagnostic research

A diagnostic build can capture the exact first rejected read: access/stat/fopen results and errno, expected and actual read counts, cryptographic failure stage, embedded timestamp and mtime, caller/thread identity, and rejected bytes copied under a diagnostic filename. This is useful for identifying the original natural trigger but is not a prerequisite for hardening every empty-read path.

## Release sequence

- [x] Complete minimal-save end-to-end gameplay validation.
- [x] Build and validate the unclamped regression-hardening lineage.
- [x] Run first-read and mid-session fault injection.
- [x] Run interrupted-write tests and correct write ordering in v23.
- [x] Build the sanitized, connectivity-independent V25 candidate.
- [x] Validate exact-V25 APK-only self-seeding, fresh progression, cold restart, mature backup state, ten cold starts, and nine first-read faults.
- [ ] Run the deferred prolonged V25 progression soak and second-device test.
- [ ] Complete release signing, legal-distribution, installation, troubleshooting, and rollback work.
- [ ] Freeze the public release artifacts.
