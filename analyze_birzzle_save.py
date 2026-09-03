import argparse
import base64
import gzip
import hashlib
import json
import re
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from Crypto.Cipher import AES


CRYPT2_KEY = b"miaeHgpdskiinerS"
HISTORICAL_UID = "3c8bb7308c3fcb60c439224bd595c794d8f31501"
REQUEST_INDEX_NAME = hashlib.md5(
    (HISTORICAL_UID + "REQUESTPOOLINDEX").encode()
).hexdigest()
REQUEST_NAMES = {
    hashlib.md5((HISTORICAL_UID + f"REQUESTPOOL_{index}").encode()).hexdigest(): index
    for index in range(4096)
}
RESPONSE_COMMANDS = (
    "SERVER.INIT", "POCKET.LOGIN", "INVENTORY.LIST", "INVENTORY.USE",
    "INVENTORY.UPDATE", "INVENTORY.BUY", "CUSTOM.GET", "CUSTOM.POST",
    "POCKET.GET", "POCKET.SET", "GLOBAL.GET.NAME", "GIFT.GET.COUNT",
    "SCORE.RANKING",
)
RESPONSE_NAMES = {
    hashlib.md5((HISTORICAL_UID + command).encode()).hexdigest(): command
    for command in RESPONSE_COMMANDS
}
STATIC_NAMES = (
    "pocket.dat", "stage.dat", "social.dat", "messagecount.dat",
    "friendlist.dat", "localtime.dat", "variable.dat", "submarinevariable.dat",
)
STATIC_HASH_NAMES = {
    hashlib.md5(name.encode()).hexdigest(): name for name in STATIC_NAMES
}


def identify_role(name: str) -> str | None:
    if name == REQUEST_INDEX_NAME:
        return "response_pool_index"
    if name in REQUEST_NAMES:
        return f"response_pool_request:{REQUEST_NAMES[name]}"
    if name in RESPONSE_NAMES:
        return f"cached_response:{RESPONSE_NAMES[name]}"
    if name in STATIC_HASH_NAMES:
        return f"hashed_static:{STATIC_HASH_NAMES[name]}"
    if name == hashlib.md5((HISTORICAL_UID + "APIFILE").encode()).hexdigest():
        return "api_command_list"
    if name.endswith(".xml"):
        return "android_shared_preferences"
    if name in {"webview.db", "Web Data"}:
        return "webview_metadata"
    if name == "e30b431a9b2d47948fed9f6a5602fa91":
        return "kontagent_api_queue"
    if name in {"clearbox", "highscore", "order", "profile", "test"}:
        return "ole_compound_workbook"
    return None


def decrypt2(raw: bytes):
    try:
        ciphertext = base64.b64decode(raw, validate=True)
    except Exception:
        return None
    if not ciphertext or len(ciphertext) % 16:
        return None
    plain = AES.new(CRYPT2_KEY, AES.MODE_ECB).decrypt(ciphertext)
    padding = plain[-1]
    if padding < 1 or padding > 16 or plain[-padding:] != bytes([padding]) * padding:
        return None
    plain = plain[:-padding]
    if len(plain) < 34 or plain[:2] != b"C+":
        return None
    digest = plain[2:34]
    body = plain[34:]
    digest_valid = digest.lower() == hashlib.md5(body).hexdigest().encode("ascii")
    fields = {}
    malformed_lines = []
    for line in body.split(b"\n"):
        if b":" not in line:
            malformed_lines.append(line.decode("utf-8", "replace"))
            continue
        key, value = line.split(b":", 1)
        fields[key.decode("ascii", "replace")] = value
    decoded_data = None
    if "DATA" in fields:
        try:
            decoded_data = base64.b64decode(fields["DATA"], validate=True)
        except Exception:
            decoded_data = None
    timestamp = None
    if "TIMESTAMP" in fields:
        try:
            timestamp = int(fields["TIMESTAMP"])
        except ValueError:
            pass
    return {
        "plaintext": plain,
        "body": body,
        "digest": digest.decode("ascii", "replace"),
        "digest_valid": digest_valid,
        "fields": {k: v.decode("utf-8", "replace") for k, v in fields.items()},
        "malformed_lines": malformed_lines,
        "decoded_data": decoded_data,
        "timestamp": timestamp,
    }


