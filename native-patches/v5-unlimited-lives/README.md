# Birzzle Fever v5 unlimited-lives patch

This build is based on the successful v4 dedicated-BSS ranking build. It keeps
the hardcoded historical identity and all ranking fixes, then patches
`CHSPManager::GetHeartCount(bool)` at native offset `0x1639bc` to always return
`5`, the normal maximum replenishable number of lives.

The patch affects the read-side getter only. It does not rewrite the restored
pocket data or alter coin/gem values. Runtime testing is required to confirm
that both the main-menu display and game-start eligibility use this getter.

## Checksums

- Signed APK SHA-256:
  `703ef6b9fc11258026eabdcbf616bdef6751d7b683c373462b6fcf2c9f060c55`
- Patched `libbirzzle.so` SHA-256:
  `f6445f55c414c58dbb234b8490414a8c40d074911166ca98c31e48db04322485`
