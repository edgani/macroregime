"""
pods_model.py — Hedgeye Pods Model
Pod 1: Revenue Growth rate-of-change
Pod 2: Margins & Cash Flow inflection
Pod 3: Capital Allocation / FCF Yield
"""
import os, logging, math, json
from datetime import datetime
from typing import Dict, List, Optional
import yfinance as yf
import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)


class PodsModel:
    def __init__(self, ticker: str):
        self.ticker = ticker.upper()
        self.tk = yf.Ticker(ticker)
        self.rev_q: Optional[pd.Series] = None
        self.ni_q: Optional[pd.Series] = None
        self.fcf_q: Optional[pd.Series] = None
        self.shares: Optional[float] = None
        self.price: Optional[float] = None
        self.mc: Optional[float] = None

    def _load(self) -> bool:
        try:
            info = self.tk.info
            self.price = info.get("currentPrice", info.get("regularMarketPrice", None))
            self.shares = info.get("sharesOutstanding", None)
            self.mc = info.get("marketCap", None)
            if self.mc is None and self.price and self.shares:
                self.mc = self.price * self.shares

            inc = self.tk.quarterly_income_stmt
            cf = self.tk.quarterly_cashflow
            if inc is None or inc.empty:
                inc = self.tk.income_stmt
            if cf is None or cf.empty:
                cf = self.tk.cashflow

            if inc is not None and not inc.empty:
                rev_row = None
                for candidate in ["Total Revenue", "Revenue", "TotalRevenue"]:
                    if candidate in inc.index:
                        rev_row = candidate
                        break
                if rev_row:
                    self.rev_q = inc.loc[rev_row].dropna()
                    self.rev_q.index = pd.to_datetime(self.rev_q.index)

                ni_row = None
                for candidate in ["Net Income", "NetIncome", "Net Income Common Stockholders"]:
                    if candidate in inc.index:
                        ni_row = candidate
                        break
                if ni_row:
                    self.ni_q = inc.loc[ni_row].dropna()
                    self.ni_q.index = pd.to_datetime(self.ni_q.index)

            if cf is not None and not cf.empty:
                fcf_row = None
                for candidate in ["Free Cash Flow", "FreeCashFlow", "Total Free Cash Flow"]:
                    if candidate in cf.index:
                        fcf_row = candidate
                        break
                if fcf_row:
                    self.fcf_q = cf.loc[fcf_row].dropna()
                    self.fcf_q.index = pd.to_datetime(self.fcf_q.index)

            return self.rev_q is not None and len(self.rev_q) >= 4
        except Exception as e:
            logger.warning(f"Pods load fail {self.ticker}: {e}")
            return False

    def _yoy_growth(self, series: pd.Series) -> List[float]:
        growth = []
        for idx, val in series.items():
            try:
                prior = series[series.index <= (idx - pd.DateOffset(years=1))].iloc[-1]
                if prior and prior != 0 and math.isfinite(prior) and math.isfinite(val):
                    growth.append((val / prior) - 1.0)
            except:
                pass
        return growth

    def _roc_of_growth(self, growth: List[float]) -> str:
        if len(growth) < 3:
            return "insufficient_data"
        g0, g1, g2 = growth[-1], growth[-2], growth[-3]
        if not all(math.isfinite(x) for x in [g0, g1, g2]):
            return "insufficient_data"
        if g0 > g1 + 0.03 and g1 > g2 + 0.03:
            return "accelerating"
        if g0 < g1 - 0.03 and g1 < g2 - 0.03:
            return "decelerating"
        return "stable"

    def pod1_revenue(self) -> Dict:
        if self.rev_q is None or len(self.rev_q) < 4:
            return {"score": 0.0, "state": "no_data", "yoy": []}
        yoy = self._yoy_growth(self.rev_q)
        roc = self._roc_of_growth(yoy)
        score_map = {"accelerating": 1.0, "stable": 0.0, "decelerating": -1.0, "insufficient_data": 0.0}
        score = score_map.get(roc, 0.0)
        return {
            "score": score,
            "state": roc,
            "yoy_latest": round(yoy[-1] * 100, 1) if yoy else None,
            "yoy_history": [round(x * 100, 1) for x in yoy[-4:]],
        }

    def pod2_margins(self) -> Dict:
        if self.rev_q is None or self.ni_q is None or len(self.rev_q) < 4 or len(self.ni_q) < 4:
            return {"score": 0.0, "state": "no_data"}
        margin = (self.ni_q / self.rev_q).dropna()
        if len(margin) < 4:
            return {"score": 0.0, "state": "insufficient_data"}
        vals = margin.iloc[-4:].values
        if not all(math.isfinite(v) for v in vals):
            return {"score": 0.0, "state": "invalid"}
        if vals[-1] > vals[-2] > vals[-3]:
            return {"score": 1.0, "state": "expanding", "margin_latest": round(float(vals[-1]) * 100, 2)}
        if vals[-1] < vals[-2] < vals[-3]:
            return {"score": -1.0, "state": "contracting", "margin_latest": round(float(vals[-1]) * 100, 2)}
        return {"score": 0.0, "state": "stable", "margin_latest": round(float(vals[-1]) * 100, 2)}

    def pod3_fcf(self) -> Dict:
        if self.fcf_q is None or len(self.fcf_q) < 2:
            return {"score": 0.0, "state": "no_data"}
        latest_fcf = float(self.fcf_q.iloc[0]) if math.isfinite(self.fcf_q.iloc[0]) else 0.0
        fcf_yield = (latest_fcf / self.mc) if self.mc and self.mc > 0 else 0.0
        fcf_vals = self.fcf_q.iloc[:4].values
        if len(fcf_vals) >= 3 and all(math.isfinite(v) for v in fcf_vals):
            if fcf_vals[0] > fcf_vals[1] > fcf_vals[2]:
                trend = "improving"
            elif fcf_vals[0] < fcf_vals[1] < fcf_vals[2]:
                trend = "deteriorating"
            else:
                trend = "mixed"
        else:
            trend = "insufficient"
        score = 0.0
        if fcf_yield > 0.03 and trend == "improving":
            score = 1.0
        elif fcf_yield > 0.02 and trend in ("improving", "mixed"):
            score = 0.5
        elif latest_fcf < 0:
            score = -1.0
        elif fcf_yield < 0.01:
            score = -0.5
        return {
            "score": score,
            "state": trend,
            "fcf_yield": round(fcf_yield * 100, 2),
            "fcf_latest": round(latest_fcf / 1e9, 2),
        }

    def evaluate(self) -> Dict:
        if not self._load():
            return {"ticker": self.ticker, "error": "Insufficient fundamental data"}
        p1 = self.pod1_revenue()
        p2 = self.pod2_margins()
        p3 = self.pod3_fcf()
        combined = 0.40 * p1["score"] + 0.35 * p2["score"] + 0.25 * p3["score"]
        grade = "A" if combined >= 0.6 else "B" if combined >= 0.2 else "C" if combined >= -0.2 else "D"
        signal = "LONG" if combined >= 0.4 else "SHORT" if combined <= -0.4 else "NEUTRAL"
        # Hedgeye insight: In Q3, secular revenue acceleration (POD1) can win while cyclical GDP slows
        # Distinguish secular growth (long-term trend) from cyclical (short-term GDP-linked)
        secular_strength = "strong" if p1["score"] >= 0.5 and p2["score"] >= 0.0 else "moderate" if p1["score"] >= 0.0 else "weak"
        cyclical_risk = "low" if p3["score"] >= 0.0 else "elevated" if p3["score"] >= -0.5 else "high"
        return {
            "ticker": self.ticker,
            "price": self.price,
            "market_cap_b": round(self.mc / 1e9, 2) if self.mc else None,
            "pod1_revenue": p1,
            "pod2_margins": p2,
            "pod3_fcf": p3,
            "combined_score": round(combined, 2),
            "grade": grade,
            "signal": signal,
            "secular_strength": secular_strength,
            "cyclical_risk": cyclical_risk,
            "timestamp": datetime.now().isoformat(),
        }


def scan_pods(tickers: List[str]) -> List[Dict]:
    results = []
    for t in tickers:
        try:
            p = PodsModel(t)
            results.append(p.evaluate())
        except Exception as e:
            results.append({"ticker": t, "error": str(e)})
    return results


if __name__ == "__main__":
    mag7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
    out = scan_pods(mag7)
    print(json.dumps(out, indent=2, default=str))