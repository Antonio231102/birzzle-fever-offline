# Birzzle Fever v7 ranking-generation patch

This build derives from v6 and preserves its working unlimited-lives patch,
hardcoded historical identity, callback deduplication, and dedicated-BSS
request guard.

V4/v6 reopened the request gate as soon as the first ranking callback arrived.
That left a narrow startup race in which a new request could clear the handled
flag before a delayed duplicate callback reached the UI.

V7 keeps the gate closed after callback completion. It re-arms one new ranking
generation only from lifecycle events that establish a fresh UI consumer:

- `CStoryManager::ProcessPostGameOver()` for returning from a completed game;
- the explicit main-menu ranking button; and
- completion of an explicit friends-ranking profile-manager reset.

The accepted request still clears the handled flag, and successful callback
completion still sets it. Rejected automatic duplicate requests return before
`ShowLoadingDialog`, preserving the v4 loading-animation softlock fix.

Interactive testing must cover cold starts with the original hashed state file,
multiple games and returns to the main menu, and explicit leaderboard actions.

## Initial device validation

The signed APK was installed in place on the Galaxy S4, preserving the current
save. Two 28-second cold starts each reached one `SCORE.RANKING` response,
reported zero fatal markers, and left the app process alive. Interactive
post-game and explicit-ranking refresh testing remains required.

Logs are in `../../device-snapshots/2026-08-23-v7-ranking-generation/`.

## Checksums

- Signed APK SHA-256:
  `6d388c578094d85959661d192c3968195e1ac013f82d2fd9a6ceb99bfb15e6d5`
- Patched `libbirzzle.so` SHA-256:
  `ef3371b363ada683562aa83b1897af4918f1a5a5bc691fe3498774c568aba461`
