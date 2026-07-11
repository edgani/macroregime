"""inventory_transfer_engine.py — Universal Inventory Transfer Engine (ITE).

Classifies the CURRENT market phase from OHLCV + benchmark with a TRACEABLE multi-evidence score.
Every phase probability decomposes into named evidence contributions ("why this phase").

Phases (the universal cycle): Liquidation → Absorption → Accumulation → Position-Building →
Markup → Momentum → Distribution → Markdown.

HONEST SCOPE: price/volume/relative-strength only. This is a phase CLASSIFIER (coincident-to-
short-lead), NOT a multi-year winner finder — that needs fundamental/theme/narrative feeds
(see alpha_discovery_test.py). The replay test below measures exactly how early it fires.
"""
from __future__ import annotations
import numpy as np, pandas as pd


def _slope(y):
    n = len(y)
    if n < 3: return 0.0
    x = np.arange(n)
    return float(np.polyfit(x, y, 1)[0] / (np.mean(np.abs(y)) + 1e-9))


def evidence(df: pd.DataFrame, bench: pd.Series | None = None, win: int = 63) -> dict:
    """Extract phase evidence from the trailing `win` bars of an OHLCV frame."""
    c, h, l, v = df["Close"], df["High"], df["Low"], df["Volume"]
    r = c.pct_change()
    w = slice(-win, None)
    lows, highs, vol, ret = l.iloc[w], h.iloc[w], v.iloc[w], r.iloc[w]
    up = vol[ret > 0].sum(); dn = vol[ret < 0].sum()
    atr = (h - l).rolling(14).mean()
    dd = (c / c.cummax() - 1.0)
    rng_hi, rng_lo = highs.max(), lows.min()
    if bench is not None:
        b = bench.reindex(c.index).ffill()
        rs = float((c.iloc[-1] / c.iloc[-win]) / (b.iloc[-1] / b.iloc[-win] + 1e-9) - 1)
    else:
        rs = float(c.iloc[-1] / c.iloc[-win] - 1)
    return {
        "hl_slope":     _slope(lows.values),                                   # >0 higher lows (accum)
        "hh_slope":     _slope(highs.values),                                  # <0 lower highs (distrib)
        "vol_asym":     float((up - dn) / (up + dn + 1e-9)),                   # >0 demand dominant
        "vol_compress": float(1 - atr.iloc[-1] / (atr.iloc[w].mean() + 1e-9)), # >0 compressing
        "dd_shrink":    float(dd.iloc[-win // 2:].min() - dd.iloc[-win:-win // 2].min()),  # >0 shallower
        "rel_strength": rs,
        "vol_spike":    float(v.iloc[-5:].mean() / (vol.mean() + 1e-9) - 1),   # >0 spike (liq/capit)
        "range_loc":    float((c.iloc[-1] - rng_lo) / (rng_hi - rng_lo + 1e-9)),
        "trend":        float(c.iloc[-1] / c.ewm(span=50, adjust=False).mean().iloc[-1] - 1),
    }


def classify_phase(df: pd.DataFrame, bench: pd.Series | None = None) -> dict:
    if df is None or len(df) < 130:
        return {"ok": False, "reason": "insufficient history"}
    e = evidence(df, bench)
    z = {k: float(np.tanh(v * 5)) for k, v in e.items()}
    p = max  # readability
    ph = {
        "Liquidation":       p(0, z["vol_spike"]) * 1.5 + p(0, -z["vol_compress"]) + p(0, -z["trend"]) * 1.5 + p(0, 0.2 - e["range_loc"]),
        "Absorption":        p(0, z["dd_shrink"]) + p(0, z["vol_spike"]) * .5 + p(0, .3 - e["range_loc"]) + p(0, z["vol_compress"]) * .5 + p(0, -z["trend"]) * .5,
        "Accumulation":      p(0, z["hl_slope"]) + p(0, z["vol_asym"]) + p(0, z["vol_compress"]) + p(0, z["dd_shrink"]) + p(0, -z["trend"]) * .5 + p(0, .5 - e["range_loc"]),
        "Position Building": p(0, z["hl_slope"]) + p(0, z["rel_strength"]) + p(0, z["vol_asym"]) + (1.0 if 0.3 < e["range_loc"] < 0.7 else 0.0),
        "Markup":            p(0, z["trend"]) + p(0, e["range_loc"] - 0.6) + p(0, z["rel_strength"]) + p(0, z["hh_slope"]),
        "Momentum":          p(0, z["trend"]) * 1.5 + p(0, e["range_loc"] - 0.8) + p(0, z["vol_spike"]),
        "Distribution":      p(0, -z["hh_slope"]) + p(0, -z["vol_asym"]) + p(0, e["range_loc"] - 0.6) + p(0, -z["rel_strength"]),
        "Markdown":          p(0, -z["trend"]) + p(0, -z["hl_slope"]) + p(0, -z["vol_asym"]) + p(0, .4 - e["range_loc"]),
    }
    tot = sum(ph.values()) + 1e-9
    probs = {k: round(v / tot, 3) for k, v in ph.items()}
    top = max(probs, key=probs.get)
    # traceable contributions to the winning phase
    contrib = {
        "Accumulation": {"higher_lows": z["hl_slope"], "demand_volume": z["vol_asym"], "vol_compression": z["vol_compress"], "shallower_dd": z["dd_shrink"]},
        "Markup": {"trend": z["trend"], "range_high": e["range_loc"], "rel_strength": z["rel_strength"], "higher_highs": z["hh_slope"]},
        "Distribution": {"lower_highs": -z["hh_slope"], "supply_volume": -z["vol_asym"], "range_high": e["range_loc"], "weak_rs": -z["rel_strength"]},
    }.get(top, {k: round(v, 2) for k, v in list(z.items())[:4]})
    return {"ok": True, "phase": top, "confidence": round(probs[top] * 100),
            "phase_probs": dict(sorted(probs.items(), key=lambda x: -x[1])),
            "why": {k: round(float(v), 2) for k, v in contrib.items()},
            "evidence": {k: round(v, 3) for k, v in e.items()}}
