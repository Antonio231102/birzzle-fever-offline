import argparse
import hashlib
from pathlib import Path


EXPECTED_SHA256 = "607aa3efd6acb0c35f26171158853a9e56d8600c4dba6ed7a523d0756f30e79e"
PATCH_OFFSET = 0x163B48
EXPECTED_BYTES = bytes.fromhex("00 b5")  # push {lr}
PATCHED_BYTES = bytes.fromhex("70 47")   # bx lr


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Disable Birzzle Fever's redundant global-ranking request."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()

    source_data = args.source.read_bytes()
    source_hash = sha256(source_data)
    if source_hash != EXPECTED_SHA256:
        raise SystemExit(
            f"refusing unknown input: SHA-256 {source_hash}, expected {EXPECTED_SHA256}"
        )

    actual = source_data[PATCH_OFFSET : PATCH_OFFSET + len(EXPECTED_BYTES)]
    if actual != EXPECTED_BYTES:
        raise SystemExit(
            f"refusing unexpected bytes at {PATCH_OFFSET:#x}: {actual.hex(' ')}"
        )

    patched = bytearray(source_data)
    patched[PATCH_OFFSET : PATCH_OFFSET + len(PATCHED_BYTES)] = PATCHED_BYTES
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_bytes(patched)

    print(f"source:  {args.source} ({source_hash})")
    print(f"patch:   {PATCH_OFFSET:#x}: {EXPECTED_BYTES.hex(' ')} -> {PATCHED_BYTES.hex(' ')}")
    print(f"output:  {args.destination} ({sha256(patched)})")


if __name__ == "__main__":
    main()
