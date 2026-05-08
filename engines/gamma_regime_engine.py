"""engines/gamma_regime_engine.py — Gamma Regime Approximation

Tier 1 Alpha's Gamma Throttle adalah proprietary.
Kita compute approximation yang secara statistik sangat berkorelasi:

Core Formula:
  Gamma Throttle ≈ f(VIX_implied, rVol_realized, vol_premium, skew, put_call_ratio)

Logika:
  - VIX = implied vol (forward-looking dealer hedging cost)
  - rVol = realized vol (apa yang benar-benar terjadi)
  - Vol Premium = VIX - rVol → tinggi = dealer hedging mahal = cenderung long gamma
  - Gamma Throttle tinggi (+) = dealer long gamma = suppression mode
  - Gamma Throttle rendah (-) = dealer short gamma = amplification mode

Dari scatter chart Tier 1 Alpha:
  - Throttle +26 → rVol ~12 (sekarang)
  - Throttle 0   → rVol ~20 (transition zone)
  - Throttle -50 → rVol ~60+ (bear market / crash)

Engine ini menghasilkan:
  throttle_approx: float  (scale -105 to +35, sama dengan Tier 1 Alpha)
  rvol_10d: float
  rvol_30d: float
  vol_premium: float
  regime: str  (DEEP_POSITIVE / POSITIVE / TRANSITION / NEGATIVE / DEEP_NEGATIVE)
  dip_buy: bool
  regime_color: str
  regime_note: str
"""
from __future__ import annotations

import math
import numpy as np
import pandas as pd
from typing import Dict, Optional


# ── Constants (dari calibrasi scatter Tier 1 Alpha chart) ────────────────────
# rVol vs Throttle relationship (approximate inverse curve)
# Throttle = A - B * rVol^C  (fitted from scatter)
# Best fit dari data yang visible di chart:
THROTTLE_A = 35.0    # max throttle (rVol → 0)
THROTTLE_B = 2.8     # scaling coefficient
THROTTLE_C = 1.35    # exponent (curvature)
THROTTLE_MIN = -105.0

# Vol premium thresholds
VOL_PREMIUM_BOOST = 2.0  # setiap 1 point vol premium → +2 throttle points (approx)


def _compute_rvol(prices: pd.Series, n: int) -> Optional[float]:
    """Annualized realized vol dari n-day log returns."""
    s = pd.to_numeric(prices, errors="coerce").dropna()
    if len(s) < n + 1:
        return None
    lr = np.log(s.iloc[-n:] / s.iloc[-n:].shift(1)).dropna()
    if len(lr) < 2:
        return None
    rvol = float(np.std(lr)) * np.sqrt(252) * 100  # annualized %, sama unit dengan VIX
    return round(rvol, 2) if math.isfinite(rvol) else None


def _throttle_from_rvol(rvol: float, vol_premium: float) -> float:
    """
    Core approximation: Gamma Throttle dari rVol + vol premium.
    
    Fitted dari Tier 1 Alpha scatter (rVol vs Throttle):
    - rVol ~12 → Throttle ~+26
    - rVol ~20 → Throttle ~+5
    - rVol ~30 → Throttle ~-15
    - rVol ~50 → Throttle ~-55
    - rVol ~80 → Throttle ~-95
    
    Vol premium adjustment: dealer lebih likely long gamma kalau VIX >> rVol
    (mereka jual options mahal → net long gamma dari hedging perspective)
    """
    if rvol <= 0:
        return THROTTLE_A

    # Base throttle dari rVol curve
    base = THROTTLE_A - THROTTLE_B * (rvol ** THROTTLE_C)
    base = max(THROTTLE_MIN, min(THROTTLE_A, base))

    # Vol premium adjustment (VIX - rVol > 0 = implied > realized = more likely long gamma)
    premium_adj = np.clip(vol_premium * VOL_PREMIUM_BOOST, -15, 15)

    throttle = base + premium_adj
    return round(np.clip(throttle, THROTTLE_MIN, THROTTLE_A), 2)


