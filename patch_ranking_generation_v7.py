import hashlib
import struct
from pathlib import Path


SOURCE = Path("native-patches/v6-safe-heart-setter/libbirzzle.so")
OUTPUT = Path("native-patches/v7-ranking-generation/libbirzzle.so")
EXPECTED_SHA256 = "3042910e4f13e28289e28cec6879aea2ff8fe6982708916470832e44e9010249"

BSS_GATE = 0x2C7730
UNLOCK_STUB = 0x2ACE30
REARM_REQUEST_STUB = 0x2ACE40
POSTGAME_STUB = 0x2ACE50
GET_RANKING = 0x163B78
POSTGAME_CONTINUE = 0x145BD0


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
    second_base = 0xD000 if link else 0x9000
    second = second_base | (j1 << 13) | (j2 << 11) | ((value >> 1) & 0x7FF)
    return struct.pack("<HH", first, second)


def unlock_code(address: int, literal_address: int, tail_target: int | None) -> bytes:
    # ldr r3, [pc, #8]; add r3, pc; movs r2, #0; strb r2, [r3]
    result = bytes.fromhex("024b7b4400221a70")
    if tail_target is None:
        result += bytes.fromhex("7047c046")  # bx lr; nop
    else:
        result += thumb2_branch(address + 8, tail_target, False)
    pc_for_add = (address + 2 + 4) & ~3
    result += struct.pack("<I", BSS_GATE - pc_for_add)
    if literal_address != address + 12:
        raise ValueError("unexpected literal placement")
    return result


data = bytearray(SOURCE.read_bytes())
actual_hash = hashlib.sha256(data).hexdigest()
if actual_hash != EXPECTED_SHA256:
    raise SystemExit(f"unexpected source SHA-256: {actual_hash}")

patches: list[tuple[int, bytes, bytes]] = []

# Completion still sets CHSPManager's handled byte, but now leaves the gate
# closed. This is the crucial change: response arrival no longer re-arms a new
# request while the current leaderboard UI is still consuming its data.
patches.append((0x2ACE08, bytes.fromhex("00221a70"), bytes.fromhex("01221a70")))

# Dedicated gate helpers in the executable padding already extended by v4.
patches.append((UNLOCK_STUB, bytes(0x10), unlock_code(UNLOCK_STUB, 0x2ACE3C, None)))
patches.append(
    (
        REARM_REQUEST_STUB,
        bytes(0x10),
        unlock_code(REARM_REQUEST_STUB, 0x2ACE4C, GET_RANKING),
    )
)

# ProcessPostGameOver is unique to a completed game. Relocate its overwritten
# prologue into a trampoline, unlock one future request, then resume normally.
postgame_original = bytes.fromhex("f0b55f4656464d464446f0b4")
postgame_stub = (
    postgame_original
    + bytes.fromhex("024b7b4400221a70")
    + thumb2_branch(POSTGAME_STUB + 0x14, POSTGAME_CONTINUE, False)
    + struct.pack("<I", BSS_GATE - ((POSTGAME_STUB + 0x0E + 4) & ~3))
)
if len(postgame_stub) != 0x1C:
    raise SystemExit(f"unexpected post-game stub size: {len(postgame_stub):#x}")
patches.append((POSTGAME_STUB, bytes(0x1C), postgame_stub))
patches.append(
    (
        0x145BC4,
        postgame_original,
        thumb2_branch(0x145BC4, POSTGAME_STUB, False) + bytes.fromhex("c046") * 4,
    )
)

# These are explicit user/UI-reset generations, not automatic startup calls.
patches.append(
    (
        0x8C906,
        thumb2_branch(0x8C906, GET_RANKING, True),
        thumb2_branch(0x8C906, REARM_REQUEST_STUB, True),
    )
)
patches.append(
    (
        0x1453D2,
        thumb2_branch(0x1453D2, GET_RANKING, True),
        thumb2_branch(0x1453D2, REARM_REQUEST_STUB, True),
    )
)

for offset, expected, replacement in patches:
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
