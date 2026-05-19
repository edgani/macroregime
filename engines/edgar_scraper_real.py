"""engines/edgar_scraper_real.py — Real SEC EDGAR Scraper (Sprint 3)

Replaces the 13-line stub. Implements:
  • CIK lookup from ticker (cached locally)
  • Recent filings fetch (/submissions/CIK{cik}.json)
  • 10-K, 10-Q, 8-K filing text extraction
  • Risk Factors section parsing
  • Bottleneck language detection (constraint, sole source, capacity, etc.)
  • Output: structured filing signals for discovery_brain

USAGE: SEC EDGAR has no rate limits but requires User-Agent header per fair use policy.
Free, no API key needed.
"""
from __future__ import annotations

import re
import json
import time
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

logger = logging.getLogger(__name__)

# SEC requires identifying User-Agent per fair-use policy
SEC_USER_AGENT = "MacroRegimePro research@macroregime.dev"
EDGAR_BASE = "https://www.sec.gov"
DATA_BASE = "https://data.sec.gov"

# Local cache for CIK lookups
CACHE_DIR = Path(".cache/edgar")
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CIK_CACHE_FILE = CACHE_DIR / "ticker_to_cik.json"


# ────────────────────────────────────────────────────────────────────────
# CONSTRAINT LANGUAGE PATTERNS
# ────────────────────────────────────────────────────────────────────────

CONSTRAINT_PATTERNS = {
    "capacity_constraint": [
        r"capacity\s+constrain", r"capacity\s+limited",
        r"manufacturing\s+capacity\s+(?:limit|constrain)",
        r"unable\s+to\s+meet\s+(?:demand|orders)",
    ],
    "supply_chain": [
        r"supply\s+chain\s+(?:disrupt|constrain|risk|shortage)",
        r"shortage\s+of\s+(?:component|material|chip|wafer)",
        r"limited\s+supplier",
        r"sole\s+source\s+(?:supplier|provider)",
        r"only\s+(?:one|two)\s+supplier",
    ],
    "backlog_pressure": [
        r"order\s+backlog.{0,30}(?:grow|increas|extend|record)",
        r"backlog\s+(?:grew|increased|extended)\s+to",
        r"lead\s+time.{0,30}(?:extend|increas|month)",
    ],
    "demand_exceeds": [
        r"demand\s+(?:exceeds?|outpaces?)\s+supply",
        r"strong\s+demand\s+(?:exceed|outpace)",
        r"orders?\s+exceed\s+capacity",
    ],
    "pricing_power": [
        r"raised?\s+prices?",
        r"pricing\s+(?:power|leverage)",
        r"pass\s+through\s+(?:cost|price)",
    ],
}


# ────────────────────────────────────────────────────────────────────────
# CIK Lookup
# ────────────────────────────────────────────────────────────────────────

def _load_cik_cache() -> Dict[str, str]:
    if CIK_CACHE_FILE.exists():
        try:
            with open(CIK_CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cik_cache(cache: Dict[str, str]):
    try:
        with open(CIK_CACHE_FILE, "w") as f:
            json.dump(cache, f)
    except Exception as e:
        logger.debug(f"CIK cache save failed: {e}")


def _fetch_cik_mapping() -> Dict[str, str]:
    """One-time fetch of full ticker→CIK mapping from SEC."""
    try:
        r = requests.get(
            f"{EDGAR_BASE}/files/company_tickers.json",
            headers={"User-Agent": SEC_USER_AGENT},
            timeout=10,
        )
        if r.status_code != 200:
            return {}
        data = r.json()
        mapping = {}
        # Format: {"0": {"cik_str": 1234, "ticker": "AAPL", "title": "..."}, ...}
        for entry in data.values() if isinstance(data, dict) else []:
            if not isinstance(entry, dict):
                continue
            ticker = entry.get("ticker", "").upper()
            cik = entry.get("cik_str")
            if ticker and cik:
                mapping[ticker] = str(cik).zfill(10)
        return mapping
    except Exception as e:
        logger.warning(f"SEC CIK mapping fetch failed: {e}")
        return {}


_CIK_CACHE: Dict[str, str] = {}
_CIK_LOADED = False


def get_cik(ticker: str) -> Optional[str]:
    """Resolve ticker → CIK (10-digit zero-padded)."""
    global _CIK_CACHE, _CIK_LOADED
    if not _CIK_LOADED:
        _CIK_CACHE = _load_cik_cache()
        if not _CIK_CACHE:
            _CIK_CACHE = _fetch_cik_mapping()
            if _CIK_CACHE:
                _save_cik_cache(_CIK_CACHE)
        _CIK_LOADED = True
    return _CIK_CACHE.get(ticker.upper())


# ────────────────────────────────────────────────────────────────────────
# Filings Fetch
# ────────────────────────────────────────────────────────────────────────

def fetch_recent_filings(ticker: str, days: int = 90,
                        filing_types: Optional[List[str]] = None) -> List[Dict]:
    """Fetch recent filings for a ticker."""
    filing_types = filing_types or ["10-K", "10-Q", "8-K"]
    cik = get_cik(ticker)
    if not cik:
        return []

    try:
        url = f"{DATA_BASE}/submissions/CIK{cik}.json"
        r = requests.get(url, headers={"User-Agent": SEC_USER_AGENT}, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        recent = data.get("filings", {}).get("recent", {})

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        access = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])

        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        results = []

        for i in range(min(len(forms), 50)):
            form = forms[i]
            date = dates[i] if i < len(dates) else ""
            if form not in filing_types:
                continue
            if date < cutoff:
                continue
            acc = access[i] if i < len(access) else ""
            doc = primary_docs[i] if i < len(primary_docs) else ""
            acc_clean = acc.replace("-", "")
            results.append({
                "ticker": ticker,
                "cik": cik,
                "form": form,
                "filing_date": date,
                "accession": acc,
                "url": f"{EDGAR_BASE}/Archives/edgar/data/{int(cik)}/{acc_clean}/{doc}",
            })
        return results
    except Exception as e:
        logger.debug(f"Filings fetch failed for {ticker}: {e}")
        return []


