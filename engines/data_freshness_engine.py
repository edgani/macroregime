"""data_freshness_engine.py

Real-time data confidence scoring per indicator.
Tells you: "This data is 3 days old, this one is proxy-only, this one is live."

Prevents over-confidence when FRED is stale or yfinance fails.
"""
from __future__ import annotations
import math, os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List
import pandas as pd


_FRED_CACHE_DIR = os.environ.get("MRP_FRED_CACHE_DIR", ".cache/fred")
_EXPECTED_FREQ: Dict[str, int] = {
    # Series → expected lag in days (how old can it be before it's stale?)
    "INDPRO":   45,  "RSAFS":   45,  "PAYEMS":  35,
    "UNRATE":   45,  "ICSA":     7,  "ISMNO":   35,
    "HOUST":    45,  "CPI":     35,  "CORECPI": 35,
    "T5YIE":    1,   "DFII10":   1,  "FEDFUNDS": 30,
    "HY_OAS":   7,   "IG_OAS":   7,
}

_PRICE_FRESHNESS_DAYS = 2  # prices older than 2 days = stale


@pd.api.extensions.register_dataframe_accessor("freshness")
class FreshnessAccessor:
    def __init__(self, pandas_obj): self._obj = pandas_obj


def _series_freshness(s: pd.Series, max_lag_days: int) -> Dict:
    """Score a single series for data freshness."""
    if s is None or len(s) == 0:
        return {"status": "missing", "score": 0.0, "age_days": None, "latest": None}
    try:
        latest = s.index[-1]
        if hasattr(latest, 'date'):
            latest_date = latest.date() if hasattr(latest, 'date') else latest
        else:
            latest_date = pd.Timestamp(latest).date()
        today = datetime.now(timezone.utc).date()
        age_days = (today - latest_date).days
        if age_days <= 0:
            status, score = "live", 1.00
        elif age_days <= max_lag_days:
            score = max(0.30, 1.0 - (age_days / max_lag_days) * 0.70)
            status = "fresh" if age_days <= max_lag_days // 2 else "aging"
        else:
            score = max(0.05, 0.30 * (max_lag_days / max(age_days, 1)))
            status = "stale"
        return {
            "status": status, "score": round(score, 3),
            "age_days": age_days, "latest": str(latest_date),
        }
    except Exception:
        return {"status": "error", "score": 0.10, "age_days": None, "latest": None}


def build_data_freshness_report(
    fred: Dict[str, pd.Series],
    prices: Dict[str, pd.Series],
) -> Dict:
    """
    Build a per-series freshness report and aggregate confidence score.

    Returns:
        {
            "overall_confidence": 0.0-1.0,
            "fred_confidence": 0.0-1.0,
            "price_confidence": 0.0-1.0,
            "series": {name: {status, score, age_days, latest}},
            "stale_count": int,
            "missing_count": int,
            "freshness_label": "Live | Aging | Stale | Degraded",
            "freshness_color": "#hex",
            "warning_text": str or None,
        }
    """
    series_report: Dict[str, Dict] = {}

    # FRED series
    fred_scores = []
    for name, s in (fred or {}).items():
        max_lag = _EXPECTED_FREQ.get(name, 30)
        info = _series_freshness(s, max_lag)
        series_report[name] = {**info, "type": "fred"}
        fred_scores.append(info["score"])

    # Key price series
    key_prices = ["SPY", "QQQ", "IWM", "GLD", "TLT", "HYG", "^VIX",
                  "CL=F", "GC=F", "HG=F", "UUP", "BTC-USD", "^JKSE"]
    price_scores = []
    for tk in key_prices:
        s = (prices or {}).get(tk)
        info = _series_freshness(s, _PRICE_FRESHNESS_DAYS)
        series_report[tk] = {**info, "type": "price"}
        price_scores.append(info["score"])

    fred_conf = float(sum(fred_scores) / max(len(fred_scores), 1)) if fred_scores else 0.5
    price_conf = float(sum(price_scores) / max(len(price_scores), 1)) if price_scores else 0.5
    overall = round(0.65 * fred_conf + 0.35 * price_conf, 3)

    stale = sum(1 for v in series_report.values() if v["status"] == "stale")
    missing = sum(1 for v in series_report.values() if v["status"] == "missing")

    if overall >= 0.80:
        label, color = "Live", "#48bb78"
    elif overall >= 0.60:
        label, color = "Aging", "#f6ad55"
    elif overall >= 0.40:
        label, color = "Stale", "#fc8181"
    else:
        label, color = "Degraded", "#e53e3e"

    warning = None
    if stale >= 3:
        warning = f"{stale} series stale — regime signal reliability reduced"
    elif missing >= 2:
        warning = f"{missing} series missing — FRED or price fetch failed"

    return {
        "overall_confidence": overall,
        "fred_confidence": round(fred_conf, 3),
        "price_confidence": round(price_conf, 3),
        "series": series_report,
        "stale_count": stale,
        "missing_count": missing,
        "freshness_label": label,
        "freshness_color": color,
        "warning_text": warning,
    }
