import hashlib
import json
import os
import re
import subprocess
import tarfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image

from reconstruct_response_pool import HISTORICAL_UID, reconstruct


ADB = str(Path("platform-tools-latest-windows/platform-tools/adb.exe"))
SERIAL = os.environ.get("ADB_SERIAL")
PACKAGE = "com.halfbrick.birzzlefever"
DATA = f"/data/data/{PACKAGE}"
FILES = f"{DATA}/files"
INDEX_NAME = "5f7d50ff681a65b10550a631e11a2ded"
INDEX = f"{FILES}/{INDEX_NAME}"
CHECKPOINT = Path(
    "device-snapshots/2026-08-30-unclamped-11-game-longrun/final-data.tar.gz"
)
REMOTE_CHECKPOINT = "/data/local/tmp/v22-stage-d-baseline.tar.gz"
OUTPUT = Path("native-patches/v22-first-read-recovery/stage-d-mid-session-faults")
OUTPUT.mkdir(parents=True, exist_ok=True)
EXPECTED_VALUES = ('"coin":"980800"', '"gem":"99870"', '"exp":"3810"')
FATAL_MARKERS = (
    "FATAL EXCEPTION",
    "Fatal signal",
    "SIGSEGV",
    f"ANR in {PACKAGE}",
    "Force finishing activity com.halfbrick.birzzlefever",
)
GAMESTART_REQUEST = "SAVE REQUEST:pocket.set"
GAMESTART_RESPONSE = '"extradata":"GameStart","message":"POCKET.SET"'
MAIN_MENU = '"message":"SCORE.RANKING"'


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [ADB]
    if SERIAL:
        command.extend(["-s", SERIAL])
    command.extend(args)
    result = None
    for attempt in range(5):
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            errors="replace",
        )
        if result.returncode == 0 or not check:
            return result
        time.sleep(2 * (attempt + 1))
    assert result is not None
    result.check_returncode()
    return result


