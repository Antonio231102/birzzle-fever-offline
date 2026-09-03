import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

from PIL import Image

from diagnose_response_index import diagnose_bytes
from reconstruct_response_pool import HISTORICAL_UID, reconstruct


ADB = str(Path("platform-tools-latest-windows/platform-tools/adb.exe"))
SERIAL = os.environ.get("ADB_SERIAL")
PACKAGE = "com.halfbrick.birzzlefever"
DATA = f"/data/data/{PACKAGE}"
FILES = f"{DATA}/files"
INDEX_NAME = "5f7d50ff681a65b10550a631e11a2ded"
INDEX = f"{FILES}/{INDEX_NAME}"
TEMP_INDEX = f"{INDEX}.tmp"
CHECKPOINT = Path(
    "device-snapshots/2026-08-30-unclamped-11-game-longrun/final-data.tar.gz"
)
PRODUCTION_APK = Path(
    "native-patches/v23-request-first-index/"
    "BirzzleFever-1.1.2-v23-request-first-index.apk"
)
PRODUCTION_LIBRARY = Path("native-patches/v23-request-first-index/libef2d.so")
OUTPUT = Path("native-patches/v23-request-first-index/stage-e-interrupted-writes")
DIAGNOSTICS = OUTPUT / "diagnostics"
REMOTE_CHECKPOINT = "/data/local/tmp/v23-stage-e-baseline.tar.gz"
REMOTE_PRODUCTION_LIBRARY = "/data/local/tmp/v23-stage-e-production-libef2d.so"
PRODUCTION_LIBRARY_SHA = "a66f91a1e498c325d4f9ef8e78df5bd4f71d4fce44b6fbcb5d51425eb3e83145"
BASE_INDEX_SHA = "c75e925c83ce92d7157f77306b123eb0e7e5944f3926e0d623edb55ed8813d07"
BASE_REQUEST0_SHA = "5f86e21d92f615c0854eadc08b7872857e280d92f516053d7c4577eba59ef0a2"
MAIN_MENU = '"message":"SCORE.RANKING"'
GAMESTART_RESPONSE = '"extradata":"GameStart","message":"POCKET.SET"'
UPLOAD_RESPONSE = '"extradata":"UploadPocket","message":"POCKET.SET"'
FATAL_MARKERS = (
    "FATAL EXCEPTION", "Fatal signal", "SIGSEGV", f"ANR in {PACKAGE}",
    "Force finishing activity com.halfbrick.birzzlefever",
)
OUTPUT.mkdir(parents=True, exist_ok=True)

REQUEST0_NAME = hashlib.md5(
    (HISTORICAL_UID + "REQUESTPOOL_0").encode()
).hexdigest()
REQUEST157_NAME = hashlib.md5(
    (HISTORICAL_UID + "REQUESTPOOL_157").encode()
).hexdigest()
REQUEST157 = f"{FILES}/{REQUEST157_NAME}"

