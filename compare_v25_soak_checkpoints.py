import argparse
import hashlib
import json
import sys
import tarfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from analyze_birzzle_save import HISTORICAL_UID


SCHEMA_VERSION = 1
REQUIRED_ARTIFACTS = {
    "app_data_tar",
    "pool_report",
    "profile_report",
    "save_report",
    "logcat",
}
POOL_SUMMARY_FIELDS = {
    "classification",
    "index_text",
    "last_index",
    "record_count",
    "valid_record_count",
    "contiguous_last",
    "highest_valid",
    "semantic_warnings",
    "index_sha256",
    "request0_sha256",
    "tail_sha256",
    "record_sha256",
}
CHECK_NAMES = (
    "before_manifest_schema",
    "after_manifest_schema",
    "before_artifact_hashes",
    "after_artifact_hashes",
    "before_pool_report",
    "after_pool_report",
    "before_pool_tar_records",
    "after_pool_tar_records",
    "before_pool_summary",
    "after_pool_summary",
    "before_pool_consistent",
    "after_pool_consistent",
    "before_pool_contiguous",
    "after_pool_contiguous",
    "before_no_invalid_records",
    "after_no_invalid_records",
    "before_no_semantic_warnings",
    "after_no_semantic_warnings",
    "before_no_fatal_markers",
    "after_no_fatal_markers",
    "same_package",
    "installed_apk_hash_compatible",
    "last_nondecreasing",
    "request_zero_unchanged",
    "prior_records_unchanged",
)


class InputError(Exception):
    pass


@dataclass(frozen=True)
class Artifact:
    name: str
    path: Path
    size: int
    sha256: str


@dataclass
class Checkpoint:
    manifest: dict[str, Any]
    report: dict[str, Any]
    records: dict[int, dict[str, Any]]
    record_sha256: dict[int, str]
    last_index: int
    summary: dict[str, Any]


class Results:
    def __init__(self) -> None:
        self.checks = {name: False for name in CHECK_NAMES}
        self.failures: list[str] = []
        self._reported: set[str] = set()

    def mark(self, name: str, passed: bool, messages: list[str] | None = None) -> None:
        self.checks[name] = bool(passed)
        if passed:
            return
        self._reported.add(name)
        for message in messages or ["failed"]:
            self.failures.append(f"{name}: {message}")

    def finish(self) -> None:
        for name, passed in self.checks.items():
            if not passed and name not in self._reported:
                self.failures.append(f"{name}: not completed because a required input was unavailable")


def is_int(value: Any) -> bool:
    return type(value) is int


def is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path, description: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise InputError(f"cannot read {description} {path}: {error}") from error
    if not isinstance(value, dict):
        raise InputError(f"{description} {path} is not a JSON object")
    return value


def resolve_artifact(manifest_path: Path, name: str, value: Any) -> Artifact:
    if not isinstance(value, dict):
        raise InputError(f"artifact {name!r} is not an object")
    relative = value.get("path")
    size = value.get("size")
    recorded_hash = value.get("sha256")
    if not isinstance(relative, str) or not relative:
        raise InputError(f"artifact {name!r} has no path")
    relative_path = Path(relative)
    if relative_path.is_absolute():
        raise InputError(f"artifact {name!r} path is not checkpoint-relative")
    root = manifest_path.parent.resolve()
    path = (root / relative_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise InputError(f"artifact {name!r} path escapes its checkpoint") from error
    if not is_int(size) or size < 0:
        raise InputError(f"artifact {name!r} has an invalid size")
    if not is_sha256(recorded_hash):
        raise InputError(f"artifact {name!r} has an invalid SHA-256")
    return Artifact(name=name, path=path, size=size, sha256=recorded_hash.lower())


def validate_manifest(manifest_path: Path, manifest: dict[str, Any]) -> tuple[dict[str, Artifact], list[str]]:
    errors: list[str] = []
    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}")
    if not isinstance(manifest.get("label"), str) or not manifest.get("label"):
        errors.append("label must be a non-empty string")
    for key in ("time", "device", "app", "process", "artifacts", "pool"):
        if not isinstance(manifest.get(key), dict):
            errors.append(f"{key} must be an object")
    if not isinstance(manifest.get("fatal_markers"), list):
        errors.append("fatal_markers must be an array")
    app = manifest.get("app")
    if isinstance(app, dict):
        if not isinstance(app.get("package"), str) or not app.get("package"):
            errors.append("app.package must be a non-empty string")
        apk_hash = app.get("installed_apk_sha256")
        if apk_hash is not None and not is_sha256(apk_hash):
            errors.append("app.installed_apk_sha256 is invalid")
    pool = manifest.get("pool")
    if isinstance(pool, dict):
        missing_fields = sorted(POOL_SUMMARY_FIELDS - pool.keys())
        if missing_fields:
            errors.append("pool is missing fields: " + ", ".join(missing_fields))
    artifacts: dict[str, Artifact] = {}
    values = manifest.get("artifacts")
    if isinstance(values, dict):
        missing_artifacts = sorted(REQUIRED_ARTIFACTS - values.keys())
        if missing_artifacts:
            errors.append("artifacts is missing: " + ", ".join(missing_artifacts))
        for name in sorted(values):
            try:
                artifacts[name] = resolve_artifact(manifest_path, name, values[name])
            except InputError as error:
                errors.append(str(error))
    return artifacts, errors


