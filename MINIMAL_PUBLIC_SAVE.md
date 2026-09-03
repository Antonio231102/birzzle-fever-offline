# Minimal public save dependency graph

## Validated bundle

`minimal-public-save/birzzle-2016-minimal-data.tar.gz` is the current minimal data-only bundle.

- Source: untouched May 1, 2016 Titanium data archive.
- Included: 27 files.
- Excluded: 18 device, analytics, cache, database, and static-resource files.
- Exact members, sizes, mtimes, and roles: `minimal-public-save/manifest.json`.
- Reproducible builder: `build_minimal_public_save.py`.
- SHA-256: `109925b9c3fc41498e6ed337270be2e1f65ed78270402c0217aeec50313efbaa` (identical across consecutive rebuilds).

## Dependency graph

```text
portable patched APK
├── .birzzle_seed_v1
│   └── prevents APK first-run seeding from replacing the restored historical files
├── historical UID-derived API map
│   ├── APIFILE
│   └── 13 cached command responses
├── literal-name game state
│   ├── pocket.dat
│   ├── stage.dat
│   ├── social.dat
│   ├── messagecount.dat
│   ├── friendlist.dat
│   ├── localtime.dat
│   ├── variable.dat
│   └── submarinevariable.dat
└── local proprietary profiles
    ├── new2profile.dat
    ├── bMarket.dat
    ├── exp.dat
    └── tuto.dat_<historical UID>
```

The 22 CCrypt2 records are exactly:

- 8 literal-name state records;
- 13 historical-UID-derived cached API responses;
- 1 historical-UID-derived `APIFILE` command list.

The original save correctly has no `REQUESTPOOLINDEX` and no numbered `REQUESTPOOL_n` history. That is the supported virgin-pool state, not missing data. The patched APK creates request zero on the first offline mutation.

## Why the marker is required

The first device trial omitted `.birzzle_seed_v1`. The portable APK treated the installation as unseeded and copied its embedded defaults over the restored files. That changed timestamps/state and produced zero-state behavior followed by a crash.

The marked bundle was then restored with package ownership and historical mtimes preserved. A cold launch on the rooted Galaxy S4 reached:

- `SERVER.INIT`;
- `POCKET.LOGIN` from file;
- the cached `SCORE.RANKING` response;
- a live main-menu process with no fatal exception or native signal.

Evidence: `minimal-public-save/minimal-public-save.log`. The process remained alive as PID 14709 after the 25-second observation window.

This proves the marker is a dependency of the patched APK's deployment contract. It is not original game save data.

## Ownership and timestamps

The CCrypt2 reader authenticates content and checks embedded timestamps against filesystem mtime. Restore tooling must preserve each member's mtime. On a rooted direct-data restore, set the package UID/GID recursively and use mode `0600` for files (`0700` for the files directory).

The numeric UID is installation-specific. The historical game identity used to derive hashed filenames is a separate value hardcoded by the patched APK; it is not the Linux package UID.

## Excluded branches

The minimal bundle excludes entire independent branches:

```text
static resources: clearbox, highscore, order, profile, test
analytics: MAT, Kontagent, Facebook App Events, OtherLevels
push identity: GCM preferences and historical device tokens
browser/cache: WebView databases and journals
```

The OLE and analytics classifications are documented in `OLE_ANALYTICS_ARTIFACTS.md`. None changed between the original and progressed snapshots in a way that carries gameplay state.

## Distribution implications

A standalone installer still must perform a privileged data restore on Android 4.4-era devices: install the APK, copy these 27 files into the app-private files directory, preserve mtimes, set the installed package's UID/GID, then launch. Titanium Backup can perform the private-data portion, but a custom rooted installer can reduce this to one operation.

Do not add a fabricated response-pool index to the public bundle. Starting from the legitimate absent-index state avoids publishing a partially replayed or device-session-specific request history.
