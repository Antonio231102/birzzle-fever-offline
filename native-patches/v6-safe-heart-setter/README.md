# Birzzle Fever v6 safe heart-setter patch

This test build starts from the preserved v4 dedicated-BSS checkpoint, so it
includes the hardcoded historical identity and all previous leaderboard and
return-to-menu patches.

Unlike v5, it does not replace `CHSPManager::GetHeartCount(bool)`. That getter
returns a `CSafeNumber`, which is why treating it as a plain integer did not
affect the real life balance.

At native offset `0x171bfc`, v6 replaces
`CCashManager::SetCurrentHeartCount(CSafeNumber)` with a tail call to the
game's original `CSafeNumber::SetNumber(int)` encoder using the value `5`.
Consequently, attempts to consume or otherwise update normal lives store a
valid encoded five. Coin, gem, and other safe-number setters are unchanged.

Runtime testing should verify starting games repeatedly, returning to the
menu, the visible life counter, and restored-save startup behavior.

## Checksums

- Signed APK SHA-256:
  `d145e6eba569c4ac4d8f78d56713c97e193f65cc4c5315960f7182b87bf18e46`
- Patched `libbirzzle.so` SHA-256:
  `3042910e4f13e28289e28cec6879aea2ff8fe6982708916470832e44e9010249`