def root(command: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return adb("shell", "su", "-c", command, check=check)


def logs() -> str:
    return adb("shell", "logcat", "-d", "-v", "time").stdout


def process_alive() -> bool:
    return bool(adb("shell", "pidof", PACKAGE, check=False).stdout.strip())


def fatal_markers(log: str) -> list[str]:
    return [marker for marker in FATAL_MARKERS if marker in log]


def remote_sha(path: str) -> str | None:
    result = root(f"busybox sha256sum {path}", check=False)
    fields = result.stdout.strip().split()
    if not fields or len(fields[0]) != 64:
        return None
    return fields[0].lower()


def remote_stat(path: str) -> dict | None:
    result = root(f"stat -c %s,%Y,%u,%g,%a {path}", check=False)
    fields = result.stdout.strip().split(",")
    if len(fields) != 5:
        return None
    size, mtime, uid, gid, mode = fields
    if not all(field.isdigit() for field in fields):
        return None
    return {
        "size": int(size),
        "mtime": int(mtime),
        "uid": int(uid),
        "gid": int(gid),
        "mode": int(mode),
    }


def touch_value(timestamp: int) -> str:
    offset = adb("shell", "date", "+%z").stdout.strip()
    sign = 1 if offset[0] == "+" else -1
    minutes = sign * (int(offset[1:3]) * 60 + int(offset[3:5]))
    local = datetime.fromtimestamp(timestamp, timezone(timedelta(minutes=minutes)))
    return local.strftime("%Y%m%d.%H%M%S")


def set_mtime(path: str, timestamp: int) -> None:
    root(f"touch -t {touch_value(timestamp)} {path}")


def restore_baseline() -> None:
    root(f"am force-stop {PACKAGE}", check=False)
    root(
        f"rm -rf {DATA}/cache {DATA}/databases {DATA}/files "
        f"{DATA}/shared_prefs {DATA}/app_webview {DATA}/.birzzle_seed_v1"
    )
    root(f"tar -xzf {REMOTE_CHECKPOINT} -C /")
    root(f"busybox chown -R {package_uid}:{package_uid} {DATA}")


def wait_for(marker: str, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    current = ""
    while time.monotonic() < deadline:
        time.sleep(1)
        current = logs()
        if marker in current:
            return current
        if fatal_markers(current):
            return current
        if not process_alive():
            return current
    return current


def ensure_awake_unlocked() -> None:
    power = adb("shell", "dumpsys", "power").stdout
    if "mScreenOn=false" in power:
        adb("shell", "input", "keyevent", "26")
        time.sleep(2)
    adb("shell", "input", "keyevent", "82", check=False)
    time.sleep(1)
    for _ in range(3):
        policy = adb("shell", "dumpsys", "window", "policy").stdout
        if "mShowingLockscreen=false" in policy:
            break
        adb(
            "shell", "input", "swipe",
            "540", "1650", "540", "250", "500",
            check=False,
        )
        time.sleep(2)
    else:
        raise SystemExit("could not dismiss Galaxy S4 keyguard")
    adb("shell", "input", "keyevent", "3", check=False)
    time.sleep(1)


def start_app_and_wait_for_menu(timeout: int = 75) -> str:
    ensure_awake_unlocked()
    adb("shell", "logcat", "-c")
    adb(
        "shell", "monkey", "-p", PACKAGE,
        "-c", "android.intent.category.LAUNCHER", "1",
    )
    return wait_for(MAIN_MENU, timeout)


def capture_screen(case_dir: Path, label: str) -> str:
    remote = f"/data/local/tmp/v22-stage-d-{case_dir.name}-{label}.png"
    local = case_dir / f"{label}.png"
    adb("shell", "screencap", "-p", remote)
    adb("pull", remote, str(local))
    image = Image.open(local).convert("RGB")
    center_total = sum(image.getpixel((540, 400)))
    if center_total >= 300:
        return "main-menu"
    if center_total <= 150:
        return "power-up"
    return f"unknown-{center_total}"


def snapshot_pool(case_dir: Path, label: str) -> dict:
    remote = f"/data/local/tmp/v22-stage-d-{case_dir.name}-{label}.tar.gz"
    local = case_dir / f"{label}-pool.tar.gz"
    root(f"tar -czf {remote} -C {FILES} .")
    root(f"busybox chmod 644 {remote}")
    adb("pull", remote, str(local))
    report = reconstruct(local, HISTORICAL_UID, 4096)
    (case_dir / f"{label}-pool.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def pool_is_consistent(report: dict, minimum_last: int) -> bool:
    state = report.get("index_state") or {}
    last = state.get("last_index")
    return bool(
        isinstance(last, int)
        and last >= minimum_last
        and report.get("classification") == "CONSISTENT"
        and report.get("contiguous_last") == last
        and report.get("highest_valid") == last
        and report.get("valid_record_count") == last + 1
        and not report.get("invalid_records")
        and not report.get("semantic_warnings")
    )


def pool_has_new_gamestart(report: dict) -> bool:
    if not pool_is_consistent(report, baseline_last + 1):
        return False
    records = report.get("records") or []
    return any(
        record.get("index", -1) > baseline_last
        and record.get("command") == "pocket.set"
        and "extradata=GameStart" in record.get("parameters", "")
        for record in records
    )


def apply_fault(kind: str, backup: str) -> dict:
    root(f"rm -f {backup}", check=False)
    if kind == "remove":
        root(f"mv {INDEX} {backup}")
    elif kind == "mtime":
        set_mtime(INDEX, baseline_mtime + 60)
    elif kind == "deny":
        root(f"busybox chmod 000 {INDEX}")
    elif kind == "zero":
        root(f"mv {INDEX} {backup}")
        root(f"cat /dev/null > {INDEX}")
        root(f"busybox chown {package_uid}:{package_uid} {INDEX}")
        root(f"busybox chmod 600 {INDEX}")
        set_mtime(INDEX, baseline_mtime)
    else:
        raise ValueError(kind)
    return {
        "index": remote_stat(INDEX),
        "index_sha256": remote_sha(INDEX),
        "backup": remote_stat(backup),
        "backup_sha256": remote_sha(backup),
    }


def restore_fault(kind: str, backup: str) -> str:
    stat = remote_stat(INDEX)
    sha = remote_sha(INDEX)
    action = ""
    if kind == "remove":
        if stat is None:
            root(f"mv {backup} {INDEX}")
            action = "restored-original-index"
        else:
            root(f"rm -f {backup}")
            action = "kept-atomic-replacement"
    elif kind == "zero":
        if stat is None or stat["size"] == 0:
            root(f"rm -f {INDEX}", check=False)
            root(f"mv {backup} {INDEX}")
            action = "restored-original-index"
        else:
            root(f"rm -f {backup}")
            action = "kept-atomic-replacement"
    elif kind == "deny":
        root(f"busybox chmod 600 {INDEX}")
        action = "restored-index-permissions"
    elif kind == "mtime":
        if sha == baseline_index_sha:
            set_mtime(INDEX, baseline_mtime)
            action = "restored-original-mtime"
        else:
            action = "kept-atomic-replacement"
    root(f"busybox chown {package_uid}:{package_uid} {INDEX}")
    root(f"busybox chmod 600 {INDEX}")
    root(f"rm -f {backup}", check=False)
    return action


with tarfile.open(CHECKPOINT, "r:gz") as archive:
    members = {
        Path(member.name).name: member
        for member in archive.getmembers()
        if member.isfile()
    }
    index_member = members[INDEX_NAME]
    baseline_index = archive.extractfile(index_member).read()
    baseline_mtime = int(index_member.mtime)
    request0_name = hashlib.md5(
        (HISTORICAL_UID + "REQUESTPOOL_0").encode()
    ).hexdigest()
    baseline_request0 = archive.extractfile(members[request0_name]).read()

baseline_index_sha = hashlib.sha256(baseline_index).hexdigest()
baseline_request0_sha = hashlib.sha256(baseline_request0).hexdigest()
baseline_last = 156
package_uid_text = root(f"stat -c %u {DATA}").stdout.strip()
if not package_uid_text.isdigit():
    raise SystemExit("could not determine package UID")
package_uid = int(package_uid_text)
adb("push", str(CHECKPOINT), REMOTE_CHECKPOINT)

cases = [
    {"name": "temporary-index-removal", "kind": "remove"},
    {"name": "index-mtime-plus-60", "kind": "mtime"},
    {"name": "temporary-index-access-denial", "kind": "deny"},
    {"name": "temporary-zero-length-index", "kind": "zero"},
]
selected_case = os.environ.get("STAGE_D_CASE")
if selected_case:
    cases = [case for case in cases if case["name"] == selected_case]
    if not cases:
        raise SystemExit(f"unknown STAGE_D_CASE: {selected_case}")

baseline = {
    "checkpoint": str(CHECKPOINT),
    "package_uid": package_uid,
    "index": "-1,156",
    "index_mtime": baseline_mtime,
    "index_sha256": baseline_index_sha,
    "request0_name": request0_name,
    "request0_sha256": baseline_request0_sha,
}
(OUTPUT / "baseline.json").write_text(
    json.dumps(baseline, indent=2) + "\n", encoding="utf-8"
)

results = []
adb("shell", "svc", "power", "stayon", "true", check=False)
ensure_awake_unlocked()
try:
    for case in cases:
        name = case["name"]
        kind = case["kind"]
        case_dir = OUTPUT / name
        case_dir.mkdir(parents=True, exist_ok=True)
        restore_baseline()
        startup_log = start_app_and_wait_for_menu()
        (case_dir / "startup.log").write_text(startup_log, encoding="utf-8")
        startup_ok = bool(
            MAIN_MENU in startup_log
            and all(value in startup_log for value in EXPECTED_VALUES)
            and process_alive()
            and not fatal_markers(startup_log)
        )
        startup_screen = capture_screen(case_dir, "main-menu")

        adb("shell", "input", "tap", "540", "1550")
        time.sleep(4)
        powerup_screen = capture_screen(case_dir, "power-up")
        if powerup_screen == "main-menu":
            adb("shell", "input", "tap", "540", "1550")
            time.sleep(4)
            powerup_screen = capture_screen(case_dir, "power-up-retry")
        powerup_ready = powerup_screen == "power-up"
        if not powerup_ready:
            raise SystemExit(f"{name}: power-up transition failed: {powerup_screen}")
        adb("shell", "logcat", "-c")
        backup = f"{INDEX}.stage-d-good"
        fault_state = apply_fault(kind, backup)
        (case_dir / "fault-state.json").write_text(
            json.dumps(fault_state, indent=2) + "\n", encoding="utf-8"
        )

        confirm_attempts = 1
        adb("shell", "input", "tap", "540", "1550")
        fault_window_log = wait_for("OFFLINE REQUEST: pocket.set", 5)
        confirm_retry_screen = None
        if "OFFLINE REQUEST: pocket.set" not in fault_window_log:
            confirm_retry_screen = capture_screen(case_dir, "confirm-retry-check")
            if confirm_retry_screen == "power-up":
                confirm_attempts = 2
                adb("shell", "input", "tap", "540", "1550")
                fault_window_log = wait_for("OFFLINE REQUEST: pocket.set", 5)
        invoked_during_fault = "OFFLINE REQUEST: pocket.set" in fault_window_log
        time.sleep(2)
        fault_window_log = logs()
        (case_dir / "fault-window.log").write_text(
            fault_window_log, encoding="utf-8"
        )
        restoration_action = restore_fault(kind, backup)

        recovery_log = wait_for(GAMESTART_RESPONSE, 45)
        (case_dir / "live-recovery.log").write_text(
            recovery_log, encoding="utf-8"
        )
        request_line = next(
            (
                line for line in recovery_log.splitlines()
                if GAMESTART_REQUEST in line and "extradata=GameStart" in line
            ),
            "",
        )
        response_line = next(
            (line for line in recovery_log.splitlines() if GAMESTART_RESPONSE in line),
            "",
        )
        coin_delta_match = re.search(r"&coin=(-?\d+)&", request_line)
        expected_coin = (
            980800 + int(coin_delta_match.group(1))
            if coin_delta_match else None
        )
        response_ok = bool(
            request_line
            and GAMESTART_RESPONSE in response_line
            and f'"coin":"{expected_coin}"' in response_line
            and '"gem":"99870"' in response_line
            and '"exp":"3810"' in response_line
        )
        live_alive = process_alive()
        live_fatal = fatal_markers(recovery_log)
        clamp_markers = [
            marker for marker in ("POCKET CLAMP", "INVENTORY CLAMP")
            if marker in recovery_log
        ]
        time.sleep(3)
        live_pool = snapshot_pool(case_dir, "live-recovered")
        live_request0_sha = remote_sha(f"{FILES}/{request0_name}")
        live_monotonic = pool_has_new_gamestart(live_pool)

        root(f"am force-stop {PACKAGE}", check=False)
        cold_log = start_app_and_wait_for_menu()
        (case_dir / "cold-restart.log").write_text(cold_log, encoding="utf-8")
        cold_ok = bool(
            MAIN_MENU in cold_log
            and '"gem":"99870"' in cold_log
            and '"exp":"3810"' in cold_log
            and process_alive()
            and not fatal_markers(cold_log)
        )
        cold_pool = snapshot_pool(case_dir, "cold-restart")
        cold_request0_sha = remote_sha(f"{FILES}/{request0_name}")
        live_last = live_pool.get("index_state", {}).get("last_index", -1)
        cold_last = cold_pool.get("index_state", {}).get("last_index", -1)
        cold_monotonic = pool_is_consistent(cold_pool, live_last)
        index_monotonic = cold_last >= live_last

        passed = bool(
            startup_ok
            and powerup_ready
            and invoked_during_fault
            and response_ok
            and live_alive
            and not live_fatal
            and not clamp_markers
            and live_monotonic
            and cold_ok
            and cold_monotonic
            and index_monotonic
            and live_request0_sha == baseline_request0_sha
            and cold_request0_sha == baseline_request0_sha
        )
        result = {
            "name": name,
            "kind": kind,
            "passed": passed,
            "startup_ok": startup_ok,
            "startup_screen": startup_screen,
            "powerup_screen": powerup_screen,
            "powerup_ready": powerup_ready,
            "confirm_attempts": confirm_attempts,
            "confirm_retry_screen": confirm_retry_screen,
            "game_start_invoked_during_fault": invoked_during_fault,
            "restoration_action": restoration_action,
            "response_ok": response_ok,
            "expected_response_coin": expected_coin,
            "live_alive": live_alive,
            "live_fatal_markers": live_fatal,
            "clamp_markers": clamp_markers,
            "live_monotonic": live_monotonic,
            "live_index": live_pool.get("index_state", {}).get("index_text"),
            "live_request0_sha256": live_request0_sha,
            "cold_restart_ok": cold_ok,
            "cold_monotonic": cold_monotonic,
            "cold_index": cold_pool.get("index_state", {}).get("index_text"),
            "cold_request0_sha256": cold_request0_sha,
            "index_monotonic_across_restart": index_monotonic,
        }
        results.append(result)
        (case_dir / "result.json").write_text(
            json.dumps(result, indent=2) + "\n", encoding="utf-8"
        )
        print(json.dumps(result), flush=True)
        root(f"am force-stop {PACKAGE}", check=False)
        restore_baseline()
        time.sleep(5)
finally:
    root(f"am force-stop {PACKAGE}", check=False)
    restore_baseline()
    adb("shell", "svc", "power", "stayon", "false", check=False)

summary = {
    "case_count": len(results),
    "all_passed": len(results) == len(cases) and all(result["passed"] for result in results),
    "results": results,
    "final_process_alive": process_alive(),
}
(OUTPUT / "results.json").write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(summary), flush=True)
if not summary["all_passed"]:
    raise SystemExit("stage D mid-session fault matrix failed")
