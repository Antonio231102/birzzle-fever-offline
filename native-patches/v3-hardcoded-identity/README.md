# Birzzle Fever v3: hardcoded identity + ranking deduplication

This variant is based on the validated v2 ranking-deduplication APK. It changes
only `classes.dex` (plus the APK signature) and preserves all 1,138 non-Dex APK
entries byte-for-byte.

`BirzzleFever.GetUniqueDeviceID()` now returns:

```text
3c8bb7308c3fcb60c439224bd595c794d8f31501
```

The embedded `libbirzzle.so` retains the ranking-delivery patch at file offset
`0x163baa` (`c0 46`) and has SHA-256:

```text
f0f10455eb6f0c949168bbed5411bbfac7d4299830d15837bb5449694ebe8608
```

The signed APK SHA-256 is:

```text
9a325e12ceb25fde1988fdace6e8aa325378e3bc660b294fbabe02fa618c92d0
```

The previous v2 APK is preserved at
`../v2-deduplicate-ranking/BirzzleFever-1.1.2-ranking-dedupe.apk`.

## Device validation

Validated on the rooted Galaxy S4 with the identity module completely absent.
The APK was installed fresh, app data was wiped, and the untouched May 2016
archive was restored under the newly assigned package UID 10220.

Five cold launches all loaded `POCKET.LOGIN`, used the historical identity, had
no Xposed hook activity, and produced zero fatal markers. Raw `SCORE.RANKING`
response counts were 1, 2, 1, 1, and 3. The fifth launch remained alive through
an extended observation window after receiving three ranking responses.

Logs are stored in `../../device-snapshots/2026-08-23-v3-no-xposed-tests`.
