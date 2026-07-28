"""tools/build_r8_case_reports.py — SNDK/PLTR/SPXC evaluation reports (R8).

Frozen decision dates from R6 case files (SNDK/PLTR) and prereg_r8 (SPXC).
Fetches PIT-eligible daily bars; computes forward MAE/MFE, lead time to +100%,
remaining return. Detection claims: NONE — causal families are DATA_GATED.
Baseline rank reported only when the ticker exists in the cache universe.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

HORIZON_DAYS = 366


def fetch_bars(ticker: str, start: str, end: str) -> pd.Series:
    import yfinance as yf
    df = yf.download(ticker, start=start, end=end, auto_adjust=False, progress=False)
    if df.empty:
        return pd.Series(dtype=float)
    c = df["Adj Close"] if "Adj Close" in df.columns else df["Close"]
    if isinstance(c, pd.DataFrame):
        c = c.iloc[:, 0]
    return c.dropna()


def case_report(ticker: str, decision_dates: list, bars: pd.Series) -> dict:
    out = {"instrument": ticker, "decision_dates": []}
    for dd in decision_dates:
        d0 = pd.Timestamp(dd["date"])
        past = bars[bars.index <= d0]
        if past.empty:
            out["decision_dates"].append({"date": dd["date"], "status": "NO_PRICE_AT_DATE"})
            continue
        p0 = float(past.iloc[-1])
        fwd = bars[bars.index > past.index[-1]].iloc[:HORIZON_DAYS]
        rec = {"date": dd["date"], "rationale": dd.get("rationale", ""), "price_at_date": round(p0, 2)}
        if fwd.empty:
            rec["status"] = "NO_FORWARD_DATA"
        else:
            path = fwd / p0 - 1.0
            cross = path[path >= 1.0]
            rec.update({
                "mae_pct": round(float(path.min()) * 100, 2),
                "mfe_pct": round(float(path.max()) * 100, 2),
                "crossed_100pct": bool(not cross.empty),
                "lead_time_days": int((cross.index[0] - past.index[-1]).days) if not cross.empty else None,
                "remaining_return_pct": round((float(path.max()) - 1.0) * 100, 2) if not cross.empty else None,
                "return_velocity_pct_per_month": round(float(path.max()) * 100 / max(len(fwd) / 21.0, 1), 2),
                "detection_claim": "NONE — causal extreme-winner families DATA_GATED; "
                                   "no rank/projection existed at this date",
                "evidence_available_at_date": dd.get("data_availability", {}),
            })
        out["decision_dates"].append(rec)
    return out


def main():
    prereg = json.loads((ROOT / "data/research/prereg_r8.json").read_text())
    sndk = json.loads((ROOT / "data/bottleneck/case_studies/sndk_pit_case.json").read_text())
    pltr = json.loads((ROOT / "data/bottleneck/case_studies/pltr_pit_case.json").read_text())
    cases = [
        ("SNDK", sndk["decision_dates"], sndk.get("scope_note", "")),
        ("PLTR", pltr["decision_dates"], pltr.get("scope_note", "")),
        ("SPXC", [{"date": d, "rationale": "generic quarter-start (prereg_r8)"}
                  for d in prereg["evaluation_cases"]["spxc_decision_dates"]],
         "SPXC evaluation case added R8; no formula selected from it"),
    ]
    reports = []
    for ticker, dates, scope in cases:
        bars = fetch_bars(ticker, "2023-06-01", "2026-07-29")
        rep = case_report(ticker, dates, bars)
        rep["scope_note"] = scope
        rep["bars_source"] = "yfinance daily Adj Close (PIT-eligible)"
        rep["verdict"] = ("NOT_CAPTURED — no admitted causal family produced a Top-K rank, "
                          "projection, or activation state at the frozen dates. Price outcomes "
                          "reported for audit only.")
        reports.append(rep)
        for r in rep["decision_dates"]:
            print(ticker, r["date"], "| +100%:", r.get("crossed_100pct"),
                  "| lead:", r.get("lead_time_days"), "| MFE:", r.get("mfe_pct"))
    out = {"schema": "warroom.r8_case_reports.v1", "prereg_hash": prereg["frozen_hash"],
           "generated_at": pd.Timestamp.utcnow().isoformat(), "reports": reports}
    (ROOT / "data/research/r8_case_reports.json").write_text(json.dumps(out, indent=1))
    print("-> data/research/r8_case_reports.json")


if __name__ == "__main__":
    main()
