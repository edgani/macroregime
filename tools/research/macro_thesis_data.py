"""tools/research/macro_thesis_data.py — primary-data engine for the macro
thesis investigation (R11).

Pulls FRED series (no API key needed via fredgraph.csv) into
data/macro_investigation/ and computes the statistical core of the report:

  1. Fed cut-cycle detection (monthly FEDFUNDS) with first-cut dates
  2. Forward SP500 returns (3/6/12/24m) + 12m max drawdown after each first cut
  3. Slow-cut vs emergency-cut split and outcome comparison
  4. Gold study: crisis-window behavior, gold/equity co-movement
  5. Yield curve inversion/uninversion vs NBER recession dates
  6. Current cross-asset / labor / liquidity / credit snapshot with percentiles

Honesty rules: every number in the report must come from this script's output
(or be labeled Estimate/Speculation). Missing data is reported, never filled.
"""
from __future__ import annotations

import csv
import datetime as dt
import io
import json
import math
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "macro_investigation"
UA = "warroom-macro-research/1.0 (operator investigation)"

SERIES = {
    # rates / curve / policy
    "DFF": "daily", "FEDFUNDS": "monthly", "DGS10": "daily", "DGS2": "daily",
    "T10Y2Y": "daily", "T10Y3M": "daily", "USREC": "monthly",
    # equity / vol / credit
    "SP500": "daily", "NASDAQCOM": "daily", "VIXCLS": "daily",
    "BAMLH0A0HYM2": "daily", "BAMLC0A0CM": "daily",
    # commodities / dollar (gold pulled separately from stooq; FRED's LBMA
    # series GOLDAMGBD228NLBM is discontinued)
    "DCOILWTICO": "daily", "DTWEXBGS": "daily",
    # labor
    "UNRATE": "monthly", "PAYEMS": "monthly", "CIVPART": "monthly",
    "CES0500000003": "monthly", "ICSA": "weekly", "CCSA": "weekly",
    "JTSJOL": "monthly", "JTSQUR": "monthly",
    # inflation
    "CPIAUCSL": "monthly", "CPILFESL": "monthly", "PCEPILFE": "monthly",
    # activity / leading
    "GDP": "quarterly", "INDPRO": "monthly", "USSLIND": "monthly",
    "HOUST": "monthly", "CSUSHPINSA": "monthly",
    # liquidity
    "WALCL": "weekly", "RRPONTSYD": "daily", "WRESBAL": "weekly",
    "M2SL": "monthly", "WTREGEN": "weekly",
    # debt
    "HDTGPDUSQ163N": "quarterly",
}


def fetch(series_id: str, retries: int = 3) -> list[tuple[str, float]]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8")
            rows = []
            for line in csv.DictReader(io.StringIO(text)):
                v = line.get(series_id, "")
                if v not in ("", "."):
                    try:
                        rows.append((line["observation_date"], float(v)))
                    except ValueError:
                        pass
            return rows
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return []


def fetch_stooq(symbol: str, retries: int = 3) -> list[tuple[str, float]]:
    """Stooq daily CSV (no key). Used for gold (XAUUSD) because FRED's LBMA
    series was discontinued."""
    url = f"https://stooq.com/q/d/l/?s={symbol}&i=d"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8")
            rows = []
            for line in csv.DictReader(io.StringIO(text)):
                try:
                    rows.append((line["Date"], float(line["Close"])))
                except (KeyError, ValueError):
                    pass
            return rows
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    return []


def pct_change(a: float, b: float) -> float | None:
    return None if a == 0 else (b / a - 1.0)


def nearest_on_or_after(series: list[tuple[str, float]], date: str) -> tuple[str, float] | None:
    for d, v in series:
        if d >= date:
            return (d, v)
    return None


def forward_stat(series: list[tuple[str, float]], start_date: str, days: int) -> float | None:
    start = nearest_on_or_after(series, start_date)
    if not start:
        return None
    d0, v0 = start
    target = (dt.date.fromisoformat(d0) + dt.timedelta(days=days)).isoformat()
    end = nearest_on_or_after(series, target)
    if not end:
        return None
    return pct_change(v0, end[1])


def max_drawdown(series: list[tuple[str, float]], start_date: str, days: int) -> float | None:
    start = nearest_on_or_after(series, start_date)
    if not start:
        return None
    d0 = dt.date.fromisoformat(start[0])
    window = [(d, v) for d, v in series if d0 <= dt.date.fromisoformat(d) <= d0 + dt.timedelta(days=days)]
    if len(window) < 10:
        return None
    peak = window[0][1]
    mdd = 0.0
    for _, v in window:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return mdd


