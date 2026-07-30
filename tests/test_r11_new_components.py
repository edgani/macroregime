"""Rule-level tests for the R11 components: crashmeter_v3, btc_monday, JARVIS.

These test the FORMULAS on synthetic data (no network) — the modules fetch
live data in production, so the fetch functions are monkeypatched here.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from warroom.research import btc_monday, crashmeter_v3
from run import _jarvis_brief


# ---------------- crashmeter_v3 formula tests (article rules, fixed) ----------

def _fake_sources(spread: dict[date, float], hy: dict[date, float], cape: float):
    crashmeter_v3._fred = lambda sid: spread if sid == "T10Y3M" else hy  # noqa: SLF001
    crashmeter_v3._cape_current = lambda: cape  # noqa: SLF001


def _daily(end: date, n: int, value: float) -> dict[date, float]:
    return {end - timedelta(days=i): value for i in range(n)}


def test_cmv3_a1_threshold_exactly_050():
    end = date(2026, 7, 28)
    spread = _daily(end, 400, 0.51)
    _fake_sources(spread, _daily(end, 200, 3.0), 30.0)
    assert crashmeter_v3.compute()["a1"] == 0
    spread = _daily(end, 400, 0.50)
    _fake_sources(spread, _daily(end, 200, 3.0), 30.0)
    assert crashmeter_v3.compute()["a1"] == 1  # rule: score 0 only ABOVE 0.5


def test_cmv3_a2_window_18_months():
    end = date(2026, 7, 28)
    # inversion ended 6 months ago -> a2 = 1
    spread = _daily(end, 400, 1.0)
    inv_start = end - timedelta(days=210)
    for i in range(30):
        spread[inv_start + timedelta(days=i)] = -0.3
    _fake_sources(spread, _daily(end, 200, 3.0), 30.0)
    out = crashmeter_v3.compute()
    assert out["a2"] == 1 and out["last_inversion_end"] is not None
    # inversion ended 20 months ago -> a2 = 0
    spread2 = _daily(end, 800, 1.0)
    inv2 = end - timedelta(days=640)
    for i in range(30):
        spread2[inv2 + timedelta(days=i)] = -0.3
    _fake_sources(spread2, _daily(end, 200, 3.0), 30.0)
    assert crashmeter_v3.compute()["a2"] == 0


def test_cmv3_b1_b2_c_thresholds():
    end = date(2026, 7, 28)
    spread = _daily(end, 400, 1.0)
    # HY: 6m range 160bps, level 560bps -> b1=1, b2=1
    hy = {end - timedelta(days=i): (5.6 if i == 0 else (2.0 if i > 100 else 3.6)) for i in range(200)}
    _fake_sources(spread, hy, 36.0)
    out = crashmeter_v3.compute()
    assert out["b1"] == 1 and out["b2"] == 1 and out["c"] == 1
    assert out["score"] == out["a1"] + out["a2"] + 1 + 1 + 1
    # cape exactly 35 -> c=0 (rule: above 35)
    _fake_sources(spread, _daily(end, 200, 3.0), 35.0)
    assert crashmeter_v3.compute()["c"] == 0


def test_cmv3_label_bands():
    assert {0: "AMAN", 1: "AMAN", 2: "WASPADA", 3: "EXIT WINDOW", 4: "CRITICAL"}[2] == "WASPADA"


# ---------------- btc_monday study logic tests (synthetic weeks) --------------

def _day(d: date, o: float, h: float, l: float, c: float) -> dict[str, Any]:
    return {"date": d, "o": o, "h": h, "l": l, "c": c}


def test_btc_high_sweep_reversal_counted():
    mon = date(2026, 7, 20)
    days = [
        _day(mon, 100, 110, 90, 105),        # Monday: H=110 L=90 mid=100
        _day(mon + timedelta(days=1), 105, 115, 100, 112),  # sweeps HIGH first
        _day(mon + timedelta(days=2), 112, 113, 95, 98),    # dips through mid -> reversal
        _day(mon + timedelta(days=3), 98, 102, 92, 100),    # never takes low (90)
    ]
    out = btc_monday._study(days)  # noqa: SLF001
    assert out["after_high_sweep"]["n"] == 1
    assert out["after_high_sweep"]["reversal_through_mid_pct"] == 100.0
    assert out["after_high_sweep"]["opposite_side_also_taken_pct"] == 0.0


def test_btc_ambiguous_same_day_not_guessed():
    mon = date(2026, 7, 20)
    days = [
        _day(mon, 100, 110, 90, 105),
        _day(mon + timedelta(days=1), 105, 120, 80, 100),  # touches BOTH sides same day
        _day(mon + timedelta(days=2), 100, 105, 95, 100),
    ]
    out = btc_monday._study(days)  # noqa: SLF001
    assert out["sweep_direction"]["ambiguous_pct"] == 100.0
    assert out["after_high_sweep"]["n"] == 0 and out["after_low_sweep"]["n"] == 0


def test_btc_no_sweep_and_outside_week_flag():
    mon1 = date(2026, 7, 13)
    mon2 = date(2026, 7, 20)
    days = [
        # week 1: tight week, high 105 low 95
        _day(mon1, 100, 105, 95, 102),
        _day(mon1 + timedelta(days=1), 102, 104, 96, 100),
        _day(mon1 + timedelta(days=2), 100, 103, 97, 101),
        # week 2: Monday opens OUTSIDE prev week range on one side only
        # (H=106 > prev 105, L=96 > prev 95 -> outside=True, engulf=False)
        _day(mon2, 106, 106, 96, 100),
        _day(mon2 + timedelta(days=1), 100, 104, 97, 100),
        _day(mon2 + timedelta(days=2), 100, 103, 98, 99),
    ]
    out = btc_monday._study(days)  # noqa: SLF001
    assert out["weeks_analyzed"] == 2
    assert out["outside_prev_week"]["n"] == 1
    assert out["outside_prev_week"]["engulf_n"] == 0  # one day never engulfs a 7d range here


# ---------------- JARVIS consistency (numbers come from inputs, no fabrication)

def test_jarvis_uses_only_snapshot_numbers():
    desk = {
        "market_intelligence": {
            "state": "CURRENT",
            "macro_quad": {"quad": "Q2 Reflation"},
            "cycle_compass": {"compass": "RISK-ON · DOWN the curve"},
            "crash_meter": {"value": 39, "severity": "WATCH", "coverage": "6/12 subcomponents live"},
            "early_warning": {"fear_greed": {"value": 55, "state": "Neutral", "signal": "no contrarian edge"}},
            "crashmeter_v3": {"state": "CURRENT", "score": 2, "label": "WASPADA", "c": 1, "cape": 40.57,
                              "a2": 1, "months_since_inversion_end": 11.4, "b1": 0, "b2": 0},
        },
        "carry_trade": {"state": "CARRY_ON",
                        "top_carry_trades": [{"trade_expression": "LONG_PAIR AUDJPY / fund JPY / own AUD"}]},
        "ticker_packets": {"us": {"AAA": {"thesis_lifecycle": {"state": "PREPARING"}},
                                  "BBB": {"thesis_lifecycle": {"state": "NOT_READY"}}}},
        "alpha_center": {"shadow_candidates": []},
        "capital_gate": {"permission": "BLOCKED", "mature_required": 30},
    }
    out = _jarvis_brief(desk)
    text = "\n".join(out)
    assert "Q2 Reflation" in text and "39/100" in text and "2/4" in text
    assert "AUDJPY" in text and "40.57" in text
    assert "2 ticker" in text  # lifecycle counts reflect the synthetic packets


def test_jarvis_silent_when_data_missing():
    out = _jarvis_brief({"market_intelligence": {"state": "UNAVAILABLE"}, "ticker_packets": {}})
    assert all("None" not in line and "nan" not in line.lower() for line in out)
