import hashlib
import zipfile
from pathlib import Path


SOURCE_APK = Path("native-patches/v2-deduplicate-ranking/BirzzleFever-1.1.2-ranking-dedupe.apk")
APKTOOL_BUILD = Path("native-patches/v3-hardcoded-identity/build/BirzzleFever-1.1.2-identity-ranking-unsigned.apk")
OUTPUT_APK = Path("native-patches/v3-hardcoded-identity/BirzzleFever-1.1.2-identity-ranking-unsigned.apk")


with zipfile.ZipFile(APKTOOL_BUILD, "r") as rebuilt:
    patched_dex = rebuilt.read("classes.dex")

temporary = OUTPUT_APK.with_suffix(".tmp.apk")
with zipfile.ZipFile(SOURCE_APK, "r") as source, zipfile.ZipFile(temporary, "w") as output:
    for item in source.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        data = patched_dex if item.filename == "classes.dex" else source.read(item.filename)
        output.writestr(item, data)
temporary.replace(OUTPUT_APK)

with zipfile.ZipFile(OUTPUT_APK, "r") as result:
    native = result.read("lib/armeabi/libbirzzle.so")
    dex = result.read("classes.dex")

print(f"output_apk_sha256={hashlib.sha256(OUTPUT_APK.read_bytes()).hexdigest()}")
print(f"classes_dex_sha256={hashlib.sha256(dex).hexdigest()}")
print(f"libbirzzle_sha256={hashlib.sha256(native).hexdigest()}")
print(f"ranking_patch_bytes={native[0x163baa:0x163bac].hex()}")
