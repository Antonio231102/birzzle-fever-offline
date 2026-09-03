import subprocess
import time
from pathlib import Path


ADB = str(Path("platform-tools-latest-windows/platform-tools/adb.exe"))
PACKAGE = "com.halfbrick.birzzlefever"
OUTPUT = Path("native-patches/v20-request-index-retention/cold-launch-stress-complete")
OUTPUT.mkdir(exist_ok=True)


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [ADB, *args],
        check=check,
        capture_output=True,
        text=True,
        errors="replace",
    )


def snapshot() -> str:
    return adb("logcat", "-d", "-v", "time").stdout


adb("shell", "input", "keyevent", "224")
adb("shell", "input", "keyevent", "82")
results = []
for launch in range(1, 6):
    # The prior launch is stopped only after it reached the main menu.
    adb("shell", "su", "-c", "am", "force-stop", PACKAGE)
    adb("logcat", "-c")
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
    reached_menu = False
    process_alive = False
    log = ""
    while time.monotonic() < deadline:
        time.sleep(2)
        log = snapshot()
        process_alive = bool(adb("shell", "pidof", PACKAGE, check=False).stdout.strip())
        fatal = "Fatal signal" in log or "FATAL EXCEPTION" in log
        reached_menu = '"message":"SCORE.RANKING"' in log
        if fatal or reached_menu or not process_alive:
            break

    (OUTPUT / f"launch-{launch}.log").write_text(log, encoding="utf-8")
    pocket = all(
        marker in log
        for marker in ('coin":"982920"', 'exp":"2200"', 'gem":"99870"')
    )
    inventory = '"message":"INVENTORY.LIST"' in log
    fatal = "Fatal signal" in log or "FATAL EXCEPTION" in log
    result = {
        "launch": launch,
        "alive": process_alive,
        "main_menu": reached_menu,
        "pocket": pocket,
        "inventory": inventory,
        "fatal": fatal,
    }
    results.append(result)
    print(result, flush=True)
    if not (process_alive and reached_menu and pocket and inventory and not fatal):
        raise SystemExit(f"launch {launch} failed before main-menu completion")
    time.sleep(3)

print(f"results={results}")
print("Final launch intentionally left running at the main menu.")
