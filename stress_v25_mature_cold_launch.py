from pathlib import Path


source_path = Path("stress_v21_mature_cold_launch.py")
source = source_path.read_text(encoding="utf-8")
old_output = "native-patches/v21-response-index-hardening/stage-b-mature-cold-starts"
new_output = "native-patches/v25-ranking-template/evidence/mature-cold-starts"
if old_output not in source:
    raise SystemExit(f"expected harness token not found: {old_output}")
source = source.replace(old_output, new_output)

exec(compile(source, str(source_path), "exec"))
