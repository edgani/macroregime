"""User-machine validation for V5.9 position lifecycle continuation."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
COMMANDS = [
    ("manifest", [sys.executable, "verify_manifest_v59.py"], 180),
    ("v59_contracts", [sys.executable, "validate_v59_position_lifecycle.py"], 900),
    ("ui_contracts", [sys.executable, "validate_v42_deep_reaudit.py"], 600),
    ("synthetic_snapshot", [sys.executable, "run.py", "--synthetic", "--markets", "us,idx,crypto,commodity,fx", "--out", "runtime/v59_desk.json", "--html", "runtime/v59_dashboard.html"], 600),
]

def main() -> int:
    rows = []
    for name, cmd, timeout in COMMANDS:
        try:
            proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
            rows.append({"name": name, "status": "PASS" if proc.returncode == 0 else "FAIL", "returncode": proc.returncode, "output_tail": (proc.stdout + "\n" + proc.stderr)[-12000:]})
        except subprocess.TimeoutExpired as exc:
            rows.append({"name": name, "status": "FAIL", "returncode": None, "output_tail": f"timeout:{exc}"})
    report = {
        "schema": "warroom.user_validation.v59",
        "status": "PASS" if all(row["status"] == "PASS" for row in rows) else "FAIL",
        "predictive_components_promoted_to_live": 0,
        "capital_permission": "BLOCKED",
        "tests": rows,
    }
    (ROOT / "V59_USER_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "tests"}, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
