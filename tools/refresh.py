"""tools/refresh.py — one-click balanced refresh (R5 data plane).

Phase 1 (FAST): quick quote snapshot per market, interleaved so all five markets
get an early read; each market publishes immediately — never blocked by slow work.
Phase 2 (SLOW): full cache refresh (build_cache.py) + feeds (build_feeds.py),
runs after fast snapshot is published.

Status + progress + exact provider errors: runtime/refresh_status.json
Fast snapshot: runtime/fast_snapshot.json (per-instrument price, as_of, state)

    .venv/Scripts/python.exe tools/refresh.py            # fast + slow
    .venv/Scripts/python.exe tools/refresh.py --fast-only
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)

MARKETS = ["us", "ihsg", "crypto", "commodities", "fx"]


def _now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Status:
    def __init__(self):
        self.doc = {"schema": "warroom.refresh_status.v1", "started_at": _now(),
                    "phase": "fast", "markets": {}, "errors": [], "updated_at": _now()}
        self.write()

    def write(self):
        self.doc["updated_at"] = _now()
        (RUNTIME / "refresh_status.json").write_text(json.dumps(self.doc, indent=1))

    def market(self, name, **kw):
        self.doc["markets"].setdefault(name, {}).update(kw)
        self.write()

    def error(self, where, msg):
        self.doc["errors"].append({"where": where, "error": msg, "at": _now()})
        self.write()


def _universe(market):
    from warroom import data as D
    return {"us": D.US_UNIVERSE, "ihsg": D.IDX_UNIVERSE, "crypto": D.CRYPTO_UNIVERSE,
            "commodities": D.COMMO_UNIVERSE, "fx": D.FX_UNIVERSE}[market]


def fast_snapshot(status: Status):
    """Interleaved fast quotes: one batch per market per round; publish per market."""
    import yfinance as yf
    snap = {"schema": "warroom.fast_snapshot.v1", "built_at": None, "markets": {}}
    per_market = {}
    for m in MARKETS:
        tickers = _universe(m)
        status.market(m, fast_state="FETCHING", fast_total=len(tickers))
        try:
            d = yf.download(tickers, period="5d", interval="1d", auto_adjust=False,
                            progress=False, group_by="ticker", threads=True)
            quotes = {}
            for t in tickers:
                try:
                    close = d[t]["Close"].dropna()
                    if len(close) == 0:
                        quotes[t] = {"state": "NO_DATA", "price": None, "as_of": None}
                    else:
                        quotes[t] = {"state": "CURRENT", "price": round(float(close.iloc[-1]), 6),
                                     "as_of": str(close.index[-1].date())}
                except Exception:
                    quotes[t] = {"state": "NO_DATA", "price": None, "as_of": None}
            ok = sum(1 for q in quotes.values() if q["state"] == "CURRENT")
            per_market[m] = quotes
            snap["markets"][m] = {"published_at": _now(), "current": ok,
                                  "no_data": len(quotes) - ok, "quotes": quotes}
            status.market(m, fast_state="PUBLISHED", fast_current=ok,
                          fast_no_data=len(quotes) - ok)
        except Exception as e:
            status.error(f"fast.{m}", f"{type(e).__name__}: {e}")
            status.market(m, fast_state="ERROR")
    snap["built_at"] = _now()
    (RUNTIME / "fast_snapshot.json").write_text(json.dumps(snap, indent=1))
    return snap


def slow_refresh(status: Status):
    status.doc["phase"] = "slow"
    status.write()
    py = str(ROOT / ".venv" / "Scripts" / "python.exe")
    for name, script in (("cache", "build_cache.py"), ("feeds", "build_feeds.py")):
        if not (ROOT / script).exists():
            status.error(f"slow.{name}", f"{script} not found")
            continue
        status.market(f"slow_{name}", state="RUNNING")
        t0 = time.time()
        proc = subprocess.run([py, script], cwd=str(ROOT), capture_output=True, text=True)
        if proc.returncode == 0:
            status.market(f"slow_{name}", state="DONE", seconds=round(time.time() - t0, 1))
        else:
            tail = (proc.stderr or proc.stdout or "")[-300:]
            status.error(f"slow.{name}", f"exit {proc.returncode}: {tail}")
            status.market(f"slow_{name}", state="ERROR")
    status.doc["phase"] = "done"
    status.write()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast-only", action="store_true")
    args = ap.parse_args()
    status = Status()
    print("[refresh] phase 1: fast quote snapshot (5 markets, interleaved)")
    snap = fast_snapshot(status)
    for m in MARKETS:
        info = snap["markets"].get(m) or {}
        print(f"  {m}: {info.get('current', 0)} current / {info.get('no_data', 0)} no_data "
              f"published {info.get('published_at', '-')}")
    print(f"[refresh] fast snapshot -> runtime/fast_snapshot.json")
    if not args.fast_only:
        print("[refresh] phase 2: slow cache + feeds (fast snapshot already published)")
        slow_refresh(status)
    print("[refresh] done -> runtime/refresh_status.json")


if __name__ == "__main__":
    main()
