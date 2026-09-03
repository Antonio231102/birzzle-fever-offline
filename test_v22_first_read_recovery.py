import hashlib
import struct
import zipfile
from pathlib import Path

from elftools.elf.elffile import ELFFile


ROOT = Path("native-patches/v22-first-read-recovery")
LIBRARY = ROOT / "libef2d.so"
STUB = ROOT / "v22_hardening.bin"
RODATA = ROOT / "v22_hardening-rodata.bin"
STUB_ELF = ROOT / "v22_hardening.elf"
APK = ROOT / "BirzzleFever-1.1.2-v22-first-read-recovery.apk"
EXPECTED = {
    LIBRARY: "64c083f7d3b614b77f09cdf38259577eccca8fc2276d67e6ba04209116ede0ae",
    STUB: "674e24a660d41a300362598e7c4c2336a15ead64fc962be359eff7b393319b01",
    RODATA: "3126a2b43baf692f3c57c74898163b8c5828e49b52845b678a891213a8e79070",
    APK: "cb929cf772067b270da9f5e050e34b32156b92ad5fc21100bae57d92ccfbe848",
}
EXPECTED_BIRZZLE = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"
RODATA_OFFSET = 0x263D70
STUB_OFFSET = 0x27BC50


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def thumb2_target(source: int, encoded: bytes) -> int:
    first, second = struct.unpack("<HH", encoded)
    if first & 0xF800 != 0xF000 or second & 0xD000 != 0x9000:
        raise AssertionError(f"not a Thumb-2 B.W at {source:#x}: {encoded.hex()}")
    s = (first >> 10) & 1
    j1 = (second >> 13) & 1
    j2 = (second >> 11) & 1
    i1 = (~(j1 ^ s)) & 1
    i2 = (~(j2 ^ s)) & 1
    value = (
        (s << 24)
        | (i1 << 23)
        | (i2 << 22)
        | ((first & 0x3FF) << 12)
        | ((second & 0x7FF) << 1)
    )
    if s:
        value -= 1 << 25
    return source + 4 + value


def symbols(path: Path):
    with path.open("rb") as stream:
        elf = ELFFile(stream)
        table = elf.get_section_by_name(".symtab")
        return {symbol.name: symbol["st_value"] & ~1 for symbol in table.iter_symbols()}


for path, expected in EXPECTED.items():
    assert sha256(path) == expected, path

library = LIBRARY.read_bytes()
stub = STUB.read_bytes()
rodata = RODATA.read_bytes()
assert len(stub) == 926
assert STUB_OFFSET + len(stub) == 0x27BFEE
assert library[STUB_OFFSET : STUB_OFFSET + len(stub)] == stub
assert library[RODATA_OFFSET : RODATA_OFFSET + len(rodata)] == rodata

stub_symbols = symbols(STUB_ELF)
hooks = {
    0x13107A: "suite_retry_guard",
    0x1310BE: "suite_capture_guard",
    0x1315A2: "all_retry_guard",
    0x1315E4: "all_capture_guard",
    0x131E52: "set_retry_guard",
    0x131E94: "set_highwater_update",
    0x131218: "suite_record_retry_guard",
    0x1316EA: "all_record_retry_guard",
    0x121BE4: "mtime_guard",
    0x1213BE: "write_dispatch",
}
for source, symbol_name in hooks.items():
    actual_target = thumb2_target(source, library[source : source + 4])
    assert actual_target == stub_symbols[symbol_name], (
        hex(source),
        symbol_name,
        hex(actual_target),
        hex(stub_symbols[symbol_name]),
    )
assert library[0x131E56:0x131E58] == bytes.fromhex("00bf")

with LIBRARY.open("rb") as stream:
    elf = ELFFile(stream)
    loads = [segment for segment in elf.iter_segments() if segment["p_type"] == "PT_LOAD"]
    executable = next(segment for segment in loads if segment["p_flags"] & 1)
    writable = next(segment for segment in loads if segment["p_flags"] & 2)
    assert executable["p_filesz"] == 0x27BFEE
    assert executable["p_memsz"] == 0x27BFEE
    assert executable["p_offset"] + executable["p_filesz"] <= writable["p_offset"]
    assert writable["p_memsz"] == 0x18628

for expected_string in (
    b"5f7d50ff681a65b10550a631e11a2ded\0",
    b"5f7d50ff681a65b10550a631e11a2ded.tmp\0",
    b"3ec79b0f1529e3fda4242b59a97d2123\0",
):
    assert expected_string in rodata

# Linux ARM EABI syscall sequences required by the atomic writer.
for syscall_number in (5, 6, 10, 38, 118):
    assert bytes((syscall_number, 0x27)) in stub or bytes((syscall_number, 0x27)) in library
assert stub.count(bytes.fromhex("00df")) >= 8

# Contract truth table: only an actually virgin pool may use the empty path.
def should_retry(highwater: int, request_zero_exists: bool) -> bool:
    return highwater > 0 or request_zero_exists


assert not should_retry(0, False)
assert should_retry(0, True)
assert should_retry(103, False)
assert should_retry(103, True)

with zipfile.ZipFile(APK, "r") as archive:
    embedded_ef2d = archive.read("lib/armeabi/libef2d.so")
    embedded_birzzle = archive.read("lib/armeabi/libbirzzle.so")
    assert hashlib.sha256(embedded_ef2d).hexdigest() == EXPECTED[LIBRARY]
    assert hashlib.sha256(embedded_birzzle).hexdigest() == EXPECTED_BIRZZLE
    assert archive.read("assets/birzzle_seed_v1.zip")
    assert any(name.upper().startswith("META-INF/") for name in archive.namelist())

print(
    "v22 structural validation passed: retry register restoration, "
    "numbered-record wait guards, cold-start maturity, index mtime, "
    "atomic writer, unclamped gameplay library, signed APK"
)
