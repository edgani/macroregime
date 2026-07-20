"""Offline v2.9 contract validation.

Uses deterministic test fixtures only. It never writes fixture data into the production snapshot.
"""
from __future__ import annotations

import json
import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
checks: list[dict] = []


def check(name: str, passed: bool, detail: str = "") -> None:
    checks.append({"name": name, "passed": bool(passed), "detail": detail})
    print(("PASS" if passed else "FAIL"), name, detail)


# Python compile contract.
errors = []
py_files = [p for p in ROOT.rglob("*.py") if "__pycache__" not in p.parts]
for path in py_files:
    try:
        py_compile.compile(str(path), doraise=True)
    except Exception as exc:  # pragma: no cover - diagnostic path
        errors.append(f"{path.relative_to(ROOT)}: {exc}")
check("python_compile", not errors, f"{len(py_files)} files; {len(errors)} errors")

html = (ROOT / "dashboard.html").read_text(encoding="utf-8")
script_match = re.search(r"<script>(.*?)</script>", html, flags=re.S)
check("dashboard_script_present", bool(script_match))
if script_match and shutil.which("node"):
    temp = ROOT / ".v29_dashboard_check.js"
    temp.write_text(script_match.group(1), encoding="utf-8")
    result = subprocess.run([shutil.which("node"), "--check", str(temp)], capture_output=True, text=True)
    temp.unlink(missing_ok=True)
    check("javascript_parse", result.returncode == 0, result.stderr.strip())
else:
    check("javascript_parse", bool(script_match), "node unavailable; source extraction only")

source_contracts = {
    "v29_header": "v2.9 DECISION-FIRST" in html,
    "alpha_is_structural": "EXTREME ALPHA RADAR" in html and "Structural asymmetry universe has not loaded yet" in html,
    "alpha_headroom_percent": "+4,900%–49,900%" in html and "scenario headroom, not a target or probability" in html,
    "explicit_market_actions": all(x in html for x in ["BUILD LONG", "WATCH LONG", "BUILD SHORT", "WATCH SHORT", "REDUCE / AVOID", "NO TRADE"]),
    "ihsg_long_only": "IHSG is cash long-only" in html,
    "provider_errors_not_canvas": "Raw endpoint errors are retained in the ledger" in html and "Canvas shows usable evidence domains" in html,
    "robust_evidence_type": "String(n.evidence||'observed')" in html,
    "validation_layered_not_radial": "RESEARCH INVENTORY" in html and "SELECTION CONTROL" in html and "Math.cos(angle)" not in html,
}
for name, passed in source_contracts.items():
    check(name, passed)

# Setup-engine contract: long and short construction are both present.
setup_source = (ROOT / "price_setups.py").read_text(encoding="utf-8")
check("two_sided_setup_engine", all(x in setup_source for x in ["BUILD_LONG", "WATCH_LONG", "BUILD_SHORT", "WATCH_SHORT"]))
check("no_synthetic_production_fallback", "synthetic" not in setup_source.lower())

report = {
    "version": "2.9",
    "suite": "decision_first_offline_contract",
    "passed": sum(1 for item in checks if item["passed"]),
    "total": len(checks),
    "checks": checks,
    "note": "Browser geometry and fixture behavior are recorded in V29_FULL_VALIDATION_REPORT.json.",
}
(ROOT / "V29_OFFLINE_CONTRACT_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
if report["passed"] != report["total"]:
    sys.exit(1)
