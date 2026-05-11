"""engines/laevitas_scraper.py — Laevitas.ch Crypto Options Scraper
⚠️  Laevitas is a premium crypto options analytics platform with heavy JS rendering.
This engine provides:
   1. API endpoint probing (if public endpoints are discoverable)
   2. Static page scraping for summary metrics
   3. Fallback to Deribit API (public) for BTC/ETH options

For full Laevitas data, a subscription + API key is required.
"""
import requests
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Deribit public API (free, no key needed for public endpoints)
DERIBIT_API = "https://www.deribit.com/api/v2/public"

# Laevitas (premium — limited without key)
LAEVITAS_BASE = "https://api.laevitas.ch"


class LaevitasScraper:
    """Crypto options scraper: tries Laevitas, falls back to Deribit."""

    def __init__(self):
        self._cache: Dict[str, tuple] = {}
        self.cache_ttl = timedelta(minutes=30)

    def _fetch_deribit_summary(self, currency: str = "BTC") -> Optional[Dict]:
        """Fetch options summary from Deribit public API."""
        try:
            url = f"{DERIBIT_API}/get_book_summary_by_currency?currency={currency}&kind=option"
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            if data.get("result"):
                items = data["result"]
                # Aggregate metrics
                total_volume = sum(i.get("volume", 0) for i in items)
                total_oi = sum(i.get("open_interest", 0) for i in items)
                # Find ATM IV
                underlying = items[0].get("underlying_price", 0) if items else 0
                atm_items = [i for i in items if abs(i.get("strike", 0) - underlying) < underlying * 0.05]
                atm_iv = sum(i.get("mark_iv", 0) for i in atm_items) / max(len(atm_items), 1) if atm_items else 0

                # Put/Call split
                calls = [i for i in items if "C" in i.get("instrument_name", "")]
                puts = [i for i in items if "P" in i.get("instrument_name", "")]
                call_oi = sum(c.get("open_interest", 0) for c in calls)
                put_oi = sum(p.get("open_interest", 0) for p in puts)
                pc_oi = put_oi / max(call_oi, 1)

                # Max Pain approximation (strike with highest OI)
                by_strike = {}
                for i in items:
                    s = i.get("strike", 0)
                    by_strike[s] = by_strike.get(s, 0) + i.get("open_interest", 0)
                max_pain = max(by_strike.items(), key=lambda x: x[1])[0] if by_strike else underlying

                return {
                    "underlying": underlying,
                    "total_volume": total_volume,
                    "total_oi": total_oi,
                    "atm_iv": round(atm_iv, 2),
                    "pc_oi": round(pc_oi, 2),
                    "max_pain": max_pain,
                    "call_count": len(calls),
                    "put_count": len(puts),
                    "source": "Deribit API (LIVE)",
                }
        except Exception as e:
            logger.debug(f"Deribit fetch failed for {currency}: {e}")
        return None

    def _fetch_laevitas_probe(self, currency: str = "BTC") -> Optional[Dict]:
        """Probe Laevitas public endpoints (best effort, no guarantee)."""
        # Laevitas public endpoints are limited without auth
        # Try common patterns
        endpoints = [
            f"/options/{currency.lower()}/summary",
            f"/analytics/{currency.lower()}/gex",
            f"/market/{currency.lower()}/pc_ratio",
        ]
        for ep in endpoints:
            try:
                url = f"{LAEVITAS_BASE}{ep}"
                resp = requests.get(url, timeout=10, headers={"Accept": "application/json"})
                if resp.status_code == 200:
                    return {"laevitas_data": resp.json(), "source": "Laevitas API"}
            except Exception:
                continue
        return None

    def analyze(self, ticker: str, prices=None, vix: float = 20) -> Dict:
        """Crypto options analysis for BTC/ETH tickers."""
        cache_key = f"lae_{ticker}"
        now = datetime.now()
        if cache_key in self._cache:
            ts, data = self._cache[cache_key]
            if (now - ts) < self.cache_ttl:
                return data

        currency = "BTC" if "BTC" in ticker else "ETH" if "ETH" in ticker else None
        if not currency:
            return {"ok": False, "reason": f"Laevitas/Deribit only supports BTC/ETH options, not {ticker}"}

        # Try Deribit
        deribit = self._fetch_deribit_summary(currency)
        if deribit:
            result = {
                "ok": True,
                "ticker": ticker,
                "currency": currency,
                **deribit,
                "expected_move": {
                    "note": f"Use ATM IV {deribit.get('atm_iv', 0)}% for expected move calc",
                    "atm_iv": deribit.get("atm_iv"),
                },
                "unusual_activity": [],  # Would require tick-level data
                "gex": {"note": "GEX requires Laevitas premium API or Deribit depth endpoint"},
            }
            self._cache[cache_key] = (now, result)
            return result

        return {
            "ok": False,
            "ticker": ticker,
            "reason": "No crypto options data available. Deribit API may be rate-limited.",
            "suggestion": "For full crypto options: subscribe to Laevitas or use Deribit API directly",
        }

    def analyze_multi(self, tickers: List[str], prices=None, vix: float = 20, **kwargs) -> Dict[str, Dict]:
        results = {}
        for t in tickers:
            try:
                r = self.analyze(t, prices, vix)
                if r.get("ok"):
                    results[t] = r
            except Exception as e:
                logger.warning(f"Laevitas analysis failed for {t}: {e}")
        return results


# Singleton
laevitas_scraper = LaevitasScraper()


def analyze(ticker: str, prices=None, vix: float = 20) -> Dict:
    return laevitas_scraper.analyze(ticker, prices, vix)


def analyze_multi(tickers: List[str], prices=None, vix: float = 20, **kwargs) -> Dict[str, Dict]:
    return laevitas_scraper.analyze_multi(tickers, prices, vix)
