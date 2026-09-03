import gzip
import hashlib
import shutil
import zipfile
from pathlib import Path


LIBRARY_ENTRY = "lib/armeabi/libbirzzle.so"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("apk_gz", type=Path)
    parser.add_argument("patched_library", type=Path)
    parser.add_argument("unsigned_apk", type=Path)
    args = parser.parse_args()
    apk_gz = args.apk_gz
    patched_library_path = args.patched_library
    unsigned_apk = args.unsigned_apk
    build_dir = unsigned_apk.parent
    build_dir.mkdir(parents=True, exist_ok=True)
    original_apk = build_dir / "BirzzleFever-1.1.2-original.apk"
    with gzip.open(apk_gz, "rb") as source, original_apk.open("wb") as destination:
        shutil.copyfileobj(source, destination)

    patched_library = patched_library_path.read_bytes()
    temporary = unsigned_apk.with_suffix(".tmp.apk")
    with zipfile.ZipFile(original_apk, "r") as source, zipfile.ZipFile(temporary, "w") as destination:
        found = False
        for item in source.infolist():
            upper_name = item.filename.upper()
            if upper_name.startswith("META-INF/"):
                continue
            data = source.read(item.filename)
            if item.filename == LIBRARY_ENTRY:
                data = patched_library
                found = True
            destination.writestr(item, data)
        if not found:
            raise SystemExit(f"missing APK entry: {LIBRARY_ENTRY}")
    temporary.replace(unsigned_apk)

    with zipfile.ZipFile(unsigned_apk, "r") as result:
        embedded_hash = hashlib.sha256(result.read(LIBRARY_ENTRY)).hexdigest()
    if embedded_hash != digest(patched_library_path):
        raise SystemExit("embedded native library does not match the patched input")

    print(f"original APK: {original_apk} ({digest(original_apk)})")
    print(f"unsigned APK: {unsigned_apk} ({digest(unsigned_apk)})")
    print(f"embedded {LIBRARY_ENTRY}: {embedded_hash}")


if __name__ == "__main__":
    main()
