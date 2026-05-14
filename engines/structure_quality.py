"""engines/structure_quality.py — Options Structure Quality Detector
Detects fishbone patterns (alternating long/short gamma) and messy structures.
"""
import numpy as np


def analyze_structure(ticker, prices, gex_data=None):
    """Analyze options structure quality."""
    s = prices.get(ticker)
    if s is None or len(s) < 50:
        return {"ok": False, "error": "Insufficient data"}

    try:
        import pandas as pd
        s_clean = pd.to_numeric(s, errors="coerce").dropna()

        # Fishbone proxy: sign changes in 20d vs 50d momentum
        r20d = float(s_clean.iloc[-1] / s_clean.iloc[-21] - 1) if len(s_clean) >= 21 else 0
        r50d = float(s_clean.iloc[-1] / s_clean.iloc[-51] - 1) if len(s_clean) >= 51 else r20d

        # Multiple sign changes = messy structure
        signs = []
        for period in [5, 10, 20, 30]:
            if len(s_clean) >= period + 1:
                ret = float(s_clean.iloc[-1] / s_clean.iloc[-(period+1)] - 1)
                signs.append(1 if ret > 0 else -1)

        sign_changes = sum(1 for i in range(1, len(signs)) if signs[i] != signs[i-1])

        # Fishbone: >2 sign changes in short windows
        if sign_changes >= 3:
            quality = "FISHBONE"
            conviction = "SIT_OUT"
            color = "#F85149"
            note = f"{sign_changes} sign changes — alternating gamma, low conviction"
        elif sign_changes == 2:
            quality = "MESSY"
            conviction = "LOW"
            color = "#D29922"
            note = "Mixed structure — reduce size"
        else:
            quality = "CLEAN"
            conviction = "HIGH"
            color = "#3FB950"
            note = "Clean gamma structure — standard sizing"

        # Additional: volatility compression/expansion
        vol_20 = float(s_clean.tail(20).std())
        vol_50 = float(s_clean.tail(50).std()) if len(s_clean) >= 50 else vol_20
        vol_regime = "COMPRESSING" if vol_20 < vol_50 * 0.8 else "EXPANDING" if vol_20 > vol_50 * 1.2 else "STABLE"

        return {
            "ok": True,
            "quality": quality,
            "conviction": conviction,
            "color": color,
            "note": note,
            "sign_changes": sign_changes,
            "vol_regime": vol_regime,
            "source": "PROXY",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def analyze_multi(tickers, prices, gex_data=None):
    results = {}
    for t in tickers:
        results[t] = analyze_structure(t, prices, gex_data)
    return results
