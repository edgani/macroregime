"""engines/auto_discovery_engine_v3.py — FIXED for orchestrator compatibility

FIXES:
1. __init__ now has ALL optional args (defaults from config.settings)
2. run() accepts (prices, gip=None, risk_ranges=None) so orchestrator can call it simply
3. Defensive imports: if sub-engines missing, uses lightweight fallback
4. If prices empty or gip missing, returns graceful empty result instead of crashing
"""
from __future__ import annotations
import time
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger(__name__)

# ── Defensive sub-engine imports ────────────────────────────────────────────
def _safe_import(module, cls, fallback):
    try:
        mod = __import__(module, fromlist=[cls])
        return getattr(mod, cls)
    except Exception as e:
        logger.warning(f"{module}.{cls} unavailable: {e}")
        return fallback

class _FakeClusterEngine:
    def __init__(self, *a, **k): pass
    def run(self, prices, benchmark="SPY", lookback=63):
        return {"clusters": [], "meta": {"error": "PriceClusterEngineV3 unavailable"}}

class _FakeNewsEngine:
    def __init__(self, *a, **k): pass
    def run(self, tickers, theme_queries=None):
        return {"ticker_specific": {}, "new_theme_candidates": [], "analyzed_count": 0}

class _FakeEDGAREngine:
    def run(self, tickers):
        return {"candidates": [], "strong_candidates": []}

class _FakeGraphEngine:
    def __init__(self, *a, **k): pass
    def build_graph(self, edgar, news, clusters, prices):
        return {"bottlenecks": []}

class _FakeLeadingEngine:
    def fit(self, snapshots): pass
    def predict_forward_return(self, features, quad):
        return {"expected_1m": 0.0, "expected_3m": 0.0, "confidence": 0.0}

class _FakeRegimePredictor:
    def predict(self, current_quad, features, months_forward=3):
        return {
            "current_quad": current_quad,
            "predicted_quad": current_quad,
            "prediction_confidence": 0.25,
            "probability_distribution": {"Q1":0.25,"Q2":0.25,"Q3":0.25,"Q4":0.25},
            "expected_transition_weeks": 8,
            "months_forward": months_forward,
            "model_used": False,
        }

