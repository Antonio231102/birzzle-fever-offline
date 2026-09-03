# Repository inclusion policy

## Purpose

The local workspace is both a development tree and an evidence archive. Git is intentionally a curated source view, not a mirror of every local file. `.gitignore` exclusions do not delete, move, or modify excluded files.

## Included

Commit material when it is authored by the project and useful for implementation or independent review:

- Python patch, build, analysis, and test source;
- ARM/Thumb assembly source;
- Xposed module source and compile-time stubs;
- Markdown design, research, checkpoint, and result summaries;
- aggregate JSON manifests that contain no private identifiers or raw save payloads;
- repository validation and GitHub workflow files;
- public checksums and signing-certificate fingerprints;
- the project license and third-party-rights notice.

Historical or rejected approaches may remain when they explain an important invariant or prevent recurrence. Label them clearly as investigative or rejected.

## Excluded

Never commit:

- original, modified, signed, or unsigned APKs;
- compressed APKs and Android incremental-install signatures;
- extracted `.so` libraries, DEX/resources, decompiled Smali trees, or original assets;
- compiled patch blobs, ELF/object files, or generated build directories;
- Titanium Backup bundles, save archives, embedded seed archives, or decrypted profiles;
- device app-data archives, response pools, raw checkpoint state, or cleanup backups;
- logcat captures, device logs, screenshots, recordings, or other media;
- Android SDK/platform tools, apktool JARs, LLVM distributions, or vendored Python dependencies;
- debug keystores, release keys, certificates containing private keys, passwords, tokens, `.env` files, or account material;
- fixed ADB serial numbers, workstation usernames, or absolute private workstation paths.

Public certificates can be added deliberately during a release even though certificate extensions are ignored by default. Use `git add -f` only after review and document why the exception is public.

## Evidence reduction

When raw evidence supports a claim:

1. retain the raw capture locally;
2. calculate and record its checksum if provenance matters;
3. extract only the events and invariants needed for review;
4. remove device serials, unrelated processes, account data, tokens, and personal state;
5. publish a Markdown or JSON aggregate;
6. name the environment and exact limitations.

A checksum proves which local artifact was reviewed; it does not make the underlying private artifact suitable for publication.

## Milestone preservation

Binary checkpoint contents stay local. Git preserves each milestone through some combination of:

- patch/build source;
- authored assembly;
- exact source/output hashes;
- changed offsets and byte sequences;
- checkpoint notes;
- aggregate behavioral results;
- acceptance or rejection rationale.

The initial Git commit is a curated import. It must not be presented as the original chronological commit history; chronology is reconstructed in `CHANGELOG.md` from the surviving artifacts and test records.

## Enforcement

Run before every push:

```powershell
python scripts/validate_repository.py
```

The GitHub workflow repeats the same policy audit and safe unit test. Review `git status --short` and `git diff --cached --stat` before committing. Do not use broad force-add commands to override `.gitignore`.

## Local retention

Excluded files are deliberately retained in the workspace for provenance, rollback, and future patcher development. Removing a file from Git's candidate set is not authorization to remove it from disk. Any later local deletion requires an independent verified backup and explicit approval.
