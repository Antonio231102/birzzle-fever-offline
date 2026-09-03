import hashlib
import struct
import zipfile
from pathlib import Path


SOURCE_LIBRARY = Path("native-patches/v17-defensive-state-guards/libbirzzle.so")
SOURCE_APK = Path(
    "native-patches/v17-defensive-state-guards/"
    "BirzzleFever-1.1.2-v17-defensive-state-guards.apk"
)
STUB_PATH = Path(
    "native-patches/v17-defensive-state-guards/"
    "test_economy_grant_990k_99900.bin"
)
OUTPUT_DIR = Path("native-patches/v17-test-economy-grant-990k-99900")
OUTPUT_LIBRARY = OUTPUT_DIR / "libbirzzle.so"
OUTPUT_APK = OUTPUT_DIR / (
    "BirzzleFever-1.1.2-v17-test-economy-grant-990k-99900-unsigned.apk"
)
EXPECTED_LIBRARY_SHA256 = "fdf036916d8ddbe7ccbd4ad3dad53b6e294ee41fbc960cb9a1a1a86ff59bd258"
EXPECTED_STUB_SHA256 = "5a8d076e29cf6311990df79e70e6efd1b86f19f704b7e019924b29f33c7cca90"
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


source = SOURCE_LIBRARY.read_bytes()
if hashlib.sha256(source).hexdigest() != EXPECTED_LIBRARY_SHA256:
    raise SystemExit("unexpected public v17 library SHA-256")
stub = STUB_PATH.read_bytes()
if hashlib.sha256(stub).hexdigest() != EXPECTED_STUB_SHA256:
    raise SystemExit("unexpected economy stub SHA-256")

library = bytearray(source)
replace(library, 0x148510, bytes.fromhex("43f714f8"), thumb2_branch(0x148510, 0x2ACFD8))
replace(library, 0x148520, bytes.fromhex("43f70cf8"), thumb2_branch(0x148520, 0x2ACFE8))
replace(library, 0x2ACFD8, bytes(len(stub)), stub)

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_LIBRARY.write_bytes(library)
with zipfile.ZipFile(SOURCE_APK, "r") as source_apk, zipfile.ZipFile(OUTPUT_APK, "w") as output:
    for item in source_apk.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        payload = bytes(library) if item.filename == LIBRARY_ENTRY else source_apk.read(item.filename)
        output.writestr(item, payload)
with zipfile.ZipFile(OUTPUT_APK, "r") as result:
    if result.read(LIBRARY_ENTRY) != bytes(library):
        raise SystemExit("embedded test economy library verification failed")

print(f"test_library_sha256={hashlib.sha256(library).hexdigest()}")
print(f"unsigned_apk_sha256={hashlib.sha256(OUTPUT_APK.read_bytes()).hexdigest()}")
