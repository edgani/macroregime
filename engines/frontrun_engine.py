"""frontrun_engine.py

Front-Run Engine — Anticipate Hedgeye's next move BEFORE they signal it.

Philosophy (from McCullough himself):
  "Deterministic and unpredictable at the same time because small differences 
   in starting conditions produce large differences later." — Brennan

Since Hedgeye's process is deterministic (rule-based), WE CAN predict their 
next signal if we measure the same inputs they measure.

HOW HEDGEYE PICKS TICKERS:
  1. QUAD determines the playbook (historical winners/losers)
  2. RISK RANGE SIGNAL (TRADE/TREND/TAIL) determines timing
     - Signal = price + volume + volatility RoC at 3 durations
     - TRADE = immediate-term (days to weeks)
     - TREND = intermediate-term (weeks to months) ← most important
     - TAIL = long-term (months to years)
  3. Signal + Quad BOTH align → highest conviction entry
  4. Signal changes BEFORE Hedgeye communicates → we can be earlier

HOW TO FRONT-RUN:
  A. Lead indicators: 
     - Dubai/Abu Dhabi exchanges bottomed March 16 → US bottomed March 31
     - Semiconductors held trend during selloff → led the rally
     - FX pairs broke before equities confirmed
  B. Price over narrative:
     - When oil futures peak BEFORE the news → regime shift is starting
     - When EM ETFs make new highs BEFORE USD is officially "broken" → buy EM
  C. Correlation regime shift:
     - When USD/SPX corr breaks below -0.85 → Hedgeye will add long equities
     - When USD/BTC corr breaks below -0.90 → Hedgeye will add BTC
  D. Global leading regions:
     - Tel Aviv, Dubai: geopolitical risk leading indicators
     - South Korea (EWY): tech/semis proxy, leads US tech by 4-6 weeks
     - Taiwan (EWT): same — holds trend = semis healthy
"""
from __future__ import annotations
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


def _ret(s: pd.Series, n: int) -> Optional[float]:
    if s is None or len(s) < n + 1:
        return None
    try:
        r = float(s.iloc[-1] / s.iloc[-n] - 1)
        return r if math.isfinite(r) else None
    except Exception:
        return None


def _approximate_signal_state(s: pd.Series) -> Tuple[str, str, str]:
    """
    Approximate Hedgeye's TRADE/TREND/TAIL signals from price.
    
    Hedgeye uses price + volume + volatility. We approximate:
    - TRADE (immediate, ~15D): above/below recent range midpoint
    - TREND (intermediate, ~63D): above/below 63-day moving average  
    - TAIL (long-term, ~252D): above/below 252-day moving average

    State: "bullish" | "bearish" | "neutral"
    """
    if s is None or len(s) < 20:
        return "neutral", "neutral", "neutral"

    latest = float(s.iloc[-1])

    # TRADE: is price in upper or lower half of 15D range?
    tail15 = s.tail(15)
    lo15, hi15 = float(tail15.min()), float(tail15.max())
    mid15 = (lo15 + hi15) / 2
    if hi15 <= lo15 + 1e-6:
        trade = "neutral"
    elif latest > mid15 * 1.005:
        trade = "bullish"
    elif latest < mid15 * 0.995:
        trade = "bearish"
    else:
        trade = "neutral"

    # TREND: above/below 63D MA
    if len(s) >= 63:
        ma63 = float(s.tail(63).mean())
        if latest > ma63 * 1.01:
            trend = "bullish"
        elif latest < ma63 * 0.99:
            trend = "bearish"
        else:
            trend = "neutral"
    else:
        trend = "neutral"

    # TAIL: above/below 252D MA
    if len(s) >= 252:
        ma252 = float(s.tail(252).mean())
        tail_st = "bullish" if latest > ma252 * 1.02 else ("bearish" if latest < ma252 * 0.98 else "neutral")
    else:
        tail_st = "neutral"

    return trade, trend, tail_st


def _score_signal(trade: str, trend: str, tail: str) -> float:
    """Combine TRADE/TREND/TAIL into 0-1 bullish score."""
    m = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}
    return 0.30 * m[trade] + 0.45 * m[trend] + 0.25 * m[tail]


