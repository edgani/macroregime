"""intraday_regime_engine.py

Intraday regime update — refreshes regime probability shifts based on
real-time price moves without waiting for a full FRED data refresh.

Logic: if SPY moves -2% while TLT +1% and VIX +15% in a session,
the monthly quad probability distribution shifts toward Q3/Q4 even
before FRED data confirms it.

This gives 4-8 hour early warning on regime moves.
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import pandas as pd

from utils.math_utils import clamp01


@dataclass
class IntradayRegimeUpdate:
    # Intraday moves
    spy_1d: float
    vix_1d: float
    tlt_1d: float
    oil_1d: float
    gold_1d: float
    dxy_1d: float
    hyg_1d: float

    # Derived signals
    risk_on_signal: float       # 0-1
    inflation_pressure: float   # 0-1
    flight_to_safety: float     # 0-1
    credit_stress: float        # 0-1

    # Regime probability update (shift from baseline)
    q1_shift: float             # positive = more likely, negative = less likely
    q2_shift: float
    q3_shift: float
    q4_shift: float

    # Plain language
    intraday_regime: str        # "risk_on" | "risk_off" | "inflationary" | "deflationary" | "neutral"
    signal_strength: str        # "strong" | "moderate" | "weak" | "noise"
    summary: str
    action_note: str            # what this means for open positions


def _safe_1d_ret(prices: Dict[str, pd.Series], ticker: str) -> float:
    """Get 1-day return safely."""
    s = prices.get(ticker)
    if s is None or len(s) < 2:
        return 0.0
    try:
        r = float(s.iloc[-1] / s.iloc[-2] - 1)
        return r if math.isfinite(r) else 0.0
    except Exception:
        return 0.0


def run_intraday_update(
    prices: Dict[str, pd.Series],
    current_quad: str = "Q?",
) -> IntradayRegimeUpdate:
    """
    Compute intraday regime signals from latest price moves.
    Returns update that can modify regime probabilities on intraday basis.
    """
    spy = _safe_1d_ret(prices, "SPY")
    vix_s = prices.get("^VIX")
    vix_1d = 0.0
    if vix_s is not None and len(vix_s) >= 2:
        try:
            vix_1d = float(vix_s.iloc[-1] - vix_s.iloc[-2])  # VIX in points not %
        except Exception:
            pass
    tlt = _safe_1d_ret(prices, "TLT")
    oil = _safe_1d_ret(prices, "CL=F")
    gold = _safe_1d_ret(prices, "GLD") or _safe_1d_ret(prices, "GC=F")
    dxy = _safe_1d_ret(prices, "UUP")
    hyg = _safe_1d_ret(prices, "HYG")
    iwm = _safe_1d_ret(prices, "IWM")
    qqq = _safe_1d_ret(prices, "QQQ")

    # ── Risk-on signal: SPY up, VIX down, HYG up, IWM leading ──────────────
    risk_on = clamp01(
        0.30 * clamp01(0.5 + spy / 0.015)
        + 0.20 * clamp01(0.5 - vix_1d / 2.0)
        + 0.20 * clamp01(0.5 + hyg / 0.008)
        + 0.15 * clamp01(0.5 + (iwm - spy) / 0.008)  # small cap leading
        + 0.15 * clamp01(0.5 - dxy / 0.010)
    )

    # ── Inflation pressure: oil up, gold up, bonds down, USD up ─────────────
    inflation_p = clamp01(
        0.35 * clamp01(0.5 + oil / 0.025)
        + 0.25 * clamp01(0.5 + gold / 0.012)
        + 0.25 * clamp01(0.5 - tlt / 0.010)
        + 0.15 * clamp01(0.5 + dxy / 0.008)
    )

    # ── Flight to safety: TLT up, gold up, VIX spiking, SPY down ───────────
    fts = clamp01(
        0.35 * clamp01(0.5 + tlt / 0.012)
        + 0.25 * clamp01(0.5 + gold / 0.012)
        + 0.25 * clamp01(0.5 + vix_1d / 2.0)
        + 0.15 * clamp01(0.5 - spy / 0.015)
    )

    # ── Credit stress: HYG underperforming, VIX rising, IWM lagging ─────────
    credit_s = clamp01(
        0.40 * clamp01(0.5 - hyg / 0.010)
        + 0.35 * clamp01(0.5 + vix_1d / 2.5)
        + 0.25 * clamp01(0.5 - (iwm - spy) / 0.010)
    )

    # ── Regime probability shifts ────────────────────────────────────────────
    # Q1 (growth↑ inflation↓): risk-on + inflation low + credit calm
    q1_shift = 0.60 * risk_on - 0.40 * inflation_p - 0.20 * credit_s

    # Q2 (growth↑ inflation↑): risk-on + inflation rising + commodities
    q2_shift = 0.40 * risk_on + 0.50 * inflation_p - 0.10 * credit_s

    # Q3 (growth↓ inflation↑): inflation + credit stress + risk-off
    q3_shift = -0.20 * risk_on + 0.40 * inflation_p + 0.40 * credit_s

    # Q4 (growth↓ inflation↓): flight to safety + credit stress + deflation
    q4_shift = -0.30 * risk_on - 0.20 * inflation_p + 0.25 * fts + 0.25 * credit_s

    # Normalize shifts to -1..+1 range
    max_shift = max(abs(q1_shift), abs(q2_shift), abs(q3_shift), abs(q4_shift), 0.001)
    scale = 0.30 / max_shift  # max shift ±0.30 probability units
    q1_shift *= scale; q2_shift *= scale
    q3_shift *= scale; q4_shift *= scale

    # ── Classify intraday regime ─────────────────────────────────────────────
    move_mag = max(abs(spy), abs(vix_1d/30), abs(oil), abs(tlt))

    if move_mag < 0.005:
        intraday_regime = "neutral"
        strength = "noise"
    elif risk_on >= 0.65 and inflation_p < 0.45:
        intraday_regime = "risk_on"
        strength = "strong" if move_mag > 0.015 else "moderate"
    elif credit_s >= 0.60 or (fts >= 0.60 and risk_on < 0.40):
        intraday_regime = "risk_off"
        strength = "strong" if credit_s >= 0.70 else "moderate"
    elif inflation_p >= 0.65:
        intraday_regime = "inflationary"
        strength = "strong" if oil > 0.02 else "moderate"
    elif fts >= 0.60 and inflation_p < 0.40:
        intraday_regime = "deflationary"
        strength = "moderate"
    else:
        intraday_regime = "neutral"
        strength = "weak"

    # ── Plain language ────────────────────────────────────────────────────────
    regime_labels = {
        "risk_on": "Risk-on tape",
        "risk_off": "Risk-off / defensive",
        "inflationary": "Inflationary impulse",
        "deflationary": "Deflationary / flight to safety",
        "neutral": "Neutral / noise",
    }
    summary = f"{regime_labels.get(intraday_regime, 'Neutral')} ({strength}). "
    if abs(spy) > 0.005:
        summary += f"SPY {spy:+.1%}. "
    if abs(oil) > 0.010:
        summary += f"Oil {oil:+.1%}. "
    if vix_1d > 1.0:
        summary += f"VIX +{vix_1d:.1f}pts (stress). "
    elif vix_1d < -1.0:
        summary += f"VIX {vix_1d:.1f}pts (calm). "

    # ── Action note for open positions ────────────────────────────────────────
    action_note = ""
    if intraday_regime == "risk_off" and strength == "strong":
        action_note = "⚠️ Strong risk-off tape — review stops on long positions"
    elif intraday_regime == "risk_on" and strength == "strong" and current_quad in ("Q1","Q2"):
        action_note = "✅ Risk-on confirms regime — longs working, don't chase"
    elif intraday_regime == "inflationary" and current_quad == "Q3":
        action_note = "⚡ Inflation impulse confirms Q3 — energy/gold working"
    elif credit_s >= 0.65:
        action_note = "🚨 Credit stress — reduce position risk, widen stops"
    else:
        action_note = "Monitor — no urgent action from intraday signal"

    return IntradayRegimeUpdate(
        spy_1d=spy, vix_1d=vix_1d, tlt_1d=tlt,
        oil_1d=oil, gold_1d=gold, dxy_1d=dxy, hyg_1d=hyg,
        risk_on_signal=round(risk_on, 3),
        inflation_pressure=round(inflation_p, 3),
        flight_to_safety=round(fts, 3),
        credit_stress=round(credit_s, 3),
        q1_shift=round(q1_shift, 4),
        q2_shift=round(q2_shift, 4),
        q3_shift=round(q3_shift, 4),
        q4_shift=round(q4_shift, 4),
        intraday_regime=intraday_regime,
        signal_strength=strength,
        summary=summary.strip(),
        action_note=action_note,
    )
