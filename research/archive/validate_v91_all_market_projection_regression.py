"""V8.8 software/enforcement validation.

PASS here means the calculators and fail-closed gates behave as specified.  It never means a market
edge, target calibration or trading readiness has been proven.
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import ast
import json
import math
import py_compile
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from global_market_promotion_gate import evaluate_all
from market_projection_benchmark import evaluate as evaluate_benchmark
from market_projection_engine import project_payload
from promotion_gate_v88 import evaluate as evaluate_promotion
from proof_registry import attach_proof_registry
from runtime_sanitizer import sanitize_runtime_payload

H = "a" * 64
TESTS: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    TESTS.append({"name": name, "pass": bool(condition), "detail": detail})


def common(market: str, method: str, scenarios: list[dict]) -> dict:
    return {
        "projection_id": f"p-{market}", "narrative_id": f"n-{market}", "market": market,
        "instrument_id": f"i-{market}", "ticker": market.upper(), "as_of": "2026-07-01T00:00:00Z",
        "availability_max": "2026-06-30T23:59:00Z", "horizon_days": 365, "current_price": 10.0,
        "currency": "USD", "quote_convention": "currency per unit", "method": method,
        "bottleneck_claim": "point-in-time capacity or market-structure bottleneck",
        "beneficiary_value_capture": "explicit market-specific value recipient",
        "projection_reason": "activation and lagged supply response create a scenario valuation gap",
        "invalidation_rule": "pre-registered supply response or value-capture failure",
        "feature_domains": ["fundamentals", "bottleneck", "valuation", "causal_transmission"],
        "narrative_state": "REPRICING_READY_RESEARCH_CANDIDATE",
        "feature_snapshot_hash": H, "evidence_lineage_hash": H, "universe_snapshot_hash": H,
        "model_hash": H, "trial_ledger_hash": H, "narrative_state_hash": H,
        "scenarios": scenarios,
    }


def scenario(name: str, probability: float, drivers: dict) -> dict:
    return {"name": name, "probability": probability, "drivers": drivers, "evidence_ids": [f"e-{name}"], "assumptions": [f"frozen-{name}"]}


def requests() -> dict[str, dict]:
    return {
        "us": common("us", "equity_sales_bridge", [
            scenario("low", .25, {"baseline_revenue": 100, "bottleneck_incremental_revenue": 10, "sales_multiple": 1, "net_debt": 10, "non_operating_assets": 0, "diluted_shares": 10}),
            scenario("base", .50, {"baseline_revenue": 100, "bottleneck_incremental_revenue": 30, "sales_multiple": 1.5, "net_debt": 10, "non_operating_assets": 0, "diluted_shares": 10}),
            scenario("high", .25, {"baseline_revenue": 100, "bottleneck_incremental_revenue": 60, "sales_multiple": 2, "net_debt": 10, "non_operating_assets": 0, "diluted_shares": 10}),
        ]),
        "idx": common("idx", "equity_earnings_bridge", [
            scenario("low", .25, {"baseline_revenue": 100, "bottleneck_incremental_revenue": 10, "gross_margin": .30, "operating_expense": 20, "tax_rate": .20, "earnings_multiple": 8, "net_debt": 5, "non_operating_assets": 0, "diluted_shares": 10}),
            scenario("base", .50, {"baseline_revenue": 100, "bottleneck_incremental_revenue": 30, "gross_margin": .35, "operating_expense": 20, "tax_rate": .20, "earnings_multiple": 10, "net_debt": 5, "non_operating_assets": 0, "diluted_shares": 10}),
            scenario("high", .25, {"baseline_revenue": 100, "bottleneck_incremental_revenue": 60, "gross_margin": .40, "operating_expense": 20, "tax_rate": .20, "earnings_multiple": 12, "net_debt": 5, "non_operating_assets": 0, "diluted_shares": 10}),
        ]),
        "commodity": common("commodity", "commodity_scarcity_bridge", [
            scenario("low", .25, {"marginal_supply_cost": 50, "inventory_cover_days": 30, "normal_inventory_cover_days": 30, "scarcity_sensitivity": 1, "quality_basis": 0, "location_basis": 0, "freight_insurance": 2, "policy_premium": 0}),
            scenario("base", .50, {"marginal_supply_cost": 50, "inventory_cover_days": 24, "normal_inventory_cover_days": 30, "scarcity_sensitivity": 1, "quality_basis": 1, "location_basis": 1, "freight_insurance": 3, "policy_premium": 0}),
            scenario("high", .25, {"marginal_supply_cost": 50, "inventory_cover_days": 15, "normal_inventory_cover_days": 30, "scarcity_sensitivity": 1.2, "quality_basis": 2, "location_basis": 2, "freight_insurance": 5, "policy_premium": 2}),
        ]),
        "fx": common("fx", "fx_external_balance_bridge", [
            scenario("low", .25, {"fundamental_anchor_rate": 1, "log_adjustments": {"policy_path": -.02, "balance_of_payments": -.01, "terms_of_trade": 0, "global_liquidity": 0, "funding_stress": 0, "intervention": 0}}),
            scenario("base", .50, {"fundamental_anchor_rate": 1, "log_adjustments": {"policy_path": 0, "balance_of_payments": 0, "terms_of_trade": 0, "global_liquidity": 0, "funding_stress": 0, "intervention": 0}}),
            scenario("high", .25, {"fundamental_anchor_rate": 1, "log_adjustments": {"policy_path": .02, "balance_of_payments": .01, "terms_of_trade": 0, "global_liquidity": 0, "funding_stress": 0, "intervention": 0}}),
        ]),
        "crypto": common("crypto", "crypto_value_capture_bridge", [
            scenario("low", .25, {"baseline_annual_value_capture": 100, "bottleneck_incremental_value_capture": 0, "value_capture_multiple": 5, "treasury_value": 0, "monetary_premium": 0, "net_liabilities": 0, "projected_diluted_token_supply": 100}),
            scenario("base", .50, {"baseline_annual_value_capture": 100, "bottleneck_incremental_value_capture": 50, "value_capture_multiple": 8, "treasury_value": 100, "monetary_premium": 0, "net_liabilities": 0, "projected_diluted_token_supply": 100}),
            scenario("high", .25, {"baseline_annual_value_capture": 100, "bottleneck_incremental_value_capture": 100, "value_capture_multiple": 10, "treasury_value": 200, "monetary_premium": 100, "net_liabilities": 0, "projected_diluted_token_supply": 100}),
        ]),
    }


def benchmark_fixture() -> pd.DataFrame:
    rows = []
    markets = ["us", "idx", "commodity", "fx", "crypto"]
    start = pd.Timestamp("2023-01-01", tz="UTC")
    for market_index, market in enumerate(markets):
        for i in range(200):
            as_of = start + pd.DateOffset(days=4 * i)
            horizon = as_of + pd.DateOffset(days=180)
            regime = f"R{i % 4 + 1}"
            current = 100.0
            projected_return = -0.15 + 0.003 * (i % 150) + 0.01 * market_index
            base = current * (1 + projected_return)
            low = base * 0.78
            high = base * 1.22
            # 80% inside the interval; 20% deliberately outside to verify coverage calibration.
            if i % 10 == 0:
                realized = high * 1.12
            elif i % 10 == 1:
                realized = low * 0.88
            else:
                realized = base * math.exp(0.04 * math.sin(i))
            rows.append({
                "prediction_id": f"{market}-{i}", "market": market, "instrument_id": f"{market}-{i%40}",
                "as_of": as_of, "horizon_end": horizon, "regime": regime, "current_price": current,
                "target_low": low, "target_base": base, "target_high": high, "expected_target_price": base,
                "probability_low": .2, "probability_base": .6, "probability_high": .2,
                "realized_price": realized, "point_in_time_valid": True, "model_frozen_before_outcome": True,
                "projection_hash": H, "outcome_source_hash": H,
            })
    return pd.DataFrame(rows)


def promotion_fixture(market: str) -> dict:
    metrics = {
        "closed_trades": 250, "prospective_months": 30, "regime_count": 4,
        "real_net_profit_factor": 1.70, "profit_factor_bootstrap_95pct_lower": 1.30,
        "normal_max_drawdown": .12, "stress_max_drawdown": .18,
        "narrative_timing_ready_50pct_hit_rate_12m": .40,
        "narrative_incremental_hit_rate_vs_dormant": .18,
        "narrative_incremental_bootstrap_lower": .02,
        "narrative_median_days_to_50pct": 150, "narrative_median_mae": .20,
        "projection_count": 250, "projection_months": 30, "projection_regime_count": 4,
        "projection_median_abs_log_error": {"us": .25, "idx": .30, "commodity": .15, "fx": .08, "crypto": .35}[market],
        "projection_error_improvement_vs_no_change": .20,
        "projection_interval_coverage": .80, "projection_interval_coverage_upper": .80,
        "projection_scenario_brier": .15, "projection_direction_accuracy": .60,
        "projection_return_rank_correlation": .20, "projection_severe_loss_rate": .10,
    }
    if market in {"us", "idx", "crypto"}:
        metrics |= {"extreme_winner_recall_at_20": .30, "extreme_winner_recall_at_50": .50, "extreme_winner_precision_at_20": .10, "extreme_winner_median_remaining_return": 3.5, "mandatory_known_cases_captured": True}
    else:
        metrics |= {"large_move_recall_at_20": .30, "large_move_precision_at_20": .12}
    artifacts = {role: H for role in ["trial_ledger", "pit_dataset", "model", "holdout_result", "trade_ledger", "equity_ledger", "narrative_timing_benchmark", "projection_spec", "projection_benchmark", "review"]}
    artifacts["extreme_winner_benchmark" if market in {"us", "idx", "crypto"} else "large_move_benchmark"] = H
    return {
        "scope": {"market": market, "universe": "blind-universe", "direction": "long-short", "horizon": "frozen", "execution_method": "actual-fills"},
        "gates": {name: True for name in [
            "zero_technical_inputs", "complete_global_trial_ledger", "blind_signal_ids", "point_in_time_lineage",
            "frozen_model_before_holdout", "walk_forward_validation", "untouched_lockbox", "global_multiple_testing_correction",
            "post_cutoff_or_prospective_evidence", "calibration_pass", "false_alarm_pass", "remaining_return_lower_bound_positive",
            "actual_costs_borrow_impact_capacity", "realized_performance_gate_pass", "narrative_incremental_timing_pass",
            "market_specific_projection_pass", "bottleneck_value_bridge_pass", "projection_calibration_pass", "independent_reviewer_approval",
        ]},
        "metrics": metrics, "artifacts": artifacts,
    }


def main() -> int:
    reqs = requests()
    outputs = {market: project_payload(request) for market, request in reqs.items()}
    for market, result in outputs.items():
        check(f"{market} projection valid", result["valid"], str(result.get("errors")))
        check(f"{market} targets ordered", result["target_low"] <= result["target_base"] <= result["target_high"])
        check(f"{market} target has bridge reasons", all(s["reasons"] and s["bridge"].get("formula") for s in result["scenarios"]))
        check(f"{market} capital remains blocked", result["capital_permission"] == "BLOCKED")

    bad = deepcopy(reqs["us"]); bad["availability_max"] = "2026-07-02T00:00:00Z"
    check("future evidence rejected", not project_payload(bad)["valid"])
    bad = deepcopy(reqs["us"]); bad["feature_domains"].append("price_momentum")
    check("chart-derived predictor rejected", not project_payload(bad)["valid"])
    bad = deepcopy(reqs["us"]); bad["scenarios"][0]["probability"] = .30
    check("probabilities not summing to one rejected", not project_payload(bad)["valid"])
    bad = deepcopy(reqs["commodity"]); bad["method"] = "equity_sales_bridge"
    check("cross-market valuation method rejected", not project_payload(bad)["valid"])
    bad = deepcopy(reqs["crypto"]); bad["scenarios"][2]["drivers"]["projected_diluted_token_supply"] = 0
    check("zero diluted supply rejected", not project_payload(bad)["valid"])
    dormant = deepcopy(reqs["us"]); dormant["narrative_state"] = "STRUCTURAL_DORMANT"
    check("dormant bottleneck can be valued but is not timing ready", project_payload(dormant)["projection_status"] == "RESEARCH_PROJECTION_NOT_TIMING_READY")

    sanitized = sanitize_runtime_payload({"projection": {"target_price": 25, "technical_target": 30}})
    check("fundamental target survives sanitizer", sanitized["projection"].get("target_price") == 25)
    check("technical target removed by sanitizer", "technical_target" not in sanitized["projection"])

    bench = evaluate_benchmark(benchmark_fixture())
    check("benchmark fixture structurally valid", bench["valid"], str(bench.get("errors")))
    for market, result in bench.get("by_market", {}).items():
        check(f"{market} benchmark gate implementation can pass", result["all_projection_gates_pass"], json.dumps(result.get("gates"), sort_keys=True))
    broken_frame = benchmark_fixture().drop(columns=["outcome_source_hash"])
    check("benchmark missing outcome lineage rejected", not evaluate_benchmark(broken_frame)["valid"])
    broken_frame = benchmark_fixture(); broken_frame.loc[0, "model_frozen_before_outcome"] = False
    check("benchmark post-outcome model rejected", not evaluate_benchmark(broken_frame)["valid"])

    receipts = {market: promotion_fixture(market) for market in ["us", "idx", "commodity", "fx", "crypto"]}
    for market, receipt in receipts.items():
        check(f"{market} promotion gate pass fixture", evaluate_promotion(receipt)["eligible"])
        broken = deepcopy(receipt); broken["metrics"]["real_net_profit_factor"] = 1.49
        check(f"{market} profit factor below 1.50 blocked", not evaluate_promotion(broken)["eligible"])
        broken = deepcopy(receipt); broken["metrics"]["normal_max_drawdown"] = .151
        check(f"{market} drawdown above 15pct blocked", not evaluate_promotion(broken)["eligible"])
        broken = deepcopy(receipt); broken["metrics"]["projection_error_improvement_vs_no_change"] = .09
        check(f"{market} projection not beating baseline blocked", not evaluate_promotion(broken)["eligible"])
    check("global gate pass fixture requires all five", evaluate_all(receipts)["global_trading_ready"])
    missing = deepcopy(receipts); missing.pop("fx")
    check("global gate blocks one missing market", not evaluate_all(missing)["global_trading_ready"])

    registry = attach_proof_registry({})
    ps = registry.get("proof_status") or {}
    check("empty trust store blocks all market components", ps.get("predictive_components_promoted") == 0)
    check("global final false without all five receipts", ps.get("final_trading_system") is False)
    check("five exact market components registered", len((registry.get("proof_registry") or {}).get("components") or {}) == 5)

    check("legacy technical factor dataset absent", not (HERE / "research_v82").exists())
    active_modules = [
        "app.py", "run.py", "research_kernel.py", "market_projection_engine.py", "market_projection_benchmark.py",
        "promotion_gate_v88.py", "global_market_promotion_gate.py", "proof_registry.py", "proof_receipts.py",
    ]
    imports = []
    for name in active_modules:
        tree = ast.parse((HERE / name).read_text(encoding="utf-8"), filename=name)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import): imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module: imports.append(node.module)
    check("active import graph contains no legacy chart engine", not any(any(token in item.lower() for token in ("technical_engine", "momentum_engine", "price_action", "risk_range")) for item in imports), ",".join(imports))

    compiled = True; compile_errors = []
    for path in HERE.rglob("*.py"):
        try: py_compile.compile(str(path), doraise=True)
        except Exception as exc: compiled = False; compile_errors.append(f"{path.name}: {exc}")
    check("all Python files compile", compiled, " | ".join(compile_errors))

    html = (HERE / "dashboard.html").read_text(encoding="utf-8")
    run_text = (HERE / "run.py").read_text(encoding="utf-8")
    check("CLI identifies V9.1", "WAR ROOM OS V9.1" in run_text and "War Room OS V9.1" in run_text)
    check("Windows operator scripts present", all((HERE / name).exists() for name in ("CHECK_V91.bat", "SETUP_V88.bat", "RUN_V88.bat")))
    readme = (HERE / "README.md").read_text(encoding="utf-8")
    check("README preserves capital-blocked claim limit", "capital blocked" in readme.lower() and "not trading-ready" in readme.lower() and "zero technical predictors" in readme.lower())
    check("dashboard identifies V9.1", "V9.1" in html and "PRICE PROJECTION" in html)
    check("dashboard exposes low base high explanation", all(token in html for token in ("LOW SCENARIO", "BASE SCENARIO", "HIGH SCENARIO", "VALUE-CAPTURE BRIDGE")))
    try:
        js = html.split("<script>", 2)[2].split("</script>", 1)[0]
        temp = HERE / ".v88_dashboard_check.js"; temp.write_text(js, encoding="utf-8")
        run = subprocess.run(["node", "--check", str(temp)], capture_output=True, text=True, timeout=20)
        temp.unlink(missing_ok=True)
        check("dashboard JavaScript parses", run.returncode == 0, run.stderr)
    except Exception as exc:
        check("dashboard JavaScript parses", False, str(exc))

    passed = sum(item["pass"] for item in TESTS)
    report = {
        "schema": "warroom.v91.all_market_regression.v1", "passed": passed, "total": len(TESTS),
        "all_pass": passed == len(TESTS), "tests": TESTS,
        "claim_limit": "Software/enforcement validation only. It does not prove trading edge, target accuracy, profit factor or drawdown in any market.",
    }
    (HERE / "V91_ALL_MARKET_REGRESSION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"passed": passed, "total": len(TESTS), "all_pass": report["all_pass"]}, indent=2))
    if not report["all_pass"]:
        for row in TESTS:
            if not row["pass"]: print("FAIL", row["name"], row["detail"])
    return 0 if report["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
