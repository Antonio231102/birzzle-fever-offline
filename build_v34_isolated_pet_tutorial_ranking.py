import argparse
import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v33-pet-tutorial-retryable-ranking/"
    "BirzzleFever-1.1.2-v33-pet-tutorial-retryable-ranking.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v33-pet-tutorial-retryable-ranking/"
    "libbirzzle-v33-pet-tutorial-retryable-ranking.so"
)
OUTPUT_DIR = Path("native-patches/v34-isolated-pet-tutorial-ranking")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v34-isolated-pet-tutorial-ranking.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v34-isolated-pet-tutorial-ranking-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v34-isolated-pet-tutorial-ranking.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "71553a6a2b06244155705e40ccb0ecaee75e74ada5c65b7e89f4c1bdf82597a6"
EXPECTED_SOURCE_LIBRARY_SHA256 = "d620863b6c8e5ed1a1a2c981e509cb9acdf86e31d99341be5d3955eebdb350e4"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

GET_RANKING = 0x163B78
OPERATOR_NEW = 0x18FB58
TUTORIAL_MARK_STUB = 0x2ACF10
RETRYABLE_DISPATCH_STUB = 0x2ACF20

# The legacy stubs calculated ADD-PC literals as though Thumb aligned the PC.
# This high-register ADD actually observes instruction_address + 4, shifting
# their two allocated bytes by +2. Keep those deployed addresses intact:
#   0x2c7732 = request gate, 0x2c7733 = power-up return marker.
# Use the first genuinely unused byte of the same four-byte BSS extension for
# the independent pet-tutorial marker.
TUTORIAL_PENDING = 0x2C7730
LEGACY_REQUEST_GATE = 0x2C7732
LEGACY_POWERUP_PENDING = 0x2C7733


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


def add_pc_literal(add_instruction: int, target: int) -> bytes:
    # Thumb ADD (high registers) reads PC as this instruction's address + 4;
    # unlike LDR (literal), it does not word-align that value.
    return struct.pack("<I", target - (add_instruction + 4))


def tutorial_mark_code(address: int) -> bytes:
    code = bytes.fromhex(
        "024b"      # ldr r3, literal
        "7b44"      # add r3, pc
        "0122"      # movs r2, #1
        "1a70"      # strb r2, [r3]
    )
    code += thumb2_branch(address + 8, OPERATOR_NEW, False)
    code += add_pc_literal(address + 2, TUTORIAL_PENDING)
    if len(code) != 0x10:
        raise SystemExit("unexpected tutorial marker stub size")
    return code


def isolated_retryable_dispatch_code(address: int) -> bytes:
    # Accept either kind of deliberate menu return, but keep the pet tutorial
    # marker independent from V14's ProcessGameStart clear. Clear both markers
    # only after GetRanking closes the request gate, proving it accepted the
    # request. A rejected early dispatch therefore remains retryable.
    code = bytes.fromhex(
        "0b4b"      # ldr r3, [pc, #0x2c] (tutorial marker literal)
        "7b44"      # add r3, pc
        "1a78"      # ldrb r2, [r3] (tutorial marker)
        "002a"      # cmp r2, #0
        "02d1"      # bne pending
        "da78"      # ldrb r2, [r3, #3] (legacy power-up marker)
        "002a"      # cmp r2, #0
        "0cd0"      # beq direct_get_ranking
        "10b5"      # push {r4, lr}
        "1c1c"      # adds r4, r3, #0
        "0022"      # movs r2, #0
        "a270"      # strb r2, [r4, #2] (legacy request gate)
    )
    code += thumb2_branch(address + len(code), GET_RANKING, True)
    code += bytes.fromhex(
        "a278"      # ldrb r2, [r4, #2]
        "012a"      # cmp r2, #1 (GetRanking accepted)
        "02d1"      # bne return_with_markers_intact
        "0022"      # movs r2, #0
        "2270"      # strb r2, [r4] (consume tutorial marker)
        "e270"      # strb r2, [r4, #3] (consume power-up marker)
        "10bd"      # pop {r4, pc}
    )
    code += thumb2_branch(address + len(code), GET_RANKING, False)
    code += bytes.fromhex("c046")
    code += add_pc_literal(address + 2, TUTORIAL_PENDING)
    if len(code) != 0x34:
        raise SystemExit(f"unexpected isolated dispatch size: {len(code):#x}")
    if (LEGACY_REQUEST_GATE, LEGACY_POWERUP_PENDING) != (
        TUTORIAL_PENDING + 2,
        TUTORIAL_PENDING + 3,
    ):
        raise SystemExit("ranking state bytes are no longer in the expected layout")
    return code


_parser = argparse.ArgumentParser(description="Apply the V34 isolated pet ranking patch.")
_parser.add_argument("--native-only", action="store_true", help="Build only the native library; do not read, package, or sign an APK.")
_args = _parser.parse_args()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not _args.native_only and sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V33 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V33 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
patches = (
    (
        TUTORIAL_MARK_STUB,
        bytes.fromhex("024b7b4401221a70e2f61ebe1da80100"),
        tutorial_mark_code(TUTORIAL_MARK_STUB),
    ),
    (
        RETRYABLE_DISPATCH_STUB,
        bytes.fromhex(
            "094b7b441a78002a0bd010b55c1e00222270b6f621fe2278012a01d100226270"
            "10bdb6f619bec0460da80100" + "00" * 8
        ),
        isolated_retryable_dispatch_code(RETRYABLE_DISPATCH_STUB),
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
        raise SystemExit("unexpected V33 APK libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V33 APK libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V33 APK classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V33 APK seed")

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
    raise SystemExit("V33 APK does not contain libbirzzle")
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
