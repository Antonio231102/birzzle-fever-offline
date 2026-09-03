import hashlib
import zipfile
from pathlib import Path


SOURCE_APK = Path(
    "native-patches/v20-request-index-retention/"
    "BirzzleFever-1.1.2-v20-request-index-retention.apk"
)
OUTPUT_DIR = Path("native-patches/v22-first-read-recovery")
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_APK = OUTPUT_DIR / "BirzzleFever-1.1.2-v22-first-read-recovery-unsigned.apk"
UNCLAMPED_LIBRARY = Path(
    "native-patches/v15-portable-no-heart-deduction/libbirzzle.so"
)
HARDENED_LIBRARY = OUTPUT_DIR / "libef2d.so"
EXPECTED_BIRZZLE_SHA256 = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"
EXPECTED_EF2D_SHA256 = "64c083f7d3b614b77f09cdf38259577eccca8fc2276d67e6ba04209116ede0ae"
SEED_ENTRY = "assets/birzzle_seed_v1.zip"
REPLACEMENTS = {
    "lib/armeabi/libbirzzle.so": UNCLAMPED_LIBRARY.read_bytes(),
    "lib/armeabi/libef2d.so": HARDENED_LIBRARY.read_bytes(),
}

if hashlib.sha256(REPLACEMENTS["lib/armeabi/libbirzzle.so"]).hexdigest() != EXPECTED_BIRZZLE_SHA256:
    raise SystemExit("unexpected unclamped libbirzzle SHA-256")
if hashlib.sha256(REPLACEMENTS["lib/armeabi/libef2d.so"]).hexdigest() != EXPECTED_EF2D_SHA256:
    raise SystemExit("unexpected hardened libef2d SHA-256")

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
        if result.read(name) != expected:
            raise SystemExit(f"embedded verification failed for {name}")
    seed = result.read(SEED_ENTRY)
if not seed:
    raise SystemExit("embedded minimal-save seed is missing")

print(f"libbirzzle_sha256={EXPECTED_BIRZZLE_SHA256}")
print(f"libef2d_sha256={EXPECTED_EF2D_SHA256}")
print(f"seed_sha256={hashlib.sha256(seed).hexdigest()}")
print(f"unsigned_apk_sha256={hashlib.sha256(OUTPUT_APK.read_bytes()).hexdigest()}")
