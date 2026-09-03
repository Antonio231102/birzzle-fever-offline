import base64
import subprocess
import time
from pathlib import Path

from Crypto.Cipher import AES


ADB = str(Path("platform-tools-latest-windows/platform-tools/adb.exe"))
PACKAGE = "com.halfbrick.birzzlefever"
CONTROL_APK = Path(
    "native-patches/v20-request-index-retention/unclamped-control/"
    "BirzzleFever-1.1.2-v20-unclamped-control.apk"
)
CHECKPOINT = Path(
    "device-snapshots/2026-08-29-bonus-mode-test/post-bonus-v18-data.tar.gz"
)
OUT = Path("native-patches/v20-request-index-retention/unclamped-control")
INDEX = "5f7d50ff681a65b10550a631e11a2ded"
REMOTE_DATA = "/data/data/com.halfbrick.birzzlefever"


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [ADB, *args],
        check=check,
        capture_output=True,
        text=True,
        errors="replace",
    )


def logs() -> str:
    return adb("logcat", "-d", "-v", "time").stdout


def wait_for(marker: str, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    current = ""
    while time.monotonic() < deadline:
        time.sleep(2)
        current = logs()
        if marker in current:
            return current
        if not adb("shell", "pidof", PACKAGE, check=False).stdout.strip():
            raise SystemExit(f"process died while waiting for {marker}")
    raise SystemExit(f"timed out waiting for {marker}")


print(adb("install", "-r", str(CONTROL_APK)).stdout, end="")
adb("shell", "su", "-c", "am", "force-stop", PACKAGE)
adb("push", str(CHECKPOINT), "/data/local/tmp/unclamped-checkpoint.tar.gz")
adb(
    "shell", "su", "-c", "rm", "-rf",
    f"{REMOTE_DATA}/cache", f"{REMOTE_DATA}/databases", f"{REMOTE_DATA}/files",
    f"{REMOTE_DATA}/shared_prefs", f"{REMOTE_DATA}/app_webview",
    f"{REMOTE_DATA}/.birzzle_seed_v1",
)
adb(
    "shell", "su", "-c", "tar", "-xzf",
    "/data/local/tmp/unclamped-checkpoint.tar.gz", "-C", "/",
    "--exclude=data/data/com.halfbrick.birzzlefever/lib",
)
adb("shell", "input", "keyevent", "224")
adb("shell", "input", "keyevent", "82")
adb("logcat", "-c")
adb(
    "shell", "monkey", "-p", PACKAGE,
    "-c", "android.intent.category.LAUNCHER", "1",
)
wait_for('"message":"SCORE.RANKING"', 75)
print("main_menu=True")

adb("shell", "input", "tap", "540", "1550")
time.sleep(4)
fault = f"{REMOTE_DATA}/files/{INDEX}.fault"
index = f"{REMOTE_DATA}/files/{INDEX}"
adb("shell", "su", "-c", "mv", index, fault)
try:
    adb("shell", "input", "tap", "540", "1550")
    time.sleep(3)
finally:
    adb("shell", "su", "-c", "mv", fault, index, check=False)

log = wait_for('extradata":"GameStart"', 40)
# Wait for the response rather than accepting only the request line.
deadline = time.monotonic() + 30
while '"extradata":"GameStart","message":"POCKET.SET"' not in log:
    if time.monotonic() >= deadline:
        raise SystemExit("GameStart response did not arrive")
    time.sleep(2)
    log = logs()
(OUT / "unclamped-live-index-fault.log").write_text(log, encoding="utf-8")

alive = bool(adb("shell", "pidof", PACKAGE, check=False).stdout.strip())
game_start_response = next(
    line
    for line in log.splitlines()
    if '"extradata":"GameStart","message":"POCKET.SET"' in line
)
values = all(
    marker in game_start_response
    for marker in ('coin":"982920"', 'gem":"99870"', 'exp":"2200"')
)
fatal = "Fatal signal" in log or "FATAL EXCEPTION" in log
clamp = "POCKET CLAMP" in log

adb("shell", "su", "-c", "cp", index, "/data/local/tmp/unclamped-post-fault-index")
adb("shell", "su", "-c", "chmod", "644", "/data/local/tmp/unclamped-post-fault-index")
adb("pull", "/data/local/tmp/unclamped-post-fault-index", str(OUT / "post-fault-index.bin"))
raw = (OUT / "post-fault-index.bin").read_bytes()
decrypted = AES.new(b"miaeHgpdskiinerS", AES.MODE_ECB).decrypt(base64.b64decode(raw))
decrypted = decrypted.rstrip(bytes([decrypted[-1]]))

print(f"alive={alive}")
print(f"authoritative_values={values}")
print(f"fatal={fatal}")
print(f"clamp_log={clamp}")
print(f"decrypted_index={decrypted!r}")
if not alive or not values or fatal or clamp or b"DATA:LTEsMTAz" not in decrypted:
    raise SystemExit("unclamped v20 control failed")
