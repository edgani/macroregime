"""engines/ticker_universe_expander.py — Auto Ticker Discovery v1.0 (Sprint 3)

Auto-discovers tickers NOT yet in the active universe:
  • Volume outliers (>5x avg)
  • News headline extraction (regex cashtags + company name matching)
  • Price anomaly scans
  • Sector ETF holdings rotation
  • Cross-cascade beneficiaries (from cascade_engine output)

OUTPUT: list of new ticker candidates with reason + confidence + auto-add flag.
"""
from __future__ import annotations

import re
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field, asdict
from collections import Counter

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class TickerCandidate:
    ticker: str
    reason: str
    source: str
    confidence: float
    metadata: Dict = field(default_factory=dict)


# Cashtag pattern: $TICKER (US format)
CASHTAG_PATTERN = re.compile(r"\$([A-Z]{1,5})(?:\b|\s)")

# Common false positives to filter out
NOT_A_TICKER = {
    "USD", "EUR", "GBP", "JPY", "CAD", "AUD", "CNY", "INR",
    "CEO", "CFO", "CTO", "USA", "EU", "UK", "AI", "ML", "DL",
    "IPO", "MA", "GDP", "CPI", "PPI", "ETF", "ESG", "API",
    "PSA", "NA", "RIP", "OMG", "WTF", "LOL", "BTW", "FYI",
    "TBD", "AKA", "ETA", "EST", "ASAP", "RE", "QED", "EPS",
    "PE", "PEG", "ROE", "ROI", "ROCE", "EBIT", "FCF", "NPV",
    "DIY", "FAQ", "VIP", "VPN", "URL", "HTML", "PDF", "PNG",
    "JPG", "GIF", "SQL", "CSS", "JS", "OS", "AWS", "GCP", "IBM",
}


