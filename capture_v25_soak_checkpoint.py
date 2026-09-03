#!/usr/bin/env python3
"""Create a quiesced, read-only V25 Birzzle Fever soak checkpoint."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from analyze_birzzle_save import HISTORICAL_UID, analyze_entry, iter_source as iter_save_source
from decode_birzzle_profiles import (
    BIRZZLE_XOR_KEY,
    DEFAULT_SEED_KEY,
    EFFECTIVE_SEED_KEY,
    analyze_profile,
    decrypt_profile,
    encrypt_profile_image,
    iter_source as iter_profile_source,
    profile_spec,
)
from reconstruct_response_pool import index_name, reconstruct, request_name

SCRIPT_ROOT = Path(__file__).resolve().parent
PACKAGE = "com.halfbrick.birzzlefever"
DATA_PATH = f"/data/data/{PACKAGE}"
ADB = SCRIPT_ROOT / "platform-tools-latest-windows/platform-tools/adb.exe"
DEFAULT_SERIAL = os.environ.get("ADB_SERIAL")
DEFAULT_OUTPUT_ROOT = Path("v25-soak-checkpoints")
MAX_POOL_INDEX = 65535
LOGCAT_ENTRY_LIMIT = 5000
LOGCAT_CHARACTER_LIMIT = 8 * 1024 * 1024
METADATA_CHARACTER_LIMIT = 256 * 1024
FATAL_MARKERS = (
    "FATAL EXCEPTION",
    "Fatal signal",
    "SIGSEGV",
    f"ANR in {PACKAGE}",
    f"Force finishing activity {PACKAGE}",
)


class CaptureError(RuntimeError):
    """An actionable checkpoint-capture failure."""


class Adb:
    def __init__(self, executable: Path, serial: str | None):
        self.executable = executable
        self.serial = serial

    def run(self, *args: str, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess[str]:
        command = [str(self.executable)]
        if self.serial:
            command.extend(["-s", self.serial])
        command.extend(args)
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, errors="replace", timeout=timeout
            )
        except FileNotFoundError as error:
            raise CaptureError(f"ADB executable was not found: {self.executable}") from error
        except subprocess.TimeoutExpired as error:
            rendered = subprocess.list2cmdline(command)
            raise CaptureError(f"ADB command timed out after {timeout}s: {rendered}") from error
        if check and result.returncode != 0:
            rendered = subprocess.list2cmdline(command)
            stdout = result.stdout.strip()[-2000:]
            stderr = result.stderr.strip()[-2000:]
            raise CaptureError(
                f"ADB command failed ({result.returncode}): {rendered}\n"
                f"stdout: {stdout or '<empty>'}\nstderr: {stderr or '<empty>'}"
            )
        return result

    def root(
        self, command: str, *, check: bool = True, timeout: int = 120
    ) -> subprocess.CompletedProcess[str]:
        return self.run("shell", "su", "-c", command, check=check, timeout=timeout)


class ArtifactWriter:
    def __init__(self, checkpoint_dir: Path):
        self.checkpoint_dir = checkpoint_dir
        self.artifacts: dict[str, dict[str, Any]] = {}

    def _finish(self, key: str, relative_path: str, temporary: Path) -> Path:
        destination = self.checkpoint_dir / relative_path
        os.replace(temporary, destination)
        self.artifacts[key] = {
            "path": relative_path,
            "size": destination.stat().st_size,
            "sha256": sha256_path(destination),
        }
        return destination

    def bytes(self, key: str, relative_path: str, content: bytes) -> Path:
        temporary = self.checkpoint_dir / f".{relative_path}.{uuid.uuid4().hex}.tmp"
        temporary.write_bytes(content)
        return self._finish(key, relative_path, temporary)

    def text(self, key: str, relative_path: str, content: str) -> Path:
        return self.bytes(key, relative_path, content.encode("utf-8"))

    def json(self, key: str, relative_path: str, value: Any) -> Path:
        return self.text(
            key,
            relative_path,
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        )

    def copy(self, key: str, relative_path: str, source: Path) -> Path:
        temporary = self.checkpoint_dir / f".{relative_path}.{uuid.uuid4().hex}.tmp"
        try:
            shutil.copyfile(source, temporary)
        except OSError as error:
            temporary.unlink(missing_ok=True)
            raise CaptureError(f"could not copy lifetime log {source}: {error}") from error
        return self._finish(key, relative_path, temporary)

    def pulled(self, key: str, relative_path: str, temporary: Path) -> Path:
        return self._finish(key, relative_path, temporary)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quote_remote(value: str) -> str:
    return shlex.quote(value)


def require_text(result: subprocess.CompletedProcess[str], description: str) -> str:
    value = result.stdout.strip()
    if not value:
        raise CaptureError(f"device returned no {description}")
    return value


def bounded_text(text: str, maximum: int) -> str:
    if len(text) <= maximum:
        return text
    omitted = len(text) - maximum
    return f"[capture omitted {omitted} earlier characters]\n" + text[-maximum:]


def optional_shell_metadata(
    adb: Adb, *args: str, limit: int = METADATA_CHARACTER_LIMIT
) -> dict[str, Any]:
    result = adb.run("shell", *args, check=False)
    value: dict[str, Any] = {
        "returncode": result.returncode,
        "stdout": bounded_text(result.stdout, limit),
    }
    if result.stderr:
        value["stderr"] = bounded_text(result.stderr, limit)
    return value


def parse_scalar(value: str) -> Any:
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    try:
        return int(stripped)
    except ValueError:
        return stripped


def parse_battery(raw: str) -> dict[str, Any]:
    parsed: dict[str, Any] = {}
    for line in raw.splitlines():
        if ":" not in line:
            continue
        key, value = line.strip().split(":", 1)
        if key:
            parsed[key.replace(" ", "_")] = parse_scalar(value)
    return parsed


def process_snapshot(adb: Adb) -> dict[str, Any]:
    result = adb.run("shell", "ps")
    matching_lines: list[str] = []
    pids: list[int] = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if not fields:
            continue
        if not any(field == PACKAGE or field.startswith(f"{PACKAGE}:") for field in fields):
            continue
        matching_lines.append(line)
        numeric_fields = [int(field) for field in fields[1:] if field.isdigit()]
        if numeric_fields:
            pids.append(numeric_fields[0])
    return {
        "observed_at_utc": utc_now(),
        "running": bool(matching_lines),
        "pids": sorted(set(pids)),
        "ps_lines": matching_lines,
    }


def remote_sha256(adb: Adb, path: str) -> tuple[str | None, list[str]]:
    errors: list[str] = []
    quoted_path = quote_remote(path)
    for utility in ("sha256sum", "busybox sha256sum", "toybox sha256sum"):
        result = adb.root(f"{utility} {quoted_path}", check=False)
        candidate = result.stdout.strip().split()
        if candidate and re.fullmatch(r"[0-9a-fA-F]{64}", candidate[0]):
            return candidate[0].lower(), errors
        detail = (result.stderr or result.stdout).strip()[-500:]
        errors.append(f"{utility}: rc={result.returncode}: {detail or '<no output>'}")
    return None, errors


def collect_device_and_app(adb: Adb) -> tuple[dict[str, Any], dict[str, Any]]:
    state = require_text(adb.run("get-state"), "ADB device state")
    if state != "device":
        raise CaptureError(f"selected serial {adb.serial} is not ready (state={state!r})")

    root_identity = require_text(adb.root("id"), "root identity")
    if not re.search(r"(?:^|\s)uid=0(?:\D|$)", root_identity):
        raise CaptureError(f"su did not provide root on {adb.serial}: {root_identity!r}")

    model = require_text(adb.run("shell", "getprop", "ro.product.model"), "device model")
    android_release = require_text(
        adb.run("shell", "getprop", "ro.build.version.release"), "Android release"
    )
    boot_id = require_text(
        adb.run("shell", "cat", "/proc/sys/kernel/random/boot_id"), "boot identifier"
    )

    package_result = adb.run("shell", "pm", "path", PACKAGE)
    apk_paths = [
        line.removeprefix("package:").strip()
        for line in package_result.stdout.splitlines()
        if line.startswith("package:") and line.removeprefix("package:").strip()
    ]
    if not apk_paths:
        raise CaptureError(f"package {PACKAGE} is not installed or has no reported APK path")

    uid_text = adb.root(f"stat -c %u {quote_remote(DATA_PATH)}").stdout.strip()
    if not uid_text.isdigit():
        raise CaptureError(f"could not determine package UID from {DATA_PATH}: {uid_text!r}")

    installed_hashes: dict[str, str | None] = {}
    installed_hash_errors: dict[str, list[str]] = {}
    for apk_path in apk_paths:
        remote_hash, errors = remote_sha256(adb, apk_path)
        installed_hashes[apk_path] = remote_hash
        if remote_hash is None:
            installed_hash_errors[apk_path] = errors

    storage = optional_shell_metadata(adb, "df", "/data")
    battery_raw = optional_shell_metadata(adb, "dumpsys", "battery")
    battery = {**battery_raw, "values": parse_battery(str(battery_raw.get("stdout", "")))}
    network = {
        "airplane_mode": optional_shell_metadata(
            adb, "settings", "get", "global", "airplane_mode_on"
        ),
        "network_type": optional_shell_metadata(adb, "getprop", "gsm.network.type"),
        "operator": optional_shell_metadata(adb, "getprop", "gsm.operator.alpha"),
        "connectivity": optional_shell_metadata(adb, "dumpsys", "connectivity"),
    }
    device = {
        "serial": adb.serial,
        "model": model,
        "android_release": android_release,
        "boot_id": boot_id,
        "storage": storage,
        "battery": battery,
        "network": network,
    }
    primary_apk_hash = installed_hashes.get(apk_paths[0])
    app: dict[str, Any] = {
        "package": PACKAGE,
        "uid": int(uid_text),
        "data_path": DATA_PATH,
        "apk_paths": apk_paths,
        "installed_apk_sha256": primary_apk_hash,
        "installed_apk_sha256_by_path": installed_hashes,
    }
    if installed_hash_errors:
        app["installed_apk_hash_errors"] = installed_hash_errors
    return device, app


def capture_logcat(adb: Adb) -> str:
    result = adb.run(
        "logcat",
        "-d",
        "-v",
        "threadtime",
        "-t",
        str(LOGCAT_ENTRY_LIMIT),
        timeout=180,
    )
    content = result.stdout
    if result.stderr:
        content += "\n[adb logcat stderr]\n" + result.stderr
    return bounded_text(content, LOGCAT_CHARACTER_LIMIT)


def pull_quiesced_tar(adb: Adb, writer: ArtifactWriter) -> Path:
    remote = f"/data/local/tmp/birzzle-v25-soak-{uuid.uuid4().hex}.tar.gz"
    remote_q = quote_remote(remote)
    adb.root(
        f"tar -czf {remote_q} -C / {quote_remote(DATA_PATH.removeprefix('/'))}",
        timeout=600,
    )
    adb.root(f"chmod 0644 {remote_q}")

    temporary = writer.checkpoint_dir / f".app-data.tar.gz.{uuid.uuid4().hex}.pulling"
    pull = adb.run("pull", remote, str(temporary), check=False, timeout=900)
    if pull.returncode != 0 or not temporary.is_file():
        temporary.unlink(missing_ok=True)
        detail = (pull.stderr or pull.stdout).strip()[-2000:]
        raise CaptureError(
            f"failed to pull quiesced app-data tar; remote copy retained at {remote}: "
            f"rc={pull.returncode}: {detail or '<no output>'}"
        )
    if temporary.stat().st_size == 0:
        temporary.unlink(missing_ok=True)
        raise CaptureError(f"pulled app-data tar is empty; remote copy retained at {remote}")

    cleanup = adb.root(f"rm -f {remote_q}", check=False)
    if cleanup.returncode != 0:
        detail = (cleanup.stderr or cleanup.stdout).strip()[-2000:]
        temporary.unlink(missing_ok=True)
        raise CaptureError(
            f"pull succeeded but remote temporary tar cleanup failed at {remote}: "
            f"rc={cleanup.returncode}: {detail or '<no output>'}"
        )
    return writer.pulled("app_data_tar", "app-data.tar.gz", temporary)


def analyze_pool(tar_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    report = reconstruct(tar_path, HISTORICAL_UID, MAX_POOL_INDEX)
    report["source"] = "app-data.tar.gz"
    report["max_index_scanned"] = MAX_POOL_INDEX

    hashes_by_name: dict[str, str] = {}
    for source_path, raw, _mtime in iter_save_source(tar_path):
        hashes_by_name[Path(source_path).name] = hashlib.sha256(raw).hexdigest()

    numbered_hashes: dict[str, str] = {}
    for record in report["records"]:
        digest = hashes_by_name.get(record["filename"])
        if digest is None:
            raise CaptureError(
                f"pool analyzer reported {record['filename']} but it was not found in the tar"
            )
        record["sha256"] = digest
        numbered_hashes[str(record["index"])] = digest

    index_state = report.get("index_state")
    index_sha256 = hashes_by_name.get(index_name(HISTORICAL_UID))
    request0_sha256 = hashes_by_name.get(request_name(0, HISTORICAL_UID))
    highest_valid = report.get("highest_valid")
    tail_sha256 = numbered_hashes.get(str(highest_valid)) if highest_valid is not None else None
    report["numbered_record_sha256"] = numbered_hashes
    report["index_sha256"] = index_sha256
    report["request0_sha256"] = request0_sha256
    report["tail_sha256"] = tail_sha256

    summary = {
        "classification": report["classification"],
        "index_text": index_state.get("index_text") if index_state else None,
        "last_index": index_state.get("last_index") if index_state else None,
        "record_count": report["record_count"],
        "valid_record_count": report["valid_record_count"],
        "contiguous_last": report["contiguous_last"],
        "highest_valid": report["highest_valid"],
        "semantic_warnings": report["semantic_warnings"],
        "index_sha256": index_sha256,
        "request0_sha256": request0_sha256,
        "tail_sha256": tail_sha256,
        "record_sha256": numbered_hashes,
        "response_filename_identity": HISTORICAL_UID,
    }
    return report, summary


def analyze_profiles(tar_path: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for name, raw, mtime in iter_profile_source(tar_path):
        spec = profile_spec(name)
        if spec is None:
            raise CaptureError(f"profile decoder selected unknown profile {name}")
        load_size, _role = spec
        padded, plain = decrypt_profile(raw, load_size)
        if encrypt_profile_image(padded) != raw:
            raise CaptureError(f"SEED round-trip mismatch while decoding {name}")
        records.append(analyze_profile(name, plain, padded, mtime))
    return {
        "source": "app-data.tar.gz",
        "default_seed_key_hex": DEFAULT_SEED_KEY.hex(),
        "xor_key_ascii": BIRZZLE_XOR_KEY.decode("ascii"),
        "effective_seed_key_hex": EFFECTIVE_SEED_KEY.hex(),
        "records": records,
    }


def analyze_save(tar_path: Path) -> dict[str, Any]:
    records = [analyze_entry(name, raw, mtime) for name, raw, mtime in iter_save_source(tar_path)]
    counts: dict[str, int] = {}
    for record in records:
        kind = record["kind"]
        counts[kind] = counts.get(kind, 0) + 1
    return {"source": "app-data.tar.gz", "counts": counts, "records": records}


def find_fatal_markers(log_sources: Iterable[str]) -> list[str]:
    combined = "\n".join(log_sources)
    return [marker for marker in FATAL_MARKERS if marker in combined]

def find_file_fatal_markers(path: Path) -> list[str]:
    marker_bytes = {marker: marker.encode("utf-8") for marker in FATAL_MARKERS}
    found: set[str] = set()
    overlap = max(len(value) for value in marker_bytes.values()) - 1
    carry = b""
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                window = carry + block
                found.update(
                    marker for marker, value in marker_bytes.items() if value in window
                )
                carry = window[-overlap:]
    except OSError as error:
        raise CaptureError(f"could not scan copied lifetime log {path}: {error}") from error
    return [marker for marker in FATAL_MARKERS if marker in found]


def validate_pool(report: dict[str, Any]) -> None:
    classification = report["classification"]
    if classification not in {"CONSISTENT", "VIRGIN_NO_POOL"}:
        raise CaptureError(f"response pool is inconsistent: classification={classification}")
    invalid_records = report.get("invalid_records", [])
    if invalid_records:
        indices = [str(record.get("index")) for record in invalid_records]
        raise CaptureError(f"response pool contains invalid records at indices {', '.join(indices)}")
    warnings = report.get("semantic_warnings", [])
    if warnings:
        raise CaptureError(f"response pool has semantic warnings: {', '.join(warnings)}")


def validate_label(label: str) -> str:
    if not label or label in {".", ".."}:
        raise CaptureError("label must be a non-empty directory name")
    if Path(label).name != label or "/" in label or "\\" in label:
        raise CaptureError("label must be one directory name, not a path")
    return label


def run_capture(args: argparse.Namespace) -> Path:
    started_at = utc_now()
    label = validate_label(args.label)
    output_root = args.output_root.expanduser()
    checkpoint_dir = output_root / label
    output_root.mkdir(parents=True, exist_ok=True)
    try:
        checkpoint_dir.mkdir()
    except FileExistsError as error:
        raise CaptureError(f"checkpoint destination already exists: {checkpoint_dir}") from error
    except OSError as error:
        raise CaptureError(f"could not create checkpoint destination {checkpoint_dir}: {error}") from error

    writer = ArtifactWriter(checkpoint_dir)
    adb = Adb(ADB, args.serial)
    device, app = collect_device_and_app(adb)
    before_quiesce = process_snapshot(adb)
    force_stop_started = utc_now()
    adb.root(f"am force-stop {quote_remote(PACKAGE)}")
    time.sleep(0.5)
    after_quiesce = process_snapshot(adb)
    if after_quiesce["running"]:
        raise CaptureError(f"{PACKAGE} is still running after force-stop: {after_quiesce['ps_lines']}")
    quiesced_at = utc_now()
    process = {
        "before_quiesce": before_quiesce,
        "force_stop": {
            "started_at_utc": force_stop_started,
            "completed_at_utc": quiesced_at,
            "succeeded": True,
        },
        "after_quiesce": after_quiesce,
    }

    logcat_text = capture_logcat(adb)
    writer.text("logcat", "whole-device-logcat.txt", logcat_text)
    fatal_marker_set = set(find_fatal_markers([logcat_text]))
    if args.log_source is not None:
        source = args.log_source.expanduser()
        if not source.is_file():
            raise CaptureError(f"lifetime log source is not a file: {source}")
        lifetime_path = writer.copy("lifetime_log", "lifetime.log", source)
        fatal_marker_set.update(find_file_fatal_markers(lifetime_path))

    tar_path = pull_quiesced_tar(adb, writer)
    try:
        pool_report, pool_summary = analyze_pool(tar_path)
    except (CaptureError, SystemExit):
        raise
    except Exception as error:
        raise CaptureError(f"response-pool analysis failed: {error}") from error
    writer.json("pool_report", "response-pool-report.json", pool_report)

    try:
        profile_report = analyze_profiles(tar_path)
    except (CaptureError, SystemExit):
        raise
    except Exception as error:
        raise CaptureError(f"profile analysis failed: {error}") from error
    writer.json("profile_report", "profile-report.json", profile_report)

    try:
        save_report = analyze_save(tar_path)
    except (CaptureError, SystemExit):
        raise
    except Exception as error:
        raise CaptureError(f"generic save analysis failed: {error}") from error
    writer.json("save_report", "save-report.json", save_report)

    fatal_markers = [marker for marker in FATAL_MARKERS if marker in fatal_marker_set]
    validate_pool(pool_report)
    if fatal_markers:
        raise CaptureError(f"fatal log markers present: {', '.join(fatal_markers)}")

    manifest = {
        "schema_version": 1,
        "label": label,
        "time": {
            "started_utc": started_at,
            "quiesced_utc": quiesced_at,
            "completed_utc": utc_now(),
        },
        "device": device,
        "app": app,
        "process": process,
        "artifacts": writer.artifacts,
        "pool": pool_summary,
        "fatal_markers": fatal_markers,
    }
    manifest_temporary = checkpoint_dir / f".manifest.json.{uuid.uuid4().hex}.tmp"
    manifest_temporary.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    os.replace(manifest_temporary, checkpoint_dir / "manifest.json")
    return checkpoint_dir / "manifest.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Force-stop Birzzle Fever, capture its complete app data, and emit a "
            "read-only analyzed V25 soak checkpoint. No in-game input is performed."
        )
    )
    parser.add_argument("--label", required=True, help="single-directory checkpoint label")
    parser.add_argument(
        "--output-root",
        type=Path,
        default=DEFAULT_OUTPUT_ROOT,
        help=f"checkpoint parent directory (default: {DEFAULT_OUTPUT_ROOT})",
    )
    parser.add_argument(
        "--serial",
        default=DEFAULT_SERIAL,
        help="ADB device serial (default: ADB_SERIAL or adb's sole connected device)",
    )
    parser.add_argument(
        "--log-source",
        type=Path,
        help="optional lifetime log to copy into the checkpoint and scan for fatal markers",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = run_capture(args)
    except CaptureError as error:
        print(f"capture failed: {error}", file=sys.stderr)
        return 1
    except SystemExit as error:
        detail = error.code if isinstance(error.code, str) else f"status {error.code}"
        print(f"capture failed: analyzer exited: {detail}", file=sys.stderr)
        return 1
    except Exception as error:
        print(f"capture failed unexpectedly: {type(error).__name__}: {error}", file=sys.stderr)
        return 1
    print(json.dumps({"manifest": str(manifest)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
