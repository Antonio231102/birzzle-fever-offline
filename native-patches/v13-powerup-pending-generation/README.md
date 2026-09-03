# Birzzle Fever v13 one-shot power-up ranking generation

V12 established that dispatch B (`0x148e38`) is necessary for the main-menu
ranking completion state machine after leaving power-up selection, but globally
re-arming it also causes the clean-save startup duplicate crash.

V13 separates those two uses with a dedicated one-shot BSS marker at `0x2c7731`:

1. the menu-restoration transition sets `powerup_return_pending` without opening
   the ranking request gate;
2. unrelated asynchronous requests cannot consume that marker;
3. dispatch B checks the marker;
4. when set, it clears the marker and uses v7's re-arm-and-request helper;
5. when clear, it calls `GetRanking` with the existing gate untouched, preserving
   clean-startup duplicate protection.

Dispatch A is restored to its guarded v10 behavior. The completed-game and
mid-game hooks, rejected-request loading cleanup, identity patch, unlimited
lives, and earlier response protections remain unchanged.

## Initial validation

The APK was installed in place on the Galaxy S4 with the original 2016 save.
A cold launch produced exactly one `SCORE.RANKING` response, no fatal marker,
and a live application process.

Interactive power-up selection -> back repetition is required to validate the
one-shot marked path.

## Checksums

- Signed APK SHA-256:
  `081a2368faba04d3509ccf3e8f986c846de54b72dd2f785013203580dcda53c5`
- Patched `libbirzzle.so` SHA-256:
  `5ddc810950d623bf4cff8bde483900c89d4b3b06dbd826f9bc5608540b45449f`
- v12 source `libbirzzle.so` SHA-256:
  `0d673f4827ae588119b9fd0bb518db033e654c9f6d1af6a1f1da6bf2eb8c2ae6`
