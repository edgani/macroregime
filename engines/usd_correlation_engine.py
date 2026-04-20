"""usd_correlation_engine.py

THE MYTHIC VARIABLE — USD Correlation Engine.

McCullough April 20: "If only there were some mythic variable to which oil, yields,
equities, volatility, inflation expectations and absolute/relative policy expectations
all correlated to!"

When USD inverse correlations converge toward -1.0 on TRADE duration (15D),
THE DOLLAR becomes ALL THAT MATTERS. This is the regime switch signal.

Key insight from Hedgeye:
  - USD bearish TRADE+TREND → buy SPX, BTC, Gold, EM equities
  - USD bearish but Brent +0.82 → oil rises WITH dollar falling = Q2/Q3 hybrid
  - When USD/SPX correlation = -0.98 and USD/BTC = -0.97 → BOTH are pure dollar plays
  - FRONT-RUN: when correlation crosses -0.80 threshold, regime confirmation imminent

How to front-run Hedgeye:
  1. Monitor USD correlation DAILY
  2. When USD 15D corr vs SPX crosses below -0.85 → Hedgeye will start buying dips
  3. When USD 15D corr vs BTC crosses below -0.90 → expect BTC addition
  4. When USD/Brent corr rises above +0.70 → Q3 inflation impulse confirmed
  5. When correlations BREAK (USD/SPX goes from -0.97 to -0.50) → regime transition alert
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


# Hedgeye's exact correlation matrix from April 17-20, 2026
# Used to calibrate our thresholds
_HEDGEYE_REFERENCE = {
    "USD_SPX_15D": -0.98,  "USD_SPX_30D": -0.88,
    "USD_BTC_15D": -0.97,  "USD_BTC_30D": -0.75,
    "USD_BRENT_15D": 0.82, "USD_BRENT_30D": 0.53,
    "USD_GOLD_15D": -0.86, "USD_GOLD_30D": -0.20,
}

_CORR_PAIRS = {
    "SPX":     ("UUP", "SPY"),
    "NASDAQ":  ("UUP", "QQQ"),
    "BTC":     ("UUP", "BTC-USD"),
    "GOLD":    ("UUP", "GC=F"),
    "SILVER":  ("UUP", "SLV"),
    "BRENT":   ("UUP", "BZ=F"),
    "OIL_WTI": ("UUP", "CL=F"),
    "COPPER":  ("UUP", "HG=F"),
    "EEM":     ("UUP", "EEM"),
    "VIX":     ("UUP", "^VIX"),
    "TLT":     ("UUP", "TLT"),
    "TELECOM": ("UUP", "XTL"),
    "INDUST":  ("UUP", "XLI"),
    # Country ETFs for Global Quad signal
    "HK":      ("UUP", "EWH"),
    "MEXICO":  ("UUP", "EWW"),
    "ARGENTINA":("UUP","ARGT"),
    "NORWAY":  ("UUP", "NORW"),
    "GERMANY": ("UUP", "EWG"),
    "JAPAN":   ("UUP", "EWJ"),
    "JKSE":    ("UUP", "^JKSE"),
}


def _rolling_corr(s1: pd.Series, s2: pd.Series, window: int) -> Optional[float]:
    """Rolling correlation between daily returns over n trading days."""
    try:
        r1 = s1.pct_change().dropna()
        r2 = s2.pct_change().dropna()
        aligned = pd.concat([r1, r2], axis=1).dropna()
        if len(aligned) < window // 2:
            return None
        tail = aligned.tail(window)
        if len(tail) < 5:
            return None
        c = float(tail.iloc[:, 0].corr(tail.iloc[:, 1]))
        return c if math.isfinite(c) else None
    except Exception:
        return None


def _regime_from_corr(usd_spx_15d: Optional[float], usd_btc_15d: Optional[float],
                       usd_brent_15d: Optional[float]) -> str:
    """
    Classify USD correlation regime.

    Hedgeye framework:
    - DOLLAR DOMINANT (corr < -0.85): everything moves with USD → pure dollar play
    - GROWTH SIGNAL (corr -0.70 to -0.85): dollar matters but not everything
    - MIXED (corr -0.50 to -0.70): dollar one factor among many
    - FADING (corr > -0.50): dollar losing correlation → potential regime shift
    """
    if usd_spx_15d is None:
        return "unknown"
    c = usd_spx_15d
    if c <= -0.90:
        return "dollar_dominant"
    elif c <= -0.80:
        return "dollar_primary"
    elif c <= -0.65:
        return "dollar_factor"
    elif c <= -0.40:
        return "dollar_fading"
    else:
        return "dollar_decoupled"


def _classify_action(name: str, corr_15d: Optional[float], corr_30d: Optional[float],
                     usd_trend: str) -> Dict:
    """
    Per-asset action based on USD correlation strength.
    Replicates McCullough's "act on fractal signals" logic.
    """
    if corr_15d is None:
        return {"action": "monitor", "conviction": 0.0, "reason": "insufficient data"}

    abs_c = abs(corr_15d)
    # Is this an inverse (negative) or direct (positive) USD relationship?
    is_inverse = corr_15d < 0

    if usd_trend == "bearish":  # USD going down
        if is_inverse and abs_c >= 0.85:
            action = "strong_buy"
            conviction = min(1.0, abs_c)
            reason = f"USD bearish + high inverse corr {corr_15d:.2f} → mechanical long"
        elif is_inverse and abs_c >= 0.65:
            action = "buy_dip"
            conviction = abs_c * 0.8
            reason = f"USD bearish + moderate inverse corr {corr_15d:.2f}"
        elif not is_inverse and abs_c >= 0.70:  # direct positive (like oil in Q3)
            action = "overweight"
            conviction = abs_c * 0.7
            reason = f"Oil/commodities: direct USD corr {corr_15d:.2f} = inflation proxy"
        else:
            action = "neutral"
            conviction = 0.3
            reason = f"Weak corr {corr_15d:.2f} vs USD"
    elif usd_trend == "bullish":  # USD going up
        if is_inverse and abs_c >= 0.85:
            action = "avoid_short"
            conviction = abs_c
            reason = f"USD bullish + high inverse corr → mechanical SHORT setup"
        elif not is_inverse and abs_c >= 0.70:
            action = "overweight"
            conviction = abs_c * 0.6
            reason = "Inflation asset, benefits from USD strength"
        else:
            action = "neutral"
            conviction = 0.3
            reason = f"USD bullish, monitor {name}"
    else:
        action = "neutral"
        conviction = 0.25
        reason = "USD trend unclear"

    # Strengthen conviction if 15D and 30D are aligned
    if corr_30d is not None and abs(corr_30d) > abs_c * 0.7:
        conviction = min(1.0, conviction * 1.15)

    return {"action": action, "conviction": round(conviction, 3), "reason": reason,
            "corr_15d": corr_15d, "corr_30d": corr_30d}


def build_usd_correlation_matrix(prices: Dict[str, pd.Series]) -> Dict:
    """
    Build the full USD correlation matrix.

    Returns:
        {
            "usd_trend": "bearish" | "bullish" | "neutral",
            "usd_1m_return": float,
            "regime": "dollar_dominant" | "dollar_primary" | etc.,
            "correlations": {asset: {corr_15d, corr_30d, action, conviction}},
            "front_run_signals": [...],  # list of cross-threshold events
            "mythic_variable_active": bool,  # True when everything correlates
            "vs_hedgeye": {...},  # comparison to Hedgeye's reference numbers
            "best_longs_now": [str],
            "best_shorts_now": [str],
            "key_signal": str,
        }
    """
    uup = prices.get("UUP", pd.Series())
    if uup is None or len(uup) < 10:
        return {"available": False, "usd_trend": "unknown"}

    # USD trend
    usd_1m = float(uup.pct_change(21).iloc[-1]) if len(uup) > 21 else 0.0
    usd_1w = float(uup.pct_change(5).iloc[-1]) if len(uup) > 5 else 0.0

    if usd_1w < -0.005 and usd_1m < -0.01:
        usd_trend = "bearish"
    elif usd_1w > 0.005 and usd_1m > 0.01:
        usd_trend = "bullish"
    else:
        usd_trend = "neutral"

    # Compute correlations for all pairs
    correlations = {}
    for asset_name, (usd_tk, asset_tk) in _CORR_PAIRS.items():
        s_usd = prices.get(usd_tk, pd.Series())
        s_asset = prices.get(asset_tk, pd.Series())

        c15 = _rolling_corr(s_usd, s_asset, 15)
        c30 = _rolling_corr(s_usd, s_asset, 30)

        action_info = _classify_action(asset_name, c15, c30, usd_trend)
        correlations[asset_name] = {
            "corr_15d": round(c15, 3) if c15 is not None else None,
            "corr_30d": round(c30, 3) if c30 is not None else None,
            **action_info,
        }

    # Check "mythic variable active" — when corrs are extreme
    spx_c15 = correlations.get("SPX", {}).get("corr_15d")
    btc_c15 = correlations.get("BTC", {}).get("corr_15d")
    brent_c15 = correlations.get("BRENT", {}).get("corr_15d")
    gold_c15 = correlations.get("GOLD", {}).get("corr_15d")

    mythic_active = (
        spx_c15 is not None and abs(spx_c15) > 0.85 and
        btc_c15 is not None and abs(btc_c15) > 0.80
    )

    regime = _regime_from_corr(spx_c15, btc_c15, brent_c15)

    # Front-run signals: new threshold crossings
    front_run = []
    for asset, data in correlations.items():
        c = data.get("corr_15d")
        if c is None:
            continue
        if c <= -0.90 and usd_trend == "bearish":
            front_run.append({
                "asset": asset,
                "signal": f"⚡ {asset}: USD/corr extreme ({c:.2f}) → buy dip now",
                "priority": "high",
            })
        elif c >= 0.80 and asset in ("BRENT", "OIL_WTI", "COPPER") and usd_trend == "bearish":
            front_run.append({
                "asset": asset,
                "signal": f"🔥 {asset}: Positive USD/corr ({c:.2f}) + USD down = Q3 inflation signal",
                "priority": "high",
            })

    # Best longs/shorts based on action
    longs = [a for a, d in correlations.items()
             if d.get("action") in ("strong_buy", "buy_dip") and d.get("conviction", 0) > 0.6]
    shorts = [a for a, d in correlations.items()
              if d.get("action") == "avoid_short" and d.get("conviction", 0) > 0.6]

    # Vs Hedgeye reference
    vs_hedgeye = {}
    for key, ref_val in _HEDGEYE_REFERENCE.items():
        parts = key.split("_")
        asset = "_".join(parts[1:-1])  # e.g. SPX, BTC, BRENT
        window = "corr_15d" if parts[-1] == "15D" else "corr_30d"
        our_val = correlations.get(asset, {}).get(window)
        if our_val is not None:
            vs_hedgeye[key] = {
                "hedgeye": ref_val, "ours": our_val,
                "delta": round(our_val - ref_val, 3),
                "aligned": abs(our_val - ref_val) < 0.15,
            }

    # Key signal text
    if mythic_active and usd_trend == "bearish":
        key_signal = f"🎯 DOLLAR DOMINANT BEARISH — USD driving everything. Buy: {', '.join(longs[:4])}"
    elif regime == "dollar_fading":
        key_signal = "⚠️ USD correlations fading — regime transition possible, reduce conviction"
    elif usd_trend == "bullish":
        key_signal = "🔴 USD BULLISH — defensive posture, reduce equity/BTC/EM exposure"
    else:
        key_signal = f"USD {usd_trend} ({regime}) — moderate signal environment"

    return {
        "available": True,
        "usd_trend": usd_trend,
        "usd_1m_return": round(usd_1m, 4),
        "usd_1w_return": round(usd_1w, 4),
        "regime": regime,
        "mythic_variable_active": mythic_active,
        "correlations": correlations,
        "front_run_signals": front_run,
        "best_longs_now": longs[:5],
        "best_shorts_now": shorts[:3],
        "vs_hedgeye": vs_hedgeye,
        "key_signal": key_signal,
        "hedgeye_quote": '"If only there were some mythic variable to which everything correlated..." — KM',
    }
