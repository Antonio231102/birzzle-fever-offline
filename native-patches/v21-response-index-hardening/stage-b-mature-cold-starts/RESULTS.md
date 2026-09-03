# v21 test matrix B: healthy mature cold starts

## Input

- APK: `../BirzzleFever-1.1.2-v21-response-index-hardening.apk`
- APK SHA-256: `3fcabc4b998d6beedfb96e84c35918a011ea8d519dd190920a96706133a77c69`
- Data: final level-9 checkpoint from the eleven-game unclamped control.
- Installed package UID/GID: 10218.

The restored prelaunch pool was valid and mature:

```text
classification:     CONSISTENT
index:              -1,156
records:            0..156
record count:       157
semantic warnings:  none
```

## Procedure

`stress_v21_mature_cold_launch.py` performed ten independent cycles:

1. force-stop Birzzle Fever;
2. clear logcat;
3. launch through the launcher intent;
4. wait for `SCORE.RANKING` or a fatal/process-death condition;
5. verify the process remained alive at the main menu;
6. verify pocket, inventory, and ranking state;
7. preserve the launch log;
8. force-stop before the next cycle.

The final process was force-stopped. No gameplay input or save mutation was performed during these launches.

## Per-launch result

All ten launches reached the main menu and satisfied every required marker:

- 980,800 coins;
- 99,870 gems;
- 3,810 EXP;
- Suri owned at ability 10;
- Polo owned at ability 2;
- `SCORE.RANKING` containing score 1,017,964;
- process alive;
- no Java fatal exception;
- no native fatal signal or `SIGSEGV`;
- no app ANR;
- no forced activity finish.

Startup duration:

```text
minimum: 23.292 seconds
maximum: 26.794 seconds
mean:    25.257 seconds
```

The ten logs contain zero `SAVE REQUEST:` entries, confirming that passive cold launches did not mutate the request pool.

Machine-readable results: `results.json` and `analysis.json`. Logs: `launch-01.log` through `launch-10.log`.

## Persistent integrity

The pool was reconstructed before launch 1 and after launch 10:

```text
before: CONSISTENT, -1,156, records 0..156
 after: CONSISTENT, -1,156, records 0..156
```

The authoritative index was byte-identical:

```text
c75e925c83ce92d7157f77306b123eb0e7e5944f3926e0d623edb55ed8813d07
```

Request zero was byte-identical:

```text
5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2
```

No record was added, removed, or invalidated; no semantic warning appeared. Evidence: `prelaunch-pool.json`, `postlaunch-pool.json`, `postlaunch-index.bin`, `postlaunch-request0.bin`, and `integrity.json`.

## Result

Test-matrix stage B passed. v21 repeatedly recognizes and replays a healthy mature pool from a zeroed process-local high-water state without resetting progression, mutating request zero, or depending on the removed consumer-side clamps.
