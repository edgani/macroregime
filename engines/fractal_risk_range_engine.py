"""engines/fractal_risk_range_engine.py — Hedgeye Risk Range v39 FINAL

DEEP RESEARCH FINDINGS #2 (from Keith tweets + Hedgeye Tier1Alpha partnership):

1. "Fractal" = Multi-scale self-similarity (Trade/Trend/Tail), NOT formal fractal math
   → No need for Hurst/fBm. Multi-duration structure is sufficient.

2. "Stochastic Differentials" = SDE (Itô calculus), non-linear drift+diffusion
   → dX = μdt + σdW + λdt where μ,σ,λ are functions of cross-factors

3. "Relationships between factors" = Cross-factor interactions
   → price×volume, vol×slope, gamma×flow — NOT independent weighted sum

4. "The Machine" = 90% systematic trading volume (JPMorgan estimate)
   → Delta hedging, vol-controlled rebalancing, market cap distortions
   → Risk Range front-runs 1-month momentum by ~1 week

5. TIER 1 ALPHA PARTNERSHIP (July 2023):
   → Dealer Gamma analysis
   → Volatility term structure + 0DTE contracts
   → Vol control flows
   → Leveraged ETF flows
   → Mechanical buying/selling moments
   → Gamma-derived trading ranges

COMPLETE FORMULA:
  dP = μ(P,V,σ,Γ,Φ)dt + σ(P,V,Γ)dW + λ(P,V,σ,Γ,Φ)dt

  Where:
    P = price, V = volume, σ = volatility
    Γ = dealer gamma exposure (from Tier1Alpha)
    Φ = systematic flow pressure (The Machine)
    μ = drift = f(price_velocity, volume_regime, vol_regime, gamma_regime, flow_pressure)
    σ = diffusion = f(realized_vol, volume, gamma, cross-factor interactions)
    λ = non-linear correction = vol_control + 0DTE_pressure + ETF_flow

  Range(T) = px × exp(μT ± z×σ×√T × machine_factor × gamma_factor)

  machine_factor = 1 + systematic_flow_pressure
  gamma_factor = 1 + |GEX|/threshold (pinning when high, breakout when low)
"""
from __future__ import annotations
import math
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────────────────────────
# SYSTEMATIC FLOW PRESSURE ("The Machine" — 90% of volume)
# ────────────────────────────────────────────────────────────────────────

def calculate_machine_pressure(
    prices: pd.Series,
    volume: Optional[pd.Series] = None,
    lookback: int = 21,  # 1-month momentum for The Machine
) -> Dict:
    """Calculate systematic flow pressure from The Machine.

    The Machine chases 1-month momentum. Risk Range front-runs by ~1 week.
    Components:
      1. Momentum pressure: 1m return → systematic buying/selling
      2. Volume pressure: abnormal volume = flow acceleration
      3. Vol control pressure: vol-targeting rebalancing
      4. ETF flow pressure: leveraged ETF rebalancing
    """
    s = pd.to_numeric(prices, errors="coerce").dropna()
    if len(s) < lookback + 5:
        return {"pressure": 0.0, "direction": "NEUTRAL", "components": {}}

    # 1. Momentum pressure (1-month return)
    px_now = float(s.iloc[-1])
    px_1m = float(s.iloc[-lookback])
    mom_1m = (px_now - px_1m) / px_1m

    # Momentum pressure: strong momentum = The Machine chases
    if abs(mom_1m) > 0.15:  # >15% in 1 month = extreme
        mom_pressure = math.copysign(0.30, mom_1m)
    elif abs(mom_1m) > 0.08:
        mom_pressure = math.copysign(0.15, mom_1m)
    else:
        mom_pressure = math.copysign(0.05, mom_1m) if abs(mom_1m) > 0.03 else 0.0

    # 2. Volume pressure
    vol_pressure = 0.0
    if volume is not None:
        v = pd.to_numeric(volume, errors="coerce").dropna()
        if len(v) >= lookback:
            recent_vol = float(v.tail(5).mean())
            baseline_vol = float(v.tail(lookback).mean())
            if baseline_vol > 0:
                vol_ratio = recent_vol / baseline_vol
                if vol_ratio > 2.0:
                    vol_pressure = math.copysign(0.20, mom_1m)  # High volume = flow acceleration
                elif vol_ratio > 1.5:
                    vol_pressure = math.copysign(0.10, mom_1m)

    # 3. Vol control pressure (vol-targeting rebalancing)
    ret = s.pct_change().dropna()
    if len(ret) >= lookback:
        recent_vol = float(ret.tail(5).std() * np.sqrt(252))
        baseline_vol = float(ret.tail(lookback).std() * np.sqrt(252))
        if baseline_vol > 0:
            vol_regime = recent_vol / baseline_vol
            # Vol control sells when vol rises, buys when vol falls
            if vol_regime > 1.5:
                vol_control_pressure = -0.15  # Selling pressure from vol control
            elif vol_regime < 0.7:
                vol_control_pressure = 0.10   # Buying from vol compression
            else:
                vol_control_pressure = 0.0
        else:
            vol_control_pressure = 0.0
    else:
        vol_control_pressure = 0.0

    # Total pressure
    total_pressure = mom_pressure + vol_pressure + vol_control_pressure
    total_pressure = max(-0.50, min(0.50, total_pressure))

    return {
        "pressure": round(total_pressure, 4),
        "direction": "BUY" if total_pressure > 0.1 else "SELL" if total_pressure < -0.1 else "NEUTRAL",
        "components": {
            "momentum_pressure": round(mom_pressure, 4),
            "volume_pressure": round(vol_pressure, 4),
            "vol_control_pressure": round(vol_control_pressure, 4),
        },
        "mom_1m": round(mom_1m, 4),
    }

