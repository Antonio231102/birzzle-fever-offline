# Birzzle Fever V37 global power-up scene marker

Status: built and statically verified; not deployed or behaviorally qualified.

## V36 failure evidence

V36 retained V14's power-up marker at one callsite in
`CStoryManager::ClickedFeverPlayButton()`. It passed the fresh-save free-pet
sequence, an ordinary Polo purchase, and 10/10 settled cold launches. The first
power-up-selection return in the final S4 stress pass nevertheless reproduced
the non-crashing softlock:

- `POCKET.GET` timeout 10 completed;
- `GIFT.GET.COUNT` timeout 11 completed;
- no subsequent `SCORE.RANKING` response was delivered;
- the process remained alive without a fatal exception, signal, tombstone, or
  ANR;
- the loading animation disappeared, but the personal score and ranking rows
  were absent and the main-menu UI was unresponsive;
- live BSS bytes at `0x2c7730..0x2c7733` were `00 00 01 00`: the ranking gate
  was closed and `powerup_return_pending` was clear.

Local evidence is preserved under
`device-snapshots/2026-09-06-s4-v36-final-stress/`. Device captures remain
excluded from version control.

## Root cause

The V14 lineage marked scene `0x0a` only at the call at `0x1437fa`. ARM
inspection found six additional constant-`0x0a` calls to
`CStoryManager::SetCurrentScene()` at `0x1450de`, `0x14511a`, `0x14523c`,
`0x1458ce`, `0x146bf6`, and `0x146dea`. Tutorial and progression state can
therefore reach the same visible power-up selection screen without traversing
the one marked callsite.

When the marker is absent, dispatch B calls `GetRanking()` with V7's gate still
closed. V10's preserved rejection cleanup hides the loading animation, but no
ranking response reaches the new main-menu consumer. That produces the exact
empty-ranking, nonresponsive state captured on the S4.

## V37 correction

V37 derives only from the exact V36 APK and native library. It moves the marker
to the semantic boundary shared by every route:

- `CStoryManager::SetCurrentScene()` at `0x141870` now branches to a 24-byte
  wrapper at `0x2acf60`;
- the wrapper sets the deployed `powerup_return_pending` byte at `0x2c7733`
  whenever `r1 == 0x0a`;
- for every scene value, it preserves the complete original operation,
  `str r1, [r0, #0x60]`, and returns directly;
- the old callsite at `0x1437fa` is restored to a normal direct call to
  `SetCurrentScene()`;
- the obsolete narrow marker stub at `0x2acef0` is cleared;
- V14's `ProcessGameStart` clear remains unchanged, so committing to a game
  still cancels the pending back-navigation generation;
- V36's BuyPet completion marker, startup ranking protection, response
  deduplication, rejected-request loading cleanup, historical identity, and
  unlimited-play patch remain byte-for-byte unchanged.

## Static verification

The build script rejects any unexpected V36 source hash or original patch byte.
The resulting native delta is confined to four ranges:

- `0x141870..0x141873`: central setter branch;
- `0x1437fa..0x1437fd`: restored direct call;
- `0x2acef0..0x2aceff`: removed narrow stub;
- `0x2acf60..0x2acf77`: global scene marker wrapper.

Disassembly confirmed the new branch target and original store semantics. The
wrapper's PC-relative literal resolves exactly to `0x2c7733`. The signed APK
was reopened to verify `libbirzzle.so`, `libef2d.so`, `classes.dex`, and the
embedded seed, then passed `jarsigner -verify`.

## Checksums

- V36 source APK:
  `a0e8187e3f67f7e010aa1c26631feac6363e2baaa591035826c3165342a952de`
- V36 source `libbirzzle.so`:
  `67a11e74e0cf9ae0540a46e62619b4b81e468bb0dc400fbd5976be3fb547e613`
- V37 signed APK:
  `26b1e87a4a8b9caf68f1c6e7d57fdf57d58b9936391206a562c3917d85e866bb`
- V37 unsigned APK:
  `90b1152d4306c96e534b42d900ccb917a59db14039e5c2908b1910dcd9cf3098`
- V37 `libbirzzle.so`:
  `5cc699aedb1ad48ab0f46edcdd0b0b4cc733c1de01f906bac382d175a601d94f`

## Required device qualification

1. Install V37 without changing the preserved V36 artifacts.
2. Restore the high-resource checkpoint.
3. Verify one cold start and then ten power-up-selection returns.
4. Require one personal-score ranking response and responsive UI after every
   return.
5. Repeat the free-pet tutorial and ordinary-pet purchase paths.
6. Resume the deferred three mid-game exits and three completed-game returns.
