"""engines/interconnect_engine.py — Causal Cascade & Interconnect Monitor
Maps how events flow through the system: geopolitical → commodity → sector → macro → policy → asset repricing.
"""
from __future__ import annotations
import math, logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np

logger = logging.getLogger("interconnect")

# Predefined causal chains
CAUSAL_CHAINS = {
    "war_middle_east": {
        "trigger": "Middle East conflict / Iran sanctions",
        "shock": {"oil": +0.20, "gas": +0.25, "gold": +0.10},
        "sector_cascade": [
            ("energy", +0.15, 0),      # immediate
            ("shipping", +0.20, 7),     # 1 week lag
            ("airlines", -0.15, 14),   # 2 weeks lag
            ("defense", +0.10, 3),      # 3 days lag
            ("consumer", -0.05, 30),    # 1 month lag
        ],
        "macro_feedback": {"inflation": +0.30, "cpi_sticky": True, "fed_hawkish": +0.20},
        "asset_repricing": {
            "CL=F": {"direction": "LONG", "magnitude": +0.20, "timeframe": "1-2w"},
            "GC=F": {"direction": "LONG", "magnitude": +0.10, "timeframe": "2-4w"},
            "XLE": {"direction": "LONG", "magnitude": +0.15, "timeframe": "1-2w"},
            "FRO": {"direction": "LONG", "magnitude": +0.25, "timeframe": "2-4w"},
            "UAL": {"direction": "SHORT", "magnitude": -0.15, "timeframe": "2-4w"},
            "XLY": {"direction": "SHORT", "magnitude": -0.08, "timeframe": "1-2M"},
            "TLT": {"direction": "SHORT", "magnitude": -0.10, "timeframe": "1-2M"},
        },
        "em_impact": {"DXY": +0.03, "EM": -0.10, "rupiah": -0.05},
    },
    "china_taiwan": {
        "trigger": "China-Taiwan escalation / chip sanctions",
        "shock": {"semiconductors": -0.30, "tech": -0.15, "gold": +0.08},
        "sector_cascade": [
            ("semis", -0.25, 0),
            ("tech", -0.15, 3),
            ("defense", +0.12, 7),
            ("materials", +0.10, 14),
        ],
        "macro_feedback": {"inflation": +0.10, "supply_chain": True, "fed_patience": True},
        "asset_repricing": {
            "NVDA": {"direction": "SHORT", "magnitude": -0.20, "timeframe": "1-2w"},
            "TSM": {"direction": "SHORT", "magnitude": -0.25, "timeframe": "1-2w"},
            "SMH": {"direction": "SHORT", "magnitude": -0.18, "timeframe": "1-2w"},
            "LMT": {"direction": "LONG", "magnitude": +0.10, "timeframe": "2-4w"},
            "GC=F": {"direction": "LONG", "magnitude": +0.08, "timeframe": "2-4w"},
        },
        "em_impact": {"DXY": +0.02, "EM": -0.08, "rupiah": -0.03},
    },
    "fed_hawkish": {
        "trigger": "Fed hawkish pivot / rate hike surprise",
        "shock": {"rates": +0.50, "dxy": +0.05, "tech": -0.20},
        "sector_cascade": [
            ("tech", -0.20, 0),
            ("growth", -0.18, 0),
            ("financials", +0.08, 7),
            ("utilities", +0.05, 14),
            ("reits", -0.12, 7),
        ],
        "macro_feedback": {"dxy_rise": True, "em_stress": True, "credit_tightening": True},
        "asset_repricing": {
            "QQQ": {"direction": "SHORT", "magnitude": -0.15, "timeframe": "1-2w"},
            "IWM": {"direction": "SHORT", "magnitude": -0.12, "timeframe": "1-2w"},
            "XLF": {"direction": "LONG", "magnitude": +0.08, "timeframe": "2-4w"},
            "TLT": {"direction": "SHORT", "magnitude": -0.15, "timeframe": "1-2w"},
            "GLD": {"direction": "LONG", "magnitude": +0.05, "timeframe": "2-4w"},
            "UUP": {"direction": "LONG", "magnitude": +0.05, "timeframe": "1-2w"},
        },
        "em_impact": {"DXY": +0.05, "EM": -0.12, "rupiah": -0.08},
    },
    "recession_signal": {
        "trigger": "Recession signal (yield curve, PMI, jobs)",
        "shock": {"yields": -0.30, "equity": -0.15, "credit": +0.20},
        "sector_cascade": [
            ("cyclicals", -0.20, 0),
            ("financials", -0.15, 7),
            ("defensives", +0.10, 3),
            ("gold", +0.08, 0),
            ("treasuries", +0.12, 0),
        ],
        "macro_feedback": {"fed_cuts": True, "dxy_fall": True, "flight_to_safety": True},
        "asset_repricing": {
            "SPY": {"direction": "SHORT", "magnitude": -0.12, "timeframe": "2-4w"},
            "QQQ": {"direction": "SHORT", "magnitude": -0.18, "timeframe": "2-4w"},
            "XLE": {"direction": "SHORT", "magnitude": -0.15, "timeframe": "1-2M"},
            "XLU": {"direction": "LONG", "magnitude": +0.08, "timeframe": "2-4w"},
            "TLT": {"direction": "LONG", "magnitude": +0.12, "timeframe": "1-2w"},
            "GLD": {"direction": "LONG", "magnitude": +0.10, "timeframe": "1-2w"},
        },
        "em_impact": {"DXY": -0.03, "EM": +0.05, "rupiah": +0.03},
    },
    "ai_bottleneck": {
        "trigger": "AI infrastructure bottleneck (HBM, power, transformers)",
        "shock": {"memory": +0.30, "power": +0.25, "optical": +0.15},
        "sector_cascade": [
            ("semis", +0.20, 0),
            ("power", +0.25, 7),
            ("optical", +0.15, 14),
            ("data_center", +0.10, 30),
            ("cloud", -0.05, 60),
        ],
        "macro_feedback": {"capex_inflation": True, "productivity_boost": True, "long_term_growth": True},
        "asset_repricing": {
            "MU": {"direction": "LONG", "magnitude": +0.25, "timeframe": "2-4w"},
            "VST": {"direction": "LONG", "magnitude": +0.20, "timeframe": "1-2M"},
            "COHR": {"direction": "LONG", "magnitude": +0.15, "timeframe": "2-4w"},
            "NVDA": {"direction": "LONG", "magnitude": +0.10, "timeframe": "1-2M"},
            "AMZN": {"direction": "SHORT", "magnitude": -0.05, "timeframe": "2-3M"},
        },
        "em_impact": {"DXY": 0, "EM": +0.02, "rupiah": 0},
    },
}

