import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v35-pet-tutorial-state41-marker/"
    "BirzzleFever-1.1.2-v35-pet-tutorial-state41-marker.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v35-pet-tutorial-state41-marker/"
    "libbirzzle-v35-pet-tutorial-state41-marker.so"
)
OUTPUT_DIR = Path("native-patches/v36-buypet-response-ranking")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v36-buypet-response-ranking.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v36-buypet-response-ranking-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v36-buypet-response-ranking.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "5e4831f6fc22bd0da08b9094ff4d2f8ce53dd4e384241d52931f4dfc0e2c0009"
EXPECTED_SOURCE_LIBRARY_SHA256 = "e8d4e6717a7471191a2ca5cbc9a5a3cd2076d1a79f5cf8f3bafa3fb6e1dd80dd"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

OPERATOR_NEW = 0x18FB58
COMPLETE_POST_INVENTORY = 0x16817C
PET_STATE42_CALL = 0x0AED5C
PET_STATE41_CALL = 0x0AEDDA
SEND_MESSAGE_PLT_ARM = 0x073B50
BUY_PET_COMPLETION_CALL = 0x16B972
BUY_PET_MARK_STUB = 0x2ACF10
OBSOLETE_STATE41_STUB = 0x2ACF60
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


def mark_then_tail(address: int, target: int) -> bytes:
    code = bytes.fromhex(
        "024b"      # ldr r3, literal
        "7b44"      # add r3, pc
        "0122"      # movs r2, #1
        "1a70"      # strb r2, [r3]
    )
    code += thumb2_branch(address + 8, target, False)
    # Thumb ADD (high registers) reads instruction_address + 4 without the
    # word alignment used by LDR literals.
    code += struct.pack("<I", TUTORIAL_PENDING - (address + 2 + 4))
    if len(code) != 0x10:
        raise SystemExit("unexpected BuyPet marker stub size")
    return code


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V35 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V35 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
patches = (
    # The state-0x41 and state-0x42 callbacks were not traversed by the observed
    # free-pet purchase. Restore both original calls and remove their wrappers.
    (
        PET_STATE42_CALL,
        thumb2_branch(PET_STATE42_CALL, BUY_PET_MARK_STUB, True),
        thumb2_branch(PET_STATE42_CALL, OPERATOR_NEW, True),
    ),
    (
        PET_STATE41_CALL,
        thumb2_branch(PET_STATE41_CALL, OBSOLETE_STATE41_STUB, True),
        thumb2_blx(PET_STATE41_CALL, SEND_MESSAGE_PLT_ARM),
    ),
    (
        OBSOLETE_STATE41_STUB,
        bytes.fromhex("04b5044b7b4401221a70009ac6f5f0ed04bdc046c8a70100"),
        bytes(0x18),
    ),
    # POCKET.SET with extradata=BuyPet deterministically reaches this call after
    # both tutorial and ordinary pet purchases. Such a completed purchase is a
    # deliberate later generation, so retain its ranking request until the
    # main-menu dispatch accepts it.
    (
        BUY_PET_MARK_STUB,
        bytes.fromhex("024b7b4401221a70e2f61ebe1aa80100"),
        mark_then_tail(BUY_PET_MARK_STUB, COMPLETE_POST_INVENTORY),
    ),
    (
        BUY_PET_COMPLETION_CALL,
        thumb2_branch(BUY_PET_COMPLETION_CALL, COMPLETE_POST_INVENTORY, True),
        thumb2_branch(BUY_PET_COMPLETION_CALL, BUY_PET_MARK_STUB, True),
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

with zipfile.ZipFile(SOURCE_APK, "r") as source:
    if sha256_bytes(source.read("lib/armeabi/libbirzzle.so")) != EXPECTED_SOURCE_LIBRARY_SHA256:
        raise SystemExit("unexpected V35 APK libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V35 APK libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V35 APK classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V35 APK seed")

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
    raise SystemExit("V35 APK does not contain libbirzzle")
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
