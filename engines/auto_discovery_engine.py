"""engines/auto_discovery_engine.py v1 — True Autonomous Discovery

Integrates:
  - PriceClusterEngine (L1: what's moving together)
  - NewsNLPEngine (L2: why it's moving)
  - SupplyChainLightEngine (L3: is it a bottleneck)

Outputs:
  - new bottleneck dict entries (ready to append to KNOWN_BOTTLENECKS)
  - new narrative themes (ready to append to NARRATIVES)
  - new transition implications (from recent realized regime paths)
"""
from __future__ import annotations
import json
import math
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

from engines.price_cluster_engine import PriceClusterEngine
from engines.news_nlp_engine import NewsNLPEngine
from engines.supply_chain_light_engine import SupplyChainLightEngine

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryCandidate:
    name: str
    category: str  # "bottleneck" | "narrative" | "transition"
    stage: str   # "active" | "building" | "brewing"
    thesis: str
    confidence: float
    source_signals: List[str] = field(default_factory=list)
    beneficiary_tickers: List[str] = field(default_factory=list)
    fade_tickers: List[str] = field(default_factory=list)
    confirmation_signal: str = ""
    invalidators: List[str] = field(default_factory=list)
    regime_fit: float = 0.5
    pump_risk: float = 0.5
    discovered_at: str = ""

