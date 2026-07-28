"""build_cache.py — bulk/incremental price cache. THIS is the 'complete but not heavy' answer:
run it periodically (cron / Windows Task Scheduler), NOT on every app load.

    python build_cache.py            # full + incremental update of the whole universe
    python build_cache.py --full     # force full re-download

Writes cache/prices.parquet (MultiIndex columns: ticker x OHLCV) plus cache/lineage.json
(per-ticker source, retrieval time, last bar, state, exact provider errors).

Data contract (R2):
- A failed batch never erases last-known-good data: the new cache is written only when
  its ticker coverage is >= the existing cache coverage, and per-ticker the new frame
  is kept only when it has at least as many bars as the old one.
- No synthetic rows are ever written.
- Progress and exact provider errors are printed and recorded in lineage.json.
"""
from __future__ import annotations
import json
import os
import sys
from datetime import datetime, timezone

import pandas as pd
from parquet_compat import read_parquet_compat
from warroom import data as D

CACHE = os.path.join(os.path.dirname(__file__), "cache")
UNIVERSE = list(dict.fromkeys(D.US_UNIVERSE + D.IDX_UNIVERSE + D.CRYPTO_UNIVERSE + D.FX_UNIVERSE + D.COMMO_UNIVERSE))

MARKET_OF = {}
for _t in D.US_UNIVERSE: MARKET_OF.setdefault(_t, "us")
for _t in D.IDX_UNIVERSE: MARKET_OF.setdefault(_t, "ihsg")
for _t in D.CRYPTO_UNIVERSE: MARKET_OF.setdefault(_t, "crypto")
for _t in D.FX_UNIVERSE: MARKET_OF.setdefault(_t, "fx")
for _t in D.COMMO_UNIVERSE: MARKET_OF.setdefault(_t, "commodities")


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_existing(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        df = read_parquet_compat(path)
        return {t: df[t][["Open", "High", "Low", "Close", "Volume"]].dropna()
                for t in df.columns.get_level_values(0)}
    except Exception as exc:
        print(f"  WARN existing cache unreadable ({type(exc).__name__}: {exc}); keeping it untouched on failure")
        return {}


def build(full=False, days=500, batch=40):
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, "prices.parquet")
    lineage_path = os.path.join(CACHE, "lineage.json")
    existing = {} if full else _load_existing(path)

    import yfinance as yf
    fetched: dict = {}
    errors: list = []
    total = len(UNIVERSE)
    for i in range(0, total, batch):
        chunk = UNIVERSE[i:i + batch]
        markets = sorted({MARKET_OF.get(t, "?") for t in chunk})
        try:
            raw = yf.download(chunk, period=f"{days}d", interval="1d", auto_adjust=False,
                              progress=False, group_by="ticker", threads=True)
            if isinstance(raw.columns, pd.MultiIndex):
                for t in chunk:
                    if t in raw.columns.get_level_values(0):
                        d = raw[t][["Open", "High", "Low", "Close", "Volume"]].dropna()
                        if len(d) > D.MIN_BARS:
                            fetched[t] = d
                        else:
                            errors.append(f"yfinance: insufficient bars for {t} ({len(d)})")
                    else:
                        errors.append(f"yfinance: no data returned for {t}")
            elif chunk:
                d = raw[["Open", "High", "Low", "Close", "Volume"]].dropna()
                if len(d) > D.MIN_BARS:
                    fetched[chunk[0]] = d
                else:
                    errors.append(f"yfinance: insufficient bars for {chunk[0]} ({len(d)})")
        except Exception as exc:
            errors.append(f"yfinance batch {i}-{i + len(chunk)} failed: {type(exc).__name__}: {exc}")
        print(f"  fetched {min(i + batch, total)}/{total}  markets={'+'.join(markets)}  ok={len(fetched)}  errors={len(errors)}")

    if not fetched and not existing:
        print("ERROR: no data fetched and no existing cache — nothing written")
        return 1

    # Merge: never shrink. New frame wins only if it has >= bars of the old one.
    merged = dict(existing)
    for t, d in fetched.items():
        old = existing.get(t)
        if old is None or len(d) >= len(old):
            merged[t] = d
    if existing and len(merged) < len(existing):
        print("ERROR: merged coverage shrank — keeping existing cache untouched")
        return 1

    out = pd.concat(merged, axis=1).sort_index()
    tmp = path + ".tmp"
    out.to_parquet(tmp)
    os.replace(tmp, path)

    retrieved = _utcnow()
    lineage = {
        "schema": "warroom.cache_lineage.v1",
        "built_at": retrieved,
        "provider": "yfinance (period=max-window daily, auto_adjust=False)",
        "tickers": {
            t: {
                "market": MARKET_OF.get(t, "?"),
                "state": D._frame_state(d),
                "source": "yfinance" if t in fetched else "cache (last-known)",
                "last_bar": str(d.index[-1].date()) if len(d) else None,
                "bars": int(len(d)),
                "retrieved_at": retrieved,
            } for t, d in merged.items()
        },
        "errors": errors,
        "universe_size": total,
        "coverage": len(merged),
    }
    with open(lineage_path, "w", encoding="utf-8") as fh:
        json.dump(lineage, fh, indent=2)
    print(f"wrote {path}  ({len(merged)} tickers, {len(out)} rows)")
    print(f"wrote {lineage_path}  ({len(errors)} provider errors recorded)")
    return 0


if __name__ == "__main__":
    sys.exit(build(full="--full" in sys.argv))
