import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path


SOURCE_DIR = Path("native-patches/v26-modern-syscalls")
SOURCE_APK = SOURCE_DIR / "BirzzleFever-1.1.2-v26-modern-syscalls.apk"
SOURCE_LIBRARY = SOURCE_DIR / "libef2d-v26-modern-syscalls.so"
OUTPUT_DIR = Path("native-patches/v27-mtime-guard-restore")
OUTPUT_LIBRARY = OUTPUT_DIR / "libef2d-v27-mtime-guard-restore.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v27-mtime-guard-restore-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v27-mtime-guard-restore.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")
EXPECTED_APK_SHA256 = "cf34c8e640ee785cf34d1b75d55b5610b01357fda9315c2f380d7a6923260ee8"
EXPECTED_LIBRARY_SHA256 = "3b762fd52a641be52014f0a391798c1263198e4d4fcba63f10ffbf3fd2c2ec6b"
EXPECTED_BIRZZLE_SHA256 = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"
EXPECTED_SEED_SHA256 = "654d78172046d1c95488447a133c827edfd01e09313d2298c3670d29d5ae088c"
MTIME_HOOK_OFFSET = 0x121BE4
V26_MTIME_HOOK = bytes.fromhex("42f193b9")
V25_MTIME_HOOK = bytes.fromhex("5af17ab9")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
if sha256(SOURCE_APK) != EXPECTED_APK_SHA256:
    raise SystemExit("unexpected V26 APK SHA-256")
if sha256(SOURCE_LIBRARY) != EXPECTED_LIBRARY_SHA256:
    raise SystemExit("unexpected V26 libef2d SHA-256")

library = bytearray(SOURCE_LIBRARY.read_bytes())
actual = bytes(library[MTIME_HOOK_OFFSET:MTIME_HOOK_OFFSET + 4])
if actual != V26_MTIME_HOOK:
    raise SystemExit(
        f"unexpected V26 mtime hook: {actual.hex()} != {V26_MTIME_HOOK.hex()}"
    )
library[MTIME_HOOK_OFFSET:MTIME_HOOK_OFFSET + 4] = V25_MTIME_HOOK
OUTPUT_LIBRARY.write_bytes(library)

with zipfile.ZipFile(SOURCE_APK, "r") as source:
    temporary = UNSIGNED_APK.with_suffix(".tmp.apk")
    with zipfile.ZipFile(temporary, "w") as output:
        found = False
        for item in source.infolist():
            if item.filename.upper().startswith("META-INF/"):
                continue
            payload = source.read(item.filename)
            if item.filename == "lib/armeabi/libef2d.so":
                payload = bytes(library)
                found = True
            output.writestr(item, payload)
if not found:
    raise SystemExit("V26 APK does not contain lib/armeabi/libef2d.so")
temporary.replace(UNSIGNED_APK)

shutil.copyfile(UNSIGNED_APK, SIGNED_APK)
subprocess.run(
    [
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
    ],
    check=True,
)
subprocess.run(["jarsigner", "-verify", str(SIGNED_APK)], check=True)

with zipfile.ZipFile(SIGNED_APK, "r") as result:
    if result.read("lib/armeabi/libef2d.so") != bytes(library):
        raise SystemExit("signed APK libef2d mismatch")
    if sha256_bytes(result.read("lib/armeabi/libbirzzle.so")) != EXPECTED_BIRZZLE_SHA256:
        raise SystemExit("signed APK libbirzzle mismatch")
    if sha256_bytes(result.read("assets/birzzle_seed_v1.zip")) != EXPECTED_SEED_SHA256:
        raise SystemExit("signed APK seed mismatch")

print(f"libef2d_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
