import argparse
import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v34-isolated-pet-tutorial-ranking/"
    "BirzzleFever-1.1.2-v34-isolated-pet-tutorial-ranking.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v34-isolated-pet-tutorial-ranking/"
    "libbirzzle-v34-isolated-pet-tutorial-ranking.so"
)
OUTPUT_DIR = Path("native-patches/v35-pet-tutorial-state41-marker")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v35-pet-tutorial-state41-marker.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v35-pet-tutorial-state41-marker-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v35-pet-tutorial-state41-marker.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "3e27f39f000eea58a00a5ffa325b4c83ae3f66a526fe4e3c3c41f5717e10e6d4"
EXPECTED_SOURCE_LIBRARY_SHA256 = "f235f8da9b8e95ac04deb5e7eb6709873c4a1e1ccd6bf2f437facf585129edcd"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

STATE41_MESSAGE_CALL = 0x0AEDDA
STATE41_MARK_STUB = 0x2ACF60
SEND_MESSAGE_PLT_ARM = 0x073B50
TUTORIAL_PENDING = 0x2C7730


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def thumb2_branch(source: int, target: int, link: bool) -> bytes:
    offset = target - (source + 4)
    if offset & 1 or not -(1 << 24) <= offset < (1 << 24):
        raise ValueError(f"invalid Thumb-2 branch {source:#x} -> {target:#x}")
    value = offset & 0x1FFFFFF
    s = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    j1 = (~(i1 ^ s)) & 1
    j2 = (~(i2 ^ s)) & 1
    first = 0xF000 | (s << 10) | ((value >> 12) & 0x3FF)
    second = (0xD000 if link else 0x9000) | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


def thumb2_blx(source: int, target: int) -> bytes:
    offset = target - ((source + 4) & ~3)
    if offset & 3 or not -(1 << 24) <= offset < (1 << 24):
        raise ValueError(f"invalid Thumb-2 BLX {source:#x} -> {target:#x}")
    value = offset & 0x1FFFFFF
    s = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    j1 = (~(i1 ^ s)) & 1
    j2 = (~(i2 ^ s)) & 1
    first = 0xF000 | (s << 10) | ((value >> 12) & 0x3FF)
    second = 0xC000 | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


def state41_mark_code(address: int) -> bytes:
    # The observed free-pet flow traverses state 0x41, which posts message 0x42,
    # but not V32's later state-0x42 allocation hook. Preserve r2 because it is
    # the third argument to the original ARM-state PLT call.
    code = bytes.fromhex(
        "04b5"      # push {r2, lr}
        "044b"      # ldr r3, [pc, #0x10]
        "7b44"      # add r3, pc
        "0122"      # movs r2, #1
        "1a70"      # strb r2, [r3]
        "009a"      # ldr r2, [sp]
    )
    code += thumb2_blx(address + len(code), SEND_MESSAGE_PLT_ARM)
    code += bytes.fromhex(
        "04bd"      # pop {r2, pc}
        "c046"      # align literal
    )
    add_pc_instruction = address + 4
    code += struct.pack("<I", TUTORIAL_PENDING - (add_pc_instruction + 4))
    if len(code) != 0x18:
        raise SystemExit(f"unexpected state-41 wrapper size: {len(code):#x}")
    return code


_parser = argparse.ArgumentParser(description="Apply the V35 pet tutorial marker patch.")
_parser.add_argument("--native-only", action="store_true", help="Build only the native library; do not read, package, or sign an APK.")
_args = _parser.parse_args()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not _args.native_only and sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V34 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V34 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
patches = (
    (
        STATE41_MARK_STUB,
        bytes(0x18),
        state41_mark_code(STATE41_MARK_STUB),
    ),
    (
        STATE41_MESSAGE_CALL,
        thumb2_blx(STATE41_MESSAGE_CALL, SEND_MESSAGE_PLT_ARM),
        thumb2_branch(STATE41_MESSAGE_CALL, STATE41_MARK_STUB, True),
    ),
)
for offset, expected, replacement in patches:
    actual = bytes(library[offset : offset + len(expected)])
    if actual != expected:
        raise SystemExit(
            f"unexpected bytes at {offset:#x}: {actual.hex()} != {expected.hex()}"
        )
    library[offset : offset + len(expected)] = replacement
    print(f"{offset:#x}: {expected.hex()} -> {replacement.hex()}")
OUTPUT_LIBRARY.write_bytes(library)
if _args.native_only:
    print(f"native_sha256={hashlib.sha256(library).hexdigest()}")
    raise SystemExit(0)

with zipfile.ZipFile(SOURCE_APK, "r") as source:
    if sha256_bytes(source.read("lib/armeabi/libbirzzle.so")) != EXPECTED_SOURCE_LIBRARY_SHA256:
        raise SystemExit("unexpected V34 APK libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V34 APK libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V34 APK classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V34 APK seed")

    temporary = UNSIGNED_APK.with_suffix(".tmp.apk")
    with zipfile.ZipFile(temporary, "w") as output:
        replaced = False
        for item in source.infolist():
            if item.filename.upper().startswith("META-INF/"):
                continue
            payload = source.read(item.filename)
            if item.filename == "lib/armeabi/libbirzzle.so":
                payload = bytes(library)
                replaced = True
            output.writestr(item, payload)
if not replaced:
    raise SystemExit("V34 APK does not contain libbirzzle")
temporary.replace(UNSIGNED_APK)

shutil.copyfile(UNSIGNED_APK, SIGNED_APK)
run(
    "jarsigner",
    "-keystore",
    str(KEYSTORE),
    "-storepass",
    "android",
    "-keypass",
    "android",
    "-sigalg",
    "SHA256withRSA",
    "-digestalg",
    "SHA-256",
    str(SIGNED_APK),
    "androiddebugkey",
)
run("jarsigner", "-verify", str(SIGNED_APK))

with zipfile.ZipFile(SIGNED_APK, "r") as result:
    if result.read("lib/armeabi/libbirzzle.so") != bytes(library):
        raise SystemExit("signed APK libbirzzle mismatch")
    if sha256_bytes(result.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("signed APK libef2d mismatch")
    if sha256_bytes(result.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("signed APK classes.dex mismatch")
    if sha256_bytes(result.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("signed APK seed mismatch")

print(f"libbirzzle_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
