# Birzzle Fever native ranking crash analysis

## Finding

The intermittent crash is consistent with two ranking requests consuming the same
offline `SCORE.RANKING` data. Successful runs logged one ranking response; failing
runs logged two. The two native request paths are distinct:

- `CHSPManager::GetRanking()` at `libbirzzle.so` file offset `0x163b78`
- `CHSPManager::GetGlobalRanking()` at file offset `0x163b48`

The latter resolves through the ARM PLT to
`Enfeel::Hangame::GetGlobalRanking()`. Its original Thumb code opens a loading
dialog before issuing that request. The offline backend maps both ranking paths
onto the same response type, which can cause duplicate or incompatible UI state.

The eventual native crash occurs in `EF::CListCtrl::DrawListItem()` at
`libef2d.so` offset `0xcb948`: `blx r3` is executed after loading a null function
pointer from vtable slot `+0x6c`. That is a downstream symptom. Globally bypassing
the virtual call would affect every list control, so it is not the preferred fix.

## Candidate patch

Disable only `CHSPManager::GetGlobalRanking()` at its entry, before it creates the
loading dialog or submits the redundant request:

| Library | File offset | Original Thumb | Patched Thumb | Meaning |
| --- | ---: | --- | --- | --- |
| `libbirzzle.so` | `0x163b48` | `00 b5` | `70 47` | `push {lr}` -> `bx lr` |

This retains personal ranking while removing the second offline ranking consumer.
The source library SHA-256 is
`607aa3efd6acb0c35f26171158853a9e56d8600c4dba6ed7a523d0756f30e79e`.

`patch_disable_global_ranking.py` checks both this hash and the original bytes
before writing a new library. It never edits the source in place.

## Validation required

Package the patched library in a separate test APK/module, then repeat cold starts
from the same restored backup. The expected log has one `SCORE.RANKING` response,
no call to the global-ranking path, no stuck loading dialog, and no null-PC crash.
Keep the original APK, native libraries, and all existing Xposed module versions.

## Runtime result (2026-08-23)

This candidate was installed and tested on the Galaxy S4 from the identical
working Titanium archive before each cold launch. The device-loaded library hash
matched the candidate, and offset `0x163b48` contained `70 47`.

- Trial 1: one `SCORE.RANKING` response; the process remained alive.
- Trial 2: two `SCORE.RANKING` responses (`timeout` 7 and 10), followed by
  `SIGSEGV` at address zero in `EF::CListCtrl::DrawListItem()+588`.

Therefore, disabling `CHSPManager::GetGlobalRanking()` does **not** remove every
source of the duplicate callback and is not a distributable fix. The next patch
must serialize/deduplicate `SCORE.RANKING` delivery itself (or make the list-item
consumer tolerate a missing callback target), instead of suppressing only this
request entry point.

## Ranking-delivery deduplication candidate

`OnResponseRequestRanking()` uses byte `CHSPManager+0x79f` as an existing
per-process “ranking handled” guard. A successful first callback sets it to one,
but `CHSPManager::GetRanking()` cleared it before every request. Removing that
reset makes subsequent callbacks return through the callback's existing early
exit without altering the transport or response data.

| Library | File offset | Original Thumb | Patched Thumb | Meaning |
| --- | ---: | --- | --- | --- |
| `libbirzzle.so` | `0x163baa` | `e5 54` | `c0 46` | `strb r5,[r4,r3]` -> NOP |

The patch was made from the original library, so it does not include the rejected
global-ranking change. Patched library SHA-256:
`f0f10455eb6f0c949168bbed5411bbfac7d4299830d15837bb5449694ebe8608`.

Five cold starts were performed from the identical working archive after fixing
restored ownership to the package's new UID 10217. Four runs received two raw
`SCORE.RANKING` transport responses and one received one response. All five had
zero fatal markers and retained a live process. The raw duplicate remains visible
in `HangameWrapper::OnReceivedResponse` logging, but the second callback is
discarded by the existing UI-delivery guard.
