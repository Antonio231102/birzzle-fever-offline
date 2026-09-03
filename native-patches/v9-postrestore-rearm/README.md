# Birzzle Fever v9 post-restoration ranking re-arm

This build derives from v8 and preserves every earlier patch, including v7's
startup ranking protection, the completed-game return fix, v8's working
mid-game-quit return fix, loading-dialog protection, hardcoded identity, and
unlimited-lives behavior.

V8 opened the ranking gate immediately before `RestoreFeverRanking`. During
the relatively long UI reconstruction, an automatic request could consume the
gate before the newly restored main-menu ranking UI became its consumer. This
made backing out of power-up selection succeed only intermittently.

V9 changes only the two central `RestoreFeverRanking` hooks. The new stub:

1. calls the original `RestoreFeverRanking` with its arguments intact;
2. waits for the function to return after rebuilding the main-menu UI;
3. opens exactly one subsequent ranking request; and
4. returns to the original button-dispatch caller.

The v8 mid-game hook and v7 completed-game hook are unchanged.

## Initial validation

The KitKat-compatible APK was signed with the same debug certificate and
installed in place on the Galaxy S4 without clearing data. A 25-second cold
launch received one logged `SCORE.RANKING` response, produced no fatal marker,
and left the process alive.

Interactive repetition of power-up selection -> back is required to validate
the timing change.

## Checksums

- Signed APK SHA-256:
  `e2e7fbef946d2695cfb7b1fb270cb636b1cf18882057830637251200bd5f412d`
- Patched `libbirzzle.so` SHA-256:
  `3720275be9e4215856d8b5713faddfc6edf05816606eae58d6da8fb93d673b9b`
- v8 source `libbirzzle.so` SHA-256:
  `b3e524a38e06c0c31fb79171ad9635f2e5ab6694f80648fe48de1db36073ea97`
