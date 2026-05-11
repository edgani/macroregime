"""engines/cme_scraper.py — CME Group FX & Commodities Data
Scrapes delayed quotes and settlement data from CME Group website.
Falls back to yfinance for continuous futures proxies.
"""
import requests
import pandas as pd
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# CME public quotes API (discovered endpoints — may need updating)
CME_QUOTE_API = "https://www.cmegroup.com/CmeWS/mvc/Quotes/Future/{code}/G"

# Product code mapping for CME futures
CME_PRODUCT_MAP = {
    # FX
    "EURUSD=X": {"code": "437", "name": "Euro FX", "yfin": "EURUSD=X"},
    "GBPUSD=X": {"code": "438", "name": "British Pound", "yfin": "GBPUSD=X"},
    "JPYUSD=X": {"code": "442", "name": "Japanese Yen", "yfin": "JPYUSD=X"},
    "AUDUSD=X": {"code": "443", "name": "Australian Dollar", "yfin": "AUDUSD=X"},
    "CADUSD=X": {"code": "444", "name": "Canadian Dollar", "yfin": "CADUSD=X"},
    "CHFUSD=X": {"code": "445", "name": "Swiss Franc", "yfin": "CHFUSD=X"},
    "NZDUSD=X": {"code": "446", "name": "New Zealand Dollar", "yfin": "NZDUSD=X"},
    "MXNUSD=X": {"code": "447", "name": "Mexican Peso", "yfin": "MXNUSD=X"},
    "BRLUSD=X": {"code": "448", "name": "Brazilian Real", "yfin": "BRLUSD=X"},
    # Commodities
    "GC=F": {"code": "458", "name": "Gold", "yfin": "GC=F"},
    "SI=F": {"code": "459", "name": "Silver", "yfin": "SI=F"},
    "HG=F": {"code": "460", "name": "Copper", "yfin": "HG=F"},
    "PL=F": {"code": "461", "name": "Platinum", "yfin": "PL=F"},
    "PA=F": {"code": "462", "name": "Palladium", "yfin": "PA=F"},
    "CL=F": {"code": "425", "name": "Crude Oil WTI", "yfin": "CL=F"},
    "NG=F": {"code": "426", "name": "Natural Gas", "yfin": "NG=F"},
    "RB=F": {"code": "429", "name": "RBOB Gasoline", "yfin": "RB=F"},
    "HO=F": {"code": "428", "name": "NY Harbor ULSD", "yfin": "HO=F"},
    "ZC=F": {"code": "12", "name": "Corn", "yfin": "ZC=F"},
    "ZS=F": {"code": "13", "name": "Soybeans", "yfin": "ZS=F"},
    "ZW=F": {"code": "14", "name": "Chicago Wheat", "yfin": "ZW=F"},
    "ZL=F": {"code": "15", "name": "Soybean Oil", "yfin": "ZL=F"},
    "ZM=F": {"code": "16", "name": "Soybean Meal", "yfin": "ZM=F"},
    "DX-Y.NYB": {"code": "449", "name": "US Dollar Index", "yfin": "DX-Y.NYB"},
}


class CMEScraper:
    """CME Group delayed quotes scraper."""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}  # (timestamp, data)
        self.cache_ttl = timedelta(minutes=30)

    def _fetch_cme_quote(self, code: str) -> Optional[Dict]:
        """Try to fetch from CME public API."""
        url = CME_QUOTE_API.format(code=code)
        try:
            resp = requests.get(url, timeout=15, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json",
            })
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    quote = data[0]
                    return {
                        "last": quote.get("last"),
                        "open": quote.get("open"),
                        "high": quote.get("high"),
                        "low": quote.get("low"),
                        "settle": quote.get("settle"),
                        "volume": quote.get("volume"),
                        "oi": quote.get("openInterest"),
                        "change": quote.get("change"),
                        "pct_change": quote.get("pctChange"),
                        "source": "CME",
                    }
        except Exception as e:
            logger.debug(f"CME API fetch failed for code {code}: {e}")
        return None

    def _fetch_yf_fallback(self, ticker: str) -> Optional[Dict]:
        """Fallback to yfinance for continuous futures."""
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            hist = t.history(period="5d")
            if hist.empty:
                return None
            last = hist["Close"].iloc[-1]
            prev = hist["Close"].iloc[-2] if len(hist) > 1 else last
            change = last - prev
            pct = change / prev if prev else 0
            return {
                "last": round(last, 4),
                "change": round(change, 4),
                "pct_change": round(pct, 4),
                "volume": int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else None,
                "source": "yfinance (CME fallback)",
            }
        except Exception as e:
            logger.debug(f"yfinance fallback failed for {ticker}: {e}")
            return None

    def get_quote(self, ticker: str) -> Optional[Dict]:
        """Get best available quote for a CME-mapped ticker."""
        now = datetime.now()
        if ticker in self._cache:
            ts, data = self._cache[ticker]
            if (now - ts) < self.cache_ttl:
                return data

        meta = CME_PRODUCT_MAP.get(ticker)
        if not meta:
            return None

        # Try CME first
        result = self._fetch_cme_quote(meta["code"])
        if result is None:
            result = self._fetch_yf_fallback(meta["yfin"])

        if result:
            result["ticker"] = ticker
            result["name"] = meta["name"]
            self._cache[ticker] = (now, result)
        return result

    def analyze(self, ticker: str, prices=None, vix: float = 20) -> Dict:
        """Orchestrator-compatible interface for FX/Commodities."""
        quote = self.get_quote(ticker)
        if quote is None:
            return {"ok": False, "reason": f"No CME data for {ticker}"}

        # Determine bias from change
        change = quote.get("change", 0) or 0
        pct = quote.get("pct_change", 0) or 0
        if pct > 0.005:
            bias = "Bullish"; delta = "Bullish 📈"
        elif pct < -0.005:
            bias = "Bearish"; delta = "Bearish 📉"
        else:
            bias = "Neutral"; delta = "Neutral ↔"

        # Volume/OI proxy
        vol = quote.get("volume", 0) or 0
        oi = quote.get("oi", 0) or 0
        vol_oi_note = "High activity" if vol > 100000 else "Normal"

        return {
            "ok": True,
            "ticker": ticker,
            "last": quote.get("last"),
            "change": change,
            "pct_change": pct,
            "volume": vol,
            "open_interest": oi,
            "bias": bias,
            "delta": delta,
            "signal": f"{bias} — {quote.get('name', ticker)} {pct:+.2%}",
            "source": quote.get("source", "CME/yfinance"),
        }

    def analyze_multi(self, tickers: List[str], prices=None, vix: float = 20) -> Dict[str, Dict]:
        results = {}
        for t in tickers:
            try:
                r = self.analyze(t, prices, vix)
                if r.get("ok"):
                    results[t] = r
            except Exception as e:
                logger.warning(f"CME analysis failed for {t}: {e}")
        return results


# Singleton
cme_scraper = CMEScraper()


def analyze(ticker: str, prices=None, vix: float = 20) -> Dict:
    return cme_scraper.analyze(ticker, prices, vix)


def analyze_multi(tickers: List[str], prices=None, vix: float = 20) -> Dict[str, Dict]:
    return cme_scraper.analyze_multi(tickers, prices, vix)
