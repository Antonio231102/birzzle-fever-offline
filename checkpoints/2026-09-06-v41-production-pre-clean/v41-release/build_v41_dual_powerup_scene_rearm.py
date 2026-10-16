import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v37-global-powerup-scene-marker/"
    "BirzzleFever-1.1.2-v37-global-powerup-scene-marker.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v37-global-powerup-scene-marker/"
    "libbirzzle-v37-global-powerup-scene-marker.so"
)
OUTPUT_DIR = Path("native-patches/v41-dual-powerup-scene-rearm")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v41-dual-powerup-scene-rearm.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v41-dual-powerup-scene-rearm-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v41-dual-powerup-scene-rearm.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "26b1e87a4a8b9caf68f1c6e7d57fdf57d58b9936391206a562c3917d85e866bb"
EXPECTED_SOURCE_LIBRARY_SHA256 = "5cc699aedb1ad48ab0f46edcdd0b0b4cc733c1de01f906bac382d175a601d94f"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

GLOBAL_SCENE_MARK_STUB = 0x2ACF60
POWERUP_PENDING = 0x2C7733


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def add_pc_literal(add_instruction: int, target: int) -> bytes:
    return struct.pack("<I", target - (add_instruction + 4))


def dual_scene_marker_code(address: int) -> bytes:
    # Preserve SetCurrentScene's store and arm a deliberate ranking generation
    # for either the legacy scene 0x0a or the observed power-up scene 0x1a.
    # Unlike V38-V40, this production stub performs no diagnostic trace writes.
    code = bytes.fromhex(
        "0166"      # str r1, [r0, #0x60]
        "0a29"      # cmp r1, #0x0a
        "01d0"      # beq mark_powerup
        "1a29"      # cmp r1, #0x1a
        "03d1"      # bne return
        "024b"      # mark_powerup: ldr r3, [pc, #8]
        "7b44"      # add r3, pc
        "0122"      # movs r2, #1
        "1a70"      # strb r2, [r3] (power-up pending)
        "7047"      # return: bx lr
    )
    code += add_pc_literal(address + 0x0C, POWERUP_PENDING)
    if len(code) != 0x18:
        raise SystemExit(f"unexpected dual-scene marker size: {len(code):#x}")
    return code


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V37 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V37 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
expected_scene_stub = bytes.fromhex(
    "0a2901d001667047024b7b4401221a7001667047c5a70100"
)
replacement_scene_stub = dual_scene_marker_code(GLOBAL_SCENE_MARK_STUB)
actual = bytes(
    library[
        GLOBAL_SCENE_MARK_STUB : GLOBAL_SCENE_MARK_STUB + len(expected_scene_stub)
    ]
)
if actual != expected_scene_stub:
    raise SystemExit(
        f"unexpected bytes at {GLOBAL_SCENE_MARK_STUB:#x}: "
        f"{actual.hex()} != {expected_scene_stub.hex()}"
    )
library[
    GLOBAL_SCENE_MARK_STUB : GLOBAL_SCENE_MARK_STUB + len(expected_scene_stub)
] = replacement_scene_stub
OUTPUT_LIBRARY.write_bytes(library)

with zipfile.ZipFile(SOURCE_APK, "r") as source:
    if sha256_bytes(source.read("lib/armeabi/libbirzzle.so")) != EXPECTED_SOURCE_LIBRARY_SHA256:
        raise SystemExit("V37 APK does not contain the expected libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V37 libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V37 classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V37 seed")

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
    raise SystemExit("V37 APK does not contain libbirzzle")
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

print(f"dual_scene_stub={replacement_scene_stub.hex()}")
print(f"libbirzzle_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
