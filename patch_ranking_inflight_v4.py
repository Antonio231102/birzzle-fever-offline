import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v2-deduplicate-ranking/libbirzzle.so")
OUTPUT = Path("native-patches/v4-ranking-inflight/libbirzzle.so")
EXPECTED_SHA256 = "f0f10455eb6f0c949168bbed5411bbfac7d4299830d15837bb5449694ebe8608"

REQUEST_STUB = 0x2ACDE0
COMPLETION_STUB = 0x2ACE00
BSS_INFLIGHT = 0x2C7730

PATCHES = (
    # Genuine executable padding between PT_LOAD segments. Both stubs address
    # a dedicated zero-initialized byte appended to the writable BSS.
    (
        REQUEST_STUB,
        "00" * 0x50,
        "0e4bc256002a16d00d4b7b441a78012a11d001221a700b4b0022c2547047c046"
        "0122c254084b7b4400221a707047c046c046c046c04630bdc046c046"
        "9d07000044a901009f07000028a90100" + "00" * 4,
    ),
    # Call the guard stub, then perform the original stack allocation and r4
    # initialization before continuing at GetLoadingDialog().
    (
        0x163B7A,
        "1b4b85b0041cc356002b01d1",
        "49f131f985b0041c02e0c046",
    ),
    # The v2 patch already leaves the original handled flag untouched here.
    (0x163BAA, "c046", "c046"),
    # Replace the original handled-flag store with a call to the completion
    # stub, which performs that store and also clears the independent flag.
    (0x16CD2C, "0122c254", "40f168f8"),
)


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

# Extend the RX PT_LOAD from 0x2acde0 to the next page boundary. The following
# RW segment starts at 0x2ad000, so no segment overlap is introduced.
e_phoff = struct.unpack_from("<I", data, 0x1C)[0]
e_phentsize = struct.unpack_from("<H", data, 0x2A)[0]
e_phnum = struct.unpack_from("<H", data, 0x2C)[0]
rx_header = None
for index in range(e_phnum):
    header = e_phoff + index * e_phentsize
    p_type, p_offset = struct.unpack_from("<II", data, header)
    p_flags = struct.unpack_from("<I", data, header + 24)[0]
    if p_type == 1 and p_offset == 0 and p_flags == 5:
        rx_header = header
        break
if rx_header is None:
    raise SystemExit("RX PT_LOAD not found")
old_filesz, old_memsz = struct.unpack_from("<II", data, rx_header + 16)
if (old_filesz, old_memsz) != (0x2ACDE0, 0x2ACDE0):
    raise SystemExit(
        f"unexpected RX sizes: {old_filesz:#x}, {old_memsz:#x}"
    )
struct.pack_into("<II", data, rx_header + 16, 0x2AD000, 0x2AD000)
print("RX PT_LOAD: 0x2acde0 -> 0x2ad000")

# Add one dedicated zero-initialized word at the end of the RW segment's BSS.
rw_header = None
for index in range(e_phnum):
    header = e_phoff + index * e_phentsize
    p_type, p_offset, p_vaddr = struct.unpack_from("<III", data, header)
    p_flags = struct.unpack_from("<I", data, header + 24)[0]
    if p_type == 1 and p_offset == 0x2AD000 and p_vaddr == 0x2AD000 and p_flags == 6:
        rw_header = header
        break
if rw_header is None:
    raise SystemExit("RW PT_LOAD not found")
rw_filesz, rw_memsz = struct.unpack_from("<II", data, rw_header + 16)
if (rw_filesz, rw_memsz) != (0x19D74, 0x1A730):
    raise SystemExit(f"unexpected RW sizes: {rw_filesz:#x}, {rw_memsz:#x}")
if 0x2AD000 + rw_memsz != BSS_INFLIGHT:
    raise SystemExit("unexpected BSS end")
struct.pack_into("<I", data, rw_header + 20, rw_memsz + 4)
print("RW PT_LOAD BSS: 0x1a730 -> 0x1a734")

for offset, expected_hex, replacement_hex in PATCHES:
    expected = bytes.fromhex(expected_hex)
    replacement = bytes.fromhex(replacement_hex)
    if len(replacement) != len(expected):
        raise SystemExit(
            f"length mismatch at {offset:#x}: {len(replacement)} != {len(expected)}"
        )
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise SystemExit(
            f"unexpected bytes at {offset:#x}: {actual.hex()} != {expected.hex()}"
        )
    data[offset : offset + len(expected)] = replacement
    print(f"{offset:#x}: {expected.hex()} -> {replacement.hex()}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_bytes(data)
print(f"source_sha256={actual_hash}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
