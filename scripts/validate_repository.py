#!/usr/bin/env python3
"""Fail when the Git index contains private or non-source research artifacts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
MAX_FILE_SIZE = 2 * 1024 * 1024

REQUIRED_PATHS = {
    ".gitattributes",
    ".gitignore",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "NOTICE",
    "README.md",
    "docs/ARCHITECTURE.md",
    "docs/BUILDING.md",
    "docs/INSTALLATION.md",
    "docs/REPOSITORY_POLICY.md",
    "docs/TESTING.md",
    "reverse-engineering/README.md",
    "reverse-engineering/smali/BirzzleFever.GetUniqueDeviceID.smali",
    "reverse-engineering/smali/BirzzleFever.Network.smali",
    "reverse-engineering/smali/BirzzleFever.PostInitialize-gcm-bypass.snippet.smali",
    "reverse-engineering/smali/MyApplication.onCreate-bootstrap.snippet.smali",
    "native-patches/v25-ranking-template/release-evidence.json",
}

FORBIDDEN_SUFFIXES = {
    ".a",
    ".aab",
    ".apk",
    ".apks",
    ".arsc",
    ".bin",
    ".bmp",
    ".cer",
    ".class",
    ".crt",
    ".der",
    ".dex",
    ".elf",
    ".gif",
    ".gz",
    ".idsig",
    ".jar",
    ".jpeg",
    ".jpg",
    ".jks",
    ".key",
    ".keystore",
    ".log",
    ".logcat",
    ".mp4",
    ".o",
    ".obj",
    ".p12",
    ".pem",
    ".pfx",
    ".png",
    ".properties",
    ".pyc",
    ".rar",
    ".so",
    ".tar",
    ".tgz",
    ".war",
    ".webm",
    ".webp",
    ".zip",
}

FORBIDDEN_PARTS = {
    ".analysis-tools",
    "__pycache__",
    "analysis-backup-compare",
    "analysis_extract",
    "apk-build",
    "apktool",
    "build-v2",
    "device-cleanup-backups",
    "device-snapshots",
    "minimal-public-save",
    "platform-tools-latest-windows",
    "recovery-backups",
    "save-analysis",
    "tools",
    "v25-soak-checkpoints",
}
ALLOWED_FORBIDDEN_PART_PATHS = {
    "native-patches/v24-connectivity-independent/apktool/smali/com/halfbrick/birzzlefever/SaveBootstrap.smali",
}


# Construct local-only values in pieces so this validator does not match itself.
PRIVATE_LITERALS = {
    "4b53" + "e568": "authorized test-device serial",
    "C:\\Users\\" + "Antonio": "private workstation home path",
}


def tracked_paths() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    return [entry.decode("utf-8") for entry in result.stdout.split(b"\0") if entry]


def main() -> int:
    try:
        tracked = tracked_paths()
    except (FileNotFoundError, subprocess.CalledProcessError) as error:
        print(f"repository validation could not enumerate Git files: {error}", file=sys.stderr)
        return 2

    errors: list[str] = []
    tracked_set = set(tracked)

    for required in sorted(REQUIRED_PATHS - tracked_set):
        errors.append(f"missing required tracked file: {required}")

    for relative in tracked:
        logical = PurePosixPath(relative)
        suffix = logical.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            errors.append(f"forbidden tracked extension {suffix}: {relative}")

        bad_parts = FORBIDDEN_PARTS.intersection(logical.parts)
        if bad_parts and relative not in ALLOWED_FORBIDDEN_PART_PATHS:
            errors.append(
                f"forbidden tracked directory {sorted(bad_parts)[0]}: {relative}"
            )

        physical = ROOT / Path(*logical.parts)
        if not physical.is_file():
            continue
        size = physical.stat().st_size
        if size > MAX_FILE_SIZE:
            errors.append(f"tracked file exceeds {MAX_FILE_SIZE} bytes: {relative} ({size})")
            continue

        try:
            text = physical.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            errors.append(f"tracked file is not UTF-8 text: {relative}")
            continue

        for literal, label in PRIVATE_LITERALS.items():
            if literal in text:
                errors.append(f"{label} appears in tracked file: {relative}")

    if errors:
        print("repository policy validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(f"repository policy validation passed: {len(tracked)} tracked source files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
