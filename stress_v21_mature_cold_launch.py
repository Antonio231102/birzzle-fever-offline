import json
import subprocess
import time
from pathlib import Path


ADB = str(Path("platform-tools-latest-windows/platform-tools/adb.exe"))
PACKAGE = "com.halfbrick.birzzlefever"
OUTPUT = Path("native-patches/v21-response-index-hardening/stage-b-mature-cold-starts")
OUTPUT.mkdir(exist_ok=True)
LAUNCH_COUNT = 10
EXPECTED_MARKERS = {
    "pocket": ('"coin":"980800"', '"gem":"99870"', '"exp":"3810"'),
    "suri_level_10": ('"ability":"10","itemid":"0"',),
    "polo_owned": ('"ability":"2","itemid":"2"',),
    "ranking": ('"message":"SCORE.RANKING"', '"scorecurrent":"1017964"'),
}
FATAL_MARKERS = (
    "FATAL EXCEPTION",
    "Fatal signal",
    "SIGSEGV",
    f"ANR in {PACKAGE}",
    "Force finishing activity com.halfbrick.birzzlefever",
)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [ADB, *args],
        check=check,
        capture_output=True,
        text=True,
        errors="replace",
    )


def process_alive() -> bool:
    return any(PACKAGE in line for line in adb("shell", "ps").stdout.splitlines())


def snapshot() -> str:
    return adb("shell", "logcat", "-d", "-v", "time").stdout


adb("shell", "input", "keyevent", "224")
adb("shell", "input", "keyevent", "82")
adb("shell", "input", "swipe", "540", "1600", "540", "400", "500")
adb("shell", "svc", "power", "stayon", "true")

results = []
try:
    for launch in range(1, LAUNCH_COUNT + 1):
        adb("shell", "am", "force-stop", PACKAGE)
        adb("shell", "logcat", "-c")
        started_at = time.monotonic()
        adb(
            "shell",
            "monkey",
            "-p",
            PACKAGE,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        )

        deadline = time.monotonic() + 75
        log = ""
        alive = False
        reached_menu = False
        fatal_markers = []
        while time.monotonic() < deadline:
            time.sleep(1)
            log = snapshot()
            alive = process_alive()
            fatal_markers = [marker for marker in FATAL_MARKERS if marker in log]
            reached_menu = '"message":"SCORE.RANKING"' in log
            if fatal_markers or reached_menu or not alive:
                break

        log_path = OUTPUT / f"launch-{launch:02d}.log"
        log_path.write_text(log, encoding="utf-8")
        marker_results = {
            name: all(marker in log for marker in markers)
            for name, markers in EXPECTED_MARKERS.items()
        }
        result = {
            "launch": launch,
            "duration_seconds": round(time.monotonic() - started_at, 3),
            "process_alive": alive,
            "main_menu": reached_menu,
            **marker_results,
            "fatal_markers": fatal_markers,
            "log": log_path.as_posix(),
        }
        results.append(result)
        print(json.dumps(result), flush=True)
        if not (
            alive
            and reached_menu
            and all(marker_results.values())
            and not fatal_markers
        ):
            raise SystemExit(f"launch {launch} failed validation")
        time.sleep(2)
finally:
    adb("shell", "am", "force-stop", PACKAGE, check=False)
    adb("shell", "svc", "power", "stayon", "false", check=False)
    (OUTPUT / "results.json").write_text(
        json.dumps({"launches": results}, indent=2) + "\n",
        encoding="utf-8",
    )

print(f"validated_launches={len(results)}")
print("final_state=force-stopped")
