import argparse
import hashlib
import json
import shutil
import struct
import subprocess
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


DEFAULT_SEED_KEY = bytes.fromhex("0b01080202010e0f0008000a0c010e00")
BIRZZLE_XOR_KEY = b"1234567890ABCDEF"
EFFECTIVE_SEED_KEY = bytes(a ^ b for a, b in zip(DEFAULT_SEED_KEY, BIRZZLE_XOR_KEY))
SIGNATURE = b"Birzzle\x00"

# Exact byte counts passed to CProfileHandler::LoadProfile.
KNOWN_PROFILES = {
    "bMarket.dat": (40, "black_market_state"),
    "exp.dat": (44, "experience_safe_number"),
    "new2profile.dat": (752, "general_profile_and_progress_flags"),
    "UPI.dat": (36, "user_pattern_info"),
    "bonus.dat": (32, "mystery_box_bonus_state"),
    "classic_stage_save.dat": (520, "classic_stage_history"),
    "select.dat": (604, "powerup_selection_state"),
    "eventNotice.dat": (20640, "event_webview_notice_state"),
    "rating.bat": (28, "rating_event_state"),
    "kontagentCheck_v2_2.dat": (208, "kontagent_first_check_flags"),
}


def profile_spec(name: str):
    if name.startswith("tuto.dat_"):
        return 208, "tutorial_flags"
    if name.startswith("quest_progress.dat_"):
        return 180, "current_quest_progress"
    if name.startswith("bonusgame.dat_"):
        return 44, "bonus_game_key_state"
    if name.startswith("friendship.dat_"):
        return 80, "friendship_points_state"
    return KNOWN_PROFILES.get(name)


def find_openssl():
    candidates = [
        Path(r"C:\Program Files\Git\mingw64\bin\openssl.exe"),
        Path(shutil.which("openssl") or ""),
    ]
    for candidate in candidates:
        if candidate and candidate.is_file():
            provider = candidate.parent.parent / "lib" / "ossl-modules"
            return candidate, provider if provider.is_dir() else None
    raise SystemExit("OpenSSL with SEED-ECB support was not found")


def seed_crypt(data: bytes, decrypt: bool) -> bytes:
    openssl, provider = find_openssl()
    command = [str(openssl), "enc"]
    if decrypt:
        command.append("-d")
    command.extend(["-seed-ecb", "-K", EFFECTIVE_SEED_KEY.hex(), "-nopad"])
    if provider is not None:
        command.extend(["-provider-path", str(provider), "-provider", "legacy"])
    process = subprocess.run(command, input=data, capture_output=True)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.decode("utf-8", "replace"))
    return process.stdout