# Hedgeye's Quad-based playbook (calibrated from April 17 weekly summary)
_QUAD_PLAYBOOK = {
    "Q1": {
        "long":  ["QQQ", "XLK", "XLY", "XLI", "IWM", "EWH", "EWW", "ARGT", "GLD", "IBIT"],
        "short": ["TLT", "ZROZ", "XLU", "XLP", "GLD"],
        "style": ["growth", "momentum", "high_beta"],
        "avoid": ["defensives", "staples", "utilities"],
    },
    "Q2": {
        "long":  ["XLE", "XLI", "XLB", "GLD", "SLV", "IBIT", "EWH", "EWW", "ARGT", "NORW", "XTL", "COM"],
        "short": ["XLP", "XLU", "TLT"],
        "style": ["value", "cyclicals", "commodities"],
        "avoid": ["consumer_staples", "long_duration_bonds"],
    },
    "Q3": {
        "long":  ["GLD", "XLE", "XOP", "COM", "TLT", "XTL", "XLI", "ARGT", "EWH", "NORW", "BNO"],
        "short": ["XLK", "XLY", "XLF", "MAGS", "QQQ", "XLP"],
        "style": ["stagflation_protection", "real_assets", "inflation_hedges"],
        "avoid": ["tech", "growth", "consumer_discretionary"],
    },
    "Q4": {
        "long":  ["TLT", "XLV", "XLP", "XLU", "GLD", "LQD"],
        "short": ["XLE", "XLB", "XLK", "XLY", "IWM"],
        "style": ["defensive", "quality", "low_beta"],
        "avoid": ["cyclicals", "energy", "small_cap"],
    },
}

# Hybrid Q2/Q3 playbook (April 2026 situation: Monthly Q2 + Structural Q3)
_HYBRID_Q2_Q3 = {
    "long": ["GLD", "XLI", "XTL", "XLE", "EWH", "EWW", "ARGT", "NORW", "IBIT", "SLV", "COM", "BNO"],
    "short": ["XLP", "XLK", "XLY", "XLF", "MAGS"],
    "long_rationale": "Monthly Q2 (growth + inflation) INSIDE Structural Q3 (stagflation)",
    "short_rationale": "Q3 structural shorts on Q2 rallies = highest conviction",
    "position_sizing": "50% conviction — use monthly signal for timing, structural for direction",
    "key_message": "'Flation Now' = commodities/gold/energy NOW. 'Stag On A Lag' = short tech/discretionary LATER.",
}


def _ticker_opportunity_score(
    ticker: str,
    s: pd.Series,
    s_quad: str,
    m_quad: str,
    usd_trend: str,
    usd_corr: Optional[float],
) -> Dict:
    """
    Score a single ticker for long/short opportunity.
    Replicates the Signal + Quad convergence logic.
    """
    if s is None or len(s) < 20:
        return {"available": False}

    trade, trend, tail = _approximate_signal_state(s)
    signal_score = _score_signal(trade, trend, tail)

    # Is this ticker in the quad playbook?
    s_pb = _QUAD_PLAYBOOK.get(s_quad, {})
    m_pb = _QUAD_PLAYBOOK.get(m_quad, {})

    in_s_long = ticker in s_pb.get("long", [])
    in_m_long = ticker in m_pb.get("long", [])
    in_s_short = ticker in s_pb.get("short", [])
    in_m_short = ticker in m_pb.get("short", [])
    in_hybrid_long = ticker in _HYBRID_Q2_Q3["long"]
    in_hybrid_short = ticker in _HYBRID_Q2_Q3["short"]

    # Quad alignment score
    quad_long_score = 0.0
    quad_short_score = 0.0
    if in_s_long and in_m_long:
        quad_long_score = 1.0
    elif in_hybrid_long:
        quad_long_score = 0.85
    elif in_s_long or in_m_long:
        quad_long_score = 0.60
    if in_s_short and in_m_short:
        quad_short_score = 1.0
    elif in_hybrid_short:
        quad_short_score = 0.85
    elif in_s_short or in_m_short:
        quad_short_score = 0.60

    # USD overlay
    usd_boost = 0.0
    if usd_corr is not None and usd_trend == "bearish":
        if usd_corr < -0.85:
            usd_boost = 0.20
        elif usd_corr < -0.70:
            usd_boost = 0.10

    # Final long/short conviction
    long_conv = (0.45 * quad_long_score + 0.40 * signal_score + 0.15) + usd_boost
    short_conv = 0.45 * quad_short_score + 0.40 * (1 - signal_score) + 0.15

    r1m = _ret(s, 21)
    r3m = _ret(s, 63)

    action = "neutral"
    if long_conv >= 0.65 and quad_long_score > quad_short_score:
        action = "LONG"
    elif short_conv >= 0.65 and quad_short_score > quad_long_score:
        action = "SHORT"
    elif long_conv >= 0.55:
        action = "lean_long"
    elif short_conv >= 0.55:
        action = "lean_short"

    return {
        "available": True,
        "trade": trade, "trend": trend, "tail": tail,
        "signal_score": round(signal_score, 3),
        "quad_long_score": round(quad_long_score, 3),
        "quad_short_score": round(quad_short_score, 3),
        "long_conviction": round(long_conv, 3),
        "short_conviction": round(short_conv, 3),
        "action": action,
        "r1m": round(r1m, 4) if r1m is not None else None,
        "r3m": round(r3m, 4) if r3m is not None else None,
        "usd_boost": round(usd_boost, 3),
        "in_hybrid_long": in_hybrid_long,
        "in_hybrid_short": in_hybrid_short,
    }


