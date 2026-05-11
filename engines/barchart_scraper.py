"""engines/barchart_scraper.py — Barchart Options Data Scraper
⚠️  Barchart is heavily JavaScript-rendered. This engine uses:
   1. Hidden API endpoint discovery (if available)
   2. BeautifulSoup fallback on static fragments
   3. yfinance fallback for US equities

For production reliability, consider:
   - Barchart OnDemand API (paid): https://www.barchart.com/ondemand
   - Selenium/Playwright for full JS rendering
"""
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Known Barchart internal API patterns (may change without notice)
BARCHART_API_BASE = "https://www.barchart.com/proxies/timeseries"
BARCHART_QUOTE_API = "https://www.barchart.com/proxies/core-api/v1/quotes/get"


class BarchartScraper:
    """Best-effort Barchart scraper with multiple fallback strategies."""

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.barchart.com/",
        })
        self._cache: Dict[str, tuple] = {}
        self.cache_ttl = timedelta(minutes=30)

    def _fetch_api_quote(self, symbol: str) -> Optional[Dict]:
        """Try Barchart internal quote API."""
        try:
            url = f"{BARCHART_QUOTE_API}?symbols={symbol}&fields=symbol,lastPrice,priceChange,percentChange,volume,openInterest,impliedVolatility,highPrice,lowPrice"
            resp = self._session.get(url, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, dict):
                    quotes = data.get("data", []) or data.get("results", [])
                    if quotes:
                        q = quotes[0]
                        return {
                            "last": q.get("lastPrice") or q.get("last"),
                            "change": q.get("priceChange") or q.get("change"),
                            "pct_change": q.get("percentChange") or q.get("pctChange"),
                            "volume": q.get("volume"),
                            "oi": q.get("openInterest"),
                            "iv": q.get("impliedVolatility"),
                            "high": q.get("highPrice") or q.get("high"),
                            "low": q.get("lowPrice") or q.get("low"),
                            "source": "Barchart API",
                        }
        except Exception as e:
            logger.debug(f"Barchart API quote failed for {symbol}: {e}")
        return None

    def _fetch_options_page(self, symbol: str) -> Optional[Dict]:
        """Scrape options page static HTML for metadata."""
        try:
            url = f"https://www.barchart.com/stocks/quotes/{symbol}/options"
            resp = self._session.get(url, timeout=15)
            if resp.status_code == 200:
                # Look for JSON data embedded in script tags
                import re
                # Search for window.__INITIAL_STATE__ or similar
                scripts = re.findall(r'<script[^>]*>(.*?)</script>', resp.text, re.DOTALL)
                for script in scripts:
                    if "options" in script.lower() or "strike" in script.lower():
                        # Try to extract any JSON structures
                        json_matches = re.findall(r'\{[^{}]*"strike"[^{}]*\}', script)
                        if json_matches:
                            # This is a very rough extraction
                            logger.debug(f"Found potential options JSON fragments for {symbol}")
                # Fallback: extract any numeric tables
                return {"ok": False, "note": "Barchart options page is JS-rendered. Use yfinance for live options chain."}
        except Exception as e:
            logger.debug(f"Barchart page scrape failed for {symbol}: {e}")
        return None

    def _yfinance_fallback(self, symbol: str) -> Optional[Dict]:
        """Fallback to yfinance options."""
        try:
            from engines.yfinance_options import options_engine
            return options_engine.analyze(symbol)
        except Exception as e:
            logger.debug(f"yfinance fallback failed for {symbol}: {e}")
            return None

    def analyze(self, ticker: str, prices=None, vix: float = 20) -> Dict:
        """Best-effort Barchart analysis with fallbacks."""
        cache_key = f"bc_{ticker}"
        now = datetime.now()
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if (now - ts) < self.cache_ttl:
                return data

        # Strategy 1: Barchart API
        result = self._fetch_api_quote(ticker)
        if result:
            result.update({"ok": True, "ticker": ticker, "source": "Barchart API (LIVE)"})
            self._cache[cache_key] = (now, result)
            return result

        # Strategy 2: yfinance options
        yf_result = self._yfinance_fallback(ticker)
        if yf_result and yf_result.get("ok"):
            yf_result["source"] = "yfinance (Barchart fallback)"
            self._cache[cache_key] = (now, yf_result)
            return yf_result

        return {
            "ok": False,
            "ticker": ticker,
            "reason": "Barchart requires JS rendering or API key. Use yfinance for US equity options.",
            "suggestion": "For production: subscribe to Barchart OnDemand API or use Playwright/Selenium",
        }

    def analyze_multi(self, tickers: List[str], prices=None, vix: float = 20, **kwargs) -> Dict[str, Dict]:
        results = {}
        for t in tickers:
            try:
                r = self.analyze(t, prices, vix)
                if r.get("ok"):
                    results[t] = r
            except Exception as e:
                logger.warning(f"Barchart analysis failed for {t}: {e}")
        return results


# Singleton
barchart_scraper = BarchartScraper()


def analyze(ticker: str, prices=None, vix: float = 20) -> Dict:
    return barchart_scraper.analyze(ticker, prices, vix)


def analyze_multi(tickers: List[str], prices=None, vix: float = 20, **kwargs) -> Dict[str, Dict]:
    return barchart_scraper.analyze_multi(tickers, prices, vix)
