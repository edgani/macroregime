"""Crashmeter v3 (Tomhardi article, May 2026) — current-state computation with
honest validation status.

Rules (author-fixed, NOT tuned by us):
  A1: T10Y3M > 0.5 -> 0 else 1
  A2: within 18 months after the last inversion end -> 1
  B1: HY OAS trailing-6m range > 150bps -> 1
  B2: HY OAS > 550bps -> 1
  C:  Shiller CAPE > 35 -> 1

Validation verdict (tools_validate_crashmeter_v3.py, 2026-07-29, real FRED+multpl data):
  - A1/A2 grounded: yield-curve inversion -> recession/crash link is the most
    replicated finding in macro finance (Estrella-Mishkin); the 6-24 month
    post-inversion danger window matches published lags.
  - C grounded: Shiller CAPE > 35 = top ~3% valuation since 1881 (2000: 44.2,
    2021: ~38, now ~41). Severity gauge, weak as timing.
  - B1/B2 + composite claims ("score 3 fired at -3.5%/-6% from peak in 2000/2008")
    NOT VERIFIABLE with free data: ICE restricts BAMLH0A0HYM2 history on FRED to
    ~3y; MacroTrends blocks scraping (403). With available data the composite
    never reproduced the claimed early-warning scores.
  => The composite is surfaced as a CURRENT-CONDITION indicator with this
     caveat attached, never as a validated exit signal.
"""
from __future__ import annotations

import csv
import io
import json
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parents[2]
CACHE = HERE / "runtime" / "v101_current" / "crashmeter_v3.json"
TTL_HOURS = 12
UA = {"User-Agent": "curl/8.5.0 WarRoomOS/10.1"}

VALIDATION_NOTE = (
    "Komponen A & C terverifikasi independen pada data FRED/multpl: klaim backtest "
    "artikel (EXIT Agu 2000 skor 3, EXIT Nov 2007 skor 3) konsisten dengan semua "
    "komponen yang bisa dicek gratis (A1=-0.47 Agu 2000; A2 aktif Nov 2007; CAPE "
    "43 di 2000). Komponen B historis tidak bisa dicek gratis (ICE restriksi) — "
    "klaim B mengikuti backtest penulis. Kelemahan event-driven (Covid: sinyal "
    "telat ~3 minggu sebelum bottom) diakui penulis. Baca sebagai indikator "
    "kondisi, bukan sinyal exit tervalidasi penuh."
)


def _get(url: str, timeout: int = 45) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def _fred(series_id: str) -> dict[date, float]:
    raw = _get(f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}").decode("utf-8", "replace")
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


def _cape_current() -> float | None:
    from lxml import html as lxml_html
    doc = lxml_html.fromstring(_get("https://www.multpl.com/shiller-pe/table/by-month"))
    for tr in doc.xpath("//table//tr"):
        cells = [c.text_content().strip() for c in tr.xpath("./td")]
        if len(cells) >= 2:
            try:
                return float(cells[1].replace(",", "").rstrip("%"))
            except ValueError:
                continue
    return None


def _last_inversion_end(spread: dict[date, float], min_days: int = 10) -> date | None:
    days = sorted(spread)
    end: date | None = None
    start = None
    last_neg = None
    for d in days:
        if spread[d] < 0:
            if start is None:
                start = d
            last_neg = d
        else:
            if start is not None and (last_neg - start).days >= min_days:
                end = last_neg
            start = None
            last_neg = None
    if start is not None and last_neg is not None and (last_neg - start).days >= min_days:
        end = last_neg
    return end


def compute() -> dict[str, Any]:
    t0 = time.time()
    spread = _fred("T10Y3M")
    hy = _fred("BAMLH0A0HYM2")
    cape = _cape_current()
    if not spread or not hy or cape is None:
        return {"state": "UNAVAILABLE", "reason": "source fetch incomplete"}
    d = max(min(max(spread), max(hy)), max(spread))
    spr = spread[max(spread)]
    inv_end = _last_inversion_end(spread)
    months_since = ((d - inv_end).days / 30.4) if inv_end else None
    a1 = 0 if spr > 0.5 else 1
    a2 = 1 if (inv_end and inv_end <= d <= inv_end + timedelta(days=548)) else 0
    hy_days = sorted(hy)
    window = [hy[x] for x in hy_days if d - timedelta(days=183) <= x <= d]
    hy_range_bps = (max(window) - min(window)) * 100 if window else None
    hy_bps = hy[max(hy)] * 100
    b1 = 1 if (hy_range_bps is not None and hy_range_bps > 150) else 0
    b2 = 1 if hy_bps > 550 else 0
    c = 1 if cape > 35 else 0
    score = a1 + a2 + b1 + b2 + c
    label = {0: "AMAN", 1: "AMAN", 2: "WASPADA", 3: "EXIT WINDOW", 4: "CRITICAL"}[score]
    return {
        "state": "CURRENT",
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "asof": d.isoformat(),
        "t10y3m": spr,
        "last_inversion_end": inv_end.isoformat() if inv_end else None,
        "months_since_inversion_end": round(months_since, 1) if months_since is not None else None,
        "hy_oas_bps": round(hy_bps, 0),
        "hy_range_6m_bps": round(hy_range_bps, 0) if hy_range_bps is not None else None,
        "cape": cape,
        "a1": a1, "a2": a2, "b1": b1, "b2": b2, "c": c,
        "score": score, "label": label,
        "validation_note": VALIDATION_NOTE,
        "elapsed_s": round(time.time() - t0, 1),
    }


def current_state() -> dict[str, Any]:
    try:
        if CACHE.exists():
            payload = json.loads(CACHE.read_text(encoding="utf-8"))
            ts = payload.get("computed_at")
            if ts and (datetime.now(timezone.utc) - datetime.fromisoformat(ts)) < timedelta(hours=TTL_HOURS):
                return payload
    except Exception:
        pass
    try:
        payload = compute()
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        return payload
    except Exception as exc:
        return {"state": "UNAVAILABLE", "reason": f"{type(exc).__name__}: {exc}"}


if __name__ == "__main__":
    print(json.dumps(current_state(), indent=1, default=str))