def classify(raw: bytes) -> str:
    if raw.startswith(b"SQLite format 3\x00"):
        return "sqlite"
    if raw.startswith(bytes.fromhex("d0cf11e0a1b11ae1")):
        return "ole_cfb"
    if raw.startswith(bytes.fromhex("aced0005")):
        return "java_serialized"
    if raw.lstrip().startswith((b"<?xml", b"<map", b"<plist")):
        return "xml"
    if decrypt2(raw) is not None:
        return "ccrypt2"
    if not raw:
        return "empty"
    printable = sum(c in b"\t\n\r" or 32 <= c < 127 for c in raw)
    if printable / len(raw) >= 0.9:
        return "text"
    return "binary"


def summarize_data(data: bytes | None, depth: int = 0):
    if data is None:
        return None
    result = {"size": len(data)}
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        result.update({"encoding": "binary", "hex_prefix": data[:96].hex()})
        return result
    result.update({"encoding": "utf-8", "text": text})
    if depth >= 3:
        return result
    candidate = text
    revision = None
    match = re.fullmatch(r"([A-Za-z0-9+/]+={0,2})_(\d+)", text)
    if match:
        candidate, revision = match.groups()
    if not candidate:
        return result
    try:
        padded = candidate + "=" * (-len(candidate) % 4)
        nested = base64.b64decode(padded, validate=True)
    except Exception:
        return result
    layer = summarize_data(nested, depth + 1)
    if nested.startswith(b"\x1f\x8b"):
        try:
            inflated = gzip.decompress(nested)
            layer = {
                "encoding": "gzip",
                "compressed_size": len(nested),
                "decoded": summarize_data(inflated, depth + 1),
            }
        except Exception:
            pass
    result["nested_base64"] = layer
    if revision is not None:
        result["suffix_revision"] = revision
    return result


def analyze_entry(path: str, raw: bytes, mtime: int):
    kind = classify(raw)
    record = {
        "path": path,
        "name": Path(path).name,
        "size": len(raw),
        "mtime": mtime,
        "mtime_utc": datetime.fromtimestamp(mtime, timezone.utc).isoformat(),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "kind": kind,
        "role": identify_role(Path(path).name),
    }
    if kind == "ccrypt2":
        decoded = decrypt2(raw)
        assert decoded is not None
        timestamp = decoded["timestamp"]
        record["ccrypt2"] = {
            "digest": decoded["digest"],
            "digest_valid": decoded["digest_valid"],
            "fields": decoded["fields"],
            "malformed_lines": decoded["malformed_lines"],
            "decoded_data": summarize_data(decoded["decoded_data"]),
            "embedded_timestamp": timestamp,
            "timestamp_utc": (
                datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
                if timestamp is not None else None
            ),
            "mtime_delta_seconds": mtime - timestamp if timestamp is not None else None,
            "passes_fileworker_time_check": (
                abs(mtime - timestamp) <= 10 if timestamp is not None else False
            ),
        }
    elif kind == "text":
        record["text_prefix"] = raw[:512].decode("utf-8", "replace")
    return record


def iter_source(path: Path) -> Iterable[tuple[str, bytes, int]]:
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            for member in archive.getmembers():
                if not member.isfile():
                    continue
                stream = archive.extractfile(member)
                if stream is not None:
                    yield member.name, stream.read(), int(member.mtime)
        return
    if path.is_dir():
        for item in sorted(path.rglob("*")):
            if item.is_file():
                stat = item.stat()
                yield str(item.relative_to(path)), item.read_bytes(), int(stat.st_mtime)
        return
    stat = path.stat()
    yield path.name, path.read_bytes(), int(stat.st_mtime)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    records = [analyze_entry(name, raw, mtime) for name, raw, mtime in iter_source(args.source)]
    counts = {}
    for record in records:
        counts[record["kind"]] = counts.get(record["kind"], 0) + 1
    output = {
        "source": str(args.source),
        "counts": counts,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"source": str(args.source), "counts": counts, "output": str(args.output)}))


if __name__ == "__main__":
    main()
