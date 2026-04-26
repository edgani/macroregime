"""engines/auto_discovery_engine_v3.py — 10/10 Autonomous Discovery Brain

Integrates ALL L1-L4 signals into actionable candidates:
  L1: PriceClusterEngineV3 — what's moving together
  L2: NewsNLPEngineV3 — why it's moving  
  L3: EDGARScraperEngine + SupplyChainGraphEngine — is it a real bottleneck
  L4: LeadingIndicatorEngine + RegimePredictorEngine — forward forecast

Outputs candidates ready for FeedbackLoopEngine.
"""
from __future__ import annotations
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

from engines.price_cluster_engine_v3 import PriceClusterEngineV3
from engines.news_nlp_engine_v3 import NewsNLPEngineV3
from engines.edgar_scraper_engine import EDGARScraperEngine
from engines.supply_chain_graph_engine import SupplyChainGraphEngine
from engines.leading_indicator_engine import LeadingIndicatorEngine
from engines.regime_predictor_engine import RegimePredictorEngine

logger = logging.getLogger(__name__)

@dataclass
class DiscoveryCandidate:
    name: str
    category: str
    stage: str
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
    forward_return_expectation: Dict[str, float] = field(default_factory=dict)
    transition_forecast: Dict[str, object] = field(default_factory=dict)