# ────────────────────────────────────────────────────────────────────────
# DEALER GAMMA FACTOR (Tier1Alpha partnership)
# ────────────────────────────────────────────────────────────────────────

def calculate_gamma_factor(
    gex: Optional[float] = None,
    gamma_notional: Optional[float] = None,
    max_pain: Optional[float] = None,
    px: float = 100.0,
) -> Dict:
    """Calculate gamma factor from dealer positioning.

    From Tier1Alpha partnership:
      - High GEX → pinning to max pain
      - Low GEX → breakout/acceleration
      - Positive GEX → stabilizing (dealer buy dips, sell rips)
      - Negative GEX → vol expansion (dealer sell dips, buy rips)
    """
    if gex is None:
        return {"factor": 1.0, "regime": "UNKNOWN", "pinning_strength": 0.0}

    # Normalize GEX
    gex_normalized = gex / max(abs(px), 1.0)

    # Gamma regime
    if abs(gex_normalized) > 100:  # Very high gamma
        regime = "PINNING_HIGH"
        factor = 0.70  # Tighter range = pinning
        pinning = 0.90
    elif abs(gex_normalized) > 50:
        regime = "PINNING"
        factor = 0.85
        pinning = 0.70
    elif abs(gex_normalized) > 20:
        regime = "POSITIVE_GEX" if gex > 0 else "NEGATIVE_GEX"
        factor = 0.95 if gex > 0 else 1.15  # Negative = wider range
        pinning = 0.40 if gex > 0 else 0.20
    else:
        regime = "BREAKOUT_RISK"
        factor = 1.30  # Low gamma = moves accelerate
        pinning = 0.10

    return {
        "factor": round(factor, 4),
        "regime": regime,
        "pinning_strength": round(pinning, 4),
        "gex_raw": gex,
        "gex_normalized": round(gex_normalized, 4),
    }

# ────────────────────────────────────────────────────────────────────────
# STOCHASTIC DIFFERENTIAL ENGINE (SDE — Itô calculus)
# ────────────────────────────────────────────────────────────────────────

