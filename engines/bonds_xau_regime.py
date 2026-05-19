"""engines/bonds_xau_regime.py — Bonds-XAU Correlation Edge (Sprint 6)

Adds a new edge source by analyzing structural relationships:
  - Real Yield (DGS10 - T10YIE) → gold inverse correlation
  - Yield Curve (DGS10 - DGS2) → recession signal → bonds bid
  - DXY-Gold rolling correlation strength
  - Gold/Silver ratio → risk regime (>80 risk off, <60 risk on)
  - TLT/GLD ratio → flight to quality vs inflation hedge
  - HYG/LQD spread → credit stress proxy
  - Real Yield 1y rate of change → gold/silver tactical signal

OUTPUT signals consumable by app.py for biasing positions in:
  GLD, SLV, GDX, GDXJ, SIL, TLT, IEF, TIP, DBC, miners

This engine ADDS edge that existing engines miss.
"""
from __future__ import annotations

import math
import logging
from typing import Dict, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _last(s) -> Optional[float]:
    if s is None:
        return None
    try:
        ser = pd.to_numeric(s, errors="coerce").dropna()
        return float(ser.iloc[-1]) if len(ser) > 0 else None
    except Exception:
        return None


def _change(s, periods: int) -> Optional[float]:
    if s is None:
        return None
    try:
        ser = pd.to_numeric(s, errors="coerce").dropna()
        if len(ser) <= periods:
            return None
        return float(ser.iloc[-1] - ser.iloc[-periods - 1])
    except Exception:
        return None


def _rolling_corr(s1, s2, window: int = 60) -> Optional[float]:
    """Rolling correlation between two series."""
    if s1 is None or s2 is None:
        return None
    try:
        a = pd.to_numeric(s1, errors="coerce").dropna()
        b = pd.to_numeric(s2, errors="coerce").dropna()
        # Align indexes
        joined = pd.concat([a, b], axis=1, join="inner").dropna()
        if len(joined) < window:
            return None
        # Use returns for correlation
        rets = joined.pct_change().dropna()
        if len(rets) < window:
            return None
        rolling = rets.iloc[:, 0].rolling(window).corr(rets.iloc[:, 1])
        last_corr = float(rolling.iloc[-1])
        return last_corr if math.isfinite(last_corr) else None
    except Exception:
        return None


def _ratio(s1, s2) -> Optional[float]:
    """Latest ratio s1/s2."""
    v1 = _last(s1)
    v2 = _last(s2)
    if v1 is None or v2 is None or v2 == 0:
        return None
    return v1 / v2


def compute_real_yield(fred: Dict) -> Optional[float]:
    """Real yield = nominal 10y - breakeven 10y."""
    dgs10 = _last(fred.get("DGS10"))
    t10yie = _last(fred.get("T10YIE"))
    if dgs10 is None or t10yie is None:
        return None
    return dgs10 - t10yie


def compute_yield_curve_2s10s(fred: Dict) -> Optional[float]:
    """2s10s curve: positive = normal, negative = inverted (recession signal)."""
    dgs10 = _last(fred.get("DGS10"))
    dgs2 = _last(fred.get("DGS2"))
    if dgs10 is None or dgs2 is None:
        return None
    return dgs10 - dgs2


def _first_available(prices: Dict, *keys):
    """Return first non-None value among keys (avoids Series 'or' ambiguity)."""
    for k in keys:
        v = prices.get(k)
        if v is not None:
            return v
    return None


def compute_gold_silver_ratio(prices: Dict) -> Optional[float]:
    """Gold/Silver ratio. <60 = risk on, >80 = risk off."""
    gld = _first_available(prices, "GLD", "GC=F")
    slv = _first_available(prices, "SLV", "SI=F")
    return _ratio(gld, slv)


def compute_tlt_gld_ratio(prices: Dict) -> Optional[float]:
    """TLT/GLD ratio. Rising = flight to quality, falling = inflation hedge."""
    return _ratio(prices.get("TLT"), prices.get("GLD"))


def compute_dxy_gold_corr(prices: Dict, window: int = 60) -> Optional[float]:
    """DXY-Gold rolling correlation. Strongly negative = classic regime."""
    dxy = _first_available(prices, "DX-Y.NYB", "UUP")
    gld = _first_available(prices, "GLD", "GC=F")
    return _rolling_corr(dxy, gld, window)


