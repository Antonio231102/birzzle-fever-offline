import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v10-rejected-ranking-cleanup/libbirzzle.so")
OUTPUT = Path("native-patches/v12-powerup-dispatch-rearm/libbirzzle.so")
EXPECTED_SHA256 = "28435b4e4577b244e86b742df606fa77f4a0fc9bd4d9b3dcf8dbcb7963777442"

RESTORE_RANKING = 0x141A10
POSTRESTORE_STUB = 0x2ACE90
GET_RANKING = 0x163B78
REARM_REQUEST_STUB = 0x2ACE40
POWERUP_RETURN_DISPATCH = 0x147848


def thumb2_branch(source: int, target: int, link: bool) -> bytes:
    offset = target - (source + 4)
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
    (0x145938, POSTRESTORE_STUB, RESTORE_RANKING),
    (0x145A74, POSTRESTORE_STUB, RESTORE_RANKING),
    (POWERUP_RETURN_DISPATCH, GET_RANKING, REARM_REQUEST_STUB),
]

for address, old_target, new_target in patches:
    expected = thumb2_branch(address, old_target, True)
    replacement = thumb2_branch(address, new_target, True)
    actual = bytes(data[address : address + 4])
    if actual != expected:
        raise SystemExit(f"unexpected bytes at {address:#x}: {actual.hex()} != {expected.hex()}")
    data[address : address + 4] = replacement
    print(f"{address:#x}: {expected.hex()} -> {replacement.hex()}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_bytes(data)
print(f"source_sha256={actual_hash}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
