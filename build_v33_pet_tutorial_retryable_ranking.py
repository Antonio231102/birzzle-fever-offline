import argparse
import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v32-pet-tutorial-ranking-rearm/"
    "BirzzleFever-1.1.2-v32-pet-tutorial-ranking-rearm.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v32-pet-tutorial-ranking-rearm/"
    "libbirzzle-v32-pet-tutorial-ranking-rearm.so"
)
OUTPUT_DIR = Path("native-patches/v33-pet-tutorial-retryable-ranking")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v33-pet-tutorial-retryable-ranking.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v33-pet-tutorial-retryable-ranking-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v33-pet-tutorial-retryable-ranking.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "d5a9eec2a39a46143db6d8af90f25de0a2348a17f993abd231c2f64e94366793"
EXPECTED_SOURCE_LIBRARY_SHA256 = "6e6f952ee56ae911b86d4182b43ecd1988efb8a4506b84945d7bc7991503940e"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

GET_RANKING = 0x163B78
CONDITIONAL_DISPATCH_CALL = 0x148E38
V32_CONDITIONAL_DISPATCH_STUB = 0x2ACED0
RETRYABLE_DISPATCH_STUB = 0x2ACF20
RANKING_REQUEST_GATE = 0x2C7730
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


def retryable_dispatch_code(address: int) -> bytes:
    # A tutorial/main-menu generation remains pending until GetRanking actually
    # accepts a request. Re-arm the request gate, call GetRanking, and consume
    # the marker only when GetRanking closes the gate again. If an earlier
    # dispatch occurs before CHSPManager is ready, retain the marker so the
    # later main-menu dispatch can retry instead of starving its UI callback.
    code = bytes.fromhex(
        "094b"      # ldr r3, [pc, #0x24] (pending-marker literal)
        "7b44"      # add r3, pc
        "1a78"      # ldrb r2, [r3]
        "002a"      # cmp r2, #0
        "0bd0"      # beq direct_get_ranking
        "10b5"      # push {r4, lr}
        "5c1e"      # subs r4, r3, #1 (request gate)
        "0022"      # movs r2, #0
        "2270"      # strb r2, [r4] (re-arm)
    )
    code += thumb2_branch(address + len(code), GET_RANKING, True)
    code += bytes.fromhex(
        "2278"      # ldrb r2, [r4]
        "012a"      # cmp r2, #1 (accepted request closed the gate)
        "01d1"      # bne return_with_marker_intact
        "0022"      # movs r2, #0
        "6270"      # strb r2, [r4, #1] (consume pending marker)
        "10bd"      # pop {r4, pc}
    )
    code += thumb2_branch(address + len(code), GET_RANKING, False)
    code += bytes.fromhex("c046")  # align the literal
    pc_for_add = (address + 2 + 4) & ~3
    code += struct.pack("<I", RANKING_GENERATION_PENDING - pc_for_add)
    if len(code) != 0x2C:
        raise SystemExit(f"unexpected retryable dispatch size: {len(code):#x}")
    if RANKING_GENERATION_PENDING - RANKING_REQUEST_GATE != 1:
        raise SystemExit("ranking gate and generation marker are no longer adjacent")
    return code


_parser = argparse.ArgumentParser(description="Apply the V33 retryable pet ranking patch.")
_parser.add_argument("--native-only", action="store_true", help="Build only the native library; do not read, package, or sign an APK.")
_args = _parser.parse_args()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not _args.native_only and sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V32 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V32 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
patches = (
    (
        RETRYABLE_DISPATCH_STUB,
        bytes(0x2C),
        retryable_dispatch_code(RETRYABLE_DISPATCH_STUB),
    ),
    (
        CONDITIONAL_DISPATCH_CALL,
        thumb2_branch(CONDITIONAL_DISPATCH_CALL, V32_CONDITIONAL_DISPATCH_STUB, True),
        thumb2_branch(CONDITIONAL_DISPATCH_CALL, RETRYABLE_DISPATCH_STUB, True),
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
        raise SystemExit("unexpected V32 APK libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V32 APK libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V32 APK classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V32 APK seed")

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
    raise SystemExit("V32 APK does not contain libbirzzle")
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
