import hashlib
import struct
import zipfile
from pathlib import Path


PUBLIC_APK = Path(
    "native-patches/v20-request-index-retention/"
    "BirzzleFever-1.1.2-v20-request-index-retention.apk"
)
PUBLIC_LIBRARY = Path("native-patches/v20-request-index-retention/libef2d.so")
FAULT_WRAPPER = Path(
    "native-patches/v20-request-index-retention/force_retry_after_capture.bin"
)
TEST_LIBRARY = Path("native-patches/v20-request-index-retention/libef2d-forced-empty-set-test.so")
UNSIGNED_APK = Path(
    "native-patches/v20-request-index-retention/"
    "BirzzleFever-1.1.2-v20-forced-empty-set-test-unsigned.apk"
)
ENTRY = "lib/armeabi/libef2d.so"


def thumb2_branch(source: int, target: int) -> bytes:
    offset = target - (source + 4)
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
    if bytes(data[offset : offset + len(expected)]) != expected:
        raise SystemExit(f"unexpected test patch anchor at {offset:#x}")
    if len(expected) != len(replacement):
        raise SystemExit("test patch length mismatch")
    data[offset : offset + len(replacement)] = replacement


data = bytearray(PUBLIC_LIBRARY.read_bytes())
wrapper = FAULT_WRAPPER.read_bytes()
wrapper_address = 0x27BE34
replace(data, wrapper_address, bytes(len(wrapper)), wrapper)
replace(data, 0x131E52, thumb2_branch(0x131E52, 0x27BDD4), thumb2_branch(0x131E52, wrapper_address))
replace(data, 52 + 32 + 16, struct.pack("<I", 0x27BE32), struct.pack("<I", wrapper_address + len(wrapper)))
replace(data, 52 + 32 + 20, struct.pack("<I", 0x27BE32), struct.pack("<I", wrapper_address + len(wrapper)))
TEST_LIBRARY.write_bytes(data)

with zipfile.ZipFile(PUBLIC_APK, "r") as source, zipfile.ZipFile(UNSIGNED_APK, "w") as output:
    for item in source.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        payload = data if item.filename == ENTRY else source.read(item.filename)
        output.writestr(item, payload)

with zipfile.ZipFile(UNSIGNED_APK, "r") as result:
    if result.read(ENTRY) != data:
        raise SystemExit("test library embedding failed")
print(f"test_libef2d_sha256={hashlib.sha256(data).hexdigest()}")
print(f"test_unsigned_apk_sha256={hashlib.sha256(UNSIGNED_APK.read_bytes()).hexdigest()}")
