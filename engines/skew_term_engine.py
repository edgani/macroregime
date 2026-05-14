"""engines/skew_term_engine.py — Cem Karsan 30D Skew Swap Edge
Tracks 30-day vs 60-day implied skew spread using proxy from price action.
"""
from __future__ import annotations
import math, logging
from typing import Dict, List
import pandas as pd
import numpy as np

logger = logging.getLogger("skew_term")

def _skew_proxy(ticker: str, s: pd.Series, days_short: int = 30, days_long: int = 60) -> Dict:
    if s is None or len(s) < days_long + 5:
        return {"ok": False}
    try:
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        if len(s_clean) < days_long + 5:
            return {"ok": False}
        rets = s_clean.pct_change().dropna()
        if len(rets) < days_long:
            return {"ok": False}
        short_rets = rets.tail(days_short)
        long_rets = rets.tail(days_long)
        down_short = short_rets[short_rets < 0].std() * math.sqrt(252)
        up_short = short_rets[short_rets > 0].std() * math.sqrt(252)
        down_long = long_rets[long_rets < 0].std() * math.sqrt(252)
        up_long = long_rets[long_rets > 0].std() * math.sqrt(252)
        skew_short = (down_short / up_short) if up_short > 0 else 1.0
        skew_long = (down_long / up_long) if up_long > 0 else 1.0
        spread = skew_short - skew_long
        signal = "RICH_30D" if spread > 0.15 else "CHEAP_30D" if spread < -0.15 else "FAIR"
        return {
            "ok": True, "skew_30d": round(skew_short, 3), "skew_60d": round(skew_long, 3),
            "spread": round(spread, 3), "signal": signal,
            "downside_vol_30d": round(down_short, 3), "upside_vol_30d": round(up_short, 3),
        }
    except Exception as e:
        logger.debug(f"Skew proxy failed for {ticker}: {e}")
        return {"ok": False}

def run_skew_term(tickers: List[str], prices: Dict[str, pd.Series]) -> Dict:
    results = {}
    rich_30d = []
    cheap_30d = []
    for t in tickers[:80]:
        s = prices.get(t)
        r = _skew_proxy(t, s)
        if r.get("ok"):
            results[t] = r
            if r["signal"] == "RICH_30D":
                rich_30d.append(t)
            elif r["signal"] == "CHEAP_30D":
                cheap_30d.append(t)
    return {
        "skew_data": results, "rich_30d": rich_30d[:10], "cheap_30d": cheap_30d[:10],
        "term_regime": "STRUCTURAL_OVERBID_30D" if len(rich_30d) > len(cheap_30d) * 2 else "NORMAL",
        "summary": f"30D skew rich: {len(rich_30d)} | cheap: {len(cheap_30d)}",
    }
