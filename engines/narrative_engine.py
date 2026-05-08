"""engines/narrative_engine.py - Thematic Narrative Scoring v3

Hedgeye narrative framework:
- Active = confirmed, in ETF Pro
- Building = traction, approaching critical mass  
- Brewing = pre-consensus, highest alpha when right
- Score = conviction x regime fit x breadth confirmation

Narratives are NOT sectors. They are cross-sector demand themes.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
import numpy as np

from config.settings import QUAD_ASSET_PERFORMANCE, TICKER_SECTOR

# Narrative Universe (12 core Hedgeye themes)
NARRATIVES: Dict[str, dict] = {
    "AI Infrastructure": {
        "thesis": "Data center build-out creates bottleneck in power, networking, optics, packaging. Demand river meets capacity constraint.",
        "sectors": ["ai_compute", "ai_networking", "ai_optics", "ai_power", "ai_power_infra", "ai_packaging"],
        "tickers": ["NVDA", "AMD", "AVGO", "TSM", "CRDO", "MRVL", "ANET", "SMCI", "LITE", "COHR", "CIEN", "POET", "VIAV", "ON", "WOLF", "STM", "VST", "CEG", "ETN", "VRT", "GEV", "EMR", "AMKR", "ASX", "TSEM", "MKSI", "RMBS", "QCOM", "MU", "APH", "MCHP", "ENTG", "KLIC", "UCTT", "CAMT"],
        "invalidators": ["Data center capex cut", "NVDA guidance miss", "Power utility rate case denial", "AI bubble narrative peak"],
        "quad_fit": {"Q1": 0.85, "Q2": 0.75, "Q3": 0.50, "Q4": 0.30},
    },
    "Defense & National Security": {
        "thesis": "Geopolitical escalation + NATO spending mandates = secular defense upcycle. Budgets are sticky.",
        "sectors": ["defense"],
        "tickers": ["PLTR", "AXON", "SAIC", "BWXT", "LMT", "RTX", "NOC", "GD", "KTOS", "HII", "LDOS", "BAH", "ITA"],
        "invalidators": ["Ceasefire in Ukraine", "US defense budget freeze", "Peace dividend narrative"],
        "quad_fit": {"Q1": 0.55, "Q2": 0.65, "Q3": 0.78, "Q4": 0.62},
    },
    "Precious Metals Supercycle": {
        "thesis": "De-dollarization + central bank buying + stagflation hedge = structural bid for gold/silver. Silver industrial demand adds beta.",
        "sectors": ["precious_metals", "precious_metals_miners"],
        "tickers": ["GLD", "SLV", "PPLT", "GDX", "GDXJ", "SIL", "SILJ", "AEM", "WPM", "FNV", "RGLD", "NEM", "GFI", "DUST"],
        "invalidators": ["DXY Bullish TREND breakout", "Real yields spike >3%", "Fed hawkish pivot", "Crypto steals safe-haven flow"],
        "quad_fit": {"Q1": 0.70, "Q2": 0.68, "Q3": 0.88, "Q4": 0.82},
    },
    "Energy Offense": {
        "thesis": "OPEC+ discipline + SPR refill + geopolitical risk premium = oil supply constrained. Refining margins tight. E&P FCF yields attract capital.",
        "sectors": ["energy_infra", "oil_services"],
        "tickers": ["XLE", "OIH", "XOP", "BNO", "USO", "XOM", "CVX", "COP", "SLB", "HAL", "BKR", "OXY", "MPC", "VLO", "PSX", "KMI", "DAR", "MTDR"],
        "invalidators": ["Saudi price war", "Global recession demand collapse", "Iran supply surge", "EV adoption shock"],
        "quad_fit": {"Q1": 0.55, "Q2": 0.88, "Q3": 0.75, "Q4": 0.30},
    },
    "Bitcoin & Digital Assets": {
        "thesis": "Halving supply shock + ETF inflows + DXY Bearish TREND = BTC Bullish TREND. Keith: 'Any quad other than Q4, bitcoin = biggest digital asset position.'",
        "sectors": ["generic"],
        "tickers": ["IBIT", "FBTC", "BTC-USD", "MSTR", "MSTY", "BITS", "BLOK", "WGMI"],
        "invalidators": ["Q4 structural quad", "DXY Bullish TREND", "SEC enforcement wave", "Miner capitulation"],
        "quad_fit": {"Q1": 0.90, "Q2": 0.85, "Q3": 0.50, "Q4": 0.10},
    },
    "Healthcare Innovation": {
        "thesis": "GLP-1 obesity wave + medtech aging demographics + defensive cash flows. Q3 best sector.",
        "sectors": ["healthcare_eq", "pharma"],
        "tickers": ["XLV", "LLY", "MRNA", "REGN", "BMY", "PFE", "JNJ", "ABBV", "MRK", "AZN", "NVO", "ISRG", "ABT", "BSX", "MDT", "EW", "SYK", "ZBH", "DXCM", "PODD", "RMD"],
        "invalidators": ["Medicare drug pricing reform", "FDA rejection cluster", "Biotech funding freeze"],
        "quad_fit": {"Q1": 0.65, "Q2": 0.55, "Q3": 0.85, "Q4": 0.80},
    },
    "Water & Utilities": {
        "thesis": "Climate stress + infrastructure age + AI data center water demand = rate base growth. Defensive yield + inflation passthrough.",
        "sectors": ["water", "utilities"],
        "tickers": ["XLU", "AWK", "WTRG", "CWT", "NEE", "DUK", "D", "SO", "AEP", "EXC", "SRE", "PEG", "ED", "GRID"],
        "invalidators": ["Rate shock >200bps", "Regulatory disallowance", "Mild weather year"],
        "quad_fit": {"Q1": 0.50, "Q2": 0.45, "Q3": 0.82, "Q4": 0.86},
    },
    "Housing & Rate Sensitivity": {
        "thesis": "Mortgage rate peak + household formation + supply deficit = construction cycle. Rate-cut beta when Fed pivots.",
        "sectors": ["housing"],
        "tickers": ["ITB", "XHB", "DHI", "LEN", "PHM", "NVR"],
        "invalidators": ["30yr mortgage >8%", "Home price crash", "Credit crunch in non-agency"],
        "quad_fit": {"Q1": 0.72, "Q2": 0.78, "Q3": 0.45, "Q4": 0.35},
    },
    "Indonesia Commodity Play": {
        "thesis": "Nickel dominance + CPO cycle + OSV hulu recovery + coal baseline. IHSG as EM commodity proxy.",
        "sectors": ["generic"],
        "tickers": ["EIDO", "^JKSE", "ANTM.JK", "INCO.JK", "MDKA.JK", "TINS.JK", "BRMS.JK", "NCKL.JK", "AALI.JK", "LSIP.JK", "SSMS.JK", "WINS.JK", "LEAD.JK", "SHIP.JK", "ELSA.JK", "ADRO.JK", "PTBA.JK", "ITMG.JK"],
        "invalidators": ["Nickel price collapse", "CPO export ban", "Rupiah crisis >17000", "China demand cliff"],
        "quad_fit": {"Q1": 0.70, "Q2": 0.65, "Q3": 0.55, "Q4": 0.40},
    },
    "Steel & Industrial Metals": {
        "thesis": "Infrastructure reshoring + energy transition copper demand + China stimulus = metals bid. Steel consolidation improves pricing power.",
        "sectors": ["steel", "generic"],
        "tickers": ["SLX", "CPER", "JJC", "HG=F", "ALI=F", "ZNC=F"],
        "invalidators": ["China property crash deepening", "Dollar spike", "Global manufacturing PMI <45"],
        "quad_fit": {"Q1": 0.65, "Q2": 0.82, "Q3": 0.55, "Q4": 0.25},
    },
    "Uranium & Nuclear": {
        "thesis": "SMR deployment + baseload reliability + decarbonization mandate = uranium demand structural. Supply deficit until 2028.",
        "sectors": ["uranium"],
        "tickers": ["URA", "CCJ", "NXE", "UUUU", "LEU", "DNN", "URG"],
        "invalidators": ["Fukushima-style accident", "SMR cost overrun", "Grid-scale battery breakthrough"],
        "quad_fit": {"Q1": 0.70, "Q2": 0.80, "Q3": 0.65, "Q4": 0.50},
    },
    "Staples & Consumer Defense": {
        "thesis": "Margin recovery from input cost deflation + pricing power in oligopoly categories. Q3/Q4 defensive anchor.",
        "sectors": ["staples"],
        "tickers": ["XLP", "PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "GIS", "K", "HSY", "MDLZ", "BRBR", "ULS"],
        "invalidators": ["Private label share explosion", "Input cost re-inflation", "Volume elasticity shock"],
        "quad_fit": {"Q1": 0.45, "Q2": 0.40, "Q3": 0.78, "Q4": 0.82},
    },
}

# Cross-narrative spillover (correlation risk)
NARRATIVE_SPILLOVER: Dict[str, List[str]] = {
    "AI Infrastructure": ["Energy Offense", "Water & Utilities"],
    "Precious Metals Supercycle": ["Bitcoin & Digital Assets", "Staples & Consumer Defense"],
    "Energy Offense": ["Steel & Industrial Metals", "Indonesia Commodity Play"],
    "Bitcoin & Digital Assets": ["Precious Metals Supercycle"],
    "Healthcare Innovation": ["Staples & Consumer Defense", "Water & Utilities"],
    "Housing & Rate Sensitivity": ["Steel & Industrial Metals", "Water & Utilities"],
    "Uranium & Nuclear": ["Energy Offense", "Water & Utilities"],
    "Defense & National Security": ["AI Infrastructure", "Steel & Industrial Metals"],
}

class NarrativeEngine:
    """
    Score narratives by:
    1. Regime fit (quad alignment)
    2. Breadth confirmation (% of tickers in bullish TRADE)
    3. Momentum persistence (Hurst > 0.5)
    4. Volume validation
    """

    def run(
        self,
        structural_quad: str,
        monthly_quad: str,
        risk_ranges: Dict[str, dict],
        prices: Dict[str, object],
    ) -> Dict[str, object]:

        active = []
        building = []
        brewing = []

        for name, meta in NARRATIVES.items():
            sq_fit = meta["quad_fit"].get(structural_quad, 0.50)
            mq_fit = meta["quad_fit"].get(monthly_quad, 0.50)
            regime_fit = 0.60 * sq_fit + 0.40 * mq_fit

            tickers = meta["tickers"]
            bullish_count = 0; bearish_count = 0; total = 0
            momentum_score = 0.0; vol_score = 0.0
            best_tickers = []; worst_tickers = []

            for t in tickers:
                rr = risk_ranges.get(t)
                if rr is None: continue
                total += 1
                comp = rr.get("composite", "neutral")
                hurst = rr.get("trend", {}).get("hurst", 0.5)
                vc = rr.get("trade", {}).get("volume_confirm", 0.5)
                stretch = rr.get("trade", {}).get("stretch", "neutral")

                if comp == "bullish":
                    bullish_count += 1
                    momentum_score += hurst
                    vol_score += vc
                    if stretch in ("oversold", "reset_zone"):
                        best_tickers.append(t)
                elif comp == "bearish":
                    bearish_count += 1
                    if stretch in ("overbought", "extended"):
                        worst_tickers.append(t)

            if total == 0: continue
            breadth = bullish_count / total
            bear_breadth = bearish_count / total
            avg_mom = momentum_score / max(bullish_count, 1)
            avg_vol = vol_score / max(bullish_count, 1)

            score = regime_fit * (0.40 + 0.35 * breadth + 0.15 * avg_mom + 0.10 * avg_vol)

            if score > 0.60 and breadth > 0.55 and avg_mom > 0.5:
                active.append({
                    "name": name, "score": round(score, 3), "stage": "active",
                    "thesis": meta["thesis"], "tickers": tickers,
                    "best": best_tickers[:10], "worst": worst_tickers[:10],
                    "invalidators": meta["invalidators"],
                    "breadth": round(breadth, 2), "regime_fit": round(regime_fit, 2),
                })
            elif score > 0.45 and (breadth > 0.40 or avg_mom > 0.5):
                building.append({
                    "name": name, "score": round(score, 3), "stage": "building",
                    "thesis": meta["thesis"], "tickers": tickers,
                    "best": best_tickers[:8], "worst": worst_tickers[:8],
                    "invalidators": meta["invalidators"],
                    "breadth": round(breadth, 2), "regime_fit": round(regime_fit, 2),
                })
            elif score > 0.30:
                brewing.append({
                    "name": name, "score": round(score, 3), "stage": "brewing",
                    "thesis": meta["thesis"], "tickers": tickers,
                    "best": best_tickers[:6], "worst": worst_tickers[:6],
                    "invalidators": meta["invalidators"],
                    "breadth": round(breadth, 2), "regime_fit": round(regime_fit, 2),
                })

        active.sort(key=lambda x: -x["score"])
        building.sort(key=lambda x: -x["score"])
        brewing.sort(key=lambda x: -x["score"])

        return dict(
            active_narratives=active,
            building_narratives=building,
            brewing_narratives=brewing,
            spillover=NARRATIVE_SPILLOVER,
            total=len(active) + len(building) + len(brewing),
        )

    def reactive_ignition(self, narrative_name: str, risk_ranges: Dict) -> Optional[dict]:
        meta = NARRATIVES.get(narrative_name)
        if not meta: return None
        tickers = meta["tickers"]
        bullish = sum(1 for t in tickers if risk_ranges.get(t, {}).get("composite") == "bullish")
        total = len([t for t in tickers if t in risk_ranges])
        if total == 0: return None
        breadth = bullish / total
        return {
            "name": narrative_name,
            "ignition_probability": round(np.clip(breadth * 1.5, 0, 1), 2),
            "breadth": round(breadth, 2),
            "needed_for_active": max(0, 0.55 - breadth),
        }
