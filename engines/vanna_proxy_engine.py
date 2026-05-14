"""engines/vanna_proxy_engine.py — Vanna Flow Proxy
Vanna = D-Delta/D-Vol. Proxy from IV skew + VIX sensitivity.
Predicts vol-driven directional flows.
"""
import math
import numpy as np
import pandas as pd


def analyze_vanna(ticker, prices, vix=20.0, dxy_ret=0.0):
    """Calculate Vanna exposure proxy for a ticker."""
    s = prices.get(ticker)
    if s is None or len(s) < 30:
        return {"ok": False, "error": "No price data"}

    try:
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        spot = float(s_clean.iloc[-1])
        sma20 = float(s_clean.tail(20).mean())
        std20 = float(s_clean.tail(20).std())
    except Exception:
        return {"ok": False, "error": "Price parse failed"}

    # Skew proxy: 30d vs 60d realized vol spread
    vol_30 = float(s_clean.tail(30).std())
    vol_60 = float(s_clean.tail(60).std()) if len(s_clean) >= 60 else vol_30
    skew_spread = (vol_30 / sma20 if sma20 > 0 else 0) - (vol_60 / sma20 if sma20 > 0 else 0)

    # VIX regime
    vix_elevated = vix > 25
    vix_normal = 18 <= vix <= 25
    vix_low = vix < 18

    # Vanna signal
    if vix_elevated and skew_spread > 0.005:
        # Rich skew + high VIX = vol likely to drop = vanna buy signal
        signal = "NEVER_SHORT"
        regime = "DOMINANT"
        color = "#3FB950"
        futures_per_1pct = round(std20 * 2.0, 2)
        note = f"Vanna dominant — if VIX drops 1%, dealers buy {futures_per_1pct} futures"
    elif vix_elevated and skew_spread < -0.005:
        signal = "AVOID_LONG"
        regime = "DOMINANT"
        color = "#F85149"
        futures_per_1pct = round(std20 * 2.0, 2)
        note = f"Vanna headwind — if VIX rises 1%, dealers sell {futures_per_1pct} futures"
    elif vix_normal and abs(skew_spread) < 0.005:
        signal = "NEUTRAL"
        regime = "NORMAL"
        color = "#8B949E"
        futures_per_1pct = round(std20 * 1.0, 2)
        note = "Vanna balanced — vol moves have neutral impact"
    else:
        # Default: use DXY correlation as proxy
        if dxy_ret > 0.01:
            signal = "AVOID_LONG" if ticker in ["GLD", "SLV", "GC=F", "SI=F"] else "NEUTRAL"
        elif dxy_ret < -0.01:
            signal = "NEVER_SHORT" if ticker in ["GLD", "SLV", "GC=F", "SI=F"] else "NEUTRAL"
        else:
            signal = "NEUTRAL"
        regime = "NORMAL"
        color = "#8B949E"
        futures_per_1pct = round(std20 * 1.0, 2)
        note = "Vanna mixed — no clear vol-driven bias"

    return {
        "ok": True,
        "signal": signal,
        "regime": regime,
        "color": color,
        "futures_per_1pct_vix": futures_per_1pct,
        "skew_spread": round(skew_spread, 4),
        "vix_regime": "ELEVATED" if vix_elevated else "NORMAL" if vix_normal else "LOW",
        "note": note,
        "source": "PROXY",
    }


def analyze_multi(tickers, prices, vix=20.0, dxy_ret=0.0):
    results = {}
    for t in tickers:
        results[t] = analyze_vanna(t, prices, vix, dxy_ret)
    return results
