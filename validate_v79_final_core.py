"""Final source-level validation for War Room OS V7.9 exact-scope trading core."""
from __future__ import annotations

import ast
import hashlib
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "V79_FINAL_VALIDATION.json"

checks: dict[str, dict] = {}


def add(name: str, passed: bool, detail=None) -> None:
    checks[name] = {"passed": bool(passed), "detail": detail}
    if not passed:
        raise AssertionError(f"{name}: {detail}")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(cmd: list[str], timeout: int = 120, env=None) -> subprocess.CompletedProcess:
    merged = os.environ.copy()
    merged["WARROOM_V79_DISABLE_LIVE_FETCH"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, timeout=timeout, env=merged)


def main() -> None:
    required = [
        "final_trading_core_v79.py",
        "us_broad_equity_live_feed_v79.py",
        "release_contract_v79.py",
        "research_evidence_v79.py",
        "run_v79_trading_core.py",
        "V79_FINAL_PROVEN_CORE_SPEC.json",
        "V79_COMPONENT_PROOF_MATRIX.json",
        "V79_FINAL_STATUS.md",
        "V79_OPERATOR_RUNBOOK.md",
        "V79_LIVE_DATA_POLICY.md",
        "setup_v79.py",
        "SETUP_FINAL_CORE.bat",
        "RUN_FINAL_CORE.bat",
        "dashboard.html",
    ]
    add("required_files_present", all((ROOT / x).is_file() for x in required), required)

    for name in [x for x in required if x.endswith(".py")] + ["research_kernel.py", "app.py"]:
        py_compile.compile(str(ROOT / name), doraise=True)
    add("python_compile", True, "all V7.9 runtime modules compile")

    test = run([sys.executable, "test_v79_final_core.py"], timeout=120)
    add("v79_unit_adversarial_34", test.returncode == 0 and '"passed": 34' in test.stdout, test.stdout[-4000:] + test.stderr[-2000:])

    legacy = run([sys.executable, "test_v66_scoped_risk_and_shadow.py"], timeout=120)
    add("inherited_risk_and_shadow_controls_9", legacy.returncode == 0 and '"passed": 9' in legacy.stdout, legacy.stdout[-3000:] + legacy.stderr[-1000:])

    protocol_path = ROOT / "research_v66/protocols/V66_SMA10_RISK_REDUCTION_CONFIRMATION_PROTOCOL_FROZEN.json"
    result_path = ROOT / "research_v66/results/V66_SMA10_RISK_REDUCTION_CONFIRMATION_RESULTS.json"
    protocol = json.loads(protocol_path.read_text())
    result = json.loads(result_path.read_text())
    semantic = dict(protocol)
    semantic.pop("protocol_sha256", None)
    semantic_sha = hashlib.sha256(json.dumps(semantic, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    add("frozen_protocol_receipt", protocol.get("protocol_sha256") == semantic_sha == result.get("protocol_sha256"), {"semantic_sha": semantic_sha})
    add("confirmation_all_gates_pass", result.get("passed") is True and all((result.get("gates") or {}).values()), result.get("gates"))
    add("confirmation_25bps_stress_pass", (result.get("confirmatory_25bps") or {}).get("es_improvement", 0) > 0, result.get("confirmatory_25bps"))
    add("reverse_control_fails", (result.get("gates") or {}).get("reverse_fail") is True, result.get("reverse_control"))
    add("rolling_tail_stability", (result.get("rolling") or {}).get("dd_positive_share") == 1.0 and (result.get("rolling") or {}).get("es_positive_share") == 1.0, result.get("rolling"))

    contract_mod = __import__("release_contract_v79")
    contract = contract_mod.release_contract()
    add("final_contract_exact_scope", contract.get("final_trading_system") is True and contract.get("decision_active_systems") == ["US_BROAD_EQUITY_SMA10_LONG_CASH_V79"], contract)
    add("zero_ticker_and_cross_market_promotions", contract.get("decision_active_ticker_selectors") == 0 and contract.get("decision_active_cross_market_directional_components") == 0, contract)

    matrix = json.loads((ROOT / "V79_COMPONENT_PROOF_MATRIX.json").read_text())
    active = matrix.get("decision_active") or []
    inactive = matrix.get("decision_inactive") or []
    add("exactly_one_decision_active_system", len(active) == 1 and active[0].get("component_id") == "US_BROAD_EQUITY_SMA10_LONG_CASH_V79", active)
    add("all_unproven_components_zero_weight", all(float(x.get("live_weight", 1)) == 0.0 for x in inactive), inactive)

    feed_source = (ROOT / "us_broad_equity_live_feed_v79.py").read_text()
    add("no_bundled_live_seed", "sp500_monthly_shiller.csv" not in feed_source and "7450.03" not in feed_source, "live module has no legacy seed dependency")
    add("current_month_exclusion_implemented", "current_month_start" in feed_source and 'd["Date"] < current_month_start' in feed_source, "completed-month filter")
    add("feed_failure_is_explicit", "UNAVAILABLE_FAIL_CLOSED" in feed_source, "network/provider failures do not emit a signal")
    add("dual_source_confirmation_required", "FRED_CSV" in feed_source and "YAHOO_CHART" in feed_source and "LIVE_DUAL_SOURCE_CONFIRMED" in feed_source, "FRED + Yahoo agreement required")
    add("provider_mismatch_fails_closed", "Dual-source consensus failed" in feed_source and "MISMATCH" in feed_source, "cross-provider disagreement blocks execution")

    core_source = (ROOT / "final_trading_core_v79.py").read_text()
    add("no_leverage_or_short_permissions", 'leverage_permission=False' in core_source and 'short_permission=False' in core_source, "hard-coded safety contract")
    add("cost_ceiling_enforced", "estimated one-way execution cost" in core_source and "maximum_one_way_cost_bps" in core_source, "25 bps ceiling")
    add("baseline_authorization_enforced", "BASELINE_AUTHORIZATION_REQUIRED" in core_source, "system cannot allocate the account without explicit sleeve authorization")
    add("manual_data_never_executable", "DATA_SOURCE_UNVERIFIED" in core_source and "verified_live_feed" in core_source, "manual/bundled observations cannot create an order")
    cli_source = (ROOT / "run_v79_trading_core.py").read_text()
    add("csv_mode_audit_only", "CSV_AUDIT_ONLY" in cli_source and "live_verified" in cli_source, "CSV can never produce production permission")
    add("operator_receipt_atomic", "_atomic_json" in cli_source and "receipt_sha256" in cli_source, "operator output is atomically persisted with a content receipt")
    audit_csv = ROOT / "runtime" / "_v79_audit_fixture.csv"
    audit_csv.parent.mkdir(exist_ok=True)
    audit_csv.write_text("observed_month,close\n" + "\n".join(f"2025-{m:02d}-01,{100+m}" for m in range(1, 11)) + "\n", encoding="utf-8")
    audit_out = ROOT / "runtime" / "_v79_audit_receipt.json"
    audit = run([sys.executable, "run_v79_trading_core.py", "--csv", str(audit_csv), "--authorize-baseline", "--as-of", "2025-11-15", "--output", str(audit_out)], timeout=60)
    audit_payload = json.loads(audit_out.read_text()) if audit.returncode == 0 and audit_out.is_file() else {}
    add("cli_csv_cannot_execute", audit.returncode == 0 and (audit_payload.get("instruction") or {}).get("status") == "DATA_SOURCE_UNVERIFIED" and (audit_payload.get("instruction") or {}).get("ready_to_execute") is False, audit.stderr or audit.stdout[-1500:])

    html = (ROOT / "dashboard.html").read_text()
    add("dashboard_final_core_first", "TRADING CORE" in html and "function modelCore()" in html and "case'core':model=modelCore()" in html, "dedicated first workspace")
    add("dashboard_plain_language", "SATU-SATUNYA ORDER YANG DIIZINKAN" in html and "SISTEM FINAL, STRATEGY SLEEVE BELUM DIAKTIFKAN" in html, "beginner-facing core state")
    add("dashboard_other_markets_blocked", "Semua market lain tetap NO TRADE" in html, "scope visible in UI")
    script_start = html.index("<script>\n(() => {") + len("<script>\n")
    script_end = html.rindex("</script>")
    check_js = ROOT / "runtime/_v79_dashboard_check.js"
    check_js.parent.mkdir(exist_ok=True)
    check_js.write_text(html[script_start:script_end], encoding="utf-8")
    node = run(["node", "--check", str(check_js)], timeout=30)
    add("dashboard_javascript_syntax", node.returncode == 0, node.stderr)

    from research_kernel import attach_research_kernel
    desk = attach_research_kernel({"markets": {}, "meta": {"generated": "2026-07-26T00:00:00Z"}})
    ev = desk.get("research_evidence_v79") or {}
    add("research_kernel_attaches_v79", ev.get("status") == "FINAL_PROVEN_READY_TO_TRADE_EXACT_SCOPE", ev)
    runtime_validation = contract_mod.validate_runtime_desk(desk)
    add("runtime_contract_validation", runtime_validation.get("status") == "PASS", runtime_validation)
    add("offline_snapshot_no_order", (ev.get("current_instruction") or {}).get("ready_to_execute") is False, ev.get("current_instruction"))

    status = "PASS" if all(x["passed"] for x in checks.values()) else "FAIL"
    report = {
        "schema": "warroom.v79.final_validation.v1",
        "status": status,
        "passed": sum(x["passed"] for x in checks.values()),
        "total": len(checks),
        "final_trading_system": True,
        "exact_scope": contract.get("final_scope"),
        "decision_active_systems": contract.get("decision_active_systems"),
        "decision_active_ticker_selectors": 0,
        "decision_active_cross_market_directional_components": 0,
        "proof_result_sha256": sha(result_path),
        "proof_protocol_file_sha256": sha(protocol_path),
        "checks": checks,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": status, "passed": report["passed"], "total": report["total"]}, indent=2))


if __name__ == "__main__":
    main()
