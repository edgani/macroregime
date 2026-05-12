"""engines/pvv_engine.py — Hedgeye-Style PVV + VASP + Multi-Duration Risk Range
Implements:
  • PVV = Price-Volume-Volatility rate-of-change  
  • Vol-of-Vol = ROC of realized volatility
  • Multi-Duration: TRADE (≤3w), TREND (≥3m), TAIL (≤3y)
  • VASP = Volatility-Adjusted Signaling Process
  • Fractal Risk Range™ (Hurst + PVV) — NOT simple Bollinger
"""
from __future__ import annotations
import math
import logging
import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DURATIONS = {
    "TRADE": {"days": 15,  "label": "≤3 weeks"},
    "TREND": {"days": 63,  "label": "≥3 months"},
    "TAIL":  {"days": 756, "label": "≤3 years"},
}

class PVVEngine:
    """
    Hedgeye-style multi-factor, multi-duration quantitative engine.
    """

    # ── helpers ──────────────────────────────────────────────────
    @staticmethod
    def _roc(s: pd.Series, window: int) -> pd.Series:
        """Rate of change: (today / lag) - 1"""
        return s.pct_change(window)

    @staticmethod
    def _realized_vol(s: pd.Series, window: int) -> pd.Series:
        """Annualized realized volatility from daily returns."""
        rets = s.pct_change().dropna()
        return rets.rolling(window).std() * math.sqrt(252)

    @staticmethod
    def _vol_of_vol(vol_series: pd.Series, window: int = 21) -> pd.Series:
        """ROC of realized volatility = Vol-of-Vol."""
        return vol_series.pct_change(window)

    @staticmethod
    def _hurst_exponent(prices: pd.Series, max_lag: int = 100) -> float:
        """
        Rescaled Range (R/S) Hurst exponent.
        H > 0.5 → trending/persistent
        H < 0.5 → mean-reverting
        H ≈ 0.5 → random walk
        """
        prices = pd.to_numeric(prices, errors="coerce").dropna()
        if len(prices) < max_lag * 2:
            return 0.5
        lags = range(2, min(max_lag, len(prices) // 4))
        tau = []
        rs_vals = []
        for lag in lags:
            # price returns for this lag
            p = prices.iloc[::lag].dropna()
            if len(p) < 10:
                continue
            rets = p.pct_change().dropna()
            if len(rets) < 5:
                continue
            mean_ret = rets.mean()
            dev = rets - mean_ret
            cumdev = dev.cumsum()
            R = cumdev.max() - cumdev.min()
            S = rets.std(ddof=1)
            if S == 0 or not math.isfinite(S):
                continue
            rs_vals.append(R / S)
            tau.append(lag)
        if len(tau) < 5:
            return 0.5
        log_tau = np.log(tau)
        log_rs = np.log(rs_vals)
        # linear regression log(R/S) vs log(lag)
        slope, _ = np.polyfit(log_tau, log_rs, 1)
        H = slope
        return float(np.clip(H, 0.0, 1.0))

    @staticmethod
    def _fractal_risk_range(price: pd.Series, volume: Optional[pd.Series],
                            vol: pd.Series, hurst: float,
                            pvv_score: float, duration_days: int) -> Tuple[float, float, float, float]:
        """
        Fractal-adjusted risk range.
        Returns: (lower_risk_range, upper_risk_range, midpoint, stretch_factor)
        """
        price = pd.to_numeric(price, errors="coerce").dropna()
        if len(price) < duration_days + 5:
            return (None, None, None, 1.0)

        # Base range from realized vol adjusted by Hurst
        base_vol = vol.iloc[-1] if len(vol) > 0 and math.isfinite(vol.iloc[-1]) else 0.20
        if base_vol <= 0:
            base_vol = 0.20

        # Hurst scaling: persistent (H>0.5) = wider range, mean-rev (H<0.5) = tighter
        hurst_adj = 1.0 + (hurst - 0.5) * 0.4  # ±20% scaling

        # PVV momentum adjustment: strong momentum = asymmetric range extension
        pvv_adj = 1.0 + abs(pvv_score) * 0.3

        # Vol-of-vol regime: high vol-of-vol = expand range
        vov = PVVEngine._vol_of_vol(vol, window=max(5, duration_days // 3))
        vov_last = vov.iloc[-1] if len(vov) > 0 and math.isfinite(vov.iloc[-1]) else 0.0
        vov_adj = 1.0 + abs(vov_last) * 0.5

        stretch = hurst_adj * pvv_adj * vov_adj
        px_last = float(price.iloc[-1])
        # Use ATR-style average true range as base width
        high_low = (price.rolling(2).max() - price.rolling(2).min()).mean()
        if not math.isfinite(high_low) or high_low == 0:
            high_low = px_last * base_vol / math.sqrt(252) * duration_days

        half_width = high_low * stretch * math.sqrt(duration_days / 252)
        # Asymmetric skew based on PVV direction
        skew = np.sign(pvv_score) * 0.05 * abs(pvv_score)
        mid = px_last * (1 + skew)
        lrr = mid - half_width
        trr = mid + half_width
        return (round(lrr, 4), round(trr, 4), round(mid, 4), round(stretch, 3))

    # ── core PVV per duration ──────────────────────────────────
    def _compute_duration(self, price: pd.Series, volume: Optional[pd.Series],
                          duration: str) -> Dict:
        days = DURATIONS[duration]["days"]
        price = pd.to_numeric(price, errors="coerce").dropna()
        if len(price) < days + 5:
            return {"ok": False, "error": f"Need {days+5} bars, got {len(price)}"}

        # 1. Price ROC
        price_roc = self._roc(price, days)
        p_roc = price_roc.iloc[-1] if len(price_roc) > 0 else 0.0

        # 2. Volume ROC (if available)
        if volume is not None and len(volume) >= days + 5:
            volume = pd.to_numeric(volume, errors="coerce").dropna()
            vol_roc = self._roc(volume, days).iloc[-1]
        else:
            vol_roc = 0.0

        # 3. Realized Volatility + Vol-of-Vol
        rv = self._realized_vol(price, days)
        rv_last = rv.iloc[-1] if len(rv) > 0 and math.isfinite(rv.iloc[-1]) else 0.20
        vov = self._vol_of_vol(rv, max(5, days // 3))
        vov_last = vov.iloc[-1] if len(vov) > 0 and math.isfinite(vov.iloc[-1]) else 0.0

        # 4. Hurst exponent (fractal dimension proxy)
        hurst = self._hurst_exponent(price, max_lag=min(100, days))

        # 5. PVV composite score (normalized -1 to +1)
        # Keith: P=price ROC, V=volume ROC, V=vol ROC (vol expansion = negative)
        vol_roc_norm = -vov_last  # vol expansion is bearish signal component
        pvv_raw = (
            np.tanh(p_roc * 10) * 0.50 +
            np.tanh(vol_roc * 5)  * 0.20 +
            np.tanh(vol_roc_norm * 5) * 0.30
        )
        pvv_score = float(np.clip(pvv_raw, -1.0, 1.0))

        # 6. VASP: Volatility-Adjusted Signaling Process
        # If vol is extreme, compress signal magnitude (noise reduction)
        vol_regime = "LOW" if rv_last < 15 else ("NORMAL" if rv_last < 25 else ("ELEVATED" if rv_last < 35 else "EXTREME"))
        vasp_mult = 1.0 if rv_last < 30 else 0.7 if rv_last < 45 else 0.5
        vasp_score = float(np.clip(pvv_score * vasp_mult, -1.0, 1.0))

        # 7. Signal classification
        if vasp_score >= 0.25:
            signal = "BULLISH"
        elif vasp_score <= -0.25:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"

        # 8. Fractal Risk Range
        lrr, trr, mid, stretch = self._fractal_risk_range(
            price, volume, rv, hurst, pvv_score, days
        )

        # 9. Position within range
        px_last = float(price.iloc[-1])
        if lrr and trr and trr > lrr:
            pos = (px_last - lrr) / (trr - lrr)
            pos = float(np.clip(pos, 0.0, 1.0))
        else:
            pos = 0.5

        # 10. Phase transition detection
        # Price vs TREND/TAIL threshold cross
        trend_sma = price.rolling(days).mean().iloc[-1]
        above_trend = px_last > trend_sma

        return {
            "ok": True,
            "duration": duration,
            "days": days,
            "signal": signal,
            "vasp_score": round(vasp_score, 4),
            "pvv_score": round(pvv_score, 4),
            "price_roc": round(p_roc, 4),
            "volume_roc": round(vol_roc, 4),
            "vol_of_vol": round(vov_last, 4),
            "realized_vol": round(rv_last, 2),
            "vol_regime": vol_regime,
            "hurst": round(hurst, 3),
            "stretch": stretch,
            "lrr": lrr,
            "trr": trr,
            "mid": mid,
            "price": round(px_last, 4),
            "position_pct": round(pos, 2),
            "above_trend_sma": above_trend,
            "trend_sma": round(trend_sma, 4) if math.isfinite(trend_sma) else None,
        }

    # ── public API ───────────────────────────────────────────────
    def analyze(self, price: pd.Series, volume: Optional[pd.Series] = None) -> Dict:
        """
        Full PVV analysis across TRADE / TREND / TAIL.
        Returns dict with per-duration results + composite summary.
        """
        results = {}
        for dur in DURATIONS:
            results[dur] = self._compute_duration(price, volume, dur)

        # Composite signal: weighted by duration importance
        # TREND (3m) gets highest weight for position bias
        weights = {"TRADE": 0.20, "TREND": 0.50, "TAIL": 0.30}
        weighted_score = 0.0
        total_w = 0.0
        for dur, w in weights.items():
            r = results[dur]
            if r.get("ok"):
                weighted_score += r["vasp_score"] * w
                total_w += w
        composite_score = weighted_score / total_w if total_w > 0 else 0.0

        if composite_score >= 0.30:
            composite_signal = "BULLISH"
        elif composite_score <= -0.30:
            composite_signal = "BEARISH"
        else:
            composite_signal = "NEUTRAL"

        # Front-run quad logic: if PVV momentum diverges from current price regime
        # e.g., price still in Q3 but PVV turning bullish = early Q1 signal
        trade_sig = results["TRADE"].get("signal", "NEUTRAL")
        trend_sig = results["TREND"].get("signal", "NEUTRAL")
        tail_sig  = results["TAIL"].get("signal", "NEUTRAL")

        # Bullish formation = all 3 durations aligned bullish or TREND+TAIL bullish
        bullish_formation = (trend_sig == "BULLISH" and tail_sig == "BULLISH")
        bearish_formation = (trend_sig == "BEARISH" and tail_sig == "BEARISH")

        return {
            "ok": True,
            "composite_signal": composite_signal,
            "composite_score": round(composite_score, 4),
            "bullish_formation": bullish_formation,
            "bearish_formation": bearish_formation,
            "trade": results["TRADE"],
            "trend": results["TREND"],
            "tail": results["TAIL"],
            "front_run_rationale": self._front_run_rationale(results),
        }

    def _front_run_rationale(self, results: Dict) -> str:
        """
        Explain how PVV signal leads macro/quad data.
        """
        t = results["TRADE"].get("signal", "NEUTRAL")
        tr = results["TREND"].get("signal", "NEUTRAL")
        ta = results["TAIL"].get("signal", "NEUTRAL")
        if t != tr and tr == ta and tr != "NEUTRAL":
            return f"TRADE diverging from {tr} TREND/TAIL — front-run window: 1-3 weeks"
        if tr != ta and ta != "NEUTRAL":
            return f"TREND diverging from {ta} TAIL — macro transition likely in 1-3 months"
        if t == tr == ta and t != "NEUTRAL":
            return f"All durations {t} — high conviction, regime aligned"
        return "Mixed durations — no clear front-run edge"


class PVVScanner:
    """Batch PVV analysis for many tickers."""

    def __init__(self):
        self.engine = PVVEngine()

    def analyze_multi(self, prices: Dict[str, pd.Series],
                      volumes: Optional[Dict[str, pd.Series]] = None) -> Dict[str, Dict]:
        volumes = volumes or {}
        out = {}
        for ticker, px in prices.items():
            if px is None or px.empty:
                out[ticker] = {"ok": False, "error": "No price data"}
                continue
            vol = volumes.get(ticker)
            try:
                out[ticker] = self.engine.analyze(px, vol)
            except Exception as e:
                logger.warning(f"PVV failed for {ticker}: {e}")
                out[ticker] = {"ok": False, "error": str(e)}
        return out