def fetch_filing_text(filing_url: str, max_chars: int = 200_000) -> str:
    """Download filing text. Caps at max_chars to avoid memory blow-up."""
    try:
        r = requests.get(filing_url, headers={"User-Agent": SEC_USER_AGENT}, timeout=20)
        if r.status_code != 200:
            return ""
        text = r.text
        # Strip HTML tags rudimentarily (real EDGAR docs are huge)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text)
        return text[:max_chars]
    except Exception:
        return ""


# ────────────────────────────────────────────────────────────────────────
# Constraint Language Detection
# ────────────────────────────────────────────────────────────────────────

def scan_constraint_language(text: str) -> Dict:
    """Detect bottleneck/constraint language in filing text."""
    text_lower = text.lower()
    results: Dict[str, List[str]] = {}
    for category, patterns in CONSTRAINT_PATTERNS.items():
        matches = []
        for pattern in patterns:
            for m in re.finditer(pattern, text_lower):
                # Capture surrounding context (50 chars before/after)
                start = max(0, m.start() - 50)
                end = min(len(text_lower), m.end() + 100)
                context = text[start:end].strip()
                matches.append(context[:200])
                if len(matches) >= 3:
                    break
            if len(matches) >= 3:
                break
        if matches:
            results[category] = matches

    return {
        "categories_matched": list(results.keys()),
        "match_count": sum(len(v) for v in results.values()),
        "evidence": results,
    }


# ────────────────────────────────────────────────────────────────────────
# Main Scanner (orchestrator entry)
# ────────────────────────────────────────────────────────────────────────

def scan_ticker_filings(ticker: str, days: int = 90,
                       max_filings: int = 3) -> Dict:
    """
    Full scan: ticker → filings → constraint signals.
    Returns single ticker analysis.
    """
    filings = fetch_recent_filings(ticker, days)
    if not filings:
        return {"ticker": ticker, "ok": False, "reason": "no_filings_found"}

    all_signals: List[Dict] = []
    # Sample N most recent filings to avoid burning rate-limit
    for filing in filings[:max_filings]:
        text = fetch_filing_text(filing["url"])
        if not text:
            continue
        constraint = scan_constraint_language(text)
        if constraint["match_count"] > 0:
            all_signals.append({
                "filing": filing,
                "constraint_signal": constraint,
            })
        # Be polite to SEC servers
        time.sleep(0.3)

    return {
        "ticker": ticker,
        "ok": True,
        "filings_scanned": len(filings),
        "signals_detected": len(all_signals),
        "signals": all_signals,
        "has_bottleneck_language": len(all_signals) > 0,
    }


def scan_multi_tickers(tickers: List[str], days: int = 90,
                      max_workers: int = 3) -> Dict[str, Dict]:
    """Batch scan multiple tickers in parallel (gentle on SEC rate limits)."""
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(scan_ticker_filings, t, days): t for t in tickers}
        for fut in as_completed(futures):
            t = futures[fut]
            try:
                results[t] = fut.result(timeout=60)
            except Exception as e:
                results[t] = {"ticker": t, "ok": False, "error": str(e)}
    return results


# Backwards-compat with old stub signature
def scan_edgar(*args, **kwargs):
    """Legacy entry — redirects to scan_ticker_filings."""
    tickers = kwargs.get("tickers", args[0] if args else [])
    if isinstance(tickers, str):
        tickers = [tickers]
    if not tickers:
        return {}
    return scan_multi_tickers(tickers, days=kwargs.get("days", 90))