def decrypt_profile(raw: bytes, load_size: int) -> tuple[bytes, bytes]:
    if not raw or len(raw) % 16:
        raise ValueError("encrypted profile size is not a positive multiple of 16")
    expected_size = (load_size // 16 + 1) * 16
    if len(raw) != expected_size:
        raise ValueError(f"ciphertext size {len(raw)} != expected padded size {expected_size}")
    padded = seed_crypt(raw, decrypt=True)
    return padded, padded[:load_size]


def encrypt_profile_image(padded: bytes) -> bytes:
    if not padded or len(padded) % 16:
        raise ValueError("decrypted profile image must be block aligned")
    return seed_crypt(padded, decrypt=False)


def safe32_decode(block: bytes) -> int:
    if len(block) != 32:
        raise ValueError("safe-number block must be exactly 32 bytes")
    words = struct.unpack("<8I", block)
    return (
        (words[0] & 0x0000000F)
        | (words[1] & 0x000000F0)
        | (words[5] & 0x00000F00)
        | (words[7] & 0x0000F000)
        | (words[4] & 0x000F0000)
        | (words[6] & 0x00F00000)
        | (words[2] & 0x0F000000)
        | (words[3] & 0xF0000000)
    )


def safe32_encode(template: bytes, value: int) -> bytes:
    if len(template) != 32:
        raise ValueError("safe-number template must be exactly 32 bytes")
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError("safe-number value must fit uint32")
    words = list(struct.unpack("<8I", template))
    masks = [0xF, 0xF0, 0xF000000, 0xF0000000, 0xF0000, 0xF00, 0xF00000, 0xF000]
    for index, mask in enumerate(masks):
        words[index] = (words[index] & ~mask) | (value & mask)
    return struct.pack("<8I", *words)


def u32_list(data: bytes):
    return list(struct.unpack(f"<{len(data) // 4}I", data[: len(data) // 4 * 4]))


def analyze_profile(name: str, plain: bytes, padded: bytes, mtime: int):
    signature_offset = plain.find(SIGNATURE)
    mtime_bytes = struct.pack("<I", mtime & 0xFFFFFFFF)
    mtime_offsets = []
    start = 0
    while True:
        offset = plain.find(mtime_bytes, start)
        if offset < 0:
            break
        mtime_offsets.append(offset)
        start = offset + 1
    result = {
        "name": name,
        "role": profile_spec(name)[1],
        "load_size": len(plain),
        "padded_plaintext_size": len(padded),
        "ignored_tail_hex": padded[len(plain) :].hex(),
        "sha256": hashlib.sha256(plain).hexdigest(),
        "signature_offset": signature_offset if signature_offset >= 0 else None,
        "filesystem_mtime": mtime,
        "filesystem_mtime_utc": datetime.fromtimestamp(mtime, timezone.utc).isoformat(),
        "matching_mtime_offsets": mtime_offsets,
        "u32_prefix": u32_list(plain[: min(len(plain), 128)]),
    }
    if signature_offset == 0 and len(plain) >= 12:
        result["standard_header"] = {
            "signature": plain[:8].decode("ascii", "replace").rstrip("\x00"),
            "timestamp": struct.unpack_from("<I", plain, 8)[0],
        }
    if name == "exp.dat":
        result["experience"] = safe32_decode(plain[12:44])
    elif name == "bonus.dat":
        flag_names = (
            "extra_time_10_seconds",
            "starting_booster_box",
            "recurring_super_bombs",
            "recurring_paint_bombs",
            "recurring_paired_bombs",
            "experience_multiplier_5x",
            "experience_multiplier_10x",
        )
        result["pending_reward_flags"] = {
            flag_name: bool(plain[12 + index])
            for index, flag_name in enumerate(flag_names)
        }
        result["reserved_reward_flags_hex"] = plain[19:26].hex()
        result["uninitialized_save_gap_hex"] = plain[26:28].hex()
        result["paid_open_count_before_next_game"] = struct.unpack_from("<I", plain, 28)[0]
    elif name.startswith("bonusgame.dat_"):
        result["bonus_key_count"] = safe32_decode(plain[12:44])
    elif name.startswith("friendship.dat_"):
        result["current_friendship_points"] = safe32_decode(plain[12:44])
        result["daily_friendship_points"] = safe32_decode(plain[44:76])
        result["trailing_u32"] = struct.unpack_from("<I", plain, 76)[0]
    elif name == "select.dat":
        result["selected_item_ids"] = list(struct.unpack_from("<12i", plain, 12))
        result["selection_flags_hex"] = plain[60:92].hex()
        result["safe_values"] = [
            safe32_decode(plain[offset : offset + 32])
            for offset in range(92, 604, 32)
        ]
    elif name == "classic_stage_save.dat":
        result["classic_header"] = {
            "timestamp": struct.unpack_from("<I", plain, 0)[0],
            "signature": plain[4:12].decode("ascii", "replace").rstrip("\x00"),
            "progress_counter": struct.unpack_from("<I", plain, 12)[0],
            "record_slots": (len(plain) - 16) // 28,
        }
        result["records"] = [
            list(struct.unpack_from("<7I", plain, 16 + index * 28))
            for index in range(result["classic_header"]["record_slots"])
        ]
    elif name.startswith("tuto.dat_") or name == "kontagentCheck_v2_2.dat":
        result["flag_counts"] = {
            "zero": plain[8:].count(0),
            "one": plain[8:].count(1),
            "other": sum(value not in (0, 1) for value in plain[8:]),
        }
    return result


def iter_source(path: Path) -> Iterable[tuple[str, bytes, int]]:
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                name = Path(member.name).name
                if profile_spec(name) is not None:
                    stream = archive.extractfile(member)
                    if stream is not None:
                        yield name, stream.read(), int(member.mtime)
        return
    if path.is_dir():
        for item in path.rglob("*"):
            if item.is_file() and profile_spec(item.name) is not None:
                stat = item.stat()
                yield item.name, item.read_bytes(), int(stat.st_mtime)
        return
    spec = profile_spec(path.name)
    if spec is None:
        raise SystemExit(f"unknown profile filename: {path.name}")
    stat = path.stat()
    yield path.name, path.read_bytes(), int(stat.st_mtime)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dump-plaintext", type=Path)
    args = parser.parse_args()
    records = []
    for name, raw, mtime in iter_source(args.source):
        load_size, _ = profile_spec(name)
        padded, plain = decrypt_profile(raw, load_size)
        if encrypt_profile_image(padded) != raw:
            raise SystemExit(f"SEED round-trip mismatch: {name}")
        records.append(analyze_profile(name, plain, padded, mtime))
        if args.dump_plaintext is not None:
            args.dump_plaintext.mkdir(parents=True, exist_ok=True)
            (args.dump_plaintext / f"{name}.decrypted.bin").write_bytes(plain)
            (args.dump_plaintext / f"{name}.decrypted-padded.bin").write_bytes(padded)
    output = {
        "source": str(args.source),
        "default_seed_key_hex": DEFAULT_SEED_KEY.hex(),
        "xor_key_ascii": BIRZZLE_XOR_KEY.decode("ascii"),
        "effective_seed_key_hex": EFFECTIVE_SEED_KEY.hex(),
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(json.dumps({"records": len(records), "output": str(args.output)}))


if __name__ == "__main__":
    main()
