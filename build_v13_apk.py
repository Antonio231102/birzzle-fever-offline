import hashlib
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v12-powerup-dispatch-rearm/"
    "BirzzleFever-1.1.2-v12-powerup-dispatch-rearm.apk"
)
PATCHED_LIBRARY = Path("native-patches/v13-powerup-pending-generation/libbirzzle.so")
OUTPUT_APK = Path(
    "native-patches/v13-powerup-pending-generation/"
    "BirzzleFever-1.1.2-v13-powerup-pending-generation-unsigned.apk"
)
LIBRARY_ENTRY = "lib/armeabi/libbirzzle.so"

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
if embedded != library:
    raise SystemExit("embedded library verification failed")

print(f"unsigned_apk_sha256={hashlib.sha256(OUTPUT_APK.read_bytes()).hexdigest()}")
print(f"libbirzzle_sha256={hashlib.sha256(embedded).hexdigest()}")
