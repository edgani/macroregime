"""Adversarial release validation for War Room OS V9.6."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import py_compile
import tempfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from anti_overfit_gate_v96 import evaluate as evaluate_anti_overfit
from anti_overfit_seal_v96 import create as create_seal
from autonomous_research_factory_v96 import run_all as run_research_all
from blind_proof_runner_v96 import run as run_blind_v96
from causal_research_lifecycle_v96 import append_event, replay, sha256_json
from global_market_promotion_gate_v96 import evaluate_all
from proof_registry_v96 import attach_proof_registry, load_registry
from run import build_desk, render_dashboard
from warroom.no_technical_policy import assert_registry_has_no_active_technical_components, validate_feature_names

ROOT = Path(__file__).resolve().parent
MARKETS = ("us", "idx", "commodity", "fx", "crypto")


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def _fixture(root: Path, variant: str = "stable") -> dict[str, Path]:
    market = "us"
    lifecycle = root / "research_lifecycle.jsonl"
    maps = json.loads((ROOT / "V96_MARKET_CAUSAL_MAPS.json").read_text(encoding="utf-8"))
    mapping = dict(maps["markets"][market])
    mapping["data_contract_hash"] = digest("data-contract")
    mapping_hash = sha256_json(mapping)
    base_time = dt.datetime(2025, 12, 30, 12, 0, tzinfo=dt.timezone.utc)
    append_event(lifecycle, {
        "event_id": "map-1", "research_id": "us-core-v96", "market": market,
        "event_type": "MAP_FREEZE", "payload": mapping,
    }, now=base_time)
    features = ["earnings_expectation_gap", "capacity_qualification_state", "valuation_gap"]
    if variant == "technical":
        features = ["rsi_14"]
    for i, candidate in enumerate(("A0", "A1", "A2")):
        when = base_time + dt.timedelta(seconds=1 + i * 2)
        append_event(lifecycle, {
            "event_id": f"candidate-{candidate}", "research_id": "us-core-v96", "market": market,
            "event_type": "CANDIDATE_REGISTER",
            "payload": {
                "candidate_id": candidate,
                "mapping_hash": mapping_hash,
                "metric_role": "expectations-bottleneck-value bridge",
                "formula_hash": digest("formula-" + candidate),
                "config_hash": digest("config-" + candidate),
                "code_hash": digest("code-" + candidate),
                "benchmark_id": "SECTOR_SIZE_BASELINE",
                "target_definition": "net forward excess return",
                "horizon": "4 weeks",
                "feature_names": features,
                "family_id": "FAMILY_A",
                "parameter_vector": {"strength": i},
                "expected_failure_modes": ["capacity arrives", "expectations already priced"],
            },
        }, now=when)
        append_event(lifecycle, {
            "event_id": f"test-{candidate}", "research_id": "us-core-v96", "market": market,
            "event_type": "TEST_START",
            "payload": {
                "candidate_id": candidate,
                "test_protocol_hash": digest("protocol"),
                "dataset_manifest_hash": digest("dataset"),
            },
        }, now=when + dt.timedelta(seconds=1))

    dates = pd.date_range("2019-01-06", "2026-07-26", freq="W-SUN", tz="UTC")
    rows: list[dict[str, Any]] = []
    for t_idx, timestamp in enumerate(dates):
        regime = f"R{(t_idx % 4) + 1}"
        cyc = 0.00025 * np.sin(t_idx / 4.0)
        values = {
            "A0": 0.00120 + cyc + 0.00006 * np.cos(t_idx / 7.0),
            "A1": 0.00155 + cyc + 0.00005 * np.sin(t_idx / 9.0),
            "A2": 0.00110 + cyc + 0.00006 * np.cos(t_idx / 11.0),
        }
        if variant == "lockbox_reversal" and timestamp >= pd.Timestamp("2026-01-01", tz="UTC"):
            values["A1"] = -0.0010 + 0.0001 * np.sin(t_idx)
        if variant == "parameter_spike" and pd.Timestamp("2024-01-01", tz="UTC") <= timestamp <= pd.Timestamp("2025-12-31", tz="UTC"):
            values["A0"] = -0.0002 + 0.00005 * np.sin(t_idx)
            values["A2"] = -0.0001 + 0.00005 * np.cos(t_idx)
            values["A1"] = 0.0020 + 0.00005 * np.sin(t_idx)
        if variant == "concentrated" and timestamp >= pd.Timestamp("2026-01-01", tz="UTC"):
            values["A1"] = 0.00005
            if timestamp == pd.Timestamp("2026-03-01", tz="UTC"):
                values["A1"] = 0.05
        if variant == "regime_missing" and timestamp >= pd.Timestamp("2026-01-01", tz="UTC"):
            regime = "R1"
        for candidate, net in values.items():
            if variant == "incomplete_trials" and candidate == "A2":
                continue
            stress = net - 0.00025
            rows.append({
                "timestamp": timestamp.isoformat(), "candidate_id": candidate,
                "net_return": float(net), "stress_return": float(stress),
                "benchmark_return": 0.0, "regime": regime,
                "family_id": "FAMILY_A", "parameter_index": {"A0": 0, "A1": 1, "A2": 2}[candidate],
            })
    returns = root / "candidate_returns.csv"
    pd.DataFrame(rows).to_csv(returns, index=False)

    protocol = {
        "schema": "warroom.v96.anti_overfit_protocol.v1",
        "market": market,
        "periods_per_year": 52,
        "periods": {
            "discovery_end": "2023-12-31T23:59:59Z",
            "validation_end": "2025-12-31T23:59:59Z",
            "lockbox_end": "2026-07-26T23:59:59Z",
        },
        "pbo_blocks": 8,
        "walk_forward_folds": 5,
        "purge_periods": 2,
        "embargo_periods": 2,
        "bootstrap_repetitions": 500,
        "bootstrap_block_periods": 4,
        "minimum_observations_per_regime": 4,
        "thresholds": {
            "pbo_max": 0.20,
            "dsr_probability_min": 0.95,
            "familywise_pvalue_max": 0.05,
            "holm_pvalue_max": 0.05,
            "walk_forward_min_folds": 4,
            "walk_forward_positive_fraction_min": 0.70,
            "walk_forward_stress_positive_fraction_min": 0.60,
            "lockbox_min_periods": 20,
            "lockbox_pvalue_max": 0.05,
            "stress_mean_excess_min": 0.0,
            "minimum_regimes": 4,
            "minimum_positive_regimes": 3,
            "minimum_stress_positive_regimes": 3,
            "parameter_spike_ratio_max": 3.0,
            "single_period_profit_concentration_max": 0.20,
            "top5_period_profit_concentration_max": 0.55,
        },
        "contamination_controls": {
            "model_knowledge_cutoff": "2025-12-31T23:59:59Z",
            "global_trial_accounting_complete": True,
            "independent_data_custodian": True,
            "post_model_cutoff_holdout": True,
            "low_contamination_asset_holdout": True,
            "prospective_outcomes_primary": False,
        },
    }
    protocol_path = root / "anti_overfit_protocol.json"
    _write_json(protocol_path, protocol)
    sealed_at = "2025-12-31T12:00:00Z" if variant != "late_seal" else "2026-02-01T12:00:00Z"
    seal = create_seal(
        market=market, candidate_id="A1", lifecycle=lifecycle, protocol=protocol_path,
        model_hash=digest("model"), code_snapshot_hash=digest("code-snapshot"),
        data_contract_hash=digest("data-contract"), sealed_at=sealed_at,
    )
    seal_path = root / "anti_overfit_seal.json"
    _write_json(seal_path, seal)
    return {"returns": returns, "lifecycle": lifecycle, "protocol": protocol_path, "seal": seal_path}


def _run_fixture(variant: str) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        paths = _fixture(Path(td), variant)
        return evaluate_anti_overfit(
            returns_path=paths["returns"], lifecycle_path=paths["lifecycle"],
            protocol_path=paths["protocol"], seal_path=paths["seal"],
        )


def _test(name: str, passed: bool, detail: Any) -> dict[str, Any]:
    return {"name": name, "pass": bool(passed), "detail": detail}


def main() -> None:
    tests: list[dict[str, Any]] = []

    compile_failures = []
    for path in sorted(ROOT.rglob("*.py")):
        if any(part in {".venv", "__pycache__"} for part in path.parts):
            continue
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            compile_failures.append(f"{path.relative_to(ROOT)}: {exc}")
    tests.append(_test("all_python_compiles", not compile_failures, {"files": len(list(ROOT.rglob('*.py'))), "failures": compile_failures}))

    maps = json.loads((ROOT / "V96_MARKET_CAUSAL_MAPS.json").read_text(encoding="utf-8"))
    required_map_fields = {
        "decision_purpose", "causal_role", "source_country_liquidity", "stock_flow_surprise_state",
        "transmission_path", "benchmark_target_horizon", "data_lineage_availability",
        "interaction_conditions", "invalidation", "claim_limits",
    }
    map_ok = set(maps.get("markets", {})) == set(MARKETS) and all(required_map_fields.issubset(maps["markets"][m]) for m in MARKETS)
    tests.append(_test("five_market_mapping_complete", map_ok, list(maps.get("markets", {}))))

    registry = load_registry()
    try:
        assert_registry_has_no_active_technical_components(registry)
        registry_ok = len(registry.get("components", {})) == 5 and not any(x.get("decision_active") for x in registry["components"].values())
    except Exception:
        registry_ok = False
    tests.append(_test("five_market_registry_fail_closed", registry_ok, registry))

    stable = _run_fixture("stable")
    tests.append(_test("stable_family_passes_historical_anti_overfit_fixture", stable.get("historical_blind_proven") is True, stable))

    reversal = _run_fixture("lockbox_reversal")
    tests.append(_test("validation_winner_fails_lockbox_reversal", reversal.get("historical_blind_proven") is False and not reversal.get("gates", {}).get("untouched_lockbox_positive"), reversal))

    incomplete = _run_fixture("incomplete_trials")
    tests.append(_test("incomplete_trial_family_rejected", incomplete.get("historical_blind_proven") is False and any("complete registered candidate" in e for e in incomplete.get("errors", [])), incomplete))

    spike = _run_fixture("parameter_spike")
    tests.append(_test("parameter_spike_rejected", spike.get("historical_blind_proven") is False and not spike.get("gates", {}).get("parameter_neighbourhood"), spike))

    missing_regime = _run_fixture("regime_missing")
    tests.append(_test("missing_regime_coverage_rejected", missing_regime.get("historical_blind_proven") is False and not missing_regime.get("gates", {}).get("regime_consistency"), missing_regime))

    concentration = _run_fixture("concentrated")
    tests.append(_test("single_lucky_period_concentration_rejected", concentration.get("historical_blind_proven") is False and not concentration.get("gates", {}).get("pnl_not_concentrated"), concentration))

    late = _run_fixture("late_seal")
    tests.append(_test("seal_after_lockbox_rejected", late.get("historical_blind_proven") is False and any("seal" in e for e in late.get("errors", [])), late))

    with tempfile.TemporaryDirectory() as td:
        try:
            _fixture(Path(td), "technical")
            technical_rejected = False
            detail = "technical candidate was accepted"
        except Exception as exc:
            technical_rejected = "technical predictor rejected" in str(exc)
            detail = str(exc)
    tests.append(_test("technical_candidate_rejected_before_test", technical_rejected, detail))

    with tempfile.TemporaryDirectory() as td:
        paths = _fixture(Path(td), "stable")
        lines = paths["lifecycle"].read_text(encoding="utf-8").splitlines()
        row = json.loads(lines[0]); row["payload"]["decision_purpose"] = "tampered"
        lines[0] = json.dumps(row)
        paths["lifecycle"].write_text("\n".join(lines) + "\n", encoding="utf-8")
        replayed = replay(paths["lifecycle"])
    tests.append(_test("lifecycle_tamper_detected", replayed.get("valid") is False, replayed))

    tests.append(_test("research_report_never_authorizes_live_capital", stable.get("capital_permission") == "BLOCKED_PENDING_ACTUAL_FILL_PROOF", stable.get("capital_permission")))

    with tempfile.TemporaryDirectory() as td:
        missing = Path(td) / "missing"
        blind = run_blind_v96(
            predictor_manifest=missing, outcome_manifest=missing, projections=missing,
            trades=missing, equity=missing, signed_receipt=missing,
            forecast_seal=missing, anti_overfit_report=missing,
        )
    tests.append(_test("blind_proof_missing_anti_overfit_fails_closed", blind.get("trading_ready") is False and blind.get("schema") == "warroom.v96.blind_proof_run.v1", blind))

    fake_v95 = {m: {"schema": "warroom.v95.blind_proof_run.v1", "market": m, "trading_ready": True, "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE", "errors": []} for m in MARKETS}
    global_result = evaluate_all(fake_v95)
    tests.append(_test("legacy_v95_proof_cannot_activate_v96", global_result.get("global_trading_ready") is False, global_result))

    attached = attach_proof_registry({})
    tests.append(_test("dashboard_registry_has_zero_promoted_components", attached.get("proof_status", {}).get("predictive_components_promoted") == 0 and attached.get("proof_status", {}).get("capital_permission") == "BLOCKED", attached.get("proof_status")))

    with tempfile.TemporaryDirectory() as td:
        status = run_research_all(root=Path(td))
    tests.append(_test("orchestrator_missing_workspaces_fail_closed", status.get("pipeline_ready_markets") == 0 and status.get("historical_blind_proven_markets") == 0 and status.get("capital_permission") == "BLOCKED", status))

    policy_violations = validate_feature_names(["earnings_gap", "stablecoin_supply", "rsi_14", "moving_average_20"])
    tests.append(_test("technical_policy_detects_disguised_chart_features", len(policy_violations) == 2, policy_violations))

    source = (ROOT / "blind_proof_runner_v96.py").read_text(encoding="utf-8")
    tests.append(_test("live_gate_requires_anti_overfit_binding", "anti_overfit_report_sha256" in source and "historical_blind_proven" in source, "binding present"))

    protocol = json.loads((ROOT / "V96_ANTI_OVERFIT_PROTOCOL_TEMPLATE.json").read_text(encoding="utf-8"))
    threshold_keys = set(protocol.get("thresholds", {}))
    required_thresholds = {"pbo_max", "dsr_probability_min", "familywise_pvalue_max", "lockbox_pvalue_max", "minimum_regimes", "parameter_spike_ratio_max"}
    tests.append(_test("frozen_protocol_has_core_anti_overfit_gates", required_thresholds.issubset(threshold_keys), sorted(threshold_keys)))

    empty_data = {"markets": MARKETS, "fred": {}, "prices": {}, "feeds": {"_status": {}}, "sources": {}, "overall_source": "VALIDATION_EMPTY"}
    runtime_desk = build_desk(empty_data)
    runtime_ok = (
        runtime_desk.get("v96_status", {}).get("causal_mapping_ready_markets") == 5
        and runtime_desk.get("proof_status", {}).get("proof_firewall_version") == "9.6"
        and runtime_desk.get("proof_status", {}).get("capital_permission") == "BLOCKED"
    )
    tests.append(_test("runtime_exposes_v96_readiness_without_promoting_capital", runtime_ok, {
        "v96_status": runtime_desk.get("v96_status"), "proof_status": runtime_desk.get("proof_status")
    }))

    dashboard_source = (ROOT / "dashboard.html").read_text(encoding="utf-8")
    dashboard_ok = all(x in dashboard_source for x in (
        "War Room OS V9.6", "V9.6 FIVE-LAYER READINESS", "FIXTURE PASS ≠ MARKET PROOF",
        "historical_statistical_pass_markets", "prospective_actual_fill_proven_markets"
    ))
    with tempfile.TemporaryDirectory() as td:
        rendered = Path(td) / "dashboard.html"
        render_ok = render_dashboard(runtime_desk, str(ROOT / "dashboard.html"), str(rendered))
        rendered_text = rendered.read_text(encoding="utf-8") if rendered.is_file() else ""
    dashboard_ok = dashboard_ok and render_ok and "window.DASHBOARD_DATA=" in rendered_text
    tests.append(_test("dashboard_separates_infrastructure_from_market_proof", dashboard_ok, "V9.6 readiness ladder and injected runtime data present"))

    passed = sum(x["pass"] for x in tests)
    result = {
        "schema": "warroom.v96.final_validation.v1",
        "release": "War Room OS V9.6 Causal Anti-Overfit Research Factory",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "passed": passed,
        "total": len(tests),
        "all_pass": passed == len(tests),
        "tests": tests,
        "research_pipeline_ready_markets": 5,
        "historical_blind_proven_markets": 0,
        "limited_production_ready_markets": 0,
        "live_capital_ready_markets": 0,
        "capital_permission": "BLOCKED",
        "claim_limit": "Fixture passes validate the gate implementation only. They are synthetic software tests and are never market evidence.",
    }
    unhashed = json.dumps(result, sort_keys=True, separators=(",", ":"), default=str, allow_nan=False).encode()
    result["validation_hash"] = hashlib.sha256(unhashed).hexdigest()
    (ROOT / "V96_FINAL_VALIDATION.json").write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(result, indent=2, allow_nan=False))
    raise SystemExit(0 if result["all_pass"] else 2)


if __name__ == "__main__":
    main()
