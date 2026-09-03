from pathlib import Path
import os


source_path = Path("stress_v22_first_read_faults.py")
source = source_path.read_text(encoding="utf-8")
selected_case = os.environ.get("STAGE_C_CASE")
run_name = selected_case or "batch"
output_path = f"native-patches/v25-ranking-template/evidence/first-read-faults/{run_name}"
replacements = {
    "native-patches/v22-first-read-recovery/stage-c-first-read-faults":
        output_path,
    "/data/local/tmp/v22-stage-c-": "/data/local/tmp/v25-stage-c-",
    "/data/local/tmp/v21-stage-c-": "/data/local/tmp/v25-stage-c-",
}
for old, new in replacements.items():
    if old not in source:
        raise SystemExit(f"expected harness token not found: {old}")
    source = source.replace(old, new)

exec(compile(source, str(source_path), "exec"))
