import hashlib
import struct
import zipfile
from pathlib import Path


ROOT = Path("native-patches/v20-request-index-retention")
SOURCE_LIBRARY = ROOT / "libef2d.so"
SOURCE_APK = ROOT / "BirzzleFever-1.1.2-v20-request-index-retention.apk"
STUB = ROOT / "profile_key_diagnostic.bin"
OUTPUT_DIR = ROOT / "profile-diagnostic"
OUTPUT_DIR.mkdir(exist_ok=True)
OUTPUT_LIBRARY = OUTPUT_DIR / "libef2d.so"
OUTPUT_UNSIGNED = OUTPUT_DIR / "BirzzleFever-1.1.2-v20-profile-diagnostic-unsigned.apk"
EXPECTED_SOURCE_SHA256 = "291247fa42e11070ad30b4c6c0f4554535ba24d1252b88b635929343c29c21e2"


def thumb2_branch(source: int, target: int) -> bytes:
    offset = target - (source + 4)
    value = offset & 0x1FFFFFF
    s = (value >> 24) & 1
    i1 = (value >> 23) & 1
    i2 = (value >> 22) & 1
    j1 = (~(i1 ^ s)) & 1
    j2 = (~(i2 ^ s)) & 1
    return struct.pack(
        "<HH",
        0xF000 | (s << 10) | ((value >> 12) & 0x3FF),
        0x9000 | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF),
    )


def replace(data: bytearray, offset: int, expected: bytes, replacement: bytes) -> None:
    if data[offset : offset + len(expected)] != expected:
        raise SystemExit(f"unexpected patch anchor at {offset:#x}")
    if len(expected) != len(replacement):
        raise SystemExit("replacement length mismatch")
    data[offset : offset + len(replacement)] = replacement


data = bytearray(SOURCE_LIBRARY.read_bytes())
if hashlib.sha256(data).hexdigest() != EXPECTED_SOURCE_SHA256:
    raise SystemExit("unexpected production libef2d SHA-256")
stub = STUB.read_bytes()
stub_address = 0x27BE34
stub_end = stub_address + len(stub)
replace(data, stub_address, bytes(len(stub)), stub)
replace(data, 0x98538, bytes.fromhex("30b50c1c"), thumb2_branch(0x98538, stub_address))
replace(data, 52 + 32 + 16, struct.pack("<I", 0x27BE32), struct.pack("<I", stub_end))
replace(data, 52 + 32 + 20, struct.pack("<I", 0x27BE32), struct.pack("<I", stub_end))
OUTPUT_LIBRARY.write_bytes(data)

with zipfile.ZipFile(SOURCE_APK) as source, zipfile.ZipFile(OUTPUT_UNSIGNED, "w") as output:
    for item in source.infolist():
        if item.filename.upper().startswith("META-INF/"):
            continue
        payload = data if item.filename == "lib/armeabi/libef2d.so" else source.read(item.filename)
        output.writestr(item, payload)

print(f"stub_size={len(stub)}")
print(f"stub_end={stub_end:#x}")
print(f"libef2d_sha256={hashlib.sha256(data).hexdigest()}")
print(f"unsigned_apk_sha256={hashlib.sha256(OUTPUT_UNSIGNED.read_bytes()).hexdigest()}")
