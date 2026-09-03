import hashlib
import shutil
import subprocess
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v22-first-read-recovery/"
    "BirzzleFever-1.1.2-v22-first-read-recovery.apk"
)
SOURCE_LIBRARY = Path("native-patches/v22-first-read-recovery/libef2d.so")
OUTPUT_DIR = Path("native-patches/v23-request-first-index")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_LIBRARY = OUTPUT_DIR / "libef2d.so"
UNSIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v23-request-first-index-unsigned.apk"
SIGNED_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v23-request-first-index.apk"
KEYSTORE = Path("xposed-birzzle-id-spoof/build/debug.keystore")
EXPECTED_SOURCE_SHA256 = "64c083f7d3b614b77f09cdf38259577eccca8fc2276d67e6ba04209116ede0ae"
PATCHES = {
    # SetRequest originally commits the atomic index before its numbered record.
    # Swap the data/path register pairs so the numbered record is durable first.
    0x131FEC: (bytes.fromhex("4946"), bytes.fromhex("391c")),  # r9 path -> r7 path
    0x131FF8: (bytes.fromhex("4146"), bytes.fromhex("211c")),  # r8 data -> r4 data
    0x132020: (bytes.fromhex("391c"), bytes.fromhex("4946")),  # r7 path -> r9 path
    0x13202A: (bytes.fromhex("211c"), bytes.fromhex("4146")),  # r4 data -> r8 data
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sha256(SOURCE_LIBRARY) != EXPECTED_SOURCE_SHA256:
    raise SystemExit("unexpected v22 libef2d SHA-256")

library = bytearray(SOURCE_LIBRARY.read_bytes())
for offset, (expected, replacement) in PATCHES.items():
    actual = bytes(library[offset:offset + len(expected)])
    if actual != expected:
        raise SystemExit(
            f"unexpected bytes at {offset:#x}: {actual.hex()} != {expected.hex()}"
        )
    library[offset:offset + len(replacement)] = replacement
OUTPUT_LIBRARY.write_bytes(library)

with zipfile.ZipFile(SOURCE_APK, "r") as source, zipfile.ZipFile(UNSIGNED_APK, "w") as output:
    for item in source.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        payload = (
            library if item.filename == "lib/armeabi/libef2d.so"
            else source.read(item.filename)
        )
        output.writestr(item, payload)

shutil.copyfile(UNSIGNED_APK, SIGNED_APK)
subprocess.run(
    [
        "jarsigner", "-keystore", str(KEYSTORE), "-storepass", "android",
        "-keypass", "android", "-sigalg", "SHA256withRSA",
        "-digestalg", "SHA-256", str(SIGNED_APK), "androiddebugkey",
    ],
    check=True,
)
subprocess.run(["jarsigner", "-verify", str(SIGNED_APK)], check=True)
with zipfile.ZipFile(SIGNED_APK, "r") as result:
    if result.read("lib/armeabi/libef2d.so") != library:
        raise SystemExit("signed APK library mismatch")

print(f"source_libef2d_sha256={EXPECTED_SOURCE_SHA256}")
print(f"libef2d_sha256={sha256(OUTPUT_LIBRARY)}")
print(f"unsigned_apk_sha256={sha256(UNSIGNED_APK)}")
print(f"signed_apk_sha256={sha256(SIGNED_APK)}")
