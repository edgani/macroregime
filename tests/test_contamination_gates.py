"""Contamination gate tests (R9.3): verified gates from ledger/registry state,
attestation policy handling, fail-closed behavior, evaluator integration."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shadow_execution_ledger_v95 import (
    append_forecast,
    append_order_intent,
    append_outcome,
    append_shadow_fill,
)
from tools.paper_trading.evaluate_shadow_ledger import build_evaluation
from warroom.research import contamination_gates, trial_counter

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
H = lambda seed: hashlib.sha256(seed.encode()).hexdigest()
REAL_LEDGER = ROOT / "runtime" / "v101_shadow" / "shadow_ledger.jsonl"
REAL_POLICY = ROOT / "config" / "contamination_policy.json"


def _forecast(**over):
    base = {
        "forecast_id": "F95_TEST_US_SPY_20260110",
        "trial_id": "TEST_POLICY",
        "market": "us",
        "security_id": "SPY",
        "generated_at": T0.isoformat().replace("+00:00", "Z"),
        "decision_at": (T0 + dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
        "outcome_start": (T0 + dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
        "outcome_end": (T0 + dt.timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        "horizon": "30D",
        "direction": "LONG",
        "probability": 0.6,
        "expected_return": 0.05,
        "lower_confidence_bound_return": 0.01,
        "expected_shortfall": -0.03,
        "opportunity_cost_estimate": 0.0,
        "target_price": 525.0,
        "invalidation": "thesis invalidated",
        "regime": "TEST",
        "git_commit": "0" * 39 + "1",
        "model_hash": H("model"),
        "data_snapshot_hash": H("data"),
        "code_snapshot_hash": H("code"),
        "global_trial_ledger_hash": H("trials"),
        "projection_file_hash": H("projection"),
    }
    base.update(over)
    return base


def _order(**over):
    base = {
        "forecast_id": "F95_TEST_US_SPY_20260110",
        "shadow_order_id": "S100_TEST_US_SPY_20260110",
        "created_at": (T0 + dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
        "instrument_id": "SPY",
        "side": "BUY",
        "quantity": 1.0,
        "order_type": "REFERENCE_MARKET",
        "reference_price": 500.0,
        "max_slippage_bps": 25.0,
    }
    base.update(over)
    return base


def _fill(**over):
    base = {
        "forecast_id": "F95_TEST_US_SPY_20260110",
        "shadow_order_id": "S100_TEST_US_SPY_20260110",
        "filled_at": (T0 + dt.timedelta(seconds=2)).isoformat().replace("+00:00", "Z"),
        "quantity": 1.0,
        "price": 500.0,
        "commission": 0.0,
        "fees": 0.0,
        "spread_cost": 0.0,
        "slippage_cost": 0.0,
        "source_snapshot_hash": H("data"),
    }
    base.update(over)
    return base


def _outcome(**over):
    base = {
        "forecast_id": "F95_TEST_US_SPY_20260110",
        "horizon_end": (T0 + dt.timedelta(days=30)).isoformat().replace("+00:00", "Z"),
        "realized_return": 0.04,
        "max_adverse_excursion": -0.02,
        "max_favorable_excursion": 0.09,
        "outcome_source_hash": H("outcome"),
        "exit_reason": "HORIZON_REACHED",
        "later_revision_impact": "NONE_RECORDED",
    }
    base.update(over)
    return base


def _seed_full_lifecycle(tmp_path: Path) -> Path:
    ledger = tmp_path / "shadow_ledger.jsonl"
    append_forecast(ledger, _forecast(), now=T0)
    append_order_intent(ledger, _order(), now=T0 + dt.timedelta(seconds=1))
    append_shadow_fill(ledger, _fill(), now=T0 + dt.timedelta(seconds=2))
    append_outcome(ledger, _outcome(), now=T0 + dt.timedelta(days=31))
    return ledger


def _crafted_registry(tmp_path: Path, trial_id: str, timestamp: str) -> Path:
    """A valid flat-chain registry with an operator-chosen timestamp."""
    registry = tmp_path / "trials.jsonl"
    entry = {
        "trial_id": trial_id,
        "timestamp": timestamp,
        "outcome": "REGISTERED_PROSPECTIVE",
        "claims": [],
        "structural_hash": H(trial_id),
        "spec": {"test": True},
        "previous_hash": "GENESIS",
    }
    entry["entry_hash"] = hashlib.sha256(trial_counter._canonical(entry)).hexdigest()
    registry.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    return registry


def _gate(verdict, gate_id):
    return next(g for g in verdict["gates"] if g["id"] == gate_id)


def test_real_ledger_shadow_pass_capital_blocked():
    verdict = contamination_gates.evaluate_contamination(REAL_LEDGER, policy_path=REAL_POLICY)
    assert verdict["shadow_pass"] is True, verdict["gates"]
    assert verdict["capital_pass"] is False
    # The blocking capital gates are exactly the V84 failure modes, honestly attested.
    blocking = {g["id"] for g in verdict["gates"] if g["tier"] == "capital" and not g["passed"]}
    assert "independent_data_custodian_used" in blocking
    assert "model_blind_signal_ids_used" in blocking


def test_missing_policy_fails_closed(tmp_path):
    ledger = _seed_full_lifecycle(tmp_path)
    registry = _crafted_registry(tmp_path, "TEST_POLICY", "2026-01-01T00:00:00Z")
    verdict = contamination_gates.evaluate_contamination(
        ledger, policy_path=tmp_path / "missing.json", registries=(registry,)
    )
    assert verdict["shadow_pass"] is False
    assert _gate(verdict, "llm_in_signal_path")["passed"] is False


def test_unregistered_trial_fails_gate(tmp_path):
    ledger = _seed_full_lifecycle(tmp_path)
    empty_registry = tmp_path / "trials.jsonl"
    verdict = contamination_gates.evaluate_contamination(
        ledger, policy_path=REAL_POLICY, registries=(empty_registry,)
    )
    assert _gate(verdict, "complete_global_trial_ledger")["passed"] is False
    assert verdict["shadow_pass"] is False


def test_registration_after_outcome_fails_prospective_gate(tmp_path):
    ledger = _seed_full_lifecycle(tmp_path)
    # The ledger stamps recorded_at at real append time; a registration crafted
    # in the future is definitionally retroactive relative to that outcome.
    registry = _crafted_registry(tmp_path, "TEST_POLICY", "2027-03-01T00:00:00Z")
    verdict = contamination_gates.evaluate_contamination(
        ledger, policy_path=REAL_POLICY, registries=(registry,)
    )
    assert _gate(verdict, "trial_registration_prospective")["passed"] is False
    assert verdict["shadow_pass"] is False


def test_prospective_registration_and_matured_outcome_passes(tmp_path):
    ledger = _seed_full_lifecycle(tmp_path)
    # Registration before the first outcome: the prospective principle holds.
    registry = _crafted_registry(tmp_path, "TEST_POLICY", "2026-01-01T00:00:00Z")
    verdict = contamination_gates.evaluate_contamination(
        ledger, policy_path=REAL_POLICY, registries=(registry,)
    )
    assert _gate(verdict, "trial_registration_prospective")["passed"] is True
    assert _gate(verdict, "post_model_cutoff_holdout")["passed"] is True  # 2026-02-09 > 2026-01-01
    assert verdict["shadow_pass"] is True
    assert verdict["capital_pass"] is False  # attested capital gates still block


def test_tampered_ledger_fails(tmp_path):
    ledger = _seed_full_lifecycle(tmp_path)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    row = json.loads(lines[0])
    row["expected_return"] = 0.99  # silent edit
    lines[0] = json.dumps(row)
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    registry = _crafted_registry(tmp_path, "TEST_POLICY", "2026-01-01T00:00:00Z")
    verdict = contamination_gates.evaluate_contamination(
        ledger, policy_path=REAL_POLICY, registries=(registry,)
    )
    assert _gate(verdict, "ledger_append_only_valid")["passed"] is False
    assert verdict["shadow_pass"] is False


def test_evaluator_report_carries_contamination_verdict():
    report = build_evaluation(REAL_LEDGER)
    assert "contamination" in report
    assert report["contamination"]["schema"] == "warroom.contamination_verdict.v1"
    assert report["contamination"]["shadow_pass"] is True
    assert report["contamination"]["capital_pass"] is False
    assert report["capital_permission"] == "BLOCKED"
