"""
momentum_tracker.py — Hedgeye Momentum Stock Tracker
Daily Risk Range™ signals for Magnificent 7 + signal strength grading.
Reuses TRRLRREngine from app.py.
"""
import os, sys, json, logging
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import yfinance as yf

try:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from app import TRRLRREngine, TRR_PARAMS, _fetch
    TRR_AVAILABLE = True
except Exception as e:
    TRR_AVAILABLE = False
    logging.warning(f"TRR import fail: {e}")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
GATE_MAG7 = {"vm": 1.00, "qmin": 55, "amin": 40, "short": True, "agemax": 35}


class MomentumTracker:
    def __init__(self, tickers=None):
        self.tickers = tickers or MAG7
        self.engine = TRRLRREngine(TRR_PARAMS) if TRR_AVAILABLE else None

    def _grade(self, quality: float, activity: float, transition: bool) -> str:
        strength = quality * 0.6 + activity * 0.4 + (15 if transition else 0)
        if strength >= 80:
            return "S"
        if strength >= 65:
            return "A"
        if strength >= 50:
            return "B"
        return "C"

    def _regime_alignment(self, trend_phase: int, structural_quad: str) -> str:
        quad_bullish = {"Q1": [1], "Q2": [1], "Q3": [1, -1], "Q4": [-1]}
        allowed = quad_bullish.get(structural_quad, [1])
        return "ALIGNED" if trend_phase in allowed else "COUNTER"

    def scan(self, prices: Optional[Dict[str, pd.Series]] = None, regime_quad: str = "Q2") -> List[Dict]:
        if not TRR_AVAILABLE or self.engine is None:
            return [{"error": "TRR engine unavailable"}]

        results = []
        for t in self.tickers:
            try:
                if prices and t in prices:
                    df_raw = prices[t]
                    df = pd.DataFrame({
                        "Open": df_raw, "High": df_raw, "Low": df_raw,
                        "Close": df_raw, "Volume": pd.Series(0, index=df_raw.index)
                    })
                else:
                    df = _fetch(t, period="3y")
                    if df is None or len(df) < 300:
                        continue

                r = self.engine.latest(df, vm=GATE_MAG7["vm"])
                if not r:
                    continue

                pr = float(df["Close"].iloc[-1])
                transition = r["trendTransUp"] or r["trendTransDown"] or r["tailTransUp"] or r["tailTransDown"]
                grade = self._grade(r["qualityScore"], r["activityScore"], transition)
                alignment = self._regime_alignment(r["trendPhase"], regime_quad)

                sig = "HOLD"
                if r["trendPhase"] == 1 and r["qualityScore"] >= 55:
                    sig = "BUY" if r["tradeBreakUp"] or r["trendTransUp"] else "ACCUMULATE"
                elif r["trendPhase"] == -1 and r["qualityScore"] >= 55:
                    sig = "SELL" if r["tradeBreakDown"] or r["trendTransDown"] else "REDUCE"
                elif r["trendPhase"] == 0:
                    sig = "WATCH"

                results.append({
                    "ticker": t,
                    "price": round(pr, 2),
                    "signal": sig,
                    "grade": grade,
                    "strength": round(r["qualityScore"] * 0.6 + r["activityScore"] * 0.4 + (15 if transition else 0), 1),
                    "quality": round(r["qualityScore"], 1),
                    "activity": round(r["activityScore"], 1),
                    "compression": round(r["compressionScore"], 1),
                    "trend_phase": r["trendPhase"],
                    "trade_trr": round(r["tradeTRR"], 2),
                    "trade_lrr": round(r["tradeLRR"], 2),
                    "trend_trr": round(r["trendTRR"], 2),
                    "trend_lrr": round(r["trendLRR"], 2),
                    "tail_trr": round(r["tailTRR"], 2),
                    "tail_lrr": round(r["tailLRR"], 2),
                    "transition": transition,
                    "regime_alignment": alignment,
                    "vol_regime": "EXPANDING" if r["volRegimeConfirm"] else "NORMAL",
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.warning(f"Momentum scan fail {t}: {e}")
                results.append({"ticker": t, "error": str(e)})

        results.sort(key=lambda x: x.get("strength", 0), reverse=True)
        return results


def get_momentum_snapshot(prices=None, regime_quad="Q2"):
    tracker = MomentumTracker()
    return tracker.scan(prices=prices, regime_quad=regime_quad)


if __name__ == "__main__":
    snap = get_momentum_snapshot(regime_quad="Q2")
    print(json.dumps(snap, indent=2, default=str))