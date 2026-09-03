# Birzzle Fever v12 power-up dispatch re-arm

This build replaces v11's two message-dispatch re-arms with the single dispatch
actually safe for a new ranking generation.

## Evidence

With the original 2016 save, v11 produced two `SCORE.RANKING` responses 210 ms
apart and then crashed with SIGSEGV at address zero. Isolated builds established:

- dispatch A (`0x147848`) only: one ranking response, no fatal signal, process alive;
- dispatch B (`0x148e38`) only: two ranking responses, one SIGSEGV, process dead.

Dispatch B is therefore part of clean-save startup and must remain protected by
v7's closed gate. Dispatch A is retained as the explicit re-arm used by the
power-up/main-menu transition.

V12 also removes the ineffective v8/v9 re-arms around `RestoreFeverRanking`.
The working completed-game and mid-game hooks, rejected-request overlay cleanup,
hardcoded identity, unlimited lives, and all earlier callback protections remain.

## Device validation

The signed APK was installed in place on the Galaxy S4 with the original 2016
save restored. A cold launch produced exactly one `SCORE.RANKING` response, no
fatal marker, and left the process alive.

Interactive power-up selection -> back testing remains required to confirm that
dispatch A alone retains v11's successful fix.

## Checksums

- Signed APK SHA-256:
  `3da218c5b4eb82445d56dc33108c029671441055b79b2fbd12ebcde3d7819663`
- Patched `libbirzzle.so` SHA-256:
  `0d673f4827ae588119b9fd0bb518db033e654c9f6d1af6a1f1da6bf2eb8c2ae6`
- v10 source `libbirzzle.so` SHA-256:
  `28435b4e4577b244e86b742df606fa77f4a0fc9bd4d9b3dcf8dbcb7963777442`
