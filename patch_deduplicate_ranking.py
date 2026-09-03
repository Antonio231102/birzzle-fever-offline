import argparse
import hashlib
from pathlib import Path


EXPECTED_SHA256 = "607aa3efd6acb0c35f26171158853a9e56d8600c4dba6ed7a523d0756f30e79e"
PATCH_OFFSET = 0x163BAA
EXPECTED_BYTES = bytes.fromhex("e5 54")  # strb r5, [r4, r3], clears CHSPManager+0x79f
PATCHED_BYTES = bytes.fromhex("c0 46")   # Thumb NOP (mov r8, r8)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Keep Birzzle Fever's per-process ranking-delivery guard set."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    data = args.source.read_bytes()
    actual_hash = sha256(data)
    if actual_hash != EXPECTED_SHA256:
        raise SystemExit(
            f"refusing unknown input: SHA-256 {actual_hash}, expected {EXPECTED_SHA256}"
        )
    actual = data[PATCH_OFFSET : PATCH_OFFSET + 2]
    if actual != EXPECTED_BYTES:
        raise SystemExit(
            f"refusing unexpected bytes at {PATCH_OFFSET:#x}: {actual.hex(' ')}"
        )

    patched = bytearray(data)
    patched[PATCH_OFFSET : PATCH_OFFSET + 2] = PATCHED_BYTES
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_bytes(patched)
    print(f"source: {actual_hash}")
    print(f"patch:  {PATCH_OFFSET:#x}: {EXPECTED_BYTES.hex(' ')} -> {PATCHED_BYTES.hex(' ')}")
    print(f"output: {sha256(patched)}")


if __name__ == "__main__":
    main()
