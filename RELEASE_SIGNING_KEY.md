# Android release signing key procedure

## Status

No private release key is stored in this repository. The current v23 development APK is signed with `xposed-birzzle-id-spoof/build/debug.keystore`. Before the first public release, generate a dedicated Birzzle Fever key locally and keep its private keystore outside the repository.

The release key affects Android update identity and publisher provenance. It does not change offline behavior or confer ownership of the original game.

## Generate the key

Use the JDK `keytool` and allow it to prompt for the password so the secret is not recorded in shell history:

```powershell
keytool -genkeypair -v -keystore birzzle-release.p12 -storetype PKCS12 -alias birzzle-release -keyalg RSA -keysize 4096 -sigalg SHA256withRSA -validity 36500 -dname "CN=Birzzle Fever Preservation, OU=Releases, O=Birzzle Fever Preservation Project"
```

Parameters:

- keystore: PKCS#12;
- alias: `birzzle-release`;
- key: RSA-4096;
- signature: SHA-256 with RSA;
- validity: 36,500 days;
- Android target: retain v1/JAR signing for Android 4.4 compatibility.

`birzzle-release.p12` contains the private key. Never commit or publish it.

## Export the public certificate

```powershell
keytool -exportcert -rfc -keystore birzzle-release.p12 -storetype PKCS12 -alias birzzle-release -file birzzle-release-cert.pem
keytool -list -v -keystore birzzle-release.p12 -storetype PKCS12 -alias birzzle-release
```

`birzzle-release-cert.pem` and the certificate's SHA-256 fingerprint are public release metadata. Publish them with APK checksums.

## Sign a release APK

Preferred Android Build Tools flow:

```powershell
apksigner sign --ks birzzle-release.p12 --ks-type PKCS12 --ks-key-alias birzzle-release --v1-signing-enabled true --v2-signing-enabled true --min-sdk-version 19 --out BirzzleFever-release.apk BirzzleFever-release-unsigned.apk
apksigner verify --verbose --print-certs BirzzleFever-release.apk
```

If using `zipalign`, align before signing and never modify the APK afterward.

Android-4.4-compatible `jarsigner` fallback:

```powershell
jarsigner -keystore birzzle-release.p12 -storetype PKCS12 -sigalg SHA256withRSA -digestalg SHA-256 -signedjar BirzzleFever-release.apk BirzzleFever-release-unsigned.apk birzzle-release
jarsigner -verify -verbose -certs BirzzleFever-release.apk
```

Use one signer, not both, on a finished APK.

## Security and continuity

- Keep at least two encrypted offline backups of `birzzle-release.p12` in separate locations.
- Store the password separately in a password manager.
- Restrict private-key access to authorized release maintainers.
- Commit only the public certificate and its fingerprints.
- Record the alias, keystore type, algorithms, certificate fingerprint, and signing command in the release manifest.
- Every update must use the same key. Android 4.4 cannot rotate the signing identity while preserving in-place updates.
- Losing the key permanently ends the official in-place update path.
- A release-signed APK cannot update the current debug-signed installation; the first release-key cutover requires uninstall/reinstall with data backup or self-seeding.

## Reuse policy

A key can technically sign multiple APK packages. Prefer one key per independent project so compromise, ownership transfer, certificate linkage, and legacy signature-level trust remain isolated. Reuse only when multiple apps intentionally share one publisher and security boundary.

## Protection provided

An APK signed by another key cannot install over the official package on an ordinary Android device. A third party may still publish a differently signed fork, require users to uninstall first, use another package name, or bypass checks on a modified/rooted system. Signing protects the official update path; it does not prevent all redistribution or modification.
