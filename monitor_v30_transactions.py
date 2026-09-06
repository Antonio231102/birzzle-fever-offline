import argparse
import hashlib
import json
import queue
import re
import subprocess
import tarfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path


PACKAGE = "com.halfbrick.birzzlefever"
SAVE_RE = re.compile(r"SAVE REQUEST:([^,]+).*?timeout=(\d+)")
RESPONSE_RE = re.compile(r'HangameWrapper::OnReceivedResponse\[.*?"timeout":"(\d+)"')
BOUNDARY_RE = re.compile(r"\bB30\s*: o=(\d+) r=(-?\d+)")


def adb_command(adb: Path, serial: str, *args: str, binary: bool = False):
    command = [str(adb), "-s", serial, *args]
    if binary:
        return subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    return subprocess.run(
        command,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def snapshot(adb: Path, serial: str, root: Path, reason: str, details: dict) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = root / f"{stamp}-{reason}"
    target.mkdir(parents=True, exist_ok=False)

    private = adb_command(
        adb,
        serial,
        "exec-out",
        "run-as",
        PACKAGE,
        "tar",
        "-cf",
        "-",
        ".",
        binary=True,
    ).stdout
    private_path = target / "private-data.tar"
    private_path.write_bytes(private)
    with tarfile.open(private_path, "r:") as archive:
        private_entries = len(archive.getmembers())

    logcat = adb_command(adb, serial, "logcat", "-d", "-v", "threadtime").stdout
    log_path = target / "logcat.txt"
    log_path.write_text(logcat, encoding="utf-8", newline="\n")

    metadata = {
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "serial": serial,
        "package": PACKAGE,
        "reason": reason,
        "details": details,
        "private_data": {
            "path": private_path.name,
            "bytes": len(private),
            "entries": private_entries,
            "sha256": sha256(private),
        },
        "logcat": {
            "path": log_path.name,
            "bytes": len(logcat.encode("utf-8")),
            "sha256": sha256(logcat.encode("utf-8")),
        },
    }
    (target / "metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return target


def reader_thread(process: subprocess.Popen, events: queue.Queue):
    try:
        for line in process.stdout:
            events.put(("line", line))
    finally:
        events.put(("eof", None))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Monitor V30 transactions, inject one process interruption, and snapshot private state."
    )
    parser.add_argument("--serial", required=True)
    parser.add_argument(
        "--kill-after-op",
        type=int,
        choices=range(1, 13),
        help="Force-stop once after the selected completed boundary (1-12).",
    )
    parser.add_argument("--stall-seconds", type=float, default=15.0)
    parser.add_argument("--timeout-seconds", type=float, default=600.0)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("device-snapshots/2026-09-04-s20-v30-fault-matrix"),
    )
    parser.add_argument(
        "--adb",
        type=Path,
        default=Path("platform-tools-latest-windows/platform-tools/adb.exe"),
    )
    args = parser.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)
    adb_command(args.adb, args.serial, "logcat", "-c")
    process = subprocess.Popen(
        [str(args.adb), "-s", args.serial, "logcat", "-v", "threadtime"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )
    events = queue.Queue()
    thread = threading.Thread(target=reader_thread, args=(process, events), daemon=True)
    thread.start()
    print(
        f"ARMED kill-after-op={args.kill_after_op} "
        f"stall-seconds={args.stall_seconds}",
        flush=True,
    )

    pending: dict[int, tuple[str, float]] = {}
    started = time.monotonic()
    try:
        while time.monotonic() - started < args.timeout_seconds:
            try:
                event, line = events.get(timeout=0.2)
            except queue.Empty:
                event, line = None, None

            if event == "eof":
                raise RuntimeError("adb logcat exited before a diagnostic event")
            if event == "line":
                print(
                    line.encode("ascii", errors="backslashreplace").decode("ascii"),
                    end="",
                    flush=True,
                )
                save = SAVE_RE.search(line)
                if save:
                    pending[int(save.group(2))] = (save.group(1), time.monotonic())
                response = RESPONSE_RE.search(line)
                if response:
                    pending.pop(int(response.group(1)), None)
                boundary = BOUNDARY_RE.search(line)
                if boundary and args.kill_after_op == int(boundary.group(1)):
                    details = {
                        "operation": int(boundary.group(1)),
                        "return": int(boundary.group(2)),
                        "boundary_line": line.rstrip(),
                    }
                    adb_command(args.adb, args.serial, "shell", "am", "force-stop", PACKAGE)
                    target = snapshot(
                        args.adb,
                        args.serial,
                        args.output,
                        f"kill-after-op-{args.kill_after_op:02d}",
                        details,
                    )
                    print(f"SNAPSHOT={target}", flush=True)
                    return 0

            now = time.monotonic()
            stalled = [
                (timeout, command, now - began)
                for timeout, (command, began) in pending.items()
                if now - began >= args.stall_seconds
            ]
            if stalled:
                timeout, command, age = min(stalled, key=lambda item: item[2])
                target = snapshot(
                    args.adb,
                    args.serial,
                    args.output,
                    f"stalled-timeout-{timeout}",
                    {"timeout": timeout, "command": command, "pending_seconds": age},
                )
                print(f"SNAPSHOT={target}", flush=True)
                return 2

        raise TimeoutError("no selected boundary or stalled transaction observed")
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
