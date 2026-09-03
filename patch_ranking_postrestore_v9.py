import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v8-menu-return-rearm/libbirzzle.so")
OUTPUT = Path("native-patches/v9-postrestore-rearm/libbirzzle.so")
EXPECTED_SHA256 = "b3e524a38e06c0c31fb79171ad9635f2e5ab6694f80648fe48de1db36073ea97"

BSS_GATE = 0x2C7730
RESTORE_RANKING = 0x141A10
V8_RESTORE_STUB = 0x2ACE70
POSTRESTORE_STUB = 0x2ACE90


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


def postrestore_code(address: int) -> bytes:
    # Preserve the caller's return address, finish rebuilding the ranking UI,
    # then open exactly one subsequent ranking generation.
    code = bytes.fromhex("10b5")                         # push {r4, lr}
    code += thumb2_branch(address + 2, RESTORE_RANKING, True)
    code += bytes.fromhex("024b7b4400221a7010bd")       # unlock; pop {r4, pc}
    pc_for_add = (address + 8 + 4) & ~3
    code += struct.pack("<I", BSS_GATE - pc_for_add)
    if len(code) != 0x14:
        raise SystemExit(f"unexpected post-restore stub size: {len(code):#x}")
    return code


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

patches = [
    (POSTRESTORE_STUB, bytes(0x14), postrestore_code(POSTRESTORE_STUB)),
    (
        0x145938,
        thumb2_branch(0x145938, V8_RESTORE_STUB, True),
        thumb2_branch(0x145938, POSTRESTORE_STUB, True),
    ),
    (
        0x145A74,
        thumb2_branch(0x145A74, V8_RESTORE_STUB, True),
        thumb2_branch(0x145A74, POSTRESTORE_STUB, True),
    ),
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