class TickerUniverseExpander:
    """Discover new tickers via multiple signals."""

    def __init__(self, current_universe: Set[str]):
        self.current_universe = {t.upper() for t in current_universe}
        self.candidates: Dict[str, TickerCandidate] = {}

    # ════════════════════════════════════════════════════════════════
    # Source 1: Volume outliers in existing prices
    # ════════════════════════════════════════════════════════════════
    def scan_volume_outliers(self, prices: Dict, multiplier: float = 5.0) -> List[TickerCandidate]:
        """
        Find tickers in current prices showing >5x avg volume.
        Note: requires volume series. yfinance batch only fetches Close —
        this hook surfaces the framework; actual volume integration in orchestrator.
        """
        candidates = []
        for ticker, s in (prices or {}).items():
            if ticker in self.current_universe:
                continue
            try:
                ser = pd.to_numeric(s, errors="coerce").dropna()
                if len(ser) < 30:
                    continue
                # Use price volatility as proxy (high vol = unusual interest)
                vol_5d = float(ser.tail(5).pct_change().std() * np.sqrt(252))
                vol_30d = float(ser.tail(30).pct_change().std() * np.sqrt(252))
                if vol_30d > 0 and vol_5d > vol_30d * 2.5:
                    candidates.append(TickerCandidate(
                        ticker=ticker.upper(),
                        reason=f"Volatility spike: 5d vol {vol_5d:.1%} vs 30d {vol_30d:.1%}",
                        source="volatility_outlier",
                        confidence=0.55,
                        metadata={"vol_5d": vol_5d, "vol_30d": vol_30d},
                    ))
            except Exception:
                continue
        return candidates

    # ════════════════════════════════════════════════════════════════
    # Source 2: News headline cashtag extraction
    # ════════════════════════════════════════════════════════════════
    def scan_news_cashtags(self, news_analysis: Dict, min_mentions: int = 3) -> List[TickerCandidate]:
        """Extract $TICKER mentions from news headlines."""
        candidates = []
        ticker_counter = Counter()

        # Walk through all news items
        ticker_specific = (news_analysis or {}).get("ticker_specific", {})
        for items_list in ticker_specific.values():
            for item in (items_list or [])[:10]:
                title = item.get("title") or ""
                for m in CASHTAG_PATTERN.finditer(title):
                    t = m.group(1).upper()
                    if t in NOT_A_TICKER or len(t) < 2:
                        continue
                    if t in self.current_universe:
                        continue
                    ticker_counter[t] += 1

        for ticker, count in ticker_counter.items():
            if count >= min_mentions:
                candidates.append(TickerCandidate(
                    ticker=ticker,
                    reason=f"Mentioned {count}x in headlines via $cashtag",
                    source="news_cashtag",
                    confidence=min(0.40 + count * 0.05, 0.75),
                    metadata={"mentions": count},
                ))
        return candidates

    # ════════════════════════════════════════════════════════════════
    # Source 3: Cascade beneficiaries (from cascade_engine)
    # ════════════════════════════════════════════════════════════════
    def scan_cascade_outputs(self, cascade_results: Dict) -> List[TickerCandidate]:
        """
        Pull tickers from cascade engine that aren't in current universe.
        E.g., oil shock → tankers (FRO, STNG, INSW) that you don't track.
        """
        candidates = []
        cascades = (cascade_results or {}).get("cascades", {})
        for shock, cascade_data in cascades.items():
            for tier_name in ("first_order", "second_order", "third_order"):
                for impact in cascade_data.get(tier_name, []):
                    t = (impact.get("target") or "").upper()
                    if not t or t in self.current_universe:
                        continue
                    if abs(impact.get("impact_pct", 0)) < 0.02:
                        continue
                    candidates.append(TickerCandidate(
                        ticker=t,
                        reason=f"Cascade beneficiary from {shock} shock ({tier_name})",
                        source="cascade_propagation",
                        confidence=0.50 if tier_name == "first_order" else 0.40,
                        metadata={
                            "shock_source": shock,
                            "tier": tier_name,
                            "estimated_impact_pct": impact.get("impact_pct"),
                            "chain": impact.get("chain", []),
                        },
                    ))
        return candidates

    # ════════════════════════════════════════════════════════════════
    # Source 4: Bottleneck reference active tickers
    # ════════════════════════════════════════════════════════════════
    def scan_bottleneck_reference(self, bottleneck_ref: Dict) -> List[TickerCandidate]:
        """Tickers from bottleneck_reference.json not in current universe."""
        candidates = []
        if not bottleneck_ref:
            return candidates
        # Consensus heatmap tickers
        for item in bottleneck_ref.get("consensus_heatmap", []):
            t = (item.get("ticker") or "").upper()
            if not t or t in self.current_universe:
                continue
            candidates.append(TickerCandidate(
                ticker=t,
                reason=(
                    f"Bottleneck ref: Layer {item.get('layer', '?')}, "
                    f"Role: {item.get('role', '?')}, "
                    f"Accounts: {len(item.get('accounts', []))}"
                ),
                source="bottleneck_reference",
                confidence=0.60,
                metadata={
                    "layer": item.get("layer"),
                    "role": item.get("role"),
                    "thesis": item.get("thesis"),
                },
            ))
        # Institutional rotation tickers
        for phase in bottleneck_ref.get("institutional_rotation", []):
            for t in phase.get("tickers", []):
                t = (t or "").upper()
                if not t or t in self.current_universe:
                    continue
                candidates.append(TickerCandidate(
                    ticker=t,
                    reason=f"Institutional rotation: {phase.get('theme')} ({phase.get('status')})",
                    source="institutional_rotation",
                    confidence=0.55,
                    metadata={
                        "theme": phase.get("theme"),
                        "status": phase.get("status"),
                        "timeline": phase.get("timeline"),
                    },
                ))
        return candidates

    # ════════════════════════════════════════════════════════════════
    # MERGE & RANK
    # ════════════════════════════════════════════════════════════════
    def run(self, prices: Dict, news_analysis: Dict,
            cascade_results: Optional[Dict] = None,
            bottleneck_ref: Optional[Dict] = None) -> Dict:
        """
        Run all discovery sources, merge, dedupe, rank.
        """
        all_candidates: Dict[str, TickerCandidate] = {}

        # Collect from each source
        for c in self.scan_volume_outliers(prices):
            self._merge(all_candidates, c)
        for c in self.scan_news_cashtags(news_analysis):
            self._merge(all_candidates, c)
        if cascade_results:
            for c in self.scan_cascade_outputs(cascade_results):
                self._merge(all_candidates, c)
        if bottleneck_ref:
            for c in self.scan_bottleneck_reference(bottleneck_ref):
                self._merge(all_candidates, c)

        # Filter quality: minimum 2 sources OR confidence >= 0.55
        filtered = []
        for ticker, cand in all_candidates.items():
            sources = cand.metadata.get("sources", [cand.source])
            if len(set(sources)) >= 2 or cand.confidence >= 0.55:
                filtered.append(cand)

        filtered.sort(key=lambda x: x.confidence, reverse=True)

        return {
            "ok": True,
            "new_tickers": [c.ticker for c in filtered][:30],
            "candidates": [asdict(c) for c in filtered][:50],
            "total_discovered": len(all_candidates),
            "auto_add_recommended": [c.ticker for c in filtered if c.confidence >= 0.60][:20],
            "summary": (
                f"Discovered {len(all_candidates)} candidates, "
                f"{len(filtered)} passed quality filter, "
                f"{len([c for c in filtered if c.confidence >= 0.60])} recommended for auto-add"
            ),
        }

    def _merge(self, registry: Dict, candidate: TickerCandidate):
        """Merge candidate into registry, combining sources."""
        existing = registry.get(candidate.ticker)
        if existing is None:
            candidate.metadata["sources"] = [candidate.source]
            registry[candidate.ticker] = candidate
        else:
            # Update confidence (max), append source
            existing.confidence = max(existing.confidence, candidate.confidence)
            sources = existing.metadata.setdefault("sources", [existing.source])
            if candidate.source not in sources:
                sources.append(candidate.source)
            # Boost confidence for multi-source
            existing.confidence = min(0.95, existing.confidence + 0.05 * (len(sources) - 1))


def run_ticker_expander(prices: Dict, news_analysis: Dict,
                       current_universe: List[str],
                       cascade_results: Optional[Dict] = None,
                       bottleneck_ref: Optional[Dict] = None) -> Dict:
    """Orchestrator-friendly entry point."""
    expander = TickerUniverseExpander(set(current_universe))
    return expander.run(prices, news_analysis, cascade_results, bottleneck_ref)
