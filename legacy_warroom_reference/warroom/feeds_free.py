"""warroom/feeds_free.py — FREE data layer that unlocks the 'needs paid data' engines.

Map of free sources (all no-cost):
  • yfinance      → fundamentals, analyst price targets, earnings estimates, short interest, options
  • FRED          → macro / liquidity (already wired in fred.py)
  • SEC EDGAR     → 13F institutional holdings, filings        (free JSON API; not yet wired)
  • pytrends      → Google Trends search interest (attention)  (free; not yet wired)
  • EIA           → power / grid / energy                      (free API key; not yet wired)
  • StockTwits    → retail sentiment                           (free API; not yet wired)

This module currently implements the yfinance free fundamentals/targets/estimates (the highest-value
unlock: Fair Value + Expectation engines). Everything degrades gracefully — if yfinance is missing or a
fetch fails, callers get None and the app shows 'no fundamental data' instead of breaking.

HONEST: free data is retail-grade — estimates can be stale/missing, 13F is ~45d delayed, Trends is noisy.
It is directionally useful, NOT institutional-grade. And it cannot be fetch-tested in a no-network sandbox;
validate on a live machine.
"""
from __future__ import annotations
import functools


def _yf():
    try:
        import yfinance as yf
        return yf
    except Exception:
        return None


@functools.lru_cache(maxsize=256)
def fundamentals(symbol):
    """Normalized free fundamentals + analyst targets for one symbol (yfinance). None on any failure."""
    yf = _yf()
    if yf is None or not symbol:
        return None
    try:
        t = yf.Ticker(symbol)
        info = {}
        for getter in ("get_info", "info"):
            try:
                v = getattr(t, getter)
                info = (v() if callable(v) else v) or {}
                if info:
                    break
            except Exception:
                continue
        # analyst price targets — newer yfinance exposes .analyst_price_targets (dict)
        tgt = {}
        try:
            apt = getattr(t, "analyst_price_targets", None)
            if isinstance(apt, dict):
                tgt = apt
        except Exception:
            pass
        mean_t = tgt.get("mean") or info.get("targetMeanPrice")
        low_t = tgt.get("low") or info.get("targetLowPrice")
        high_t = tgt.get("high") or info.get("targetHighPrice")
        cur = tgt.get("current") or info.get("currentPrice") or info.get("regularMarketPrice")
        if not (info or mean_t):
            return None
        return {"name": info.get("shortName") or info.get("longName") or symbol, "sector": info.get("sector"),
                "price": cur, "market_cap": info.get("marketCap"),
                "pe": info.get("trailingPE"), "fwd_pe": info.get("forwardPE"), "pb": info.get("priceToBook"),
                "eps": info.get("trailingEps"), "fwd_eps": info.get("forwardEps"),
                "rev_growth": info.get("revenueGrowth"), "earn_growth": info.get("earningsGrowth"),
                "margin": info.get("profitMargins"), "roe": info.get("returnOnEquity"),
                "target_mean": mean_t, "target_low": low_t, "target_high": high_t,
                "short_pct": info.get("shortPercentOfFloat"),
                "rec_mean": info.get("recommendationMean"), "n_analysts": info.get("numberOfAnalystOpinions")}
    except Exception:
        return None


@functools.lru_cache(maxsize=256)
def earnings_surprise(symbol):
    """Last earnings: estimate vs actual + surprise % (yfinance). Powers the Expectation engine. None on failure."""
    yf = _yf()
    if yf is None or not symbol:
        return None
    try:
        t = yf.Ticker(symbol)
        for getter in ("get_earnings_dates", "earnings_dates"):
            try:
                df = getattr(t, getter)
                df = df() if callable(df) else df
            except Exception:
                df = None
            if df is not None and len(df):
                cols = {c.lower(): c for c in df.columns}
                ec = cols.get("eps estimate"); ac = cols.get("reported eps"); sc = cols.get("surprise(%)") or cols.get("surprise(%) ")
                past = df.dropna(subset=[ac]) if ac else df
                if len(past):
                    row = past.iloc[0]
                    est = float(row[ec]) if ec and row.get(ec) == row.get(ec) else None
                    act = float(row[ac]) if ac and row.get(ac) == row.get(ac) else None
                    surp = ((act - est) / abs(est) * 100) if (est and act is not None and est != 0) else None
                    return {"estimate": est, "actual": act, "surprise_pct": round(surp, 1) if surp is not None else None}
        return None
    except Exception:
        return None