class AutoDiscoveryEngine:
    """
    The core autonomy engine. No Claude API. No external AI.
    Pure integration of price, news, and fundamental signals.
    """

    def __init__(self, sector_map, market_map, known_tickers, use_transformers=True):
        self.cluster_engine = PriceClusterEngine(sector_map, market_map)
        self.news_engine = NewsNLPEngine(use_transformers=use_transformers, known_tickers=known_tickers)
        self.supply_engine = SupplyChainLightEngine(news_engine=self.news_engine)
        self.known_tickers = known_tickers

    def run(
        self,
        prices: Dict[str, object],
        structural_quad: str,
        monthly_quad: str,
        gip_features: Dict[str, float],
        theme_queries: Optional[List[str]] = None,
    ) -> Dict[str, object]:
        t0 = time.time()

        # ── L1: Price Clusters ────────────────────────────────────────
        clusters = self.cluster_engine.run(prices, benchmark="SPY", lookback=63)

        # ── L2: News NLP ──────────────────────────────────────────────
        # Query news for: (a) cluster members, (b) top outperformers, (c) theme queries
        query_tickers = []
        for c in clusters.get("clusters", []):
            query_tickers.extend(c["members"])
        # Add top individual outperformers
        # (simplified: use cluster members as proxy)
        query_tickers = list(dict.fromkeys(query_tickers))[:30]  # max 30 to avoid RSS overload

        news_queries = theme_queries or self._auto_theme_queries(structural_quad, monthly_quad)
        news_results = self.news_engine.run(query_tickers, theme_queries=news_queries)

        # ── L3: Supply Chain Signals ──────────────────────────────────
        supply_results = self.supply_engine.run(query_tickers, prices, news_results)

        # ── L4: Integrate & Generate Candidates ──────────────────────
        candidates = []

        # 4A: Bottleneck candidates from supply chain + price confirmation
        for sc in supply_results.get("strong_candidates", []):
            ticker = sc["ticker"]
            # Cross-check: is this ticker in a price cluster?
            in_cluster = None
            for c in clusters.get("clusters", []):
                if ticker in c["members"]:
                    in_cluster = c
                    break
            
            if in_cluster:
                conf = min(sc["constraint_score"] * 1.2, 1.0)
                candidates.append(DiscoveryCandidate(
                    name=f"{ticker} structural bottleneck",
                    category="bottleneck",
                    stage="active" if in_cluster["avg_rs_3m"] > 0.15 else "building",
                    thesis=sc["thesis"] + f" Confirmed by price cluster with {in_cluster['member_count']} peers.",
                    confidence=round(conf, 2),
                    source_signals=["supply_chain", "price_cluster"],
                    beneficiary_tickers=[ticker],
                    confirmation_signal=f"{ticker} RS 3M > 5% + supply chain news mentions increasing",
                    invalidators=["Supply constraint resolves", "Competitor enters market", "Demand collapse"],
                    regime_fit=self._regime_fit_bottleneck(ticker, structural_quad),
                    discovered_at=time.strftime("%Y-%m-%d %H:%M"),
                ))

        # 4B: Narrative candidates from price clusters + news validation
        for c in clusters.get("clusters", []):
            if not c.get("is_novel_theme"):
                continue  # skip sector-pure clusters (already known)
            
            # Validate with news: does this cluster have news coverage?
            cluster_news_count = 0
            cluster_supply_hits = 0
            for t in c["members"]:
                t_news = news_results.get("ticker_specific", {}).get(t, [])
                cluster_news_count += len(t_news)
                for ni in t_news:
                    if hasattr(ni, 'supply_chain_mentions') and len(ni.supply_chain_mentions) > 0:
                        cluster_supply_hits += 1

            # If news validates → real narrative
            if cluster_news_count >= 3:
                conf = min(c["confidence"] + 0.15, 1.0)
                candidates.append(DiscoveryCandidate(
                    name=c["theme_hypothesis"],
                    category="narrative",
                    stage="active" if c["avg_rs_3m"] > 0.10 else "building",
                    thesis=f"Cross-sector cluster detected: {', '.join(c['members'][:5])}. "
                          f"News validation: {cluster_news_count} articles. Supply mentions: {cluster_supply_hits}.",
                    confidence=round(conf, 2),
                    source_signals=["price_cluster", "news_validation"],
                    beneficiary_tickers=c["members"],
                    confirmation_signal="Cluster RS sustained 3M + news volume increasing",
                    invalidators=["Cluster correlation breaks", "News volume drops", "Lead ticker breaks TREND LRR"],
                    regime_fit=self._regime_fit_narrative(c["dominant_sector"], structural_quad),
                    discovered_at=time.strftime("%Y-%m-%d %H:%M"),
                ))

        # 4C: New themes from news NLP (not from price clusters)
        for nt in news_results.get("new_theme_candidates", []):
            candidates.append(DiscoveryCandidate(
                name=nt.get("suggested_theme_name", "unknown_theme"),
                category="narrative",
                stage="brewing",
                thesis=f"Emergent theme from news clustering: {', '.join(nt.get('shared_keywords', [])[:5])}. "
                      f"Sample: {nt.get('sample_headlines', [''])[0]}",
                confidence=0.45,
                source_signals=["news_clustering"],
                beneficiary_tickers=[],
                confirmation_signal="Keyword frequency increasing in news + price cluster forms",
                invalidators=["Headlines revert to old themes", "No price confirmation"],
                discovered_at=time.strftime("%Y-%m-%d %H:%M"),
            ))

        # 4D: Transition implications from current regime + early warning
        transition_candidates = self._discover_transitions(structural_quad, monthly_quad, gip_features)
        candidates.extend(transition_candidates)

        # ── Output ─────────────────────────────────────────────────────
        return {
            "candidates": [self._candidate_to_dict(c) for c in candidates],
            "bottlenecks": [self._candidate_to_dict(c) for c in candidates if c.category == "bottleneck"],
            "narratives": [self._candidate_to_dict(c) for c in candidates if c.category == "narrative"],
            "transitions": [self._candidate_to_dict(c) for c in candidates if c.category == "transition"],
            "meta": {
                "clusters_found": len(clusters.get("clusters", [])),
                "news_analyzed": news_results.get("analyzed_count", 0),
                "supply_candidates": len(supply_results.get("strong_candidates", [])),
                "total_candidates": len(candidates),
                "build_time_s": round(time.time() - t0, 1),
            }
        }

    def _auto_theme_queries(self, sq, mq):
        """Generate news queries based on current regime."""
        queries = []
        if sq == "Q3" or mq == "Q3":
            queries.extend(["gold shortage central bank", "defensive stocks healthcare utilities", "stagflation supply chain"])
        if sq == "Q2" or mq == "Q2":
            queries.extend(["commodity shortage", "energy bottleneck", "inflation supply constraint"])
        if sq == "Q4" or mq == "Q4":
            queries.extend(["deflation recession", "bond rally flight to quality", "credit stress"])
        if sq == "Q1" or mq == "Q1":
            queries.extend(["tech breakout AI", "growth rebound", "small cap rally"])
        queries.extend(["supply chain bottleneck", "shortage constrained", "data center power"])
        return queries

    def _regime_fit_bottleneck(self, ticker, quad):
        # Simple proxy: use sector map to look up profile
        from config.settings import BOTTLENECK_PROFILES, TICKER_SECTOR
        sector = TICKER_SECTOR.get(ticker, "generic")
        prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES["generic"])
        return float(prof.get(quad, 0.5))

    def _regime_fit_narrative(self, sector, quad):
        # Proxy from bottleneck profiles
        from config.settings import BOTTLENECK_PROFILES
        prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES["generic"])
        return float(prof.get(quad, 0.5))

    def _discover_transitions(self, sq, mq, features):
        """Auto-generate transition implications from realized paths."""
        candidates = []
        # If monthly diverges from structural → transition building
        if sq != mq:
            path = f"{sq}→{mq}"
            g_mom = features.get("growth_momentum", 0)
            i_mom = features.get("inflation_momentum", 0)
            
            # Auto-generate thesis from feature directions
            if g_mom > 0.05 and i_mom > 0.05:
                thesis = f"Growth re-accelerating + inflation rising = {sq}→Q2 path building"
                best = ["XLE","XLB","XLI","Commodities"]; worst = ["TLT","XLU"]
            elif g_mom < -0.05 and i_mom < -0.05:
                thesis = f"Growth decelerating + inflation falling = {sq}→Q4 path building"
                best = ["TLT","XLV","XLP","XLU"]; worst = ["XLK","XLY","IWM"]
            elif g_mom > 0.05 and i_mom < -0.05:
                thesis = f"Goldilocks recovery signal = {sq}→Q1 path building"
                best = ["SPY","QQQ","XLK","XLY","IWM"]; worst = ["GLD","XLE"]
            elif g_mom < -0.05 and i_mom > 0.05:
                thesis = f"Stagflation pressure intensifying = {sq}→Q3 path building"
                best = ["GLD","XLV","XLP"]; worst = ["XLK","XLY","HYG"]
            else:
                thesis = f"Mixed signals = {sq}→{mq} monthly divergence, structural holds"
                best = []; worst = []

            candidates.append(DiscoveryCandidate(
                name=path,
                category="transition",
                stage="building",
                thesis=thesis,
                confidence=0.55,
                source_signals=["gip_features", "monthly_divergence"],
                beneficiary_tickers=best,
                fade_tickers=worst,
                confirmation_signal="Monthly data confirms direction for 2+ months",
                invalidators=["Macro data reverses", "Fed policy surprise"],
                regime_fit=0.6,
                discovered_at=time.strftime("%Y-%m-%d %H:%M"),
            ))
        return candidates

    def _candidate_to_dict(self, c: DiscoveryCandidate):
        return {
            "name": c.name,
            "category": c.category,
            "stage": c.stage,
            "thesis": c.thesis,
            "confidence": c.confidence,
            "source_signals": c.source_signals,
            "beneficiary_tickers": c.beneficiary_tickers,
            "fade_tickers": c.fade_tickers,
            "confirmation_signal": c.confirmation_signal,
            "invalidators": c.invalidators,
            "regime_fit": c.regime_fit,
            "pump_risk": c.pump_risk,
            "discovered_at": c.discovered_at,
        }