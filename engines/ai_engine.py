"""engines/ai_engine.py — Autonomous Intelligence Layer (RULE-BASED, NO API)

Generates narratives, bottlenecks, alpha ideas, and scenario updates
purely from snapshot data. Zero external API calls. Self-contained.
"""
from __future__ import annotations

import logging
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_AI_CACHE: Dict = {}
_AI_CACHE_TS: float = 0.0
_AI_CACHE_TTL: float = 6 * 3600

# ── Regime-driven narrative templates ──────────────────────────────────────────
NARRATIVE_TEMPLATES = {
    "Q1": [
        {
            "name": "Tech & Crypto Momentum",
            "score": 0.85,
            "stage": "active",
            "thesis": "Goldilocks regime supports growth assets. Easing inflation + accelerating growth = ideal for tech and crypto. Dips are buying opportunities.",
            "regime_bias": "Q1",
            "tickers": ["QQQ","IBIT","MAGS","XLK","IWM"],
            "best": ["QQQ","IBIT","MAGS"],
            "worst": ["TLT","XLU"],
            "invalidators": ["Inflation re-accelerates above 3.5%","GDP growth turns negative"],
            "news_catalyst": "Fed dovish pivot + strong earnings",
        },
        {
            "name": "Small Cap Breakout",
            "score": 0.72,
            "stage": "building",
            "thesis": "Rate cut expectations favor smaller companies with floating-rate debt. Russell 2000 showing relative strength.",
            "regime_bias": "Q1",
            "tickers": ["IWM","RSP","VTI"],
            "best": ["IWM","RSP"],
            "worst": ["QQQ","XLK"],
            "invalidators": ["Credit spreads widen >200bps","Recession signal triggers"],
            "news_catalyst": "CPI cooling + credit expansion",
        },
    ],
    "Q2": [
        {
            "name": "Energy Offense",
            "score": 0.88,
            "stage": "active",
            "thesis": "Reflation regime = energy and commodities win. Oil services have operating leverage. Inflation hedges outperform.",
            "regime_bias": "Q2",
            "tickers": ["XLE","OIH","BNO","XOP","DAR","MTDR"],
            "best": ["OIH","BNO","XOP"],
            "worst": ["XLU","XLP","TLT"],
            "invalidators": ["Oil demand collapse","Q4 deflation signal"],
            "news_catalyst": "OPEC cuts + industrial demand rebound",
        },
        {
            "name": "International Rotation",
            "score": 0.80,
            "stage": "active",
            "thesis": "USD bearish trend supports EM and international equities. Diversify away from US concentration risk.",
            "regime_bias": "Q2",
            "tickers": ["JPXN","EIS","TUR","NORW","EWZ","GLIN"],
            "best": ["JPXN","EIS","TUR"],
            "worst": ["SPY","IWM"],
            "invalidators": ["DXY bullish reversal","Global recession"],
            "news_catalyst": "Yen weakness + EM capital inflows",
        },
        {
            "name": "Commodity Supercycle",
            "score": 0.78,
            "stage": "building",
            "thesis": "Industrial metals and energy bid by reflation. Supply constraints + rising demand = structural tailwind.",
            "regime_bias": "Q2",
            "tickers": ["SLV","GDX","GDXJ","CPER","SLX"],
            "best": ["SLV","GDXJ","CPER"],
            "worst": ["XLK","MAGS"],
            "invalidators": ["China hard landing","Q4 deflation"],
            "news_catalyst": "China stimulus + green energy demand",
        },
        {
            "name": "Bitcoin Reflation",
            "score": 0.75,
            "stage": "active",
            "thesis": "Every quad except Q4 = long Bitcoin. DXY bearish correlation supports crypto bid. Institutional adoption accelerates.",
            "regime_bias": "Q2",
            "tickers": ["IBIT","FBTC","BTC-USD"],
            "best": ["IBIT"],
            "worst": ["MSTY","BLOK"],
            "invalidators": ["Q4 signal","DXY bullish reversal"],
            "news_catalyst": "ETF inflows + halving supply shock",
        },
    ],
    "Q3": [
        {
            "name": "Gold & Silver Defense",
            "score": 0.92,
            "stage": "active",
            "thesis": "Stagflation = most dangerous regime. Gold and silver are the single best assets. Central bank buying at record pace.",
            "regime_bias": "Q3",
            "tickers": ["GLD","SLV","GDX","GDXJ","SILJ"],
            "best": ["GLD","SLV","GDX"],
            "worst": ["XLK","MAGS","QQQ"],
            "invalidators": ["Q4→Q1 direct transition","DXY strong bullish reversal"],
            "news_catalyst": "De-dollarization + geopolitical hedging",
        },
        {
            "name": "Defense Reshoring",
            "score": 0.85,
            "stage": "active",
            "thesis": "NATO commitments + geopolitical premium = defense secular bid. ITA/LMT/KTOS work in ALL quads but especially Q3.",
            "regime_bias": "Q3",
            "tickers": ["ITA","LMT","RTX","KTOS","PLTR"],
            "best": ["ITA","KTOS"],
            "worst": ["XLU"],
            "invalidators": ["Global peace agreement","Defense budget cuts"],
            "news_catalyst": "NATO 2% GDP + Indo-Pacific tension",
        },
        {
            "name": "AI Power Infrastructure",
            "score": 0.78,
            "stage": "building",
            "thesis": "AI data centers need 24/7 firm power. Nuclear + gas = only scalable solution. Long-term contracts secured.",
            "regime_bias": "Q3",
            "tickers": ["VST","CEG","GEV","ETN","VRT"],
            "best": ["VST","CEG"],
            "worst": ["INTC","SMCI"],
            "invalidators": ["AI capex cycle pause","Regulatory block on nuclear"],
            "news_catalyst": "NVIDIA $2B photonics commitment + data center buildout",
        },
        {
            "name": "Indonesia Commodity Play",
            "score": 0.65,
            "stage": "brewing",
            "thesis": "EIDO = coal + nickel + CPO + geothermal. Q3 stagflation = commodity bid. PGEO geothermal = renewable hybrid.",
            "regime_bias": "Q3",
            "tickers": ["EIDO","PGEO.JK","ADRO.JK","NCKL.JK"],
            "best": ["EIDO","PGEO.JK"],
            "worst": ["TLKM.JK"],
            "invalidators": ["China demand collapse","Q4 deflation"],
            "news_catalyst": "Pertamina hulu expansion + nickel EV demand",
        },
    ],
    "Q4": [
        {
            "name": "Bond & Gold Safety",
            "score": 0.90,
            "stage": "active",
            "thesis": "Deflation = both growth and inflation falling. Government bonds and gold win. Cash is king. Avoid risk.",
            "regime_bias": "Q4",
            "tickers": ["TLT","GLD","XLU","VZ"],
            "best": ["TLT","GLD","XLU"],
            "worst": ["QQQ","IWM","XLE"],
            "invalidators": ["Fed emergency cut ends","Q1 signal triggers"],
            "news_catalyst": "Recession confirmation + credit event",
        },
        {
            "name": "Dollar Strength Play",
            "score": 0.75,
            "stage": "active",
            "thesis": "Deflationary collapse drives flight to USD. DXY bullish = short EM and commodities. Long dollar proxies.",
            "regime_bias": "Q4",
            "tickers": ["UUP","DX-Y.NYB"],
            "best": ["UUP"],
            "worst": ["EEM","EIDO","BNO"],
            "invalidators": ["Fed prints money","Q1 signal"],
            "news_catalyst": "Credit crunch + global deleveraging",
        },
    ],
}

