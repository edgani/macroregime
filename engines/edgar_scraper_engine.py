"""engines/edgar_scraper_engine.py — minimal EDGARScraperEngine stub.
Placeholder for SEC 10-K parsing (bottleneck/supply-chain discovery from filings).
Returns empty result set until full SEC API integration is implemented.
"""
from __future__ import annotations


class EDGARScraperEngine:
    def __init__(self, *args, **kwargs):
        pass

    def run(self, tickers):
        return {"candidates": [], "strong_candidates": []}
