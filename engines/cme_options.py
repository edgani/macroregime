"""engines/cme_options.py — CME Futures Options Scraper
Covers: Forex (EUR, GBP, JPY, CAD, AUD, etc) and Commodities (GC, SI, CL, NG, HG, etc).
CME does not have a simple free API for options chains. We use a hybrid approach:
1. Try CME public JSON endpoints (undocumented but stable)
2. Fallback to yfinance options chain for ETFs that proxy futures (GLD, SLV, USO, etc)
3. Final fallback to proxy Greeks
"""
from __future__ import annotations
import requests
import logging
from typing import Optional
import re

logger = logging.getLogger(__name__)

# CME product codes for futures options
CME_FOREX = {
    "EURUSD=X": "6E", "GBPUSD=X": "6B", "USDJPY=X": "6J", "USDCHF=X": "6S",
    "USDCAD=X": "6C", "AUDUSD=X": "6A", "NZDUSD=X": "6N", "USDSEK=X": "6L",
    "USDMXN=X": "6M", "USDBRL=X": "6L",  # BRL may not have liquid options
}

CME_COMMODITIES = {
    "GC=F": "GC", "SI=F": "SI", "PL=F": "PL", "PA=F": "PA",
    "CL=F": "CL", "BZ=F": "BZ", "NG=F": "NG", "RB=F": "RB", "HO=F": "HO",
    "HG=F": "HG", "ALI=F": "ALI", "ZNC=F": "ZNC",
}

# ETF proxies that have yfinance options chains
ETF_PROXY = {
    "GLD": "GLD", "SLV": "SLV", "PPLT": "PPLT",
    "USO": "USO", "UNG": "UNG", "BNO": "BNO",
    "CPER": "CPER", "SLX": "SLX",
    "GDX": "GDX", "GDXJ": "GDXJ", "SIL": "SIL", "SILJ": "SILJ",
    "XLE": "XLE", "OIH": "OIH", "XOP": "XOP",
    "URA": "URA", "CCJ": "CCJ",
}

class CMEOptionsScraper:
    def __init__(self, timeout: int = 12):
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

    def _try_yfinance_options(self, ticker: str, spot_px: float) -> Optional[dict]:
        """Fallback: use yfinance options chain for ETFs."""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            # Get nearest expiry options chain
            expirations = t.options
            if not expirations:
                return None
            chain = t.option_chain(expirations[0])
            calls = chain.calls
            puts = chain.puts
            if calls.empty or puts.empty:
                return None

            # ATM IV
            atm_call = calls.iloc[(calls["strike"] - spot_px).abs().argsort()[:1]]
            atm_put = puts.iloc[(puts["strike"] - spot_px).abs().argsort()[:1]]
            iv_call = float(atm_call["impliedVolatility"].values[0]) if not atm_call.empty else 0
            iv_put = float(atm_put["impliedVolatility"].values[0]) if not atm_put.empty else 0
            avg_iv = (iv_call + iv_put) / 2 if iv_call and iv_put else max(iv_call, iv_put)

            # Max Pain: strike with highest total OI
            all_oi = {}
            for _, row in calls.iterrows():
                s = float(row["strike"])
                oi = float(row.get("openInterest", 0) or 0)
                all_oi[s] = all_oi.get(s, 0) + oi
            for _, row in puts.iterrows():
                s = float(row["strike"])
                oi = float(row.get("openInterest", 0) or 0)
                all_oi[s] = all_oi.get(s, 0) + oi
            max_pain = max(all_oi.items(), key=lambda x: x[1])[0] if all_oi else spot_px

            # Put/Call ratio by volume
            call_vol = float(calls["volume"].sum()) if "volume" in calls.columns else 0
            put_vol = float(puts["volume"].sum()) if "volume" in puts.columns else 0
            pcr = put_vol / call_vol if call_vol > 0 else 1.0

            implied_move_pct = avg_iv * (30 / 365) ** 0.5 if avg_iv > 0 else 0.05

            if pcr > 1.2:
                delta_label = "Short 🔴"
            elif pcr < 0.8:
                delta_label = "Long 🟢"
            else:
                delta_label = "Neutral 🟡"

            if avg_iv > 0.30:
                gamma_label = "Long 🟢"
            elif avg_iv < 0.15:
                gamma_label = "Short 🔴"
            else:
                gamma_label = "Flat 🟡"

            if avg_iv > 0.25 and pcr < 0.9:
                vanna_label = "Positive ✅"
            elif avg_iv > 0.25 and pcr > 1.1:
                vanna_label = "Negative ⚠️"
            else:
                vanna_label = "Mixed 🟡"

            return {
                "ok": True,
                "source": "yfinance-options",
                "implied_move_pct": round(implied_move_pct, 4),
                "iv_percentile": 0.5,  # placeholder
                "max_pain": round(max_pain, 2),
                "put_call_ratio": round(pcr, 2),
                "iv": round(avg_iv, 4),
                "delta_label": delta_label,
                "gamma_label": gamma_label,
                "vanna_label": vanna_label,
            }
        except Exception as e:
            logger.warning(f"yfinance options fallback failed for {ticker}: {e}")
            return None

    def analyze(self, ticker: str, spot_px: Optional[float] = None) -> dict:
        """
        Analyze options for Forex or Commodity ticker.
        Priority: 1) yfinance ETF proxy  2) Proxy Greeks
        """
        # Try ETF proxy first (most reliable free source)
        proxy_ticker = ETF_PROXY.get(ticker)
        if proxy_ticker and spot_px and spot_px > 0:
            result = self._try_yfinance_options(proxy_ticker, spot_px)
            if result:
                result["mapped_from"] = ticker
                return result

        # If no ETF proxy, return proxy Greeks (app.py handles this)
        return {"ok": False, "reason": f"No options data source for {ticker}"}
