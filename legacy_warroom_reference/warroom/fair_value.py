"""warroom/fair_value.py — Fair Value engine (base/bull/bear) on FREE data. Fills the Company Page spec.

base = analyst mean target (cross-checked vs forward-EPS × current multiple); bull = high target;
bear = low target. Upside = base/price − 1. All from yfinance free fundamentals/targets.

HONEST: a multiple/target model, NOT a full DCF. Analyst targets are a consensus shorthand and lag; the
forward-multiple cross-check is crude. Treat base/bull/bear as a sanity band, not a precise valuation.
"""
from __future__ import annotations
from warroom import feeds_free as FF


def for_symbol(symbol, fund=None):
    f = fund if fund is not None else FF.fundamentals(symbol)
    if not f:
        return None
    price = f.get("price")
    base = f.get("target_mean")
    high = f.get("target_high")
    low = f.get("target_low")
    mult_fv = None
    if f.get("fwd_eps") and f.get("pe") and f["pe"] > 0:
        mult_fv = f["fwd_eps"] * f["pe"]                  # forward EPS at current trailing multiple
    if base is None:
        base = mult_fv
    if base is None:
        return None
    bull = high if high else base * 1.25
    bear = low if low else base * 0.75
    up = round((base / price - 1) * 100) if price else None
    return {"price": price, "market_cap": f.get("market_cap"), "base": round(base, 2), "bull": round(bull, 2),
            "bear": round(bear, 2), "upside_pct": up, "pe": f.get("pe"), "fwd_pe": f.get("fwd_pe"),
            "mult_fv": round(mult_fv, 2) if mult_fv else None, "n_analysts": f.get("n_analysts"),
            "method": "analyst targets + fwd-EPS×multiple cross-check"}


def for_names(symbols, limit=8):
    """Bounded fair-value fetch for the top names (avoids rate limits). Returns {symbol: fv}."""
    out = {}
    for s in list(symbols)[:limit]:
        try:
            fv = for_symbol(s)
            if fv:
                out[s] = fv
        except Exception:
            continue
    return out