# ── Bottleneck templates ──────────────────────────────────────────────────────
BOTTLENECK_TEMPLATES = {
    "ai_optics": {
        "name": "AI Photonics Bottleneck",
        "constraint": 0.97,
        "sector": "ai_optics",
        "thesis": "200G EML lasers supply-constrained. NVIDIA committed $2B to photonics. POET co-packaged optics removes thermal limits. Only LITE, COHR, CIEN scale.",
        "beneficiary_tickers": ["LITE","COHR","CIEN","VIAV"],
        "fade_tickers": ["INTC","SMCI"],
        "time_horizon": "months",
        "confidence": 0.88,
        "stage": "active",
    },
    "ai_power": {
        "name": "AI Power Infrastructure Bottleneck",
        "constraint": 0.85,
        "sector": "ai_power",
        "thesis": "AI data centers need 24/7 firm power. Nuclear + gas only scalable. VST, CEG, GEV winning long-term contracts. Grid capacity limited.",
        "beneficiary_tickers": ["VST","CEG","GEV","ETN","VRT"],
        "fade_tickers": ["INTC"],
        "time_horizon": "months",
        "confidence": 0.83,
        "stage": "active",
    },
    "precious_metals": {
        "name": "Silver Supply Squeeze",
        "constraint": 0.92,
        "sector": "precious_metals",
        "thesis": "Solar + AI chip silver demand accelerating. Mine supply flat. LBMA vault declining. Dual industrial + monetary demand.",
        "beneficiary_tickers": ["SLV","SILJ","SIL","GDXJ"],
        "fade_tickers": ["MSTY","BLOK"],
        "time_horizon": "months",
        "confidence": 0.85,
        "stage": "active",
    },
    "defense": {
        "name": "Defense Reshoring",
        "constraint": 0.78,
        "sector": "defense",
        "thesis": "NATO 2%+ GDP commitment. Geopolitical premium structural. ITA/LMT/KTOS secular long. Supply chain reshoring = bottleneck.",
        "beneficiary_tickers": ["ITA","LMT","RTX","KTOS","PLTR"],
        "fade_tickers": ["XLU"],
        "time_horizon": "months",
        "confidence": 0.82,
        "stage": "active",
    },
    "energy_infra": {
        "name": "Oil Services Capacity",
        "constraint": 0.72,
        "sector": "energy_infra",
        "thesis": "OPEC discipline + shale plateau = oil services bottleneck. Day rates rising. OIH/XOP operating leverage extreme.",
        "beneficiary_tickers": ["OIH","XOP","SLB","HAL"],
        "fade_tickers": ["XLE"],
        "time_horizon": "months",
        "confidence": 0.75,
        "stage": "building",
    },
}

