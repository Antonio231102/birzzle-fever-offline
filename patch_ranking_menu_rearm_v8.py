import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v7-ranking-generation/libbirzzle.so")
OUTPUT = Path("native-patches/v8-menu-return-rearm/libbirzzle.so")
EXPECTED_SHA256 = "ef3371b363ada683562aa83b1897af4918f1a5a5bc691fe3498774c568aba461"

BSS_GATE = 0x2C7730
RESTORE_RANKING = 0x141A10
EXIT_MAIN_MENU = 0x14512C
RESTORE_REARM_STUB = 0x2ACE70
EXIT_REARM_STUB = 0x2ACE80


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


def unlock_then_tail(address: int, target: int) -> bytes:
    # Preserve all arguments, clear only v7's dedicated request gate, then
    # tail-call the original transition function.
    code = bytes.fromhex("024b7b4400221a70")
    code += thumb2_branch(address + 8, target, False)
    pc_for_add = (address + 2 + 4) & ~3
    code += struct.pack("<I", BSS_GATE - pc_for_add)
    if len(code) != 0x10:
        raise SystemExit("unexpected stub size")
    return code


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

patches = [
    # The two central UI branches which reconstruct the main-menu ranking.
    # Re-arm before reconstruction starts, rather than after a response is
    # delivered, so v7's startup duplicate protection remains closed.
    (RESTORE_REARM_STUB, bytes(0x10), unlock_then_tail(RESTORE_REARM_STUB, RESTORE_RANKING)),
    (0x145938, thumb2_branch(0x145938, RESTORE_RANKING, True), thumb2_branch(0x145938, RESTORE_REARM_STUB, True)),
    (0x145A74, thumb2_branch(0x145A74, RESTORE_RANKING, True), thumb2_branch(0x145A74, RESTORE_REARM_STUB, True)),

    # Mid-game quit has a separate dispatcher path. Re-arm at its explicit
    # exit-to-menu transition; the original function and arguments are kept.
    (EXIT_REARM_STUB, bytes(0x10), unlock_then_tail(EXIT_REARM_STUB, EXIT_MAIN_MENU)),
    (0x147904, thumb2_branch(0x147904, EXIT_MAIN_MENU, True), thumb2_branch(0x147904, EXIT_REARM_STUB, True)),
]

for offset, expected, replacement in patches:
    if len(expected) != len(replacement):
        raise SystemExit(f"length mismatch at {offset:#x}")
    actual = bytes(data[offset : offset + len(expected)])
    if actual != expected:
        raise SystemExit(f"unexpected bytes at {offset:#x}: {actual.hex()} != {expected.hex()}")
    data[offset : offset + len(expected)] = replacement
    print(f"{offset:#x}: {expected.hex()} -> {replacement.hex()}")

OUTPUT.parent.mkdir(parents=True, exist_ok=True)
OUTPUT.write_bytes(data)
print(f"source_sha256={actual_hash}")
print(f"output_sha256={hashlib.sha256(data).hexdigest()}")
