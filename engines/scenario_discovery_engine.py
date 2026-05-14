"""engines/scenario_discovery_engine.py — Scenario Discovery Engine v1.0
Generates forward-looking scenario cards: "If X happens → Y assets move Z%"
Uses: price action, news NLP, FRED macro, options flow, interconnect triggers.
"""
import logging
import math
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Scenario templates with cascade logic
SCENARIO_TEMPLATES = [
    {
        "id": "war_middle_east",
        "name": "Middle East Escalation",
        "triggers": {"oil_spike_pct": 0.15, "vix_threshold": 28, "news_keywords": ["iran", "israel", "saudi", "oil", "sanctions"]},
        "shock": {"CL=F": 0.20, "GC=F": 0.10, "DX-Y.NYB": 0.03, "TLT": -0.05, "SPY": -0.08, "EEM": -0.12},
        "cascade": [
            ("Energy", 0.18, 3),
            ("Shipping", 0.25, 7),
            ("Airlines", -0.15, 14),
            ("Consumer Discretionary", -0.08, 30),
            ("Tech", -0.05, 45),
        ],
        "em_impact": {"DXY": 0.03, "EM": -0.10, "Rupiah": -0.05},
        "confidence_boosters": ["oil_>100", "vix_>30"],
    },
    {
        "id": "china_taiwan",
        "name": "China-Taiwan Tensions",
        "triggers": {"semis_selloff_pct": -0.12, "dxy_spike": 0.02, "news_keywords": ["taiwan", "tsmc", "china", "chip", "semiconductor"]},
        "shock": {"SMH": -0.20, "NVDA": -0.18, "TSM": -0.25, "QQQ": -0.12, "UUP": 0.04, "GLD": 0.08},
        "cascade": [
            ("Semiconductors", -0.20, 1),
            ("Hardware", -0.15, 5),
            ("Cloud", -0.10, 10),
            ("Software", -0.05, 20),
            ("Industrials", -0.08, 30),
        ],
        "em_impact": {"DXY": 0.04, "EM": -0.08, "Rupiah": -0.03},
        "confidence_boosters": ["smh_<-15%", "nvda_<-10%"],
    },
    {
        "id": "fed_hawkish",
        "name": "Fed Hawkish Pivot",
        "triggers": {"yield_curve_steepening": 0.30, "dxy_rise_1m": 0.03, "real_yield_>2.5": True},
        "shock": {"TLT": -0.12, "HYG": -0.08, "SPY": -0.06, "IWM": -0.10, "GLD": -0.05, "DX-Y.NYB": 0.04},
        "cascade": [
            ("Rates", -0.12, 1),
            ("REITs", -0.10, 3),
            ("Growth", -0.08, 7),
            ("Small Caps", -0.10, 14),
            ("EM", -0.12, 21),
        ],
        "em_impact": {"DXY": 0.05, "EM": -0.15, "Rupiah": -0.08},
        "confidence_boosters": ["dgs10_>5", "real_yield_>3"],
    },
    {
        "id": "recession_signal",
        "name": "Recession Signal (Sahm Rule)",
        "triggers": {"unrate_3m_change": 0.005, "indpro_contraction": True, "yield_curve_inversion": True},
        "shock": {"SPY": -0.15, "QQQ": -0.18, "IWM": -0.20, "TLT": 0.08, "GLD": 0.12, "DX-Y.NYB": 0.02, "XLU": 0.05},
        "cascade": [
            ("Cyclicals", -0.18, 5),
            ("Financials", -0.15, 10),
            ("Tech", -0.12, 15),
            ("Defensives", 0.05, 20),
            ("Treasuries", 0.08, 30),
        ],
        "em_impact": {"DXY": 0.02, "EM": -0.20, "Rupiah": -0.10},
        "confidence_boosters": ["unrate_>4.5", "ism_>48"],
    },
    {
        "id": "ai_bottleneck",
        "name": "AI Infrastructure Bottleneck",
        "triggers": {"nvda_earnings_miss": False, "hbm_shortage_news": True, "power_grid_constraint": True},
        "shock": {"NVDA": -0.15, "AMD": -0.12, "SMCI": -0.20, "VST": 0.25, "ETN": 0.20, "COHR": 0.15, "CL=F": 0.08},
        "cascade": [
            ("AI Chips", -0.15, 2),
            ("Server OEM", -0.12, 7),
            ("Power / Grid", 0.25, 10),
            ("Optical", 0.15, 14),
            ("Data Center REIT", 0.10, 21),
        ],
        "em_impact": {"DXY": 0.01, "EM": 0.02, "Rupiah": 0.01},
        "confidence_boosters": ["mu_earnings_warn", "pjm_alert"],
    },
    {
        "id": "dollar_crisis_em",
        "name": "Dollar Crisis → EM Opportunity",
        "triggers": {"dxy_fall_3m": -0.05, "gold_rally": 0.10, "em_flow_positive": True},
        "shock": {"EEM": 0.15, "VWO": 0.12, "GLD": 0.10, "SLV": 0.15, "FXI": 0.10, "DX-Y.NYB": -0.05, "TLT": 0.05},
        "cascade": [
            ("Precious Metals", 0.12, 3),
            ("EM Equity", 0.15, 7),
            ("Commodities", 0.10, 14),
            ("Materials", 0.08, 21),
            ("International", 0.06, 30),
        ],
        "em_impact": {"DXY": -0.05, "EM": 0.15, "Rupiah": 0.08},
        "confidence_boosters": ["dxy_<-100", "gold_>2500"],
    },
]

