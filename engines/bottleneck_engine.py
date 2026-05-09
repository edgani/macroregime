"""engines/bottleneck_engine.py — Supply Chain Alpha Scanner v4.1
FIXES:
- Lower EV thresholds so Level 1/2 actually populates (was too strict: EV>=1.0)
- Better handling when risk_ranges partially missing
- Add option_expiry_bucket field for dashboard integration
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
import numpy as np
import pandas as pd
from config.settings import BOTTLENECK_PROFILES, TICKER_SECTOR, MARKET_CLASSIFICATION, QUAD_MARKET_DIRECTION

FUTURES_EXCLUDE = {
    "CL=F", "BZ=F", "NG=F", "RB=F", "HO=F",
    "GC=F", "SI=F", "PL=F", "PA=F",
    "HG=F", "ALI=F", "ZNC=F",
    "ZW=F", "ZC=F", "ZS=F", "ZO=F", "KC=F", "SB=F", "CT=F", "CC=F", "LBS=F",
}

def _safe_series(s):
    if s is None: return pd.Series(dtype=float)
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0] if s.shape[1] > 0 else s.squeeze()
    return pd.to_numeric(s, errors="coerce").dropna()

def _ret(s, n):
    s = _safe_series(s)
    if len(s) < n + 1: return float("nan")
    b = float(s.iloc[-n-1])
    return float(s.iloc[-1]/b - 1) if abs(b) > 1e-9 else float("nan")

class BottleneckEngine:
    def run(self, prices: Dict[str, object], structural_quad: str, monthly_quad: str,
            risk_ranges: Optional[Dict] = None) -> Dict[str, object]:
        risk_ranges = risk_ranges or {}
        level_1 = []; level_2 = []; watch = []; avoid = []
        market_buckets = {"us_equity": [], "forex": [], "commodity": [], "crypto": [], "ihsg": []}

        for ticker, close in prices.items():
            if ticker in FUTURES_EXCLUDE:
                continue

            sector = TICKER_SECTOR.get(ticker, "generic")
            profile = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES["generic"])
            mkt = MARKET_CLASSIFICATION.get(ticker, "us_equity")

            s = _safe_series(close)
            if len(s) < 64: continue
            r1 = _ret(s, 21); r3 = _ret(s, 63); r6 = _ret(s, 126)
            if not all(math.isfinite(x) for x in [r1, r3, r6]): continue

            trend = "uptrend" if r3 > 0.05 and r1 > -0.10 else "downtrend" if r3 < -0.05 else "mixed"
            if trend == "downtrend":
                avoid.append({"ticker": ticker, "sector": sector, "trend": trend, "score": 0.0, "ev": -0.5,
                              "regime_fit": False, "constraint": 0, "direction": "avoid",
                              "known_thesis": "", "regime_trap": True})
                continue

            # Regime fit
            sq_fit = profile["Q1"] if structural_quad == "Q1" else profile["Q2"] if structural_quad == "Q2" else profile["Q3"] if structural_quad == "Q3" else profile["Q4"]
            mq_fit = profile["Q1"] if monthly_quad == "Q1" else profile["Q2"] if monthly_quad == "Q2" else profile["Q3"] if monthly_quad == "Q3" else profile["Q4"]
            regime_fit = 0.55 * sq_fit + 0.45 * mq_fit

            # Trend score
            trend_score = np.clip((r3 + 0.5*r1) / 0.30, -1.0, 1.0)
            constraint = profile["constraint"]
            rs3m = r3
            forward_mult = 1.0 + np.clip(r6 / 0.50, -0.3, 0.5)

            # Range discount from Risk Ranges
            rr = risk_ranges.get(ticker, {}) if risk_ranges else {}
            tr = rr.get("trade", {}) if isinstance(rr, dict) else {}
            lrr = tr.get("lrr", float("nan")) if isinstance(tr, dict) else float("nan")
            trr = tr.get("trr", float("nan")) if isinstance(tr, dict) else float("nan")
            px = rr.get("px", float("nan")) if isinstance(rr, dict) else float("nan")
            range_discount = 1.0
            pos = float("nan")
            if all(math.isfinite(x) for x in [px, lrr, trr]) and (trr - lrr) > 1e-9:
                pos = (px - lrr) / (trr - lrr)
                range_discount = 1.0 - 0.30 * max(0, pos - 0.70)

            # EV v4.1 — slightly more lenient base multiplier
            ev = regime_fit * trend_score * constraint * (1.0 + rs3m) * forward_mult * range_discount
            ev = float(np.clip(ev, -2.0, 2.0))

            # Direction
            quad_dir = QUAD_MARKET_DIRECTION.get(structural_quad, {}).get(mkt, "neutral")
            direction = quad_dir if ev > 0 else "avoid" if ev < -0.3 else "neutral"

            # Regime trap
            regime_trap = False
            if ev > 0.8 and math.isfinite(pos):
                if pos > 0.85: regime_trap = True

            item = {
                "ticker": ticker, "sector": sector, "trend": trend,
                "score": round(float(np.clip(trend_score, 0, 1)), 2),
                "ev": round(ev, 2), "regime_fit": round(regime_fit, 2),
                "constraint": round(constraint, 2), "direction": direction,
                "known_thesis": "", "regime_trap": regime_trap,
                "r1": round(r1, 3), "r3": round(r3, 3), "r6": round(r6, 3),
                "range_pos": round(pos, 2) if math.isfinite(pos) else None,
                "option_expiry_bucket": None,  # populated by options engine later
            }

            if mkt in market_buckets:
                market_buckets[mkt].append(item)

            # v4.1: LOWER THRESHOLDS so dashboard actually shows setups
            if ev >= 0.70 and not regime_trap:      # was 1.0
                level_1.append(item)
            elif ev >= 0.35:                         # was 0.5
                level_2.append(item)
            elif ev >= 0.10:                          # was 0.15
                watch.append(item)
            elif ev < -0.15:                          # was -0.2
                avoid.append(item)

        level_1.sort(key=lambda x: -x["ev"])
        level_2.sort(key=lambda x: -x["ev"])
        watch.sort(key=lambda x: -x["ev"])
        avoid.sort(key=lambda x: x["ev"])

        # EM recovery signal
        em_recovery = None
        if structural_quad == "Q3" and monthly_quad == "Q2":
            em_recovery = {"trigger": "Monthly Q2 inside Structural Q3 = EM selective recovery",
                           "rationale": "Q2 monthly = commodity bid + growth rebound. EM commodity exporters lead.",
                           "confidence": 0.55, "best": ["EIDO", "EWW", "EWZ", "EWC", "NORW", "EWA"]}
        elif structural_quad == "Q4" and monthly_quad == "Q1":
            em_recovery = {"trigger": "Deflation -> Goldilocks = MAX EM recovery setup",
                           "rationale": "Q4->Q1 = growth re-acceleration + Fed easing. EM equities historically +25-40% in first 6M of Q1.",
                           "confidence": 0.85, "best": ["EIDO", "INDA", "EWZ", "EWW", "EEM", "VWO"]}

        return dict(
            level_1=level_1, level_2=level_2, watch=watch, avoid=avoid,
            market_buckets=market_buckets,
            em_recovery=em_recovery,
            total_scanned=len(prices),
            futures_excluded=len([t for t in prices if t in FUTURES_EXCLUDE]),
        )