# ── Helpers ───────────────────────────────────────────────────────────────────
def _safe_float(v):
    if v is None:
        return None
    try:
        import math
        f = float(v)
        return f if math.isfinite(f) else None
    except:
        return None

def _price_perf(s, days: int):
    if s is None or len(s) < days + 1:
        return None
    s = pd.to_numeric(s, errors="coerce").dropna()
    if len(s) < days + 1:
        return None
    try:
        return float(s.iloc[-1] / s.iloc[-(days + 1)] - 1)
    except:
        return None

def _detect_sector_momentum(prices, sector_map):
    sector_returns = {}
    for ticker, s in prices.items():
        sector = sector_map.get(ticker)
        if not sector:
            continue
        r = _price_perf(s, 21)
        if r is not None:
            sector_returns.setdefault(sector, []).append(r)
    return {sec: float(np.mean(rets)) for sec, rets in sector_returns.items() if rets}

def _build_narratives(sq, mq, gq, prices, sector_map, gip_features):
    base = []
    if sq in NARRATIVE_TEMPLATES:
        base.extend([{**n, "regime_bias": sq} for n in NARRATIVE_TEMPLATES[sq]])
    if mq != sq and mq in NARRATIVE_TEMPLATES:
        for n in NARRATIVE_TEMPLATES[mq]:
            if not any(b["name"] == n["name"] for b in base):
                base.append({**n, "regime_bias": mq, "score": n["score"] * 0.9})

    for narr in base:
        tickers = narr.get("tickers", [])
        returns = []
        for t in tickers:
            r = _price_perf(prices.get(t), 21)
            if r is not None:
                returns.append(r)
        if returns:
            avg_ret = float(np.mean(returns))
            if avg_ret > 0.05:
                narr["score"] = min(0.98, narr["score"] + 0.05)
                narr["stage"] = "active"
            elif avg_ret < -0.05:
                narr["score"] = max(0.3, narr["score"] - 0.10)
                narr["stage"] = "brewing"
        narr["ai_generated"] = False
        narr["source"] = "rule-based"

    return sorted(base, key=lambda x: x["score"], reverse=True)

def _build_bottlenecks(sq, mq, prices, sector_map):
    relevant_sectors = []
    if sq in ("Q2", "Q3"):
        relevant_sectors = ["precious_metals", "ai_optics", "ai_power", "defense", "energy_infra"]
    elif sq == "Q1":
        relevant_sectors = ["ai_optics", "ai_power", "energy_infra"]
    elif sq == "Q4":
        relevant_sectors = ["precious_metals", "defense"]

    btks = []
    for sector in relevant_sectors:
        tmpl = BOTTLENECK_TEMPLATES.get(sector)
        if not tmpl:
            continue
        ben_rets = []
        for t in tmpl["beneficiary_tickers"]:
            r = _price_perf(prices.get(t), 21)
            if r is not None:
                ben_rets.append(r)
        if ben_rets and np.mean(ben_rets) > 0.03:
            confidence = min(0.95, tmpl["confidence"] + 0.05)
            stage = "active"
        else:
            confidence = tmpl["confidence"]
            stage = tmpl["stage"]

        btks.append({
            **tmpl,
            "confidence": confidence,
            "stage": stage,
            "ai_generated": False,
            "source": "rule-based",
            "beneficiary_1m_avg": float(np.mean(ben_rets)) if ben_rets else None,
        })

    # Price-detected outliers
    sector_mom = _detect_sector_momentum(prices, sector_map)
    for ticker, s in prices.items():
        sector = sector_map.get(ticker)
        if not sector:
            continue
        sec_ret = sector_mom.get(sector, 0)
        tick_ret = _price_perf(s, 21)
        if tick_ret is None:
            continue
        if tick_ret > sec_ret * 2 and sec_ret > 0.05 and tick_ret > 0.10:
            if not any(b["sector"] == sector for b in btks):
                btks.append({
                    "name": f"{sector.replace('_', ' ').title()} Outperformance",
                    "constraint": 0.70,
                    "sector": sector,
                    "thesis": f"{ticker} up {tick_ret:+.1%} vs sector avg {sec_ret:+.1%}. Supply-demand imbalance detected.",
                    "beneficiary_tickers": [ticker],
                    "fade_tickers": [],
                    "time_horizon": "weeks",
                    "confidence": 0.65,
                    "stage": "building",
                    "ai_generated": False,
                    "source": "price-detection",
                })

    return sorted(btks, key=lambda x: x["confidence"], reverse=True)

