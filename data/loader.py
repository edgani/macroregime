"""data/loader.py — resilient real-data adapter (v5).

Backwards-compatible public functions:
* load_prices(tickers, ...)
* load_ohlcv(tickers, ...)
* load_market(tickers, market, ...)

No synthetic output is returned. Failed providers fall back to persistent last-known-good cache.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd

from data.resilient_market_data import MarketBundle, load_market_bundle

_MEMO: dict[tuple, MarketBundle] = {}


def _infer_market(tickers: Iterable[str]) -> str:
    tickers = list(tickers or [])
    if not tickers:
        return "us"
    if all(str(t).endswith("-USD") for t in tickers):
        return "crypto"
    if all(str(t).endswith(".JK") or str(t).startswith("^JK") for t in tickers):
        return "idx"
    if any(str(t).endswith("=X") or str(t) == "DX-Y.NYB" for t in tickers):
        return "fx"
    if any(str(t).endswith("=F") for t in tickers):
        return "commodity"
    return "us"


def load_market(tickers, market=None, days=756, force_refresh=False) -> MarketBundle:
    tickers = tuple(dict.fromkeys(tickers or []))
    market = market or _infer_market(tickers)
    key = (market, tickers, int(days), bool(force_refresh))
    if key not in _MEMO:
        _MEMO[key] = load_market_bundle(tickers, market=market, days=days, force_refresh=force_refresh)
    return _MEMO[key]


def clear_memory_cache():
    _MEMO.clear()


def load_prices(tickers, days=756, max_age_hours=12.0, progress_cb=None, market=None, force_refresh=False):
    bundle = load_market(tickers, market=market, days=days, force_refresh=force_refresh)
    return {ticker: frame["Close"].dropna() for ticker, frame in bundle.frames.items() if "Close" in frame}


def load_ohlcv(tickers, days=756, market=None, force_refresh=False):
    bundle = load_market(tickers, market=market, days=days, force_refresh=force_refresh)
    return dict(bundle.frames)
