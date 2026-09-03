import hashlib
import struct
import zipfile
from pathlib import Path


SOURCE_LIBRARY = Path("native-patches/v17-defensive-state-guards/libbirzzle.so")
SOURCE_APK = Path(
    "native-patches/v17-defensive-state-guards/"
    "BirzzleFever-1.1.2-v17-defensive-state-guards.apk"
)
EXPECTED_LIBRARY_SHA256 = "fdf036916d8ddbe7ccbd4ad3dad53b6e294ee41fbc960cb9a1a1a86ff59bd258"
GET_INJECTOR = Path("native-patches/v17-defensive-state-guards/get_pocket_fault_injector.bin")
EXPECTED_GET_INJECTOR_SHA256 = "354811af74d240def7fd74d70dd93eb3082ccdd0c69a25f749c9d0c1058478a8"
LIBRARY_ENTRY = "lib/armeabi/libbirzzle.so"


def thumb2_branch(source: int, target: int) -> bytes:
    offset = target - (source + 4)
    if offset & 1 or not -(1 << 24) <= offset < (1 << 24):
        raise ValueError(f"invalid Thumb-2 branch {source:#x} -> {target:#x}")
    value = offset & 0x1FFFFFF
    s = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    j1 = (~(i1 ^ s)) & 1
    j2 = (~(i2 ^ s)) & 1
    first = 0xF000 | (s << 10) | ((value >> 12) & 0x3FF)
    second = 0x9000 | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


def replace(data: bytearray, offset: int, expected: bytes, replacement: bytes) -> None:
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise SystemExit(
            f"unexpected bytes at {offset:#x}: {actual.hex()} != {expected.hex()}"
        )
    if len(expected) != len(replacement):
        raise SystemExit(f"length mismatch at {offset:#x}")
    data[offset : offset + len(replacement)] = replacement


def package_variant(name: str, library: bytes) -> None:
    output_dir = Path(f"native-patches/{name}")
    output_dir.mkdir(parents=True, exist_ok=True)
    lib_path = output_dir / "libbirzzle.so"
    apk_path = output_dir / f"BirzzleFever-1.1.2-{name}-unsigned.apk"
    lib_path.write_bytes(library)
    with zipfile.ZipFile(SOURCE_APK, "r") as source, zipfile.ZipFile(apk_path, "w") as output:
        for item in source.infolist():
            if item.filename.upper().startswith("META-INF/"):
                continue
            payload = library if item.filename == LIBRARY_ENTRY else source.read(item.filename)
            output.writestr(item, payload)
    with zipfile.ZipFile(apk_path, "r") as result:
        if result.read(LIBRARY_ENTRY) != library:
            raise SystemExit(f"{name}: embedded library verification failed")
    print(f"{name}_lib_sha256={hashlib.sha256(library).hexdigest()}")
    print(f"{name}_unsigned_apk_sha256={hashlib.sha256(apk_path.read_bytes()).hexdigest()}")


source = SOURCE_LIBRARY.read_bytes()
source_hash = hashlib.sha256(source).hexdigest()
if source_hash != EXPECTED_LIBRARY_SHA256:
    raise SystemExit(f"unexpected v17 library SHA-256: {source_hash}")


get_injector = GET_INJECTOR.read_bytes()
if hashlib.sha256(get_injector).hexdigest() != EXPECTED_GET_INJECTOR_SHA256:
    raise SystemExit("unexpected GET pocket fault injector SHA-256")

pocket = bytearray(source)
replace(pocket, 0x16F51E, thumb2_branch(0x16F51E, 0x2ACEE8), thumb2_branch(0x16F51E, 0x2ACFE0))
replace(pocket, 0x2ACFE0, bytes(len(get_injector)), get_injector)
package_variant("v17-test-pocket-regression", bytes(pocket))

inventory = bytearray(source)
replace(inventory, 0x2ACF9A, bytes.fromhex("62f60bfa"), bytes.fromhex("012000bf"))
replace(inventory, 0x2ACFAA, bytes.fromhex("0138"), bytes.fromhex("0020"))
package_variant("v17-test-inventory-truncation", bytes(inventory))