def run_frontrun_engine(
    prices: Dict[str, pd.Series],
    s_quad: str = "Q3",
    m_quad: str = "Q2",
    usd_trend: str = "bearish",
    usd_correlations: Optional[Dict] = None,
) -> Dict:
    """
    Run the full front-run analysis.

    Returns:
    - top_longs: ranked tickers to buy (Signal + Quad aligned)
    - top_shorts: ranked tickers to sell
    - frontrun_alerts: signals that Hedgeye will likely act on soon
    - regime_specific_playbook: current Q2/Q3 hybrid playbook
    - three_big_themes: AI buildout, supply chain, demographics
    """
    corrs = usd_correlations or {}

    # Score all tracked tickers
    ticker_universe = list(set(
        _HYBRID_Q2_Q3["long"] + _HYBRID_Q2_Q3["short"] +
        _QUAD_PLAYBOOK.get(s_quad, {}).get("long", []) +
        _QUAD_PLAYBOOK.get(s_quad, {}).get("short", []) +
        _QUAD_PLAYBOOK.get(m_quad, {}).get("long", []) +
        _QUAD_PLAYBOOK.get(m_quad, {}).get("short", [])
    ))

    results = {}
    for tk in ticker_universe:
        s = prices.get(tk)
        usd_corr = corrs.get(tk, {}).get("corr_15d") if isinstance(corrs.get(tk), dict) else None
        score_data = _ticker_opportunity_score(tk, s, s_quad, m_quad, usd_trend, usd_corr)
        if score_data.get("available"):
            results[tk] = score_data

    # Rank
    longs = sorted(
        [(tk, d) for tk, d in results.items() if d["action"] in ("LONG", "lean_long")],
        key=lambda x: x[1]["long_conviction"], reverse=True
    )
    shorts = sorted(
        [(tk, d) for tk, d in results.items() if d["action"] in ("SHORT", "lean_short")],
        key=lambda x: x[1]["short_conviction"], reverse=True
    )

    # Front-run alerts: Signal just turned bullish on a Quad-aligned ticker
    frontrun_alerts = []
    for tk, d in results.items():
        if d["in_hybrid_long"] and d["trend"] == "bullish" and d["trade"] == "bullish":
            frontrun_alerts.append({
                "ticker": tk,
                "alert": f"⚡ {tk}: TRADE+TREND both bullish on Hybrid Q2/Q3 long list → Hedgeye add imminent",
                "priority": "high",
                "conviction": d["long_conviction"],
            })
        elif d["in_hybrid_short"] and d["trend"] == "bearish" and d["trade"] == "bearish":
            frontrun_alerts.append({
                "ticker": tk,
                "alert": f"🔴 {tk}: TRADE+TREND both bearish on Hybrid Q2/Q3 short list → Hedgeye short signal",
                "priority": "high",
                "conviction": d["short_conviction"],
            })

    frontrun_alerts.sort(key=lambda x: x["conviction"], reverse=True)

    # Three structural narratives from Hedgeye (April 2026)
    three_themes = [
        {
            "name": "AI Buildout — GPU→CPU Shift",
            "stage": "early",
            "description": (
                "Agentic AI shifts bottleneck from GPU compute to CPU processing. "
                "Complex orchestration = 95% CPU. Winners: Intel (INTC), AMD, NVDA (still), "
                "memory (MU), photonics, power infrastructure. "
                "From Morgan Stanley/Georgia Tech: as AI workflows become action-heavy, "
                "GPU dominance fades → CPU, memory, networking benefit."
            ),
            "tickers_long": ["XLK", "NVDA", "AVGO", "GOOGL", "AMZN"],
            "tickers_short": ["MSFT", "SKYY", "CIBR"],
            "confluence_with_quad": "Monthly Q2 provides growth runway; Structural Q3 creates selectivity",
            "hedgeye_note": "AI hype staging comeback — $BIRD, $MYSE AI-branded names surging",
        },
        {
            "name": "Supply Chain Realignment — Western Hemisphere",
            "stage": "structural",
            "description": (
                "Strait of Hormuz disruption = Supply Chain Shock 3.0 (after COVID 2020, Ukraine 2022). "
                "Companies diversifying away from Hormuz-dependent supply chains. "
                "'All roads lead to the Western Hemisphere.' "
                "Beneficiaries: Mexico (reshoring hub), Canada (energy alternative), "
                "US industrials (domestic manufacturing), Argentina (ag + lithium)."
            ),
            "tickers_long": ["EWW", "EWC", "XLI", "ARGT", "IWM"],
            "tickers_short": ["EWG", "EWJ", "companies with Hormuz exposure"],
            "confluence_with_quad": "Q3 stagflation rewards real assets + infrastructure. Q2 monthly amplifies cyclicals.",
            "hedgeye_note": "McCullough: 'Strike three on geopolitical supply chain shocks'",
        },
        {
            "name": "K-Shaped Economy / Demographic Divergence",
            "stage": "ongoing",
            "description": (
                "SPX at all-time highs, Michigan Consumer Sentiment at 74-year LOW. "
                "Financial assets inflating while consumer purchasing power deflates. "
                "'The brands of my youth are dead men walking.' "
                "Winners: premium/luxury (pricing power), healthcare, tech platforms. "
                "Losers: mid-market consumer brands, brick-and-mortar, traditional media."
            ),
            "tickers_long": ["XLV", "XLI", "premium consumer plays"],
            "tickers_short": ["XLP", "traditional retail", "legacy media"],
            "confluence_with_quad": "Q3 stagflation accelerates K-shape — rich get richer, middle gets squeezed",
            "hedgeye_note": "K-shaped economy = Fourth Turning in motion. Trade the divergence.",
        },
    ]

    # Current hybrid playbook with exact Hedgeye positioning
    current_playbook = {
        **_HYBRID_Q2_Q3,
        "risk_ranges": {
            "SPX": {"range": "6771-7198", "signal": "bullish"},
            "NASDAQ": {"range": "22701-24830", "signal": "bullish"},
            "RUT": {"range": "2634-2805", "signal": "bullish"},
            "Gold": {"range": "4701-4851", "signal": "bullish"},
            "Oil_WTI": {"range": "81.90-110.04", "signal": "bullish"},
            "USD": {"range": "97.55-98.95", "signal": "bearish"},
            "VIX": {"range": "15.64-22.12", "signal": "bearish"},
            "XTL": {"range": "202-223", "signal": "bullish"},
            "XLI": {"range": "implied bullish", "signal": "bullish"},
            "BTC": {"range": "TREND support broken higher", "signal": "bullish"},
            "Copper": {"range": "5.67-6.26", "signal": "bullish"},
            "Silver": {"range": "71-82", "signal": "bullish"},
        },
        "as_of": "April 20, 2026",
        "source": "Hedgeye Macro Monday + Signs & Signals",
    }

    return {
        "top_longs": [(tk, d["long_conviction"], d.get("trade"), d.get("trend"))
                      for tk, d in longs[:10]],
        "top_shorts": [(tk, d["short_conviction"], d.get("trade"), d.get("trend"))
                       for tk, d in shorts[:6]],
        "frontrun_alerts": frontrun_alerts[:8],
        "ticker_signals": results,
        "current_playbook": current_playbook,
        "three_structural_themes": three_themes,
        "regime_summary": (
            f"Structural {s_quad} + Monthly {m_quad} + USD {usd_trend.upper()} = "
            "Hybrid Q2/Q3 setup. Trade the Monthly Q2 relief with Q3 structural awareness. "
            "Buy: GLD, XLI, XTL, EWH, EWW, IBIT. Short: XLP, XLK, XLY on Q2 bounces."
        ),
    }
