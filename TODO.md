# Release roadmap

V25 is the current functionally qualified development milestone. The source repository is curated for an eventual public release, but no public APK is committed or endorsed.

## Distribution decision

- [ ] Complete legal review of modified-APK redistribution.
- [ ] If redistribution is not approved, ship only a user-supplied-original patcher.
- [ ] Document provenance requirements for the sanitized bootstrap seed.
- [x] Use the `birzzle-fever-offline` repository name with private visibility under the authenticated GitHub account.

## Reproducible build

- [ ] Convert the V1–V23 historical chain into a clean transform from a validated user-supplied Birzzle Fever 1.1.2 APK.
- [ ] Express V24 Java/manifest/GCM/network changes as narrow expected-input patches rather than publishing a decompiled tree.
- [ ] Reproduce `SaveBootstrap` and the V25 two-slot ranking template without committing save archives.
- [ ] Rebuild every ARM/Thumb blob from tracked `.S` sources with pinned commands.
- [ ] Verify every input range, output library, seed, APK, and signing certificate hash.
- [ ] Produce the same functional V25 result without depending on prior milestone APKs.

## Release signing

- [ ] Generate a dedicated release key outside the repository.
- [ ] Store at least two encrypted offline key backups and keep the password separately.
- [ ] Publish only the certificate and fingerprint.
- [ ] Record alignment, signature schemes, and `apksigner` verification in the release manifest.

## Compatibility

- [ ] Repeat clean-install and mature-save qualification on a second 32-bit ARM device before claiming broad support.
- [ ] Test a clean single-package installation on a modern Android version where 32-bit applications are supported.
- [ ] Exercise startup, first seed, ranking, power-up cancellation, mid-game quit, completed-game return, progression persistence, zero-life start, offline mode, and connected-interface mode.
- [ ] Publish aggregate results without device serials, logs, screenshots, tokens, or raw save data.

## Public release material

- [x] Add repository inclusion/exclusion policy.
- [x] Add architecture, build, installation, validation, contribution, and legal documentation.
- [x] Preserve milestone patch sources, checkpoint notes, and aggregate V25 evidence.
- [x] Add GitHub validation workflow and local repository-policy checker.
- [ ] Add final patcher usage, checksum, troubleshooting, rollback, and provenance instructions after the build is reproducible.
- [ ] Create, push, and verify the private GitHub remote.
