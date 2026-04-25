"""engines/historical_analog_engine.py - Ported from v9_fixed.
Matches current macro fingerprint against historical regimes.
"""
from __future__ import annotations
import math
from typing import Dict, List
import numpy as np

def clamp01(x): return float(max(0.0, min(1.0, x)))

_ANALOG_LIBRARY = [
    {"label":"2018 trade-war pressure","vector":{"growth":-0.20,"inflation":0.15,"dollar":0.40,"oil":0.05,"vol":0.25},
     "path_1m":"policy-sensitive chop","path_3m":"narrow leaders and defensive bid","path_6m":"relief possible after moderation",
     "next_bias":"Monthly pressure may fade, structural slowdown stays","duration":"3-8 weeks",
     "impacts":{"us":"mixed","ihsg":"bearish","fx":"bullish_usd","commodities":"mixed","crypto":"bearish"}},
    {"label":"2022 commodity shock (Q3)","vector":{"growth":-0.35,"inflation":0.75,"dollar":0.20,"oil":0.90,"vol":0.50},
     "path_1m":"inflation scare, resource lead","path_3m":"dispersion with fragile beta","path_6m":"policy threshold eventually matters",
     "next_bias":"Monthly Q3 can persist while structural pressure broadens","duration":"4-10 weeks",
     "impacts":{"us":"energy_up_beta_fragile","ihsg":"exporters_up_importers_down","fx":"commodity_fx_up","commodities":"bullish","crypto":"bearish"}},
    {"label":"2025 tariff bond rout","vector":{"growth":-0.25,"inflation":0.30,"dollar":0.50,"oil":0.10,"vol":0.45},
     "path_1m":"long-end pain, broad stress","path_3m":"negotiation relief can squeeze laggards","path_6m":"outcome hinges on de-escalation",
     "next_bias":"Structural stress dominates unless policy relief lands","duration":"2-6 weeks",
     "impacts":{"us":"defensive","ihsg":"bearish","fx":"usd_up","commodities":"gold_over_cyclicals","crypto":"bearish"}},
    {"label":"2026 war-oil stagflation","vector":{"growth":-0.30,"inflation":0.80,"dollar":0.35,"oil":0.95,"vol":0.55},
     "path_1m":"oil-first stagflation pressure","path_3m":"energy lead with mixed broader tape","path_6m":"de-escalation can rotate leadership",
     "next_bias":"Petrodollar branch can keep monthly Q3 alive inside structural slowdown","duration":"2-8 weeks",
     "impacts":{"us":"energy_vs_cyclicals","ihsg":"coal_up_rupiah_fragile","fx":"usd_petro_bid","commodities":"energy_gold_up","crypto":"fragile"}},
    {"label":"mid-cycle mixed slowdown","vector":{"growth":-0.05,"inflation":0.05,"dollar":0.00,"oil":0.00,"vol":0.10},
     "path_1m":"rotation without panic","path_3m":"slowdown signs, no crash","path_6m":"macro path decides winners",
     "next_bias":"Base case stays mixed until a cleaner impulse emerges","duration":"4-12 weeks",
     "impacts":{"us":"mixed","ihsg":"mixed","fx":"range","commodities":"selective","crypto":"selective"}},
    {"label":"2019 Fed pivot relief","vector":{"growth":-0.10,"inflation":-0.10,"dollar":-0.20,"oil":-0.05,"vol":-0.20},
     "path_1m":"rate-cut pricing squeezes shorts","path_3m":"broad risk-on but shallow","path_6m":"growth must materialize for sustainability",
     "next_bias":"Pivot-driven rally: Q4→Q1 transition. EM recovery begins.","duration":"6-12 weeks",
     "impacts":{"us":"bullish","ihsg":"recovery","fx":"usd_down_em_up","commodities":"base_metals_bid","crypto":"bullish"}},
    {"label":"2020 COVID recovery (Q4→Q1)","vector":{"growth":0.60,"inflation":-0.10,"dollar":-0.30,"oil":0.20,"vol":-0.40},
     "path_1m":"beta chase, small cap surge","path_3m":"broadest risk-on in a generation","path_6m":"inflation eventually returns",
     "next_bias":"Maximum conviction long. All assets rally off deflationary base.","duration":"12-20 weeks",
     "impacts":{"us":"maximum_long","ihsg":"max_recovery","fx":"usd_down_all_em_up","commodities":"commodity_supercycle","crypto":"bullish_extreme"}},
]

class HistoricalAnalogEngine:
    def run(self, gip_features: Dict[str,float], prices_context: Dict[str,float] = None) -> Dict:
        prices_context = prices_context or {}
        # Build current fingerprint
        current = {
            "growth":   float(gip_features.get("growth_level",0) + gip_features.get("growth_momentum",0)) * 0.5,
            "inflation":float(gip_features.get("inflation_level",0) + gip_features.get("inflation_momentum",0)) * 0.5,
            "dollar":   float(prices_context.get("dxy_1m", 0.0)) / 0.04,
            "oil":      float(prices_context.get("oil_3m", 0.0)) / 0.25,
            "vol":      float(prices_context.get("vol_stress", 0.0)),
        }

        scored = []
        for analog in _ANALOG_LIBRARY:
            vec = analog["vector"]
            # Euclidean distance in 5D space
            dist = math.sqrt(sum((current.get(k,0)-vec.get(k,0))**2 for k in ["growth","inflation","dollar","oil","vol"]))
            similarity = clamp01(1.0 - dist / 3.0)
            scored.append({**analog, "similarity": round(similarity,3), "distance": round(dist,3)})

        scored.sort(key=lambda x: x["similarity"], reverse=True)
        top3 = scored[:3]

        # Composite path narrative from top analogs
        if top3 and top3[0]["similarity"] > 0.45:
            best = top3[0]
            composite_note = f"Current fingerprint most resembles **{best['label']}**. {best['next_bias']}. Typical duration: {best['duration']}."
        else:
            composite_note = "No strong historical analog match — regime has novel characteristics. Stay data-dependent."

        return dict(
            top_analogs=top3,
            all_analogs=scored,
            composite_note=composite_note,
            current_fingerprint=current,
        )
