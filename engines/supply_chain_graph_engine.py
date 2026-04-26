"""engines/supply_chain_graph_engine.py — 10/10 Supply Chain Graph + Centrality

Builds supply chain graph from:
  1. EDGAR 10-K supplier/customer mentions
  2. News co-mention (who is mentioned together in bottleneck context)
  3. Correlation clustering (who moves together = likely linked)

Centrality analysis → auto-rank bottleneck criticality.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Set, Tuple
import numpy as np
import pandas as pd
from collections import defaultdict

try:
    import networkx as nx
    NETWORKX_AVAILABLE = True
except ImportError:
    NETWORKX_AVAILABLE = False

class SupplyChainGraphEngine:
    def __init__(self, sector_map: Dict[str,str], market_map: Dict[str,str]):
        self.sector_map = sector_map
        self.market_map = market_map

    def build_graph(
        self,
        edgar_results: Dict[str, object],
        news_results: Dict[str, object],
        price_clusters: Dict[str, object],
        prices: Dict[str, pd.Series],
    ) -> Dict[str, object]:

        if not NETWORKX_AVAILABLE:
            return {"error": "networkx required", "bottlenecks": []}

        G = nx.DiGraph()

        # 1. Add nodes from all tickers
        all_tickers = set()
        for r in edgar_results.get("candidates", []):
            if "ticker" in r:
                all_tickers.add(r["ticker"])
        for c in price_clusters.get("clusters", []):
            all_tickers.update(c.get("members", []))

        for t in all_tickers:
            G.add_node(t, sector=self.sector_map.get(t, "unknown"),
                       market=self.market_map.get(t, "us_equity"))

        # 2. EDGAR edges: supplier → customer
        for r in edgar_results.get("candidates", []):
            t = r.get("ticker")
            if not t:
                continue
            for supplier in r.get("supplier_mentions", [])[:5]:
                s_ticker = self._guess_ticker(supplier)
                if s_ticker and s_ticker != t:
                    G.add_edge(s_ticker, t, relation="supplier", weight=0.7)
            for customer in r.get("customer_mentions", [])[:5]:
                c_ticker = self._guess_ticker(customer)
                if c_ticker and c_ticker != t:
                    G.add_edge(t, c_ticker, relation="customer", weight=0.7)

        # 3. News co-mention edges
        for ni in news_results.get("supply_chain_alerts", []):
            if hasattr(ni, 'linked_tickers') and len(ni.linked_tickers) > 1:
                lt = ni.linked_tickers
                for i in range(len(lt)):
                    for j in range(i+1, len(lt)):
                        if G.has_edge(lt[i], lt[j]):
                            G[lt[i]][lt[j]]["weight"] += 0.2
                        else:
                            G.add_edge(lt[i], lt[j], relation="news_comention", weight=0.3)

        # 4. Price correlation edges (within clusters)
        for c in price_clusters.get("clusters", []):
            members = c.get("members", [])
            for i in range(len(members)):
                for j in range(i+1, len(members)):
                    if G.has_edge(members[i], members[j]):
                        G[members[i]][members[j]]["weight"] += c.get("avg_correlation", 0.5) * 0.5
                    else:
                        G.add_edge(members[i], members[j], relation="price_correlated",
                                   weight=c.get("avg_correlation", 0.5) * 0.5)

        # 5. Centrality analysis
        if len(G.nodes()) < 3:
            return {"graph_nodes": len(G.nodes()), "bottlenecks": []}

        try:
            betweenness = nx.betweenness_centrality(G, weight="weight")
            eigenvector = nx.eigenvector_centrality(G, weight="weight", max_iter=100)
            in_degree = dict(G.in_degree(weight="weight"))
            out_degree = dict(G.out_degree(weight="weight"))
        except Exception as e:
            return {"error": str(e), "bottlenecks": []}

        # 6. Rank bottleneck candidates
        scored = []
        for node in G.nodes():
            # Bottleneck score = high betweenness (bridge) + high in-degree (many suppliers)
            # + eigenvector (connected to other important nodes)
            b = betweenness.get(node, 0)
            e = eigenvector.get(node, 0)
            ind = in_degree.get(node, 0)
            outd = out_degree.get(node, 0)

            # EDGAR constraint boost
            edgar_boost = 0.0
            for r in edgar_results.get("candidates", []):
                if r.get("ticker") == node:
                    edgar_boost = r.get("constraint_score", 0) * 0.3

            score = min(b * 2.0 + e * 1.5 + ind * 0.5 + edgar_boost, 1.0)

            # Detect "chokepoint": high betweenness + few alternative paths
            try:
                alt_paths = len(list(nx.all_simple_paths(G, source=node, target=list(G.nodes())[:10], cutoff=2)))
            except:
                alt_paths = 0
            chokepoint = b > 0.15 and alt_paths < 3

            scored.append({
                "ticker": node,
                "bottleneck_score": round(score, 3),
                "betweenness": round(b, 4),
                "eigenvector": round(e, 4),
                "in_degree_weighted": round(ind, 2),
                "out_degree_weighted": round(outd, 2),
                "is_chokepoint": chokepoint,
                "sector": G.nodes[node].get("sector", "unknown"),
                "thesis": f"High centrality ({b:.3f}) + {ind:.1f} weighted suppliers. " +
                          ("Chokepoint detected. " if chokepoint else "") +
                          f"Connected to {len(list(G.neighbors(node)))} peers.",
            })

        scored.sort(key=lambda x: x["bottleneck_score"], reverse=True)
        return {
            "graph_nodes": len(G.nodes()),
            "graph_edges": len(G.edges()),
            "bottlenecks": scored,
            "chokepoints": [s for s in scored if s["is_chokepoint"]],
            "meta": {"networkx": True, "centrality_methods": ["betweenness", "eigenvector", "degree"]}
        }

    def _guess_ticker(self, company_name: str) -> Optional[str]:
        """Naive mapping from company name to ticker. Extendable via lookup table."""
        # This is a lightweight heuristic. For 10/10, use a proper company→ticker DB.
        name_upper = company_name.upper().strip()
        # Known mappings
        mappings = {
            "NVIDIA": "NVDA", "MICROSOFT": "MSFT", "APPLE": "AAPL", "TESLA": "TSLA",
            "AMAZON": "AMZN", "GOOGLE": "GOOGL", "ALPHABET": "GOOGL", "META": "META",
            "TSMC": "TSM", "TAIWAN SEMICONDUCTOR": "TSM", "ASML": "ASML",
            "LITE": "LITE", "LUMENTUM": "LITE", "COHERENT": "COHR", "COHR": "COHR",
            "ON SEMICONDUCTOR": "ON", "ON SEMI": "ON", "WOLFSPEED": "WOLF",
            "EATON": "ETN", "VERTIV": "VRT", "GE VERNOVA": "GEV",
        }
        for key, tick in mappings.items():
            if key in name_upper:
                return tick
        return None
