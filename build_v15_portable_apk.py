import hashlib
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v12-self-seeding/"
    "BirzzleFever-1.1.2-v12-self-seeding.apk"
)
PATCHED_LIBRARY = Path("native-patches/v15-portable-no-heart-deduction/libbirzzle.so")
OUTPUT_APK = Path(
    "native-patches/v15-portable-no-heart-deduction/"
    "BirzzleFever-1.1.2-v15-portable-no-heart-deduction-unsigned.apk"
)
LIBRARY_ENTRY = "lib/armeabi/libbirzzle.so"
SEED_ENTRY = "assets/birzzle_seed_v1.zip"

library = PATCHED_LIBRARY.read_bytes()
temporary = OUTPUT_APK.with_suffix(".tmp.apk")
with zipfile.ZipFile(SOURCE_APK, "r") as source, zipfile.ZipFile(temporary, "w") as output:
    for item in source.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        payload = library if item.filename == LIBRARY_ENTRY else source.read(item.filename)
        output.writestr(item, payload)
temporary.replace(OUTPUT_APK)

with zipfile.ZipFile(OUTPUT_APK, "r") as result:
    embedded = result.read(LIBRARY_ENTRY)
    seed = result.read(SEED_ENTRY)
if embedded != library:
    raise SystemExit("embedded library verification failed")
if not seed:
    raise SystemExit("embedded save asset is missing")

print(f"unsigned_apk_sha256={hashlib.sha256(OUTPUT_APK.read_bytes()).hexdigest()}")
print(f"libbirzzle_sha256={hashlib.sha256(embedded).hexdigest()}")
print(f"seed_sha256={hashlib.sha256(seed).hexdigest()}")
