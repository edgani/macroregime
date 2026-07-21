"""Compatibility entrypoint. v2.5 deployment checks are superseded by v2.7 shell/bootstrap tests."""
from __future__ import annotations
import json
from pathlib import Path
import validate_v27_full as v
HERE = Path(__file__).resolve().parent
try:
    v.app_shell_check()
    v.app_fresh_boot_check()
    ok = all(row.get("passed") for row in v.RESULTS)
    report = {"version": "2.7", "status": "PASS" if ok else "FAIL", "checks": v.RESULTS}
except Exception as exc:
    report = {"version": "2.7", "status": "FAIL", "error": f"{type(exc).__name__}: {exc}", "checks": v.RESULTS}
(HERE / "V27_DEPLOYMENT_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(0 if report["status"] == "PASS" else 1)
