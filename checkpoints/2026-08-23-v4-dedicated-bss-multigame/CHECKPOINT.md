# Birzzle Fever v4 dedicated-BSS checkpoint

Created on 2026-08-23 after successful testing on the Galaxy S4.

## Result

- Several games were played in one process.
- Returning to the main menu repeatedly produced no crash or softlock.
- Cold-start testing received two raw `SCORE.RANKING` responses without a
  crash, confirming callback deduplication remained active.
- The Xposed module was not required by this APK because it retains the v3
  hardcoded historical identity patch.

## Known unresolved issue

The life-recovery timer remained at `00:00`, preventing automatic recovery of
lives after depletion. It is not yet known whether this behavior also occurs
with the original APK plus Xposed v1.

## Primary checksums

- `BirzzleFever-1.1.2-v4-dedicated-bss.apk`
  SHA-256: `8dfc4ef552bb9a3313b39add3a3c362a86b9d1a2197ff016365d63d7a05f5999`
- `libbirzzle.so`
  SHA-256: `7d079a460b738e4de3d73829a811a0234474d2f55b8072981ba6c7f97fefabf0`
- `patch_ranking_inflight_v4.py`
  SHA-256: `936da64b08952ba4bdf4becb0235145414ed7606600c325b2d062808146f1e0d`

The patch uses a dedicated four-byte extension at the end of the writable BSS
for request-in-flight state. Its Thumb stubs occupy unused executable padding;
no original game function is repurposed.