def compute_credit_spread(prices: Dict) -> Optional[float]:
    """HYG/LQD price ratio change as credit stress proxy."""
    try:
        hyg_raw = prices.get("HYG")
        lqd_raw = prices.get("LQD")
        if hyg_raw is None or lqd_raw is None:
            return None
        hyg = pd.to_numeric(hyg_raw, errors="coerce").dropna()
        lqd = pd.to_numeric(lqd_raw, errors="coerce").dropna()
        if len(hyg) > 30 and len(lqd) > 30:
            r_hyg = float(hyg.iloc[-1] / hyg.iloc[-30] - 1)
            r_lqd = float(lqd.iloc[-1] / lqd.iloc[-30] - 1)
            return r_hyg - r_lqd  # negative = credit underperforming = stress
    except Exception as e:
        logger.debug(f"Credit spread calc failed: {e}")
    return None


# ────────────────────────────────────────────────────────────────────────
# Regime classification
# ────────────────────────────────────────────────────────────────────────

def classify_bonds_xau_regime(
    real_yield: Optional[float],
    yield_curve: Optional[float],
    gold_silver: Optional[float],
    tlt_gld: Optional[float],
    dxy_gold_corr: Optional[float],
    credit_spread: Optional[float],
) -> Dict:
    """Combine metrics into a regime label + position biases."""
    flags = []
    score_gold = 0.0
    score_silver = 0.0
    score_bonds = 0.0
    score_miners = 0.0

    # Real yield logic
    if real_yield is not None:
        if real_yield < 0.5:
            flags.append("REAL_YIELD_LOW")
            score_gold += 0.7
            score_silver += 0.5
            score_miners += 0.6
        elif real_yield < 1.2:
            flags.append("REAL_YIELD_MODERATE")
            score_gold += 0.3
            score_silver += 0.2
        elif real_yield > 2.5:
            flags.append("REAL_YIELD_HIGH")
            score_gold -= 0.6
            score_silver -= 0.4

    # Yield curve
    if yield_curve is not None:
        if yield_curve < 0:
            flags.append("CURVE_INVERTED")
            score_bonds += 0.6  # Recession bid for bonds
            score_gold += 0.4
        elif yield_curve > 1.5:
            flags.append("CURVE_STEEP")
            score_bonds -= 0.4  # Re-acceleration bearish for bonds
        elif 0 < yield_curve < 0.5:
            flags.append("CURVE_FLATTENING")
            score_bonds += 0.2

    # Gold/Silver ratio
    if gold_silver is not None:
        if gold_silver > 90:
            flags.append("GOLD_SILVER_EXTREME_HIGH")
            score_silver += 0.7  # Mean reversion — silver underperformed
            score_gold -= 0.2
        elif gold_silver > 80:
            flags.append("GOLD_SILVER_HIGH_RISK_OFF")
            score_gold += 0.4
            score_silver += 0.3  # eventual catch up
        elif gold_silver < 60:
            flags.append("GOLD_SILVER_LOW_RISK_ON")
            score_silver -= 0.3
        elif gold_silver < 50:
            flags.append("GOLD_SILVER_EXTREME_LOW")
            score_silver -= 0.6

    # TLT/GLD ratio (relative inflation hedge vs flight to quality)
    if tlt_gld is not None:
        # Note: ratio reading is contextual, log-based interpretation
        pass  # Used for color signal only

    # DXY-Gold correlation
    if dxy_gold_corr is not None:
        if dxy_gold_corr < -0.5:
            flags.append("DXY_GOLD_DECORRELATED_NORMAL")  # classic inverse
            # No bias change — it's the baseline regime
        elif dxy_gold_corr > 0.3:
            flags.append("DXY_GOLD_CORRELATED_RARE")  # both rising = monetary panic
            score_gold += 0.5
            score_silver += 0.3

    # Credit spread
    if credit_spread is not None:
        if credit_spread < -0.02:  # HYG -2% relative to LQD
            flags.append("CREDIT_STRESS")
            score_bonds += 0.5
            score_gold += 0.3
            score_silver -= 0.2
        elif credit_spread > 0.02:
            flags.append("CREDIT_EUPHORIA")
            score_bonds -= 0.3

    # Final regime label
    if "CREDIT_STRESS" in flags or "CURVE_INVERTED" in flags:
        regime = "RISK_OFF_BONDS_BID"
    elif "REAL_YIELD_LOW" in flags and "GOLD_SILVER_HIGH_RISK_OFF" in flags:
        regime = "STAGFLATION_GOLD_BULL"
    elif "REAL_YIELD_HIGH" in flags:
        regime = "TIGHT_FED_GOLD_HEADWIND"
    elif "CURVE_STEEP" in flags:
        regime = "RE_ACCELERATION"
    else:
        regime = "NEUTRAL"

    # Position biases (-1 to +1)
    def _bias_label(score: float) -> str:
        if score >= 0.5:
            return "STRONG_LONG"
        elif score >= 0.2:
            return "LONG"
        elif score <= -0.5:
            return "STRONG_SHORT"
        elif score <= -0.2:
            return "SHORT"
        return "NEUTRAL"

    return {
        "regime": regime,
        "flags": flags,
        "metrics": {
            "real_yield": round(real_yield, 3) if real_yield is not None else None,
            "yield_curve_2s10s": round(yield_curve, 3) if yield_curve is not None else None,
            "gold_silver_ratio": round(gold_silver, 1) if gold_silver is not None else None,
            "tlt_gld_ratio": round(tlt_gld, 3) if tlt_gld is not None else None,
            "dxy_gold_corr_60d": round(dxy_gold_corr, 3) if dxy_gold_corr is not None else None,
            "credit_spread_30d": round(credit_spread, 4) if credit_spread is not None else None,
        },
        "position_biases": {
            "gold": {"score": round(score_gold, 2), "bias": _bias_label(score_gold)},
            "silver": {"score": round(score_silver, 2), "bias": _bias_label(score_silver)},
            "bonds": {"score": round(score_bonds, 2), "bias": _bias_label(score_bonds)},
            "miners": {"score": round(score_miners, 2), "bias": _bias_label(score_miners)},
        },
        "ticker_biases": _build_ticker_biases(score_gold, score_silver, score_bonds, score_miners),
    }