def _detect_active_scenarios(prices: Dict[str, pd.Series], fred: Dict[str, pd.Series], news_analysis: dict) -> List[str]:
    """Detect which scenarios are currently active based on market conditions."""
    active = []

    # Check oil spike
    cl_s = prices.get("CL=F")
    if cl_s is not None and len(cl_s) >= 22:
        try:
            s_clean = pd.to_numeric(cl_s, errors="coerce").dropna()
            if len(s_clean) >= 22:
                r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1)
                if r1m > 0.10:
                    active.append("war_middle_east")
        except Exception:
            pass

    # Check tech selloff
    qqq_s = prices.get("QQQ")
    if qqq_s is not None and len(qqq_s) >= 22:
        try:
            s_clean = pd.to_numeric(qqq_s, errors="coerce").dropna()
            if len(s_clean) >= 22:
                r1m = float(s_clean.iloc[-1] / s_clean.iloc[-22] - 1)
                vix_s = prices.get("^VIX")
                vix_high = False
                if vix_s is not None:
                    vix_clean = pd.to_numeric(vix_s, errors="coerce").dropna()
                    if len(vix_clean) > 0 and float(vix_clean.iloc[-1]) > 25:
                        vix_high = True
                if r1m < -0.10 and vix_high:
                    active.append("recession_signal")
                elif r1m < -0.08:
                    active.append("fed_hawkish")
        except Exception:
            pass

    # Check news for geopolitical keywords
    if news_analysis and news_analysis.get("emergent_narratives"):
        for en in news_analysis["emergent_narratives"]:
            theme = en.get("name", "").lower()
            if any(k in theme for k in ["iran", "middle east", "oil", "sanctions", "war"]):
                if "war_middle_east" not in active:
                    active.append("war_middle_east")
            if any(k in theme for k in ["china", "taiwan", "chip", "semiconductor"]):
                if "china_taiwan" not in active:
                    active.append("china_taiwan")
            if any(k in theme for k in ["ai", "bottleneck", "power", "transformer", "hbm"]):
                if "ai_bottleneck" not in active:
                    active.append("ai_bottleneck")

    # Check FRED for recession signals
    dgs10 = fred.get("DGS10")
    dgs2 = fred.get("DGS2")
    if dgs10 is not None and dgs2 is not None and not dgs10.empty and not dgs2.empty:
        try:
            spread = float(dgs10.dropna().iloc[-1]) - float(dgs2.dropna().iloc[-1])
            if spread < 0 and "recession_signal" not in active:
                active.append("recession_signal")
        except Exception:
            pass

    return active