class AutoDiscoveryEngineV3:
    def __init__(self, sector_map, market_map, known_tickers, use_transformers=True):
        self.cluster_engine = PriceClusterEngineV3(sector_map, market_map)
        self.news_engine = NewsNLPEngineV3(use_transformers=use_transformers, known_tickers=known_tickers)
        self.edgar_engine = EDGARScraperEngine()
        self.graph_engine = SupplyChainGraphEngine(sector_map, market_map)
        self.leading_engine = LeadingIndicatorEngine()
        self.regime_predictor = RegimePredictorEngine()
        self.known_tickers = known_tickers

    def run(self, prices, structural_quad, monthly_quad, gip_features,
            theme_queries=None, run_edgar=True) -> Dict[str, object]:
        t0 = time.time()

        # L1: Price Clusters
        clusters = self.cluster_engine.run(prices, benchmark="SPY", lookback=63)

        # L2: News NLP
        query_tickers = []
        for c in clusters.get("clusters", []):
            query_tickers.extend(c["members"])
        query_tickers = list(dict.fromkeys(query_tickers))[:30]
        news_queries = theme_queries or self._auto_queries(structural_quad, monthly_quad)
        news_results = self.news_engine.run(query_tickers, theme_queries=news_queries)

        # L3a: EDGAR (optional, slower)
        edgar_results = {"candidates": [], "strong_candidates": []}
        if run_edgar and len(query_tickers) <= 20:
            try:
                edgar_results = self.edgar_engine.run(query_tickers)
            except Exception as e:
                logger.warning(f"EDGAR error: {e}")

        # L3b: Supply Chain Graph
        graph_results = self.graph_engine.build_graph(edgar_results, news_results, clusters, prices)

        # L4: Forward prediction
        trans_forecast = self.regime_predictor.predict(structural_quad, gip_features, months_forward=3)
        self.leading_engine.fit([])  # placeholder; real fit needs historical_snapshots
        forward_ret = self.leading_engine.predict_forward_return(gip_features, structural_quad)

        # Integrate: generate candidates
        candidates = []

        # 4A: Bottlenecks from graph centrality + EDGAR + price confirmation
        for b in graph_results.get("bottlenecks", [])[:15]:
            ticker = b["ticker"]
            # Cross-check with price cluster
            in_cluster = None
            for c in clusters.get("clusters", []):
                if ticker in c["members"]:
                    in_cluster = c
                    break

            conf = min(b["bottleneck_score"] * 1.1, 1.0)
            if in_cluster:
                conf = min(conf + 0.1, 1.0)

            candidates.append(DiscoveryCandidate(
                name=f"{ticker} structural bottleneck",
                category="bottleneck",
                stage="active" if (in_cluster and in_cluster["avg_rs_3m"] > 0.10) else "building",
                thesis=b["thesis"] + (f" Confirmed by price cluster with {in_cluster['member_count']} peers." if in_cluster else ""),
                confidence=round(conf, 2),
                source_signals=["supply_chain_graph", "edgar"] + (["price_cluster"] if in_cluster else []),
                beneficiary_tickers=[ticker],
                confirmation_signal=f"{ticker} RS 3M > 5% + graph centrality rising",
                invalidators=["Supply constraint resolves", "Competitor enters", "Demand collapse"],
                regime_fit=self._regime_fit(ticker, structural_quad),
                forward_return_expectation=forward_ret,
                transition_forecast=trans_forecast,
                discovered_at=time.strftime("%Y-%m-%d %H:%M"),
            ))

        # 4B: Narratives from price clusters + news validation
        for c in clusters.get("clusters", []):
            if not c.get("is_novel_theme"):
                continue
            cluster_news_count = 0
            cluster_supply_hits = 0
            for t in c["members"]:
                t_news = news_results.get("ticker_specific", {}).get(t, [])
                cluster_news_count += len(t_news)
                for ni in t_news:
                    if hasattr(ni, 'supply_chain_mentions') and len(ni.supply_chain_mentions) > 0:
                        cluster_supply_hits += 1

            if cluster_news_count >= 3:
                conf = min(c["confidence"] + 0.15, 1.0)
                candidates.append(DiscoveryCandidate(
                    name=c["theme_hypothesis"],
                    category="narrative",
                    stage="active" if c["avg_rs_3m"] > 0.10 else "building",
                    thesis=f"Cross-sector cluster: {', '.join(c['members'][:5])}. News: {cluster_news_count} articles. Supply mentions: {cluster_supply_hits}.",
                    confidence=round(conf, 2),
                    source_signals=["price_cluster", "news_validation"],
                    beneficiary_tickers=c["members"],
                    confirmation_signal="Cluster RS sustained 3M + news volume increasing",
                    invalidators=["Cluster correlation breaks", "News volume drops", "Lead ticker breaks TREND LRR"],
                    regime_fit=self._regime_fit_narrative(c["dominant_sector"], structural_quad),
                    forward_return_expectation=forward_ret,
                    transition_forecast=trans_forecast,
                    discovered_at=time.strftime("%Y-%m-%d %H:%M"),
                ))

        # 4C: New themes from news clustering
        for nt in news_results.get("new_theme_candidates", []):
            candidates.append(DiscoveryCandidate(
                name=nt.get("suggested_theme_name", "unknown_theme"),
                category="narrative",
                stage="brewing",
                thesis=f"Emergent theme from news: {', '.join(nt.get('shared_keywords', [])[:5])}. Sample: {nt.get('sample_headlines', [''])[0]}",
                confidence=0.45,
                source_signals=["news_clustering"],
                beneficiary_tickers=[],
                confirmation_signal="Keyword frequency increasing + price cluster forms",
                invalidators=["Headlines revert to old themes", "No price confirmation"],
                forward_return_expectation=forward_ret,
                transition_forecast=trans_forecast,
                discovered_at=time.strftime("%Y-%m-%d %H:%M"),
            ))

        # 4D: Transitions from regime predictor
        if structural_quad != monthly_quad:
            path = f"{structural_quad}→{monthly_quad}"
            candidates.append(DiscoveryCandidate(
                name=path,
                category="transition",
                stage="building",
                thesis=f"Monthly divergence detected. Predicted quad 3M forward: {trans_forecast['predicted_quad']} (confidence {trans_forecast['prediction_confidence']:.0%}).",
                confidence=round(trans_forecast["prediction_confidence"], 2),
                source_signals=["regime_predictor", "monthly_divergence"],
                beneficiary_tickers=trans_forecast.get("probability_distribution", {}),
                confirmation_signal="Monthly data confirms direction for 2+ months",
                invalidators=["Macro data reverses", "Fed policy surprise"],
                regime_fit=0.6,
                forward_return_expectation=forward_ret,
                transition_forecast=trans_forecast,
                discovered_at=time.strftime("%Y-%m-%d %H:%M"),
            ))

        return {
            "candidates": [self._to_dict(c) for c in candidates],
            "bottlenecks": [self._to_dict(c) for c in candidates if c.category == "bottleneck"],
            "narratives": [self._to_dict(c) for c in candidates if c.category == "narrative"],
            "transitions": [self._to_dict(c) for c in candidates if c.category == "transition"],
            "meta": {
                "clusters_found": len(clusters.get("clusters", [])),
                "news_analyzed": news_results.get("analyzed_count", 0),
                "graph_bottlenecks": len(graph_results.get("bottlenecks", [])),
                "total_candidates": len(candidates),
                "predicted_quad": trans_forecast.get("predicted_quad"),
                "build_time_s": round(time.time() - t0, 1),
            }
        }

    def _auto_queries(self, sq, mq):
        queries = []
        if sq == "Q3" or mq == "Q3":
            queries.extend(["gold shortage central bank", "defensive stocks", "stagflation supply chain"])
        if sq == "Q2" or mq == "Q2":
            queries.extend(["commodity shortage", "energy bottleneck", "inflation supply constraint"])
        if sq == "Q4" or mq == "Q4":
            queries.extend(["deflation recession", "bond rally", "credit stress"])
        if sq == "Q1" or mq == "Q1":
            queries.extend(["tech breakout AI", "growth rebound", "small cap rally"])
        queries.extend(["supply chain bottleneck", "shortage constrained", "data center power"])
        return queries

    def _regime_fit(self, ticker, quad):
        from config.settings import BOTTLENECK_PROFILES, TICKER_SECTOR
        sector = TICKER_SECTOR.get(ticker, "generic")
        prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES["generic"])
        return float(prof.get(quad, 0.5))

    def _regime_fit_narrative(self, sector, quad):
        from config.settings import BOTTLENECK_PROFILES
        prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES["generic"])
        return float(prof.get(quad, 0.5))

    def _to_dict(self, c: DiscoveryCandidate):
        return {
            "name": c.name, "category": c.category, "stage": c.stage,
            "thesis": c.thesis, "confidence": c.confidence,
            "source_signals": c.source_signals, "beneficiary_tickers": c.beneficiary_tickers,
            "fade_tickers": c.fade_tickers, "confirmation_signal": c.confirmation_signal,
            "invalidators": c.invalidators, "regime_fit": c.regime_fit,
            "pump_risk": c.pump_risk, "discovered_at": c.discovered_at,
            "forward_return_expectation": c.forward_return_expectation,
            "transition_forecast": c.transition_forecast,
        }