def _build_ticker_biases(g: float, s: float, b: float, m: float) -> Dict:
    """Map regime scores to specific tickers."""
    return {
        # Gold proxies
        "GLD": g, "GC=F": g, "IAU": g, "PHYS": g,
        # Silver proxies
        "SLV": s, "SI=F": s, "PSLV": s,
        # Gold miners (higher beta to gold)
        "GDX": (g + m) / 2, "GDXJ": (g + m) / 2,
        "NEM": g * 0.7, "AEM": g * 0.7, "GOLD": g * 0.7,
        # Silver miners
        "SIL": (s + m) / 2, "SILJ": (s + m) / 2, "PAAS": s * 0.7, "WPM": s * 0.7,
        # Bonds
        "TLT": b, "IEF": b * 0.8, "SHY": b * 0.5, "TIP": b * 0.7,
        # PM ETF combos
        "DBP": (g + s) / 2,
        # Negative beta — short dollar plays
        "UUP": -g * 0.5,
    }


# ────────────────────────────────────────────────────────────────────────
# Main entry
# ────────────────────────────────────────────────────────────────────────

def run_bonds_xau_regime(prices: Dict, fred: Dict) -> Dict:
    """Compute bonds-XAU regime from FRED + price data."""
    try:
        real_yield = compute_real_yield(fred)
        yield_curve = compute_yield_curve_2s10s(fred)
        gold_silver = compute_gold_silver_ratio(prices)
        tlt_gld = compute_tlt_gld_ratio(prices)
        dxy_gold_corr = compute_dxy_gold_corr(prices, window=60)
        credit_spread = compute_credit_spread(prices)

        result = classify_bonds_xau_regime(
            real_yield, yield_curve, gold_silver, tlt_gld, dxy_gold_corr, credit_spread
        )
        result["ok"] = True
        return result
    except Exception as e:
        logger.warning(f"Bonds-XAU regime failed: {e}")
        return {"ok": False, "regime": "UNKNOWN", "error": str(e), "ticker_biases": {}}
