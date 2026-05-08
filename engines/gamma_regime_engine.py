"""engines/gamma_regime_engine.py — Gamma Regime Detection v3

FIX v3: Defensive against DataFrame->Series contamination from yfinance multi-ticker.
"""
from __future__ import annotations
import math
from typing import Dict, Optional
import numpy as np
import pandas as pd

class GammaRegimeEngine:
    """
    Detect gamma regime from realized vol + VIX proxy + price structure.
    """

    def _compute_rvol(self, prices, n: int = 21) -> Optional[float]:
        """Annualized realized volatility (%). DEFENSIVE against DataFrame input."""
        if prices is None: return None

        # DEFENSIVE: squeeze DataFrame -> Series
        s = prices
        if isinstance(s, pd.DataFrame):
            if s.shape[1] == 1:
                s = s.iloc[:, 0]
            else:
                s = s.squeeze()
        if not isinstance(s, pd.Series):
            return None

        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < n + 2:
            return None
        lr = np.log(s.iloc[-n:] / s.iloc[-n:].shift(1)).dropna()
        if len(lr) < 2:
            return None
        std_val = float(np.std(lr))
        if not math.isfinite(std_val):
            return None
        rvol = std_val * np.sqrt(252) * 100
        return round(rvol, 2) if math.isfinite(rvol) else None

    def run(self, prices: Dict[str, object], vix_proxy: Optional[float] = None) -> Dict:
        # DEFENSIVE: extract SPY with DataFrame guard
        spy_raw = prices.get("SPY")
        spy = spy_raw
        if isinstance(spy_raw, pd.DataFrame):
            spy = spy_raw.iloc[:, 0] if spy_raw.shape[1] > 0 else spy_raw.squeeze()
        if spy is None or (isinstance(spy, pd.Series) and spy.empty):
            return dict(ok=False, note="SPY price data unavailable")

        r10 = self._compute_rvol(spy, 10)
        r21 = self._compute_rvol(spy, 21)
        if r10 is None or r21 is None:
            return dict(ok=False, note="Insufficient SPY history for rVol")

        # VIX proxy fallback
        vix = vix_proxy
        if vix is None:
            vix_s = prices.get("^VIX")
            if vix_s is not None:
                if isinstance(vix_s, pd.DataFrame):
                    vix_s = vix_s.iloc[:, 0] if vix_s.shape[1] > 0 else vix_s.squeeze()
                if isinstance(vix_s, pd.Series) and not vix_s.empty:
                    vix = float(vix_s.iloc[-1]) if math.isfinite(vix_s.iloc[-1]) else None

        # Vol premium = implied - realized
        vp = (vix - r21) if (vix is not None and r21 is not None) else None

        # Throttle = slope of vol term structure (10d vs 21d)
        th = (r10 - r21) if (r10 is not None and r21 is not None) else 0.0

        # Bar position (where in the recent range is price)
        spy_num = pd.to_numeric(spy, errors="coerce").dropna()
        if len(spy_num) >= 20:
            recent = spy_num.iloc[-20:]
            lo = float(recent.min()); hi = float(recent.max())
            px = float(spy_num.iloc[-1])
            bar_pct = int(100 * (px - lo) / max(hi - lo, 1e-9)) if math.isfinite(px) else 50
        else:
            bar_pct = 50

        # Regime classification
        if r21 < 12 and (vp is not None and vp < 2):
            label = "Deep Positive"; color = "#10B981"; regime = "DEEP_POSITIVE"; action = "RISK ON — Max long gamma"
        elif r21 < 16 and (vp is not None and vp < 5):
            label = "Positive"; color = "#00D4AA"; regime = "POSITIVE"; action = "RISK ON — Trend-follow"
        elif r21 < 22 and (vp is not None and vp < 8):
            label = "Transition"; color = "#F59E0B"; regime = "TRANSITION"; action = "CAUTION — Reduce size"
        elif r21 < 30:
            label = "Negative"; color = "#EF4444"; regime = "NEGATIVE"; action = "RISK OFF — Hedge up"
        else:
            label = "Deep Negative"; color = "#7F1D1D"; regime = "DEEP_NEGATIVE"; action = "CRASH MODE — Cash + TLT"

        impl = (
            f"rVol {r21:.1f}% | VIX prem {vp:.1f}% | Throttle {th:+.1f} | "
            f"Bar {bar_pct}% | {action}"
        )

        return dict(
            ok=True, rvol_10d=r10, rvol_21d=r21, vix=vix, vol_premium=vp,
            throttle=round(th, 2), bar_pct=bar_pct, color=color, label=label,
            action=action, impl=impl, regime=regime,
        )
