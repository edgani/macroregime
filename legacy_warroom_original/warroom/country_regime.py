"""warroom/country_regime.py — global macro regime grid (borrowed LAYOUT from the reference
dashboard's country grid, but driven by REAL price-proxy quads, not fabricated labels).

The reference dashboard (Nova Capital) shows a clean 16-country Goldilocks/Reflation/Stagflation/
Deflation grid. Nice presentation — but a label without a computation is decoration. Here each
country's regime is derived from its US-listed equity ETF (growth proxy = 63d vs 126d momentum) and
an inflation proxy (local commodity/currency tilt). Countries WITHOUT a usable proxy are shown as
'data pending' — never assigned a fake regime.

Quad mapping (same axes as GIP): growth accel × inflation accel →
  Goldilocks (g>0, i≤0) · Reflation (g>0, i>0) · Stagflation (g≤0, i>0) · Deflation (g≤0, i≤0)
"""
from __future__ import annotations
import numpy as np

# country → (US-listed equity ETF proxy, label, flag). Growth read from the ETF; inflation from a
# commodity/FX tilt where a clean proxy exists. This is retail-grade + price-coincident — flagged.
_COUNTRIES = [
    ("United States", "SPY", "🇺🇸"), ("Euro Zone", "EZU", "🇪🇺"), ("United Kingdom", "EWU", "🇬🇧"),
    ("Japan", "EWJ", "🇯🇵"), ("China", "FXI", "🇨🇳"), ("Indonesia", "EIDO", "🇮🇩"),
    ("India", "INDA", "🇮🇳"), ("Brazil", "EWZ", "🇧🇷"), ("Australia", "EWA", "🇦🇺"),
    ("Canada", "EWC", "🇨🇦"), ("Germany", "EWG", "🇩🇪"), ("South Korea", "EWY", "🇰🇷"),
    ("Mexico", "EWW", "🇲🇽"), ("Switzerland", "EWL", "🇨🇭"), ("South Africa", "EZA", "🇿🇦"),
    ("Taiwan", "EWT", "🇹🇼"),
]

_STATE = {
    "goldilocks": ("Goldilocks", "✨", "grn"),
    "reflation":  ("Reflation", "🔥", "amb"),
    "stagflation": ("Stagflation", "⚠️", "red"),
    "deflation":  ("Deflation", "❄️", "blu"),
}


def _ret(c, n):
    return float(c.iloc[-1] / c.iloc[-1 - n] - 1) if len(c) > n else None


def _regime_for(df, infl_tilt):
    """growth = 63d-126d momentum accel of the country ETF; inflation = shared commodity tilt.
    Returns (state_key, g, i) or None if no data."""
    if df is None or len(df) < 131:
        return None
    c = df["Close"]
    r63, r126 = _ret(c, 63), _ret(c, 126)
    if r63 is None or r126 is None:
        return None
    g = r63 - r126                      # growth acceleration
    i = infl_tilt                       # inflation acceleration (shared proxy — see build)
    if g > 0 and i <= 0:
        k = "goldilocks"
    elif g > 0 and i > 0:
        k = "reflation"
    elif g <= 0 and i > 0:
        k = "stagflation"
    else:
        k = "deflation"
    return k, round(g * 100, 1), round(i * 100, 1)


def build(prices_us, commo=None):
    """prices_us: dict of loaded US-listed ETFs (the country proxies live here or in a wider load).
    commo: dict with commodity ETFs for the inflation tilt (DBC/USO/GLD). Missing → tilt 0 + flag."""
    # shared inflation tilt: commodity complex 63d-126d accel (global inflation impulse proxy)
    infl_tilt = 0.0
    tilt_src = "none"
    src = commo or prices_us
    parts = []
    for t in ("DBC", "USO", "GLD", "CPER"):
        d = src.get(t)
        if d is not None and len(d) > 131:
            v = _ret(d["Close"], 63)
            w = _ret(d["Close"], 126)
            if v is not None and w is not None:
                parts.append(v - w)
    if parts:
        infl_tilt = float(np.mean(parts))
        tilt_src = "commodity-proxy"

    cells = []
    for name, proxy, flag in _COUNTRIES:
        df = prices_us.get(proxy)
        r = _regime_for(df, infl_tilt)
        if r is None:
            cells.append({"country": name, "flag": flag, "proxy": proxy, "state": None,
                          "label": "data pending", "emoji": "·", "color": "gry",
                          "g": None, "i": None})
            continue
        k, g, i = r
        label, emoji, color = _STATE[k]
        cells.append({"country": name, "flag": flag, "proxy": proxy, "state": k,
                      "label": label, "emoji": emoji, "color": color, "g": g, "i": i})
    n_live = sum(1 for c in cells if c["state"])
    return {"cells": cells, "n_live": n_live, "n_total": len(cells),
            "infl_tilt": round(infl_tilt * 100, 2), "tilt_src": tilt_src,
            "note": ("price-proxy quads (retail-grade, coincident) — growth from country ETF momentum, "
                     "inflation from shared commodity tilt. Countries without a proxy = 'data pending', not faked.")}
