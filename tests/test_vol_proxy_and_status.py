"""R10 tests: vol_proxy (proxy-labeled options-free vol layer) and
warroom_status (operator status CLI)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools.warroom_status import build_status
from warroom.research import vol_proxy


def _gbm_closes(n: int, daily_vol: float, start: float = 100.0, seed: int = 7) -> list[float]:
    """Deterministic pseudo-random walk with roughly known dispersion."""
    import random

    rng = random.Random(seed)
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * math.exp(rng.gauss(0.0, daily_vol)))
    return closes


# --- vol_proxy ---------------------------------------------------------------


def test_expected_move_math():
    # EM = S * sigma * sqrt(T/252); 100 * 0.20 * sqrt(30/252)
    em = vol_proxy.expected_move(100.0, 0.20, 30)
    assert em == pytest.approx(100.0 * 0.20 * math.sqrt(30 / 252))


def test_assess_labels_proxy_and_lists_unmeasurable():
    closes = _gbm_closes(120, 0.01)
    out = vol_proxy.assess("SPY", closes, horizon_days=30)
    assert out["status"] == "OK"
    assert out["source"] == "PROXY_REALIZED_VOL_NO_OPTIONS_DATA"
    assert "implied_volatility" in out["not_measurable_without_options_data"]
    assert "gamma_exposure" in out["not_measurable_without_options_data"]
    lo, hi = out["expected_move_band"]
    assert lo < out["price"] < hi
    xlo, xhi = out["extreme_move_band_2sigma"]
    assert xlo < lo and xhi > hi


def test_realized_vol_recovers_input_dispersion():
    # daily vol 1% -> annualized ~ 0.01*sqrt(252) = 0.1587 (loose band, estimator noise)
    closes = _gbm_closes(500, 0.01)
    sigma = vol_proxy.realized_vol_annualized(closes, 60)
    assert sigma == pytest.approx(0.01 * math.sqrt(252), rel=0.35)


def test_vol_regime_classification():
    closes = _gbm_closes(120, 0.01)
    pct = vol_proxy.vol_cone_percentile(closes, 20)
    assert pct is not None and 0.0 <= pct <= 100.0
    out = vol_proxy.assess("SPY", closes)
    assert out["vol_regime"] in ("COMPRESSED", "NORMAL", "EXPANDED")


def test_insufficient_data_is_honest():
    out = vol_proxy.assess("SPY", [100.0, 101.0, 100.5])
    assert out["status"] == "INSUFFICIENT_DATA"
    assert "expected_move_1sigma" not in out  # no fabricated numbers


def test_low_vol_flags_squeeze_risk():
    # Long calm history then still calm: current percentile low -> squeeze flag.
    closes = _gbm_closes(200, 0.004)
    out = vol_proxy.assess("CALM", closes)
    if out["vol_cone_percentile"] is not None and out["vol_cone_percentile"] < 15.0:
        assert out["squeeze_expansion_risk"] is True
    else:
        assert out["squeeze_expansion_risk"] is False


def test_assess_many_batch():
    out = vol_proxy.assess_many({"A": _gbm_closes(60, 0.01), "B": [1.0, 1.1]})
    assert out["A"]["status"] == "OK"
    assert out["B"]["status"] == "INSUFFICIENT_DATA"


# --- warroom_status ------------------------------------------------------------


def test_status_builds_and_is_honest():
    status = build_status()
    assert status["schema"] == "warroom.status.v1"
    assert status["ledger"]["verification_valid"] is True
    assert status["ledger"]["forecasts"] == 12
    assert status["ledger"]["outcomes_matured"] == 0
    assert status["capital_permission"] == "BLOCKED"
    assert status["contamination"]["shadow_pass"] is True
    assert status["contamination"]["capital_pass"] is False
    assert status["trial_registries"]["valid"] is True
    assert isinstance(status["ledger"]["days_to_first_maturity"], int)
    assert len(status["git_head"]) == 40


def test_status_json_serializable():
    json.dumps(build_status())  # must not raise
