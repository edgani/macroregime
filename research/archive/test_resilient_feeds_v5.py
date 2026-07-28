from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd

from data import resilient_market_data as rmd


def _frame(n=120, start=100.0):
    idx = pd.date_range("2025-01-01", periods=n, freq="B")
    close = start + np.arange(n) * 0.1
    return pd.DataFrame({
        "Open": close - 0.1,
        "High": close + 0.5,
        "Low": close - 0.5,
        "Close": close,
        "Volume": 1_000_000,
    }, index=idx)


def _cleanup(ticker):
    for p in (*rmd._daily_paths(ticker), rmd._quote_path(ticker)):
        try:
            p.unlink()
        except FileNotFoundError:
            pass


def test_lkg_cache_survives_provider_failure():
    ticker = "V5CACHE_TEST"
    _cleanup(ticker)
    rmd._save_frame(ticker, _frame(), "unit_test")
    with patch.object(rmd, "_fetch_yfinance_batch", return_value=({}, ["offline"])), \
         patch.object(rmd, "_provider_fallback", return_value=(None, "", ["offline"])):
        bundle = rmd.load_market_bundle([ticker], market="us", force_refresh=True)
    assert ticker in bundle.frames
    assert bundle.health[ticker].status in {"CACHE_FRESH", "CACHE_STALE"}
    assert len(bundle.frames[ticker]) == 120
    _cleanup(ticker)


def test_missing_ticker_does_not_remove_cached_ticker():
    good, bad = "V5GOOD_TEST", "V5BAD_TEST"
    _cleanup(good); _cleanup(bad)
    rmd._save_frame(good, _frame(), "unit_test")
    with patch.object(rmd, "_fetch_yfinance_batch", return_value=({}, ["offline"])), \
         patch.object(rmd, "_provider_fallback", return_value=(None, "", ["offline"])):
        bundle = rmd.load_market_bundle([good, bad], market="us", force_refresh=True)
    assert good in bundle.frames
    assert bad not in bundle.frames
    assert bundle.missing_count == 1
    _cleanup(good); _cleanup(bad)


def test_quote_cache_fallback():
    ticker = "V5QUOTE_TEST"
    _cleanup(ticker)
    payload = {
        "ticker": ticker, "price": 123.45, "as_of": "2026-07-18T00:00:00Z",
        "fetched_at_utc": "2026-07-18T00:00:00Z", "provider": "unit_test",
        "status": "INTRADAY_FRESH",
    }
    rmd._save_quote_cache(ticker, payload)
    with patch.object(rmd, "_fetch_yfinance_intraday", return_value={}), \
         patch.object(rmd, "_fetch_yahoo_quote", side_effect=RuntimeError("offline")):
        result = rmd.load_quotes([ticker], market="us", force_refresh=True)
    assert result[ticker]["price"] == 123.45
    assert result[ticker]["status"] == "INTRADAY_CACHE_STALE"
    _cleanup(ticker)


def test_attach_quotes_is_local_and_non_destructive():
    desk = {
        "meta": {},
        "markets": {
            "us": {"setups": [{"tk": "AAA", "valid": True}, {"tk": "BBB", "valid": True}]},
            "fx": {"setups": []},
        },
    }
    quotes = {"AAA": {"price": 10.0, "as_of": "2026-07-18T00:00:00Z", "provider": "x", "status": "INTRADAY_FRESH"}}
    with patch.object(rmd, "load_quotes", side_effect=lambda tickers, market, force_refresh=False: quotes if market == "us" else {}):
        out = rmd.attach_quotes_to_desk(desk)
    assert out["markets"]["us"]["setups"][0]["current_quote"] == 10.0
    assert out["markets"]["us"]["setups"][1]["quote_status"] == "MISSING"
    assert out["meta"]["quote_fresh"] == 1


def test_normalizer_never_invents_missing_close():
    frame = pd.DataFrame({"Open": [1.0], "High": [2.0], "Low": [0.5], "Volume": [10]}, index=["2026-01-01"])
    out = rmd._normalize_frame(frame)
    assert out.empty
