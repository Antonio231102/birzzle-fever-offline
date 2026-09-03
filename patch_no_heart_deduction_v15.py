import hashlib
from pathlib import Path


SOURCE = Path("native-patches/v11-ranking-dispatch-rearm/libbirzzle.so")
OUTPUT = Path("native-patches/v15-portable-no-heart-deduction/libbirzzle.so")
EXPECTED_SHA256 = "9f4d9144e9c1afe3495c7a0c9d1cde9ebda359e5b5d182e5ac9924033224c34d"

# 0x1484fc, classic GameStart request:
#     rsbs r1, r7, #0  ->  movs r1, #0
# Keep the normal pocket.set callback, but never submit a heart deduction.
#
# 0x171bfc, CCashManager::SetCurrentHeartCount(CSafeNumber):
# Restore the original function prologue, removing v6's global forced-five setter.
PATCHES = (
    (0x1484FC, "7942", "0021"),
    (0x171BFC, "052119f79dbc", "f8b55f465646"),
)


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

for offset, expected_hex, replacement_hex in PATCHES:
    expected = bytes.fromhex(expected_hex)
    replacement = bytes.fromhex(replacement_hex)
    if len(expected) != len(replacement):
        raise SystemExit(f"length mismatch at {offset:#x}")
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
