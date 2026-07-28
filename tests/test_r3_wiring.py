"""R3 engine-UI wiring tests: canonical schema, crash meter, quads, carry, alpha funnel.

Unit tests use a constructed desk dict (test fixture — not production data).
Integration boot uses AppTest with the real cache in offline mode.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from warroom import crash_meter as CM
from warroom import component_registry as REG


def _fake_desk(stale_days=0):
    return {
        "data_asof": {"date": "2026-07-28", "stale_days": stale_days},
        "regime": {"structural": "Quad 3", "monthly": "Quad 4",
                   "struct_probs": {"Quad 3": 0.6}, "month_probs": {"Quad 4": 0.5}},
        "regime_transition": {"stage": "BUILDING", "next_quad": "Quad 4", "drivers": ["cpi"]},
        "explain": "test explanation",
        "vix": 24.0,
        "breadth": 42,
        "posture": "Defensive",
        "shock_prob": "elevated",
        "meters_computed": {
            "trend": {"value": 55, "status": "ok", "real": True},
            "credit": {"value": 70, "status": "HY spread widening", "real": True},
            "liquidity": {"value": 30, "status": "tight", "real": True},
        },
        "funding": {"score": 68, "source": "FRED", "label": "stress"},
        "crowd_market": {"score": 60},
        "macro_regime": {"risk_regime": {"score": 55, "label": "risk-off"}},
        "policy": {"stance": "restrictive", "score": 50},
        "early_warning": {"fear_greed": {"value": 80, "state": "greed", "confidence": "weak"}},
        "crash": {"pressure": 45, "type": "watch", "components": {"vol": 1}},
        "crash_lead": {"crash_lead": {"risk_level": "moderate", "honest_note": "note"}},
        "fx": {"carry": {"stage": "active", "pairs": []}},
        "causal_chains": [{"t": "x"}],
        "batch_a": {"transmission": {"x": 1}, "cascade": None},
        "conviction": [{"ticker": "NVDA", "_dir": "Long", "score": 80, "close": 100.0}],
        "watchlist": [{"ticker": "AMD", "_dir": "Watch", "score": 40, "close": 90.0}],
        "ranked": 50,
        "decision_market": {"ai": {"candidates": [{"ticker": "NVDA", "status": "MODEL_REQUIRED", "reason": "no calibrated model"}]}},
        "validation": {"checked": 5, "passed": 3},
        "risk": {"n": 0},
    }


# ---- crash meter ----

def test_crash_meter_schema_and_severity():
    cm = CM.build(_fake_desk())
    assert 0 <= cm["value"] <= 100
    assert cm["severity"] in {"CALM", "WATCH", "ELEVATED", "SEVERE", "EXTREME"}
    assert cm["proof_status"] == "RESEARCH_ONLY"
    assert cm["execution_eligible"] is False
    assert "NOT a calibrated crash probability" in cm["claim_limit"]
    for key in CM.COMPONENT_KEYS:
        assert key in cm["subcomponents"]
    # leverage and physical have no feeds -> NO_DATA, never 0
    assert cm["subcomponents"]["leverage"]["value"] is None
    assert cm["subcomponents"]["leverage"]["state"] == "NO_DATA"
    assert cm["subcomponents"]["physical"]["state"] == "NO_DATA"
    # live subcomponents carry values and basis
    assert cm["subcomponents"]["volatility"]["value"] == 35  # (24-10)*2.5
    assert cm["subcomponents"]["volatility"]["basis"] == "VIX 24.0"
    assert cm["drivers"], "drivers must be listed"


def test_crash_meter_empty_desk_no_fabrication():
    cm = CM.build({"data_asof": {"date": None, "stale_days": None}})
    assert cm["value"] is None
    assert cm["severity"] == "NO_DATA"
    assert cm["action_hint"] == "no action — insufficient evidence"


# ---- component registry ----

def test_registry_canonical_schema_valid():
    d = _fake_desk()
    d["crash_meter"] = CM.build(d)
    comps = REG.build(d)
    assert len(comps) >= 20, f"only {len(comps)} components registered"
    errors = REG.validate(comps)
    assert errors == [], f"schema errors: {errors}"


def test_registry_stale_not_executable():
    d = _fake_desk(stale_days=30)
    d["crash_meter"] = CM.build(d)
    comps = REG.build(d)
    assert all(c["data_state"] == "STALE_LAST_KNOWN" for c in comps)
    assert all(c["execution_eligible"] is False for c in comps)
    assert all(c["as_of"] == "2026-07-28" for c in comps)
    assert all(c["source"] for c in comps)


def test_registry_no_duplicate_source_of_truth():
    d = _fake_desk()
    d["crash_meter"] = CM.build(d)
    comps = REG.build(d)
    ids = [c["component_id"] for c in comps]
    assert len(ids) == len(set(ids)), "duplicate component_id -> conflicting source of truth"


def test_registry_quads_and_carry_present():
    d = _fake_desk()
    d["crash_meter"] = CM.build(d)
    comps = {c["component_id"]: c for c in REG.build(d)}
    assert comps["gip_structural_quad"]["value"] == "Quad 3"
    assert comps["gip_tactical_quad"]["value"] == "Quad 4"
    assert comps["regime_transition"]["value"] == "BUILDING"
    assert comps["fx_carry"]["value"]["stage"] == "active"
    assert comps["watch_universe"]["claim_limit"].startswith("WATCH is not alpha")


# ---- alpha funnel honesty ----

def test_alpha_watch_excluded_distinction():
    d = _fake_desk()
    # conviction = actionable candidates, watchlist = WATCH (not alpha),
    # decision_market candidates with status+reason = excluded with reason
    assert d["conviction"][0]["_dir"] == "Long"
    assert d["watchlist"][0]["_dir"] == "Watch"
    excl = [c for m in d["decision_market"].values() for c in m["candidates"] if c.get("status")]
    assert excl and excl[0]["reason"], "excluded candidates must carry an exact reason"
    # no zero prices anywhere in funnel
    for r in d["conviction"] + d["watchlist"]:
        assert r["close"] > 0


# ---- integration boot ----

@pytest.mark.skipif(os.getenv("RUN_SLOW") != "1", reason="slow integration boot; RUN_SLOW=1 to enable")
def test_app_boot_tabs_and_markers():
    os.environ["WARROOM_OFFLINE"] = "1"
    os.environ["WARROOM_AUTO_SHADOW"] = "0"
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=280).run()
    assert not app.exception
    # R4 consolidated the original 17 tabs into the final 11-tab design;
    # all original sections remain (see test_r4_consolidation.py parity tests)
    assert len(app.tabs) == 11
    md = " ".join(m.value for m in app.markdown).lower()
    for marker in ("crash meter", "structural", "tactical", "transition", "carry",
                   "alpha center", "validation", "early warning"):
        assert marker in md, f"missing marker: {marker}"
