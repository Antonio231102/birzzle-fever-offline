from pathlib import Path


source_path = Path("stress_v22_first_read_faults.py")
source = source_path.read_text(encoding="utf-8")
replacements = {
    "native-patches/v22-first-read-recovery/stage-c-first-read-faults":
        "native-patches/v24-connectivity-independent/evidence/first-read-faults",
    "/data/local/tmp/v22-stage-c-": "/data/local/tmp/v24-stage-c-",
    "/data/local/tmp/v21-stage-c-": "/data/local/tmp/v24-stage-c-",
}
for old, new in replacements.items():
    if old not in source:
        raise SystemExit(f"expected harness token not found: {old}")
    source = source.replace(old, new)

exec(compile(source, str(source_path), "exec"))
