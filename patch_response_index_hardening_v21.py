import hashlib
import struct
from pathlib import Path

from elftools.elf.elffile import ELFFile


SOURCE = Path("native-patches/v20-request-index-retention/libef2d-source.so")
STUB = Path("native-patches/v21-response-index-hardening/v21_hardening.bin")
STUB_ELF = Path("native-patches/v21-response-index-hardening/v21_hardening.elf")
OUTPUT = Path("native-patches/v21-response-index-hardening/libef2d.so")
EXPECTED_SOURCE_SHA256 = "cfd0c07ee435afcf07d827acd2ae5d3774bc4e6cc0a24a4e4e96e3663eb9d91b"
EXPECTED_STUB_SHA256 = "d8ac38efe8b86a2da76ed9260c4cfef3c14f56c88f6dc0948a53e25168a80ec3"
STUB_OFFSET = 0x27BC50
RW_OFFSET = 0x27C000


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


def stub_symbols():
    with STUB_ELF.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        return {
            symbol.name: symbol["st_value"] & ~1
            for symbol in table.iter_symbols()
            if symbol.name
        }


data = bytearray(SOURCE.read_bytes())
source_hash = hashlib.sha256(data).hexdigest()
if source_hash != EXPECTED_SOURCE_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {source_hash}")

stub = STUB.read_bytes()
stub_hash = hashlib.sha256(stub).hexdigest()
if stub_hash != EXPECTED_STUB_SHA256:
    raise SystemExit(f"unexpected stub SHA-256: {stub_hash}")
if STUB_OFFSET + len(stub) > RW_OFFSET:
    raise SystemExit(f"stub overlaps RW segment: end={STUB_OFFSET + len(stub):#x}")

symbols = stub_symbols()
required_symbols = {
    "suite_retry_guard",
    "suite_capture_guard",
    "all_retry_guard",
    "all_capture_guard",
    "set_retry_guard",
    "set_highwater_update",
    "mtime_guard",
    "write_dispatch",
}
if not required_symbols <= symbols.keys():
    raise SystemExit(f"missing stub symbols: {sorted(required_symbols - symbols.keys())}")

nop = bytes.fromhex("00bf")
replace(
    data,
    0x13107A,
    bytes.fromhex("00d140e1"),
    thumb2_branch(0x13107A, symbols["suite_retry_guard"]),
    "GetRequestSuite mature retry guard",
)
replace(
    data,
    0x1310BE,
    bytes.fromhex("059b0d98"),
    thumb2_branch(0x1310BE, symbols["suite_capture_guard"]),
    "GetRequestSuite high-water capture",
)
replace(
    data,
    0x1315A2,
    bytes.fromhex("00d1d5e1"),
    thumb2_branch(0x1315A2, symbols["all_retry_guard"]),
    "GetRequestAll mature retry guard",
)
replace(
    data,
    0x1315E4,
    bytes.fromhex("08990023"),
    thumb2_branch(0x1315E4, symbols["all_capture_guard"]),
    "GetRequestAll high-water capture",
)
replace(
    data,
    0x131E52,
    bytes.fromhex("9a4200d155e1"),
    thumb2_branch(0x131E52, symbols["set_retry_guard"]) + nop,
    "SetRequest mature retry guard",
)
replace(
    data,
    0x131E94,
    bytes.fromhex("631cda43"),
    thumb2_branch(0x131E94, symbols["set_highwater_update"]),
    "SetRequest high-water update",
)
replace(
    data,
    0x121BE4,
    bytes.fromhex("0a2800dc"),
    thumb2_branch(0x121BE4, symbols["mtime_guard"]),
    "ReadContent index-only mtime guard",
)
replace(
    data,
    0x1213BE,
    bytes.fromhex("54495046"),
    thumb2_branch(0x1213BE, symbols["write_dispatch"]),
    "WriteContent atomic index dispatcher",
)
replace(data, STUB_OFFSET, bytes(len(stub)), stub, "v21 executable hardening stub")

stub_end = STUB_OFFSET + len(stub)
replace_u32(data, 52 + 32 + 16, 0x27BC4C, stub_end, "RX PT_LOAD file size")
replace_u32(data, 52 + 32 + 20, 0x27BC4C, stub_end, "RX PT_LOAD memory size")

# Reserve one process-local uint32 immediately after the original BSS.
replace_u32(data, 52 + 2 * 32 + 20, 0x18624, 0x18628, "RW PT_LOAD memory size")
section_headers = 0x293580
section_size = 40
bss_size_offset = section_headers + 17 * section_size + 20
replace_u32(data, bss_size_offset, 0x4084, 0x4088, "BSS size")

OUTPUT.write_bytes(data)
print(f"source_sha256={source_hash}")
print(f"stub_sha256={stub_hash}")
print(f"stub_size={len(stub)}")
print(f"stub_end={stub_end:#x}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