def _build_alpha_ideas(sq, mq, prices, asset_ranges, sector_map):
    QUAD_BEST = {
        "Q1": ["QQQ", "IBIT", "MAGS", "XLK", "IWM", "RSP"],
        "Q2": ["XLE", "OIH", "BNO", "XOP", "JPXN", "EIS", "SLV", "GDXJ"],
        "Q3": ["GLD", "SLV", "GDX", "ITA", "KTOS", "VST", "CEG"],
        "Q4": ["TLT", "GLD", "XLU", "VZ", "UUP"],
    }

    best_tickers = list(dict.fromkeys(QUAD_BEST.get(sq, []) + (QUAD_BEST.get(mq, []) if mq != sq else [])))
    ideas = []

    for ticker in best_tickers:
        v = asset_ranges.get(ticker, {})
        tr = v.get("trade", {})
        px = _safe_float(v.get("px"))
        lrr = _safe_float(tr.get("lrr"))
        trr = _safe_float(tr.get("trr"))
        comp = v.get("composite", "neutral")
        qual = v.get("quality", "")

        if not (px and lrr and trr and trr > lrr):
            continue

        spread = trr - lrr
        pos = (px - lrr) / spread if spread > 0 else 0.5

        if comp == "bullish" and qual in ("A", "B", "C"):
            if pos <= 0.60:
                rr = round((lrr + spread * 0.50 - lrr) / max(lrr - (lrr - spread * 0.25), 0.01), 2)
                ideas.append({
                    "ticker": ticker,
                    "name": ticker,
                    "direction": "long",
                    "confidence": min(0.95, 0.60 + (0.15 if qual == "A" else 0.10 if qual == "B" else 0.05)),
                    "stage": "active" if pos <= 0.35 else "building",
                    "thesis": f"{sq} regime favors {ticker}. Risk range buy zone at ${lrr:.2f}. Signal grade {qual}.",
                    "regime_fit": f"Aligned with {sq} structural + {mq} monthly regime. Price at {pos:.0%} of range.",
                    "category": "Macro Rotation",
                    "invalidators": [f"Breaks below ${lrr:.2f} (LRR)", f"Regime shifts to {mq if mq != sq else 'Q4'}"],
                })

        elif comp == "bearish" and qual in ("short_A", "short_B", "short_C"):
            if pos >= 0.40:
                rr = round((trr - (trr - spread * 0.50)) / max((trr + spread * 0.25) - trr, 0.01), 2)
                ideas.append({
                    "ticker": ticker,
                    "name": ticker,
                    "direction": "short",
                    "confidence": min(0.90, 0.55 + (0.15 if qual == "short_A" else 0.10)),
                    "stage": "active" if pos >= 0.65 else "building",
                    "thesis": f"{sq} regime headwind for {ticker}. Risk range sell zone at ${trr:.2f}. Signal grade {qual}.",
                    "regime_fit": f"Counter-trend in {sq} structural + {mq} monthly. Price at {pos:.0%} of range.",
                    "category": "Macro Rotation",
                    "invalidators": [f"Breaks above ${trr:.2f} (TRR)", f"Regime shifts to Q1/Q2"],
                })

    # Momentum outliers
    for ticker, s in prices.items():
        if any(i["ticker"] == ticker for i in ideas):
            continue
        r1m = _price_perf(s, 21)
        r3m = _price_perf(s, 63)
        if r1m and r1m > 0.15 and r3m and r3m > 0.25:
            sector = sector_map.get(ticker, "unknown")
            ideas.append({
                "ticker": ticker,
                "name": ticker,
                "direction": "long",
                "confidence": 0.65,
                "stage": "building",
                "thesis": f"Strong momentum: +{r1m:.1%} 1M, +{r3m:.1%} 3M. Possible narrative acceleration.",
                "regime_fit": f"Sector: {sector.replace('_', ' ')}. Verify regime alignment before sizing.",
                "category": "Technical",
                "invalidators": ["Momentum reverses", "Volume dries up"],
            })

    return sorted(ideas, key=lambda x: x["confidence"], reverse=True)[:8]

