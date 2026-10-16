"""Build or verify a narrowly patched Birzzle Fever 1.0.4 iOS IPA.

Only the two calls that probe the bundled game host are replaced. This does
not fabricate SERVER.INIT or POCKET.LOGIN replies or modify device saves.
"""

import argparse
import hashlib
import plistlib
import struct
import zipfile
from pathlib import Path

IOS_DIR = Path(__file__).resolve().parent
ORIGINAL = IOS_DIR / "com.halfbrick.birzzlefever-iOS5.1-(Clutch-2.0.4).ipa"
ORIGINAL_SHA256 = "544b0eec4836ab906733c36090b8d736face61dc25723ed7a127949f432ef053"
APP = "Payload/BirzzleFever HB.app/"
EXECUTABLE = APP + "BirzzleFever HB"
INFO = APP + "Info.plist"
# Thumb BL to the shared TCP probe at 0x1fad08 (image-relative addresses).
# Thumb movs r0, #1; nop preserves the surrounding function's return path.
PATCHES = (
    (0x17F830, bytes.fromhex("7bf06afa")),
    (0x22EFD8, bytes.fromhex("cbf796fe")),
)
REPLACEMENT = bytes.fromhex("012000bf")
IMAGE_BASE = 0x4000  # __TEXT vmaddr; the file's __TEXT starts at offset zero.


def digest(path):
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def ensure_inside_ios(path):
    path = path.resolve()
    if path.parent != IOS_DIR or path.suffix.lower() != ".ipa":
        raise ValueError("The output or verification IPA must be directly under ios/")
    if path == ORIGINAL:
        raise ValueError("Never overwrite or use the clean original as patched output")
    return path


def original_executable():
    if digest(ORIGINAL) != ORIGINAL_SHA256:
        raise ValueError("Clean IPA SHA-256 mismatch; no patch was applied")
    with zipfile.ZipFile(ORIGINAL) as archive:
        info = plistlib.loads(archive.read(INFO))
        if (info.get("CFBundleIdentifier"), info.get("CFBundleVersion"), info.get("CFBundleExecutable")) != (
            "com.halfbrick.birzzlefever", "1.0.4", "BirzzleFever HB"
        ):
            raise ValueError("Not the inspected iOS Birzzle Fever 1.0.4 build")
        original = archive.read(EXECUTABLE)
    if struct.unpack_from("<IIII", original) != (0xFEEDFACE, 12, 9, 2):
        raise ValueError("Not the inspected 32-bit ARMv7 executable")
    for address, expected in PATCHES:
        offset = address - IMAGE_BASE
        if original[offset : offset + len(expected)] != expected:
            raise ValueError(f"Probe call mismatch at image address 0x{address:x}")
    return original


def patched_executable(original):
    patched = bytearray(original)
    for address, expected in PATCHES:
        offset = address - IMAGE_BASE
        patched[offset : offset + len(expected)] = REPLACEMENT
    return bytes(patched)


def verify(output, original):
    expected = patched_executable(original)
    with zipfile.ZipFile(ORIGINAL) as clean, zipfile.ZipFile(output) as candidate:
        clean_names = clean.namelist()
        if candidate.namelist() != clean_names:
            raise ValueError("IPA member names or order changed")
        for name in clean_names:
            wanted = expected if name == EXECUTABLE else clean.read(name)
            if candidate.read(name) != wanted:
                raise ValueError(f"Unexpected IPA member change: {name}")
    print(f"Verified: two Thumb probe calls replaced; all other archive member contents unchanged: {output}")


def build(output, original):
    # Exclusive creation prevents accidental overwrite of an existing build.
    patched = patched_executable(original)
    with zipfile.ZipFile(ORIGINAL) as clean:
        stream = output.open("xb")
        try:
            with stream, zipfile.ZipFile(stream, "w") as candidate:
                candidate.comment = clean.comment
                for member in clean.infolist():
                    candidate.writestr(
                        member, patched if member.filename == EXECUTABLE else clean.read(member)
                    )
            verify(output, original)
        except BaseException:
            stream.close()
            output.unlink()
            raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    operation = parser.add_mutually_exclusive_group(required=True)
    operation.add_argument("--build", type=Path, metavar="IOS_OUTPUT_IPA")
    operation.add_argument("--verify", type=Path, metavar="IOS_PATCHED_IPA")
    args = parser.parse_args()
    original = original_executable()
    path = ensure_inside_ios(args.build if args.build is not None else args.verify)
    if args.build is not None:
        build(path, original)
    else:
        verify(path, original)


if __name__ == "__main__":
    main()
