"""options_regime_engine.py

VIX term structure + skew as INDEPENDENT regime confirmation signals.
These are FORWARD-LOOKING (market-implied) whereas FRED data is backward-looking.

What this detects:
- VIX term structure slope: spot vs 3m vs 6m VIX futures
  · Contango (spot < 3m < 6m) = calm, risk-on → confirms Q1/Q2
  · Backwardation (spot > 3m) = fear near-term → confirms Q3/Q4

- VIX level buckets (Hedgeye-style):
  · <15 = Goldilocks → full size, risk-on
  · 15-20 = Normal → standard sizing
  · 20-28 = Elevated → reduce size
  · >28 = Stress → defensive only

- Realized vs Implied Vol spread:
  · IV >> RV = fear premium → market pricing in more risk than realized → potential Q3/Q4
  · IV << RV = complacency → potential reversal signal

- Credit spread (HYG vs LQD) as vol companion:
  · Tightening = credit healthy → risk-on
  · Widening = credit stress → risk-off

Data sources: yfinance (^VIX, ^VIX3M, HYG, LQD, SPY)
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict
import numpy as np

from utils.math_utils import clamp01


@dataclass
class OptionsRegimeSignal:
    # VIX levels
    vix_spot: float
    vix_3m: float
    term_structure_slope: float       # vix_3m - vix_spot; positive = contango (calm)
    term_structure_state: str         # contango | flat | backwardation

    # Regime signal
    vix_bucket: str                   # goldilocks | normal | elevated | stress | crisis
    vix_regime_signal: str            # risk_on | neutral | risk_off | defensive_only
    vix_sizing_cap: float             # 0-1: max position size given VIX

    # Vol premium
    iv_rv_spread: float               # IV - RV: positive = fear premium
    vol_premium_state: str            # cheap | fair | expensive | crisis_premium

    # Credit companion
    hyg_lqd_spread: float             # HYG return - LQD return (1m): positive = credit healthy
    credit_regime: str                # tightening | stable | widening | blowout

    # Combined regime confirmation
    options_regime_confirm: str       # confirms_risk_on | neutral | confirms_risk_off
    regime_alignment_score: float     # 0-1: how strongly options confirm macro regime


class OptionsRegimeEngine:
    """
    Derives regime confirmation signals from options market data.
    Uses prices already loaded in the price_frames dict.
    """

    def run(
        self,
        prices: Dict,                  # {ticker: pd.Series} from price_loader
        macro_quad: str = "Q?",
        vix_last: float = 20.0,
        market_features: Dict | None = None,
    ) -> OptionsRegimeSignal:
        market_features = market_features or {}

        # --- VIX data ---
        vix_spot = float(market_features.get("vix_last", vix_last))

        # Try to get VIX 3m from prices dict; fallback to estimate
        vix3m_series = prices.get("^VIX3M") or prices.get("^VXV") or prices.get("VIX3M")
        if vix3m_series is not None and len(vix3m_series) > 0:
            try:
                vix_3m = float(vix3m_series.iloc[-1])
            except Exception:
                vix_3m = vix_spot * 1.05  # typical contango estimate
        else:
            # Estimate VIX3M from VIX spot + regime context
            if macro_quad in ("Q1", "Q2"):
                vix_3m = vix_spot * 1.04   # mild contango in risk-on
            elif macro_quad == "Q3":
                vix_3m = vix_spot * 0.97   # backwardation in stagflation
            else:
                vix_3m = vix_spot * 1.02   # slight contango in Q4

        term_slope = vix_3m - vix_spot

        if term_slope > 1.5:
            ts_state = "contango"
        elif term_slope < -1.0:
            ts_state = "backwardation"
        else:
            ts_state = "flat"

        # --- VIX bucket ---
        if vix_spot < 15:
            bucket = "goldilocks"
            sizing_cap = 1.00
            vix_signal = "risk_on"
        elif vix_spot < 20:
            bucket = "normal"
            sizing_cap = 0.85
            vix_signal = "neutral"
        elif vix_spot < 28:
            bucket = "elevated"
            sizing_cap = 0.60
            vix_signal = "risk_off"
        elif vix_spot < 40:
            bucket = "stress"
            sizing_cap = 0.35
            vix_signal = "defensive_only"
        else:
            bucket = "crisis"
            sizing_cap = 0.15
            vix_signal = "defensive_only"

        # --- IV vs RV spread (realized vol from SPY) ---
        spy_series = prices.get("SPY")
        rv_20 = 0.0
        if spy_series is not None and len(spy_series) > 22:
            try:
                rets = spy_series.pct_change().dropna()
                rv_20 = float(rets.iloc[-20:].std() * np.sqrt(252) * 100)
            except Exception:
                rv_20 = vix_spot * 0.85  # typical RV < IV relationship
        else:
            rv_20 = vix_spot * 0.85

        iv_rv_spread = vix_spot - rv_20
        if iv_rv_spread > 8:
            vol_prem = "crisis_premium"
        elif iv_rv_spread > 4:
            vol_prem = "expensive"
        elif iv_rv_spread > 0:
            vol_prem = "fair"
        else:
            vol_prem = "cheap"  # RV > IV = realized fear higher than priced

        # --- Credit spread (HYG - LQD relative performance) ---
        hyg_series = prices.get("HYG")
        lqd_series = prices.get("LQD")
        hyg_lqd_spread = 0.0
        if hyg_series is not None and lqd_series is not None:
            try:
                hyg_ret = float(hyg_series.pct_change(21).iloc[-1]) * 100
                lqd_ret = float(lqd_series.pct_change(21).iloc[-1]) * 100
                hyg_lqd_spread = hyg_ret - lqd_ret
            except Exception:
                hyg_lqd_spread = float(market_features.get("credit_health", 0.5) * 2 - 1)
        else:
            hyg_lqd_spread = float(market_features.get("credit_health", 0.5) * 2 - 1)

        if hyg_lqd_spread > 0.5:
            credit_regime = "tightening"    # HY outperforming IG = credit healthy
        elif hyg_lqd_spread > -0.5:
            credit_regime = "stable"
        elif hyg_lqd_spread > -2.0:
            credit_regime = "widening"
        else:
            credit_regime = "blowout"

        # --- Combined options regime confirmation ---
        risk_on_signals = sum([
            1 if ts_state == "contango" else 0,
            1 if vix_signal in ("risk_on", "neutral") else 0,
            1 if vol_prem in ("cheap", "fair") else 0,
            1 if credit_regime in ("tightening", "stable") else 0,
        ])

        if risk_on_signals >= 3:
            confirm = "confirms_risk_on"
            alignment = clamp01(0.50 + 0.15 * risk_on_signals)
        elif risk_on_signals <= 1:
            confirm = "confirms_risk_off"
            alignment = clamp01(0.20 + 0.15 * (4 - risk_on_signals))
        else:
            confirm = "neutral"
            alignment = 0.50

        # Alignment with macro quad
        quad_expected = {
            "Q1": "confirms_risk_on",
            "Q2": "confirms_risk_on",
            "Q3": "confirms_risk_off",
            "Q4": "confirms_risk_off",
        }.get(macro_quad, "neutral")
        if confirm == quad_expected:
            alignment = clamp01(alignment + 0.15)
        elif confirm != "neutral" and confirm != quad_expected:
            alignment = clamp01(alignment - 0.10)  # divergence = uncertainty

        return OptionsRegimeSignal(
            vix_spot=vix_spot,
            vix_3m=vix_3m,
            term_structure_slope=round(term_slope, 2),
            term_structure_state=ts_state,
            vix_bucket=bucket,
            vix_regime_signal=vix_signal,
            vix_sizing_cap=sizing_cap,
            iv_rv_spread=round(iv_rv_spread, 2),
            vol_premium_state=vol_prem,
            hyg_lqd_spread=round(hyg_lqd_spread, 2),
            credit_regime=credit_regime,
            options_regime_confirm=confirm,
            regime_alignment_score=round(alignment, 3),
        )
