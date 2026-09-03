# Birzzle Fever v14 power-up scene pending marker

V13 attached its one-shot marker to `RestoreFeverRanking`, but interactive
testing showed that the power-up back button does not traverse either of those
restoration calls.

V14 relocates the marker to the confirmed power-up lifecycle:

- the successful `ClickedFeverPlayButton` branch sets scene `0x0A`; that exact
  `SetCurrentScene` call now sets the one-shot pending byte;
- the sole `ProcessGameStart` dispatch clears the byte when the player commits
  to a game;
- therefore, backing out leaves the marker set for dispatch B to consume;
- clean startup never enters scene `0x0A`, so dispatch B remains guarded there.

V13's unrelated `RestoreFeverRanking` hooks were removed. All earlier working
patches and the conditional dispatch-B implementation remain intact.

## Initial validation

The APK was installed in place with the original 2016 save. A cold launch
produced exactly one `SCORE.RANKING` response, no fatal marker, and a live
application process.

Interactive power-up selection -> back repetition is required to validate the
marked abandonment path.

## Checksums

- Signed APK SHA-256:
  `eace300d83c69129725d6b47875ad3cb6b3eb3cb36ebe8944751abbb69b4ee05`
- Patched `libbirzzle.so` SHA-256:
  `437d09e9463c77d9b0a8d9e658ff8cd7d31de53c1a572786d5b9e6b7db1ccdb5`
- v13 source `libbirzzle.so` SHA-256:
  `5ddc810950d623bf4cff8bde483900c89d4b3b06dbd826f9bc5608540b45449f`
