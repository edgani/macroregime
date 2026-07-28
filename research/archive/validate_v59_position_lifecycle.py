"""Focused V5.9 source and contract validation."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def run(name: str, cmd: list[str], timeout: int = 300) -> dict:
    try:
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        return {
            "name": name,
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode,
            "output_tail": (proc.stdout + "\n" + proc.stderr)[-12000:]
        }
    except subprocess.TimeoutExpired as exc:
        return {"name": name, "status": "FAIL", "returncode": None, "output_tail": f"timeout:{exc}"}


def static_checks() -> list[dict]:
    checks = []
    text = (ROOT / "gcfis/orchestrator.py").read_text(encoding="utf-8")
    final = (ROOT / "gcfis/meta/final_desk.py").read_text(encoding="utf-8")
    lifecycle = (ROOT / "position_lifecycle.py").read_text(encoding="utf-8")
    registry = json.loads((ROOT / "COMPONENT_PROOF_REGISTRY_DEFAULT.json").read_text())
    formula = json.loads((ROOT / "FORMULA_AND_SELECTOR_REGISTER.json").read_text())
    oil = json.loads((ROOT / "V59_OIL_2026_CASE_AUDIT.json").read_text())

    def add(name: str, ok: bool, detail: str = "") -> None:
        checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

    add("surge_before_signal_serialization", text.find('a["surge"] = run_surge') < text.find("sig.surge ="))
    add("final_desk_receives_master_rows", 'build_final_desk(_final_ranking' in text)
    add("surge_removed_from_desk_score", "surge" not in final[final.find("def _score"):final.find("def build_final_desk")])
    add("lifecycle_zero_live_weight", "LIVE_DECISION_WEIGHT = 0.0" in lifecycle)
    add("lifecycle_capital_blocked", 'CAPITAL_PERMISSION = "BLOCKED"' in lifecycle)
    add("price_oi_claim_ambiguous", "cannot prove long accumulation" in lifecycle)
    add("top_requires_signed_distribution", "and signed_selling" in lifecycle and "and weakening_votes >= 1" in lifecycle)
    add("registry_contains_v59", "position_lifecycle_v59" in json.dumps(registry))
    add("formula_register_contains_v59", "position_lifecycle_v59" in json.dumps(formula))
    add("oil_prewar_not_accumulation", oil["verdict"]["prewar_clean_long_accumulation"] == "NOT_DETECTED")
    add("oil_current_top_not_confirmed", oil["verdict"]["current_top"] == "NOT_CONFIRMED")
    add("oil_war_prediction_forbidden", oil["verdict"]["war_prediction_claim"] == "FORBIDDEN")
    return checks


def main() -> int:
    tests = static_checks()
    tests.extend([
        run("compile", [sys.executable, "-m", "compileall", "-q", "."], 240),
        run("lifecycle_adversarial", [sys.executable, "-m", "pytest", "-q", "hardening_tests/test_position_lifecycle_v59.py"], 240),
        run("gcfis_contracts", [sys.executable, "gcfis/tests/test_all.py"], 300),
        run("v58_research_regression", [sys.executable, "validate_v58_exhaustive_research.py"], 300),
        run("live_stack_regression", [sys.executable, "validate_live_stack.py"], 300),
    ])
    report = {
        "schema": "warroom.validation.v59.position_lifecycle",
        "status": "PASS" if all(row["status"] == "PASS" for row in tests) else "FAIL",
        "tests_passed": sum(row["status"] == "PASS" for row in tests),
        "tests_total": len(tests),
        "live_predictive_components_promoted": 0,
        "capital_permission": "BLOCKED",
        "tests": tests,
    }
    (ROOT / "V59_SOURCE_VALIDATION.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "tests"}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
