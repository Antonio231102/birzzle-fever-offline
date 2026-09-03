import argparse
import base64
import hashlib
import json
import os
import shutil
import stat
import struct
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from Crypto.Cipher import AES


UID = "3c8bb7308c3fcb60c439224bd595c794d8f31501"
INDEX_NAME = hashlib.md5((UID + "REQUESTPOOLINDEX").encode()).hexdigest()
AES_KEY = b"miaeHgpdskiinerS"
PACKAGE = "com.halfbrick.birzzlefever"
REMOTE_INDEX = f"/data/data/{PACKAGE}/files/{INDEX_NAME}"
ADB = Path("platform-tools-latest-windows/platform-tools/adb.exe")


def utc(timestamp):
    try:
        return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()
    except Exception:
        return None


def diagnose_bytes(raw: bytes, mtime: int | None = None):
    result = {
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "mtime": mtime,
        "mtime_utc": utc(mtime) if mtime is not None else None,
        "failure_reason": None,
    }
    if not raw:
        result["failure_reason"] = "EMPTY_FILE"
        return result
    try:
        cipher = base64.b64decode(raw, validate=True)
    except Exception as error:
        result.update(failure_reason="OUTER_BASE64_INVALID", error=str(error))
        return result
    result["ciphertext_size"] = len(cipher)
    if not cipher or len(cipher) % 16:
        result["failure_reason"] = "AES_BLOCK_SIZE_INVALID"
        return result
    padded = AES.new(AES_KEY, AES.MODE_ECB).decrypt(cipher)
    padding = padded[-1]
    result["padding_byte"] = padding
    if padding < 1 or padding > 16 or padded[-padding:] != bytes([padding]) * padding:
        result["failure_reason"] = "PKCS7_PADDING_INVALID"
        return result
    plain = padded[:-padding]
    result["plaintext_size"] = len(plain)
    if not plain.startswith(b"C+"):
        result["failure_reason"] = "PREFIX_INVALID"
        return result
    if len(plain) < 34:
        result["failure_reason"] = "ENVELOPE_TOO_SHORT"
        return result
    digest = plain[2:34]
    body = plain[34:]
    expected_digest = hashlib.md5(body).hexdigest().encode()
    result["stored_md5"] = digest.decode("ascii", "replace")
    result["computed_md5"] = expected_digest.decode()
    if digest.lower() != expected_digest:
        result["failure_reason"] = "ENVELOPE_MD5_MISMATCH"
        return result
    fields = {}
    malformed = []
    duplicates = []
    for line in body.split(b"\n"):
        if b":" not in line:
            malformed.append(line.decode("utf-8", "replace"))
            continue
        key, value = line.split(b":", 1)
        name = key.decode("ascii", "replace")
        if name in fields:
            duplicates.append(name)
        fields[name] = value
    result["field_names"] = list(fields)
    result["malformed_lines"] = malformed
    result["duplicate_fields"] = duplicates
    for required in ("KEY", "DATA", "TIMESTAMP"):
        if required not in fields:
            result["failure_reason"] = f"FIELD_MISSING_{required}"
            return result
    try:
        token = base64.b64decode(fields["KEY"], validate=True)
        result["key_token_size"] = len(token)
    except Exception as error:
        result.update(failure_reason="KEY_BASE64_INVALID", error=str(error))
        return result
    try:
        payload = base64.b64decode(fields["DATA"], validate=True)
    except Exception as error:
        result.update(failure_reason="DATA_BASE64_INVALID", error=str(error))
        return result
    try:
        timestamp = int(fields["TIMESTAMP"])
    except Exception as error:
        result.update(failure_reason="TIMESTAMP_INVALID", error=str(error))
        return result
    result["embedded_timestamp"] = timestamp
    result["embedded_timestamp_utc"] = utc(timestamp)
    if mtime is not None:
        delta = mtime - timestamp
        result["mtime_delta_seconds"] = delta
        if abs(delta) > 10:
            result["failure_reason"] = "MTIME_MISMATCH"
            return result
    try:
        index_text = payload.decode("ascii")
        first_text, last_text = index_text.split(",", 1)
        first, last = int(first_text), int(last_text)
    except Exception as error:
        result.update(failure_reason="INDEX_PAYLOAD_INVALID", error=str(error), payload_hex=payload.hex())
        return result
    result.update(index_text=index_text, first_index=first, last_index=last)
    if first < -1 or last < -1 or first > last:
        result["failure_reason"] = "INDEX_RANGE_INVALID"
        return result
    result["readcontent_result"] = "ACCEPT"
    return result