def verify_artifacts(artifacts: dict[str, Artifact]) -> list[str]:
    errors: list[str] = []
    for name in sorted(artifacts):
        artifact = artifacts[name]
        try:
            actual_size = artifact.path.stat().st_size
        except OSError as error:
            errors.append(f"artifact {name!r} is unavailable: {error}")
            continue
        if not artifact.path.is_file():
            errors.append(f"artifact {name!r} is not a regular file")
            continue
        if actual_size != artifact.size:
            errors.append(f"artifact {name!r} size is {actual_size}, expected {artifact.size}")
        try:
            actual_hash = sha256_file(artifact.path)
        except OSError as error:
            errors.append(f"cannot hash artifact {name!r}: {error}")
            continue
        if actual_hash != artifact.sha256:
            errors.append(f"artifact {name!r} SHA-256 is {actual_hash}, expected {artifact.sha256}")
    return errors


def expected_request_filename(index: int) -> str:
    value = HISTORICAL_UID + f"REQUESTPOOL_{index}"
    return hashlib.md5(value.encode()).hexdigest()


def expected_index_filename() -> str:
    return hashlib.md5((HISTORICAL_UID + "REQUESTPOOLINDEX").encode()).hexdigest()


def validate_pool_report(report: dict[str, Any]) -> tuple[dict[int, dict[str, Any]], int, dict[str, Any], dict[str, list[str]]]:
    errors = {
        "report": [],
        "consistent": [],
        "contiguous": [],
        "invalid": [],
        "warnings": [],
    }
    if report.get("uid") != HISTORICAL_UID:
        errors["report"].append("uid does not match analyze_birzzle_save.HISTORICAL_UID")
    if report.get("index_filename") != expected_index_filename():
        errors["report"].append("index_filename does not match the historical UID")

    index_state = report.get("index_state")
    if not isinstance(index_state, dict):
        errors["report"].append("index_state is not an object")
        index_state = {}
    last_index = index_state.get("last_index")
    if not is_int(last_index) or last_index < 0:
        errors["report"].append("index_state.last_index is not a non-negative integer")
        last_index = -1
    index_text = index_state.get("index_text")
    expected_text = f"-1,{last_index}" if last_index >= 0 else None
    if index_text != expected_text:
        errors["contiguous"].append(f"index text is {index_text!r}, expected {expected_text!r}")
    if index_state.get("first_index") != -1:
        errors["contiguous"].append("index_state.first_index is not -1")

    raw_records = report.get("records")
    if not isinstance(raw_records, list):
        errors["report"].append("records is not an array")
        raw_records = []
    records: dict[int, dict[str, Any]] = {}
    for position, record in enumerate(raw_records):
        if not isinstance(record, dict):
            errors["report"].append(f"record at position {position} is not an object")
            continue
        index = record.get("index")
        if not is_int(index) or index < 0:
            errors["report"].append(f"record at position {position} has an invalid index")
            continue
        if index in records:
            errors["report"].append(f"record index {index} is duplicated")
            continue
        filename = record.get("filename")
        if filename != expected_request_filename(index):
            errors["report"].append(f"record {index} filename does not match its historical UID-derived name")
        records[index] = record

    expected_indices = list(range(last_index + 1)) if last_index >= 0 else []
    actual_indices = sorted(records)
    if actual_indices != expected_indices:
        errors["contiguous"].append(f"record indices are {actual_indices!r}, expected {expected_indices!r}")
    expected_count = last_index + 1 if last_index >= 0 else 0
    for field in ("record_count", "valid_record_count"):
        if report.get(field) != expected_count:
            errors["contiguous"].append(f"{field} is {report.get(field)!r}, expected {expected_count}")
    for field in ("contiguous_last", "highest_valid"):
        if report.get(field) != last_index:
            errors["contiguous"].append(f"{field} is {report.get(field)!r}, expected {last_index}")
    expected_ranges = [[0, last_index]] if last_index >= 0 else []
    if report.get("valid_record_ranges") != expected_ranges:
        errors["contiguous"].append(
            f"valid_record_ranges is {report.get('valid_record_ranges')!r}, expected {expected_ranges!r}"
        )

    if report.get("classification") != "CONSISTENT":
        errors["consistent"].append(
            f"classification is {report.get('classification')!r}, expected 'CONSISTENT'"
        )
    if report.get("invalid_records") != []:
        errors["invalid"].append("invalid_records is not empty")
    for index, record in sorted(records.items()):
        if record.get("valid") is not True:
            errors["invalid"].append(f"record {index} is not valid")
        if record.get("digest_valid") is not True:
            errors["invalid"].append(f"record {index} does not have a valid digest")
    if report.get("semantic_warnings") != []:
        errors["warnings"].append("semantic_warnings is not empty")

    derived = {
        "classification": report.get("classification"),
        "index_text": index_text,
        "last_index": last_index,
        "record_count": report.get("record_count"),
        "valid_record_count": report.get("valid_record_count"),
        "contiguous_last": report.get("contiguous_last"),
        "highest_valid": report.get("highest_valid"),
        "semantic_warnings": report.get("semantic_warnings"),
    }
    return records, last_index, derived, errors