def detect_first_cuts(ffr_monthly: list[tuple[str, float]], min_hold_months: int = 4, cut_threshold: float = 0.15) -> list[dict]:
    """First month of a cutting cycle: rate drops >= cut_threshold vs prior month
    after >= min_hold_months without a decline, following a restrictive plateau."""
    cuts = []
    since_decline = min_hold_months
    for i in range(1, len(ffr_monthly)):
        d, v = ffr_monthly[i]
        prev = ffr_monthly[i - 1][1]
        delta = v - prev
        if delta <= -cut_threshold and since_decline >= min_hold_months:
            peak = max(x[1] for x in ffr_monthly[max(0, i - 24):i])
            cuts.append({"first_cut_month": d, "rate_before": prev, "rate_after": v,
                         "plateau_peak_24m": peak, "months_since_prev_cut": since_decline})
            since_decline = 0
        elif delta < 0:
            since_decline = 0
        else:
            since_decline += 1
    return cuts


def percentile_of(series: list[tuple[str, float]], value: float, lookback_years: float | None = None) -> float | None:
    vals = [v for _, v in series]
    if lookback_years:
        cutoff = (dt.date.today() - dt.timedelta(days=365.25 * lookback_years)).isoformat()
        vals = [v for d, v in series if d >= cutoff]
    if len(vals) < 20:
        return None
    return round(100.0 * sum(1 for v in vals if v < value) / len(vals), 1)


def yoy(series: list[tuple[str, float]], periods: int = 12) -> float | None:
    if len(series) < periods + 1:
        return None
    return pct_change(series[-1 - periods][1], series[-1][1])


