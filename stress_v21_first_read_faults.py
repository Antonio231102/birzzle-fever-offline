import base64
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

from datetime import datetime, timedelta, timezone
from Crypto.Cipher import AES

from diagnose_response_index import AES_KEY, INDEX_NAME, diagnose_bytes
from reconstruct_response_pool import HISTORICAL_UID, reconstruct


ADB = str(Path("platform-tools-latest-windows/platform-tools/adb.exe"))
SERIAL = os.environ.get("ADB_SERIAL")
PACKAGE = "com.halfbrick.birzzlefever"
DATA = f"/data/data/{PACKAGE}"
FILES = f"{DATA}/files"
INDEX = f"{FILES}/{INDEX_NAME}"
CHECKPOINT = Path("device-snapshots/2026-08-30-unclamped-11-game-longrun/final-data.tar.gz")
REMOTE_CHECKPOINT = "/data/local/tmp/v21-stage-c-baseline.tar.gz"
OUTPUT = Path("native-patches/v21-response-index-hardening/stage-c-first-read-faults")
OUTPUT.mkdir(parents=True, exist_ok=True)
EXPECTED_MARKERS = {
    "coin": '"coin":"980800"',
    "gem": '"gem":"99870"',
    "exp": '"exp":"3810"',
    "suri_level_10": '"ability":"10","itemid":"0"',
    "polo_owned": '"ability":"2","itemid":"2"',
    "ranking": '"message":"SCORE.RANKING"',
    "ranking_score": '"scorecurrent":"1017964"',
    "quests_nonempty": '"queststatus":[{',
}
FATAL_MARKERS = (
    "FATAL EXCEPTION",
    "Fatal signal",
    "SIGSEGV",
    f"ANR in {PACKAGE}",
    "Force finishing activity com.halfbrick.birzzlefever",
)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [ADB]
    if SERIAL:
        command.extend(["-s", SERIAL])
    command.extend(args)
    return subprocess.run(
        command,
        check=check,
        capture_output=True,
        text=True,
        errors="replace",
    )


