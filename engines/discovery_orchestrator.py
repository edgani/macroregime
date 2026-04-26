"""engines/discovery_orchestrator.py — Multi-Market Integration Layer

Wires together:
  • bottleneck_discovery_v3.py  (Reactive / Adaptive / Proactive discovery — ALL markets)
  • narrative_engine_v3.py      (Narrative scoring + cross-market spillover)
  • scenario_engine.py           (existing: macro regime transitions — Hedgeye GIP)
  • bottleneck_engine.py         (existing: curated scanner + TP logic)

Hedgeye Foundation = UNCHANGED. Discovery v3 = Tactical Overlay.
"""
from __future__ import annotations
from typing import Dict, List, Optional
import pandas as pd

from engines.bottleneck_discovery_v3 import BottleneckDiscoveryV3
from engines.narrative_engine_v3 import NarrativeEngineV3


class DiscoveryOrchestrator:
    def __init__(self, settings_module):
        self.cfg = settings_module
        self.discovery = BottleneckDiscoveryV3(settings_module)
        self.narrative = NarrativeEngineV3(settings_module)

    def run_full_pipeline(
        self,
        prices: Dict[str, pd.Series],
        volumes: Optional[Dict[str, pd.Series]] = None,
        quad_str: str = "Q3",
        quad_mon: str = "Q2",
        benchmark: str = "SPY",
        asset_ranges: Optional[Dict] = None,
        scenario_output: Optional[Dict] = None,
        supply_chain_signals: Optional[Dict] = None,
        sector_momentum: Optional[Dict[str, float]] = None,
        flow_scores: Optional[Dict[str, float]] = None,
        top_n: int = 50,
    ) -> Dict:
        """One-call full discovery + narrative + spillover across ALL markets."""

        # 1. DISCOVERY v3 — multi-market
        disc = self.discovery.run(
            prices=prices, volumes=volumes, quad_str=quad_str, quad_mon=quad_mon,
            asset_ranges=asset_ranges, sector_momentum=sector_momentum,
            flow_scores=flow_scores, top_n=top_n,
        )

        # 2. NARRATIVE v3 — multi-market
        narr = self.narrative.run(
            prices=prices, volumes=volumes, quad_str=quad_str,
            scenario_output=scenario_output,
            supply_chain_signals=supply_chain_signals,
            target_asset_classes=["crypto", "forex", "commodity", "ihsg", "bonds", "global"],
        )

        # 3. MERGE candidates enriched with narrative tags
        merged = []
        seen = set()
        for c in disc["reactive"]:
            c["narrative_tag"] = self._match_narrative(c["sector"], narr)
            c["source"] = "reactive_discovery"
            merged.append(c)
            seen.add(c["ticker"])
        for c in disc["proactive"]:
            if c["ticker"] not in seen:
                c["narrative_tag"] = self._match_narrative(c["sector"], narr)
                c["source"] = "proactive_chain"
                merged.append(c)
                seen.add(c["ticker"])

        merged.sort(key=lambda x: x["ev"] * (1.2 if x["source"] == "reactive_discovery" else 1.0), reverse=True)

        # 4. CROSS-MARKET SPILLOVER MAP
        spillover_by_market = {"crypto": [], "ihsg": [], "forex": [], "commodity": [], "bonds": [], "global": []}
        for row in disc.get("spillover", []):
            target = row.get("target", "")
            mkt = self.discovery.market_map.get(target, "us_equity")
            if mkt in spillover_by_market:
                spillover_by_market[mkt].append(row)
            else:
                if target.endswith(".JK"):
                    spillover_by_market["ihsg"].append(row)
                elif "-USD" in target or target in ("IBIT", "FBTC", "ETHA", "MSTR"):
                    spillover_by_market["crypto"].append(row)
                elif "=F" in target or target in ("GLD", "SLV", "USO", "UNG", "CPER"):
                    spillover_by_market["commodity"].append(row)
                elif "=X" in target or target == "DX-Y.NYB":
                    spillover_by_market["forex"].append(row)

        for mkt in spillover_by_market:
            spillover_by_market[mkt].sort(key=lambda x: x["spillover_score"], reverse=True)
            spillover_by_market[mkt] = spillover_by_market[mkt][:10]

        # 5. REGIME-NARRATIVE ALIGNMENT
        regime_forecast = {}
        if scenario_output and narr.get("dominant_narrative"):
            base = scenario_output.get("base_case")
            if base:
                alignment_score = 0.0
                dn = narr["dominant_narrative"]
                if base.to_quad in ("Q1", "Q2") and dn in ("ai_infrastructure", "fed_pivot_liquidity"):
                    alignment_score = 0.85
                elif base.to_quad == "Q3" and dn in ("hard_assets_scarcity", "healthcare_scarcity", "dxy_bearish_em_recovery"):
                    alignment_score = 0.80
                elif base.to_quad == "Q4" and dn in ("bond_duration_bull", "healthcare_scarcity"):
                    alignment_score = 0.90
                else:
                    alignment_score = 0.50

                regime_forecast = {
                    "current_quad": quad_str,
                    "target_quad": base.to_quad,
                    "transition_prob": round(base.probability, 3),
                    "dominant_narrative": dn,
                    "dominant_strength": narr["dominant_strength"],
                    "narrative_regime_alignment": round(alignment_score, 2),
                    "alignment_verdict": "HIGH" if alignment_score > 0.75 else "MEDIUM" if alignment_score > 0.50 else "LOW",
                    "best_expression_per_market": {
                        "us_equity": narr.get("spillover", {}).get("global", [])[:3],
                        "crypto": spillover_by_market["crypto"][:5],
                        "ihsg": spillover_by_market["ihsg"][:5],
                        "commodity": spillover_by_market["commodity"][:5],
                        "forex": spillover_by_market["forex"][:5],
                        "bonds": spillover_by_market["bonds"][:5],
                    },
                }

        return {
            "discovered": disc,
            "narrative": narr,
            "merged_candidates": merged[:top_n],
            "spillover_by_market": spillover_by_market,
            "proactive_chain": disc["proactive"],
            "regime_forecast": regime_forecast,
            "meta": {
                "total_candidates": len(merged),
                "reactive_count": len(disc["reactive"]),
                "proactive_count": len(disc["proactive"]),
                "markets_covered": len([k for k, v in spillover_by_market.items() if v]),
                "igniting_narratives": narr["meta"]["igniting_now"],
                "quad": quad_str,
                "monthly_quad": quad_mon,
            },
        }

    def _match_narrative(self, sector: str, narr_output: Dict) -> str:
        from engines.narrative_engine_v3 import NARRATIVES
        best_match = ""
        best_score = 0.0
        for name, meta in NARRATIVES.items():
            if sector in meta.get("sectors", []):
                strength = narr_output.get("adaptive_weights", {}).get(name, 0.5)
                if strength > best_score:
                    best_score = strength
                    best_match = name
        return best_match