#!/usr/bin/env python3
"""Gated S4 clock/power stress runner. No APK, cooldown, or save patching.

Default: print the plan without contacting ADB. Calibrate navigation once,
then run against an already active cooldown. Shutdown needs physical power-on.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import time
import uuid
from pathlib import Path

from capture_v25_soak_checkpoint import (
    ADB, DATA_PATH, PACKAGE, Adb, ArtifactWriter, CaptureError,
    process_snapshot, pull_quiesced_tar, remote_sha256,
)
from decode_birzzle_profiles import seed_crypt

APK_SHA256 = "29929b466b5cb33d9eff463a85b19c67924e116591c45ec8e579272e20bcc719"
PROFILE = DATA_PATH + "/files/petPresent.dat_9"
INTERVAL = 21600
OFFSETS = (60, -60, 3600, -3600, 21600, -21600, 86400, -86400, 31536000, -31536000)
PROMPT = "Please prepare the Android device. Let me know when you are ready to begin the manual test."


def decode_timer(raw: bytes) -> dict:
    if len(raw) != 64:
        raise CaptureError("Expected the installed fix's 64-byte Eve profile")
    plain = seed_crypt(raw, decrypt=True)
    checksum = 2166136261
    for byte in plain[:48]:
        checksum = ((checksum ^ byte) * 16777619) & 0xFFFFFFFF
    remaining = int.from_bytes(plain[8:12], "little")
    boot = plain[12:48].decode("ascii")
    if (plain[:4] != b"EVE1" or remaining > INTERVAL or
            checksum != int.from_bytes(plain[48:52], "little") or
            not re.fullmatch(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}", boot)):
        raise CaptureError("Invalid Eve profile; not replacing or resetting it")
    return {"sampled": int.from_bytes(plain[4:8], "little"),
            "remaining": remaining, "boot": boot,
            "ciphertext_sha256": hashlib.sha256(raw).hexdigest()}


def check_transition(before: dict, after: dict, *, power_cycle: bool) -> None:
    old, new = before["timer"], after["timer"]
    if new["boot"] != after["boot"] or new["sampled"] > after["uptime"] + 1:
        raise CaptureError("Game did not establish a valid current-boot checkpoint")
    if power_cycle:
        if old["boot"] == after["boot"]:
            raise CaptureError("Power cycle did not change the kernel boot UUID")
        # This must be the FIRST observed new-boot write. Later writes can
        # legitimately subtract time; do not accept them as proof of resumption.
        if new["remaining"] != old["remaining"]:
            raise CaptureError("Reboot/shutdown did not resume the exact saved remainder")
    else:
        if before["boot"] != after["boot"]:
            raise CaptureError("Unexpected reboot during a same-boot test")
        if new["sampled"] + new["remaining"] != old["sampled"] + old["remaining"]:
            raise CaptureError("Calendar/app restart changed the boot-time deadline")
    if new["remaining"] == 0:
        raise CaptureError("Cooldown expired; stop this no-payout campaign")


def validate_action(step: list, width: int, height: int) -> None:
    if not isinstance(step, list) or not step:
        raise CaptureError("Invalid navigation action")
    kind, *values = step
    if kind == "wait":
        valid = len(values) == 1 and isinstance(values[0], (int, float)) and 0 < values[0] <= 30
    else:
        count = {"tap": 2, "swipe": 5}.get(kind)
        valid = count is not None and len(values) == count and all(type(v) is int and v >= 0 for v in values)
        if valid:
            valid = all(v < (width if i % 2 == 0 else height)
                        for i, v in enumerate(values[:4 if kind == "swipe" else 2]))
            if kind == "swipe":
                valid = valid and 1 <= values[4] <= 5000
    if not valid:
        raise CaptureError(f"Unsupported navigation action: {step}")


def navigation(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for phase in ("open", "probe"):
        steps = data.get(phase)
        if not isinstance(steps, list) or not 1 <= len(steps) <= 20:
            raise CaptureError(f"Navigation requires 1–20 {phase} actions")
        for step in steps:
            validate_action(step, data["width"], data["height"])
        if not any(step[0] in ("tap", "swipe") for step in steps):
            raise CaptureError(f"{phase} must include actual UI input")
        if sum(step[1] for step in steps if step[0] == "wait") > 30:
            raise CaptureError("Navigation waits must total at most 30 seconds per phase")
    return data


class Stress:
    def __init__(self, args):
        self.args = args
        self.adb = Adb(args.adb, args.serial)
        self.output = args.output
        self.output.mkdir(parents=True, exist_ok=False)
        self.report = {"serial": args.serial, "cases": [], "status": "preparing"}
        self.recovery = None
        self.nav = None

    def save(self):
        (self.output / "results.json").write_text(json.dumps(self.report, indent=2), encoding="utf-8")

    def pull(self, remote: str, name: str) -> bytes:
        temporary = "/data/local/tmp/eve-stress-" + uuid.uuid4().hex
        local = self.output / name
        try:
            self.adb.root(f"cp {remote} {temporary}")
            self.adb.root(f"chmod 0644 {temporary}")
            self.adb.run("pull", temporary, str(local))
            return local.read_bytes()
        finally:
            self.adb.root(f"rm -f {temporary}", check=False)

    def shell_records(self, *args: str) -> list[str]:
        result = self.adb.run("shell", *args)
        records = []
        diagnostics = self.report.setdefault("shell_diagnostics", [])
        for line in (result.stdout + "\n" + result.stderr).splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("WARNING: linker:"):
                if line not in diagnostics:
                    diagnostics.append(line)
            else:
                records.append(line)
        return records

    def setting(self, key: str) -> str:
        records = self.shell_records("settings", "get", "global", key)
        if len(records) != 1 or records[0] not in ("0", "1", "null"):
            raise CaptureError(f"Unexpected {key} setting response: {records}")
        return records[0]

    def clock(self) -> dict:
        lines = self.shell_records("cat /proc/sys/kernel/random/boot_id; cat /proc/uptime; date +%s")
        if len(lines) != 3:
            raise CaptureError("Could not read boot UUID, uptime, and calendar")
        return {"boot": str(uuid.UUID(lines[0].strip())),
                "uptime": float(lines[1].split()[0]), "wall": int(lines[2])}

    def observe(self, label: str) -> dict:
        timer = decode_timer(self.pull(PROFILE, label + ".dat"))
        return {"timer": timer, **self.clock()}

    def screen(self, label: str):
        remote = "/data/local/tmp/eve-screen-" + uuid.uuid4().hex + ".png"
        try:
            self.adb.run("shell", "screencap", "-p", remote)
            self.adb.run("pull", remote, str(self.output / (label + ".png")))
        finally:
            self.adb.run("shell", "rm", "-f", remote, check=False)

    def logs(self, label: str):
        raw = self.adb.run("logcat", "-d", "-v", "threadtime", "[Birzzle]:V",
                           "AndroidRuntime:E", "DEBUG:F", "libc:F", "*:S").stdout
        lines = raw.splitlines()
        pids = {line.split()[2] for line in lines if "[Birzzle]" in line and len(line.split()) >= 6}
        scoped = [line for line in lines if PACKAGE in line or
                  (len(line.split()) >= 6 and line.split()[2] in pids)]
        text = "\n".join(scoped) + "\n"
        (self.output / (label + ".log")).write_text(text, encoding="utf-8")
        Path(".omp").mkdir(exist_ok=True)
        Path(".omp/current_test_log.txt").write_text(text, encoding="utf-8")
        if any(token in text for token in ("FATAL EXCEPTION", "Fatal signal", "SIGSEGV", "SIGILL", "ANR in " + PACKAGE)):
            raise CaptureError("Fatal runtime marker in scoped game log")
        for line in scoped:
            if "SAVE REQUEST:pocket.set" in line:
                deltas = dict(re.findall(r"(?:[?&])(heart|gem|coin)=(-?\d+)", line))
                if any(int(value) != 0 for value in deltas.values()):
                    raise CaptureError("Unexpected currency/heart mutation during no-payout stress")

    def bootstrap(self):
        # Same required manual-test bootstrap; Android 4.4 lacks -b crash.
        self.adb.run("logcat", "-c")
        self.adb.run("logcat", "-b", "crash", "-c", check=False)
        self.adb.run("shell", "monkey", "-p", PACKAGE, "-c", "android.intent.category.LAUNCHER", "1")

    def preflight(self):
        if self.adb.run("get-state").stdout.strip() != "device":
            raise CaptureError("Target device unavailable")
        if "uid=0" not in self.adb.root("id").stdout:
            raise CaptureError("This physical runner requires the rooted S4")
        if self.adb.run("shell", "getprop", "ro.build.version.sdk").stdout.strip() != "19":
            raise CaptureError("Clock-setting command is qualified for Android 4.4 only")
        paths = self.shell_records("pm", "path", PACKAGE)
        if len(paths) != 1 or not paths[0].startswith("package:"):
            raise CaptureError("Unexpected package layout")
        digest, errors = remote_sha256(self.adb, paths[0][8:].strip())
        if digest != APK_SHA256:
            raise CaptureError(f"Installed APK identity mismatch: {digest}; {errors}")
        self.report["apk_sha256"] = digest
        self.adb.run("shell", "am", "force-stop", PACKAGE)
        if process_snapshot(self.adb)["running"]:
            raise CaptureError("App did not stop for backup")
        backup = self.output / "backup"
        backup.mkdir()
        archive = pull_quiesced_tar(self.adb, ArtifactWriter(backup))
        self.report["backup"] = str(archive)
        import tarfile
        inventory = {}
        with tarfile.open(archive, "r:gz") as saved:
            for member in saved:
                if member.isfile():
                    raw = saved.extractfile(member).read()
                    inventory[member.name] = hashlib.sha256(raw).hexdigest()
        if not any(name.endswith("/files/petPresent.dat_9") for name in inventory):
            raise CaptureError("Backup does not contain Eve's reward state")
        (backup / "file-hashes.json").write_text(json.dumps(inventory, indent=2), encoding="utf-8")
        baseline = self.observe("baseline")
        left = baseline["timer"]["remaining"]
        if baseline["boot"] == baseline["timer"]["boot"]:
            left -= max(0, math.floor(baseline["uptime"]) - baseline["timer"]["sampled"])
        if left < 3600:
            raise CaptureError("Need at least one hour of active cooldown; do not reset the save")
        self.report["baseline"] = baseline
        self.save()

    def require_active(self):
        observed = self.observe("active-guard")
        timer = observed["timer"]
        left = timer["remaining"]
        if timer["boot"] == observed["boot"]:
            left -= max(0, math.floor(observed["uptime"]) - timer["sampled"])
        if left < 180:
            raise CaptureError("Less than three minutes remain; abort before any legitimate gift becomes due")

    def replay(self, steps):
        for kind, *values in steps:
            self.require_active()
            if kind == "wait":
                time.sleep(values[0])
            else:
                self.adb.run("shell", "input", kind, *(str(value) for value in values))

    def launch(self, label: str, before: dict, power_cycle=False) -> dict:
        self.adb.run("shell", "am", "force-stop", PACKAGE)
        self.adb.run("shell", "input", "keyevent", "224")
        self.adb.run("shell", "input", "keyevent", "82")
        clock = self.clock()
        minimum_sample = math.floor(clock["uptime"]) + 1
        time.sleep(1.1)
        self.bootstrap()
        time.sleep(self.args.launch_wait)
        self.screen(label + "-start")
        from PIL import Image
        with Image.open(self.output / (label + "-start.png")) as image:
            if image.size != (self.nav["width"], self.nav["height"]):
                raise CaptureError("Display dimensions changed since navigation calibration")
        self.replay(self.nav["open"])
        deadline = time.monotonic() + 90
        while time.monotonic() < deadline:
            after = self.observe(label)
            if after["timer"]["boot"] == after["boot"] and after["timer"]["sampled"] >= minimum_sample:
                check_transition(before, after, power_cycle=power_cycle)
                self.replay(self.nav["probe"])
                self.screen(label)
                self.logs(label)
                if not process_snapshot(self.adb)["running"]:
                    raise CaptureError("App exited during the probe")
                self.report["cases"].append({"name": label, "before": before, "after": after, "passed": True})
                self.save()
                print(f"CASE_PASS {label}: saved_remaining={after['timer']['remaining']}", flush=True)
                return after
            time.sleep(1)
        raise CaptureError("No fresh Eve checkpoint: navigation or timer initialization failed")

    def set_clock(self, epoch: int):
        if not 31536000 <= epoch < 2114380800:
            raise CaptureError("Calendar target outside safe 32-bit Android test range")
        # AOSP KitKat toolbox date accepts epoch[.fraction] without -s.
        # -s uses local calendar syntax, and -u does not change that parser.
        self.adb.root(f"date {epoch}")
        if abs(self.clock()["wall"] - epoch) > 5:
            raise CaptureError("Device calendar did not accept the requested time")

    def original_now(self) -> int:
        return int(self.recovery["device_wall"] + time.time() - self.recovery["host_wall"])

    def change_clock(self, offset: int):
        self.set_clock(self.original_now() + offset)

    def wait_online(self):
        deadline = time.monotonic() + self.args.boot_timeout
        while time.monotonic() < deadline:
            state = self.adb.run("get-state", check=False, timeout=10)
            if state.returncode == 0 and state.stdout.strip() == "device":
                if self.adb.run("shell", "getprop", "sys.boot_completed", check=False, timeout=10).stdout.strip() == "1":
                    return
            time.sleep(2)
        raise CaptureError("Device did not return; recovery state retained for --restore")

    def power_cycle(self, label: str, shutdown: bool):
        self.adb.run("shell", "am", "force-stop", PACKAGE)
        before = self.observe(label + "-before")
        self.adb.root("sync")
        if shutdown:
            self.adb.root("am start -a android.intent.action.ACTION_REQUEST_SHUTDOWN --ez android.intent.extra.KEY_CONFIRM false")
        else:
            self.adb.run("reboot")
        deadline = time.monotonic() + 90
        while self.adb.run("get-state", check=False, timeout=10).stdout.strip() == "device":
            if time.monotonic() >= deadline:
                raise CaptureError("No ADB disconnect after power-cycle request")
            time.sleep(1)
        if shutdown:
            print("Confirm Android has fully shut down, not merely lost USB. Do not power on yet.", flush=True)
            if input("Type OFF after observing shutdown: ").strip().upper() != "OFF":
                raise CaptureError("Physical shutdown was not confirmed")
            until = time.monotonic() + self.args.off_seconds
            while time.monotonic() < until:
                if self.adb.run("get-state", check=False, timeout=10).stdout.strip() == "device":
                    raise CaptureError("Device returned during the powered-off hold")
                time.sleep(2)
            self.report["cases"].append({"name": label + "-off-hold", "operator_confirmed_shutdown": True,
                                         "adb_absent_seconds_at_least": self.args.off_seconds})
            self.save()
            print("Powered-off hold complete. Power on and unlock the phone now.", flush=True)
        self.wait_online()
        if self.clock()["boot"] == before["boot"]:
            raise CaptureError("ADB reconnect was not a real kernel restart")
        # Tamper BEFORE first game initialization in the new boot, too.
        self.change_clock(31536000 if not shutdown else -31536000)
        self.launch(label, before, power_cycle=True)

    def restore(self):
        self.wait_online()
        self.adb.run("shell", "am", "force-stop", PACKAGE)
        self.set_clock(self.original_now())
        for key, value in self.recovery["settings"].items():
            args = ("delete", "global", key) if value == "null" else ("put", "global", key, value)
            self.adb.run("shell", "settings", *args)
            if self.setting(key) != value:
                raise CaptureError("Could not restore " + key)
        self.recovery["restored"] = True
        (self.output / "clock-recovery.json").write_text(json.dumps(self.recovery, indent=2), encoding="utf-8")

    def run(self):
        self.nav = navigation(self.args.navigation)
        self.preflight()
        wall = self.clock()["wall"]
        if any(not 31536000 <= wall + offset < 2114380800 for offset in (0, *OFFSETS)):
            raise CaptureError("Restore a normal device date before testing; campaign would exceed the 32-bit clock range")
        self.recovery = {"serial": self.args.serial, "device_wall": wall,
                         "host_wall": time.time(), "restored": False,
                         "settings": {key: self.setting(key)
                                      for key in ("auto_time", "auto_time_zone")}}
        (self.output / "clock-recovery.json").write_text(json.dumps(self.recovery, indent=2), encoding="utf-8")
        try:
            for key in self.recovery["settings"]:
                self.adb.run("shell", "settings", "put", "global", key, "0")
                if self.setting(key) != "0":
                    raise CaptureError("Automatic time control was not disabled")
            before = self.report["baseline"]
            # If a phone reboot predates this run, first establish its baseline.
            self.launch("initial", before, power_cycle=before["timer"]["boot"] != before["boot"])
            print("STRESS_READY: initial cooldown and navigation verified", flush=True)
            for cycle in range(self.args.cycles):
                for offset in OFFSETS:
                    label = f"cycle-{cycle + 1}-offset-{offset}"
                    before = self.observe(label + "-before")
                    self.adb.run("logcat", "-c")
                    self.change_clock(offset)
                    self.replay(self.nav["probe"])
                    time.sleep(2)
                    warm = self.observe(label + "-warm")
                    check_transition(before, warm, power_cycle=False)
                    self.screen(label + "-warm")
                    self.logs(label + "-warm")
                    if not process_snapshot(self.adb)["running"]:
                        raise CaptureError("App exited during calendar-change probe")
                    self.report["cases"].append({"name": label + "-warm", "before": before, "after": warm, "passed": True})
                    self.save()
                    print(f"CASE_PASS {label}-warm: saved_remaining={warm['timer']['remaining']}", flush=True)
                    self.adb.run("shell", "am", "force-stop", PACKAGE)
                    self.change_clock(-offset)
                    self.launch(label + "-cold", warm)
                self.change_clock(31536000)
                self.power_cycle(f"reboot-{cycle + 1}", shutdown=False)
            for cycle in range(self.args.shutdowns):
                self.change_clock(-31536000)
                self.power_cycle(f"shutdown-{cycle + 1}", shutdown=True)
            self.report["status"] = "passed"
        except BaseException as error:
            self.report["campaign_error"] = f"{type(error).__name__}: {error}"
            raise
        finally:
            self.restore()
            self.save()

    def calibrate(self):
        self.preflight()
        self.bootstrap()
        time.sleep(self.args.launch_wait)
        self.screen("calibration-start")
        from PIL import Image
        with Image.open(self.output / "calibration-start.png") as image:
            width, height = image.size
        steps = {"width": width, "height": height, "open": [], "probe": []}
        print("View the saved screenshots. Enter input actions: tap X Y; swipe X1 Y1 X2 Y2 MS; wait SECONDS.")
        print("OPEN phase: navigate from freshly launched main menu to Eve's active cooldown.")
        for phase in ("open", "probe"):
            print(f"Phase {phase}: enter actions, then DONE. Probe must attempt the blocked gift, not buy/equip anything.")
            while True:
                line = input("> ").strip().split()
                if line == ["DONE"]:
                    if not steps[phase]:
                        raise CaptureError("Each phase needs at least one actual input action")
                    break
                if not line:
                    continue
                action = [line[0], *(float(v) if line[0] == "wait" else int(v) for v in line[1:])]
                validate_action(action, width, height)
                steps[phase].append(action)
                self.replay([action])
                self.screen(f"calibration-{phase}-{len(steps[phase])}")
            if phase == "open":
                observed = self.observe("calibration-open")
                if observed["timer"]["boot"] != observed["boot"] or observed["uptime"] - observed["timer"]["sampled"] > 65:
                    raise CaptureError("Eve timer is not actively checkpointing; inspect navigation")
        self.logs("calibration")
        self.args.calibrate.write_text(json.dumps(steps, indent=2), encoding="utf-8")
        self.nav = navigation(self.args.calibrate)
        self.launch("calibration-replay", self.observe("calibration-before-replay"))
        self.report["status"] = "navigation-calibrated"
        self.save()
        self.adb.run("shell", "am", "force-stop", PACKAGE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--run", action="store_true")
    action.add_argument("--calibrate", type=Path, metavar="NAVIGATION_JSON")
    action.add_argument("--restore", type=Path, metavar="CLOCK_RECOVERY_JSON")
    parser.add_argument("--navigation", type=Path)
    parser.add_argument("--serial", default="4b53e568")
    parser.add_argument("--adb", type=Path, default=ADB)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cycles", type=int, default=3)
    parser.add_argument("--shutdowns", type=int, default=1)
    parser.add_argument("--off-seconds", type=int, default=60)
    parser.add_argument("--boot-timeout", type=int, default=600)
    parser.add_argument("--launch-wait", type=int, default=15)
    parser.add_argument("--ready", action="store_true", help="explicit readiness supplied by the operator/harness")
    args = parser.parse_args()
    if not any((args.run, args.calibrate, args.restore)):
        print(json.dumps({"mode": "plan-only; no ADB calls", "calendar_offsets_seconds": OFFSETS,
                          "cycles": args.cycles, "reboots": args.cycles, "shutdowns": args.shutdowns,
                          "requires": ["rooted S4, exact installed cooldown APK", "active cooldown >= 1 hour",
                                       "calibrated open/probe navigation", "manual power-on after full shutdown"],
                          "checks": ["warm and app-closed date/time changes", "new-boot tampering before first game launch",
                                     "exact saved remainder after reboot/shutdown", "no currency mutation or fatal errors"],
                          "safety": ["quiesced full save backup", "no save edits or shortened timer", "durable clock recovery",
                                     "restore original calendar offset and auto-time settings", "app stopped on completion"],
                          "not_covered": ["sudden battery removal or write-tearing", "actual six-hour expiry"]}, indent=2))
        return 0
    if args.run and not args.navigation:
        parser.error("--run requires --navigation from --calibrate")
    if not (1 <= args.cycles <= 20 and 1 <= args.shutdowns <= 10 and
            10 <= args.off_seconds <= 3600 and 60 <= args.boot_timeout <= 1800 and 1 <= args.launch_wait <= 60):
        parser.error("Invalid bounded campaign durations/counts")
    print("EVE COOLDOWN STRESS: watch for early gifts, reset/huge countdowns, crashes, and power-off prompts.", flush=True)
    if not args.ready:
        print(PROMPT, flush=True)
        if input().strip().lower() not in ("ready", "go", "start"):
            return 2
    args.output = args.output or Path("device-snapshots") / ("eve-stress-" + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime()))
    runner = Stress(args)
    try:
        if args.restore:
            runner.recovery = json.loads(args.restore.read_text(encoding="utf-8"))
            if runner.recovery["serial"] != args.serial:
                raise CaptureError("Recovery belongs to a different device")
            runner.restore()
            args.restore.write_text(json.dumps(runner.recovery, indent=2), encoding="utf-8")
            runner.report["status"] = "clock-restored"
        elif args.calibrate:
            runner.calibrate()
        else:
            runner.run()
    except (Exception, KeyboardInterrupt) as error:
        runner.report["status"] = "failed"
        runner.report["error"] = f"{type(error).__name__}: {error}"
        print(runner.report["error"], flush=True)
        if runner.recovery and not runner.recovery.get("restored"):
            print(f"CLOCK RECOVERY REQUIRED: python stress_eve_cooldown.py --restore {runner.output / 'clock-recovery.json'} --serial {args.serial}", flush=True)
        return 1
    finally:
        if "apk_sha256" in runner.report or runner.report["status"] == "clock-restored":
            try:
                stopped = runner.adb.run("shell", "am", "force-stop", PACKAGE, check=False, timeout=15)
                runner.report["final_force_stop_succeeded"] = stopped.returncode == 0
            except CaptureError as error:
                runner.report["final_force_stop_error"] = str(error)
        runner.save()
    print(json.dumps({"status": runner.report["status"], "results": str(runner.output / "results.json")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