def root(command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return adb("shell", "su", "-c", command, check=check)


def remote_sha(path: str) -> str | None:
    result = root(f"busybox sha256sum {path}", check=False)
    fields = result.stdout.strip().split()
    if (
        not fields
        or len(fields[0]) != 64
        or any(char not in "0123456789abcdef" for char in fields[0].lower())
    ):
        return None
    return fields[0].lower()


def remote_stat(path: str) -> dict | None:
    result = root(f"stat -c %s,%Y,%u,%g {path}", check=False)
    fields = result.stdout.strip().split(",")
    if len(fields) != 4 or not all(field.isdigit() for field in fields):
        return None
    size, mtime, uid, gid = fields
    return {"size": int(size), "mtime": int(mtime), "uid": int(uid), "gid": int(gid)}


def process_alive() -> bool:
    return any(PACKAGE in line for line in adb("shell", "ps").stdout.splitlines())


def logcat() -> str:
    return adb("shell", "logcat", "-d", "-v", "time").stdout


def fatal_markers(log: str) -> list[str]:
    return [marker for marker in FATAL_MARKERS if marker in log]


def poll(seconds: int) -> tuple[str, bool, bool]:
    deadline = time.monotonic() + seconds
    current = ""
    alive = False
    menu = False
    while time.monotonic() < deadline:
        time.sleep(1)
        current = logcat()
        alive = process_alive()
        menu = '"message":"SCORE.RANKING"' in current
        if menu or fatal_markers(current) or not alive:
            break
    return current, alive, menu


def touch_value(timestamp: int) -> str:
    offset = adb("shell", "date", "+%z").stdout.strip()
    sign = 1 if offset[0] == "+" else -1
    minutes = sign * (int(offset[1:3]) * 60 + int(offset[3:5]))
    local = datetime.fromtimestamp(timestamp, timezone(timedelta(minutes=minutes)))
    return local.strftime("%Y%m%d.%H%M%S")


def set_mtime(path: str, timestamp: int) -> None:
    root(f"touch -t {touch_value(timestamp)} {path}")


def install_file(remote_source: str, destination: str, mtime: int) -> None:
    root(f"cp {remote_source} {destination}")
    root(f"busybox chown {package_uid}:{package_uid} {destination}")
    root(f"busybox chmod 600 {destination}")
    set_mtime(destination, mtime)


def restore_baseline() -> None:
    root(f"am force-stop {PACKAGE}", check=False)
    root(
        f"rm -rf {DATA}/cache {DATA}/databases {DATA}/files "
        f"{DATA}/shared_prefs {DATA}/app_webview {DATA}/.birzzle_seed_v1"
    )
    root(f"tar -xzf {REMOTE_CHECKPOINT} -C /")
    root(f"busybox chown -R {package_uid}:{package_uid} {DATA}")


def snapshot_pool(case_name: str) -> dict:
    remote = f"/data/local/tmp/v21-stage-c-{case_name}-pool.tar.gz"
    local = OUTPUT / case_name / "recovered-pool.tar.gz"
    root(f"tar -czf {remote} -C {FILES} .")
    root(f"busybox chmod 644 {remote}")
    adb("pull", remote, str(local))
    report = reconstruct(local, HISTORICAL_UID, 4096)
    (OUTPUT / case_name / "recovered-pool.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def state_from_log(log: str) -> dict:
    return {name: marker in log for name, marker in EXPECTED_MARKERS.items()}


with tarfile.open(CHECKPOINT, "r:gz") as archive:
    members = {Path(member.name).name: member for member in archive.getmembers() if member.isfile()}
    good_index_member = members[INDEX_NAME]
    good_index = archive.extractfile(good_index_member).read()
    index_mtime = int(good_index_member.mtime)
    request0_name = hashlib.md5((HISTORICAL_UID + "REQUESTPOOL_0").encode()).hexdigest()
    request0 = archive.extractfile(members[request0_name]).read()
    request156_name = hashlib.md5((HISTORICAL_UID + "REQUESTPOOL_156").encode()).hexdigest()
    request156_member = members[request156_name]
    request156 = archive.extractfile(request156_member).read()
    request156_mtime = int(request156_member.mtime)

ciphertext = bytearray(base64.b64decode(good_index, validate=True))
invalid_padding = None
for mask in range(1, 256):
    candidate_cipher = ciphertext.copy()
    candidate_cipher[-1] ^= mask
    candidate = base64.b64encode(candidate_cipher)
    if diagnose_bytes(candidate, index_mtime).get("failure_reason") == "PKCS7_PADDING_INVALID":
        invalid_padding = candidate
        break
if invalid_padding is None:
    raise SystemExit("could not construct deterministic invalid-padding index")

padded = AES.new(AES_KEY, AES.MODE_ECB).decrypt(bytes(ciphertext))
padding = padded[-1]
plain = bytearray(padded[:-padding])
plain[2] = ord("0") if plain[2] != ord("0") else ord("1")
mutated_padded = bytes(plain) + bytes([padding]) * padding
wrong_md5 = base64.b64encode(AES.new(AES_KEY, AES.MODE_ECB).encrypt(mutated_padded))

variants = {
    "zero-length-index": b"",
    "truncated-base64": good_index[:-1],
    "invalid-aes-padding": invalid_padding,
    "wrong-envelope-md5": wrong_md5,
}
expected_variant_reasons = {
    "zero-length-index": "EMPTY_FILE",
    "truncated-base64": "OUTER_BASE64_INVALID",
    "invalid-aes-padding": "PKCS7_PADDING_INVALID",
    "wrong-envelope-md5": "ENVELOPE_MD5_MISMATCH",
}
for name, raw in variants.items():
    reason = diagnose_bytes(raw, index_mtime).get("failure_reason")
    if reason != expected_variant_reasons[name]:
        raise SystemExit(f"{name}: generated {reason}, expected {expected_variant_reasons[name]}")
    (OUTPUT / f"{name}.bin").write_bytes(raw)

(OUTPUT / "good-index.bin").write_bytes(good_index)
(OUTPUT / "good-request-156.bin").write_bytes(request156)

package_uid = int(root(f"stat -c %u {DATA}").stdout.strip())
adb("push", str(CHECKPOINT), REMOTE_CHECKPOINT)
remote_good_index = "/data/local/tmp/v21-stage-c-good-index.bin"
remote_request156 = "/data/local/tmp/v21-stage-c-good-request-156.bin"
adb("push", str(OUTPUT / "good-index.bin"), remote_good_index)
adb("push", str(OUTPUT / "good-request-156.bin"), remote_request156)
remote_variants = {}
for name in variants:
    remote = f"/data/local/tmp/v21-stage-c-{name}.bin"
    adb("push", str(OUTPUT / f"{name}.bin"), remote)
    remote_variants[name] = remote

cases = [
    {"name": "mtime-plus-10", "kind": "mtime", "delta": 10, "expect_wait": False},
    {"name": "mtime-plus-11", "kind": "mtime", "delta": 11, "expect_wait": False},
    {"name": "mtime-plus-60", "kind": "mtime", "delta": 60, "expect_wait": False},
    {"name": "missing-index", "kind": "missing-index", "expect_wait": True},
    {"name": "zero-length-index", "kind": "variant", "expect_wait": True},
    {"name": "truncated-base64", "kind": "variant", "expect_wait": True},
    {"name": "invalid-aes-padding", "kind": "variant", "expect_wait": True},
    {"name": "wrong-envelope-md5", "kind": "variant", "expect_wait": True},
    {"name": "index-missing-record", "kind": "missing-record", "expect_wait": True},
]

baseline = {
    "index_name": INDEX_NAME,
    "index_mtime": index_mtime,
    "index_sha256": hashlib.sha256(good_index).hexdigest(),
    "request0_name": request0_name,
    "request0_sha256": hashlib.sha256(request0).hexdigest(),
    "request156_name": request156_name,
    "request156_sha256": hashlib.sha256(request156).hexdigest(),
    "package_uid": package_uid,
}
(OUTPUT / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")

results = []
adb("shell", "input", "keyevent", "224")
adb("shell", "input", "keyevent", "82")
adb("shell", "input", "swipe", "540", "1600", "540", "400", "500")
adb("shell", "svc", "power", "stayon", "true")
try:
    for case in cases:
        name = case["name"]
        case_dir = OUTPUT / name
        case_dir.mkdir(exist_ok=True)
        prior_result_path = case_dir / "result.json"
        if prior_result_path.exists():
            prior_result = json.loads(prior_result_path.read_text(encoding="utf-8"))
            if prior_result.get("passed"):
                results.append(prior_result)
                print(json.dumps({"name": name, "resumed": True, "passed": True}), flush=True)
                continue
        restore_baseline()

        injected_diagnostic = None
        if case["kind"] == "mtime":
            injected_mtime = index_mtime + case["delta"]
            set_mtime(INDEX, injected_mtime)
            injected_diagnostic = diagnose_bytes(good_index, injected_mtime)
        elif case["kind"] == "missing-index":
            root(f"rm -f {INDEX}")
            injected_diagnostic = {"failure_reason": "ACCESS_NOT_FOUND"}
        elif case["kind"] == "variant":
            install_file(remote_variants[name], INDEX, index_mtime)
            injected_diagnostic = diagnose_bytes(variants[name], index_mtime)
        elif case["kind"] == "missing-record":
            root(f"rm -f {FILES}/{request156_name}")
            injected_diagnostic = {
                "failure_reason": "INDEX_REFERENCES_MISSING_RECORD",
                "missing_index": 156,
                "missing_filename": request156_name,
            }
        else:
            raise AssertionError(case["kind"])

        injected = {
            "diagnostic": injected_diagnostic,
            "index_stat": remote_stat(INDEX),
            "index_sha256": remote_sha(INDEX),
            "request0_sha256": remote_sha(f"{FILES}/{request0_name}"),
            "request156_sha256": remote_sha(f"{FILES}/{request156_name}"),
        }
        (case_dir / "injected.json").write_text(
            json.dumps(injected, indent=2) + "\n", encoding="utf-8"
        )

        adb("shell", "logcat", "-c")
        adb(
            "shell", "monkey", "-p", PACKAGE,
            "-c", "android.intent.category.LAUNCHER", "1",
        )
        started = time.monotonic()
        pre_recovery = None
        controlled_wait = None
        if case["expect_wait"]:
            pre_log, pre_alive, pre_menu = poll(35)
            controlled_wait = pre_alive and not pre_menu and not fatal_markers(pre_log)
            pre_recovery = {
                "seconds": round(time.monotonic() - started, 3),
                "process_alive": pre_alive,
                "main_menu": pre_menu,
                "controlled_wait": controlled_wait,
                "fatal_markers": fatal_markers(pre_log),
                "empty_quests": '"queststatus":[]' in pre_log,
                "sentinel_only_inventory": '"inven":[{"ability":"0","itemid":"","odr":"0","tid":"0"}]' in pre_log,
                "zero_pocket_response": (
                    '"message":"POCKET.GET"' in pre_log
                    and all(marker in pre_log for marker in ('"coin":"0"', '"exp":"0"', '"gem":"0"'))
                ),
                "save_requests": pre_log.count("SAVE REQUEST:"),
                "index_stat": remote_stat(INDEX),
                "index_sha256": remote_sha(INDEX),
                "request0_sha256": remote_sha(f"{FILES}/{request0_name}"),
            }
            (case_dir / "before-recovery.log").write_text(pre_log, encoding="utf-8")

            if case["kind"] == "missing-record":
                install_file(remote_request156, f"{FILES}/{request156_name}", request156_mtime)
            else:
                install_file(remote_good_index, INDEX, index_mtime)

            if controlled_wait:
                final_log, alive, menu = poll(75)
            else:
                final_log, alive, menu = pre_log, pre_alive, pre_menu
        else:
            final_log, alive, menu = poll(75)

        (case_dir / "launch.log").write_text(final_log, encoding="utf-8")
        root(f"am force-stop {PACKAGE}", check=False)
        if case["kind"] == "missing-record":
            install_file(remote_request156, f"{FILES}/{request156_name}", request156_mtime)
        else:
            install_file(remote_good_index, INDEX, index_mtime)

        report = snapshot_pool(name)
        state = state_from_log(final_log)
        integrity = {
            "classification": report["classification"],
            "index_text": report["index_state"].get("index_text") if report["index_state"] else None,
            "record_count": report["record_count"],
            "valid_record_count": report["valid_record_count"],
            "semantic_warnings": report["semantic_warnings"],
            "index_sha256": remote_sha(INDEX),
            "request0_sha256": remote_sha(f"{FILES}/{request0_name}"),
            "request156_sha256": remote_sha(f"{FILES}/{request156_name}"),
        }
        recovered_integrity = (
            integrity["classification"] == "CONSISTENT"
            and integrity["index_text"] == "-1,156"
            and integrity["record_count"] == 157
            and integrity["valid_record_count"] == 157
            and not integrity["semantic_warnings"]
            and integrity["index_sha256"] == baseline["index_sha256"]
            and integrity["request0_sha256"] == baseline["request0_sha256"]
            and integrity["request156_sha256"] == baseline["request156_sha256"]
        )
        pre_safe = True
        if pre_recovery is not None:
            pre_safe = (
                pre_recovery["controlled_wait"]
                and not pre_recovery["empty_quests"]
                and not pre_recovery["sentinel_only_inventory"]
                and not pre_recovery["zero_pocket_response"]
                and pre_recovery["save_requests"] == 0
                and pre_recovery["request0_sha256"] == baseline["request0_sha256"]
            )
        passed = (
            alive
            and menu
            and all(state.values())
            and not fatal_markers(final_log)
            and pre_safe
            and recovered_integrity
        )
        result = {
            "name": name,
            "passed": passed,
            "duration_seconds": round(time.monotonic() - started, 3),
            "process_alive_at_menu": alive,
            "main_menu": menu,
            "state": state,
            "fatal_markers": fatal_markers(final_log),
            "pre_recovery": pre_recovery,
            "integrity": integrity,
            "recovered_integrity": recovered_integrity,
        }
        results.append(result)
        (case_dir / "result.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        (OUTPUT / "results.json").write_text(
            json.dumps({"cases": results}, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps({
            "name": name,
            "passed": passed,
            "controlled_wait": controlled_wait,
            "main_menu": menu,
            "integrity": recovered_integrity,
        }), flush=True)
finally:
    root(f"am force-stop {PACKAGE}", check=False)
    restore_baseline()
    adb("shell", "svc", "power", "stayon", "false", check=False)

final_pool = snapshot_pool("final-restored-baseline")
summary = {
    "case_count": len(results),
    "all_passed": len(results) == len(cases) and all(result["passed"] for result in results),
    "final_baseline_classification": final_pool["classification"],
    "final_baseline_index": final_pool["index_state"].get("index_text") if final_pool["index_state"] else None,
    "final_process_alive": process_alive(),
}
(OUTPUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
print(json.dumps(summary), flush=True)
if not summary["all_passed"]:
    raise SystemExit("one or more stage C cases failed")
