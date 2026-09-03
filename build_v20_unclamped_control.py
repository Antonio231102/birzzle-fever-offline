import hashlib
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v20-request-index-retention/"
    "BirzzleFever-1.1.2-v20-request-index-retention.apk"
)
UNCLAMPED_LIBRARY = Path(
    "native-patches/v15-portable-no-heart-deduction/libbirzzle.so"
)
OUTPUT_DIR = Path("native-patches/v20-request-index-retention/unclamped-control")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v20-unclamped-control-unsigned.apk"
ENTRY = "lib/armeabi/libbirzzle.so"
EXPECTED_LIBRARY_SHA256 = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"


library = UNCLAMPED_LIBRARY.read_bytes()
actual_hash = hashlib.sha256(library).hexdigest()
if actual_hash != EXPECTED_LIBRARY_SHA256:
    raise SystemExit(f"unexpected unclamped library SHA-256: {actual_hash}")

temporary = OUTPUT_APK.with_suffix(".tmp.apk")
with zipfile.ZipFile(SOURCE_APK, "r") as source, zipfile.ZipFile(temporary, "w") as output:
    found = False
    for item in source.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        payload = library if item.filename == ENTRY else source.read(item.filename)
        found |= item.filename == ENTRY
        output.writestr(item, payload)
if not found:
    raise SystemExit(f"missing APK entry: {ENTRY}")
temporary.replace(OUTPUT_APK)

with zipfile.ZipFile(OUTPUT_APK, "r") as result:
    if result.read(ENTRY) != library:
        raise SystemExit("unclamped library embedding failed")
    ef2d_hash = hashlib.sha256(result.read("lib/armeabi/libef2d.so")).hexdigest()

print(f"libbirzzle_sha256={actual_hash}")
print(f"libef2d_sha256={ef2d_hash}")
print(f"unsigned_apk_sha256={hashlib.sha256(OUTPUT_APK.read_bytes()).hexdigest()}")
