"""Prepare private, authenticated historical game records for an iOS-only offline build.

The output contains account credentials: keep it under ignored ios/captures/.
This tool does not modify the original Android backup or install anything.
"""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import struct
import sys

from Crypto.Cipher import AES

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import analyze_birzzle_save as history
import patch_startup_probe as ios


# Byte positions used by the original runDecrypt: at VM 0x1d95e4. The eight
# NSString backing tables are read from the checked, original iOS executable;
# the server-to-client key is never printed or saved separately.
_WIRE_TABLE_VM = 0x483490
_WIRE_SOURCES = (5, 1, 5, 2, 3, 4, 6, 7, 2, 4, 1, 5, 4, 3, 7, 3)
_WIRE_OFFSETS = (0, 21, 9, 9, 0, 9, 7, 18, 15, 17, 13, 17, 3, 7, 0, 3)


def incoming_key(image: bytes) -> bytes:
    strings = []
    for index in range(8):
        ref = struct.unpack_from("<I", image, _WIRE_TABLE_VM - ios.IMAGE_BASE + index * 4)[0]
        backing, length = struct.unpack_from("<II", image, ref - ios.IMAGE_BASE + 8)
        if not 0 < length < 256 or not ios.IMAGE_BASE < backing < len(image) + ios.IMAGE_BASE - length:
            raise ValueError("Original iOS wire-key table changed")
        strings.append(image[backing - ios.IMAGE_BASE:backing - ios.IMAGE_BASE + length])
    return bytes(strings[source][offset] for source, offset in zip(_WIRE_SOURCES, _WIRE_OFFSETS))


def encode_incoming_reply(payload: bytes, key: bytes) -> str:
    """Encode the original iOS AES-ECB/MD5 wire format, not Android CCrypt2."""
    if not payload or b"\0" in payload:
        raise ValueError("Invalid original cached JSON reply")
    plain = hashlib.md5(payload).hexdigest().encode("ascii") + payload
    padding = 16 - len(plain) % 16
    encrypted = AES.new(key, AES.MODE_ECB).encrypt(plain + bytes((padding,)) * padding)
    return base64.b64encode(encrypted).decode("ascii")


def decode_incoming_reply(encoded: str, key: bytes) -> bytes:
    """Mirror decryptString:key: MD5/JSON-tail validation for build-time proof."""
    encrypted = base64.b64decode(encoded, validate=True)
    if not encrypted or len(encrypted) % 16:
        raise ValueError("Invalid AES block count")
    plain = AES.new(key, AES.MODE_ECB).decrypt(encrypted)
    padding = plain[-1]
    if padding == ord("}"):
        body = plain
    elif 1 <= padding <= 16 and plain[-padding:] == bytes((padding,)) * padding:
        body = plain[:-padding]
    else:
        raise ValueError("Invalid reply padding")
    if len(body) < 34 or hashlib.md5(body[32:]).hexdigest().encode("ascii") != body[:32]:
        raise ValueError("Reply MD5 mismatch")
    return body[32:]

def prepare(source: Path, image: bytes) -> dict:
    key = incoming_key(image)
    responses = {}
    saves = {}
    for path, raw, mtime in history.iter_source(source):
        role = history.identify_role(Path(path).name)
        if not role or not role.startswith(("cached_response:", "hashed_static:")):
            continue
        decoded = history.decrypt2(raw)
        if (not decoded or not decoded["digest_valid"] or decoded["duplicate_fields"]
                or decoded["timestamp"] is None or abs(mtime - decoded["timestamp"]) > 10):
            raise ValueError("Invalid historical encrypted record")
        if (role == "hashed_static:stage.dat" and decoded["field_failure_reason"] == "FIELD_MISSING_DATA"
                and len(decoded["malformed_lines"]) == 1):
            # The authenticated Android stage record is malformed; its login
            # reply, not this broken local record, carries historical stage state.
            continue
        if decoded["malformed_lines"] or decoded["field_failure_reason"]:
            raise ValueError("Malformed historical encrypted record")
        if role.startswith("hashed_static:"):
            if role in saves:
                raise ValueError("Duplicate historical save")
            saves[role] = {"service": Path(path).name, "password": raw.decode("ascii")}
            continue
        payload = decoded["decoded_data"]
        command = role.split(":", 1)[1]
        command_id = json.loads(payload).get("commandid") if payload else None
        if (not isinstance(command_id, str) or not command_id.isdecimal()
                or (command == "SERVER.INIT" and command_id != "1") or command in responses):
            raise ValueError("Missing, mismatched, or duplicate cached reply")
        encoded = encode_incoming_reply(payload, key)
        if decode_incoming_reply(encoded, key) != payload:
            raise ValueError("Incoming iOS wire roundtrip failed")
        responses[command] = encoded
    expected_saves = {"hashed_static:" + name for name in history.STATIC_NAMES if name != "stage.dat"}
    if set(responses) != set(history.RESPONSE_COMMANDS) or set(saves) != expected_saves:
        raise ValueError("Incomplete historical usable game saves or cached replies")
    return {"historical_uid": history.HISTORICAL_UID, "keychain_records": saves,
            "incoming_replies": responses}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="private ignored ios/captures/ JSON path")
    args = parser.parse_args()
    target = args.output.resolve()
    if not target.is_relative_to((Path(__file__).resolve().parent / "captures").resolve()):
        parser.error("Output must remain inside private ios/captures/")
    package = prepare(Path(__file__).resolve().parent.parent / "com.halfbrick.birzzlefever-20160501-111000.tar.gz",
                      ios.original_executable())
    target.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        json.dump(package, stream, sort_keys=True, separators=(",", ":"))
    print("Prepared private iOS offline history: authenticated static saves", len(package["keychain_records"]),
          "and cached service replies", len(package["incoming_replies"]))


if __name__ == "__main__":
    main()
