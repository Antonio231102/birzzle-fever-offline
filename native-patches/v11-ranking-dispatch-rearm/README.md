# Birzzle Fever v11 ranking-dispatch re-arm

This build derives from v10 and preserves the hardcoded identity, unlimited
lives, startup response guard, callback deduplication, loading-dialog cleanup,
and the working completed-game and mid-game return behavior.

V10 proved that the power-up-return spinner was only a symptom: hiding it left
the scene locked because the guarded request never ran its normal ranking
completion state machine.

V11 removes v8/v9's speculative re-arms around `RestoreFeverRanking`. Those
occurred before the request which owned the reconstructed main-menu UI and
could be consumed by unrelated asynchronous work. Instead, both dedicated
central-message `GetRanking` dispatches now re-arm directly at their call
instructions. There is no intervening code in which another request can steal
the generation. Asynchronous SNS callback requests remain guarded.

The v7 completed-game hook and v8 mid-game-exit hook are unchanged.

## Initial validation

The APK was signed for Android 4.4 and installed in place without clearing
application data. Cold startup completed through `SCORE.RANKING`, produced no
fatal marker, and left the process alive.

Interactive power-up selection -> back repetition is required to identify
whether one of these dispatches is the missing UI-owned generation.

## Checksums

- Signed APK SHA-256:
  `75821a19fb98286b87c65fb83eab739552b04d0f6b35317a6b35d3321ec60089`
- Patched `libbirzzle.so` SHA-256:
  `9f4d9144e9c1afe3495c7a0c9d1cde9ebda359e5b5d182e5ac9924033224c34d`
- v10 source `libbirzzle.so` SHA-256:
  `28435b4e4577b244e86b742df606fa77f4a0fc9bd4d9b3dcf8dbcb7963777442`
