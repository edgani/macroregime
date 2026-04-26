"""engines/edgar_scraper_engine.py — 10/10 SEC Filing Parser

Parses 10-K Item 1 (Business) and Item 1A (Risk Factors) for:
  - Supply chain keywords
  - Market position language
  - Constraint indicators

FREE. Uses SEC EDGAR public API. Rate limit: 10 req/sec.
"""
from __future__ import annotations
import re
import time
import logging
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "MacroRegime Research macroregime@example.com"}

class EDGARScraperEngine:
    CONSTRAINT_PATTERNS = [
        r"sole\s+source", r"only\s+supplier", r"only\s+provider", r"dominant\s+market\s+share",
        r"market\s+leader", r"monopoly", r"duopoly", r"oligopoly", r"near[-\s]monopoly",
        r"industry\s+leader", r"leading\s+provider", r"largest\s+supplier", r"primary\s+supplier",
        r"exclusive\s+supplier", r"critical\s+supplier", r"single\s+source", r"limited\s+suppliers",
        r"supply\s+constrained", r"capacity\s+constrained", r"tight\s+supply", r"supply\s+shortage",
        r"bottleneck", r"chokepoint", r"indispensable", r"irreplaceable",
    ]
    RISK_PATTERNS = [
        r"shortage", r"supply\s+chain\s+disruption", r"constrained", r"lead\s+times\s+extended",
        r"backlog", r"order\s+backlog", r"demand\s+exceeds\s+supply", r"unable\s+to\s+meet\s+demand",
        r"capacity\s+expansion", r"ramping\s+production", r"supply\s+crunch",
    ]

    def __init__(self, cache_dir: str = ".cache/edgar"):
        self.cache_dir = cache_dir
        import os
        os.makedirs(cache_dir, exist_ok=True)

    def get_cik(self, ticker: str) -> Optional[str]:
        """Fetch CIK from SEC ticker lookup."""
        url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}&type=10-K&dateb=&owner=include&count=1"
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            m = re.search(r'CIK=(\d+)', r.text)
            if m:
                return m.group(1).zfill(10)
        except Exception as e:
            logger.warning(f"CIK lookup error for {ticker}: {e}")
        return None

    def get_latest_10k_url(self, cik: str) -> Optional[str]:
        """Get the latest 10-K filing detail page URL."""
        cik_padded = cik.zfill(10)
        url = f"https://data.sec.gov/submissions/CIK{cik_padded}.json"
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            data = r.json()
            filings = data.get("filings", {}).get("recent", {})
            forms = filings.get("form", [])
            for idx, form in enumerate(forms):
                if form == "10-K":
                    accession = filings["accessionNumber"][idx].replace("-", "")
                    return f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/"
        except Exception as e:
            logger.warning(f"10-K list error for CIK {cik}: {e}")
        return None

    def fetch_10k_text(self, filing_url: str) -> str:
        """Fetch and extract text from 10-K filing."""
        try:
            # Try to find the primary document
            r = requests.get(filing_url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(r.text, "html.parser")
            # Look for .htm or .txt link
            for a in soup.find_all("a"):
                href = a.get("href", "")
                if href.endswith(".htm") or href.endswith(".txt"):
                    if "index" not in href.lower():
                        doc_url = href if href.startswith("http") else f"https://www.sec.gov{href}"
                        dr = requests.get(doc_url, headers=HEADERS, timeout=20)
                        return BeautifulSoup(dr.text, "html.parser").get_text(separator=" ", strip=True)
            return soup.get_text(separator=" ", strip=True)
        except Exception as e:
            logger.warning(f"10-K fetch error: {e}")
            return ""

    def extract_items(self, text: str) -> Dict[str, str]:
        """Extract Item 1 and Item 1A from 10-K text."""
        text = text.replace("\n", " ").replace("\t", " ")
        items = {}
        # Item 1. Business
        m1 = re.search(r'ITEM\s*1[\.\s]+BUSINESS(.+?)ITEM\s*1A[\.\s]+RISK\s*FACTORS', text, re.IGNORECASE | re.DOTALL)
        if m1:
            items["item1_business"] = m1.group(1)[:8000]
        # Item 1A. Risk Factors
        m1a = re.search(r'ITEM\s*1A[\.\s]+RISK\s*FACTORS(.+?)ITEM\s*1B[\.\s]', text, re.IGNORECASE | re.DOTALL)
        if not m1a:
            m1a = re.search(r'ITEM\s*1A[\.\s]+RISK\s*FACTORS(.+?)ITEM\s*2[\.\s]', text, re.IGNORECASE | re.DOTALL)
        if m1a:
            items["item1a_risk"] = m1a.group(1)[:8000]
        return items

    def analyze_ticker(self, ticker: str) -> Dict[str, object]:
        """Full pipeline for one ticker."""
        cik = self.get_cik(ticker)
        if not cik:
            return {"ticker": ticker, "error": "CIK not found"}
        filing_url = self.get_latest_10k_url(cik)
        if not filing_url:
            return {"ticker": ticker, "error": "10-K not found"}
        text = self.fetch_10k_text(filing_url)
        if not text:
            return {"ticker": ticker, "error": "10-K text empty"}
        items = self.extract_items(text)
        if not items:
            return {"ticker": ticker, "error": "Items not extracted"}

        # Mine constraints
        all_text = " ".join(items.values()).lower()
        constraint_hits = []
        for pat in self.CONSTRAINT_PATTERNS:
            if re.search(pat, all_text):
                constraint_hits.append(pat)
        risk_hits = []
        for pat in self.RISK_PATTERNS:
            if re.search(pat, all_text):
                risk_hits.append(pat)

        # Score
        constraint_score = min(len(constraint_hits) * 0.12 + len(risk_hits) * 0.08, 1.0)

        # Extract suppliers / customers mentions
        supplier_mentions = re.findall(r'(?:supplier|vendor|provider)\s+([A-Z][A-Za-z\s]+?)(?:,|\.|;)', text)
        customer_mentions = re.findall(r'(?:customer|client)\s+([A-Z][A-Za-z\s]+?)(?:,|\.|;)', text)

        return {
            "ticker": ticker,
            "cik": cik,
            "filing_url": filing_url,
            "constraint_score": round(constraint_score, 2),
            "constraint_hits": list(set(constraint_hits)),
            "risk_hits": list(set(risk_hits)),
            "supplier_mentions": list(set(s.strip() for s in supplier_mentions))[:10],
            "customer_mentions": list(set(c.strip() for c in customer_mentions))[:10],
            "is_bottleneck_candidate": constraint_score >= 0.50,
            "text_snippet": all_text[:500] + "...",
        }

    def run(self, tickers: List[str]) -> Dict[str, object]:
        results = []
        for t in tickers:
            res = self.analyze_ticker(t)
            results.append(res)
            time.sleep(0.15)  # SEC rate limit: ~6-7 req/sec
        strong = [r for r in results if r.get("is_bottleneck_candidate")]
        return {
            "candidates": results,
            "strong_candidates": strong,
            "meta": {"tickers_scanned": len(tickers), "strong_count": len(strong)}
        }