class ScenarioDiscoveryEngine:
    """Discovers active macro scenarios and their asset repricing cascades."""

    def __init__(self):
        self.scenarios = SCENARIO_TEMPLATES

    def _detect_trigger(self, template: Dict, prices: Dict, fred: Dict, news_analysis: Dict) -> float:
        """Return confidence 0-1 that this scenario is active."""
        triggers = template.get("triggers", {})
        confidence = 0.0
        checks = 0

        # Oil spike check
        if "oil_spike_pct" in triggers:
            checks += 1
            cl = prices.get("CL=F")
            if cl is not None and len(cl) >= 22:
                try:
                    ret = float(cl.iloc[-1] / cl.iloc[-22] - 1)
                    if ret >= triggers["oil_spike_pct"]:
                        confidence += 1.0
                    elif ret >= triggers["oil_spike_pct"] * 0.5:
                        confidence += 0.5
                except Exception:
                    pass

        # VIX threshold
        if "vix_threshold" in triggers:
            checks += 1
            vix = prices.get("^VIX")
            if vix is not None and len(vix) > 0:
                try:
                    v = float(vix.iloc[-1])
                    if v >= triggers["vix_threshold"]:
                        confidence += 1.0
                    elif v >= triggers["vix_threshold"] * 0.7:
                        confidence += 0.5
                except Exception:
                    pass

        # News keyword check
        if "news_keywords" in triggers:
            checks += 1
            emergent = (news_analysis or {}).get("emergent_narratives", [])
            for en in emergent:
                name = (en.get("name") or "").lower()
                if any(kw in name for kw in triggers["news_keywords"]):
                    confidence += 0.7
                    break
            # Also check rumor watch
            rumors = (news_analysis or {}).get("rumor_watch", [])
            for rw in rumors:
                headline = (rw.get("headline") or "").lower()
                if any(kw in headline for kw in triggers["news_keywords"]):
                    confidence += 0.3
                    break

        # DXY rise
        if "dxy_rise_1m" in triggers or "dxy_spike" in triggers:
            checks += 1
            dxy = prices.get("DX-Y.NYB")
            if dxy is not None and len(dxy) >= 22:
                try:
                    ret = float(dxy.iloc[-1] / dxy.iloc[-22] - 1)
                    threshold = triggers.get("dxy_rise_1m", triggers.get("dxy_spike", 0.02))
                    if ret >= threshold:
                        confidence += 1.0
                    elif ret >= threshold * 0.5:
                        confidence += 0.5
                except Exception:
                    pass

        # Real yield check
        if triggers.get("real_yield_>2.5"):
            checks += 1
            try:
                dgs10 = float(fred.get("DGS10", {}).dropna().iloc[-1]) if hasattr(fred.get("DGS10"), "dropna") else 4.5
                t5yie = float(fred.get("T5YIE", {}).dropna().iloc[-1]) if hasattr(fred.get("T5YIE"), "dropna") else 2.4
                if dgs10 - t5yie > 2.5:
                    confidence += 1.0
                elif dgs10 - t5yie > 2.0:
                    confidence += 0.5
            except Exception:
                pass

        # Unemployment spike (Sahm proxy)
        if "unrate_3m_change" in triggers:
            checks += 1
            unrate = fred.get("UNRATE")
            if unrate is not None and len(unrate) >= 4:
                try:
                    recent = float(unrate.iloc[-1])
                    past = float(unrate.iloc[-4])
                    if recent - past >= triggers["unrate_3m_change"]:
                        confidence += 1.0
                except Exception:
                    pass

        # Yield curve inversion
        if triggers.get("yield_curve_inversion"):
            checks += 1
            dgs10 = fred.get("DGS10")
            dgs2 = fred.get("DGS2")
            if dgs10 is not None and dgs2 is not None:
                try:
                    spread = float(dgs10.iloc[-1]) - float(dgs2.iloc[-1])
                    if spread < 0:
                        confidence += 1.0
                    elif spread < 0.5:
                        confidence += 0.3
                except Exception:
                    pass

        # INDPRO contraction
        if triggers.get("indpro_contraction"):
            checks += 1
            indpro = fred.get("INDPRO")
            if indpro is not None and len(indpro) >= 4:
                try:
                    if float(indpro.iloc[-1]) < float(indpro.iloc[-4]):
                        confidence += 1.0
                except Exception:
                    pass

        # NVDA earnings / HBM shortage (proxy dari price)
        if triggers.get("hbm_shortage_news"):
            checks += 1
            nvda = prices.get("NVDA")
            mu = prices.get("MU")
            if nvda is not None and len(nvda) >= 6:
                try:
                    ret5d = float(nvda.iloc[-1] / nvda.iloc[-6] - 1)
                    if ret5d < -0.08:
                        confidence += 0.7
                except Exception:
                    pass
            if mu is not None and len(mu) >= 6:
                try:
                    ret5d = float(mu.iloc[-1] / mu.iloc[-6] - 1)
                    if ret5d < -0.05:
                        confidence += 0.3
                except Exception:
                    pass

        # DXY fall (EM opportunity)
        if "dxy_fall_3m" in triggers:
            checks += 1
            dxy = prices.get("DX-Y.NYB")
            if dxy is not None and len(dxy) >= 64:
                try:
                    ret = float(dxy.iloc[-1] / dxy.iloc[-64] - 1)
                    threshold = triggers["dxy_fall_3m"]
                    if ret <= threshold:
                        confidence += 1.0
                    elif ret <= threshold * 0.5:
                        confidence += 0.5
                except Exception:
                    pass

        if checks == 0:
            return 0.0
        return min(1.0, confidence / max(checks * 0.6, 1.0))

    def _score_cascade(self, cascade: List, prices: Dict) -> List[Dict]:
        """Score each cascade step with current price context."""
        scored = []
        for sector, impact, lag in cascade:
            scored.append({
                "sector": sector,
                "impact": impact,
                "lag_days": lag,
                "status": "HIT" if lag <= 7 else ("BUILDING" if lag <= 21 else "WATCH"),
            })
        return scored

    def run(self, prices: Dict, fred: Dict, news_analysis: Dict, quad: str = "Q3") -> Dict:
        """Main entry: detect all scenarios, return active + watch list."""
        active = []
        watch = []
        for template in self.scenarios:
            conf = self._detect_trigger(template, prices, fred, news_analysis)
            scored_cascade = self._score_cascade(template.get("cascade", []), prices)
            scenario_card = {
                "id": template["id"],
                "scenario": template["name"],
                "active": conf >= 0.45,
                "confidence": round(conf, 2),
                "trigger": self._build_trigger_text(template, prices, fred),
                "shock": template.get("shock", {}),
                "sector_cascade": scored_cascade,
                "asset_scores": self._build_asset_scores(template.get("shock", {}), prices),
                "em_impact": template.get("em_impact", {}),
                "confidence_boosters": template.get("confidence_boosters", []),
            }
            if conf >= 0.45:
                active.append(scenario_card)
            elif conf >= 0.20:
                watch.append(scenario_card)
        return {
            "scenarios": active + watch,
            "active_scenarios": active,
            "watch_scenarios": [w["id"] for w in watch],
            "summary": f"{len(active)} active, {len(watch)} watching",
        }

    def _build_trigger_text(self, template: Dict, prices: Dict, fred: Dict) -> str:
        triggers = template.get("triggers", {})
        parts = []
        if "oil_spike_pct" in triggers:
            cl = prices.get("CL=F")
            if cl is not None and len(cl) >= 22:
                try:
                    ret = float(cl.iloc[-1] / cl.iloc[-22] - 1)
                    parts.append(f"Oil 1M: {ret:+.1%} (threshold {triggers['oil_spike_pct']:.0%})")
                except Exception:
                    parts.append("Oil data unavailable")
        if "vix_threshold" in triggers:
            vix = prices.get("^VIX")
            if vix is not None and len(vix) > 0:
                try:
                    v = float(vix.iloc[-1])
                    parts.append(f"VIX: {v:.1f} (threshold {triggers['vix_threshold']})")
                except Exception:
                    parts.append("VIX unavailable")
        if "dxy_rise_1m" in triggers or "dxy_spike" in triggers:
            dxy = prices.get("DX-Y.NYB")
            if dxy is not None and len(dxy) >= 22:
                try:
                    ret = float(dxy.iloc[-1] / dxy.iloc[-22] - 1)
                    parts.append(f"DXY 1M: {ret:+.1%}")
                except Exception:
                    pass
        if "real_yield_>2.5" in triggers:
            try:
                dgs10 = float(fred.get("DGS10", {}).dropna().iloc[-1]) if hasattr(fred.get("DGS10"), "dropna") else 4.5
                t5yie = float(fred.get("T5YIE", {}).dropna().iloc[-1]) if hasattr(fred.get("T5YIE"), "dropna") else 2.4
                parts.append(f"Real Yield: {dgs10-t5yie:.2f}%")
            except Exception:
                pass
        if not parts:
            return "Monitoring macro conditions..."
        return " · ".join(parts)

    def _build_asset_scores(self, shock: Dict, prices: Dict) -> Dict:
        """Enrich shock dict with current price and direction."""
        scores = {}
        for ticker, expected_shock in shock.items():
            s = prices.get(ticker)
            current_px = None
            if s is not None and len(s) > 0:
                try:
                    current_px = float(s.iloc[-1])
                except Exception:
                    pass
            scores[ticker] = {
                "expected_shock": expected_shock,
                "current_px": current_px,
                "direction": "LONG" if expected_shock > 0 else "SHORT",
                "magnitude": abs(expected_shock),
                "transmission_score": min(100, abs(expected_shock) * 500),
            }
        return scores


def run_scenario_discovery(prices: Dict, fred: Dict, news_analysis: Dict, quad: str = "Q3") -> Dict:
    engine = ScenarioDiscoveryEngine()
    return engine.run(prices, fred, news_analysis, quad)
