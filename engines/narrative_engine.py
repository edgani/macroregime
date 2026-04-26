"""engines/narrative_engine.py

Adaptive Narrative Discovery Engine.
Scores narratives from narrative_universe.py against current price data.
No news API needed — uses price action as confirmation.

Like screenshot 3 (transformer/switchgear post): the system should detect
when a bottleneck supply chain is triggering BEFORE it's consensus.

Detection logic:
1. Price momentum of beneficiary tickers vs benchmark
2. Relative strength acceleration (6M vs 12M) = emerging narrative
3. Volume expanding on up days = institutional accumulation
4. Regime alignment multiplier

Brewing narratives: high constraint + price building + not yet consensus
Active narratives: price already moved but trend intact
Exhausted narratives: overbought + weakening relative strength
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from config.narrative_universe import get_all_narratives, NarrativeTemplate, get_by_quad

def _ret(s, n):
    if s is None: return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < n+1: return None
    base = float(s.iloc[-n-1])
    if not math.isfinite(base) or abs(base) < 1e-10: return None
    r = float(s.iloc[-1]/base - 1)
    return r if math.isfinite(r) else None

def _rs(close, bench, n=63):
    a = _ret(close, n); b = _ret(bench, n)
    if a is None or b is None: return None
    return a - b

def _acc(close, n=40):
    """Volume accumulation approximation from price action only."""
    try:
        c = pd.to_numeric(close, errors="coerce").dropna().tail(n).values
        if len(c) < 10: return 0.5
        rets = np.diff(c)/(c[:-1]+1e-10)
        pos_days = rets > 0.001; neg_days = rets < -0.001
        pos_avg = float(np.mean(np.abs(rets[pos_days]))) if pos_days.any() else 0
        neg_avg = float(np.mean(np.abs(rets[neg_days]))) if neg_days.any() else 0
        if neg_avg < 1e-8: return 0.75
        return float(np.clip(0.5 * pos_avg/neg_avg, 0.0, 1.0))
    except: return 0.5

def _score_narrative_via_prices(
    narrative: NarrativeTemplate,
    prices: Dict[str, pd.Series],
    benchmark: str = "SPY",
    quad: str = "Q3",
) -> dict:
    """Score a narrative based on price action of its beneficiaries."""
    bench = prices.get(benchmark)
    beneficiary_tickers = []
    for market_tickers in narrative.beneficiaries.values():
        beneficiary_tickers.extend(market_tickers)

    scores = []
    best_ticker = None
    best_rs = None

    for ticker in beneficiary_tickers:
        close = prices.get(ticker)
        if close is None: continue
        close = pd.to_numeric(close, errors="coerce").dropna()
        if len(close) < 30: continue

        rs_3m = _rs(close, bench, 63)
        rs_1m = _rs(close, bench, 21)
        rs_6m = _rs(close, bench, 126)
        acc_s = _acc(close, 40)

        # Acceleration signal: 6M RS > 3M RS = momentum building
        acceleration = 0.0
        if rs_6m is not None and rs_3m is not None:
            acceleration = max(0.0, rs_3m - rs_6m*0.5)  # 3M accelerating vs 6M pace

        # Combined ticker score
        rs_score = float(np.clip(0.5 + 3.0*(rs_3m or 0.0), 0.0, 1.0))
        ticker_score = 0.40*rs_score + 0.30*acc_s + 0.30*float(np.clip(0.5 + acceleration*5, 0.0, 1.0))
        scores.append(ticker_score)

        if best_rs is None or (rs_3m or -99) > (best_rs or -99):
            best_rs = rs_3m
            best_ticker = ticker

    if not scores:
        # Narrative not confirmable — give base score from regime alignment
        base = narrative.regime_alignment.get(quad, 0.5) * 0.3
        return dict(
            name=narrative.name, score=round(base, 3),
            stage="unconfirmed", conviction=0.0,
            best_ticker=None, rs_confirmation=0.0,
            regime_score=narrative.regime_alignment.get(quad, 0.5),
            pump_risk=narrative.pump_risk,
            description=narrative.description[:100],
        )

    avg_score = float(np.mean(scores))
    max_score = float(np.max(scores))
    regime_mult = narrative.regime_alignment.get(quad, 0.5)

    # Final narrative score
    final = (0.40*avg_score + 0.30*max_score + 0.30*regime_mult) * narrative.conviction_ceiling
    final = float(np.clip(final * (1.0 - narrative.pump_risk*0.3), 0.0, 1.0))

    # Stage classification
    if avg_score > 0.70 and max_score > 0.80:
        stage = "active"       # narrative is running
    elif avg_score > 0.55:
        stage = "building"     # momentum building, not yet consensus
    elif avg_score > 0.40:
        stage = "brewing"      # early signals, high alpha if right
    else:
        stage = "dormant"

    # Conviction = regime fit × price confirmation × (1 - pump_risk)
    conviction = regime_mult * avg_score * (1.0 - narrative.pump_risk) * narrative.conviction_ceiling

    return dict(
        name=narrative.name,
        score=round(final, 3),
        stage=stage,
        conviction=round(conviction, 3),
        best_ticker=best_ticker,
        rs_confirmation=round(best_rs or 0.0, 4),
        regime_score=regime_mult,
        pump_risk=narrative.pump_risk,
        category=narrative.category,
        beneficiaries={k:v for k,v in narrative.beneficiaries.items()},
        fades={k:v for k,v in narrative.fades.items()},
        typical_weeks=narrative.typical_duration_weeks,
        confirmation_signals=narrative.confirmation_signals[:3],
        description=narrative.description[:120],
        catalyst_types=narrative.catalyst_types[:3],
    )


class NarrativeEngine:
    """
    Scores all narratives against current price data.
    Adaptively discovers which narratives are live, brewing, or dormant.
    """

    def run(
        self,
        prices: Dict[str, pd.Series],
        quad_str: str = "Q3",
        quad_mon: str = "Q2",
        benchmark: str = "SPY",
        top_n: int = 20,
    ) -> Dict[str, object]:

        narratives = get_all_narratives()
        scored = []

        for n in narratives:
            result = _score_narrative_via_prices(n, prices, benchmark, quad_str)
            # Monthly overlay boost: if narrative aligns with monthly quad too
            monthly_boost = n.regime_alignment.get(quad_mon, 0.5)
            if monthly_boost > 0.80:
                result["score"] = float(np.clip(result["score"] + 0.05, 0.0, 1.0))
                result["conviction"] = float(np.clip(result["conviction"] + 0.05, 0.0, 1.0))
            result["monthly_aligned"] = monthly_boost > 0.70
            scored.append(result)

        scored.sort(key=lambda x: x["score"], reverse=True)

        active   = [s for s in scored if s["stage"] == "active"][:top_n]
        building = [s for s in scored if s["stage"] == "building"][:top_n]
        brewing  = [s for s in scored if s["stage"] == "brewing"][:top_n]
        dormant  = [s for s in scored if s["stage"] == "dormant"][:5]

        # Top narrative per category
        by_cat: Dict[str, dict] = {}
        for s in scored:
            cat = s.get("category","")
            if cat not in by_cat:
                by_cat[cat] = s

        # Market-specific narratives
        us_narratives     = [s for s in scored if any("us" in k for k in s.get("beneficiaries",{}))][:10]
        ihsg_narratives   = [s for s in scored if any("ihsg" in k for k in s.get("beneficiaries",{}))][:8]
        crypto_narratives = [s for s in scored if any("crypto" in k for k in s.get("beneficiaries",{}))][:8]
        fx_narratives     = [s for s in scored if any("fx" in k for k in s.get("beneficiaries",{}))][:6]
        commodity_narr    = [s for s in scored if any("commodity" in k for k in s.get("beneficiaries",{}))][:8]

        # Find "brewing" bottleneck-like plays (before they're consensus)
        # This is the "transformer/switchgear" type discovery
        pre_consensus = [
            s for s in scored
            if s["stage"] in ("brewing","building")
            and s["regime_score"] >= 0.70
            and s["pump_risk"] <= 0.40
            and s["conviction"] >= 0.30
        ][:10]

        return dict(
            all_narratives=scored[:top_n],
            active=active,
            building=building,
            brewing=brewing,
            dormant=dormant,
            by_category=by_cat,
            us_narratives=us_narratives,
            ihsg_narratives=ihsg_narratives,
            crypto_narratives=crypto_narratives,
            fx_narratives=fx_narratives,
            commodity_narratives=commodity_narr,
            pre_consensus=pre_consensus,
            summary=dict(
                active_count=len(active),
                building_count=len(building),
                brewing_count=len(brewing),
                top_conviction=scored[0]["name"] if scored else "—",
                top_conviction_score=scored[0]["conviction"] if scored else 0.0,
            ),
        )
