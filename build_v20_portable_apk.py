import hashlib
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v19-authoritative-gem-guard/"
    "BirzzleFever-1.1.2-v19-authoritative-gem-guard.apk"
)
OUTPUT_APK = Path(
    "native-patches/v20-request-index-retention/"
    "BirzzleFever-1.1.2-v20-request-index-retention-unsigned.apk"
)
REPLACEMENTS = {
    "lib/armeabi/libbirzzle.so": Path(
        "native-patches/v20-request-index-retention/libbirzzle.so"
    ).read_bytes(),
    "lib/armeabi/libef2d.so": Path(
        "native-patches/v20-request-index-retention/libef2d.so"
    ).read_bytes(),
}
SEED_ENTRY = "assets/birzzle_seed_v1.zip"


temporary = OUTPUT_APK.with_suffix(".tmp.apk")
with zipfile.ZipFile(SOURCE_APK, "r") as source, zipfile.ZipFile(temporary, "w") as output:
    seen = set()
    for item in source.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        payload = REPLACEMENTS.get(item.filename)
        if payload is None:
            payload = source.read(item.filename)
        else:
            seen.add(item.filename)
        output.writestr(item, payload)
if seen != set(REPLACEMENTS):
    raise SystemExit(f"missing APK entries: {set(REPLACEMENTS) - seen}")
temporary.replace(OUTPUT_APK)

with zipfile.ZipFile(OUTPUT_APK, "r") as result:
    for name, expected in REPLACEMENTS.items():
        embedded = result.read(name)
        if embedded != expected:
            raise SystemExit(f"embedded verification failed for {name}")
        print(f"{name}_sha256={hashlib.sha256(embedded).hexdigest()}")
    seed = result.read(SEED_ENTRY)
if not seed:
    raise SystemExit("embedded save asset is missing")

print(f"unsigned_apk_sha256={hashlib.sha256(OUTPUT_APK.read_bytes()).hexdigest()}")
print(f"seed_sha256={hashlib.sha256(seed).hexdigest()}")
