# Birzzle Fever v10 rejected-ranking cleanup

This build derives from v9 and preserves all prior patches. Testing with both
the level-8 and original 2016 saves showed that the v8/v9 restoration re-arms
did not solve the power-up-selection return: v9 failed 12/12 attempts, while
mid-game and completed-game returns remained reliable.

The power-up transition can activate the loading overlay before issuing a
ranking request which v7's still-closed duplicate guard rejects. The rejection
previously returned immediately, leaving that pre-existing overlay orphaned.

V10 changes only the dedicated-gate rejection path. When a redundant ranking
request is rejected, it obtains the existing `CLoadingDialog` and calls its
normal `HideAnimation()` method before returning. That method is idempotent: it
checks the dialog's active byte and immediately returns when nothing is shown.
Accepted ranking requests, response delivery, and v7's startup deduplication
remain unchanged.

## Initial validation

The signed APK was installed in place on the Galaxy S4 without clearing data.
A cold start completed the offline response sequence through `SCORE.RANKING`,
showed no fatal markers, and left the application process alive.

Interactive repetition of power-up selection -> back is required to validate
the orphan-overlay cleanup.

## Checksums

- Signed APK SHA-256:
  `a5089a4b35bdf6acf9b8bf119c34723f130010da9882a5f79d40d26becd6ce56`
- Patched `libbirzzle.so` SHA-256:
  `28435b4e4577b244e86b742df606fa77f4a0fc9bd4d9b3dcf8dbcb7963777442`
- v9 source `libbirzzle.so` SHA-256:
  `3720275be9e4215856d8b5713faddfc6edf05816606eae58d6da8fb93d673b9b`
