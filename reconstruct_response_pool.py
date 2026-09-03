import argparse
import hashlib
import json
import subprocess
import tarfile
import tempfile
from pathlib import Path

from analyze_birzzle_save import HISTORICAL_UID, decrypt2
from diagnose_response_index import diagnose_bytes


PACKAGE = "com.halfbrick.birzzlefever"
ADB = Path("platform-tools-latest-windows/platform-tools/adb.exe")


def request_name(index: int, uid: str):
    return hashlib.md5((uid + f"REQUESTPOOL_{index}").encode()).hexdigest()


def index_name(uid: str):
    return hashlib.md5((uid + "REQUESTPOOLINDEX").encode()).hexdigest()


def iter_source(path: Path):
    if tarfile.is_tarfile(path):
        with tarfile.open(path, "r:*") as archive:
            for member in archive.getmembers():
                if member.isfile():
                    stream = archive.extractfile(member)
                    if stream is not None:
                        yield Path(member.name).name, stream.read(), int(member.mtime)
        return
    for item in path.rglob("*"):
        if item.is_file():
            info = item.stat()
            yield item.name, item.read_bytes(), int(info.st_mtime)


def parse_request(raw: bytes, mtime: int):
    envelope = decrypt2(raw)
    if envelope is None:
        return {"valid": False, "failure_reason": "CCRYPT2_INVALID"}
    timestamp = envelope["timestamp"]
    delta = mtime - timestamp if timestamp is not None else None
    payload = envelope["decoded_data"]
    if payload is None:
        return {"valid": False, "failure_reason": "DATA_INVALID"}
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return {"valid": False, "failure_reason": "REQUEST_NOT_UTF8", "payload_hex": payload.hex()}
    command, separator, parameters = text.partition(",")
    return {
        "valid": envelope["digest_valid"] and timestamp is not None and abs(delta) <= 10 and bool(command),
        "digest_valid": envelope["digest_valid"],
        "embedded_timestamp": timestamp,
        "mtime": mtime,
        "mtime_delta": delta,
        "command": command,
        "parameters": parameters if separator else "",
        "text": text,
        "failure_reason": None if envelope["digest_valid"] and timestamp is not None and abs(delta) <= 10 and bool(command) else "ENVELOPE_OR_TIME_INVALID",
    }


def ranges(numbers):
    if not numbers:
        return []
    result = []
    start = previous = numbers[0]
    for number in numbers[1:]:
        if number != previous + 1:
            result.append([start, previous])
            start = number
        previous = number
    result.append([start, previous])
    return result


def reconstruct(path: Path, uid: str, max_scan: int):
    pool_index_name = index_name(uid)
    files = {name: (raw, mtime) for name, raw, mtime in iter_source(path)}
    records = []
    missing_after_seen = []
    seen_any = False
    for index in range(max_scan + 1):
        name = request_name(index, uid)
        if name not in files:
            if seen_any:
                missing_after_seen.append(index)
            continue
        seen_any = True
        raw, mtime = files[name]
        parsed = parse_request(raw, mtime)
        records.append({"index": index, "filename": name, "size": len(raw), **parsed})
    valid_indices = [record["index"] for record in records if record["valid"]]
    valid_ranges = ranges(valid_indices)
    contiguous_last = -1
    valid_set = set(valid_indices)
    while contiguous_last + 1 in valid_set:
        contiguous_last += 1

    index_state = None
    if pool_index_name in files:
        raw, mtime = files[pool_index_name]
        index_state = diagnose_bytes(raw, mtime)

    if not records and index_state is None:
        classification = "VIRGIN_NO_POOL"
    elif index_state is None:
        classification = "MATURE_INDEX_MISSING"
    elif index_state.get("readcontent_result") != "ACCEPT":
        classification = "INDEX_REJECTED"
    elif valid_indices and index_state["last_index"] < max(valid_indices):
        classification = "INDEX_STALE_OR_COLLAPSED"
    elif index_state["last_index"] > contiguous_last:
        classification = "INDEX_REFERENCES_MISSING_OR_INVALID_RECORDS"
    else:
        classification = "CONSISTENT"

    semantic_warnings = []
    if records:
        by_index = {record["index"]: record for record in records}
        if 0 in by_index and 1 in by_index:
            zero = by_index[0]
            one = by_index[1]
            if zero.get("embedded_timestamp", 0) > one.get("embedded_timestamp", 0):
                semantic_warnings.append("REQUEST_0_NEWER_THAN_REQUEST_1_POSSIBLE_OVERWRITE")
        if index_state and index_state.get("last_index") == 0 and any(index > 0 for index in valid_indices):
            semantic_warnings.append("INDEX_ZERO_WITH_ORPHANED_HIGHER_RECORDS")

    recommendation = None
    if contiguous_last >= 0:
        recommendation = {
            "candidate_first": -1,
            "candidate_last": contiguous_last,
            "candidate_text": f"-1,{contiguous_last}",
            "read_only_only": True,
            "warning": "Validate semantic warnings and source a known-good request 0 before writing any repair.",
        }
    return {
        "source": str(path),
        "uid": uid,
        "index_filename": pool_index_name,
        "classification": classification,
        "index_state": index_state,
        "valid_record_ranges": valid_ranges,
        "contiguous_last": contiguous_last,
        "highest_valid": max(valid_indices) if valid_indices else None,
        "record_count": len(records),
        "valid_record_count": len(valid_indices),
        "invalid_records": [record for record in records if not record["valid"]],
        "semantic_warnings": semantic_warnings,
        "recommendation": recommendation,
        "records": records,
    }


def adb_snapshot():
    remote = "/data/local/tmp/birzzle-pool-readonly.tar.gz"
    command = [str(ADB), "shell", "su", "-c", "tar", "-czf", remote, "-C", f"/data/data/{PACKAGE}/files", "."]
    subprocess.run(command, check=True)
    subprocess.run([str(ADB), "shell", "su", "-c", "chmod", "644", remote], check=True)
    directory = tempfile.TemporaryDirectory()
    local = Path(directory.name) / "pool.tar.gz"
    subprocess.run([str(ADB), "pull", remote, str(local)], check=True)
    return directory, local


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", nargs="?", type=Path)
    parser.add_argument("--adb", action="store_true")
    parser.add_argument("--uid", default=HISTORICAL_UID)
    parser.add_argument("--max-index", type=int, default=4096)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    temporary = None
    if args.adb:
        temporary, source = adb_snapshot()
    elif args.source:
        source = args.source
    else:
        parser.error("provide source or --adb")
    try:
        result = reconstruct(source, args.uid, args.max_index)
    finally:
        if temporary:
            temporary.cleanup()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ("classification", "valid_record_ranges", "contiguous_last", "highest_valid", "semantic_warnings", "recommendation")}, indent=2))


if __name__ == "__main__":
    main()
