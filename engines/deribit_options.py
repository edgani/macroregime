"""engines/deribit_options.py — Real Crypto Options Greeks via Deribit API
Free public API, no key required. BTC, ETH, SOL, XRP, ADA, etc.
"""
from __future__ import annotations
import requests
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Map our tickers → Deribit currency codes
CURRENCY_MAP = {
    "BTC-USD": "BTC", "IBIT": "BTC", "FBTC": "BTC", "MSTY": "BTC",
    "ETH-USD": "ETH", "ETHA": "ETH",
    "SOL-USD": "SOL",
    "XRP-USD": "XRP",
    "ADA-USD": "ADA",
    "AVAX-USD": "AVAX",
    "DOT-USD": "DOT",
    "LINK-USD": "LINK",
    "DOGE-USD": "DOGE",
    "LTC-USD": "LTC",
    "BNB-USD": "BNB",
}

class DeribitOptionsAPI:
    """
    Fetch real options data from Deribit public API.
    Returns: implied_move_pct, iv_percentile, max_pain, delta, gamma, vega, theta
    """
    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.base = "https://www.deribit.com/api/v2/public"

    def _get(self, method: str, params: dict) -> dict:
        url = f"{self.base}/{method}"
        try:
            r = requests.get(url, params=params, timeout=self.timeout)
            r.raise_for_status()
            j = r.json()
            return j.get("result", {})
        except Exception as e:
            logger.warning(f"Deribit API fail {method}: {e}")
            return {}

    def get_book_summary(self, currency: str) -> List[dict]:
        """Get all option instruments summary for a currency."""
        return self._get("get_book_summary_by_currency", {
            "currency": currency,
            "kind": "option",
        })

    def get_index_price(self, currency: str) -> float:
        """Current spot/index price."""
        res = self._get("get_index_price", {"index_name": f"{currency}_usd"})
        return float(res.get("index_price", 0)) if res else 0.0

    def analyze(self, ticker: str, spot_px: Optional[float] = None) -> dict:
        """
        Analyze options for a ticker. Returns dict compatible with app.py options merge.
        """
        currency = CURRENCY_MAP.get(ticker)
        if not currency:
            return {"ok": False, "reason": f"No Deribit mapping for {ticker}"}

        if spot_px is None or spot_px <= 0:
            spot_px = self.get_index_price(currency)
        if spot_px <= 0:
            return {"ok": False, "reason": f"No spot price for {currency}"}

        summaries = self.get_book_summary(currency)
        if not summaries:
            return {"ok": False, "reason": "Deribit returned empty"}

        # Filter active instruments with greeks
        active = [s for s in summaries if s.get("mark_iv") and s.get("delta")]
        if not active:
            return {"ok": False, "reason": "No greeks available"}

        # Sort by open_interest to find most liquid expiry
        by_oi = sorted(active, key=lambda x: float(x.get("open_interest", 0) or 0), reverse=True)
        top = by_oi[0]

        # IV stats across all active
        ivs = [float(s.get("mark_iv", 0) or 0) for s in active if s.get("mark_iv")]
        avg_iv = sum(ivs) / len(ivs) if ivs else 0
        max_iv = max(ivs) if ivs else 1
        min_iv = min(ivs) if ivs else 0
        iv_range = max_iv - min_iv if max_iv > min_iv else 1
        iv_percentile = (avg_iv - min_iv) / iv_range if iv_range > 0 else 0.5

        # Max Pain approximation: strike with highest total OI (puts + calls)
        strike_oi: Dict[float, float] = {}
        for s in active:
            strike = float(s.get("strike", 0))
            oi = float(s.get("open_interest", 0) or 0)
            if strike > 0:
                strike_oi[strike] = strike_oi.get(strike, 0) + oi
        max_pain = max(strike_oi.items(), key=lambda x: x[1])[0] if strike_oi else spot_px

        # Implied move: ATM IV * sqrt(days_to_expiry/365) — use top liquid instrument
        mark_iv = float(top.get("mark_iv", 0) or 0)
        # Approximate annualized move
        implied_move_pct = mark_iv / 100.0  # IV is already annualized-ish

        # Greeks from top liquid instrument (closest to ATM)
        atm_dist = abs(float(top.get("strike", 0)) - spot_px)
        for s in by_oi[:10]:
            d = abs(float(s.get("strike", 0)) - spot_px)
            if d < atm_dist:
                atm_dist = d
                top = s

        delta = float(top.get("delta", 0) or 0)
        gamma = float(top.get("gamma", 0) or 0)
        vega = float(top.get("vega", 0) or 0)
        theta = float(top.get("theta", 0) or 0)

        # Determine direction label
        if delta > 0.3:
            delta_label = "Long 🟢"
        elif delta < -0.3:
            delta_label = "Short 🔴"
        else:
            delta_label = "Neutral 🟡"

        if gamma > 0.0005:
            gamma_label = "Long 🟢"
        elif gamma < -0.0005:
            gamma_label = "Short 🔴"
        else:
            gamma_label = "Flat 🟡"

        # Vanna proxy: delta sensitivity to vol (dDelta/dVol)
        # Approximate from sign of delta * vega
        if vega > 0 and delta > 0:
            vanna_label = "Positive ✅"
        elif vega > 0 and delta < 0:
            vanna_label = "Negative ⚠️"
        else:
            vanna_label = "Mixed 🟡"

        return {
            "ok": True,
            "source": "Deribit",
            "currency": currency,
            "implied_move_pct": round(implied_move_pct, 4),
            "iv_percentile": round(iv_percentile, 2),
            "max_pain": round(max_pain, 2),
            "delta": round(delta, 3),
            "gamma": round(gamma, 6),
            "vega": round(vega, 3),
            "theta": round(theta, 3),
            "mark_iv": round(mark_iv, 1),
            "delta_label": delta_label,
            "gamma_label": gamma_label,
            "vanna_label": vanna_label,
            "spot_px": round(spot_px, 2),
        }
