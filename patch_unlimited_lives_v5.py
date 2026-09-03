import hashlib
from pathlib import Path


SOURCE = Path("native-patches/v4-ranking-inflight/libbirzzle.so")
OUTPUT = Path("native-patches/v5-unlimited-lives/libbirzzle.so")
EXPECTED_SHA256 = "7d079a460b738e4de3d73829a811a0234474d2f55b8072981ba6c7f97fefabf0"

# CHSPManager::GetHeartCount(bool): return the maximum replenishable count.
PATCHES = (
    (0x1639BC, "10b5fff7d7ff10bd", "05207047c046c046"),
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

OUTPUT.write_bytes(data)
print(f"source_sha256={actual_hash}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
