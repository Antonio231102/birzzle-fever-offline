import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v15-portable-no-heart-deduction/libbirzzle.so")
OUTPUT = Path("native-patches/v17-defensive-state-guards/libbirzzle.so")
ASSET_DIR = Path("native-patches/v17-defensive-state-guards")
EXPECTED_SOURCE_SHA256 = "bf0a350003b8ded667505b81e3edbb5e5ca008547109412dac987fba0821e5ae"
EXPECTED_GUARDS_SHA256 = "4cb0a092708e412fd08e96c42b5f7fafa9e761302509c91e206e3a0c14ec8f34"


def checked_guards() -> bytes:
    payload = (ASSET_DIR / "guards.bin").read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != EXPECTED_GUARDS_SHA256:
        raise SystemExit(
            f"unexpected guards.bin SHA-256: {actual} != {EXPECTED_GUARDS_SHA256}"
        )
    return payload


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


data = bytearray(SOURCE.read_bytes())
source_hash = hashlib.sha256(data).hexdigest()
if source_hash != EXPECTED_SOURCE_SHA256:
    raise SystemExit(
        f"unexpected source SHA-256: {source_hash} != {EXPECTED_SOURCE_SHA256}"
    )

guards = checked_guards()
pocket_hook = thumb2_branch(0x16B04A, 0x2ACEC0)
get_pocket_hook = thumb2_branch(0x16F51E, 0x2ACEE8)
inventory_hook = thumb2_branch(0x16D7A2, 0x2ACF94)

patches = (
    (0x16B04A, bytes.fromhex("fef7bbfe"), pocket_hook, "pocket SET response guard"),
    (0x16F51E, bytes.fromhex("faf751fc"), get_pocket_hook, "pocket GET response guard"),
    (0x16D7A2, bytes.fromhex("a1f72dfd"), inventory_hook, "inventory response guard"),
    (0x2ACEC0, bytes(len(guards)), guards, "executable guard stubs"),
)

for offset, expected, replacement, label in patches:
    if len(expected) != len(replacement):
        raise SystemExit(f"length mismatch for {label}")
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise SystemExit(
            f"unexpected bytes for {label} at {offset:#x}: "
            f"{actual.hex()} != {expected.hex()}"
        )
    data[offset : offset + len(replacement)] = replacement
    print(f"{label}: {offset:#x} {expected.hex()} -> {replacement.hex()}")

OUTPUT.write_bytes(data)
print(f"source_sha256={source_hash}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
