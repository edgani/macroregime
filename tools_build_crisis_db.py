"""Build data/macro_investigation/crisis_episodes.csv from the FRED SP500 daily series.

Crisis definition (reverse-engineering protocol): peak-to-trough drawdown >= 15%.
Columns: episode, peak_date, trough_date, recovery_date, drawdown_pct,
peak_to_trough_days, recovery_days. Recovery_date is empty when the episode
has not recovered within the sample. Output is real FRED data, no synthesis.
"""
from __future__ import annotations

import csv
import io
import urllib.request
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "macro_investigation" / "crisis_episodes.csv"
FRED = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=SP500"
UA = {"User-Agent": "curl/8.5.0 WarRoomOS/10.1"}
THRESHOLD_PCT = 15.0


def load_sp500() -> pd.Series:
    req = urllib.request.Request(FRED, headers=UA)
    with urllib.request.urlopen(req, timeout=30.0) as r:
        raw = r.read()
    frame = pd.read_csv(io.BytesIO(raw))
    frame.columns = ["date", "value"]
    frame["date"] = pd.to_datetime(frame["date"])
    frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
    frame = frame.dropna().set_index("date").sort_index()
    return frame["value"]


def episodes(series: pd.Series, threshold_pct: float = THRESHOLD_PCT) -> list[dict]:
    out: list[dict] = []
    peak_date, peak_val = series.index[0], float(series.iloc[0])
    in_episode = False
    trough_date, trough_val = None, 0.0
    for date, value in series.items():
        value = float(value)
        if not in_episode:
            if value >= peak_val:
                peak_date, peak_val = date, value
            elif value <= peak_val * (1 - threshold_pct / 100):
                in_episode = True
                trough_date, trough_val = date, value
        else:
            if value < trough_val:
                trough_date, trough_val = date, value
            if value >= peak_val:
                out.append({
                    "peak_date": peak_date.date().isoformat(),
                    "trough_date": trough_date.date().isoformat(),
                    "recovery_date": date.date().isoformat(),
                    "drawdown_pct": round((trough_val / peak_val - 1) * 100, 1),
                    "peak_to_trough_days": (trough_date - peak_date).days,
                    "recovery_days": (date - trough_date).days,
                })
                in_episode = False
                peak_date, peak_val = date, value
    if in_episode:
        out.append({
            "peak_date": peak_date.date().isoformat(),
            "trough_date": trough_date.date().isoformat(),
            "recovery_date": "",
            "drawdown_pct": round((trough_val / peak_val - 1) * 100, 1),
            "peak_to_trough_days": (trough_date - peak_date).days,
            "recovery_days": "",
        })
    return out


def main() -> None:
    series = load_sp500()
    rows = episodes(series)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["episode", "peak_date", "trough_date", "recovery_date",
                                                "drawdown_pct", "peak_to_trough_days", "recovery_days"])
        writer.writeheader()
        for i, row in enumerate(rows, 1):
            writer.writerow({"episode": i, **row})
    print(f"episodes: {len(rows)} (threshold {THRESHOLD_PCT}% drawdown, SP500 {series.index[0].date()}..{series.index[-1].date()})")
    for i, row in enumerate(rows, 1):
        print(f"  {i}. {row['peak_date']} -> {row['trough_date']}: {row['drawdown_pct']}%")


if __name__ == "__main__":
    main()