def _build_scenario(sq, mq, gip_features, health, transition):
    flip = gip_features.get("flip_hazard", 0.2)
    gm = gip_features.get("growth_momentum", 0)
    im = gip_features.get("inflation_momentum", 0)

    if flip > 0.4:
        headline_risk = f"High regime change risk ({flip:.0%}). Monthly {mq} diverging from structural {sq}."
        opportunity = "Front-run the transition. Position for next regime early."
    elif gm > 0 and im > 0:
        headline_risk = "Inflation re-acceleration could force Fed hawkish pivot."
        opportunity = "Reflation trades: energy, commodities, international."
    elif gm < 0 and im > 0:
        headline_risk = "Stagflation deepening. Growth slowing while prices sticky."
        opportunity = "Defensive: gold, silver, utilities, defense."
    elif gm < 0 and im < 0:
        headline_risk = "Deflationary spiral risk. Credit event possible."
        opportunity = "Safety: bonds, gold, cash. Wait for Q1 signal."
    else:
        headline_risk = "Market chop. No clear direction. Reduce size."
        opportunity = "Range trade within risk ranges. Patience."

    if sq == "Q3" and mq == "Q2":
        regime_change_signal = "Watch CPI MoM < 0.2% + GDP acceleration = Q2→Q1 transition window"
    elif sq == "Q2" and mq == "Q3":
        regime_change_signal = "CPI > 0.4% MoM + ISM < 48 = Q2→Q3 transition risk"
    elif sq == "Q1" and mq == "Q2":
        regime_change_signal = "CPI re-acceleration > 3.5% + wage growth > 4% = Q1→Q2"
    elif sq == "Q4" and mq == "Q1":
        regime_change_signal = "ISM > 50 + CPI stabilizing < 2.5% = Q4→Q1 recovery"
    else:
        regime_change_signal = "Monthly alignment with structural = base case intact. Watch CPI + ISM."

    return {
        "headline_risk": headline_risk,
        "opportunity": opportunity,
        "regime_change_signal": regime_change_signal,
        "base_case_intact": (sq == mq) or (flip < 0.3),
    }

# ── Public API ───────────────────────────────────────────────────────────────
class AIEngine:
    def __init__(self, cache_ttl: float = _AI_CACHE_TTL):
        self.cache_ttl = cache_ttl

    def run(self, sq: str, mq: str, gq: str, gip_features: Dict,
            prices: Dict[str, pd.Series], force_refresh: bool = False,
            asset_ranges: Optional[Dict] = None,
            sector_map: Optional[Dict[str, str]] = None,
            health: Optional[Dict] = None,
            transition: Optional[object] = None) -> Dict:
        global _AI_CACHE, _AI_CACHE_TS

        if not force_refresh and _AI_CACHE and (time.time() - _AI_CACHE_TS) < self.cache_ttl:
            return {**_AI_CACHE, "from_cache": True}

        if sector_map is None:
            try:
                from config.settings import TICKER_SECTOR
                sector_map = TICKER_SECTOR
            except Exception:
                sector_map = {}

        t0 = time.time()
        narratives = _build_narratives(sq, mq, gq, prices, sector_map, gip_features)
        bottlenecks = _build_bottlenecks(sq, mq, prices, sector_map)
        alpha_ideas = _build_alpha_ideas(sq, mq, prices, asset_ranges or {}, sector_map)
        scenario = _build_scenario(sq, mq, gip_features, health, transition)

        result = {
            "ok": True,
            "elapsed": round(time.time() - t0, 2),
            "generated_at": time.time(),
            "model": "rule-based-v1",
            "narratives": narratives,
            "bottlenecks": bottlenecks,
            "alpha_ideas": alpha_ideas,
            "scenario_update": scenario,
        }

        _AI_CACHE = result
        _AI_CACHE_TS = time.time()

        logger.info(
            f"AIEngine: rule-based generated {len(narratives)} narratives, "
            f"{len(bottlenecks)} bottlenecks, {len(alpha_ideas)} alpha ideas "
            f"in {result['elapsed']}s"
        )

        return result