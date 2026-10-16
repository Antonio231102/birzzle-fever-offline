import hashlib
import shutil
import struct
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v38-powerup-marker-trace/"
    "BirzzleFever-1.1.2-v38-powerup-marker-trace.apk"
)
SOURCE_LIBRARY = Path(
    "native-patches/v38-powerup-marker-trace/"
    "libbirzzle-v38-powerup-marker-trace.so"
)
OUTPUT_DIR = Path("native-patches/v39-all-scene-trace")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v39-all-scene-trace.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v39-all-scene-trace-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v39-all-scene-trace.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "6fd0c4777e1dabbbe9517deac6fa0294b0ddcaf0b093493d59549b55dea15e16"
EXPECTED_SOURCE_LIBRARY_SHA256 = "aad10aa760561e414a6db436c540255f3a429ab3e19dc2e6bf8bd59dd6127a3d"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

GLOBAL_SCENE_MARK_STUB = 0x2ACF60
TRACE_BYTE = 0x2C7731
POWERUP_PENDING = 0x2C7733


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def add_pc_literal(add_instruction: int, target: int) -> bytes:
    return struct.pack("<I", target - (add_instruction + 4))


def all_scene_trace_code(address: int) -> bytes:
    # Preserve SetCurrentScene's store, record every scene value in the unused
    # diagnostic byte, and retain V37's scene-0x0a power-up marker behavior.
    code = bytes.fromhex(
        "0166"      # str r1, [r0, #0x60]
        "044b"      # ldr r3, [pc, #0x10]
        "7b44"      # add r3, pc
        "1970"      # strb r1, [r3] (last scene)
        "0a29"      # cmp r1, #0x0a
        "01d1"      # bne return
        "0122"      # movs r2, #1
        "9a70"      # strb r2, [r3, #2] (power-up pending)
        "7047"      # return: bx lr
        "c046"      # align literal
    )
    code += add_pc_literal(address + 4, TRACE_BYTE)
    if len(code) != 0x18:
        raise SystemExit(f"unexpected all-scene trace stub size: {len(code):#x}")
    return code


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V38 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V38 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
expected_scene_stub = bytes.fromhex(
    "01660a2905d1044b7b44a1221a7001229a707047c046c046c5a70100"
)
replacement_scene_stub = all_scene_trace_code(GLOBAL_SCENE_MARK_STUB)
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
] = replacement_scene_stub + bytes(len(expected_scene_stub) - len(replacement_scene_stub))

if POWERUP_PENDING != TRACE_BYTE + 2:
    raise SystemExit("diagnostic bytes are no longer adjacent")

OUTPUT_LIBRARY.write_bytes(library)

with zipfile.ZipFile(SOURCE_APK, "r") as source:
    if sha256_bytes(source.read("lib/armeabi/libbirzzle.so")) != EXPECTED_SOURCE_LIBRARY_SHA256:
        raise SystemExit("V38 APK does not contain the expected libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V38 libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V38 classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V38 seed")

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
    raise SystemExit("V38 APK does not contain libbirzzle")
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

print(f"scene_trace_stub={replacement_scene_stub.hex()}")
print(f"libbirzzle_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
