"""Full validator for War Room OS V7.8 Proof Expansion Checkpoint."""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "V78_FINAL_VALIDATION.json"
CHECKS: list[dict[str, Any]] = []


def add(name: str, ok: bool, detail: Any = "") -> None:
    CHECKS.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:12000]})
    print(("PASS" if ok else "FAIL"), name, flush=True)


def run(name: str, args: list[str], timeout: int = 300) -> None:
    try:
        proc = subprocess.run(args, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        output = re.sub(r"\b\d+(?:\.\d+)?s\b", "<elapsed>", proc.stdout + "\n" + proc.stderr)
        output = output.replace(str(ROOT), "<ROOT>")
        add(name, proc.returncode == 0, output[-12000:])
    except Exception as exc:
        add(name, False, f"{type(exc).__name__}: {exc}")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_checks() -> None:
    pairs = [
        ("research_v78/protocols/V78_CROSS_MARKET_TSMOM_PROTOCOL_FROZEN.json", "research_v78/protocols/V78_CROSS_MARKET_TSMOM_PROTOCOL_FROZEN.sha256.txt"),
        ("research_v78/protocols/V78_CROSS_MARKET_SMA10_RISK_CAP_PROTOCOL_FROZEN.json", "research_v78/protocols/V78_CROSS_MARKET_SMA10_RISK_CAP_PROTOCOL_FROZEN.sha256.txt"),
        ("research_v78/protocols/V78_POINT_IN_TIME_TICKER_PROOF_PROTOCOL_FROZEN.json", "research_v78/protocols/V78_POINT_IN_TIME_TICKER_PROOF_PROTOCOL_FROZEN.sha256.txt"),
        ("research_v78/protocols/V78_PROSPECTIVE_SHADOW_PROTOCOL_FROZEN.json", "research_v78/protocols/V78_PROSPECTIVE_SHADOW_PROTOCOL_FROZEN.sha256.txt"),
        ("research_v78/protocols/V78_US_EQUITY_VOL12_RISK_CAP_PROTOCOL_FROZEN.json", "research_v78/protocols/V78_US_EQUITY_VOL12_RISK_CAP_PROTOCOL_FROZEN.sha256.txt"),
    ]
    for protocol_rel, receipt_rel in pairs:
        protocol, receipt = ROOT / protocol_rel, ROOT / receipt_rel
        declared = receipt.read_text(encoding="utf-8").split()[0] if receipt.exists() else ""
        add(f"protocol_hash_{protocol.stem}", protocol.exists() and declared == sha256(protocol), {"declared": declared, "actual": sha256(protocol) if protocol.exists() else None})
    pit = json.loads((ROOT / "research_v78/protocols/V78_POINT_IN_TIME_TICKER_PROOF_PROTOCOL_FROZEN.json").read_text(encoding="utf-8"))
    add("pit_candidate_family_bounded_three", len(pit.get("candidate_family_frozen") or []) == 3 and all(int(x.get("free_parameters", -1)) == 0 for x in pit.get("candidate_family_frozen") or []), pit.get("candidate_family_frozen"))
    add("pit_protocol_forbids_current_constituent_bias", "using current constituents for historical dates" in (pit.get("forbidden_after_freeze") or []), pit.get("forbidden_after_freeze"))
    add("pit_protocol_requires_prospective_200_four_regimes", (pit.get("ticker_level_acceptance") or {}).get("prospective_frozen_forecasts_min") == 200 and (pit.get("ticker_level_acceptance") or {}).get("distinct_regimes_min") == 4, pit.get("ticker_level_acceptance"))


def result_checks() -> None:
    tsmom = list(csv.DictReader((ROOT / "research_v78/results/V78_CROSS_MARKET_TSMOM_SUMMARY.csv").open(newline="", encoding="utf-8")))
    sma = list(csv.DictReader((ROOT / "research_v78/results/V78_CROSS_MARKET_SMA10_RISK_CAP_SUMMARY.csv").open(newline="", encoding="utf-8")))
    vol = list(csv.DictReader((ROOT / "research_v78/results/V78_US_EQUITY_VOL12_RISK_CAP_SUMMARY.csv").open(newline="", encoding="utf-8")))
    add("tsmom_zero_of_five_promoted", len(tsmom) == 5 and all(x.get("status") == "NOT_PROMOTED" and float(x.get("live_decision_weight", -1)) == 0.0 for x in tsmom), tsmom)
    add("cross_market_sma10_zero_of_three_promoted", len(sma) == 3 and all(x.get("status") == "NOT_PROMOTED" and float(x.get("live_decision_weight", -1)) == 0.0 for x in sma), sma)
    add("vol12_not_promoted", len(vol) == 1 and vol[0].get("status") == "NOT_PROMOTED" and vol[0].get("validation_pass") == "False" and vol[0].get("lockbox_pass") == "False", vol)
    receipt_pairs = [
        ("research_v78/results/V78_CROSS_MARKET_TSMOM_RESULTS.json", "research_v78/protocols/V78_CROSS_MARKET_TSMOM_PROTOCOL_FROZEN.json"),
        ("research_v78/results/V78_CROSS_MARKET_SMA10_RISK_CAP_RESULTS.json", "research_v78/protocols/V78_CROSS_MARKET_SMA10_RISK_CAP_PROTOCOL_FROZEN.json"),
        ("research_v78/results/V78_US_EQUITY_VOL12_RISK_CAP_RESULTS.json", "research_v78/protocols/V78_US_EQUITY_VOL12_RISK_CAP_PROTOCOL_FROZEN.json"),
    ]
    receipt_ok = True
    receipt_detail = []
    for result_rel, protocol_rel in receipt_pairs:
        result = json.loads((ROOT / result_rel).read_text(encoding="utf-8"))
        actual = sha256(ROOT / protocol_rel)
        receipt_detail.append({"result": result_rel, "declared": result.get("protocol_sha256"), "actual": actual})
        receipt_ok = receipt_ok and result.get("protocol_sha256") == actual
    add("confirmatory_result_protocol_receipts", receipt_ok, receipt_detail)
    matrix = json.loads((ROOT / "V78_COMPONENT_PROOF_MATRIX.json").read_text(encoding="utf-8"))
    add("v78_new_promoted_zero", matrix.get("new_promoted_components") == 0 and matrix.get("decision_active_ticker_or_directional_components") == 0, matrix)
    add("all_v78_confirmatory_capital_blocked", all(str(x.get("capital_permission")).startswith("BLOCKED") and float(x.get("live_decision_weight", -1)) == 0.0 for x in matrix.get("v78_confirmatory_components") or []), matrix.get("v78_confirmatory_components"))


def data_checks() -> None:
    membership = json.loads((ROOT / "research_v78/results/V78_SP500_MEMBERSHIP_GUARD_VALIDATION.json").read_text(encoding="utf-8"))
    add("membership_guard_pass", membership.get("status") == "PASS" and membership.get("rows") == 1259 and membership.get("unique_tickers") == 1206, membership)
    source = json.loads((ROOT / "research_v78/data/V78_SP500_MEMBERSHIP_SOURCE.json").read_text(encoding="utf-8"))
    actual = sha256(ROOT / "research_v78/data/sp500_ticker_start_end.csv")
    add("membership_source_hash_frozen", source.get("sha256") == actual == membership.get("sha256"), {"source": source.get("sha256"), "actual": actual})
    add("membership_guard_claim_ceiling", source.get("capital_permission") == "BLOCKED" and "production trading permission" in (source.get("not_sufficient_for") or []), source)
    fixture = json.loads((ROOT / "research_v78/results/V78_PIT_DATA_CONTRACT_FIXTURE_VALIDATION.json").read_text(encoding="utf-8"))
    add("pit_validator_fixture_pass_only", fixture.get("status") == "PASS" and fixture.get("proof_effect") == "DATA_CONTRACT_VERIFIED_ONLY" and fixture.get("capital_permission") == "BLOCKED_DATA_VALIDATION_ONLY", fixture)
    readiness = json.loads((ROOT / "V78_DATA_READINESS_MATRIX.json").read_text(encoding="utf-8"))
    add("real_pit_panel_explicitly_not_loaded", readiness.get("status") == "BLOCKED_BY_MISSING_LAWFUL_COMPLETE_PIT_PANEL" and all(x.get("sufficient_for_proof") is False for x in readiness.get("datasets") or []), readiness)


def contract_and_runtime_checks() -> None:
    from release_contract_v78 import release_contract, validate_runtime_desk
    from research_kernel import attach_research_kernel

    contract = release_contract()
    add("v78_contract_not_final", contract.get("status") == "PROOF_EXPANSION_CHECKPOINT_NOT_FINAL_TRADING_SYSTEM" and contract.get("final_trading_system") is False, contract)
    add("v78_contract_no_new_decision_component", contract.get("new_decision_active_components") == 0 and contract.get("global_ticker_capital_permission") == "BLOCKED", contract)
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
    add("v78_contract_attached", (attached.get("release_contract_v78") or {}).get("release_id") == "WAR_ROOM_OS_V78_PROOF_EXPANSION_CHECKPOINT", attached.get("release_contract_v78"))
    add("v78_evidence_attached", (attached.get("research_evidence_v78") or {}).get("new_promoted_components") == 0, attached.get("research_evidence_v78"))
    runtime = validate_runtime_desk(attached)
    add("v78_runtime_fail_closed", runtime.get("status") == "PASS" and runtime.get("ticker_capital_permission") == "BLOCKED", runtime)


def dashboard_checks() -> None:
    dash = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    static = (ROOT / "static/dashboard_live.html").read_text(encoding="utf-8")
    add("dashboard_static_synced", dash == static, {"dashboard": len(dash), "static": len(static)})
    add("dashboard_v78_not_final_brand", "v7.8 PROOF EXPANSION · NOT FINAL" in dash and "V7.8 CHECKPOINT · NOT FINAL" in dash, "brand")
    add("dashboard_v78_contract_binding", "release_contract_v78" in dash and "research_evidence_v78" in dash and "val_v78" in dash, "binding")
    scripts = re.findall(r"<script(?:[^>]*)>(.*?)</script>", dash, flags=re.S)
    js = scripts[-1] if scripts else ""
    tmp = ROOT / "runtime/_v78_dashboard_syntax_check.js"
    try:
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(js, encoding="utf-8")
        proc = subprocess.run(["node", "--check", str(tmp)], cwd=ROOT, capture_output=True, text=True, timeout=60)
        add("dashboard_javascript_syntax", proc.returncode == 0, proc.stdout + proc.stderr)
    finally:
        try: tmp.unlink()
        except Exception: pass


def docs_checks() -> None:
    status = (ROOT / "V78_CHECKPOINT_STATUS.md").read_text(encoding="utf-8")
    results = (ROOT / "V78_PROOF_EXPANSION_RESULTS.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    add("docs_reject_false_final_label", "NOT A FINAL PROVEN TRADING SYSTEM" in status and "not a final proven trading system" in results.lower(), "status/results")
    add("readme_current_v78_checkpoint", readme.startswith("# V7.8 CURRENT RELEASE STATUS") and "not a final proven trading system" in readme.lower(), readme[:500])
    add("docs_exact_inherited_permission", "US_SMA10_MONTHLY_RISK_CAP_V66" in status and "live weight `0.0`" in status, "scope")


def main() -> int:
    run("v77_full_regression", [sys.executable, "validate_v77_final.py"], 480)
    run("v78_focused_adversarial", [sys.executable, "test_v78_proof_expansion.py"], 120)
    run("v78_tsmom_reproduction", [sys.executable, "research_v78/code/run_cross_market_tsmom_confirmatory.py"], 480)
    run("v78_cross_market_sma10_reproduction", [sys.executable, "research_v78/code/run_cross_market_sma10_risk_cap.py"], 480)
    run("v78_vol12_reproduction", [sys.executable, "research_v78/code/run_us_equity_vol12_risk_cap.py"], 480)
    protocol_checks()
    result_checks()
    data_checks()
    contract_and_runtime_checks()
    dashboard_checks()
    docs_checks()
    run("python_compile_v78", [sys.executable, "-m", "py_compile", "release_contract_v78.py", "research_evidence_v78.py", "prospective_shadow_v78.py", "research_v78/data_acquisition/pit_data_contract_v78.py", "research_v78/data_acquisition/membership_guard_v78.py", "validate_v78_proof_expansion.py", "build_release_v78.py"], 120)

    passed = sum(x["status"] == "PASS" for x in CHECKS)
    report = {
        "schema": "warroom.validation.v78.proof_expansion_checkpoint",
        "release": "WAR_ROOM_OS_V78_PROOF_EXPANSION_CHECKPOINT",
        "status": "PASS" if passed == len(CHECKS) else "FAIL",
        "passed": passed,
        "total": len(CHECKS),
        "final_trading_system": False,
        "new_promoted_components": 0,
        "inherited_decision_active_scoped_risk_controls": 1,
        "decision_active_ticker_or_directional_components": 0,
        "ticker_capital_permission": "BLOCKED",
        "checks": CHECKS,
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("release", "status", "passed", "total", "final_trading_system", "ticker_capital_permission")}, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
