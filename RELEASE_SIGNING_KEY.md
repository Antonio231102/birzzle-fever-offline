# Android release signing key procedure

## Status

No private release key is stored in this repository. On 2026-09-20, V42 was signed with the operator-selected external release key. The tested development V42 and its original signing identity remain unchanged. Key-generation instructions below are reference material, not a requirement to replace the selected key. Public documentation omits private keystore locations, internal aliases, and unrelated project associations.

The release key affects Android update identity and publisher provenance. It does not change offline behavior or confer ownership of the original game.

### V42 signed artifact

- APK: `native-patches/v42-binary-safe-tokens/release-signed/BirzzleFever-1.1.2-v42-release-signed.apk`
- Package retained: `com.halfbrick.birzzlefever`; no package migration was performed.
- Signed APK SHA-256: `766ecc422f8140fc275fc1a04f7aa0f49653e929e4906a133d132750fce8ebb4`
- Signer certificate SHA-256: `7e9ad31c19d7ee447c8e1a58bc7ca4be51acf4489f55cf2258124c45d7213417`
- Signing: RSA-2048, `SHA256withRSA`, SHA-256 entry digests, Android-4.4-compatible v1/JAR signature.
- Source development APK SHA-256: `72e02bf723969d857616b90520a0bfc6e877446dddac6c9316706be43e461506`.
- All 1,140 non-signature ZIP entries, including manifest, DEX, resources, native libraries, and embedded seed, are byte-identical to the tested V42 source.
- ZIP integrity and strict JAR signature verification passed. Strict verification used a temporary truststore containing only the intended public certificate; no system truststore was changed.
- The output directory includes `signing-report.json`, `SHA256SUMS.txt`, and `signer-certificate.der`. No private key or signing password was copied into it.
- The signing workflow performed no device actions. The operator subsequently reported V42's eight functional release checks passed on the Galaxy S4/Android 4.4.2 and Galaxy S20 Plus/Android 13. These were empirical runs without logs or save backups; see [docs/TESTING.md](docs/TESTING.md). No installed-device hash or signer was independently captured for those runs.

The selected signer differs from the development signer (`87b0896f00d62d61524a0726033fc6fc55363161bf3f7028832335fb4be3253b`). Android will reject an in-place update over that installation. Preserve wanted progress before replacing the debug-signed installation; uninstalling removes its private app data. Keep the selected signing identity stable for subsequent public updates.

### Newest V43 signed technical checkpoint

The revised normal-goal V43 APK is `native-patches/v43-offline-christmas/normal-goals-25-50/BirzzleFever-1.1.2-v43-normal-goals-FruitSpy-signed.apk`, SHA-256 `fdc05ae28a20dec263871270d7d4ffe2c0ad8ccc97a6f8bf83ace0a83628b01b`. The operator-provided external FruitSpy keystore signed the unsigned APK without disclosing or archiving its private material or passwords. The APK's certificate SHA-256 equals V42's `7e9ad31c19d7ee447c8e1a58bc7ca4be51acf4489f55cf2258124c45d7213417`. Strict JAR verification against a temporary truststore containing only that public certificate, ZIP integrity, and preservation of all 1,140 non-signature payloads pass; see `normal-goals-25-50/FruitSpy-signing-report.json`. The write-once technical checkpoint is `checkpoints/2026-09-26-v43-normal-goals-fruitspy-fdc05ae28a20/`. Following explicit operator authorization to discard the old saves, both debug-signed test installations were fully uninstalled, and the FruitSpy-signed APK was installed on S4 and S20 with exact installed hashes verified. This does **not** establish public-release clearance or physical startup qualification. Evidence: `device-snapshots/v43-fruitspy-normal-goals-fresh-install/deployment.json`.

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
- Keep the internal alias and keystore location in private operator records. Publish only necessary verification metadata: algorithms, public certificate fingerprint, APK checksum, and verification results.
- Every update must use the same key. Android 4.4 cannot rotate the signing identity while preserving in-place updates.
- Losing the key permanently ends the official in-place update path.
- A release-signed APK cannot update the current debug-signed installation; the first release-key cutover requires uninstall/reinstall with data backup or self-seeding.

## Reuse policy

A key can technically sign multiple APK packages. Prefer one key per independent project so compromise, ownership transfer, certificate linkage, and legacy signature-level trust remain isolated. Reuse only when multiple apps intentionally share one publisher and security boundary.

## Protection provided

An APK signed by another key cannot install over the official package on an ordinary Android device. A third party may still publish a differently signed fork, require users to uninstall first, use another package name, or bypass checks on a modified/rooted system. Signing protects the official update path; it does not prevent all redistribution or modification.
