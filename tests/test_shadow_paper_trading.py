"""Paper-trading framework tests: schema, lifecycle, replay, evaluation.

Covers the mandate requirements: append-only ledger, decision-time snapshot,
frozen config/model/code binding, git commit, anti-backfill, NO_TRADE gating,
tamper evidence, maturity gating, historical replay, evaluation report.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import shadow_runner_v101
from shadow_execution_ledger_v95 import (
    append_forecast,
    append_order_intent,
    append_outcome,
    append_shadow_fill,
    verify,
)
from tools.paper_trading.evaluate_shadow_ledger import build_evaluation
from warroom.research import trial_counter

UTC = dt.timezone.utc
T0 = dt.datetime(2026, 1, 10, 12, 0, 0, tzinfo=UTC)
H = lambda seed: hashlib.sha256(seed.encode()).hexdigest()


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
        "max_favorable_excursion": 0.07,
        "outcome_source_hash": H("outcome"),
        "exit_reason": "HORIZON_END",
        "later_revision_impact": "NONE",
    }
    base.update(over)
    return base


def test_full_lifecycle_and_schema(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_forecast(ledger, _forecast(), now=T0)
    append_order_intent(ledger, _order(), now=T0 + dt.timedelta(seconds=1))
    append_shadow_fill(ledger, _fill(), now=T0 + dt.timedelta(seconds=2))
    append_outcome(ledger, _outcome(), now=T0 + dt.timedelta(days=31))
    result = verify(ledger)
    assert result["valid"], result["errors"]
    assert (result["forecasts"], result["order_intents"], result["shadow_fills"], result["outcomes"]) == (1, 1, 1, 1)
    assert result["capital_permission"] == "BLOCKED"


def test_mandate_field_coverage(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_forecast(ledger, _forecast(), now=T0)
    row = json.loads(ledger.read_text().splitlines()[0])
    for field in ("git_commit", "target_price", "lower_confidence_bound_return",
                  "opportunity_cost_estimate", "invalidation", "expected_shortfall",
                  "model_hash", "data_snapshot_hash", "code_snapshot_hash"):
        assert field in row, f"mandate field missing: {field}"


def test_anti_backfill_and_future_rejected(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    stale = _forecast(generated_at=(T0 - dt.timedelta(hours=1)).isoformat().replace("+00:00", "Z"))
    with pytest.raises(ValueError, match="backfilled or future"):
        append_forecast(ledger, stale, now=T0)


def test_no_trade_cannot_create_order(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_forecast(ledger, _forecast(direction="NO_TRADE", forecast_id="F95_TEST_US_QQQ_20260110"), now=T0)
    with pytest.raises(ValueError, match="NO_TRADE"):
        append_order_intent(ledger, _order(forecast_id="F95_TEST_US_QQQ_20260110"), now=T0 + dt.timedelta(seconds=1))


def test_duplicate_forecast_rejected(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_forecast(ledger, _forecast(), now=T0)
    with pytest.raises(ValueError, match="duplicate"):
        append_forecast(ledger, _forecast(), now=T0)


def test_premature_outcome_rejected(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_forecast(ledger, _forecast(), now=T0)
    with pytest.raises(ValueError, match="not matured"):
        append_outcome(ledger, _outcome(), now=T0 + dt.timedelta(days=10))


def test_tamper_evidence(tmp_path):
    ledger = tmp_path / "ledger.jsonl"
    append_forecast(ledger, _forecast(), now=T0)
    text = ledger.read_text(encoding="utf-8").replace('"expected_return": 0.05', '"expected_return": 0.5')
    ledger.write_text(text, encoding="utf-8")
    result = verify(ledger)
    assert not result["valid"]
    assert any("record_hash mismatch" in e for e in result["errors"])


def test_historical_replay_evaluation(tmp_path):
    """Replay infrastructure: a matured ledger evaluates to real statistics."""
    ledger = tmp_path / "ledger.jsonl"
    for i, (expected, realized) in enumerate(((0.05, 0.04), (0.03, -0.01), (0.04, 0.06))):
        fid = f"F95_TEST_US_TKR{i}_20260110"
        t0 = T0 + dt.timedelta(minutes=i)
        fc = _forecast(forecast_id=fid, security_id=f"TKR{i}", expected_return=expected,
                       generated_at=t0.isoformat().replace("+00:00", "Z"),
                       decision_at=(t0 + dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                       outcome_start=(t0 + dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                       outcome_end=(t0 + dt.timedelta(days=30)).isoformat().replace("+00:00", "Z"))
        append_forecast(ledger, fc, now=t0)
        append_order_intent(ledger, _order(forecast_id=fid, shadow_order_id=f"S100_T{i}",
                                           created_at=(t0 + dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z")),
                            now=t0 + dt.timedelta(seconds=1))
        append_shadow_fill(ledger, _fill(forecast_id=fid, shadow_order_id=f"S100_T{i}",
                                         filled_at=(t0 + dt.timedelta(seconds=2)).isoformat().replace("+00:00", "Z")),
                           now=t0 + dt.timedelta(seconds=2))
        append_outcome(ledger, _outcome(forecast_id=fid, realized_return=realized,
                                        horizon_end=(t0 + dt.timedelta(days=30)).isoformat().replace("+00:00", "Z")),
                       now=t0 + dt.timedelta(days=31))
    report = build_evaluation(ledger)
    assert report["ledger_verification"]["valid"]
    assert report["summary"]["outcomes_matured"] == 3
    assert report["summary"]["direction_hit_rate"] == pytest.approx(2 / 3)
    assert report["evidence_status"] == "PROSPECTIVE_EVIDENCE_PENDING"  # <30 obs: no claim permitted
    assert report["capital_permission"] == "BLOCKED"


def _fixture_snapshot():
    return {
        "meta": {"generated": "2026-07-28T00:00:00Z"},
        "current_context": {"quotes": {"SPY": 500.0}},
        "current_action_state": {"macro_state": {"state": "TEST_REGIME"}},
        "alpha_center": {"shadow_candidates": [{
            "market": "us", "ticker": "SPY",
            "current_action": {
                "direction": "LONG_BIAS", "confidence": 0.55,
                "risk_plan": {"side": "BUY", "quantity": 1.0, "entry": 500.0, "invalidation": "thesis broken"},
                "projection": {"expected_return": 0.05, "low_return": 0.01, "high_return": 0.09, "horizon_days": 90},
            },
        }]},
    }


def test_shadow_runner_dry_run(tmp_path, monkeypatch):
    """Dry-run the production recorder against a fixture snapshot on a temp ledger."""
    monkeypatch.setattr(shadow_runner_v101, "LEDGER", tmp_path / "shadow_ledger.jsonl")
    registry = tmp_path / "trials.jsonl"
    trial_counter.register("V101_FIXED_ACTION_POLICY", {"policy": "test"}, registry=registry)
    result = shadow_runner_v101.record(snapshot=_fixture_snapshot(), trial_registries=(registry,))
    assert result["created"] == 1, result
    assert result["verification"]["valid"]
    rows = [json.loads(line) for line in (tmp_path / "shadow_ledger.jsonl").read_text().splitlines()]
    forecast = next(r for r in rows if r["record_type"] == "FORECAST")
    assert forecast["direction"] == "LONG"
    assert forecast["target_price"] == pytest.approx(525.0)
    assert forecast["lower_confidence_bound_return"] == pytest.approx(0.01)
    assert len(forecast["git_commit"]) == 40
    # The forecast binds the actual global trial registry content, not a policy file.
    assert forecast["global_trial_ledger_hash"] == trial_counter.content_hash((registry,))
    # Idempotency: a second run the same day records nothing new.
    again = shadow_runner_v101.record(snapshot=_fixture_snapshot(), trial_registries=(registry,))
    assert again["created"] == 0
    assert again["skipped"] and again["skipped"][0]["reason"] == "ALREADY_RECORDED_TODAY"


def test_shadow_runner_refuses_unregistered_trial(tmp_path, monkeypatch):
    """Fail-closed: no prospective trial registration, no shadow records."""
    monkeypatch.setattr(shadow_runner_v101, "LEDGER", tmp_path / "shadow_ledger.jsonl")
    empty_registry = tmp_path / "trials.jsonl"
    result = shadow_runner_v101.record(snapshot=_fixture_snapshot(), trial_registries=(empty_registry,))
    assert result["state"] == "TRIAL_NOT_REGISTERED"
    assert result["created"] == 0
    assert not (tmp_path / "shadow_ledger.jsonl").exists()


def test_evaluation_on_empty_ledger_is_pending(tmp_path):
    report = build_evaluation(tmp_path / "missing.jsonl")
    assert report["evidence_status"] == "PROSPECTIVE_EVIDENCE_PENDING"
    assert report["summary"]["outcomes_matured"] == 0
