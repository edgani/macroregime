"""tools/blind_replay.py — SNDK/PLTR blind case-study audit (R6 §2.2 / R8 harness).

Fetches PIT-eligible daily bars (yfinance, auto_adjust=False) and computes the
FACTUAL price-side audit at frozen decision dates:
  price at date, MFE after date, remaining return to post-date peak,
  MAE before the post-date surge, % of total move remaining at detection.

Fundamental activation columns are DATA_GATED (licensed PIT sources missing) —
never fabricated. Detection-quality judgement (Top-K, rank, stage) is produced
by R7/R8 selector tournaments, not by hand.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "bottleneck" / "case_studies"

CASES = {
    "SNDK": {
        "frozen_dates": ["2025-06-30", "2025-09-30", "2025-12-31"],
        "scope": "NAND flash / enterprise SSD (NOT DRAM/HBM)",
        "case_file": "sndk_pit_case.json",
    },
    "PLTR": {
        "frozen_dates": ["2024-01-31", "2024-06-28", "2024-10-31"],
        "scope": "data analytics / government+commercial software",
        "case_file": "pltr_pit_case.json",
    },
}


def fetch(ticker: str):
    import yfinance as yf
    df = yf.download(ticker, period="max", interval="1d", auto_adjust=False, progress=False)
    close = df["Close"]
    if hasattr(close, "columns"):
        close = close.iloc[:, 0]
    return close.dropna()


def audit(ticker: str, close, frozen_dates: list) -> list:
    rows = []
    for d in frozen_dates:
        ts = close.index[close.index <= d]
        if len(ts) == 0:
            rows.append({"date": d, "state": "NO_DATA", "note": "no bar at/before date"})
            continue
        px = float(close.loc[ts[-1]])
        after = close.loc[close.index > ts[-1]]
        if len(after) < 5:
            rows.append({"date": d, "state": "INSUFFICIENT_FORWARD_DATA"})
            continue
        peak = float(after.max())
        peak_date = str(after.idxmax().date())
        remaining_return = (peak / px - 1) * 100
        trough_after = float(after.min())
        mae_after = (trough_after / px - 1) * 100
        # fraction of full historical move still ahead at this date
        full_peak = float(close.max())
        base = float(close.iloc[0])
        total_move = (full_peak / base - 1) * 100 if base > 0 else None
        move_remaining_pct = ((full_peak - px) / (full_peak - base) * 100) if full_peak > base else None
        rows.append({
            "date": d, "state": "PRICE_AUDIT_OK",
            "price_at_date": round(px, 2),
            "post_date_peak": round(peak, 2), "peak_date": peak_date,
            "remaining_return_to_peak_pct": round(remaining_return, 1),
            "mae_after_date_pct": round(mae_after, 1),
            "move_remaining_pct_of_full_history": round(move_remaining_pct, 1) if move_remaining_pct is not None else None,
            "fundamental_activation": "DATA_GATED (PIT filings/consensus/contract prices = LICENSE_REQUIRED)",
            "topk_rank_stage": "PENDING_R7_SELECTOR_TOURNAMENT",
        })
    return rows


def main():
    results = {"schema": "warroom.blind_replay.v1",
               "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "rule": "price-side audit is factual; fundamental activation never fabricated; selector output pending R7 tournament",
               "cases": {}}
    for ticker, spec in CASES.items():
        print(f"[replay] {ticker}: fetching PIT daily bars")
        close = fetch(ticker)
        rows = audit(ticker, close, spec["frozen_dates"])
        results["cases"][ticker] = {"scope": spec["scope"],
                                    "history_range": [str(close.index[0].date()), str(close.index[-1].date())],
                                    "frozen_date_audit": rows}
        for r in rows:
            if r["state"] == "PRICE_AUDIT_OK":
                print(f"  {r['date']}: px={r['price_at_date']} remaining={r['remaining_return_to_peak_pct']}% "
                      f"move_left={r['move_remaining_pct_of_full_history']}% mae={r['mae_after_date_pct']}%")
            else:
                print(f"  {r['date']}: {r['state']}")
    out = OUT / "blind_replay_results.json"
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    print(f"-> {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
