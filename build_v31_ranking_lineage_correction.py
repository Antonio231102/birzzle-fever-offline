import argparse
import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v26-modern-syscalls/"
    "BirzzleFever-1.1.2-v26-modern-syscalls.apk"
)
CORRECT_RANKING_SOURCE = Path(
    "native-patches/v14-powerup-scene-pending/libbirzzle.so"
)
OUTPUT_DIR = Path("native-patches/v31-ranking-lineage-correction")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle-v31-ranking-lineage-correction.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v31-ranking-lineage-correction-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v31-ranking-lineage-correction.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")

EXPECTED_SOURCE_APK_SHA256 = "cf34c8e640ee785cf34d1b75d55b5610b01357fda9315c2f380d7a6923260ee8"
EXPECTED_V14_LIBRARY_SHA256 = "437d09e9463c77d9b0a8d9e658ff8cd7d31de53c1a572786d5b9e6b7db1ccdb5"
EXPECTED_V26_LIBRARY_SHA256 = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"
EXPECTED_EF2D_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_CLASSES_SHA256 = "3ad88604da0fd39e64cd75e6c2560a306c6964ec6d20c5722fd8eb97a81f3fb6"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"

# V15 accidentally applied these unlimited-play changes to V11 instead of V14,
# discarding V12-V14's clean-start ranking and power-up-return corrections.
# Apply the same two V15 changes to the actual V14 successor.
PATCHES = (
    (0x1484FC, bytes.fromhex("7942"), bytes.fromhex("0021")),
    (0x171BFC, bytes.fromhex("052119f79dbc"), bytes.fromhex("f8b55f465646")),
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def run(*args: str) -> None:
    subprocess.run(args, check=True)


_parser = argparse.ArgumentParser(description="Apply the V31 ranking lineage correction.")
_parser.add_argument("--native-only", action="store_true", help="Build only the native library; do not read, package, or sign an APK.")
_args = _parser.parse_args()

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if not _args.native_only and sha256(SOURCE_APK) != EXPECTED_SOURCE_APK_SHA256:
    raise SystemExit("unexpected V26 source APK")
if sha256(CORRECT_RANKING_SOURCE) != EXPECTED_V14_LIBRARY_SHA256:
    raise SystemExit("unexpected V14 ranking source library")

library = bytearray(CORRECT_RANKING_SOURCE.read_bytes())
for offset, expected, replacement in PATCHES:
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
    if sha256_bytes(source.read("lib/armeabi/libbirzzle.so")) != EXPECTED_V26_LIBRARY_SHA256:
        raise SystemExit("unexpected V26 libbirzzle")
    if sha256_bytes(source.read("lib/armeabi/libef2d.so")) != EXPECTED_EF2D_SHA256:
        raise SystemExit("unexpected V26 libef2d")
    if sha256_bytes(source.read("classes.dex")) != EXPECTED_CLASSES_SHA256:
        raise SystemExit("unexpected V26 classes.dex")
    if sha256_bytes(source.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("unexpected V26 seed")

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
    raise SystemExit("V26 APK does not contain libbirzzle")
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