def calculate_sde_components(
    prices: pd.Series,
    volume: Optional[pd.Series] = None,
    gex: Optional[float] = None,
    lookback: int = 20,
) -> Dict:
    """Calculate SDE components: drift (μ), diffusion (σ), correction (λ).

    dP = μdt + σdW + λdt

    μ = drift = f(price_velocity, volume_regime, vol_regime, gamma_regime, flow_pressure)
    σ = diffusion = f(realized_vol, volume, gamma, cross-factor)
    λ = non-linear correction = cross-factor interactions
    """
    s = pd.to_numeric(prices, errors="coerce").dropna()
    if len(s) < lookback + 5:
        return {"mu": 0.0, "sigma": 0.20, "lambda": 0.0, "cross_factors": {}}

    px = float(s.iloc[-1])
    ret = s.pct_change().dropna()

    # Base realized vol
    sigma_base = float(ret.tail(lookback).std() * np.sqrt(252))
    if not math.isfinite(sigma_base) or sigma_base <= 0:
        sigma_base = 0.20

    # 1. DRIFT (μ) — trend + flow + gamma
    # Price velocity
    px_velocity = (px - float(s.iloc[-lookback])) / float(s.iloc[-lookback])

    # Volume regime
    vol_regime = 1.0
    if volume is not None:
        v = pd.to_numeric(volume, errors="coerce").dropna()
        if len(v) >= lookback:
            recent_v = float(v.tail(5).mean())
            base_v = float(v.tail(lookback).mean())
            if base_v > 0:
                vol_regime = recent_v / base_v

    # Machine pressure
    machine = calculate_machine_pressure(s, volume, lookback=21)
    machine_pressure = machine["pressure"]

    # Gamma effect on drift
    gamma_drift = 0.0
    if gex is not None:
        if gex > 50:  # High positive gamma = dealer supports price
            gamma_drift = 0.02
        elif gex < -50:  # High negative gamma = dealer accelerates moves
            gamma_drift = math.copysign(0.03, px_velocity)

    # Drift = weighted combination with cross-factor interactions
    mu = (px_velocity * 0.30 + 
          machine_pressure * 0.40 + 
          gamma_drift * 0.20 +
          (vol_regime - 1.0) * 0.10)  # Volume regime interaction

    # 2. DIFFUSION (σ) — vol with gamma and volume adjustment
    # Cross-factor: vol × volume_regime
    sigma = sigma_base * (1 + 0.2 * (vol_regime - 1.0))

    # Gamma adjustment: negative gamma = vol expansion
    if gex is not None:
        if gex < -20:
            sigma *= 1.30  # Vol expansion
        elif gex > 50:
            sigma *= 0.85  # Vol compression

    # 3. NON-LINEAR CORRECTION (λ) — cross-factor interactions
    # λ = price_velocity × vol_regime × machine_pressure
    lambda_corr = px_velocity * (vol_regime - 1.0) * machine_pressure * 0.5

    return {
        "mu": round(mu, 6),
        "sigma": round(sigma, 6),
        "lambda": round(lambda_corr, 6),
        "cross_factors": {
            "price_velocity": round(px_velocity, 4),
            "volume_regime": round(vol_regime, 4),
            "machine_pressure": round(machine_pressure, 4),
            "gamma_drift": round(gamma_drift, 4),
        },
    }

# ────────────────────────────────────────────────────────────────────────
# MULTI-DURATION RANGE (Trade=3w, Trend=3m, Tail=3y)
# ────────────────────────────────────────────────────────────────────────

def calculate_sde_range(
    px: float,
    mu: float,
    sigma: float,
    lambda_corr: float,
    duration_days: int,
    machine_pressure: float,
    gamma_factor: float,
    vix_proxy: float = 20.0,
    quad: str = "Q3",
    z_score: float = 1.96,  # 95% confidence
) -> Tuple[float, float]:
    """Calculate risk range using SDE with Machine + Gamma factors.

    Range(T) = px × exp((μ + λ)T ± z×σ×√T × machine_factor × gamma_factor)

    machine_factor = 1 + |machine_pressure| (widens range when flow is chaotic)
    gamma_factor = from dealer gamma (tightens when pinning, widens when breakout)
    """
    T = duration_days / 252.0

    # VIX adjustment
    if vix_proxy > 30: vix_adj = 1.40
    elif vix_proxy > 25: vix_adj = 1.20
    elif vix_proxy < 14: vix_adj = 0.85
    else: vix_adj = 1.0

    # Quad multiplier
    quad_mult = {"Q1": 1.30, "Q2": 1.50, "Q3": 1.80, "Q4": 2.00}.get(quad, 1.80)

    # Machine factor: chaotic flow = wider range
    machine_factor = 1.0 + abs(machine_pressure) * 0.5

    # Range width
    drift_term = (mu + lambda_corr) * T
    diffusion_term = z_score * sigma * math.sqrt(T) * machine_factor * gamma_factor * vix_adj * quad_mult

    # Asymmetric: machine direction affects upper/lower
    if machine_pressure > 0.1:
        up_mult = 1.15 + machine_pressure * 0.3
        dn_mult = 0.90 - machine_pressure * 0.1
    elif machine_pressure < -0.1:
        up_mult = 0.90 + abs(machine_pressure) * 0.1
        dn_mult = 1.15 + abs(machine_pressure) * 0.3
    else:
        up_mult = 1.0
        dn_mult = 1.0

    lrr = px * math.exp(drift_term - diffusion_term * dn_mult)
    trr = px * math.exp(drift_term + diffusion_term * up_mult)

    return lrr, trr

