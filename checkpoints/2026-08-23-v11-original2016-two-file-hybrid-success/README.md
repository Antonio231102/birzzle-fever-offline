# Birzzle Fever v1.1.2 — validated hybrid checkpoint

Created 2026-08-23 from the successful Trial 12 test on the rooted Galaxy S4 (Android 4.4.2).

## Validated configuration

- APK: v11 ranking-dispatch/re-arm build (includes the previous device-ID, ranking, menu-return, and unlimited-lives patches).
- Base data: coherent original May 1, 2016 backup.
- Compatibility changes:
  - `files/09d531fd0dc2a818e49efec1d5548a78` replaced with the level-8 checkpoint version.
  - `files/f0328e1664de484d932bca2ec0e59295` added from the level-8 checkpoint.
- Stress test: approximately 15 games, progression from level 1 to level 6, repeated main-menu/power-up transitions, and mid-game exits.
- Log result: 51 `SCORE.RANKING` events, 0 fatal signals/exceptions, and 0 ANRs.
- Progress matched the original 2016 state before new test progress was earned.

## Files

- `installed-v11.apk`: APK pulled directly from the tested phone.
- `build-v11-ranking-dispatch-rearm.apk`: preserved local v11 build; byte-identical to `installed-v11.apk`.
- `pristine-2016-plus-two-compat-data.tar.gz`: reproducible pre-test data bundle at the original 2016 progression state.
- `posttest-level6-app-data.tar.gz`: device data pulled after the successful level-6 stress test.
- `trial-12-15-games.log`: complete successful test capture.

## SHA-256

```text
75821A19FB98286B87C65FB83EAB739552B04D0F6B35317A6B35D3321EC60089  build-v11-ranking-dispatch-rearm.apk
75821A19FB98286B87C65FB83EAB739552B04D0F6B35317A6B35D3321EC60089  installed-v11.apk
A8BC9FF7119090C227CC8859B93A68258FD8E9C1E154A3C8638994AC1D3E9AB1  posttest-level6-app-data.tar.gz
0F5C23E98439B1D5B898D41A52AA341854A150C6A505FA3D13A7519B9F680FA9  pristine-2016-plus-two-compat-data.tar.gz
EC0E4859670F2DC9E5FE54F63B8476DB84BBD649C4A9C7F2299AF1437A4C4228  trial-12-15-games.log
```
