import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v10-rejected-ranking-cleanup/libbirzzle.so")
OUTPUT = Path("native-patches/v11-ranking-dispatch-rearm/libbirzzle.so")
EXPECTED_SHA256 = "28435b4e4577b244e86b742df606fa77f4a0fc9bd4d9b3dcf8dbcb7963777442"

RESTORE_RANKING = 0x141A10
POSTRESTORE_STUB = 0x2ACE90
GET_RANKING = 0x163B78
REARM_REQUEST_STUB = 0x2ACE40


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


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

patches = [
    # Remove v9's speculative re-arm around UI reconstruction. It can be
    # consumed before the request which owns the restored main-menu UI.
    (
        0x145938,
        thumb2_branch(0x145938, POSTRESTORE_STUB, True),
        thumb2_branch(0x145938, RESTORE_RANKING, True),
    ),
    (
        0x145A74,
        thumb2_branch(0x145A74, POSTRESTORE_STUB, True),
        thumb2_branch(0x145A74, RESTORE_RANKING, True),
    ),

    # These central-message cases explicitly dispatch GetRanking. Re-arm at
    # the call itself so no intervening asynchronous request can steal the
    # generation. SNS callback requests remain routed through the closed gate.
    (
        0x147848,
        thumb2_branch(0x147848, GET_RANKING, True),
        thumb2_branch(0x147848, REARM_REQUEST_STUB, True),
    ),
    (
        0x148E38,
        thumb2_branch(0x148E38, GET_RANKING, True),
        thumb2_branch(0x148E38, REARM_REQUEST_STUB, True),
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