def hash_pool_members(
    archive_path: Path,
    report: dict[str, Any],
    records: dict[int, dict[str, Any]],
) -> tuple[dict[int, str], str, list[str]]:
    errors: list[str] = []
    index_filename = report.get("index_filename")
    filename_to_index = {
        record["filename"]: index
        for index, record in sorted(records.items())
        if isinstance(record.get("filename"), str)
    }
    if len(filename_to_index) != len(records):
        errors.append("pool records do not have unique filenames")
    expected_names = set(filename_to_index)
    if isinstance(index_filename, str):
        expected_names.add(index_filename)

    hashes: dict[str, str] = {}
    duplicates: set[str] = set()
    try:
        with tarfile.open(archive_path, "r:*") as archive:
            for member in archive:
                if not member.isfile():
                    continue
                name = PurePosixPath(member.name.replace("\\", "/")).name
                if name not in expected_names:
                    continue
                if name in hashes:
                    duplicates.add(name)
                    continue
                stream = archive.extractfile(member)
                if stream is None:
                    errors.append(f"cannot read archive member {member.name!r}")
                    continue
                digest = hashlib.sha256()
                for block in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(block)
                hashes[name] = digest.hexdigest()
    except (OSError, tarfile.TarError) as error:
        errors.append(f"cannot read app-data tar: {error}")

    if duplicates:
        errors.append("app-data tar has duplicate pool basenames: " + ", ".join(sorted(duplicates)))
    missing = sorted(expected_names - hashes.keys())
    if missing:
        errors.append("app-data tar is missing pool files: " + ", ".join(missing))
    record_hashes = {
        index: hashes[filename]
        for filename, index in filename_to_index.items()
        if filename in hashes
    }
    for index, digest in sorted(record_hashes.items()):
        recorded = records[index].get("sha256")
        if recorded is not None and recorded != digest:
            errors.append(f"pool report record {index} SHA-256 does not match the app-data tar")
    reported_hashes = report.get("numbered_record_sha256")
    if reported_hashes is not None:
        expected_reported_hashes = {
            str(index): digest for index, digest in sorted(record_hashes.items())
        }
        if reported_hashes != expected_reported_hashes:
            errors.append("pool report numbered_record_sha256 does not match the app-data tar")
    index_hash = hashes.get(index_filename, "")
    if report.get("index_sha256", index_hash) != index_hash:
        errors.append("pool report index_sha256 does not match the app-data tar")
    if report.get("request0_sha256", record_hashes.get(0)) != record_hashes.get(0):
        errors.append("pool report request0_sha256 does not match the app-data tar")
    report_tail = record_hashes.get(max(record_hashes)) if record_hashes else None
    if report.get("tail_sha256", report_tail) != report_tail:
        errors.append("pool report tail_sha256 does not match the app-data tar")
    return record_hashes, index_hash, errors


