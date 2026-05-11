"""engines/cot_scraper.py — Real CFTC COT Report Parser
Downloads and parses the latest CFTC Disaggregated Futures-Only COT report.
Maps tickers to CFTC market names for automatic lookup.
"""
import requests
import pandas as pd
import io
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)

# CFTC Disaggregated Futures-Only report (latest)
CFTC_URL = "https://www.cftc.gov/dea/newcot/DeaCtyFXOF.txt"
# Backup: legacy combined report
CFTC_LEGACY_URL = "https://www.cftc.gov/dea/futures/deacmesf.htm"

# Ticker → CFTC Market Name substring mapping
TICKER_COT_MAP = {
    # Commodities
    "GC=F": "GOLD", "GLD": "GOLD", "SI=F": "SILVER", "SLV": "SILVER",
    "HG=F": "COPPER", "PL=F": "PLATINUM", "PA=F": "PALLADIUM",
    "CL=F": "CRUDE OIL", "USO": "CRUDE OIL", "BZ=F": "BRENT", "BNO": "BRENT",
    "NG=F": "NATURAL GAS", "UNL": "NATURAL GAS", "HO=F": "NY HARBOR", "RB=F": "GASOLINE",
    "ZW=F": "WHEAT", "ZC=F": "CORN", "ZS=F": "SOYBEANS", "ZL=F": "SOYBEAN OIL",
    "ALI=F": "ALUMINUM", "LBS=F": "LUMBER",
    # FX
    "DX-Y.NYB": "DOLLAR INDEX", "UUP": "DOLLAR INDEX",
    "EURUSD=X": "EURO FX", "EUR=": "EURO FX",
    "GBPUSD=X": "BRITISH POUND", "GBP=": "BRITISH POUND",
    "JPYUSD=X": "JAPANESE YEN", "JPY=": "JAPANESE YEN",
    "AUDUSD=X": "AUSTRALIAN DOLLAR", "AUD=": "AUSTRALIAN DOLLAR",
    "CADUSD=X": "CANADIAN DOLLAR", "CAD=": "CANADIAN DOLLAR",
    "CHFUSD=X": "SWISS FRANC", "CHF=": "SWISS FRANC",
    "NZDUSD=X": "NEW ZEALAND DOLLAR", "NZD=": "NEW ZEALAND DOLLAR",
    "MXNUSD=X": "MEXICAN PESO", "MXN=": "MEXICAN PESO",
    "BRLUSD=X": "BRAZILIAN REAL", "BRL=": "BRAZILIAN REAL",
    # Financials
    "ZN=F": "10-YEAR NOTES", "ZT=F": "2-YEAR NOTES", "ZB=F": "30-YEAR BONDS",
    "ZF=F": "5-YEAR NOTES", "ZQ=F": "30-DAY FED FUNDS",
    "ES=F": "E-MINI S&P 500", "NQ=F": "E-MINI NASDAQ-100", "YM=F": "DJIA",
    "RTY=F": "E-MINI RUSSELL 2000",
    # Crypto (CME Bitcoin/Ether futures)
    "BTC-USD": "BITCOIN", "ETH-USD": "ETHER",
}