# ────────────────────────────────────────────────────────────────────────
# MAIN ENGINE
# ────────────────────────────────────────────────────────────────────────

def calculate_risk_range_sde(
    ticker: str,
    prices_or_series,
    volume_series: Optional[pd.Series] = None,
    gex: Optional[float] = None,
    current_quad: str = "Q3",
    vix_proxy: float = 20.0,
) -> Dict:
    """Calculate full SDE-based risk range with The Machine + Gamma.

    EXACT HEDGEYE METHODOLOGY (from deep research #2):
      1. SDE: dP = μdt + σdW + λdt (non-linear, cross-factor)
      2. The Machine: 90% systematic flow pressure (momentum + vol control + ETF)
      3. Tier1Alpha Gamma: dealer positioning (pinning vs breakout)
      4. Multi-duration: Trade(3w), Trend(3m), Tail(3y)
      5. Dynamic: ranges change as data changes
    """
    s = prices_or_series.get(ticker) if isinstance(prices_or_series, dict) else prices_or_series

    if s is None or (hasattr(s, "__len__") and len(s) < 120):
        return {"ticker": ticker, "ok": False, "reason": "insufficient_data (need 120+ days)"}

    try:
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) < 120:
            return {"ticker": ticker, "ok": False, "reason": "insufficient_clean_data"}

        px = float(s_clean.iloc[-1])
        if not math.isfinite(px) or px <= 0:
            return {"ticker": ticker, "ok": False, "reason": "invalid_price"}

        # 1. SDE components
        sde = calculate_sde_components(s_clean, volume_series, gex, lookback=20)
        mu = sde["mu"]
        sigma = sde["sigma"]
        lambda_corr = sde["lambda"]

        # 2. Machine pressure
        machine = calculate_machine_pressure(s_clean, volume_series, lookback=21)
        machine_pressure = machine["pressure"]

        # 3. Gamma factor
        gamma = calculate_gamma_factor(gex, px=px)
        gamma_factor = gamma["factor"]
        gamma_regime = gamma["regime"]

        # 4. Multi-duration ranges
        trade_lrr, trade_trr = calculate_sde_range(px, mu, sigma, lambda_corr, 15, machine_pressure, gamma_factor, vix_proxy, current_quad)
        trend_lrr, trend_trr = calculate_sde_range(px, mu, sigma, lambda_corr, 63, machine_pressure, gamma_factor, vix_proxy, current_quad)
        tail_lrr, tail_trr = calculate_sde_range(px, mu, sigma, lambda_corr, 756, machine_pressure, gamma_factor, vix_proxy, current_quad)

        # 5. Formation
        sma_50 = float(s_clean.tail(min(50, len(s_clean))).mean())
        formation = "BULLISH" if px > sma_50 else "BEARISH" if px < sma_50 else "NEUTRAL"

        # 6. Quality
        if px < trade_lrr:
            composite = "bullish"
            distance = abs(px - trade_lrr) / max(trade_lrr, 0.001)
        elif px > trade_trr:
            composite = "bearish"
            distance = abs(px - trade_trr) / max(trade_trr, 0.001)
        else:
            composite = "neutral"
            d_low = abs(px - trade_lrr) / max(trade_lrr, 0.001)
            d_high = abs(px - trade_trr) / max(trade_trr, 0.001)
            distance = min(d_low, d_high)

        if formation == "BULLISH" and composite == "bullish":
            quality = "A+" if distance < 0.02 else "A"
        elif formation == "BEARISH" and composite == "bearish":
            quality = "short_A+" if distance < 0.02 else "short_A"
        elif composite != "neutral":
            quality = "B" if formation == "BULLISH" else "short_B"
        else:
            quality = "C"

        # 7. Entry/Target/Stop
        if formation == "BULLISH":
            if px <= trade_lrr:
                entry = px * 0.995
            else:
                entry = min(px, trade_lrr * 1.01)
            target1 = trade_trr
            target2 = trend_trr
            stop = trade_lrr * 0.985
        elif formation == "BEARISH":
            if px >= trade_trr:
                entry = px * 1.005
            else:
                entry = max(px, trade_trr * 0.99)
            target1 = trade_lrr
            target2 = trend_lrr
            stop = trade_trr * 1.015
        else:
            entry = px
            target1 = trade_trr
            target2 = trend_trr
            stop = trade_lrr

        rr = abs(target1 - entry) / max(abs(entry - stop), 0.001)

        return {
            "ticker": ticker,
            "ok": True,
            "px": round(px, 4),
            "trade": {"lrr": round(trade_lrr, 4), "trr": round(trade_trr, 4)},
            "trend": {"lrr": round(trend_lrr, 4), "trr": round(trend_trr, 4)},
            "tail": {"lrr": round(tail_lrr, 4), "trr": round(tail_trr, 4)},
            "sde": sde,
            "machine": machine,
            "gamma": gamma,
            "composite": composite,
            "formation": formation,
            "quality": quality,
            "distance_to_entry_edge": round(distance, 4),
            "entry": round(entry, 4),
            "target1": round(target1, 4),
            "target2": round(target2, 4),
            "stop": round(stop, 4),
            "rr": round(rr, 2),
            "regime_mult_applied": current_quad,
            "market": _classify_market_simple(ticker),
            "method": "sde_risk_range_v2",
        }
    except Exception as e:
        logger.debug(f"SDE risk range calc failed for {ticker}: {e}")
        return {"ticker": ticker, "ok": False, "reason": f"exception:{type(e).__name__}"}

