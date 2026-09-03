import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v13-powerup-pending-generation/libbirzzle.so")
OUTPUT = Path("native-patches/v14-powerup-scene-pending/libbirzzle.so")
EXPECTED_SHA256 = "5ddc810950d623bf4cff8bde483900c89d4b3b06dbd826f9bc5608540b45449f"

RESTORE_RANKING = 0x141A10
V13_RESTORE_MARKER = 0x2ACEC0
SET_CURRENT_SCENE = 0x141870
PROCESS_GAME_START = 0x142DF4
POWERUP_PENDING = 0x2C7731
MARK_SCENE_STUB = 0x2ACEF0
CLEAR_GAMESTART_STUB = 0x2ACF00


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


def flag_then_tail(address: int, value: int, target: int) -> bytes:
    code = bytes.fromhex("024b7b44")
    code += bytes((value, 0x22))                 # movs r2, #value
    code += bytes.fromhex("1a70")               # strb r2, [r3]
    code += thumb2_branch(address + 8, target, False)
    pc_for_add = (address + 2 + 4) & ~3
    code += struct.pack("<I", POWERUP_PENDING - pc_for_add)
    if len(code) != 0x10:
        raise SystemExit("unexpected flag stub size")
    return code


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

patches = [
    # V13 marked unrelated restoration calls; restore them to their originals.
    (0x145938, thumb2_branch(0x145938, V13_RESTORE_MARKER, True), thumb2_branch(0x145938, RESTORE_RANKING, True)),
    (0x145A74, thumb2_branch(0x145A74, V13_RESTORE_MARKER, True), thumb2_branch(0x145A74, RESTORE_RANKING, True)),

    # Mark only the confirmed transition into power-up selection (scene 0x0A).
    (MARK_SCENE_STUB, bytes(0x10), flag_then_tail(MARK_SCENE_STUB, 1, SET_CURRENT_SCENE)),
    (0x1437FA, thumb2_branch(0x1437FA, SET_CURRENT_SCENE, True), thumb2_branch(0x1437FA, MARK_SCENE_STUB, True)),

    # Committing a game cancels the pending back-navigation generation.
    (CLEAR_GAMESTART_STUB, bytes(0x10), flag_then_tail(CLEAR_GAMESTART_STUB, 0, PROCESS_GAME_START)),
    (0x148E2E, thumb2_branch(0x148E2E, PROCESS_GAME_START, True), thumb2_branch(0x148E2E, CLEAR_GAMESTART_STUB, True)),
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
