"""Regression: Yahoo batch quotes (v7) + fast-cycle TTL reuse.

Batch parsing and TTL reuse are the 429-throttle defenses; a break here means
the collector goes back to ~540 requests/build or refetches every 15 minutes.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import current_context_v101 as CC  # noqa: E402


def test_yahoo_quotes_batch_parses_v7_payload(monkeypatch):
    payload = {
        "quoteResponse": {
            "result": [
                {"symbol": "AAPL", "regularMarketPrice": 250.5, "regularMarketTime": 1785000000,
                 "currency": "USD", "fullExchangeName": "NasdaqGS", "quoteType": "EQUITY", "marketState": "REGULAR"},
                {"symbol": "BBCA.JK", "regularMarketPrice": 9150, "regularMarketTime": 1785000000,
                 "currency": "IDR", "fullExchangeName": "Jakarta", "quoteType": "EQUITY", "marketState": "CLOSED"},
                {"symbol": "BROKEN", "regularMarketPrice": None, "regularMarketTime": None},
            ],
            "error": None,
        }
    }
    monkeypatch.setattr(CC, "get_json", lambda url, timeout=20.0: (payload, {"http_status": 200}))
    records, errors = CC.yahoo_quotes_batch(["AAPL", "BBCA.JK", "BROKEN"])
    assert records["AAPL"]["price"] == 250.5
    assert records["AAPL"]["provider"] == "YAHOO_QUOTE_BATCH"
    assert records["BBCA.JK"]["currency"] == "IDR"
    assert "BROKEN" not in records
    assert not errors


def test_collect_quotes_fast_reuses_fresh_entries(monkeypatch, tmp_path):
    fresh_ts = CC.iso(CC.now())
    previous = {
        "markets": {m: {} for m in CC.MARKETS},
    }
    previous["markets"]["us"]["AAA"] = {
        "instrument": "AAA", "provider_symbol": "AAA", "price": 10.0, "currency": "USD",
        "provider_timestamp": fresh_ts, "received_at": fresh_ts,
        "validation": "VALID_CURRENT_REFERENCE", "capital_eligible": False,
    }
    out = tmp_path / "quotes.json"
    previous["manifest_hash"] = CC.digest({k: v for k, v in previous.items() if k != "manifest_hash"})
    CC.atomic_json(out, previous)

    monkeypatch.setattr(CC, "prioritized_universe", lambda max_symbols=None: {
        "us": [{"instrument": "AAA", "provider_symbol": "AAA", "provider": "YAHOO"}],
        "idx": [], "crypto": [], "commodity": [], "fx": [],
    })

    def _boom(symbols, **kw):
        raise AssertionError("network must not be touched when TTL reuse applies")

    monkeypatch.setattr(CC, "yahoo_quotes_batch", _boom)
    result = CC.collect_quotes(output=out, fast=True)
    assert result["markets"]["us"]["AAA"]["price"] == 10.0
    assert result["markets"]["us"]["AAA"]["validation"] == "VALID_CURRENT_REFERENCE"


def test_collect_macro_skips_when_manifest_fresh(monkeypatch, tmp_path):
    out = tmp_path / "macro.json"
    payload = {
        "generated_at": CC.iso(CC.now()),
        "series": {"DFF": {"value": 3.63}}, "series_count": 1,
    }
    payload["manifest_hash"] = CC.digest({k: v for k, v in payload.items() if k != "manifest_hash"})
    CC.atomic_json(out, payload)
    monkeypatch.setattr(CC, "_fred_series", lambda sid: (_ for _ in ()).throw(AssertionError("no network")))
    result = CC.collect_macro(output=out)
    assert result["series"]["DFF"]["value"] == 3.63
