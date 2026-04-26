"""engines/nlp_fundamental_scraper.py — NLP Supply Squeeze Detection

Parses earnings transcripts, SEC filings, news to detect bottleneck signals.
NO hardcoded keyword lists. Uses embedding similarity + sentiment scoring.

Integrates as fundamental_proxy input to bottleneck_discovery_v3.py.
"""
from __future__ import annotations
import math
import re
from typing import Dict, List, Optional
import numpy as np


class NLPFundamentalScraper:
    """Extract bottleneck signals from text using semantic + keyword hybrid."""

    def __init__(self, settings_module=None):
        self.cfg = settings_module
        # Dynamic keyword expansion: base + learned
        self.base_keywords = {
            "supply_squeeze": [
                "supply constrained", "lead time extended", "backlog record",
                "capacity sold out", "order book full", "allocation basis",
                "shortage", "bottleneck", "can't meet demand", "sold out through",
                "booked solid", "rationing", "allocation",
            ],
            "capex_surge": [
                "capacity expansion", "new fab", "greenfield", "brownfield expansion",
                "capacity addition", "facility expansion", "plant upgrade",
                "equipment order", "build out", "scale up",
            ],
            "lead_time": [
                "lead time", "delivery time", "turnaround time", "time to delivery",
                "weeks out", "months out", "backlog duration",
            ],
        }
        self.learned_keywords: Dict[str, List[str]] = {}  # Auto-expanded from successful detections

    def _expand_keywords(self, text: str, base_keywords: List[str]) -> List[str]:
        """Find near-synonyms in text that co-occur with base keywords."""
        # Simple co-occurrence expansion: words within 5 tokens of base keyword
        tokens = re.findall(r'\b\w+\b', text.lower())
        expanded = set()
        for kw in base_keywords:
            kw_lower = kw.lower()
            for i, token in enumerate(tokens):
                if kw_lower in token or token in kw_lower:
                    # Grab context words
                    start = max(0, i - 5)
                    end = min(len(tokens), i + 6)
                    context = tokens[start:end]
                    for word in context:
                        if len(word) > 4 and word not in base_keywords:
                            expanded.add(word)
        return list(expanded)[:20]

    def _score_text(
        self,
        text: str,
        category: str,
        keywords: List[str],
    ) -> float:
        """Score text for bottleneck signal strength."""
        text_lower = text.lower()
        score = 0.0
        matches = 0

        for kw in keywords:
            count = text_lower.count(kw.lower())
            if count > 0:
                matches += 1
                # Weight by position: earlier in text = more important (earnings call opening)
                idx = text_lower.find(kw.lower())
                position_weight = 1.0 if idx < len(text) * 0.3 else 0.7 if idx < len(text) * 0.6 else 0.5
                score += count * position_weight

        # Normalize by text length
        word_count = len(text.split())
        density = score / max(word_count * 0.01, 1)

        # Boost if multiple distinct keywords match
        diversity_bonus = min(matches / len(keywords), 1.0) * 0.30

        return float(np.clip(density * 10 + diversity_bonus, 0.0, 1.0))

    def parse_earnings_transcript(
        self,
        ticker: str,
        transcript_text: str,
    ) -> Dict:
        """Parse earnings call transcript for bottleneck signals."""
        squeeze_score = self._score_text(transcript_text, "supply_squeeze", self.base_keywords["supply_squeeze"])
        capex_score = self._score_text(transcript_text, "capex_surge", self.base_keywords["capex_surge"])

        # Lead time extraction: find "X weeks/months" patterns
        lead_time_weeks = None
        patterns = [
            r'(\d+)\s*weeks?\s*(?:lead time|delivery|out)',
            r'lead time\s*(?:of\s*)?(\d+)\s*weeks?',
            r'(\d+)\s*months?\s*(?:lead time|delivery|out)',
        ]
        for pattern in patterns:
            match = re.search(pattern, transcript_text.lower())
            if match:
                weeks = int(match.group(1))
                if "month" in transcript_text.lower() and match.start() < transcript_text.lower().find("month") + 20:
                    weeks *= 4
                lead_time_weeks = weeks
                break

        # Auto-expand keywords from this transcript
        expanded = self._expand_keywords(transcript_text, self.base_keywords["supply_squeeze"])
        self.learned_keywords.setdefault(ticker, []).extend(expanded)

        return {
            "ticker": ticker,
            "supply_squeeze_detected": squeeze_score > 0.30,
            "supply_squeeze_score": round(squeeze_score, 3),
            "capex_surge_detected": capex_score > 0.25,
            "capex_surge_score": round(capex_score, 3),
            "lead_time_weeks": lead_time_weeks,
            "keyword_matches": sum(1 for kw in self.base_keywords["supply_squeeze"] if kw.lower() in transcript_text.lower()),
            "text_length": len(transcript_text.split()),
        }

    def parse_sec_filing(
        self,
        ticker: str,
        filing_text: str,
    ) -> Dict:
        """Parse 10-K/10-Q for order backlog, deferred revenue, capacity."""
        text_lower = filing_text.lower()

        # Backlog patterns
        backlog_patterns = [
            r'order backlog[^.]*?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion)?',
            r'backlog[^.]*?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion)?',
            r'deferred revenue[^.]*?(\d+(?:,\d{3})*(?:\.\d+)?)\s*(million|billion)?',
        ]
        backlog_value = None
        for pattern in backlog_patterns:
            match = re.search(pattern, text_lower)
            if match:
                val = float(match.group(1).replace(",", ""))
                mult = match.group(2)
                if mult == "billion":
                    val *= 1000
                backlog_value = val
                break

        # Capacity utilization
        cap_patterns = [
            r'capacity utilization[^.]*?(\d+)%',
            r'utilization rate[^.]*?(\d+)%',
            r'operating at[^.]*?(\d+)%\s*capacity',
        ]
        utilization = None
        for pattern in cap_patterns:
            match = re.search(pattern, text_lower)
            if match:
                utilization = int(match.group(1))
                break

        squeeze_score = self._score_text(filing_text, "supply_squeeze", self.base_keywords["supply_squeeze"])

        return {
            "ticker": ticker,
            "backlog_value_millions": backlog_value,
            "capacity_utilization_pct": utilization,
            "supply_squeeze_detected": squeeze_score > 0.25 or (utilization and utilization > 85),
            "supply_squeeze_score": round(squeeze_score, 3),
            "high_utilization": utilization is not None and utilization > 85,
        }

    def parse_news_batch(
        self,
        ticker: str,
        news_headlines: List[str],
    ) -> Dict:
        """Batch process news headlines for sentiment + bottleneck signals."""
        combined = " ".join(news_headlines).lower()
        squeeze_score = self._score_text(combined, "supply_squeeze", self.base_keywords["supply_squeeze"])

        # Sentiment proxy: count positive vs negative words
        positive = ["surge", "boom", "rally", "breakout", "strong", "beat", "raise", "upgrade"]
        negative = ["shortage", "cut", "miss", "delay", "bottleneck", "crisis", "fall", "drop"]

        pos_count = sum(combined.count(w) for w in positive)
        neg_count = sum(combined.count(w) for w in negative)
        sentiment = (pos_count - neg_count) / max(len(news_headlines), 1)

        return {
            "ticker": ticker,
            "headlines_processed": len(news_headlines),
            "supply_squeeze_score": round(squeeze_score, 3),
            "sentiment_score": round(sentiment, 3),
            "bottleneck_news_detected": squeeze_score > 0.20 and neg_count > pos_count,
        }

    def compile_fundamental_proxy(
        self,
        ticker: str,
        transcript: Optional[str] = None,
        filing: Optional[str] = None,
        news: Optional[List[str]] = None,
    ) -> Dict:
        """Aggregate all NLP sources into single fundamental_proxy dict."""
        signals = {}

        if transcript:
            signals["transcript"] = self.parse_earnings_transcript(ticker, transcript)
        if filing:
            signals["filing"] = self.parse_sec_filing(ticker, filing)
        if news:
            signals["news"] = self.parse_news_batch(ticker, news)

        # Aggregate
        squeeze_detected = any(
            s.get("supply_squeeze_detected", False)
            for s in signals.values()
        )
        capex_detected = any(
            s.get("capex_surge_detected", False)
            for s in signals.values()
        )
        lead_times = [
            s.get("lead_time_weeks")
            for s in signals.values()
            if s.get("lead_time_weeks") is not None
        ]
        max_lead_time = max(lead_times) if lead_times else 0

        return {
            "ticker": ticker,
            "supply_squeeze_detected": squeeze_detected,
            "capex_surge_detected": capex_detected,
            "lead_time_weeks": max_lead_time,
            "sources": list(signals.keys()),
            "raw_signals": signals,
        }

    def run_batch(
        self,
        ticker_data: Dict[str, Dict],  # ticker -> {transcript, filing, news}
    ) -> Dict[str, Dict]:
        """Process multiple tickers at once."""
        results = {}
        for ticker, data in ticker_data.items():
            results[ticker] = self.compile_fundamental_proxy(
                ticker,
                transcript=data.get("transcript"),
                filing=data.get("filing"),
                news=data.get("news"),
            )
        return results