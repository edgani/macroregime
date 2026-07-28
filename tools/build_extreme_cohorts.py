"""tools/build_extreme_cohorts.py — frozen extreme-winner/loser cohorts (R8 pre-registration).

Cohort definitions are FROZEN before any model testing and never tuned on results:

  winners: +100% / +200% / +300% / +500% within 24 months (rolling, close-to-close)
  losers:  -50% / -70% within 12 months (rolling peak-to-trough)

Computed over the price-fed sleeve from cache/prices.parquet (682 trading days).
SURVIVORSHIP CAVEAT (registered): the sleeve is the current listed universe —
delisted names are absent, so loser cohorts are under-counted and winner recall
is biased up. Full survivor-safe cohorts require the licensed CRSP gap (R5).
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "cohorts"
OUT.mkdir(parents=True, exist_ok=True)

FROZEN_SPEC = {
    "schema": "warroom.extreme_cohorts.v1",
    "frozen_at": "2026-07-28",
    "rule": "thresholds and horizons frozen BEFORE any selector testing; changing them requires a new pre-registration",
    "winner_thresholds_pct": [100, 200, 300, 500],
    "winner_horizon_months": 24,
    "loser_thresholds_pct": [-50, -70],
    "loser_horizon_months": 12,
    "survivorship_caveat": "current-universe sleeve only; delisted absent (CRSP gap registered in data/coverage/gap_registry.json)",
}

TRADING_DAYS_MONTH = 21


def build(prices: pd.DataFrame) -> dict:
    winners = {t: [] for t in FROZEN_SPEC["winner_thresholds_pct"]}
    losers = {t: [] for t in FROZEN_SPEC["loser_thresholds_pct"]}
    w_h = FROZEN_SPEC["winner_horizon_months"] * TRADING_DAYS_MONTH
    l_h = FROZEN_SPEC["loser_horizon_months"] * TRADING_DAYS_MONTH

    # prices.parquet is wide MultiIndex (ticker, OHLCV) — reduce to Close-only panel
    if isinstance(prices.columns, pd.MultiIndex):
        closes = prices.xs("Close", level=-1, axis=1)
    else:
        closes = prices
    closes = closes.dropna(axis=1, how="all")
    # never divide by non-positive prices; drop columns with bad (<=0) prints, tolerate NaN gaps
    closes = closes.loc[:, (closes.dropna() > 0).all(axis=0)]

    for col in closes.columns:
        s = closes[col].dropna()
        if len(s) < 60:
            continue
        v = s.values
        for thr in FROZEN_SPEC["winner_thresholds_pct"]:
            hit = False
            for i in range(len(v)):
                window = v[i + 1: i + 1 + w_h]
                if len(window) and np.isfinite(window).all() and (window / v[i] - 1).max() * 100 >= thr:
                    hit = True
                    break
            if hit:
                winners[thr].append(col)
        for thr in FROZEN_SPEC["loser_thresholds_pct"]:
            hit = False
            for i in range(len(v)):
                window = v[i + 1: i + 1 + l_h]
                if len(window) and np.isfinite(window).all() and (window / v[i] - 1).min() * 100 <= thr:
                    hit = True
                    break
            if hit:
                losers[thr].append(col)
    return {"winners": winners, "losers": losers, "evaluated": len(closes.columns)}


def main():
    prices = pd.read_parquet(ROOT / "cache" / "prices.parquet")
    cohorts = build(prices)
    doc = dict(FROZEN_SPEC)
    doc["built_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    doc["universe_size"] = cohorts["evaluated"]
    doc["price_range"] = [str(prices.index[0].date()), str(prices.index[-1].date())]
    doc["cohorts"] = {
        "winners": {f"+{t}%": {"count": len(m), "members": sorted(m)}
                    for t, m in cohorts["winners"].items()},
        "losers": {f"{t}%": {"count": len(m), "members": sorted(m)}
                   for t, m in cohorts["losers"].items()},
    }
    (OUT / "extreme_cohorts.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
    for side in ("winners", "losers"):
        for k, v in doc["cohorts"][side].items():
            print(f"{side} {k}: {v['count']}")


if __name__ == "__main__":
    main()
