import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v9-postrestore-rearm/libbirzzle.so")
OUTPUT = Path("native-patches/v10-rejected-ranking-cleanup/libbirzzle.so")
EXPECTED_SHA256 = "3720275be9e4215856d8b5713faddfc6edf05816606eae58d6da8fb93d673b9b"

LOADING_GET_HANDLE = 0x97AC8
LOADING_HIDE = 0x97554
REJECT_BRIDGE = 0x2ACE10
REJECT_CLEANUP_STUB = 0x2ACEB0
REJECT_EPILOGUE = 0x2ACE16


def thumb2_branch(source: int, target: int, link: bool) -> bytes:
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
    second = (0xD000 if link else 0x9000) | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


def cleanup_code(address: int) -> bytes:
    # GetRanking has pushed three registers, so temporarily restore 8-byte ABI
    # stack alignment while calling the loading-dialog methods.
    code = bytes.fromhex("81b0")
    code += thumb2_branch(address + 2, LOADING_GET_HANDLE, True)
    code += thumb2_branch(address + 6, LOADING_HIDE, True)
    code += bytes.fromhex("01b0")
    code += thumb2_branch(address + 12, REJECT_EPILOGUE, False)
    if len(code) != 0x10:
        raise SystemExit(f"unexpected cleanup stub size: {len(code):#x}")
    return code


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

patches = [
    # Change only the dedicated-gate rejection. The earlier CHSP eligibility
    # rejection still returns directly through the original epilogue.
    (0x2ACDF0, bytes.fromhex("11d0"), bytes.fromhex("0ed0")),
    (REJECT_BRIDGE, bytes.fromhex("c046c046"), thumb2_branch(REJECT_BRIDGE, REJECT_CLEANUP_STUB, False)),
    (REJECT_CLEANUP_STUB, bytes(0x10), cleanup_code(REJECT_CLEANUP_STUB)),
]

for offset, expected, replacement in patches:
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise SystemExit(f"unexpected bytes at {offset:#x}: {actual.hex()} != {expected.hex()}")
    data[offset : offset + len(expected)] = replacement
    print(f"{offset:#x}: {expected.hex()} -> {replacement.hex()}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_bytes(data)
print(f"source_sha256={actual_hash}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