def summarize(xs: list[float]) -> dict:
    xs = sorted(xs)
    n = len(xs)
    return {
        "n": n,
        "mean": round(statistics.fmean(xs), 4),
        "median": round(statistics.median(xs), 4),
        "prob_positive": round(sum(1 for x in xs if x > 0) / n, 4),
        "min": round(xs[0], 4),
        "max": round(xs[-1], 4),
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    data: dict[str, list[tuple[str, float]]] = {}
    failures = {}
    for sid in SERIES:
        try:
            rows = fetch(sid)
            data[sid] = rows
            with (OUT / f"{sid}.csv").open("w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["date", sid])
                w.writerows(rows)
            print(f"{sid}: {len(rows)} rows ({rows[0][0]}..{rows[-1][0]})" if rows else f"{sid}: EMPTY")
            time.sleep(0.4)
        except Exception as exc:
            failures[sid] = f"{type(exc).__name__}: {exc}"
            print(f"{sid}: FAILED {failures[sid]}")

    # gold: FRED discontinued the LBMA series; pull XAUUSD from stooq instead
    try:
        rows = fetch_stooq("xauusd")
        data["GOLD"] = rows
        with (OUT / "GOLD_stooq.csv").open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["date", "XAUUSD"])
            w.writerows(rows)
        print(f"GOLD(stooq): {len(rows)} rows ({rows[0][0]}..{rows[-1][0]})" if rows else "GOLD(stooq): EMPTY")
    except Exception as exc:
        failures["GOLD"] = f"{type(exc).__name__}: {exc}"
        print(f"GOLD(stooq): FAILED {failures['GOLD']}")

    analysis: dict = {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                      "series_failures": failures}

    # --- 1-3. cut cycles + forward returns -----------------------------------
    cuts = detect_first_cuts(data["FEDFUNDS"])
    sp = data["SP500"]
    horizons = {"3m": 91, "6m": 182, "12m": 365, "24m": 730}
    cycle_rows = []
    for c in cuts:
        row = dict(c)
        for label, days in horizons.items():
            row[f"sp_fwd_{label}"] = None if (r := forward_stat(sp, c["first_cut_month"], days)) is None else round(r, 4)
        mdd = max_drawdown(sp, c["first_cut_month"], 365)
        row["sp_max_dd_12m"] = None if mdd is None else round(mdd, 4)
        cycle_rows.append(row)
    analysis["cut_cycles"] = cycle_rows

    valid = {label: [r[f"sp_fwd_{label}"] for r in cycle_rows if r[f"sp_fwd_{label}"] is not None] for label in horizons}
    analysis["post_cut_forward_stats"] = {k: summarize(v) for k, v in valid.items() if v}
    mdds = [r["sp_max_dd_12m"] for r in cycle_rows if r["sp_max_dd_12m"] is not None]
    analysis["post_cut_max_dd_12m"] = summarize(mdds) if mdds else None

    # emergency vs slow: emergency = cumulative cut >= 1.0pp within 6 months of first cut
    ff = data["FEDFUNDS"]
    for row in cycle_rows:
        idx = next((i for i, (d, _) in enumerate(ff) if d >= row["first_cut_month"]), None)
        if idx is not None and idx + 6 < len(ff):
            row["cut_6m_pp"] = round(ff[idx][1] - min(x[1] for x in ff[idx:idx + 7]), 2)
        row["style"] = "EMERGENCY" if (row.get("cut_6m_pp") or 0) >= 1.0 else "SLOW"
    slow = [r["sp_fwd_12m"] for r in cycle_rows if r.get("style") == "SLOW" and r.get("sp_fwd_12m") is not None]
    emg = [r["sp_fwd_12m"] for r in cycle_rows if r.get("style") == "EMERGENCY" and r.get("sp_fwd_12m") is not None]
    analysis["slow_cut_12m"] = summarize(slow) if slow else None
    analysis["emergency_cut_12m"] = summarize(emg) if emg else None

    # --- 4. gold study ---------------------------------------------------------
    gold = data.get("GOLD", [])
    crisis_windows = {
        "1987_crash": "1987-10-01", "2000_dotcom": "2000-03-01", "2008_gfc": "2008-09-01",
        "2011_euro": "2011-08-01", "2020_covid": "2020-02-01", "2022_bear": "2022-01-01",
    }
    gold_rows = []
    for name, start in crisis_windows.items():
        g6 = forward_stat(gold, (dt.date.fromisoformat(start) - dt.timedelta(days=182)).isoformat(), 182)
        g_after = forward_stat(gold, start, 182)
        s_after = forward_stat(sp, start, 182)
        gold_rows.append({"window": name, "gold_6m_before": None if g6 is None else round(g6, 4),
                          "gold_6m_after": None if g_after is None else round(g_after, 4),
                          "sp500_6m_after": None if s_after is None else round(s_after, 4)})
    analysis["gold_crisis_windows"] = gold_rows

    # --- 5. yield curve vs recession ------------------------------------------
    curve = data["T10Y3M"]
    rec = data["USREC"]
    inversions, in_inv = [], False
    for d, v in curve:
        if v < 0 and not in_inv:
            inversions.append({"inversion_start": d})
            in_inv = True
        elif v >= 0 and in_inv:
            inversions[-1]["uninversion"] = d
            in_inv = False
    rec_starts = [d for i, (d, v) in enumerate(rec) if v == 1 and (i == 0 or rec[i - 1][1] == 0)]
    for inv in inversions:
        un = inv.get("uninversion")
        if un:
            nxt = next((r for r in rec_starts if r >= un), None)
            inv["next_recession_start"] = nxt
            if nxt:
                inv["months_uninvert_to_recession"] = round((dt.date.fromisoformat(nxt) - dt.date.fromisoformat(un)).days / 30.44, 1)
    analysis["curve_10y3m_inversions"] = [i for i in inversions if "uninversion" in i]

    # --- 6. current snapshot ----------------------------------------------------
    def last(sid: str):
        return {"date": data[sid][-1][0], "value": data[sid][-1][1]} if data.get(sid) else None

    snap = {}
    for sid in SERIES:
        if data.get(sid):
            snap[sid] = last(sid)
    snap["HY_spread_percentile_10y"] = percentile_of(data["BAMLH0A0HYM2"], data["BAMLH0A0HYM2"][-1][1], 10)
    snap["IG_spread_percentile_10y"] = percentile_of(data["BAMLC0A0CM"], data["BAMLC0A0CM"][-1][1], 10)
    snap["VIX_percentile_10y"] = percentile_of(data["VIXCLS"], data["VIXCLS"][-1][1], 10)
    snap["SP500_yoy"] = None if (v := yoy(data["SP500"], 252)) is None else round(v, 4)
    snap["gold_yoy"] = None if not data.get("GOLD") else (None if (v := yoy(data["GOLD"], 365)) is None else round(v, 4))
    snap["M2_yoy"] = None if (v := yoy(data["M2SL"])) is None else round(v, 4)
    snap["CPI_yoy"] = None if (v := yoy(data["CPIAUCSL"])) is None else round(v, 4)
    snap["core_CPI_yoy"] = None if (v := yoy(data["CPILFESL"])) is None else round(v, 4)
    snap["core_PCE_yoy"] = None if (v := yoy(data["PCEPILFE"])) is None else round(v, 4)
    snap["payroll_3m_avg_change_k"] = None
    if len(data["PAYEMS"]) >= 4:
        changes = [data["PAYEMS"][i][1] - data["PAYEMS"][i - 1][1] for i in range(-3, 0)]
        snap["payroll_3m_avg_change_k"] = round(statistics.fmean(changes), 1)
    snap["LEI_yoy"] = None if (v := yoy(data["USSLIND"])) is None else round(v, 4)
    snap["WALCL_12m_change_bn"] = None
    if len(data["WALCL"]) >= 53:
        snap["WALCL_12m_change_bn"] = round(data["WALCL"][-1][1] - data["WALCL"][-53][1], 1)
    analysis["snapshot"] = snap

    out_path = OUT / "analysis.json"
    out_path.write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    print(f"\nanalysis.json written: {out_path}")
    if failures:
        print(f"FAILURES: {list(failures)}")


if __name__ == "__main__":
    sys.exit(main())
