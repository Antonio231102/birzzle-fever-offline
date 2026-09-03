# Birzzle Fever v4 ranking in-flight patch

This build preserves the v3 hardcoded historical device identity and the v2
ranking-callback deduplication, then adds request serialization intended to let
later main-menu ranking refreshes work without reopening the duplicate-callback
crash.

## State protocol

- `CHSPManager+0x79f` retains its original meaning: ranking response handled.
- `CHSPManager+0x7a0` uses value `2` for a personal-ranking request in flight.
  The game's existing global-ranking path uses value `1`, so only `2` is
  rejected by the new guard.
- Starting an accepted personal-ranking request stores `2` at `+0x7a0` and
  clears `+0x79f` before showing the loading dialog.
- Successful callback completion sets `+0x79f` and clears `+0x7a0`.
- A duplicate request while `+0x7a0 == 2` returns before showing a loading
  dialog. Duplicate callbacks remain rejected by the original `+0x79f` guard.

`GetGlobalRanking()` is disabled and its retired body holds the two small Thumb
stubs. `GetRanking()` calls the request stub at entry. The successful ranking
callback calls the completion stub in place of its original handled-flag store.

## Artifacts

- `BirzzleFever-1.1.2-identity-ranking-inflight.apk` — signed test APK
- `BirzzleFever-1.1.2-identity-ranking-inflight-unsigned.apk` — unsigned APK
- `libbirzzle.so` — patched native library
- `failed-inline-build/` — preserved first inline attempt
- `failed-request-only-build/` — preserved request-only attempt
- `failed-three-state-build/` — preserved attempt that repurposed `+0x79f`
- `failed-bad-literal-build/` — preserved incorrect PC-relative literal build

## Checksums

- Final signed APK SHA-256:
  `add78ccba4ad7e499a301623d2996920dfb1fad30d1baa7fe3ed188eb1731d03`
- Final `libbirzzle.so` SHA-256:
  `ef72361e2ed8c18286bda4d0f67fc0c3f349d63a9ba3d6dbde6696b8aa817c92`

## Device validation (2026-08-23)

The final library was deployed on the rooted Galaxy S4 over the existing v3
installation, preserving restored data and UID 10220. Two 22-second cold starts
each logged one `POCKET.LOGIN` and one raw `SCORE.RANKING` response, no Xposed
module output, no fatal marker, and a live Birzzle Fever process. The gameplay
return-to-menu path still requires an interactive test.