BOUNDARY_CASES = {
    "kill-before-index-write": {
        "diagnostic": "after-numbered-before-index",
        "boundary": "numbered-complete-before-index",
    },
    "kill-before-atomic-rename": {
        "diagnostic": "after-temp-before-rename",
        "boundary": "temp-complete-before-rename",
    },
    "kill-immediately-after-rename": {
        "diagnostic": "immediately-after-rename",
        "boundary": "rename-complete-before-directory-fsync",
    },
}


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    command = [ADB]
    if SERIAL:
        command.extend(["-s", SERIAL])
    command.extend(args)
    result = None
    for attempt in range(5):
        result = subprocess.run(
            command, check=False,
            capture_output=True, text=True, errors="replace",
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


def remote_stat(path: str) -> dict | None:
    result = root(f"stat -c %s,%Y,%u,%g,%a {path}", check=False)
    fields = result.stdout.strip().split(",")
    if len(fields) != 5 or not all(field.isdigit() for field in fields):
        return None
    return dict(zip(
        ("size", "mtime", "uid", "gid", "mode"),
        map(int, fields),
    ))


def remote_sha(path: str) -> str | None:
    fields = root(f"busybox sha256sum {path}", check=False).stdout.strip().split()
    return fields[0].lower() if fields and len(fields[0]) == 64 else None


def fatal_markers(log: str) -> list[str]:
    return [marker for marker in FATAL_MARKERS if marker in log]


def wait_for(marker: str, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    current = ""
    while time.monotonic() < deadline:
        time.sleep(1)
        current = logs()
        if marker in current or fatal_markers(current) or not process_alive():
            return current
    return current


def ensure_awake_unlocked() -> None:
    if "mScreenOn=false" in adb("shell", "dumpsys", "power").stdout:
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
            "540", "1650", "540", "250", "500", check=False,
        )
        time.sleep(2)
    else:
        raise SystemExit("could not dismiss Galaxy S4 keyguard")
    adb("shell", "input", "keyevent", "3", check=False)
    time.sleep(1)


def capture_screen(case_dir: Path, label: str) -> str:
    remote = f"/data/local/tmp/v22-stage-e-{case_dir.name}-{label}.png"
    local = case_dir / f"{label}.png"
    adb("shell", "screencap", "-p", remote)
    adb("pull", remote, str(local))
    total = sum(Image.open(local).convert("RGB").getpixel((540, 400)))
    if total >= 300:
        return "main-menu"
    if total <= 150:
        return "power-up"
    return f"unknown-{total}"


def start_app(timeout: int = 75) -> str:
    ensure_awake_unlocked()
    adb("shell", "logcat", "-c")
    adb(
        "shell", "monkey", "-p", PACKAGE,
        "-c", "android.intent.category.LAUNCHER", "1",
    )
    return wait_for(MAIN_MENU, timeout)


def enter_powerup(case_dir: Path) -> dict:
    main = capture_screen(case_dir, "main-menu")
    adb("shell", "input", "tap", "540", "1550")
    time.sleep(4)
    powerup = capture_screen(case_dir, "power-up")
    attempts = 1
    if powerup == "main-menu":
        attempts = 2
        adb("shell", "input", "tap", "540", "1550")
        time.sleep(4)
        powerup = capture_screen(case_dir, "power-up-retry")
    if powerup != "power-up":
        raise SystemExit(f"power-up transition failed: {powerup}")
    return {"main_screen": main, "powerup_screen": powerup, "play_tap_attempts": attempts}


def fresh_install(apk: Path) -> int:
    root(f"am force-stop {PACKAGE}", check=False)
    adb("uninstall", PACKAGE, check=False)
    result = adb("install", str(apk))
    if "Success" not in result.stdout:
        raise SystemExit(f"install failed: {result.stdout} {result.stderr}")
    uid_text = root(f"stat -c %u {DATA}").stdout.strip()
    if not uid_text.isdigit():
        raise SystemExit("could not determine installed package UID")
    return int(uid_text)


def restore_baseline(uid: int) -> None:
    root(f"am force-stop {PACKAGE}", check=False)
    root(
        f"rm -rf {DATA}/cache {DATA}/databases {DATA}/files "
        f"{DATA}/shared_prefs {DATA}/app_webview {DATA}/.birzzle_seed_v1"
    )
    root(f"tar -xzf {REMOTE_CHECKPOINT} -C /")
    root(f"busybox chown -R {uid}:{uid} {DATA}")


def installed_library_path() -> str:
    package_lines = [
        line.strip()
        for line in adb("shell", "pm", "path", PACKAGE).stdout.splitlines()
        if line.strip().startswith("package:/data/app/")
    ]
    if len(package_lines) != 1:
        raise SystemExit(f"unexpected package paths: {package_lines}")
    base = package_lines[0].removeprefix("package:/data/app/").removesuffix(".apk")
    return f"/data/app-lib/{base}/libef2d.so"


def activate_production_library() -> str:
    destination = installed_library_path()
    stat = remote_stat(destination)
    if stat is None:
        raise SystemExit("installed diagnostic library missing")
    root(f"cp {REMOTE_PRODUCTION_LIBRARY} {destination}")
    root(f"busybox chown {stat['uid']}:{stat['gid']} {destination}")
    root(f"busybox chmod {stat['mode']} {destination}")
    if remote_sha(destination) != PRODUCTION_LIBRARY_SHA:
        raise SystemExit("production library swap failed")
    return destination


def pull_root_file(remote: str, local: Path) -> bytes | None:
    stat = remote_stat(remote)
    if stat is None:
        return None
    staging = f"/data/local/tmp/v22-stage-e-pull-{local.name}"
    root(f"cp {remote} {staging}")
    root(f"busybox chmod 644 {staging}")
    adb("pull", staging, str(local))
    return local.read_bytes()


def diagnose_remote_index(remote: str, case_dir: Path, label: str) -> dict | None:
    stat = remote_stat(remote)
    if stat is None:
        return None
    raw = pull_root_file(remote, case_dir / f"{label}.bin")
    report = diagnose_bytes(raw, stat["mtime"])
    report["stat"] = stat
    report["sha256"] = hashlib.sha256(raw).hexdigest()
    return report


def snapshot_pool(case_dir: Path, label: str) -> dict:
    remote = f"/data/local/tmp/v22-stage-e-{case_dir.name}-{label}.tar.gz"
    local = case_dir / f"{label}-pool.tar.gz"
    root(f"tar -czf {remote} -C {FILES} .")
    root(f"busybox chmod 644 {remote}")
    adb("pull", remote, str(local))
    report = reconstruct(local, HISTORICAL_UID, 4096)
    (case_dir / f"{label}-pool.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    return report


def snapshot_data(case_dir: Path, label: str) -> None:
    remote = f"/data/local/tmp/v23-stage-e-{case_dir.name}-{label}-data.tar.gz"
    local = case_dir / f"{label}-data.tar.gz"
    root(f"tar -czf {remote} -C / data/data/{PACKAGE}")
    root(f"busybox chmod 644 {remote}")
    adb("pull", remote, str(local))


def boundary_state(case_dir: Path) -> dict:
    return {
        "process_alive": process_alive(),
        "index": diagnose_remote_index(INDEX, case_dir, "boundary-index"),
        "temp_index": diagnose_remote_index(TEMP_INDEX, case_dir, "boundary-temp-index"),
        "request157": remote_stat(REQUEST157),
        "request157_sha256": remote_sha(REQUEST157),
        "request0_sha256": remote_sha(f"{FILES}/{REQUEST0_NAME}"),
    }


def boundary_reached(case_name: str, state: dict) -> bool:
    index = state["index"]
    temp = state["temp_index"]
    request = state["request157"]
    if not state["process_alive"] or request is None:
        return False
    if case_name == "kill-before-index-write":
        return bool(index and index.get("index_text") == "-1,156" and temp is None)
    if case_name == "kill-before-atomic-rename":
        return bool(
            index and index.get("index_text") == "-1,156"
            and temp and temp.get("index_text") == "-1,157"
        )
    return bool(index and index.get("index_text") == "-1,157" and temp is None)


def run_boundary_case(case_name: str, config: dict) -> dict:
    case_dir = OUTPUT / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
    diagnostic_apk = (
        DIAGNOSTICS / config["diagnostic"] /
        f"BirzzleFever-1.1.2-v23-stage-e-{config['diagnostic']}.apk"
    )
    uid = fresh_install(diagnostic_apk)
    restore_baseline(uid)
    installed_diag_sha = remote_sha(installed_library_path())
    startup = start_app()
    (case_dir / "startup.log").write_text(startup, encoding="utf-8")
    startup_ok = MAIN_MENU in startup and not fatal_markers(startup)
    visual = enter_powerup(case_dir)
    adb("shell", "logcat", "-c")
    adb("shell", "input", "tap", "540", "1550")

    deadline = time.monotonic() + 30
    state = {}
    while time.monotonic() < deadline:
        time.sleep(1)
        state = boundary_state(case_dir)
        if boundary_reached(case_name, state):
            break
    reached = boundary_reached(case_name, state)
    pre_kill_log = logs()
    (case_dir / "boundary.log").write_text(pre_kill_log, encoding="utf-8")
    (case_dir / "boundary-state.json").write_text(
        json.dumps(state, indent=2) + "\n", encoding="utf-8"
    )
    response_before_kill = GAMESTART_RESPONSE in pre_kill_log
    root(f"am force-stop {PACKAGE}", check=False)
    killed = not process_alive()
    interrupted_pool = snapshot_pool(case_dir, "interrupted")
    snapshot_data(case_dir, "interrupted")
    record157 = next(
        (record for record in interrupted_pool.get("records", []) if record.get("index") == 157),
        None,
    )
    record157_valid = bool(
        record157 and record157.get("valid")
        and record157.get("command") == "pocket.set"
        and "extradata=GameStart" in record157.get("parameters", "")
    )

    active_library = activate_production_library()
    recovery = start_app()
    (case_dir / "recovery.log").write_text(recovery, encoding="utf-8")
    recovery_pool = snapshot_pool(case_dir, "recovery")
    recovery_index = recovery_pool.get("index_state") or {}
    recovery_last = recovery_index.get("last_index")
    minimum_last = 157 if case_name == "kill-immediately-after-rename" else 156
    valid_recovery_index = bool(
        recovery_index.get("readcontent_result") == "ACCEPT"
        and isinstance(recovery_last, int)
        and recovery_last >= minimum_last
    )
    recovery_ok = bool(
        MAIN_MENU in recovery
        and '"gem":"99870"' in recovery
        and '"exp":"3810"' in recovery
        and not fatal_markers(recovery)
        and process_alive()
        and valid_recovery_index
    )
    request0_unchanged = remote_sha(f"{FILES}/{REQUEST0_NAME}") == BASE_REQUEST0_SHA
    no_clamps = "POCKET CLAMP" not in recovery and "INVENTORY CLAMP" not in recovery
    passed = bool(
        startup_ok and visual["main_screen"] == "main-menu"
        and visual["powerup_screen"] == "power-up"
        and reached and not response_before_kill and killed and record157_valid
        and state.get("request0_sha256") == BASE_REQUEST0_SHA
        and remote_sha(active_library) == PRODUCTION_LIBRARY_SHA
        and recovery_ok and request0_unchanged and no_clamps
    )
    result = {
        "name": case_name,
        "boundary": config["boundary"],
        "passed": passed,
        "package_uid": uid,
        "installed_diagnostic_library_sha256": installed_diag_sha,
        "startup_ok": startup_ok,
        **visual,
        "boundary_reached": reached,
        "response_delivered_before_kill": response_before_kill,
        "process_killed": killed,
        "interrupted_classification": interrupted_pool.get("classification"),
        "interrupted_index": interrupted_pool.get("index_state", {}).get("index_text"),
        "record157_valid_gamestart": record157_valid,
        "production_library_activated": remote_sha(active_library) == PRODUCTION_LIBRARY_SHA,
        "recovery_ok": recovery_ok,
        "recovery_classification": recovery_pool.get("classification"),
        "recovery_index": recovery_index.get("index_text"),
        "request0_unchanged": request0_unchanged,
        "no_clamps": no_clamps,
    }
    (case_dir / "result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


def run_completed_game_case() -> dict:
    case_name = "shutdown-after-completed-game"
    case_dir = OUTPUT / case_name
    case_dir.mkdir(parents=True, exist_ok=True)
    uid = fresh_install(PRODUCTION_APK)
    restore_baseline(uid)
    startup = start_app()
    (case_dir / "startup.log").write_text(startup, encoding="utf-8")
    visual = enter_powerup(case_dir)
    adb("shell", "logcat", "-c")
    adb("shell", "input", "tap", "540", "1550")
    game_log = wait_for(GAMESTART_RESPONSE, 45)
    game_started = GAMESTART_RESPONSE in game_log
    coordinates = [(250, 700), (540, 850), (820, 700), (300, 1100), (760, 1200)]
    deadline = time.monotonic() + 120
    completed_log = game_log
    index = 0
    while game_started and time.monotonic() < deadline:
        if UPLOAD_RESPONSE in completed_log or fatal_markers(completed_log) or not process_alive():
            break
        x, y = coordinates[index % len(coordinates)]
        index += 1
        adb("shell", "input", "tap", str(x), str(y), check=False)
        time.sleep(2)
        completed_log = logs()
    completed = UPLOAD_RESPONSE in completed_log
    (case_dir / "completed-game.log").write_text(completed_log, encoding="utf-8")
    completed_pool = snapshot_pool(case_dir, "completed-before-shutdown")
    completed_index = completed_pool.get("index_state") or {}
    request0_before = remote_sha(f"{FILES}/{REQUEST0_NAME}")
    root(f"am force-stop {PACKAGE}", check=False)
    killed = not process_alive()
    recovery = start_app()
    (case_dir / "recovery.log").write_text(recovery, encoding="utf-8")
    recovery_pool = snapshot_pool(case_dir, "recovery")
    request0_after = remote_sha(f"{FILES}/{REQUEST0_NAME}")
    before_last = completed_index.get("last_index")
    after_state = recovery_pool.get("index_state") or {}
    after_last = after_state.get("last_index")
    valid_previous_or_new = bool(
        completed_index.get("readcontent_result") == "ACCEPT"
        and after_state.get("readcontent_result") == "ACCEPT"
        and isinstance(before_last, int) and isinstance(after_last, int)
        and after_last >= before_last
    )
    passed = bool(
        MAIN_MENU in startup and game_started and completed
        and completed_pool.get("classification") == "CONSISTENT"
        and killed and MAIN_MENU in recovery and not fatal_markers(recovery)
        and recovery_pool.get("classification") == "CONSISTENT"
        and valid_previous_or_new
        and request0_before == BASE_REQUEST0_SHA
        and request0_after == BASE_REQUEST0_SHA
    )
    result = {
        "name": case_name,
        "passed": passed,
        "package_uid": uid,
        **visual,
        "game_started": game_started,
        "completed_game_response_seen": completed,
        "completed_index": completed_index.get("index_text"),
        "completed_classification": completed_pool.get("classification"),
        "process_killed": killed,
        "recovery_index": after_state.get("index_text"),
        "recovery_classification": recovery_pool.get("classification"),
        "previous_or_new_valid_index": valid_previous_or_new,
        "request0_unchanged": request0_before == request0_after == BASE_REQUEST0_SHA,
    }
    (case_dir / "result.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    return result


with tarfile.open(CHECKPOINT, "r:gz") as archive:
    members = {Path(member.name).name: member for member in archive.getmembers() if member.isfile()}
    checkpoint_index = archive.extractfile(members[INDEX_NAME]).read()
    checkpoint_request0 = archive.extractfile(members[REQUEST0_NAME]).read()
if hashlib.sha256(checkpoint_index).hexdigest() != BASE_INDEX_SHA:
    raise SystemExit("checkpoint index mismatch")
if hashlib.sha256(checkpoint_request0).hexdigest() != BASE_REQUEST0_SHA:
    raise SystemExit("checkpoint request zero mismatch")
if hashlib.sha256(PRODUCTION_LIBRARY.read_bytes()).hexdigest() != PRODUCTION_LIBRARY_SHA:
    raise SystemExit("production library mismatch")

adb("push", str(CHECKPOINT), REMOTE_CHECKPOINT)
adb("push", str(PRODUCTION_LIBRARY), REMOTE_PRODUCTION_LIBRARY)
adb("shell", "svc", "power", "stayon", "true", check=False)
ensure_awake_unlocked()
selected = os.environ.get("STAGE_E_CASE")
results = []
try:
    if selected in BOUNDARY_CASES:
        results.append(run_boundary_case(selected, BOUNDARY_CASES[selected]))
    elif selected == "shutdown-after-completed-game":
        results.append(run_completed_game_case())
    else:
        raise SystemExit(f"unknown or missing STAGE_E_CASE: {selected}")
finally:
    root(f"am force-stop {PACKAGE}", check=False)
    production_uid = fresh_install(PRODUCTION_APK)
    restore_baseline(production_uid)
    adb("shell", "svc", "power", "stayon", "false", check=False)

summary = {
    "case_count": len(results),
    "all_passed": bool(results) and all(result["passed"] for result in results),
    "results": results,
    "final_process_alive": process_alive(),
}
(OUTPUT / "results.json").write_text(
    json.dumps(summary, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(summary), flush=True)
if not summary["all_passed"]:
    raise SystemExit("stage E case failed")
