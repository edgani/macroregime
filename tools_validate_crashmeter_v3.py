"""Reverse-engineering + historical validation of "Crashmeter 3.0" (Tomhardi article, May 2026).

Article rules (fixed, not tuned by us):
  A1: T10Y3M spread > 0.5  -> 0 else 1           (FRED T10Y3M, daily)
  A2: within 18 months after the end of the last yield-curve inversion -> 1 else 0
  B1: HY OAS 6-month range > 150bps -> 1 else 0  (FRED BAMLH0A0HYM2, daily)
  B2: HY OAS > 550bps -> 1 else 0
  C:  Shiller CAPE > 35 -> 1 else 0               (multpl monthly table)
Score 0-4:  0-1 aman | 2 waspada | 3 exit window | 4 critical

Article claims to validate (no parameter changes — we test the author's fixed formula):
  1) Dotcom 2000: score 3 fired when S&P500 was only ~3.5% below peak.
  2) GFC 2008: score 3 fired when S&P500 was only ~6% below peak.
Validation data: FRED daily series + monthly S&P/CAPE history (multpl).
Outputs:
  data/macro_investigation/crashmeter_v3_daily.csv      (from 1997 = HY OAS start)
  data/macro_investigation/crashmeter_v3_validation.json
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "macro_investigation"
UA = {"User-Agent": "curl/8.5.0 WarRoomOS/10.1"}


def get(url: str, timeout: int = 60) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def fred_series(series_id: str) -> dict[date, float]:
    raw = get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}").decode("utf-8", "replace")
    out: dict[date, float] = {}
    for row in csv.DictReader(io.StringIO(raw)):
        v = (row.get(series_id) or row.get("VALUE") or "").strip()
        if v in ("", "."):
            continue
        try:
            out[date.fromisoformat(row["observation_date"])] = float(v)
        except (KeyError, ValueError):
            continue
    return out


def multpl_monthly(slug: str) -> dict[date, float]:
    """multpl.com <slug>/table/by-month -> {first-of-month date: value}."""
    from lxml import html as lxml_html
    raw = get(f"https://www.multpl.com/{slug}/table/by-month")
    doc = lxml_html.fromstring(raw)
    out: dict[date, float] = {}
    for tr in doc.xpath("//table//tr"):
        cells = [c.text_content().strip() for c in tr.xpath("./td")]
        if len(cells) < 2:
            continue
        try:
            d = datetime.strptime(cells[0], "%b %d, %Y").date().replace(day=1)
            v = float(cells[1].replace(",", "").rstrip("%"))
            out[d] = v
        except ValueError:
            continue
    return out


def monthly_to_daily(monthly: dict[date, float], days: list[date]) -> dict[date, float]:
    keys = sorted(monthly)
    out: dict[date, float] = {}
    for d in days:
        eligible = [k for k in keys if k <= d]
        if eligible:
            out[d] = monthly[eligible[-1]]
    return out


def inversion_episodes(spread: dict[date, float], min_days: int = 10) -> list[tuple[date, date]]:
    """Contiguous episodes where T10Y3M < 0 for at least min_days trading days."""
    days = sorted(spread)
    episodes: list[tuple[date, date]] = []
    start = None
    last_neg = None
    for d in days:
        neg = spread[d] < 0
        if neg and start is None:
            start = d
        if neg:
            last_neg = d
        if not neg and start is not None:
            if (last_neg - start).days >= min_days:
                episodes.append((start, last_neg))
            start = None
            last_neg = None
    if start is not None and last_neg is not None and (last_neg - start).days >= min_days:
        episodes.append((start, last_neg))
    return episodes


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    print("fetch T10Y3M...")
    t10y3m = fred_series("T10Y3M")
    time.sleep(1)
    print("fetch HY OAS...")
    hy = fred_series("BAMLH0A0HYM2")
    time.sleep(1)
    print("fetch CAPE (multpl)...")
    cape_m = multpl_monthly("shiller-pe")
    time.sleep(1)
    print("fetch S&P500 monthly (multpl)...")
    spx_m = multpl_monthly("s-p-500-historical-prices")
    print(f"t10y3m n={len(t10y3m)} hy n={len(hy)} cape n={len(cape_m)} spx n={len(spx_m)}")

    episodes = inversion_episodes(t10y3m)
    print("inversion episodes:", [(str(a), str(b)) for a, b in episodes])

    hy_history_start = min(hy) if hy else None
    claims_check_valid = bool(hy_history_start and hy_history_start <= date(2000, 1, 1))
    if not claims_check_valid:
        print(f"WARNING: HY OAS history starts {hy_history_start} (ICE redistribution limit) "
              "-> B components uncomputable before that; the dotcom/GFC claims check is VOID "
              "(absence of score>=3 in the check proves nothing). Author backtest screenshots "
              "claim: EXIT Agu 2000 (-6.4% from peak), EXIT Nov 2007 (-6%), Covid late (-7.6%).")

    days = sorted(hy)  # HY OAS starts 1996-12 -> score computable from 1997+
    cape_d = monthly_to_daily(cape_m, days)

    rows: list[dict] = []
    for i, d in enumerate(days):
        spr = t10y3m.get(d)
        hyv = hy[d]
        cape = cape_d.get(d)
        if spr is None or cape is None:
            continue
        a1 = 0 if spr > 0.5 else 1
        a2 = 0
        for (_s, e) in episodes:
            if e <= d <= e + timedelta(days=548):  # ~18 months
                a2 = 1
                break
        window = [hy[dd] for dd in days[max(0, i - 126): i + 1]]  # ~6 trading months
        b1 = 1 if (max(window) - min(window)) * 100 > 150 else 0
        b2 = 1 if hyv * 100 > 550 else 0
        c = 1 if cape > 35 else 0
        rows.append({"date": d.isoformat(), "t10y3m": spr, "hy_oas": hyv, "cape": cape,
                     "a1": a1, "a2": a2, "b1": b1, "b2": b2, "c": c,
                     "score": a1 + a2 + b1 + b2 + c})

    with open(OUT / "crashmeter_v3_daily.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    # ---- validation of the article's two claims (monthly S&P drawdown from running peak)
    spx_days = sorted(spx_m)
    spx_d = monthly_to_daily(spx_m, days)

    def drawdown_from_peak(d: date) -> float:
        hist = [v for k, v in spx_d.items() if k <= d]
        if not hist:
            return 0.0
        peak = max(hist)
        cur = spx_d.get(d)
        return (cur / peak - 1.0) if cur else 0.0

    def first_score_ge(threshold: int, start: date, end: date):
        for r in rows:
            d = date.fromisoformat(r["date"])
            if start <= d <= end and r["score"] >= threshold:
                return d
        return None

    events = {
        "dotcom_2000": first_score_ge(3, date(1999, 1, 1), date(2002, 12, 31)),
        "gfc_2008": first_score_ge(3, date(2006, 1, 1), date(2009, 12, 31)),
        "covid_2020": first_score_ge(3, date(2019, 6, 1), date(2020, 12, 31)),
    }
    validation: dict = {"claims": {}, "false_alarm_check": {}, "current": rows[-1]}
    for name, d in events.items():
        if d:
            validation["claims"][name] = {"first_score_ge3": d.isoformat(),
                                          "spx_drawdown_from_peak_pct": round(drawdown_from_peak(d) * 100, 1)}
        else:
            validation["claims"][name] = {"first_score_ge3": None}

    # false alarms: score>=3 dates NOT followed by >=20% drawdown within 12 months (monthly data)
    alarm_dates = [date.fromisoformat(r["date"]) for r in rows if r["score"] >= 3]
    clusters: list[date] = []
    for d in alarm_dates:
        if not clusters or (d - clusters[-1]).days > 400:
            clusters.append(d)
    fa = []
    for d in clusters:
        fwd = [v for k, v in spx_d.items() if d < k <= d + timedelta(days=365)]
        base = spx_d.get(d)
        worst = (min(fwd) / base - 1.0) if fwd and base else 0.0
        fa.append({"cluster_start": d.isoformat(), "worst_forward_12m_pct": round(worst * 100, 1),
                   "real_20pct_crash": worst <= -0.20})
    validation["false_alarm_check"] = fa
    validation["claims_check_valid"] = claims_check_valid
    validation["claims_check_void_reason"] = (
        None if claims_check_valid else
        f"HY OAS history starts {hy_history_start} (ICE redistribution limit); B components "
        "uncomputable for 2000/2008 windows, so absence of score>=3 proves nothing."
    )
    validation["score_rows"] = len(rows)
    validation["latest"] = rows[-1]
    (OUT / "crashmeter_v3_validation.json").write_text(json.dumps(validation, indent=1, default=str), encoding="utf-8")
    print(json.dumps(validation["claims"], indent=1))
    print("false-alarm clusters:", len(fa), "| with real >=20% crash within 12m:", sum(1 for x in fa if x["real_20pct_crash"]))
    print("latest:", json.dumps(rows[-1]))


if __name__ == "__main__":
    main()
