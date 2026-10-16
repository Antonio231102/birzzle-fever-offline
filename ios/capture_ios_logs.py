"""Capture Birzzle Fever iOS 6 diagnostics without launching or operating the game.

Run --check before the operator's manual-test readiness gate. Only run --capture
once the operator has explicitly begun a manual test. Captures stay under ios/.
"""

import argparse
from datetime import datetime, timezone
import os
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from threading import Event, Thread
from time import monotonic, sleep


PACKAGE = "com.halfbrick.birzzlefever"
IOS_DIR = Path(__file__).resolve().parent
FOCUSED = re.compile(r"BirzzleFever HB|com\.halfbrick\.birzzlefever|ReportCrash.*Birzzle|SpringBoard.*Birzzle", re.I)
PRIVATE_ACCOUNT_LOG = re.compile(r"(DEVICE TOKEN|MEMBERNO):[^\r\n]*", re.I)
CLIENT_ENV = dict(os.environ, OPENSSL_CONF=str(IOS_DIR / "openssl-ios6.cnf"))


def tool(name, directory):
    if directory:
        path = directory / (name + ".exe")
        if path.is_file():
            return str(path)
    found = shutil.which(name)
    if found:
        return found
    raise RuntimeError(f"{name} unavailable; install MSYS2 mingw-w64-x86_64-libimobiledevice")


def run(executable, *args):
    result = subprocess.run((executable, *args), capture_output=True, text=True, errors="replace",
                            timeout=30, env=CLIENT_ENV)
    if result.returncode:
        details = (result.stderr or result.stdout).strip()
        if "-u" in args:
            details = details.replace(args[args.index("-u") + 1], "<iPad-UDID>")
        raise RuntimeError(f"{Path(executable).name} failed: {details[:300]}")
    return result.stdout.strip()


def main():
    parser = argparse.ArgumentParser(description="Preflight or capture iPad 2 Birzzle Fever 1.0.4 diagnostics")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="verify USB tools, iPad identity, and pairing without reading logs")
    mode.add_argument("--capture", action="store_true", help="capture live syslog and copy crash reports after the manual readiness gate")
    parser.add_argument("--operator-ready", action="store_true",
                        help="confirm the operator explicitly began this manual test")
    parser.add_argument("--tools-dir", type=Path, default=Path(r"C:\msys64\mingw64\bin"))
    parser.add_argument("--udid", help="select an iPad if more than one iOS device is connected")
    parser.add_argument("--duration", type=int, default=300, help="maximum capture seconds (default: 300)")
    args = parser.parse_args()
    if args.duration <= 0:
        parser.error("--duration must be positive")
    if args.capture and not args.operator_ready:
        parser.error("--capture requires --operator-ready after the manual readiness gate")
    if not (IOS_DIR / "openssl-ios6.cnf").is_file():
        raise RuntimeError("missing local-only iOS 6 USB TLS compatibility configuration")

    clients = {name: tool(name, args.tools_dir) for name in ("idevice_id", "ideviceinfo", "idevicepair", "idevicesyslog", "idevicecrashreport")}
    devices = [line.strip() for line in run(clients["idevice_id"], "-l").splitlines() if line.strip()]
    if args.udid:
        if args.udid not in devices:
            raise RuntimeError("specified UDID is not attached via USB")
        udid = args.udid
    elif len(devices) == 1:
        udid = devices[0]
    else:
        raise RuntimeError(f"expected exactly one USB iOS device; found {len(devices)} (use --udid)")
    version = run(clients["ideviceinfo"], "-u", udid, "-k", "ProductVersion")
    model = run(clients["ideviceinfo"], "-u", udid, "-k", "ProductType")
    if version != "6.1.3" or not model.startswith("iPad2,"):
        raise RuntimeError(f"expected iPad 2 / iOS 6.1.3; got {model} / iOS {version}")
    run(clients["idevicepair"], "-u", udid, "validate")
    print(f"USB/pairing OK: {model}, iOS {version}, target {PACKAGE}", flush=True)
    if args.check:
        print("Preflight only: no syslog, crash report, or game launch was accessed.")
        return
    if not sys.stdin.isatty():
        raise RuntimeError("manual capture requires an interactive terminal and operator readiness")

    session_root = IOS_DIR / "captures"
    session_root.mkdir(exist_ok=True)
    session = session_root / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    session.mkdir(exist_ok=False)
    raw = session / "device-syslog.txt"
    stderr = session / "syslog-client-stderr.txt"
    done = Event()

    def wait_for_operator():
        try:
            input("Log capture active. Open the app manually; press Enter after the test ends or it crashes.\n")
        except (EOFError, KeyboardInterrupt):
            pass
        done.set()

    print("MANUAL TEST: iPad 2 / Birzzle Fever 1.0.4 — watch for loading, offline sign-in, menu, gameplay, freeze, or crash.", flush=True)
    print("No game launch or UI interaction is performed by this script.", flush=True)
    began = datetime.now(timezone.utc)
    with raw.open("xb") as log, stderr.open("xb") as errors:
        process = subprocess.Popen((clients["idevicesyslog"], "-u", udid), stdout=log,
                                   stderr=errors, env=CLIENT_ENV)
        Thread(target=wait_for_operator, daemon=True).start()
        deadline = monotonic() + args.duration
        try:
            while not done.is_set() and process.poll() is None and monotonic() < deadline:
                sleep(0.25)
            stop_reason = ("operator" if done.is_set() else
                           "client_exit" if process.poll() is not None else "duration_limit")
        except KeyboardInterrupt:
            stop_reason = "interrupt"
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)

    focused = session / "app-focused.txt"
    matching = 0
    with raw.open("r", encoding="utf-8", errors="replace") as source, focused.open("x", encoding="utf-8") as output:
        for line in source:
            if FOCUSED.search(line):
                output.write(PRIVATE_ACCOUNT_LOG.sub(r"\1: <redacted>", line))
                matching += 1
    crashes = session / "crashes"
    crashes.mkdir()
    crash = subprocess.run((clients["idevicecrashreport"], "-u", udid, "-k", "-e", str(crashes)),
                           capture_output=True, text=True, errors="replace", timeout=120, env=CLIENT_ENV)
    (session / "crashreport-client.txt").write_text(crash.stdout + crash.stderr, encoding="utf-8")
    summary = {
        "target": PACKAGE,
        "device": model,
        "ios_version": version,
        "started_utc": began.isoformat(),
        "ended_utc": datetime.now(timezone.utc).isoformat(),
        "stop_reason": stop_reason,
        "syslog_client_exit_code": process.returncode,
        "syslog_bytes": raw.stat().st_size,
        "app_focused_lines": matching,
        "crash_copy_return_code": crash.returncode,
        "crash_reports_kept_on_device": True,
        "copied_crash_reports_may_predate_session": True,
        "automatic_game_launch": False,
    }
    (session / "session.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"Capture: {session}\nApp-related lines: {matching}; crash-copy exit: {crash.returncode}")
    print("Raw logs and unfiltered copied crash reports stay local in the ignored session directory.")
    if crash.returncode:
        raise RuntimeError("crash-report copy failed; inspect crashreport-client.txt")
    if raw.stat().st_size == 0:
        raise RuntimeError(f"empty syslog; crash reports still copied; inspect {stderr} and {session}")


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print(f"iOS capture: {error}", file=sys.stderr)
        sys.exit(1)
