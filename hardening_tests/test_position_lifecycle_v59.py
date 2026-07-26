from __future__ import annotations

import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import numpy as np
import pandas as pd

from position_lifecycle import classify_position_lifecycle
from gcfis.meta.final_desk import _score
from gcfis.orchestrator import run_gcfis


def _series(seed=1, drift=0.002, n=360):
    rng=np.random.default_rng(seed)
    return pd.Series(100*np.exp(np.cumsum(rng.normal(drift,0.008,n))), index=pd.date_range("2024-01-01", periods=n))


def test_missing_is_not_neutral():
    r=classify_position_lifecycle("commodity", {})
    assert r["position_state"]=="NO_POSITION_DATA"
    assert r["confidence"]=="LOW"
    assert r["live_decision_weight"]==0.0 and r["capital_permission"]=="BLOCKED"


def test_oi_geometry_is_ambiguous():
    r=classify_position_lifecycle("crypto", {"price_change_pct":4,"open_interest_change_pct":6})
    assert r["position_state"]=="LONG_BUILD_OR_NEW_RISK"
    assert "cannot prove long accumulation" in r["claim_boundary"]


def test_signed_long_build():
    r=classify_position_lifecycle("commodity", {"participant_long_change":15000,"participant_short_change":500})
    assert r["position_state"]=="LONG_BUILDING"


def test_short_covering_separate_from_accumulation():
    r=classify_position_lifecycle("commodity", {"price_change_pct":5,"participant_long_change":2663,"participant_short_change":-21074})
    assert r["position_state"]=="SHORT_COVERING"
    assert "covering-led" in r["claim_boundary"]


def test_cftc_signed_change_archetypes():
    feb17=classify_position_lifecycle("commodity", {"participant_long_change":-7793,"participant_short_change":7568})
    feb24=classify_position_lifecycle("commodity", {"participant_long_change":9479,"participant_short_change":5564})
    mar03=classify_position_lifecycle("commodity", {"participant_long_change":-6098,"participant_short_change":-6783})
    jul21=classify_position_lifecycle("commodity", {"participant_long_change":6308,"participant_short_change":4303})
    assert feb17["position_state"]=="BEARISH_REPOSITIONING"
    assert feb24["position_state"]=="MIXED_RISK_BUILD"
    assert mar03["position_state"]=="MIXED_DELEVERAGING"
    assert jul21["position_state"]=="MIXED_RISK_BUILD"


def test_crowding_never_confirms_top():
    r=classify_position_lifecycle("us", {"price_change_pct":2,"crowding_percentile":99})
    assert r["top_state"]!="DISTRIBUTION_TOP_CONFIRMED"


def test_top_requires_distribution_followthrough_and_weakening():
    r=classify_position_lifecycle("commodity", {
        "price_change_pct":-4,"participant_long_change":-18000,"participant_short_change":7000,
        "failed_high":True,"curve_change":-1,"continuation_return_pct":-3,
    })
    assert r["top_state"]=="DISTRIBUTION_TOP_CONFIRMED"


def test_physical_surge_without_speculative_build():
    r=classify_position_lifecycle("commodity", {
        "price_change_pct":7,"participant_long_change":1000,"participant_short_change":-20000,
        "physical_basis_change":2,"inventory_surprise":-1,
    })
    assert r["surge_state"]=="ACTIVE_PHYSICAL_SURGE"
    assert r["position_state"]=="SHORT_COVERING"


def test_all_market_contracts_fail_closed():
    for market in ("us","idx","fx","commodity","crypto"):
        r=classify_position_lifecycle(market,{"price_change_pct":1})
        assert r["position_state"]=="PRICE_ONLY_CONTEXT", market
        assert r["proof_state"]=="NOT_PROVEN"


def test_final_desk_score_ignores_surge():
    base={"ev":5,"conviction":70,"response":{"quality":60},"surge":0}
    high={**base,"surge":100}
    assert math.isclose(_score(base),_score(high),rel_tol=0,abs_tol=1e-12)


def test_orchestrator_serializes_nondefault_surge_and_lifecycle_before_rows():
    px=_series(1); bench=_series(2,drift=0.0005)
    out=run_gcfis({"CL=F":px},bench,{"chop":1.0},market_hints={"CL=F":"commodity"},
                  lifecycle_inputs_by_ticker={"CL=F":{"participant_long_change":12000,"participant_short_change":-3000,
                                                       "physical_basis_change":1,"price_change_pct":4}})
    a=out["per_ticker"]["CL=F"]
    assert a["surge"]["score"] is not None
    assert a["position_lifecycle"]["position_state"] in {"LONG_BUILDING","BULLISH_REPOSITIONING"}
    rows=(out["ranking"].get("master_long") or [])+(out["ranking"].get("master_short") or [])+(out["ranking"].get("deferred_longs") or [])
    # If this exact synthetic series is not actionable, inspect the raw signal contract through final desk rejection path.
    if rows:
        assert rows[0]["surge"] is not None
        assert rows[0]["position_lifecycle"]["market"]=="commodity"
    assert isinstance(out["final_desk"],dict) and "picks" in out["final_desk"]


def test_cftc_adapter_exposes_weekly_signed_changes():
    from full_live_data_hub import _cftc_lifecycle
    data={"disaggregated_futures":{"report_date":"2026-07-21","rows":[{
        "market_and_exchange_names":"WTI-PHYSICAL - NEW YORK MERCANTILE EXCHANGE",
        "change_in_m_money_long_all":"6308","change_in_m_money_short_all":"4303",
        "open_interest_all":"1864487","change_in_open_interest_all":"-10000",
    }]}}
    out=_cftc_lifecycle(data)
    row=next(iter(out.values()))
    assert row["participant"]=="managed_money"
    assert row["position_lifecycle"]["position_state"]=="MIXED_RISK_BUILD"
    assert row["position_lifecycle"]["live_decision_weight"]==0.0
