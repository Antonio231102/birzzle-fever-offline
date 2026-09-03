import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v20-request-index-retention/libef2d-source.so")
OUTPUT = Path("native-patches/v20-request-index-retention/libef2d.so")
STUB_PATH = Path("native-patches/v20-request-index-retention/index_retention.bin")
EXPECTED_SOURCE_SHA256 = "cfd0c07ee435afcf07d827acd2ae5d3774bc4e6cc0a24a4e4e96e3663eb9d91b"
EXPECTED_STUB_SHA256 = "6e082eded07fb907a552426e646e9eecd4aee879bc40db52231904ab3035ede3"
RETRY_PATH = Path("native-patches/v20-request-index-retention/index_retry.bin")
EXPECTED_RETRY_SHA256 = "8d86afb0377735e847a51d0a67bdce0adda9e3f2fe3503673285a73d3eae5892"


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


def replace(data: bytearray, offset: int, expected: bytes, replacement: bytes, label: str) -> None:
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise SystemExit(
            f"unexpected bytes for {label} at {offset:#x}: "
            f"{actual.hex()} != {expected.hex()}"
        )
    if len(expected) != len(replacement):
        raise SystemExit(f"length mismatch for {label}")
    data[offset : offset + len(replacement)] = replacement
    print(f"{label}: {offset:#x} {expected.hex()} -> {replacement.hex()}")


def replace_u32(data: bytearray, offset: int, expected: int, replacement: int, label: str) -> None:
    replace(data, offset, struct.pack("<I", expected), struct.pack("<I", replacement), label)


data = bytearray(SOURCE.read_bytes())
source_hash = hashlib.sha256(data).hexdigest()
if source_hash != EXPECTED_SOURCE_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {source_hash}")
stub = STUB_PATH.read_bytes()
if hashlib.sha256(stub).hexdigest() != EXPECTED_STUB_SHA256:
    raise SystemExit("unexpected request-index stub SHA-256")
retry = RETRY_PATH.read_bytes()
if hashlib.sha256(retry).hexdigest() != EXPECTED_RETRY_SHA256:
    raise SystemExit("unexpected request-index retry SHA-256")

nop = bytes.fromhex("00bf")
replace(data, 0x13107A, bytes.fromhex("00d140e1"), thumb2_branch(0x13107A, 0x27BD18), "GetRequestSuite retry on empty index")
replace(data, 0x1310BE, bytes.fromhex("059b0d98"), thumb2_branch(0x1310BE, 0x27BC8A), "GetRequestSuite high-water capture")
replace(data, 0x1315A2, bytes.fromhex("00d1d5e1"), thumb2_branch(0x1315A2, 0x27BD76), "GetRequestAll retry on empty index")
replace(data, 0x131E52, bytes.fromhex("9a4200d155e1"), thumb2_branch(0x131E52, 0x27BDD4) + nop, "SetRequest retry on empty index")
replace(data, 0x1315E4, bytes.fromhex("08990023"), thumb2_branch(0x1315E4, 0x27BCC8), "GetRequestAll high-water capture")
replace(data, 0x131E94, bytes.fromhex("631cda43"), thumb2_branch(0x131E94, 0x27BD04), "SetRequest high-water update")
replace(data, 0x27BC50, bytes(len(stub)), stub, "executable retention stubs")
replace(data, 0x27BD18, bytes(len(retry)), retry, "executable retry hooks")

# Extend the executable PT_LOAD through the new stubs.
replace_u32(data, 52 + 32 + 16, 0x27BC4C, 0x27BE32, "RX PT_LOAD file size")
replace_u32(data, 52 + 32 + 20, 0x27BC4C, 0x27BE32, "RX PT_LOAD memory size")

# Reserve one zero-initialized uint32 immediately after the original BSS.
replace_u32(data, 52 + 2 * 32 + 20, 0x18624, 0x18628, "RW PT_LOAD memory size")
section_headers = 0x293580
section_size = 40
bss_size_offset = section_headers + 17 * section_size + 20
replace_u32(data, bss_size_offset, 0x4084, 0x4088, "BSS size")

OUTPUT.write_bytes(data)
print(f"source_sha256={source_hash}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
