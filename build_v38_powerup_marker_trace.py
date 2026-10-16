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
OUTPUT_DIR = Path("native-patches/v38-powerup-marker-trace")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v38-powerup-marker-trace.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v38-powerup-marker-trace-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v38-powerup-marker-trace.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "26b1e87a4a8b9caf68f1c6e7d57fdf57d58b9936391206a562c3917d85e866bb"
EXPECTED_SOURCE_LIBRARY_SHA256 = "5cc699aedb1ad48ab0f46edcdd0b0b4cc733c1de01f906bac382d175a601d94f"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

PROCESS_GAME_START = 0x142DF4
CLEAR_GAMESTART_STUB = 0x2ACF00
DISPATCH_ACCEPTED = 0x2ACF42
GLOBAL_SCENE_MARK_STUB = 0x2ACF60
DISPATCH_TRACE_STUB = 0x2ACF80
GAMESTART_TRACE_STUB = 0x2ACFA0
TRACE_BYTE = 0x2C7731
POWERUP_PENDING = 0x2C7733

TRACE_SCENE_0A = 0xA1
TRACE_GAMESTART_CLEAR = 0xC1
TRACE_DISPATCH_CONSUME = 0xD1


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
    return struct.pack("<I", target - (add_instruction + 4))


def traced_scene_marker_code(address: int) -> bytes:
    # Preserve the scene store for every value. For scene 0x0a, record A1 in
    # the unused diagnostic byte and arm powerup_return_pending at trace+2.
    code = bytes.fromhex(
        "0166"      # str r1, [r0, #0x60]
        "0a29"      # cmp r1, #0x0a
        "05d1"      # bne return
        "044b"      # ldr r3, [pc, #0x10]
        "7b44"      # add r3, pc
        "a122"      # movs r2, #0xa1
        "1a70"      # strb r2, [r3]
        "0122"      # movs r2, #1
        "9a70"      # strb r2, [r3, #2]
        "7047"      # return: bx lr
        "c046"      # alignment
        "c046"      # alignment
    )
    code += add_pc_literal(address + 8, TRACE_BYTE)
    if len(code) != 0x1C:
        raise SystemExit(f"unexpected scene trace stub size: {len(code):#x}")
    return code


def dispatch_trace_code() -> bytes:
    # The caller still owns {r4, lr}; preserve V37's marker cleanup and return.
    code = bytes.fromhex(
        "d122"      # movs r2, #0xd1
        "6270"      # strb r2, [r4, #1] (trace)
        "0022"      # movs r2, #0
        "2270"      # strb r2, [r4] (tutorial marker)
        "e270"      # strb r2, [r4, #3] (power-up marker)
        "10bd"      # pop {r4, pc}
    )
    if len(code) != 0x0C:
        raise SystemExit("unexpected dispatch trace stub size")
    return code


def gamestart_trace_code(address: int) -> bytes:
    # Record C1, preserve the original power-up marker clear, then tail-call
    # ProcessGameStart with the LR supplied by the original callsite.
    code = bytes.fromhex(
        "044b"      # ldr r3, [pc, #0x10]
        "7b44"      # add r3, pc
        "c122"      # movs r2, #0xc1
        "1a70"      # strb r2, [r3]
        "0022"      # movs r2, #0
        "9a70"      # strb r2, [r3, #2]
    )
    code += thumb2_branch(address + len(code), PROCESS_GAME_START, False)
    code += bytes.fromhex("c046c046")
    code += add_pc_literal(address + 2, TRACE_BYTE)
    if len(code) != 0x18:
        raise SystemExit(f"unexpected game-start trace stub size: {len(code):#x}")
    return code


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V37 source APK")
if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_LIBRARY_SHA256:
    raise SystemExit("unexpected V37 source library")

library = bytearray(SOURCE_LIBRARY.read_bytes())
patches = (
    (
        CLEAR_GAMESTART_STUB,
        bytes.fromhex("024b7b4400221a7095f674bf2da80100"),
        thumb2_branch(CLEAR_GAMESTART_STUB, GAMESTART_TRACE_STUB, False) + bytes(12),
    ),
    (
        DISPATCH_ACCEPTED,
        bytes.fromhex("00222270"),
        thumb2_branch(DISPATCH_ACCEPTED, DISPATCH_TRACE_STUB, False),
    ),
    (
        GLOBAL_SCENE_MARK_STUB,
        bytes.fromhex("0a2901d001667047024b7b4401221a7001667047c5a7010000000000"),
        traced_scene_marker_code(GLOBAL_SCENE_MARK_STUB),
    ),
    (
        DISPATCH_TRACE_STUB,
        bytes(0x0C),
        dispatch_trace_code(),
    ),
    (
        GAMESTART_TRACE_STUB,
        bytes(0x18),
        gamestart_trace_code(GAMESTART_TRACE_STUB),
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

if POWERUP_PENDING != TRACE_BYTE + 2:
    raise SystemExit("diagnostic bytes are no longer adjacent")

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

print(f"libbirzzle_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