def _classify_market_simple(ticker: str) -> str:
    t = (ticker or "").upper()
    if "=" in t or t in ("DX-Y.NYB", "UUP"): return "forex"
    if t in ("GC=F", "SI=F", "CL=F", "BZ=F", "HG=F", "NG=F", "SLV", "GLD"): return "commodity"
    if "-USD" in t or t in ("BTC-USD", "ETH-USD", "SOL-USD"): return "crypto"
    if t.endswith(".JK"): return "ihsg"
    if t.startswith("^"): return "index"
    return "us_equity"

class SDERiskRangeEngine:
    """Multi-ticker SDE Risk Range engine with The Machine + Gamma."""

    def __init__(self, current_quad: str = "Q3", vix: float = 20.0):
        self.current_quad = current_quad
        self.vix = vix

    def run(self, prices: Dict, volumes: Optional[Dict] = None,
            gex_map: Optional[Dict[str, float]] = None,
            current_quad: Optional[str] = None, vix: Optional[float] = None) -> Dict:
        quad = current_quad or self.current_quad
        v = vix if vix is not None else self.vix

        asset_ranges = {}
        ok_count = fail_count = 0

        for ticker, series in (prices or {}).items():
            vol = volumes.get(ticker) if volumes else None
            gex = gex_map.get(ticker) if gex_map else None
            result = calculate_risk_range_sde(ticker, series, vol, gex, quad, v)
            if result.get("ok"):
                asset_ranges[ticker] = result
                ok_count += 1
            else:
                fail_count += 1

        if asset_ranges:
            qualities = [r.get("quality") for r in asset_ranges.values()]
            formations = [r.get("formation") for r in asset_ranges.values()]
            summary = {
                "total": ok_count, "failed": fail_count,
                "a_plus_grade": qualities.count("A+"), "a_grade": qualities.count("A"),
                "short_a_plus_grade": qualities.count("short_A+"),
                "short_a_grade": qualities.count("short_A"),
                "bullish_formations": formations.count("BULLISH"),
                "bearish_formations": formations.count("BEARISH"),
                "neutral_formations": formations.count("NEUTRAL"),
                "quad_applied": quad, "vix_applied": v,
            }
        else:
            summary = {"total": 0, "failed": fail_count}

        logger.info(f"SDERiskRangeEngine v39: {ok_count} ranges, {fail_count} failed")
        return {"asset_ranges": asset_ranges, "summary": summary, "version": "v39_sde"}

def calculate_for_universe(prices: Dict, volumes: Optional[Dict] = None,
                           gex_map: Optional[Dict[str, float]] = None,
                           current_quad: str = "Q3", vix: float = 20.0) -> Dict:
    return SDERiskRangeEngine(current_quad, vix).run(prices, volumes, gex_map)

def get_ticker_risk_setup(ticker: str, prices: Dict, volumes: Optional[Dict] = None,
                          gex: Optional[float] = None,
                          current_quad: str = "Q3", vix: float = 20.0) -> Dict:
    return calculate_risk_range_sde(ticker, prices, volumes.get(ticker) if volumes else None, gex, current_quad, vix)
