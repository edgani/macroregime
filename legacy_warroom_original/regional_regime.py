"""
regional_regime.py — per-region market regime from REAL price action.

Replaces the hardcoded "IHSG Bull / Japan Bull / ..." mock row in Mission Control.
This is a PRICE-PROXY regime (trend + momentum + drawdown), NOT a full macro GIP quad —
labeled honestly. Each region is classified only from its own index/ETF price, so if IHSG
is actually weak, it shows weak. Nothing is hardcoded.

Regime labels (price-trend taxonomy):
  Expansion    — above 200d, +12m, momentum still positive
  Late-cycle   — above 200d but 3m momentum rolling over (decelerating)
  Recovery     — below 200d but +3m (turning up off a low)
  Weakening    — above 200d yet -3m and near-term rolling down
  Bear         — below 200d and -3m (downtrend intact)
  Neutral      — chop / insufficient trend

Color class (matches dashboard css): u=green up, a=amber, i=blue info, d=red down, m=muted.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

# region -> preferred index/ETF tickers (first that resolves wins)
REGION_TICKERS = {
    "US":     ["^GSPC", "SPY"],
    "China":  ["MCHI", "FXI", "^HSI"],
    "Europe": ["VGK", "^STOXX50E", "EZU"],
    "Japan":  ["^N225", "EWJ"],
    "India":  ["^BSESN", "INDA"],
    "IHSG":   ["^JKSE", "EIDO"],
    "Crypto": ["BTC-USD"],
    "Commod": ["DBC", "GSG", "^SPGSCI"],
}


def _series(x):
    if x is None:
        return None
    if isinstance(x, pd.DataFrame):
        for c in ("Close", "close", "Adj Close"):
            if c in x.columns:
                x = x[c]; break
        else:
            x = x.iloc[:, 3] if x.shape[1] > 3 else x.iloc[:, 0]
    s = pd.Series(x).dropna()
    return s if len(s) >= 60 else None


def _classify(s: pd.Series) -> dict:
    s = s.astype(float)
    n = len(s)
    last = float(s.iloc[-1])
    ma200 = float(s.tail(min(200, n)).mean())
    above = last >= ma200
    r12 = last / float(s.iloc[-min(252, n)]) - 1.0
    r3 = last / float(s.iloc[-min(63, n)]) - 1.0
    r1 = last / float(s.iloc[-min(21, n)]) - 1.0  # last-month momentum = deceleration tell

    if above and r3 > 0 and r1 > 0:
        lbl, cls = "Expansion", "u"
    elif above and r3 > 0 and r1 <= 0:
        lbl, cls = "Late-cycle", "a"          # trend up but near-term stalling
    elif above and r3 <= 0:
        lbl, cls = "Weakening", "a"           # above 200d yet 3m negative
    elif (not above) and r3 > 0.02:
        lbl, cls = "Recovery", "i"            # below 200d, turning up
    elif (not above) and r3 <= 0:
        lbl, cls = "Bear", "d"
    else:
        lbl, cls = "Neutral", "m"

    detail = f"12m {r12*100:+.0f}% · 3m {r3*100:+.0f}% · {'>200d' if above else '<200d'}"
    return {"label": lbl, "cls": cls, "detail": detail,
            "r12": round(r12, 4), "r3": round(r3, 4), "above_200d": above}


def regional_regime(price_lookup) -> dict:
    """
    price_lookup: dict {ticker: price_series_or_ohlcv}. We pull each region's preferred
    ticker from it. Returns {region: {label, cls, detail, ...}} for regions we can resolve.
    Regions with no data are omitted (dashboard shows the honest '—' fallback).
    """
    out = {}
    for region, tickers in REGION_TICKERS.items():
        s = None
        used = None
        for t in tickers:
            s = _series(price_lookup.get(t))
            if s is not None:
                used = t; break
        if s is None:
            continue
        r = _classify(s)
        r["ticker"] = used
        out[region] = r
    return out


# regions whose proxy tickers aren't in the default fetch — data_layer can add these
EXTRA_PROXY_TICKERS = ["MCHI", "VGK", "EWJ", "INDA", "EIDO", "DBC",
                       "^GSPC", "^N225", "^BSESN", "^JKSE", "^HSI", "^STOXX50E"]
