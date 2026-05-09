"""engines/barchart_options.py — Barchart Options Scraper (US Stocks + ETFs)
Scrapes implied volatility, max pain, put/call ratio from Barchart options page.
NOTE: Fragile — Barchart may change DOM or block scrapers. Use with fallback.
"""
from __future__ import annotations
import requests
import logging
from typing import Optional
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)

class BarchartOptionsScraper:
    """
    Scrape options data from Barchart for US-listed tickers.
    Supports: SPY, QQQ, GLD, SLV, XLE, OIH, IBIT, etc.
    """
    def __init__(self, timeout: int = 12):
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
        })

    def _fetch(self, ticker: str) -> Optional[str]:
        url = f"https://www.barchart.com/stocks/quotes/{ticker}/options"
        try:
            r = self.session.get(url, timeout=self.timeout)
            if r.status_code != 200:
                logger.warning(f"Barchart {ticker}: HTTP {r.status_code}")
                return None
            return r.text
        except Exception as e:
            logger.warning(f"Barchart {ticker} fetch error: {e}")
            return None

    def _extract_iv(self, html: str) -> float:
        """Extract implied volatility from page text."""
        # Look for patterns like "Implied Volatility: 23.45%" or "IV: 23.45"
        patterns = [
            r'Implied Volatility[:\s]+(\d+\.?\d*)\s*%?',
            r'IV\s*[:\s]+(\d+\.?\d*)\s*%?',
            r'"impliedVolatility"\s*:\s*(\d+\.?\d*)',
            r'"iv"\s*:\s*(\d+\.?\d*)',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                val = float(m.group(1))
                return val / 100.0 if val > 1.0 else val  # normalize to decimal
        return 0.0

    def _extract_max_pain(self, html: str) -> float:
        """Extract max pain strike from page text."""
        patterns = [
            r'Max[\s\-]?Pain[:\s]+\$?(\d+\.?\d*)',
            r'max_pain[:\s]+\$?(\d+\.?\d*)',
            r'"maxPain"\s*:\s*(\d+\.?\d*)',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return float(m.group(1))
        # Fallback: parse from soup if table exists
        try:
            soup = BeautifulSoup(html, "html.parser")
            for td in soup.find_all("td"):
                txt = td.get_text(strip=True)
                if "max pain" in txt.lower() or "maxpain" in txt.lower():
                    nxt = td.find_next_sibling()
                    if nxt:
                        return float(re.sub(r"[^\d.]", "", nxt.get_text()))
        except Exception:
            pass
        return 0.0

    def _extract_put_call_ratio(self, html: str) -> float:
        """Extract put/call ratio."""
        patterns = [
            r'Put/Call\s*Ratio[:\s]+(\d+\.?\d*)',
            r'put_call_ratio[:\s]+(\d+\.?\d*)',
            r'"putCallRatio"\s*:\s*(\d+\.?\d*)',
        ]
        for pat in patterns:
            m = re.search(pat, html, re.IGNORECASE)
            if m:
                return float(m.group(1))
        return 1.0

    def analyze(self, ticker: str, spot_px: Optional[float] = None) -> dict:
        """
        Analyze options for a US ticker. Returns dict compatible with app.py.
        """
        html = self._fetch(ticker)
        if not html:
            return {"ok": False, "reason": f"Barchart fetch failed for {ticker}"}

        iv = self._extract_iv(html)
        max_pain = self._extract_max_pain(html)
        pcr = self._extract_put_call_ratio(html)

        if iv <= 0 and max_pain <= 0:
            return {"ok": False, "reason": "No options data parsed"}

        # IV percentile proxy: compare to historical range (we dont have history, so use heuristic)
        iv_percentile = 0.5  # neutral placeholder
        if iv > 0.35:
            iv_percentile = 0.85
        elif iv > 0.25:
            iv_percentile = 0.65
        elif iv < 0.15:
            iv_percentile = 0.15

        # Implied move: IV * sqrt(30/365) ≈ monthly move
        implied_move_pct = iv * (30 / 365) ** 0.5 if iv > 0 else 0.05

        # Greeks proxy from IV + put/call ratio
        if pcr > 1.2:
            delta_label = "Short 🔴"  # puts dominant = bearish skew
        elif pcr < 0.8:
            delta_label = "Long 🟢"   # calls dominant = bullish skew
        else:
            delta_label = "Neutral 🟡"

        # Gamma proxy: high IV usually = high gamma environment
        if iv > 0.30:
            gamma_label = "Long 🟢"
        elif iv < 0.15:
            gamma_label = "Short 🔴"
        else:
            gamma_label = "Flat 🟡"

        # Vanna: if IV high + calls dominant = positive vanna (vol up = delta up)
        if iv > 0.25 and pcr < 0.9:
            vanna_label = "Positive ✅"
        elif iv > 0.25 and pcr > 1.1:
            vanna_label = "Negative ⚠️"
        else:
            vanna_label = "Mixed 🟡"

        return {
            "ok": True,
            "source": "Barchart",
            "implied_move_pct": round(implied_move_pct, 4),
            "iv_percentile": round(iv_percentile, 2),
            "max_pain": round(max_pain, 2) if max_pain > 0 else None,
            "put_call_ratio": round(pcr, 2),
            "iv": round(iv, 4),
            "delta_label": delta_label,
            "gamma_label": gamma_label,
            "vanna_label": vanna_label,
        }