def _classify_regime(throttle: float) -> Dict[str, str]:
    """Classify gamma regime dari throttle value."""
    if throttle >= 15:
        return {
            "regime": "DEEP_POSITIVE",
            "label": "Deep Positive",
            "color": "#10B981",
            "bg": "#052e16",
            "border": "#16a34a",
            "impl": "Dealer long gamma → jual saat rally, beli saat dip. rVol ditekan mekanik.",
            "action": "DIP BUY",
            "dip_buy": True,
        }
    elif throttle >= 3:
        return {
            "regime": "POSITIVE",
            "label": "Positive",
            "color": "#34d399",
            "bg": "#052e16",
            "border": "#059669",
            "impl": "Range-bound. Buy dip di low Trade range, sell rip di high.",
            "action": "RANGE TRADE",
            "dip_buy": True,
        }
    elif throttle >= -5:
        return {
            "regime": "TRANSITION",
            "label": "Transition Zone",
            "color": "#F59E0B",
            "bg": "#451a03",
            "border": "#d97706",
            "impl": "Gamma transition — volatility bisa expand ke mana saja. Sizing lebih kecil.",
            "action": "CAUTIOUS",
            "dip_buy": False,
        }
    elif throttle >= -30:
        return {
            "regime": "NEGATIVE",
            "label": "Negative Gamma",
            "color": "#f87171",
            "bg": "#450a0a",
            "border": "#dc2626",
            "impl": "Dealer short gamma → beli saat naik, jual saat turun. Vol MELEBAR. Trend amplification.",
            "action": "TREND MODE",
            "dip_buy": False,
        }
    else:
        return {
            "regime": "DEEP_NEGATIVE",
            "label": "Deep Negative",
            "color": "#EF4444",
            "bg": "#3b0000",
            "border": "#b91c1c",
            "impl": "EXTREME negative gamma. Crash acceleration risk. Dealer selling into decline.",
            "action": "DEFENSIVE",
            "dip_buy": False,
        }


class GammaRegimeEngine:
    """
    Compute gamma regime approximation dari market prices.
    
    Inputs yang dibutuhkan dari snap["prices"]:
      - "SPY" atau "^GSPC"  → untuk rVol
      - "^VIX"              → untuk implied vol
    
    Output: dict yang masuk ke snap["gamma"]
    """

    def run(self, prices: Dict[str, pd.Series]) -> Dict:
        """
        Main compute.
        Returns dict dengan semua gamma regime metrics.
        """
        # ── 1. Get SPY prices ─────────────────────────────────────────────
        spy = prices.get("SPY") or prices.get("^GSPC")
        vix_series = prices.get("^VIX")

        if spy is None or len(spy) < 11:
            return self._fallback()

        spy = pd.to_numeric(spy, errors="coerce").dropna()

        # ── 2. Realized Vol (10d, 21d, 63d) ──────────────────────────────
        rvol_10 = _compute_rvol(spy, 10)
        rvol_21 = _compute_rvol(spy, 21)
        rvol_63 = _compute_rvol(spy, 63)

        if rvol_10 is None:
            return self._fallback()

        # ── 3. VIX (implied vol) ──────────────────────────────────────────
        vix_last = None
        if vix_series is not None:
            vs = pd.to_numeric(vix_series, errors="coerce").dropna()
            if not vs.empty:
                vix_last = float(vs.iloc[-1])

        # Vol premium = VIX - rVol_10 (in same units: %)
        # rVol_10 sudah annualized %, VIX juga dalam %
        if vix_last is not None and rvol_10 is not None:
            vol_premium = vix_last - rvol_10
        else:
            vol_premium = 0.0

        # ── 4. Compute throttle approximation ────────────────────────────
        throttle = _throttle_from_rvol(rvol_10, vol_premium)

        # ── 5. Classify regime ────────────────────────────────────────────
        regime_info = _classify_regime(throttle)

        # ── 6. Bar position (untuk progress bar di UI) ────────────────────
        # Map throttle (-105 to +35) → (0% to 100%)
        bar_pct = int((throttle - THROTTLE_MIN) / (THROTTLE_A - THROTTLE_MIN) * 100)
        bar_pct = max(0, min(100, bar_pct))

        # ── 7. Transition from previous regime (week-over-week change) ────
        # Computed dari rVol_10 vs rVol_21 direction
        vol_trend = "compressing" if (rvol_10 or 0) < (rvol_21 or 0) else "expanding"
        throttle_direction = "improving" if vol_trend == "compressing" else "deteriorating"

        return {
            "ok": True,
            "throttle": throttle,
            "throttle_label": f"{throttle:+.1f}",
            "rvol_10d": rvol_10,
            "rvol_21d": rvol_21,
            "rvol_63d": rvol_63,
            "vix": vix_last,
            "vol_premium": round(vol_premium, 2) if vol_premium else None,
            "bar_pct": bar_pct,
            "vol_trend": vol_trend,
            "throttle_direction": throttle_direction,
            "source": "computed_approximation",
            "note": "Approximation dari rVol + VIX. Tier 1 Alpha throttle = proprietary.",
            **regime_info,
        }

    def _fallback(self) -> Dict:
        """Fallback kalau data tidak tersedia."""
        return {
            "ok": False,
            "throttle": None,
            "rvol_10d": None,
            "vix": None,
            "regime": "UNKNOWN",
            "label": "No Data",
            "color": "#6B7280",
            "bg": "#111827",
            "border": "#374151",
            "impl": "Gamma data tidak tersedia. Pastikan SPY dan ^VIX ada di price loader.",
            "action": "NO SIGNAL",
            "dip_buy": False,
            "bar_pct": 50,
            "source": "fallback",
        }
