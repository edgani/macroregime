"""regime_multitf.py — Multi-timeframe regime (structural / monthly / weekly / daily) + posture.

structural + monthly come from v40's GIPEngine (Hedgeye GIP quad). weekly + daily are short-window
growth/inflation momentum from price proxies. The POSTURE (aggressive vs defensive) comes from how
the timeframes align — so you get flexibility on which tickers surface and how you lean.

Quad: growth × inflation → Q1 Goldilocks (G+/I-), Q2 Reflation (G+/I+), Q3 Stagflation (G-/I+),
Q4 Deflation (G-/I-). HONEST: monthly quad weights in gip_engine are hand-tuned (overfit flag in
config) — treat short-tf as coincident tape, structural as the anchor.
"""
from __future__ import annotations
import numpy as np, pandas as pd

_NAME = {"Q1": "Goldilocks", "Q2": "Reflation", "Q3": "Stagflation", "Q4": "Deflation"}
_RISK_ON = {"Q1", "Q2"}


def _coerce(x):
    if isinstance(x, pd.DataFrame):
        for c in ("Close","close"):
            if c in x.columns: return x[c]
        return x.iloc[:, 3] if x.shape[1] > 3 else x.iloc[:, 0]
    return x

def _ret(s, n):
    s = pd.Series(_coerce(s)).dropna() if s is not None else None
    if s is None or len(s) <= n: return 0.0
    return float(s.iloc[-1] / s.iloc[-n - 1] - 1)


def _pick(prices, *keys):
    for k in keys:
        v = _coerce(prices.get(k))
        if v is not None and len(pd.Series(v).dropna()) > 5: return v
    return None


def _quad(g, i):
    if g >= 0 and i < 0: return "Q1"
    if g >= 0 and i >= 0: return "Q2"
    if g < 0 and i >= 0: return "Q3"
    return "Q4"


def _short_tf(prices, n):
    spy = _pick(prices, "SPY", "^GSPC"); xli = _pick(prices, "XLI")
    oil = _pick(prices, "CL=F", "USO", "BZ=F"); gold = _pick(prices, "GC=F", "GLD")
    dxy = _pick(prices, "DX-Y.NYB", "UUP", "DXY"); copper = _pick(prices, "HG=F")
    g = 0.7 * _ret(spy, n) + 0.3 * _ret(xli, n)
    i = 0.4 * _ret(oil, n) + 0.3 * _ret(copper, n) + 0.2 * _ret(gold, n) - 0.3 * _ret(dxy, n)
    return {"quad": _quad(g, i), "name": _NAME[_quad(g, i)], "g": round(g, 4), "i": round(i, 4)}


def multi_timeframe_regime(fred, prices):
    out = {"structural": None, "monthly": None, "weekly": None, "daily": None}
    try:
        from engines.gip_engine import GIPEngine
        gip = GIPEngine().run(fred or {}, prices or {})
        out["structural"] = {"quad": gip.structural_quad, "name": _NAME.get(gip.structural_quad, "?"),
                             "conf": round(float(gip.structural_conf), 2),
                             "probs": {k: round(v, 2) for k, v in gip.structural_probs.items()}}
        out["monthly"] = {"quad": gip.monthly_quad, "name": _NAME.get(gip.monthly_quad, "?"),
                          "conf": round(float(gip.monthly_conf), 2),
                          "probs": {k: round(v, 2) for k, v in gip.monthly_probs.items()}}
        out["divergence"] = getattr(gip, "divergence", None)
    except Exception as e:
        out["gip_error"] = str(e)
    out["weekly"] = _short_tf(prices or {}, 5)
    out["daily"] = _short_tf(prices or {}, 2)

    # posture: align structural (anchor) + monthly + weekly + daily
    quads = [out[k]["quad"] for k in ("structural", "monthly", "weekly", "daily") if out.get(k)]
    risk_on = sum(1 for q in quads if q in _RISK_ON)
    struct_on = out.get("structural", {}).get("quad") in _RISK_ON if out.get("structural") else False
    if not quads:
        posture = "unknown"
    elif risk_on == len(quads):
        posture = "AGGRESSIVE (all timeframes risk-on)"
    elif risk_on == 0:
        posture = "DEFENSIVE (all timeframes risk-off)"
    elif struct_on and risk_on >= len(quads) - 1:
        posture = "AGGRESSIVE-tilt (structural risk-on, minor short-tf caution)"
    elif not struct_on:
        posture = "DEFENSIVE-tilt (structural risk-off; rallies are tactical)"
    else:
        posture = "MIXED — reduce size, wait for alignment"
    out["posture"] = posture
    out["aligned"] = len(set(quads)) == 1
    return out