def validate_pool_summary(
    pool: dict[str, Any],
    derived: dict[str, Any],
    record_hashes: dict[int, str],
    index_hash: str,
    last_index: int,
) -> list[str]:
    errors: list[str] = []
    for field, expected in derived.items():
        if pool.get(field) != expected:
            errors.append(f"pool.{field} does not match the pool report")
    response_identity = pool.get("response_filename_identity")
    if response_identity is not None and response_identity != HISTORICAL_UID:
        errors.append(
            "pool.response_filename_identity does not match "
            "analyze_birzzle_save.HISTORICAL_UID"
        )


    expected_record_hashes = {str(index): digest for index, digest in sorted(record_hashes.items())}
    recorded_hashes = pool.get("record_sha256")
    if not isinstance(recorded_hashes, dict):
        errors.append("pool.record_sha256 is not an object")
    else:
        normalized: dict[str, str] = {}
        for key, value in recorded_hashes.items():
            if not isinstance(key, str) or not key.isdigit() or not is_sha256(value):
                errors.append("pool.record_sha256 contains an invalid entry")
                continue
            normalized[str(int(key))] = value.lower()
        if normalized != expected_record_hashes:
            errors.append("pool.record_sha256 does not match the app-data tar")

    if pool.get("index_sha256") != index_hash:
        errors.append("pool.index_sha256 does not match the app-data tar")
    if pool.get("request0_sha256") != record_hashes.get(0):
        errors.append("pool.request0_sha256 does not match the app-data tar")
    if pool.get("tail_sha256") != record_hashes.get(last_index):
        errors.append("pool.tail_sha256 does not match the app-data tar")
    return errors


