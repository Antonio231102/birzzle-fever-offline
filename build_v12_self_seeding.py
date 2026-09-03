import hashlib
import subprocess
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
PROJECT = ROOT / "native-patches/v12-self-seeding/apktool"
SEED_ROOT = (
    ROOT
    / "analysis-backup-compare/trial-12-original-plus-two-compat/data/data/"
    / "com.halfbrick.birzzlefever"
)
SEED_ASSET = PROJECT / "assets/birzzle_seed_v1.zip"
UNSIGNED = (
    ROOT
    / "native-patches/v12-self-seeding/"
    / "BirzzleFever-1.1.2-v12-self-seeding-unsigned.apk"
)


def build_seed() -> None:
    SEED_ASSET.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(SEED_ASSET, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(SEED_ROOT.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(SEED_ROOT).as_posix())

    with zipfile.ZipFile(SEED_ASSET) as archive:
        names = set(archive.namelist())
        required = {
            "files/09d531fd0dc2a818e49efec1d5548a78",
            "files/f0328e1664de484d932bca2ec0e59295",
            "files/profile",
        }
        missing = required - names
        if missing:
            raise SystemExit(f"seed verification failed; missing: {sorted(missing)}")
        print(f"seed_entries={len(names)}")
        print(f"seed_uncompressed_bytes={sum(info.file_size for info in archive.infolist())}")


def main() -> None:
    build_seed()
    if UNSIGNED.exists():
        UNSIGNED.unlink()
    subprocess.run(
        [
            "java",
            "-jar",
            str(ROOT / "tools/apktool_2.12.1.jar"),
            "b",
            str(PROJECT),
            "-o",
            str(UNSIGNED),
        ],
        check=True,
    )
    cleaned = UNSIGNED.with_suffix(".clean.apk")
    with zipfile.ZipFile(UNSIGNED, "r") as source, zipfile.ZipFile(cleaned, "w") as output:
        for item in source.infolist():
            if item.filename.upper().startswith("META-INF/"):
                continue
            output.writestr(item, source.read(item.filename))
    cleaned.replace(UNSIGNED)
    print(f"seed_sha256={hashlib.sha256(SEED_ASSET.read_bytes()).hexdigest()}")
    print(f"unsigned_apk_sha256={hashlib.sha256(UNSIGNED.read_bytes()).hexdigest()}")


if __name__ == "__main__":
    main()
