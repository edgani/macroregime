"""Outcome recorder tests: maturation, excursion math, honest skips, idempotency.

Covers: LONG/SHORT realized return + MAE/MFE math, maturity gating, duplicate
prevention, provider-failure / insufficient-bars / exit-gap honest skips,
provider symbol resolution, dry-run safety, and evaluator integration.
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

import shadow_outcome_recorder_v101 as recorder
from shadow_execution_ledger_v95 import (
    append_forecast,
    append_order_intent,
    append_outcome,
    append_shadow_fill,
    verify,
)
from tools.paper_trading.evaluate_shadow_ledger import build_evaluation

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


def _bars(start: dt.date, days: int, *, close0: float, step: float, low: float, high: float):
    """Synthetic daily bars: close walks by step; every bar shares the same low/high."""
    out = []
    for i in range(days):
        out.append(
            {
                "date": (start + dt.timedelta(days=i)).isoformat(),
                "open": close0 + step * (i - 1) if i else close0,
                "high": high,
                "low": low,
                "close": close0 + step * i,
            }
        )
    return out


def _seed_ledger(tmp_path: Path, *, direction: str = "LONG") -> Path:
    ledger = tmp_path / "shadow_ledger.jsonl"
    append_forecast(ledger, _forecast(direction=direction), now=T0)
    append_order_intent(ledger, _order(side="BUY" if direction == "LONG" else "SELL"), now=T0 + dt.timedelta(seconds=1))
    append_shadow_fill(ledger, _fill(), now=T0 + dt.timedelta(seconds=2))
    return ledger


def test_long_outcome_math_exact(tmp_path):
    ledger = _seed_ledger(tmp_path)
    bars = _bars(dt.date(2026, 1, 10), 31, close0=500.0, step=50.0 / 30.0, low=490.0, high=560.0)
    result = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: bars)
    assert result["created"] == 1, result["skipped"]
    row = result["created_rows"][0]
    assert row["realized_return"] == pytest.approx(550.0 / 500.0 - 1.0)
    outcomes = [json.loads(l) for l in ledger.read_text().splitlines() if json.loads(l).get("record_type") == "OUTCOME"]
    assert len(outcomes) == 1
    out = outcomes[0]
    assert out["realized_return"] == pytest.approx(0.10)
    assert out["max_adverse_excursion"] == pytest.approx(490.0 / 500.0 - 1.0)
    assert out["max_favorable_excursion"] == pytest.approx(560.0 / 500.0 - 1.0)
    assert out["exit_reason"] == "HORIZON_REACHED"
    assert out["bars_used"] == 31
    assert verify(ledger)["valid"] is True


def test_short_outcome_math_exact(tmp_path):
    ledger = _seed_ledger(tmp_path, direction="SHORT")
    bars = _bars(dt.date(2026, 1, 10), 31, close0=500.0, step=-50.0 / 30.0, low=440.0, high=520.0)
    result = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: bars)
    assert result["created"] == 1, result["skipped"]
    outcomes = [json.loads(l) for l in ledger.read_text().splitlines() if json.loads(l).get("record_type") == "OUTCOME"]
    out = outcomes[0]
    assert out["realized_return"] == pytest.approx(500.0 / 450.0 - 1.0)
    assert out["max_adverse_excursion"] == pytest.approx(500.0 / 520.0 - 1.0)
    assert out["max_favorable_excursion"] == pytest.approx(500.0 / 440.0 - 1.0)


def test_unmatured_forecast_stays_pending(tmp_path):
    ledger = tmp_path / "shadow_ledger.jsonl"
    future = dt.datetime.now(UTC) + dt.timedelta(days=30)
    append_forecast(ledger, _forecast(outcome_end=future.isoformat().replace("+00:00", "Z")), now=T0)
    append_order_intent(ledger, _order(), now=T0 + dt.timedelta(seconds=1))
    append_shadow_fill(ledger, _fill(), now=T0 + dt.timedelta(seconds=2))
    result = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: pytest.fail("fetch must not be called"))
    assert result["created"] == 0
    assert result["pending_unmatured"] == 1
    assert verify(ledger)["outcomes"] == 0


def test_existing_outcome_never_duplicated(tmp_path):
    ledger = _seed_ledger(tmp_path)
    bars = _bars(dt.date(2026, 1, 10), 31, close0=500.0, step=1.0, low=490.0, high=560.0)
    first = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: bars)
    assert first["created"] == 1
    second = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: pytest.fail("fetch must not be called"))
    assert second["created"] == 0
    assert verify(ledger)["outcomes"] == 1


def test_provider_failure_is_honest_skip(tmp_path):
    ledger = _seed_ledger(tmp_path)

    def boom(provider, symbol, start, end):
        raise ValueError("simulated provider outage")

    result = recorder.record_outcomes(ledger, fetcher=boom)
    assert result["created"] == 0
    assert result["skipped"][0]["reason"].startswith("PROVIDER_DATA_UNAVAILABLE")
    assert verify(ledger)["outcomes"] == 0


def test_insufficient_bars_is_honest_skip(tmp_path):
    ledger = _seed_ledger(tmp_path)
    bars = _bars(dt.date(2026, 1, 10), 5, close0=500.0, step=1.0, low=490.0, high=560.0)
    result = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: bars)
    assert result["created"] == 0
    assert result["skipped"][0]["reason"].startswith("INSUFFICIENT_BARS")


def test_exit_data_gap_is_honest_skip(tmp_path):
    ledger = _seed_ledger(tmp_path)
    # 20 bars (passes min_bars) but the last bar is 2026-01-29, i.e. 11 days
    # before outcome_end 2026-02-09 (> default 10-day exit gap allowance).
    bars = _bars(dt.date(2026, 1, 10), 20, close0=500.0, step=1.0, low=490.0, high=560.0)
    result = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: bars)
    assert result["created"] == 0
    assert result["skipped"][0]["reason"].startswith("EXIT_DATA_GAP")


def test_dry_run_appends_nothing(tmp_path):
    ledger = _seed_ledger(tmp_path)
    bars = _bars(dt.date(2026, 1, 10), 31, close0=500.0, step=1.0, low=490.0, high=560.0)
    result = recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: bars, dry_run=True)
    assert result["created"] == 1
    assert verify(ledger)["outcomes"] == 0


def test_provider_resolution():
    assert recorder.resolve_provider("us", "MU") == ("YAHOO", "MU")
    assert recorder.resolve_provider("idx", "BBCA") == ("YAHOO", "BBCA.JK")
    assert recorder.resolve_provider("idx", "^JKSE") == ("YAHOO", "^JKSE")
    assert recorder.resolve_provider("crypto", "BTCUSDT") == ("BINANCE", "BTCUSDT")
    assert recorder.resolve_provider("commodity", "WTI_REFERENCE") == ("YAHOO", "CL=F")


def test_evaluator_consumes_recorded_outcome(tmp_path):
    ledger = _seed_ledger(tmp_path)
    bars = _bars(dt.date(2026, 1, 10), 31, close0=500.0, step=1.0, low=490.0, high=560.0)
    recorder.record_outcomes(ledger, fetcher=lambda p, s, a, b: bars)
    report = build_evaluation(ledger)
    assert report["ledger_verification"]["outcomes"] == 1
    assert report["summary"]["outcomes_matured"] == 1
    # Below the 30-observation floor: still no profitability claim permitted.
    assert report["evidence_status"] == "PROSPECTIVE_EVIDENCE_PENDING"
    assert report["capital_permission"] == "BLOCKED"
