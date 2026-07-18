"""War Room feed doctor: dependency, cache, DNS and endpoint checks.

It never deletes last-known-good data. Run with --warm to request a full refresh and seed caches.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import socket
from pathlib import Path

HERE = Path(__file__).resolve().parent


def dns(host: str) -> dict:
    try:
        return {"ok": True, "address": socket.gethostbyname(host)}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--warm", action="store_true")
    args = parser.parse_args()

    dependencies = {name: importlib.util.find_spec(name) is not None for name in (
        "pandas", "numpy", "requests", "yfinance", "streamlit", "pyarrow"
    )}
    from data.resilient_market_data import read_health, CACHE_ROOT
    before = read_health()
    warm_error = None
    if args.warm:
        try:
            import data_layer
            data_layer.load_all(
                markets=["us", "idx", "crypto", "commodity", "fx"],
                allow_live=True,
                force_refresh=True,
            )
        except Exception as exc:
            warm_error = f"{type(exc).__name__}: {exc}"
    after = read_health()
    report = {
        "dependencies": dependencies,
        "dns": {
            "yahoo": dns("query1.finance.yahoo.com"),
            "binance": dns("api.binance.com"),
            "fred": dns("api.stlouisfed.org"),
            "stooq": dns("stooq.com"),
        },
        "cache_root": str(CACHE_ROOT),
        "cache_exists": CACHE_ROOT.exists(),
        "health_before": before,
        "health_after": after,
        "warm_error": warm_error,
        "interpretation": (
            "Provider DNS may be temporarily unavailable. Existing last-known-good cache remains usable. "
            "A first run with no network and no cache cannot produce real market data."
        ),
    }
    out = HERE / "FEED_DOCTOR_REPORT.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
