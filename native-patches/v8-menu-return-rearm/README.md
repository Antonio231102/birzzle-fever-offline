# Birzzle Fever v8 menu-return re-arm patch

This build derives directly from v7 and preserves its hardcoded historical
identity, unlimited-lives behavior, startup ranking guard, duplicate-response
handling, and loading-dialog protection.

V7 deliberately kept the ranking request gate closed after the startup
response was consumed. It re-armed after a completed game, but two other paths
could return to the main menu without opening a new ranking generation:

- backing out of the power-up selection screen; and
- quitting a game to the main menu before game-over processing.

V8 re-arms the gate at the lifecycle transitions which create a new main-menu
ranking consumer. Both central `RestoreFeverRanking` call sites now pass through
an unlock-and-tail-call stub, and the separate `CallExitMainMenu` dispatcher
used by mid-game quit does the same. Response delivery itself still leaves the
gate closed, retaining v7's startup race protection. V7's completed-game
trampoline remains unchanged.

## Initial device validation

The KitKat-compatible signed APK was installed in place on the Galaxy S4; the
existing application data was retained. A 25-second cold-launch smoke test
reached the main menu, received `SCORE.RANKING`, produced no fatal markers, and
left the process alive. Interactive testing of all three return paths remains
required.

The captured smoke-test log is in
`../../device-snapshots/2026-08-23-v8-menu-return-rearm/cold-launch.log`.

## Checksums

- Signed APK SHA-256:
  `cfa3ac8b0f691aad13a897736ed9f9cec6eff5628b0aad53ae4f65c46a818b43`
- Patched `libbirzzle.so` SHA-256:
  `b3e524a38e06c0c31fb79171ad9635f2e5ab6694f80648fe48de1db36073ea97`
- v7 source `libbirzzle.so` SHA-256:
  `ef3371b363ada683562aa83b1897af4918f1a5a5bc691fe3498774c568aba461`
