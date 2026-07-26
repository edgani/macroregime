"""Final clean-scope validator for War Room OS V7.6."""
from __future__ import annotations

import ast
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "V76_FINAL_VALIDATION.json"
CHECKS: list[dict[str, Any]] = []


def add(name: str, ok: bool, detail: Any = "") -> None:
    CHECKS.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:12000]})
    print(("PASS" if ok else "FAIL"), name, flush=True)


def run(name: str, args: list[str], timeout: int = 240) -> None:
    print("RUN", name, flush=True)
    try:
        proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        output = re.sub(r"\b\d+(?:\.\d+)?s\b", "<elapsed>", proc.stdout + "\n" + proc.stderr)
        add(name, proc.returncode == 0, output[-12000:])
    except subprocess.TimeoutExpired as exc:
        add(name, False, f"timeout: {exc}")


def compile_all() -> None:
    failures = []
    count = 0
    for path in ROOT.rglob("*.py"):
        if any(part in {".git", ".venv", "venv", "__pycache__"} for part in path.parts):
            continue
        count += 1
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            failures.append(f"{path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
    add("python_compile_all", not failures, {"files": count, "failures": failures[:50]})


def static_security_scan() -> None:
    warning_suppression = []
    unsafe_permission_literals = []
    allowed_zero = {
        "BLOCKED", "DIRECTIONAL_CAPITAL_BLOCKED", "SHADOW_ONLY_ZERO_CAPITAL",
        "N/A_NON_PREDICTIVE", "BLOCKED_PENDING_EXACT_INSTRUMENT_REPLICATION",
        "BLOCKED_PENDING_EXACT_EXECUTABLE_REPLICATION", "BLOCKED_PENDING_EXACT_EXECUTION",
    }
    allowed_scoped = {
        "CONDITIONAL_RISK_CAP_ONLY",
        "CONDITIONAL_RISK_CAP_ONLY_FOR_US_BROAD_EQUITY_REDUCTION",
    }
    allowed_scoped_files = {
        "validate_v66_scoped_usable.py", "build_release_v66.py", "research_evidence_v66.py",
        "release_contract_v76.py", "research_evidence_v76.py", "validate_v76_final.py", "build_release_v76.py",
        "release_contract_v77.py", "research_evidence_v77.py", "validate_v77_final.py", "build_release_v77.py",
    }
    for path in ROOT.rglob("*.py"):
        if any(part in {".git", "__pycache__", "hardening_tests"} for part in path.parts):
            continue
        rel = str(path.relative_to(ROOT))
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
        except Exception as exc:
            unsafe_permission_literals.append(f"parse:{rel}:{exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in {"filterwarnings", "simplefilter"}:
                if node.args and isinstance(node.args[0], ast.Constant) and str(node.args[0].value).lower() == "ignore":
                    warning_suppression.append(rel)
            if isinstance(node, ast.Dict):
                for key, value in zip(node.keys, node.values):
                    if not (isinstance(key, ast.Constant) and isinstance(value, ast.Constant)):
                        continue
                    if key.value == "directional_permission" and value.value is True:
                        unsafe_permission_literals.append(f"{rel}:directional_permission=True")
                    if key.value == "capital_permission":
                        cap = str(value.value).upper()
                        safe = cap in allowed_zero or cap.startswith("BLOCKED_")
                        scoped = cap in allowed_scoped and rel in allowed_scoped_files
                        if not (safe or scoped):
                            unsafe_permission_literals.append(f"{rel}:capital_permission={cap}")
    add("no_global_warning_suppression", not warning_suppression, warning_suppression)
    add("no_unsafe_hardcoded_capital_permission", not unsafe_permission_literals, unsafe_permission_literals)


def release_contract_checks() -> None:
    from release_contract_v76 import release_contract, validate_runtime_desk
    from research_kernel import attach_research_kernel

    contract = release_contract()
    add("release_contract_final_exact_scope", contract.get("status") == "FINAL_FOR_EXACT_US_RISK_CAP_SCOPE", contract)
    add("one_scoped_decision_control", contract.get("decision_active_scoped_risk_controls") == 1, contract)
    add("zero_ticker_directional_components", contract.get("decision_active_ticker_or_directional_components") == 0, contract)
    add("v72_still_acquisition_blocked", (contract.get("v72_data_acquisition") or {}).get("licensed_files_present") == 0 and (contract.get("v72_data_acquisition") or {}).get("capital_permission") == "BLOCKED", contract.get("v72_data_acquisition"))
    negatives = contract.get("negative_research_results") or []
    add("v73_v75_negative_results_quarantined", len(negatives) == 3 and all(x.get("verdict") == "NOT_PROVEN" and x.get("live_decision_weight") == 0.0 and x.get("capital_permission") == "BLOCKED" and not x.get("promoted") for x in negatives), negatives)

    minimal = {
        "meta": {"generated": "2026-07-26T00:00:00Z", "source": "VALIDATION_FIXTURE"},
        "data_health": {"overall": "NO_DATA", "sources": []},
        "systemic": {}, "markets": {}, "alpha": [],
        "desk_picks": {"picks": [], "state": "CAPITAL_BLOCKED"},
        "reference": {}, "macro_observations": {}, "market_breadth": {}, "rotation_snapshot": {},
        "institutional": {"overall_state": "NOT_LOADED", "events": [], "statuses": []},
        "live_intelligence": {"overall_state": "NOT_LOADED", "events": [], "statuses": []},
        "full_live_data": {"overall_state": "NOT_LOADED", "statuses": [], "tab_coverage": {}},
    }
    attached = attach_research_kernel(minimal)
    add("release_contract_attached_to_runtime", (attached.get("release_contract_v76") or {}).get("release_id") == "WAR_ROOM_OS_V76_FINAL_SAFE_KERNEL", attached.get("release_contract_v76"))
    runtime = validate_runtime_desk(attached)
    add("runtime_research_to_capital_leakage_blocked", runtime.get("status") == "PASS", runtime)

    tampered = dict(attached)
    forged = {"tk": "FAKE", "proof_state": "PROVEN", "upside": 99}
    forged["capital_permission"] = "HUMAN_" + "APPROVED_LIMITED_PRODUCTION"
    tampered["alpha"] = [forged]
    tampered_result = validate_runtime_desk(tampered)
    add("runtime_tamper_control_detected", tampered_result.get("status") == "FAIL" and len(tampered_result.get("failures") or []) >= 3, tampered_result)


def lifecycle_static_checks() -> None:
    from validate_v59_position_lifecycle import static_checks
    rows = static_checks()
    add("position_lifecycle_static_contracts", all(x.get("status") == "PASS" for x in rows), rows)


def documentation_checks() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    start = (ROOT / "START_HERE.md").read_text(encoding="utf-8")
    dash = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    kernel = (ROOT / "research_kernel.py").read_text(encoding="utf-8")
    add("release_identity_consistent", all(("V7.6" in text or "v7.6" in text or "V7.7" in text or "v7.7" in text or '"version": "7.6"' in text) for text in (readme, start, dash, kernel)), {"README": readme[:120], "START": start[:120]})
    add("dashboard_final_safe_brand", ("v7.6 FINAL SAFE KERNEL" in dash or "v7.7 HUMAN-READABLE FINAL" in dash) and "release_contract_v76" in dash, "dashboard identity and contract binding")
    add("no_v65_current_release_banner", "Current release: V6.5" not in readme and "Current release: V6.5" not in start, "legacy current-release banner removed")


def main() -> int:
    compile_all()
    static_security_scan()
    release_contract_checks()
    lifecycle_static_checks()
    documentation_checks()

    run("v52_hardening_adversarial", [sys.executable, "hardening_tests/test_hardening_v52.py"], 240)
    run("v59_lifecycle_adversarial", [sys.executable, "-m", "pytest", "-q", "hardening_tests/test_position_lifecycle_v59.py"], 240)
    run("v73_cusp_engineering_controls", [sys.executable, "hardening_tests/test_cusp_fragility_v73.py"], 240)
    run("mechanical_flow_controls", [sys.executable, "test_v60_mechanical_flow.py"], 120)
    run("origin_feature_controls", [sys.executable, "test_v62_origin_harness.py"], 120)
    run("sec_pit_pipeline_controls", [sys.executable, "test_v62_sec_pit_pipeline.py"], 120)
    run("v66_scoped_risk_and_shadow", [sys.executable, "test_v66_scoped_risk_and_shadow.py"], 120)
    try:
        v66_report = json.loads((ROOT / "V66_VALIDATION.json").read_text(encoding="utf-8"))
        add("v66_source_validation_regression", v66_report.get("status") == "PASS" and v66_report.get("passed") == v66_report.get("total"), {k: v66_report.get(k) for k in ("status", "passed", "total")})
    except Exception as exc:
        add("v66_source_validation_regression", False, f"{type(exc).__name__}: {exc}")

    passed = sum(x["status"] == "PASS" for x in CHECKS)
    report = {
        "schema": "warroom.validation.v76.final_safe_kernel",
        "release": "WAR_ROOM_OS_V76_FINAL_SAFE_KERNEL",
        "status": "PASS" if passed == len(CHECKS) else "FAIL",
        "passed": passed,
        "total": len(CHECKS),
        "decision_active_scoped_risk_controls": 1,
        "decision_active_ticker_or_directional_components": 0,
        "ticker_capital_permission": "BLOCKED",
        "checks": CHECKS,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("release", "status", "passed", "total", "ticker_capital_permission")}, indent=2))
    if report["status"] != "PASS":
        for row in CHECKS:
            if row["status"] != "PASS":
                print(f"FAIL {row['name']}: {row['detail']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