def diagnose_path(path: Path):
    result = {"path": str(path), "failure_reason": None}
    try:
        info = path.stat()
    except FileNotFoundError:
        result["failure_reason"] = "ACCESS_NOT_FOUND"
        return result
    except PermissionError as error:
        result.update(failure_reason="ACCESS_PERMISSION_DENIED", error=str(error))
        return result
    except OSError as error:
        result.update(failure_reason="STAT_FAILED", errno=error.errno, error=str(error))
        return result
    result.update(
        mode=oct(stat.S_IMODE(info.st_mode)), uid=getattr(info, "st_uid", None),
        gid=getattr(info, "st_gid", None), mtime_ns=info.st_mtime_ns,
    )
    try:
        raw = path.read_bytes()
    except PermissionError as error:
        result.update(failure_reason="OPEN_PERMISSION_DENIED", error=str(error))
        return result
    except OSError as error:
        result.update(failure_reason="OPEN_OR_READ_FAILED", errno=error.errno, error=str(error))
        return result
    result.update(diagnose_bytes(raw, int(info.st_mtime)))
    return result


def adb_command(*args, check=True):
    return subprocess.run([str(ADB), *args], capture_output=True, text=True, errors="replace", check=check)


def snapshot_adb():
    stat_result = adb_command("shell", "su", "-c", "stat", "-c", "%s,%Y,%a,%u,%g", REMOTE_INDEX, check=False)
    if stat_result.returncode != 0:
        return {
            "path": REMOTE_INDEX,
            "failure_reason": "ACCESS_OR_STAT_FAILED",
            "stderr": stat_result.stderr.strip(),
            "stdout": stat_result.stdout.strip(),
        }
    size, mtime, mode, uid, gid = stat_result.stdout.strip().split(",")
    remote_copy = "/data/local/tmp/birzzle-index-diagnostic.bin"
    copy = adb_command("shell", "su", "-c", "cp", REMOTE_INDEX, remote_copy, check=False)
    if copy.returncode != 0:
        return {"path": REMOTE_INDEX, "failure_reason": "COPY_OPEN_READ_FAILED", "stderr": copy.stderr.strip()}
    adb_command("shell", "su", "-c", "chmod", "644", remote_copy)
    with tempfile.TemporaryDirectory() as temp:
        local = Path(temp) / INDEX_NAME
        pull = adb_command("pull", remote_copy, str(local), check=False)
        if pull.returncode != 0:
            return {"path": REMOTE_INDEX, "failure_reason": "ADB_PULL_FAILED", "stderr": pull.stderr.strip()}
        result = diagnose_bytes(local.read_bytes(), int(mtime))
    result.update(path=REMOTE_INDEX, stat_size=int(size), mode=mode, uid=int(uid), gid=int(gid))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?", type=Path)
    parser.add_argument("--adb", action="store_true")
    parser.add_argument("--watch-adb", type=float, metavar="SECONDS")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.watch_adb is not None:
        previous = None
        stream = args.output.open("a", encoding="utf-8") if args.output else None
        try:
            while True:
                result = snapshot_adb()
                signature = json.dumps(result, sort_keys=True)
                if signature != previous:
                    line = json.dumps({"observed_at": time.time(), **result})
                    print(line, flush=True)
                    if stream:
                        stream.write(line + "\n")
                        stream.flush()
                    previous = signature
                time.sleep(args.watch_adb)
        finally:
            if stream:
                stream.close()
    elif args.adb:
        result = snapshot_adb()
    elif args.path is not None:
        result = diagnose_path(args.path)
    else:
        parser.error("provide path, --adb, or --watch-adb")
    text = json.dumps(result, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")


if __name__ == "__main__":
    main()