PriceClusterEngineV3 = _safe_import("engines.price_cluster_engine_v3", "PriceClusterEngineV3", _FakeClusterEngine)
NewsNLPEngineV3       = _safe_import("engines.news_nlp_engine_v3", "NewsNLPEngineV3", _FakeNewsEngine)
EDGARScraperEngine    = _safe_import("engines.edgar_scraper_engine", "EDGARScraperEngine", _FakeEDGAREngine)
SupplyChainGraphEngine= _safe_import("engines.supply_chain_graph_engine", "SupplyChainGraphEngine", _FakeGraphEngine)
LeadingIndicatorEngine= _safe_import("engines.leading_indicator_engine", "LeadingIndicatorEngine", _FakeLeadingEngine)
RegimePredictorEngine = _safe_import("engines.regime_predictor_engine", "RegimePredictorEngine", _FakeRegimePredictor)


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
    """
    L1-L4 autonomous discovery brain.
    Now compatible with orchestrator's simple call:
        engine = AutoDiscoveryEngineV3()
        engine.run(prices, gip, risk_ranges)
    """

    def __init__(self, sector_map=None, market_map=None, known_tickers=None, use_transformers=False):
        # Default to config.settings if not provided
        if sector_map is None or market_map is None:
            try:
                from config.settings import TICKER_SECTOR, MARKET_CLASSIFICATION
                sector_map = sector_map or TICKER_SECTOR
                market_map = market_map or MARKET_CLASSIFICATION
            except Exception as e:
                logger.warning(f"Could not load settings for discovery defaults: {e}")
                sector_map = sector_map or {}
                market_map = market_map or {}

        self.sector_map = sector_map
        self.market_map = market_map
        self.known_tickers = known_tickers or []

        self.cluster_engine = PriceClusterEngineV3(sector_map, market_map)
        self.news_engine = NewsNLPEngineV3(use_transformers=use_transformers, known_tickers=self.known_tickers)
        self.edgar_engine = EDGARScraperEngine()
        self.graph_engine = SupplyChainGraphEngine(sector_map, market_map)
        self.leading_engine = LeadingIndicatorEngine()
        self.regime_predictor = RegimePredictorEngine()

    def run(self, prices, gip=None, risk_ranges=None, **kwargs) -> Dict[str, object]:
        """
        PRIMARY orchestrator-compatible entry point.
        Accepts: run(prices, gip, risk_ranges)
        Also accepts legacy kwargs: structural_quad, monthly_quad, gip_features
        """
        t0 = time.time()

        # ── Extract parameters from gip object if provided ──────────────────
        if gip is not None:
            structural_quad = getattr(gip, "structural_quad", kwargs.get("structural_quad", "Q3"))
            monthly_quad = getattr(gip, "monthly_quad", kwargs.get("monthly_quad", "Q2"))
            gip_features = getattr(gip, "features", kwargs.get("gip_features", {}))
        else:
            structural_quad = kwargs.get("structural_quad", "Q3")
            monthly_quad = kwargs.get("monthly_quad", "Q2")
            gip_features = kwargs.get("gip_features", {})

        theme_queries = kwargs.get("theme_queries", None)
        run_edgar = kwargs.get("run_edgar", True)

        # ── Guard: empty prices ───────────────────────────────────────────
        if not prices:
            logger.warning("AutoDiscoveryEngineV3 received empty prices — returning empty")
            return {
                "ok": True,
                "candidates": [],
                "bottlenecks": [],
                "narratives": [],
                "transitions": [],
                "meta": {
                    "clusters_found": 0,
                    "news_analyzed": 0,
                    "graph_bottlenecks": 0,
                    "total_candidates": 0,
                    "predicted_quad": monthly_quad,
                    "build_time_s": round(time.time() - t0, 1),
                    "note": "Empty prices — no discovery possible",
                }
            }

        # ── L1: Price Clusters ────────────────────────────────────────────
        clusters = self.cluster_engine.run(prices, benchmark="SPY", lookback=63)

        # ── L2: News NLP ────────────────────────────────────────────────────
        query_tickers = []
        for c in clusters.get("clusters", []):
            query_tickers.extend(c.get("members", []))
        query_tickers = list(dict.fromkeys(query_tickers))[:30]
        news_queries = theme_queries or self._auto_queries(structural_quad, monthly_quad)
        news_results = self.news_engine.run(query_tickers, theme_queries=news_queries)

        # ── L3a: EDGAR (optional, slower) + yfinance fallback ──────────────
        edgar_results = {"candidates": [], "strong_candidates": []}
        yfinance_results = []
        if run_edgar and len(query_tickers) <= 20:
            try:
                edgar_results = self.edgar_engine.run(query_tickers)
            except Exception as e:
                logger.warning(f"EDGAR error: {e}")

        # Fallback: yfinance business summary mining
        if not edgar_results.get("strong_candidates"):
            try:
                import yfinance as yf
                for t in query_tickers[:15]:
                    try:
                        info = yf.Ticker(t).info or {}
                        summary = (info.get("longBusinessSummary", "") or "").lower()
                        if any(kw in summary for kw in ["sole source", "only supplier", "dominant", "market leader", "limited suppliers", "capacity constrained"]):
                            yfinance_results.append({
                                "ticker": t,
                                "constraint_score": 0.6,
                                "constraint_hits": ["yfinance_summary"],
                                "thesis": f"{t}: Business summary indicates supply constraint language.",
                                "is_bottleneck_candidate": True,
                            })
                    except Exception:
                        pass
            except Exception as e:
                logger.warning(f"yfinance fallback error: {e}")

        merged_candidates = edgar_results.get("candidates", []) + yfinance_results
        merged_strong = edgar_results.get("strong_candidates", []) + [r for r in yfinance_results if r.get("is_bottleneck_candidate")]
        edgar_results = {"candidates": merged_candidates, "strong_candidates": merged_strong}

        # ── L3b: Supply Chain Graph ─────────────────────────────────────────
        graph_results = self.graph_engine.build_graph(edgar_results, news_results, clusters, prices)

        # ── L4: Forward prediction ──────────────────────────────────────────
        trans_forecast = self.regime_predictor.predict(structural_quad, gip_features, months_forward=3)
        try:
            self.leading_engine.fit([])
        except Exception:
            pass
        forward_ret = self.leading_engine.predict_forward_return(gip_features, structural_quad)

        # ── Integrate: generate candidates ──────────────────────────────────
        candidates = []

        # 4A: Bottlenecks from graph centrality + EDGAR + price confirmation
        for b in graph_results.get("bottlenecks", [])[:15]:
            ticker = b.get("ticker", "UNKNOWN")
            in_cluster = None
            for c in clusters.get("clusters", []):
                if ticker in c.get("members", []):
                    in_cluster = c
                    break
            conf = min(b.get("bottleneck_score", 0.5) * 1.1, 1.0)
            if in_cluster:
                conf = min(conf + 0.1, 1.0)
            candidates.append(DiscoveryCandidate(
                name=f"{ticker} structural bottleneck",
                category="bottleneck",
                stage="active" if (in_cluster and in_cluster.get("avg_rs_3m", 0) > 0.10) else "building",
                thesis=b.get("thesis", "") + (f" Confirmed by price cluster with {in_cluster.get('member_count', 0)} peers." if in_cluster else ""),
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
            for t in c.get("members", []):
                t_news = news_results.get("ticker_specific", {}).get(t, [])
                cluster_news_count += len(t_news)
                for ni in t_news:
                    if hasattr(ni, 'supply_chain_mentions') and len(ni.supply_chain_mentions) > 0:
                        cluster_supply_hits += 1
            if cluster_news_count >= 3:
                conf = min(c.get("confidence", 0.5) + 0.15, 1.0)
                candidates.append(DiscoveryCandidate(
                    name=c.get("theme_hypothesis", "Unknown theme"),
                    category="narrative",
                    stage="active" if c.get("avg_rs_3m", 0) > 0.10 else "building",
                    thesis=f"Cross-sector cluster: {', '.join(c.get('members', [])[:5])}. News: {cluster_news_count} articles. Supply mentions: {cluster_supply_hits}.",
                    confidence=round(conf, 2),
                    source_signals=["price_cluster", "news_validation"],
                    beneficiary_tickers=c.get("members", []),
                    confirmation_signal="Cluster RS sustained 3M + news volume increasing",
                    invalidators=["Cluster correlation breaks", "News volume drops", "Lead ticker breaks TREND LRR"],
                    regime_fit=self._regime_fit_narrative(c.get("dominant_sector", "generic"), structural_quad),
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
                thesis=f"Monthly divergence detected. Predicted quad 3M forward: {trans_forecast.get('predicted_quad', '?')} (confidence {trans_forecast.get('prediction_confidence', 0):.0%}).",
                confidence=round(trans_forecast.get("prediction_confidence", 0), 2),
                source_signals=["regime_predictor", "monthly_divergence"],
                beneficiary_tickers=list(trans_forecast.get("probability_distribution", {}).keys()),
                confirmation_signal="Monthly data confirms direction for 2+ months",
                invalidators=["Macro data reverses", "Fed policy surprise"],
                regime_fit=0.6,
                forward_return_expectation=forward_ret,
                transition_forecast=trans_forecast,
                discovered_at=time.strftime("%Y-%m-%d %H:%M"),
            ))

        return {
            "ok": True,
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
        try:
            from config.settings import BOTTLENECK_PROFILES, TICKER_SECTOR
            sector = TICKER_SECTOR.get(ticker, "generic")
            prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES.get("generic", {"Q1":0.5,"Q2":0.5,"Q3":0.5,"Q4":0.5}))
            return float(prof.get(quad, 0.5))
        except Exception:
            return 0.5

    def _regime_fit_narrative(self, sector, quad):
        try:
            from config.settings import BOTTLENECK_PROFILES
            prof = BOTTLENECK_PROFILES.get(sector, BOTTLENECK_PROFILES.get("generic", {"Q1":0.5,"Q2":0.5,"Q3":0.5,"Q4":0.5}))
            return float(prof.get(quad, 0.5))
        except Exception:
            return 0.5

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
