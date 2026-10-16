import argparse
import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v31-ranking-lineage-correction/"
    "BirzzleFever-1.1.2-v31-ranking-lineage-correction.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v31-ranking-lineage-correction/"
    "libbirzzle-v31-ranking-lineage-correction.so"
)
OUTPUT_DIR = Path("native-patches/v32-pet-tutorial-ranking-rearm")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v32-pet-tutorial-ranking-rearm.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v32-pet-tutorial-ranking-rearm-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v32-pet-tutorial-ranking-rearm.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "8a18f16280d46a9c3339b24d77ec6b2e332224982a449bdc7d75bedfe8c4b06b"
EXPECTED_SOURCE_LIBRARY_SHA256 = "93b78ba94ac2162fb0272717ef2ddd418fc1d7b9c89a5c0b4d91825332bb0727"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

# OnShowPetDialogTutorial is a tutorial-manager callback. Normal purchases call
# CHSPManager::CompletePostInventory directly and never traverse this symbol.
# Its state-0x42 branch is the once-per-save pet tutorial step immediately
# before the BuyPet flow. Hook that branch's operator-new call, not the callback
# entry, so even an out-of-state callback cannot arm a ranking generation.
TUTORIAL_MARK_CALL = 0x0AED5C
OPERATOR_NEW = 0x18FB58
TUTORIAL_MARK_STUB = 0x2ACF10
RANKING_GENERATION_PENDING = 0x2C7731


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


def mark_then_tail(address: int, target: int) -> bytes:
    # ldr r3, literal; add r3, pc; movs r2, #1; strb r2, [r3]
    code = bytes.fromhex("024b7b4401221a70")
    # Preserve the original call's LR: tail-call operator new, which returns to
    # the instruction after TUTORIAL_MARK_CALL.
    code += thumb2_branch(address + 8, target, False)
    pc_for_add = (address + 2 + 4) & ~3
    code += struct.pack("<I", RANKING_GENERATION_PENDING - pc_for_add)
    if len(code) != 0x10:
        raise SystemExit("unexpected tutorial marker stub size")
    return code


_parser = argparse.ArgumentParser(description="Apply the V32 pet tutorial ranking patch.")
_parser.add_argument("--native-only", action="store_true", help="Build only the native library; do not read, package, or sign an APK.")
_args = _parser.parse_args()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not _args.native_only and sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V31 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V31 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
patches = (
    (
        TUTORIAL_MARK_STUB,
        bytes(0x10),
        mark_then_tail(TUTORIAL_MARK_STUB, OPERATOR_NEW),
    ),
    (
        TUTORIAL_MARK_CALL,
        thumb2_branch(TUTORIAL_MARK_CALL, OPERATOR_NEW, True),
        thumb2_branch(TUTORIAL_MARK_CALL, TUTORIAL_MARK_STUB, True),
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
        raise SystemExit("unexpected V31 APK libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V31 APK libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V31 APK classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V31 APK seed")

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
    raise SystemExit("V31 APK does not contain libbirzzle")
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