def run_interconnect(prices: Dict[str, pd.Series], fred: Dict[str, pd.Series], 
                     news_analysis: dict, quad: str) -> Dict:
    """Main entry point. Returns active scenarios + cascade map."""
    active = _detect_active_scenarios(prices, fred, news_analysis)

    scenarios = []
    for scenario_key in active:
        chain = CAUSAL_CHAINS.get(scenario_key)
        if not chain:
            continue

        # Calculate transmission scores for affected tickers
        asset_scores = {}
        for ticker, impact in chain.get("asset_repricing", {}).items():
            s = prices.get(ticker)
            if s is not None and len(s) >= 2:
                try:
                    s_clean = pd.to_numeric(s, errors="coerce").dropna()
                    px = float(s_clean.iloc[-1])
                    target_px = px * (1 + impact["magnitude"])
                    asset_scores[ticker] = {
                        "direction": impact["direction"],
                        "current": round(px, 2),
                        "target": round(target_px, 2),
                        "magnitude": impact["magnitude"],
                        "timeframe": impact["timeframe"],
                        "transmission_score": min(100, max(0, abs(impact["magnitude"]) * 500)),
                    }
                except Exception:
                    pass

        # Sort by transmission score
        sorted_assets = sorted(asset_scores.items(), key=lambda x: x[1]["transmission_score"], reverse=True)

        scenarios.append({
            "scenario": scenario_key,
            "trigger": chain["trigger"],
            "active": True,
            "confidence": 0.7 if len(active) == 1 else 0.5,
            "shock": chain["shock"],
            "sector_cascade": chain["sector_cascade"],
            "macro_feedback": chain["macro_feedback"],
            "asset_scores": dict(sorted_assets[:10]),
            "em_impact": chain["em_impact"],
            "lead_tickers": [t for t, _ in sorted_assets[:5]],
            "lag_tickers": [t for t, _ in sorted_assets[5:10]],
        })

    # If no active scenarios, return "all clear" with highest risk scenario
    if not scenarios:
        highest_risk = "recession_signal" if quad in ["Q3", "Q4"] else "fed_hawkish" if quad == "Q2" else "ai_bottleneck"
        chain = CAUSAL_CHAINS.get(highest_risk)
        scenarios.append({
            "scenario": highest_risk,
            "trigger": chain["trigger"] if chain else "Unknown",
            "active": False,
            "confidence": 0.3,
            "shock": chain["shock"] if chain else {},
            "sector_cascade": chain["sector_cascade"] if chain else [],
            "macro_feedback": chain["macro_feedback"] if chain else {},
            "asset_scores": {},
            "em_impact": chain["em_impact"] if chain else {},
            "lead_tickers": [],
            "lag_tickers": [],
        })

    return {
        "active_scenarios": [s["scenario"] for s in scenarios if s["active"]],
        "watch_scenarios": [s["scenario"] for s in scenarios if not s["active"]],
        "scenarios": scenarios,
        "total_active": len([s for s in scenarios if s["active"]]),
        "highest_risk": scenarios[0]["scenario"] if scenarios else "unknown",
        "summary": f"{len([s for s in scenarios if s['active']])} active cascade(s) detected" if any(s["active"] for s in scenarios) else "No active cascades — monitoring",
    }