class CFTCCOTScraper:
    """Scraper + parser for CFTC Disaggregated Commitment of Traders reports."""

    def __init__(self, cache_hours: int = 6):
        self.cache_hours = cache_hours
        self._last_fetch: Optional[datetime] = None
        self._records: List[Dict] = []
        self._df: Optional[pd.DataFrame] = None

    def _fetch_text(self) -> str:
        """Download the latest CFTC disaggregated futures-only report."""
        try:
            resp = requests.get(CFTC_URL, timeout=30)
            resp.raise_for_status()
            logger.info(f"CFTC COT fetched: {len(resp.text)} chars")
            return resp.text
        except Exception as e:
            logger.warning(f"CFTC primary URL failed: {e}, trying legacy...")
            try:
                resp = requests.get(CFTC_LEGACY_URL, timeout=30)
                resp.raise_for_status()
                return resp.text
            except Exception as e2:
                logger.error(f"CFTC legacy URL also failed: {e2}")
                return ""

    def _parse_fixed_width(self, text: str) -> List[Dict]:
        """Parse CFTC fixed-width text format into records."""
        lines = text.strip().splitlines()
        records = []
        current_market = None
        current_exchange = None
        current_date = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Market/Exchange header lines start with market name
            # The disaggregated format has sections per market
            # Format: Market_and_Exchange_Names, As_of_Date, etc.
            # This is a simplified parser — CFTC format changes occasionally

            # Detect date line
            if "As of" in line or "As_of" in line:
                try:
                    # Extract date from line
                    parts = line.split()
                    for p in parts:
                        if len(p) == 8 and p.isdigit():
                            current_date = datetime.strptime(p, "%Y%m%d").strftime("%Y-%m-%d")
                        elif "/" in p and len(p) <= 10:
                            try:
                                current_date = datetime.strptime(p, "%m/%d/%Y").strftime("%Y-%m-%d")
                            except:
                                pass
                except:
                    pass
                continue

            # Detect market name (usually first substantive line of a record block)
            # In the disaggregated format, records are separated by blank lines
            # and the market name is on its own line or starts a block
            if len(line) > 10 and not line[0].isdigit() and "," not in line[:20]:
                current_market = line.strip()
                continue

            # Try to parse data lines with numeric fields
            # Disaggregated format columns (approximate positions):
            # Non-Commercial Long, Non-Commercial Short, Non-Commercial Spreading
            # Commercial Long, Commercial Short
            # Non-Reportable Long, Non-Reportable Short
            try:
                # Split by multiple spaces
                parts = [p for p in line.split() if p]
                if len(parts) >= 7:
                    # Try to identify if this is a data row by checking for numbers
                    nums = [p.replace(",", "").replace(".", "").lstrip("-") for p in parts]
                    if all(n.isdigit() for n in nums[:7]):
                        rec = {
                            "market": current_market or "UNKNOWN",
                            "date": current_date,
                            "noncomm_long": int(parts[0].replace(",", "")),
                            "noncomm_short": int(parts[1].replace(",", "")),
                            "noncomm_spread": int(parts[2].replace(",", "")),
                            "comm_long": int(parts[3].replace(",", "")),
                            "comm_short": int(parts[4].replace(",", "")),
                            "nonrep_long": int(parts[5].replace(",", "")),
                            "nonrep_short": int(parts[6].replace(",", "")),
                        }
                        records.append(rec)
            except Exception:
                continue

        return records

    def _enrich_metrics(self, records: List[Dict]) -> List[Dict]:
        """Add computed metrics to each record."""
        for r in records:
            nc_long = r.get("noncomm_long", 0)
            nc_short = r.get("noncomm_short", 0)
            c_long = r.get("comm_long", 0)
            c_short = r.get("comm_short", 0)
            total_long = nc_long + c_long + r.get("nonrep_long", 0)
            total_short = nc_short + c_short + r.get("nonrep_short", 0)

            # Net positions
            nc_net = nc_long - nc_short
            c_net = c_long - c_short

            # Ratios
            nc_ratio = nc_long / max(nc_short, 1)
            c_ratio = c_long / max(c_short, 1)

            # Bias
            if nc_net > 0 and c_net < 0:
                bias = "Bullish"  # Speculators long, commercials short (hedging) = bullish
            elif nc_net < 0 and c_net > 0:
                bias = "Bearish"
            else:
                bias = "Neutral"

            # Commercial signal (smart money)
            if c_net > 0 and abs(c_net) > abs(nc_net) * 0.5:
                comm_signal = "Accumulation 🟢"
            elif c_net < 0 and abs(c_net) > abs(nc_net) * 0.5:
                comm_signal = "Distribution 🔴"
            else:
                comm_signal = "Neutral ⚪"

            r.update({
                "nc_net": nc_net,
                "c_net": c_net,
                "nc_ratio": round(nc_ratio, 2),
                "c_ratio": round(c_ratio, 2),
                "bias": bias,
                "commercial_signal": comm_signal,
                "total_oi": total_long + total_short,
            })
        return records

    def refresh(self) -> bool:
        """Fetch and parse latest COT report. Returns True if successful."""
        text = self._fetch_text()
        if not text:
            return False
        records = self._parse_fixed_width(text)
        if not records:
            logger.warning("COT parser returned 0 records — format may have changed.")
            return False
        self._records = self._enrich_metrics(records)
        self._df = pd.DataFrame(self._records)
        self._last_fetch = datetime.now()
        logger.info(f"COT parsed: {len(self._records)} markets")
        return True

    def _ensure_loaded(self):
        if self._last_fetch is None or (datetime.now() - self._last_fetch) > timedelta(hours=self.cache_hours):
            self.refresh()

    def get_all(self) -> pd.DataFrame:
        self._ensure_loaded()
        return self._df.copy() if self._df is not None else pd.DataFrame()

    def get_by_name(self, name_substring: str) -> Optional[Dict]:
        """Lookup by market name substring (case-insensitive)."""
        self._ensure_loaded()
        if self._df is None or self._df.empty:
            return None
        mask = self._df["market"].str.contains(name_substring, case=False, na=False)
        matches = self._df[mask]
        if matches.empty:
            return None
        # Return the first match as dict
        return matches.iloc[0].to_dict()

    def get_by_ticker(self, ticker: str) -> Optional[Dict]:
        """Lookup by our ticker symbol using the mapping table."""
        name_key = TICKER_COT_MAP.get(ticker, ticker)
        return self.get_by_name(name_key)

    def analyze(self, ticker: str, prices=None, vix: float = 20) -> Dict:
        """Orchestrator-compatible interface. Returns enriched COT analysis."""
        data = self.get_by_ticker(ticker)
        if data is None:
            return {"ok": False, "reason": f"No COT data for {ticker}"}

        nc_net = data.get("nc_net", 0)
        c_net = data.get("c_net", 0)
        bias = data.get("bias", "Neutral")
        comm_sig = data.get("commercial_signal", "Neutral ⚪")

        # Signal construction
        if bias == "Bullish" and "Accumulation" in comm_sig:
            signal = "🟢 STRONG BULLISH — Spec + Comm aligned long"
        elif bias == "Bearish" and "Distribution" in comm_sig:
            signal = "🔴 STRONG BEARISH — Spec + Comm aligned short"
        elif bias == "Bullish":
            signal = "🟡 BULLISH — Speculators net long"
        elif bias == "Bearish":
            signal = "🟡 BEARISH — Speculators net short"
        else:
            signal = "⚪ NEUTRAL — No clear COT edge"

        return {
            "ok": True,
            "ticker": ticker,
            "market": data.get("market"),
            "date": data.get("date"),
            "bias": bias,
            "commercial_label": comm_sig,
            "noncommercial_label": f"Net {'Long' if nc_net > 0 else 'Short'} {abs(nc_net):,}",
            "signal": signal,
            "nc_net": nc_net,
            "c_net": c_net,
            "nc_ratio": data.get("nc_ratio"),
            "c_ratio": data.get("c_ratio"),
            "total_oi": data.get("total_oi"),
            "source": "CFTC COT (LIVE)",
        }


# Singleton for orchestrator import
cot_scraper = CFTCCOTScraper()


def analyze(ticker: str, prices=None, vix: float = 20) -> Dict:
    """Convenience function for orchestrator import."""
    return cot_scraper.analyze(ticker, prices, vix)
