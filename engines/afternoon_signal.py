"""engines/afternoon_signal.py — "Strongest Afternoon" Signal Proxy
Conditions: VIX 12-18, strong charm, decaying straddle, clean structure, low volume.
"""
from datetime import datetime


def analyze_afternoon(ticker, prices, charm_data, vanna_data, vix, gex_data, structure_data):
    """Generate afternoon bias signal."""
    s = prices.get(ticker)
    if s is None or len(s) < 20:
        return {"ok": False, "error": "No price data"}

    try:
        import pandas as pd
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        vol_20 = float(s_clean.tail(20).std())
        mean_20 = float(s_clean.tail(20).mean())
        vol_ratio = vol_20 / mean_20 if mean_20 > 0 else 0
    except Exception:
        return {"ok": False, "error": "Parse failed"}

    # Conditions
    vix_ok = 12 <= vix <= 22
    charm_ok = charm_data.get("ok") and charm_data.get("regime") in ("BUILDING", "FADING")
    charm_strength = abs(charm_data.get("net_charm", 0)) > 1e5 if charm_data.get("ok") else False
    structure_ok = structure_data.get("ok") and structure_data.get("quality") == "CLEAN"
    volume_ok = vol_ratio < 0.03  # low vol environment

    # Time window
    now = datetime.now()
    hour = now.hour + now.minute / 60
    in_window = 13.5 <= hour <= 15.0

    score = 0
    reasons = []
    if vix_ok:
        score += 1
        reasons.append("VIX calm")
    if charm_ok and charm_strength:
        score += 2
        reasons.append("Charm strong")
    if structure_ok:
        score += 1
        reasons.append("Clean structure")
    if volume_ok:
        score += 1
        reasons.append("Low vol env")
    if in_window:
        score += 1
        reasons.append("In window")

    if score >= 4:
        signal = "STRONG"
        confidence = "HIGH"
        color = "#3FB950"
    elif score >= 2:
        signal = "MODERATE"
        confidence = "MEDIUM"
        color = "#D29922"
    else:
        signal = "WEAK"
        confidence = "LOW"
        color = "#8B949E"

    # Direction from charm
    direction = "NEUTRAL"
    if charm_data.get("ok"):
        if charm_data.get("regime") == "BUILDING":
            direction = "LONG"
        elif charm_data.get("regime") == "FADING":
            direction = "SHORT"

    return {
        "ok": True,
        "signal": signal,
        "direction": direction,
        "confidence": confidence,
        "color": color,
        "score": score,
        "max_score": 6,
        "in_window": in_window,
        "window_note": "13:30-15:00 ET" if in_window else f"Now {now.strftime('%H:%M')} — wait for 13:30",
        "reasons": reasons,
        "recommended_structure": "Fly above test level" if direction == "LONG" else "Put spread below test" if direction == "SHORT" else "Iron condor",
        "source": "PROXY",
    }


def analyze_multi(tickers, prices, charm_map, vanna_map, vix, gex_map, structure_map):
    results = {}
    for t in tickers:
        results[t] = analyze_afternoon(
            t, prices,
            charm_map.get(t, {}),
            vanna_map.get(t, {}),
            vix,
            gex_map.get(t, {}),
            structure_map.get(t, {})
        )
    return results
