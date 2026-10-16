import argparse
import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v36-buypet-response-ranking/"
    "BirzzleFever-1.1.2-v36-buypet-response-ranking.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v36-buypet-response-ranking/"
    "libbirzzle-v36-buypet-response-ranking.so"
)
OUTPUT_DIR = Path("native-patches/v37-global-powerup-scene-marker")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v37-global-powerup-scene-marker.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v37-global-powerup-scene-marker-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v37-global-powerup-scene-marker.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "a0e8187e3f67f7e010aa1c26631feac6363e2baaa591035826c3165342a952de"
EXPECTED_SOURCE_LIBRARY_SHA256 = "67a11e74e0cf9ae0540a46e62619b4b81e468bb0dc400fbd5976be3fb547e613"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

SET_CURRENT_SCENE = 0x141870
NARROW_POWERUP_MARK_CALL = 0x1437FA
NARROW_POWERUP_MARK_STUB = 0x2ACEF0
GLOBAL_POWERUP_MARK_STUB = 0x2ACF60
POWERUP_PENDING = 0x2C7733


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


def global_scene_marker_code(address: int) -> bytes:
    # Set powerup_return_pending for every transition into scene 0x0a, then
    # preserve SetCurrentScene's complete original behavior.
    code = bytes.fromhex(
        "0a29"      # cmp r1, #0x0a
        "01d0"      # beq mark_powerup
        "0166"      # str r1, [r0, #0x60]
        "7047"      # bx lr
        "024b"      # mark_powerup: ldr r3, [pc, #8]
        "7b44"      # add r3, pc
        "0122"      # movs r2, #1
        "1a70"      # strb r2, [r3]
        "0166"      # str r1, [r0, #0x60]
        "7047"      # bx lr
    )
    add_instruction = address + 10
    code += struct.pack("<I", POWERUP_PENDING - (add_instruction + 4))
    if len(code) != 0x18:
        raise SystemExit(f"unexpected global scene marker size: {len(code):#x}")
    return code


_parser = argparse.ArgumentParser(description="Apply the V37 global scene marker patch.")
_parser.add_argument("--native-only", action="store_true", help="Build only the native library; do not read, package, or sign an APK.")
_args = _parser.parse_args()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not _args.native_only and sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V36 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V36 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
patches = (
    # Route every SetCurrentScene invocation through the semantic scene-0x0a
    # marker instead of assuming ClickedFeverPlayButton is the sole entry path.
    (
        SET_CURRENT_SCENE,
        bytes.fromhex("01667047"),
        thumb2_branch(SET_CURRENT_SCENE, GLOBAL_POWERUP_MARK_STUB, False),
    ),
    (
        GLOBAL_POWERUP_MARK_STUB,
        bytes(0x18),
        global_scene_marker_code(GLOBAL_POWERUP_MARK_STUB),
    ),
    # Remove V14's now-redundant single-callsite wrapper. The original call now
    # reaches the central setter and is marked there like every other route.
    (
        NARROW_POWERUP_MARK_CALL,
        thumb2_branch(NARROW_POWERUP_MARK_CALL, NARROW_POWERUP_MARK_STUB, True),
        thumb2_branch(NARROW_POWERUP_MARK_CALL, SET_CURRENT_SCENE, True),
    ),
    (
        NARROW_POWERUP_MARK_STUB,
        bytes.fromhex("024b7b4401221a7094f6babc3da80100"),
        bytes(0x10),
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
        raise SystemExit("V36 APK does not contain the expected libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V36 libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V36 classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V36 seed")

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
    raise SystemExit("V36 APK does not contain libbirzzle")
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