def checkpoint_summary(
    manifest_path: Path,
    manifest: dict[str, Any] | None = None,
    derived: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manifest = manifest or {}
    app = manifest.get("app") if isinstance(manifest.get("app"), dict) else {}
    return {
        "manifest": str(manifest_path),
        "label": manifest.get("label"),
        "time": manifest.get("time"),
        "package": app.get("package"),
        "installed_apk_sha256": app.get("installed_apk_sha256"),
        "pool": derived,
        "fatal_markers": manifest.get("fatal_markers"),
    }


def inspect_checkpoint(role: str, manifest_path: Path, results: Results) -> Checkpoint | None:
    try:
        manifest = load_json(manifest_path, f"{role} manifest")
    except InputError as error:
        results.mark(f"{role}_manifest_schema", False, [str(error)])
        return None

    artifacts, schema_errors = validate_manifest(manifest_path, manifest)
    results.mark(f"{role}_manifest_schema", not schema_errors, schema_errors)
    if schema_errors:
        return None

    artifact_errors = verify_artifacts(artifacts)
    results.mark(f"{role}_artifact_hashes", not artifact_errors, artifact_errors)
    if artifact_errors:
        return None


    try:
        report = load_json(artifacts["pool_report"].path, f"{role} pool report")
    except InputError as error:
        results.mark(f"{role}_pool_report", False, [str(error)])
        return None

    records, last_index, derived, pool_errors = validate_pool_report(report)
    results.mark(f"{role}_pool_report", not pool_errors["report"], pool_errors["report"])
    results.mark(f"{role}_pool_consistent", not pool_errors["consistent"], pool_errors["consistent"])
    results.mark(f"{role}_pool_contiguous", not pool_errors["contiguous"], pool_errors["contiguous"])
    results.mark(f"{role}_no_invalid_records", not pool_errors["invalid"], pool_errors["invalid"])
    results.mark(f"{role}_no_semantic_warnings", not pool_errors["warnings"], pool_errors["warnings"])

    record_hashes, index_hash, tar_errors = hash_pool_members(
        artifacts["app_data_tar"].path, report, records
    )
    results.mark(f"{role}_pool_tar_records", not tar_errors, tar_errors)
    summary_errors = validate_pool_summary(
        manifest["pool"], derived, record_hashes, index_hash, last_index
    )
    results.mark(f"{role}_pool_summary", not summary_errors, summary_errors)

    fatal_markers = manifest.get("fatal_markers")
    fatal_errors = [] if fatal_markers == [] else ["fatal_markers is not empty"]
    results.mark(f"{role}_no_fatal_markers", not fatal_errors, fatal_errors)

    return Checkpoint(
        manifest=manifest,
        report=report,
        records=records,
        record_sha256=record_hashes,
        last_index=last_index,
        summary=checkpoint_summary(manifest_path, manifest, derived),
    )


def compare_checkpoints(before: Checkpoint, after: Checkpoint, results: Results) -> dict[str, Any]:
    before_app = before.manifest["app"]
    after_app = after.manifest["app"]
    same_package = before_app.get("package") == after_app.get("package")
    results.mark("same_package", same_package, ["checkpoint package names differ"])

    before_apk = before_app.get("installed_apk_sha256")
    after_apk = after_app.get("installed_apk_sha256")
    compatible_apk = not (before_apk and after_apk) or before_apk.lower() == after_apk.lower()
    results.mark("installed_apk_hash_compatible", compatible_apk, ["installed APK SHA-256 values differ"])

    monotonic = after.last_index >= before.last_index
    results.mark(
        "last_nondecreasing",
        monotonic,
        [f"last index decreased from {before.last_index} to {after.last_index}"],
    )
    request_zero_unchanged = (
        0 in before.record_sha256
        and 0 in after.record_sha256
        and before.record_sha256[0] == after.record_sha256[0]
    )
    results.mark("request_zero_unchanged", request_zero_unchanged, ["request zero is absent or changed"])

    changed_prior = [
        index
        for index in range(before.last_index + 1)
        if before.record_sha256.get(index) != after.record_sha256.get(index)
    ]
    results.mark(
        "prior_records_unchanged",
        not changed_prior,
        ["prior record SHA-256 changed or disappeared at indices: " + ", ".join(map(str, changed_prior))]
        if changed_prior
        else [],
    )

    added_indices = list(range(before.last_index + 1, after.last_index + 1)) if monotonic else []
    commands = Counter()
    for index in added_indices:
        command = after.records.get(index, {}).get("command")
        if isinstance(command, str) and command:
            commands[command] += 1
    return {
        "range": [added_indices[0], added_indices[-1]] if added_indices else None,
        "count": len(added_indices),
        "command_frequencies": {name: commands[name] for name in sorted(commands)},
    }


def build_result(before_path: Path, after_path: Path) -> dict[str, Any]:
    results = Results()
    before = inspect_checkpoint("before", before_path, results)
    after = inspect_checkpoint("after", after_path, results)
    added_records = {"range": None, "count": 0, "command_frequencies": {}}
    if before is not None and after is not None:
        added_records = compare_checkpoints(before, after, results)
    results.finish()
    return {
        "schema_version": SCHEMA_VERSION,
        "passed": all(results.checks.values()),
        "checks": results.checks,
        "failures": results.failures,
        "before": before.summary if before is not None else checkpoint_summary(before_path),
        "after": after.summary if after is not None else checkpoint_summary(after_path),
        "added_records": added_records,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two quiesced V25 soak checkpoint manifests without device access."
    )
    parser.add_argument("before_manifest", type=Path)
    parser.add_argument("after_manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    try:
        result = build_result(args.before_manifest, args.after_manifest)
    except Exception as error:
        result = {
            "schema_version": SCHEMA_VERSION,
            "passed": False,
            "checks": {name: False for name in CHECK_NAMES},
            "failures": [f"unexpected comparator error: {type(error).__name__}: {error}"],
            "before": checkpoint_summary(args.before_manifest),
            "after": checkpoint_summary(args.after_manifest),
            "added_records": {"range": None, "count": 0, "command_frequencies": {}},
        }

    output_text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    try:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output_text, encoding="utf-8")
    except OSError as error:
        print(f"cannot write result {args.output}: {error}", file=sys.stderr)
        return 1
    print(output_text, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
