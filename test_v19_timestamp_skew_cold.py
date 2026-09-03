import base64
import subprocess
import time
from pathlib import Path

from Crypto.Cipher import AES

from analyze_birzzle_save import decrypt2


ADB = str(Path("platform-tools-latest-windows/platform-tools/adb.exe"))
PACKAGE = "com.halfbrick.birzzlefever"
V19_APK = Path("native-patches/v19-authoritative-gem-guard/BirzzleFever-1.1.2-v19-authoritative-gem-guard.apk")
V20_APK = Path("native-patches/v20-request-index-retention/BirzzleFever-1.1.2-v20-request-index-retention.apk")
CHECKPOINT = Path("device-snapshots/2026-08-29-bonus-mode-test/post-bonus-v18-data.tar.gz")
OUT = Path("device-snapshots/2026-08-30-response-index-timestamp-skew")
DATA = "/data/data/com.halfbrick.birzzlefever"
INDEX_NAME = "5f7d50ff681a65b10550a631e11a2ded"
INDEX = f"{DATA}/files/{INDEX_NAME}"
REMOTE_CHECKPOINT = "/data/local/tmp/timestamp-skew-cold-checkpoint.tar.gz"
SKEWED_TOUCH = "20260829.222420"  # Embedded timestamp is 22:23:20: +60 seconds.


def adb(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run([ADB, *args], check=check, capture_output=True, text=True, errors="replace")


def restore(apk: Path) -> None:
    adb("shell", "su", "-c", "am", "force-stop", PACKAGE, check=False)
    print(adb("install", "-r", str(apk)).stdout, end="")
    adb("push", str(CHECKPOINT), REMOTE_CHECKPOINT)
    adb(
        "shell", "su", "-c", "rm", "-rf",
        f"{DATA}/cache", f"{DATA}/databases", f"{DATA}/files",
        f"{DATA}/shared_prefs", f"{DATA}/app_webview", f"{DATA}/.birzzle_seed_v1",
    )
    adb(
        "shell", "su", "-c", "tar", "-xzf", REMOTE_CHECKPOINT,
        "-C", "/", "--exclude=data/data/com.halfbrick.birzzlefever/lib",
    )


def pull_index() -> bytes:
    remote = "/data/local/tmp/v19-cold-skew-index.bin"
    local = OUT / "v19-cold-skew-index.bin"
    adb("shell", "su", "-c", "cp", INDEX, remote)
    adb("shell", "su", "-c", "chmod", "644", remote)
    adb("pull", remote, str(local))
    return local.read_bytes()


OUT.mkdir(exist_ok=True)
try:
    restore(V19_APK)
    adb("shell", "su", "-c", "touch", "-t", SKEWED_TOUCH, INDEX)
    mtime = int(adb("shell", "su", "-c", "stat", "-c", "%Y", INDEX).stdout.strip())
    adb("logcat", "-c")
    adb("shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")
    deadline = time.monotonic() + 45
    log = ""
    while time.monotonic() < deadline:
        time.sleep(2)
        log = adb("logcat", "-d", "-v", "time").stdout
        if "Fatal signal" in log:
            break
    (OUT / "v19-cold-skew.log").write_text(log, encoding="utf-8")
    raw = pull_index()
    envelope = decrypt2(raw)
    if envelope is None:
        raise SystemExit("the skewed index no longer has a valid CCrypt2 envelope")

    findings = {
        "mtime": mtime,
        "embedded_timestamp": envelope["timestamp"],
        "mtime_delta": mtime - envelope["timestamp"],
        "digest_valid": envelope["digest_valid"],
        "index_data": envelope["decoded_data"].decode("ascii"),
        "queststatus_empty": '"queststatus":[]' in log,
        "inventory_sentinel_only": '"inven":[{"ability":"0","itemid":"","odr":"0","tid":"0"}]' in log,
        "pocket_zero": all(marker in log for marker in ('coin":"0"', 'gem":"0"', 'exp":"0"')),
        "ranking_zero": '"scorehighest":"0"' in log,
        "fatal": "Fatal signal" in log,
    }
    print(findings)
    expected = {
        "mtime_delta": 60,
        "digest_valid": True,
        "index_data": "-1,102",
        "queststatus_empty": True,
        "inventory_sentinel_only": True,
        "pocket_zero": True,
        "ranking_zero": True,
    }
    for key, value in expected.items():
        if findings[key] != value:
            raise SystemExit(f"unexpected {key}: {findings[key]!r} != {value!r}")
finally:
    # Never leave the destructive control build or skewed save installed.
    restore(V20_APK)

print("production_v20_and_clean_checkpoint_restored=True")
