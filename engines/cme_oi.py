"""engines/cme_oi.py — CME Open Interest Heatmap
Scrapes CME daily settlement/OI reports for futures + options OI by strike.
Covers: Commodities (GC, CL, SI, NG), Forex (EUR, GBP, JPY), Crypto (BTC, ETH).
"""
from __future__ import annotations
import requests
import logging
from typing import Dict, List, Optional, Tuple
import re

logger = logging.getLogger(__name__)

# CME product codes
CME_PRODUCTS = {
    # Commodities
    "GC=F": "GC", "SI=F": "SI", "PL=F": "PL", "PA=F": "PA",
    "CL=F": "CL", "BZ=F": "BZ", "NG=F": "NG", "RB=F": "RB", "HO=F": "HO",
    "HG=F": "HG", "ALI=F": "ALI",
    # Forex
    "EURUSD=X": "6E", "GBPUSD=X": "6B", "USDJPY=X": "6J", "USDCHF=X": "6S",
    "USDCAD=X": "6C", "AUDUSD=X": "6A", "NZDUSD=X": "6N",
    # Crypto
    "BTC-USD": "BTC", "ETH-USD": "ETH",
}

class CMEOIScraper:
    """
    Scrape CME OI data from public settlement reports.
    """
    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json, text/plain, */*",
        })

    def _try_cme_oi_json(self, product_code: str) -> Optional[dict]:
        """Try CME public JSON endpoint for OI data."""
        try:
            # CME has undocumented but stable JSON endpoints for settlements
            url = f"https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/{product_code}/FUT"
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list) and len(data) > 0:
                    # Extract OI from settlements
                    oi_total = sum(float(item.get("openInterest", 0) or 0) for item in data)
                    oi_change = sum(float(item.get("change", 0) or 0) for item in data)
                    return {
                        "oi_total": oi_total,
                        "oi_change": oi_change,
                        "contracts": len(data),
                    }
        except Exception as e:
            logger.warning(f"CME OI JSON fetch failed for {product_code}: {e}")
        return None

    def _try_cme_options_oi(self, product_code: str, spot_px: float) -> Optional[dict]:
        """Try to get options OI by strike from CME."""
        try:
            url = f"https://www.cmegroup.com/CmeWS/mvc/Settlements/Options/Settlements/{product_code}/OPT"
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                if data and isinstance(data, list):
                    strikes = {}
                    for item in data:
                        strike = float(item.get("strike", 0))
                        oi = float(item.get("openInterest", 0) or 0)
                        if strike > 0:
                            strikes[strike] = strikes.get(strike, 0) + oi
                    if strikes:
                        max_oi_strike = max(strikes.items(), key=lambda x: x[1])[0]
                        total_oi = sum(strikes.values())
                        # Find strikes near spot
                        near_strikes = {k: v for k, v in strikes.items() if abs(k - spot_px) / spot_px < 0.05}
                        return {
                            "oi_total": total_oi,
                            "max_oi_strike": max_oi_strike,
                            "strikes_data": strikes,
                            "near_spot_oi": sum(near_strikes.values()) if near_strikes else 0,
                        }
        except Exception as e:
            logger.warning(f"CME options OI fetch failed for {product_code}: {e}")
        return None

    def analyze(self, ticker: str, spot_px: Optional[float] = None) -> dict:
        """
        Get OI data for a ticker. Returns OI summary + heatmap data.
        """
        product = CME_PRODUCTS.get(ticker)
        if not product:
            return {"ok": False, "reason": f"No CME product mapping for {ticker}"}

        # Try futures OI
        fut_oi = self._try_cme_oi_json(product)

        # Try options OI
        opt_oi = None
        if spot_px and spot_px > 0:
            opt_oi = self._try_cme_options_oi(product, spot_px)

        if fut_oi or opt_oi:
            result = {"ok": True, "source": "CME", "product": product}
            if fut_oi:
                result["futures_oi"] = fut_oi
            if opt_oi:
                result["options_oi"] = opt_oi
            return result

        return {"ok": False, "reason": "CME OI data unavailable"}


class CMEOIProxy:
    """
    Generate OI proxy from volume + price action when CME data unavailable.
    """
    def __init__(self):
        pass

    def analyze(self, ticker: str, prices: dict, vix: float = 20.0) -> dict:
        s = prices.get(ticker)
        if s is None:
            return {"ok": False, "reason": f"No price data for {ticker}"}

        import pandas as pd
        s = pd.to_numeric(s, errors="coerce").dropna()
        if len(s) < 10:
            return {"ok": False, "reason": "Insufficient price history"}

        # Volume proxy (if available)
        vol = s.diff().abs().mean() if len(s) > 1 else 0

        # OI proxy: higher vol + higher VIX = higher OI interest
        oi_proxy = 100000 + vol * 10000 + (vix - 15) * 5000

        # OI trend: increasing if price trending
        r5d = float(s.iloc[-1] / s.iloc[-6] - 1) if len(s) >= 6 else 0
        oi_trend = "Rising 📈" if abs(r5d) > 0.02 else "Stable ↔"

        # Concentration proxy: where is price relative to recent range
        recent_high = float(s.tail(20).max())
        recent_low = float(s.tail(20).min())
        pos = (float(s.iloc[-1]) - recent_low) / (recent_high - recent_low) if recent_high > recent_low else 0.5

        if pos > 0.8:
            concentration = "High at highs 🔴"
        elif pos < 0.2:
            concentration = "High at lows 🟢"
        else:
            concentration = "Mid-range 🟡"

        return {
            "ok": True,
            "source": "proxy",
            "oi_total": round(oi_proxy, 0),
            "oi_trend": oi_trend,
            "concentration": concentration,
            "position_in_range": round(pos, 2),
            "vix": vix,
        }
