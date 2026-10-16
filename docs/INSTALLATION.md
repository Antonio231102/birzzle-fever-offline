# Installation model

## Release artifact status

The repository does not ship an APK or save bundle. A release-signed V42 APK has been prepared locally, and the operator reports its eight V42 functional checks passed on the Galaxy S4/Android 4.4.2 and Galaxy S20 Plus/Android 13. Those empirical runs collected no logs or save backups; see [TESTING.md](TESTING.md). Use published checksums and signing-certificate metadata to identify an authorized artifact rather than relying on a third-party filename.

## Intended release experience

The V42 fresh APK-only initialization and fresh-player progression checks passed on both reported devices. The intended single-APK workflow is:

1. uninstall an incompatible/debug-signed prior build after backing up any wanted app data;
2. install the release-signed APK;
3. launch normally;
4. allow the package bootstrap to create the minimal private seed on first start;
5. play without Xposed, Titanium Backup, root, an active Wi-Fi interface, or package-UID repair.

Existing compatible data must not be overwritten by the bootstrap. Android owns newly extracted private files with the package's assigned UID.

## Source-only distribution alternative

If legal review does not permit redistribution of a modified APK, the public release should provide a patcher that:

- accepts a user-supplied Birzzle Fever 1.1.2 APK;
- validates package, version, hashes, and exact patch bytes;
- applies only the documented transformations;
- obtains or constructs the minimal seed through a separately lawful workflow;
- emits an unsigned APK or signs with a user-selected key;
- verifies the output and prints all checksums.

This is the repository's preferred conservative distribution model until the legal gate is resolved.

## Upgrade and rollback constraints

Android requires the same signing certificate for in-place updates. The earlier development V42 and the release-signed V42 use different certificates, so the release APK cannot update the development installation in place. The first release-key cutover therefore requires uninstall/reinstall unless the user independently migrates compatible data.

Before uninstalling any build with meaningful progress:

- force-stop the game;
- capture app data with an authorized backup method;
- retain file mtimes;
- hash the backup;
- verify that it can be listed and read before deleting the installation.

A failed or unknown build should be removed rather than installed over a working checkpoint. Keep the last known-good APK checksum and data checkpoint outside the repository.

## Compatibility claims

Reported V42 functional-pass environments:

| Device | Android | Evidence |
|---|---|---|
| Samsung Galaxy S4 | 4.4.2 | Operator-reported manual pass |
| Samsung Galaxy S20 Plus | 13 | Operator-reported manual pass |

All eight named functional checks passed on both devices without observed progress loss, crashes, freezes, or softlocks. No logs or save-file backups were collected for these empirical runs. The older instrumented S4 results remain separate evidence.

These observations do not establish support for every Android version or device, particularly devices without support for this 32-bit application.

## Historical Xposed route

The `xposed-birzzle-id-spoof` source is retained for research. It established that the save depended on the game's historical identifier rather than Android's package UID. V25 hardcodes that identity and does not need the module. Do not combine V25 with the old Xposed module unless diagnosing a controlled comparison.

## Troubleshooting evidence to collect

For a legitimate test build, record:

- APK SHA-256 and signing-certificate fingerprint;
- device model, Android version, CPU ABI, and package version;
- whether app data existed before first launch;
- whether any Xposed hooks were active;
- whether Wi-Fi/mobile data had an associated interface;
- the exact screen and transition where failure occurred;
- a narrowly scoped logcat capture with account tokens and unrelated application data removed.

Do not post complete device logs, raw save archives, Android IDs, account tokens, or screenshots containing personal information to public issues.
