import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v12-powerup-dispatch-rearm/libbirzzle.so")
OUTPUT = Path("native-patches/v13-powerup-pending-generation/libbirzzle.so")
EXPECTED_SHA256 = "0d673f4827ae588119b9fd0bb518db033e654c9f6d1af6a1f1da6bf2eb8c2ae6"

RESTORE_RANKING = 0x141A10
GET_RANKING = 0x163B78
REARM_REQUEST_STUB = 0x2ACE40
POWERUP_PENDING = 0x2C7731
MARK_PENDING_STUB = 0x2ACEC0
CONDITIONAL_DISPATCH_STUB = 0x2ACED0


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


def mark_pending_code(address: int) -> bytes:
    # Set a flag which is independent of the request gate, then perform the
    # original UI restoration. Unrelated requests cannot consume this marker.
    code = bytes.fromhex("024b7b4401221a70")
    code += thumb2_branch(address + 8, RESTORE_RANKING, False)
    pc_for_add = (address + 2 + 4) & ~3
    code += struct.pack("<I", POWERUP_PENDING - pc_for_add)
    if len(code) != 0x10:
        raise SystemExit("unexpected marker stub size")
    return code


def conditional_dispatch_code(address: int) -> bytes:
    # If a menu restoration marked this as a deliberate return, consume the
    # marker and use v7's re-arm helper. Otherwise tail-call GetRanking with the
    # existing gate untouched (the clean-startup behavior).
    code = bytes.fromhex("054b7b441a78002a03d000221a70")
    code += thumb2_branch(address + 14, REARM_REQUEST_STUB, False)
    code += thumb2_branch(address + 18, GET_RANKING, False)
    code += bytes.fromhex("c046")
    pc_for_add = (address + 2 + 4) & ~3
    code += struct.pack("<I", POWERUP_PENDING - pc_for_add)
    if len(code) != 0x1C:
        raise SystemExit(f"unexpected conditional stub size: {len(code):#x}")
    return code


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

patches = [
    (MARK_PENDING_STUB, bytes(0x10), mark_pending_code(MARK_PENDING_STUB)),
    (CONDITIONAL_DISPATCH_STUB, bytes(0x1C), conditional_dispatch_code(CONDITIONAL_DISPATCH_STUB)),
    (0x145938, thumb2_branch(0x145938, RESTORE_RANKING, True), thumb2_branch(0x145938, MARK_PENDING_STUB, True)),
    (0x145A74, thumb2_branch(0x145A74, RESTORE_RANKING, True), thumb2_branch(0x145A74, MARK_PENDING_STUB, True)),
    # Dispatch A is no longer a generation boundary.
    (0x147848, thumb2_branch(0x147848, REARM_REQUEST_STUB, True), thumb2_branch(0x147848, GET_RANKING, True)),
    # Dispatch B re-arms only when the one-shot return marker is present.
    (0x148E38, thumb2_branch(0x148E38, GET_RANKING, True), thumb2_branch(0x148E38, CONDITIONAL_DISPATCH_STUB, True)),
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
