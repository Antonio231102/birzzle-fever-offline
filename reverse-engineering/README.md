# Reviewed decompiled excerpts

This directory contains only the narrow decompiled code excerpts that were actually analyzed or changed during the offline-preservation work. It is not a reconstructed application source tree.

Complete apktool trees, extracted APKs, bulk assets, resources, original signatures, DEX files, and native libraries remain local and ignored. This follows the explicit repository scope: retain reviewable reverse-engineering evidence without committing full extracted packages.

## Smali excerpts

| File | Milestone | Purpose | Local provenance |
|---|---|---|---|
| `smali/BirzzleFever.GetUniqueDeviceID.smali` | V3 | Return the historical application identity without Xposed | V3 decoded `BirzzleFever.smali`, method at original decoded lines 1416–1422 |
| `smali/BirzzleFever.Network.smali` | V24 | Satisfy the obsolete Java startup availability gate | V24 apktool `BirzzleFever.smali`, methods at decoded lines 1856–1870 |
| `smali/BirzzleFever.PostInitialize-gcm-bypass.snippet.smali` | V24 | Supply an empty GCM ID and jump over registration | V24 apktool `BirzzleFever.smali`, accepted insertion at decoded lines 5713–5719 |
| `smali/MyApplication.onCreate-bootstrap.snippet.smali` | V12/V24 | Install the local save seed before native initialization | V24 apktool `MyApplication.smali`, accepted insertion at decoded line 36 |

`native-patches/v24-connectivity-independent/apktool/smali/com/halfbrick/birzzlefever/SaveBootstrap.smali` is also tracked because it is project-authored implementation code, not a bulk decompilation artifact.

## Native code

The ARM/Thumb reverse engineering is represented by:

- exact offsets, original/patched bytes, and disassembly in `native-patch-analysis.md`, `PROGRESS_REGRESSION_PATCHES.md`, `POST_GAME_COMMIT_ORDER.md`, and `V24_V25_REGRESSION_HISTORY.md`;
- authored `.S` sources under `native-patches/`;
- hash-checked Python patchers at the repository root.

Generated `.bin`, `.o`, `.elf`, `.so`, and APK files are not committed.

## Limitations

These excerpts show accepted replacement behavior. They are not independently assembleable classes, except the complete project-authored `SaveBootstrap.smali`. A future user-supplied-original patcher must locate and validate the surrounding original methods before applying any excerpt.
