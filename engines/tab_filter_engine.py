"""engines/tab_filter_engine.py — Per-Market Filter Logic (Sprint 7)

Different markets need DIFFERENT filter logic:
  - US Stocks  → composite + thesis + smart money + Hedgeye Quad
  - Forex      → composite + DXY + rate differential + real yield + COT commercials
  - Commodities → composite + COT (commercial vs noncommercial) + USD inverse + supply chain
  - Crypto     → composite + 21d momentum + cycle stage + QQQ correlation
  - IHSG       → composite + USDIDR + commodity proxy + Indonesia sector
  - Alpha Center → cross-market: top thesis + smart money consensus + composite high-confidence

Output per ticker:
  {
    "passes_filter": bool,
    "filter_score": 0-100,
    "filter_rationale": str,
    "tab_specific_signals": dict,  # market-appropriate signals
    "primary_thesis": str,
    "direction": LONG/SHORT/NEUTRAL/AVOID,
    "confidence": float,
  }
"""
from __future__ import annotations

import math
import logging
from typing import Dict, List, Optional, Set

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════════════
# FILTER 1: US STOCKS
# ════════════════════════════════════════════════════════════════════════

def filter_us_stocks(
    ticker: str,
    composite_signal: Dict,
    thought_process: Dict,
    smart_money: Dict,  # kept for backwards compat but NOT scored
    risk_range: Dict,
    quad: str,
) -> Dict:
    """US Stock filter (v2.6 — Sprint 11 refactor):
      - Composite signal direction (35 pts) — direction + confidence
      - Methodology cumulative (40 pts) — Leopold/COATUE/Karsan/Yves/Soros/Druckenmiller/Tier1Alpha/profplum99/Citrini/Hedgeye/Schadner = 11 frameworks
      - Risk Range quality (15 pts)
      - Behavioral bonus (10 pts) — Yves narrative divergence + Soros stage alignment
    
    Smart Money endorsement REMOVED per Edward (don't care WHO holds it,
    care if it matches the METHODOLOGY).
    """
    out = {
        "ticker": ticker,
        "passes_filter": False,
        "filter_score": 0,
        "filter_rationale": [],
        "tab_specific_signals": {},
    }
    
    score = 0
    
    # 1. Composite signal direction (35 pts — slightly reduced from 40)
    direction = composite_signal.get("direction", "NEUTRAL")
    conf = composite_signal.get("confidence", 0)
    if direction in ("NEUTRAL", "AVOID"):
        out["filter_rationale"].append(f"❌ Composite: {direction}")
        return out
    
    composite_pts = min(35, conf * 45)
    score += composite_pts
    out["direction"] = direction
    out["confidence"] = conf
    out["filter_rationale"].append(f"✓ Composite {direction} (conf {conf:.0%}, +{composite_pts:.0f}pts)")
    
    if composite_signal.get("flipped_from_composite"):
        out["filter_rationale"].append("⚠️ Direction FLIPPED by multi-signal contradiction")
    
    # 2. Methodology cumulative score (40 pts — NEW weight)
    # thought_process now contains 11-framework breakdown
    methodology_score = thought_process.get("thesis_score", 0)
    n_matches = thought_process.get("n_matches", 0)
    
    if methodology_score > 0:
        # Scale: thesis_score 80+ = full 40pts, 60-79 = scaled
        meth_pts = min(40, methodology_score * 0.45)
        score += meth_pts
        out["filter_rationale"].append(
            f"✓ Methodology {methodology_score:.0f}/100 (matched {n_matches} frameworks: "
            f"{', '.join(thought_process.get('matched_frameworks', [])[:4])}) +{meth_pts:.0f}pts"
        )
        out["tab_specific_signals"]["thesis_frameworks"] = thought_process.get("matched_frameworks", [])
        out["tab_specific_signals"]["primary_role"] = thought_process.get("primary_role")
        out["tab_specific_signals"]["n_methodology_matches"] = n_matches
    
    # 3. Risk Range quality (15 pts)
    rr_quality = risk_range.get("quality", "C") if risk_range else "C"
    quality_pts = {"A+": 15, "A": 12, "B": 7, "C": 3}.get(rr_quality, 0)
    score += quality_pts
    out["filter_rationale"].append(f"✓ Risk Range quality: {rr_quality} (+{quality_pts}pts)")
    
    # 4. Behavioral bonus (10 pts) — Yves divergence + Soros alignment
    fb = thought_process.get("framework_breakdown", {})
    behavioral_pts = 0
    yves = fb.get("yves", {})
    if yves.get("narrative_divergence"):
        behavioral_pts += 6
        out["filter_rationale"].append(f"✓ Yves narrative divergence detected (+6pts)")
    soros = fb.get("soros", {})
    if soros.get("matched"):
        # Bonus if Soros stage favorable (Inception/Acceleration for LONGS)
        if direction == "LONG" and soros.get("stage") in ("INCEPTION", "ACCELERATION"):
            behavioral_pts += 4
            out["filter_rationale"].append(f"✓ Soros {soros.get('stage')} supports LONG (+4pts)")
        elif direction == "SHORT" and soros.get("stage") in ("TWILIGHT", "REVERSAL"):
            behavioral_pts += 4
            out["filter_rationale"].append(f"✓ Soros {soros.get('stage')} supports SHORT (+4pts)")
    score += behavioral_pts
    
    out["filter_score"] = round(score, 1)
    out["passes_filter"] = score >= 35  # threshold
    
    return out


# ════════════════════════════════════════════════════════════════════════
# FILTER 2: FOREX (different criteria than stocks!)
# ════════════════════════════════════════════════════════════════════════

# Currency-to-rate mapping (for carry calculation)
CURRENCY_BENCHMARK_RATE_KEY = {
    "EURUSD=X": ("EUR_RATE_PROXY", 3.5),  # ECB rate proxy
    "USDJPY=X": ("JPY_RATE_PROXY", 0.5),  # BoJ rate proxy
    "GBPUSD=X": ("GBP_RATE_PROXY", 4.5),  # BoE
    "USDIDR=X": ("IDR_RATE_PROXY", 6.0),  # BI rate
    "AUDUSD=X": ("AUD_RATE_PROXY", 4.0),  # RBA
    "USDCNY=X": ("CNY_RATE_PROXY", 3.0),  # PBOC
    "USDCAD=X": ("CAD_RATE_PROXY", 4.5),  # BoC
    "USDCHF=X": ("CHF_RATE_PROXY", 1.5),  # SNB
    "NZDUSD=X": ("NZD_RATE_PROXY", 5.0),  # RBNZ
}


def filter_forex(
    ticker: str,
    composite_signal: Dict,
    risk_range: Dict,
    prices: Dict,
    fred: Dict,
    bonds_xau_regime: Dict,
    quad: str,
) -> Dict:
    """FX filter — carry trade differential + DXY regime + real yield + composite."""
    out = {
        "ticker": ticker,
        "passes_filter": False,
        "filter_score": 0,
        "filter_rationale": [],
        "tab_specific_signals": {},
    }
    
    score = 0
    
    # 1. Composite signal (30 pts)
    direction = composite_signal.get("direction", "NEUTRAL")
    conf = composite_signal.get("confidence", 0)
    if direction in ("NEUTRAL", "AVOID"):
        out["filter_rationale"].append(f"❌ Composite: {direction}")
        return out
    
    composite_pts = min(30, conf * 40)
    score += composite_pts
    out["direction"] = direction
    out["confidence"] = conf
    out["filter_rationale"].append(f"✓ Composite {direction} (conf {conf:.0%}, +{composite_pts:.0f}pts)")
    
    # 2. Rate differential / carry (25 pts)
    # If ticker = XXX/USD and US rates higher than XXX → USD long carry-positive
    try:
        import pandas as pd
        dgs10_data = fred.get("DGS10")
        if dgs10_data is not None:
            us_rate = float(pd.to_numeric(dgs10_data, errors="coerce").dropna().iloc[-1])
        else:
            us_rate = 4.0
        rate_info = CURRENCY_BENCHMARK_RATE_KEY.get(ticker, (None, 3.0))
        foreign_rate = rate_info[1]
        rate_diff = us_rate - foreign_rate
        
        carry_pts = 0
        if ticker.startswith("USD"):
            # USDxxx — USD long benefits from positive rate_diff
            if direction == "LONG" and rate_diff > 0.5:
                carry_pts = min(25, rate_diff * 8)
            elif direction == "SHORT" and rate_diff < -0.5:
                carry_pts = min(25, abs(rate_diff) * 8)
        else:
            # xxxUSD — xxx long benefits from foreign > US
            if direction == "LONG" and rate_diff < -0.5:
                carry_pts = min(25, abs(rate_diff) * 8)
            elif direction == "SHORT" and rate_diff > 0.5:
                carry_pts = min(25, rate_diff * 8)
        
        score += carry_pts
        if carry_pts > 0:
            out["filter_rationale"].append(f"✓ Carry: rate diff {rate_diff:+.1f}% (+{carry_pts:.0f}pts)")
        out["tab_specific_signals"]["rate_differential_pct"] = round(rate_diff, 2)
    except Exception as e:
        logger.debug(f"FX carry calc failed for {ticker}: {e}")
    
    # 3. DXY regime alignment (15 pts)
    dxy_corr = bonds_xau_regime.get("metrics", {}).get("dxy_gold_corr_60d", 0)
    real_yield = bonds_xau_regime.get("metrics", {}).get("real_yield", 1.5)
    
    if real_yield is not None and real_yield > 1.5 and direction == "LONG" and ticker.startswith("USD"):
        # High real yield bullish USD
        score += 15
        out["filter_rationale"].append(f"✓ Real yield high ({real_yield:.2f}%) supports USD strength (+15pts)")
    
    # 4. Risk Range (15 pts)
    rr_quality = risk_range.get("quality", "C") if risk_range else "C"
    quality_pts = {"A+": 15, "A": 12, "B": 7, "C": 3}.get(rr_quality, 0)
    score += quality_pts
    out["filter_rationale"].append(f"✓ Risk Range {rr_quality} (+{quality_pts}pts)")
    
    # 5. Trade range tightness for FX (15 pts) — FX needs tight ranges for edge
    if risk_range:
        trade = risk_range.get("trade", {})
        if trade.get("lrr") and trade.get("trr"):
            spread_pct = (trade["trr"] - trade["lrr"]) / max(risk_range.get("px", 1), 0.01)
            if spread_pct < 0.03:  # tight range
                score += 15
                out["filter_rationale"].append(f"✓ Tight range {spread_pct:.1%} (+15pts)")
    
    out["filter_score"] = round(score, 1)
    out["passes_filter"] = score >= 30
    
    return out


# ════════════════════════════════════════════════════════════════════════
# FILTER 3: COMMODITIES (different — focus on COT + USD inverse + supply)
# ════════════════════════════════════════════════════════════════════════

COMMODITY_CATEGORIES = {
    "Energy": ["CL=F", "BZ=F", "NG=F", "USO", "UNG", "RB=F", "HO=F"],
    "Metals": ["GC=F", "SI=F", "HG=F", "PL=F", "PA=F", "GLD", "SLV"],
    "Agricultural": ["ZC=F", "ZS=F", "ZW=F", "DBA"],
    "Softs": ["CT=F", "CC=F", "KC=F", "SB=F"],
}


def filter_commodities(
    ticker: str,
    composite_signal: Dict,
    risk_range: Dict,
    cot_data: Dict,
    bonds_xau_regime: Dict,
    cascade_analysis: Dict,
    quad: str,
) -> Dict:
    """Commodities filter — COT bias + USD inverse + supply shock cascade."""
    out = {
        "ticker": ticker,
        "passes_filter": False,
        "filter_score": 0,
        "filter_rationale": [],
        "tab_specific_signals": {},
    }
    
    score = 0
    
    # 1. Composite (25 pts)
    direction = composite_signal.get("direction", "NEUTRAL")
    conf = composite_signal.get("confidence", 0)
    if direction in ("NEUTRAL", "AVOID"):
        out["filter_rationale"].append(f"❌ Composite: {direction}")
        return out
    
    composite_pts = min(25, conf * 35)
    score += composite_pts
    out["direction"] = direction
    out["confidence"] = conf
    out["filter_rationale"].append(f"✓ Composite {direction} (conf {conf:.0%})")
    
    # 2. COT positioning (30 pts) — most important for commodities
    cot = cot_data.get(ticker, {}) if cot_data else {}
    if cot.get("ok"):
        commercial_bias = (cot.get("commercial_bias", "") or "").lower()
        smart_money_bias = (cot.get("bias", "") or "").lower()
        cot_pts = 0
        
        # Commercials typically take opposite side of trend (hedgers)
        if direction == "LONG":
            if "bullish" in smart_money_bias:
                cot_pts = 30  # smart money agrees
                out["filter_rationale"].append("✓ COT: smart money BULLISH (+30pts)")
            elif "bearish" in smart_money_bias:
                cot_pts = -15
                out["filter_rationale"].append("⚠️ COT: smart money bearish (-15pts)")
            else:
                cot_pts = 10
                out["filter_rationale"].append("✓ COT: neutral (+10pts)")
        else:  # SHORT
            if "bearish" in smart_money_bias:
                cot_pts = 30
                out["filter_rationale"].append("✓ COT: smart money BEARISH (+30pts)")
            elif "bullish" in smart_money_bias:
                cot_pts = -15
        score += cot_pts
        out["tab_specific_signals"]["cot_bias"] = smart_money_bias
    
    # 3. USD inverse correlation (15 pts) — commodities priced in USD
    dxy_gold_corr = bonds_xau_regime.get("metrics", {}).get("dxy_gold_corr_60d", 0)
    if ticker in COMMODITY_CATEGORIES["Metals"]:
        if direction == "LONG" and dxy_gold_corr is not None and dxy_gold_corr < -0.5:
            score += 15
            out["filter_rationale"].append(f"✓ USD-Gold inverse {dxy_gold_corr:+.2f} supports LONG (+15pts)")
    
    # 4. Bonds-XAU regime alignment (15 pts)
    ticker_bias = bonds_xau_regime.get("ticker_biases", {}).get(ticker, 0)
    if direction == "LONG" and ticker_bias > 0.3:
        score += 15
        out["filter_rationale"].append(f"✓ Bonds-XAU regime LONG bias {ticker_bias:+.2f} (+15pts)")
    elif direction == "SHORT" and ticker_bias < -0.3:
        score += 15
        out["filter_rationale"].append(f"✓ Bonds-XAU regime SHORT bias {ticker_bias:+.2f} (+15pts)")
    
    # 5. Cascade shock fit (15 pts)
    if cascade_analysis:
        active_shocks = cascade_analysis.get("active_shocks", {})
        # If this commodity is a shock source, mark it
        if ticker in active_shocks:
            shock_mag = active_shocks[ticker]
            if (direction == "LONG" and shock_mag > 0.05) or (direction == "SHORT" and shock_mag < -0.05):
                score += 15
                out["filter_rationale"].append(f"✓ Active shock source {shock_mag:+.1%} (+15pts)")
                out["tab_specific_signals"]["is_cascade_source"] = True
                out["tab_specific_signals"]["shock_magnitude"] = shock_mag
    
    # Category context
    for cat, tickers in COMMODITY_CATEGORIES.items():
        if ticker in tickers:
            out["tab_specific_signals"]["category"] = cat
            break
    
    out["filter_score"] = round(score, 1)
    out["passes_filter"] = score >= 35
    
    return out


# ════════════════════════════════════════════════════════════════════════
# FILTER 4: CRYPTO (different — momentum + QQQ corr + cycle)
# ════════════════════════════════════════════════════════════════════════

CRYPTO_CATEGORIES = {
    "Major": ["BTC-USD", "ETH-USD"],
    "L1": ["SOL-USD", "ADA-USD", "AVAX-USD", "DOT-USD"],
    "DeFi": ["UNI-USD", "AAVE-USD", "MKR-USD"],
    "Meme": ["DOGE-USD", "SHIB-USD"],
    "AI_Crypto": ["FET-USD", "RNDR-USD", "TAO-USD"],
}


def filter_crypto(
    ticker: str,
    composite_signal: Dict,
    risk_range: Dict,
    prices: Dict,
    markov_v3: Dict,
    quad: str,
) -> Dict:
    """Crypto filter — momentum + QQQ corr + regime + halving cycle."""
    out = {
        "ticker": ticker,
        "passes_filter": False,
        "filter_score": 0,
        "filter_rationale": [],
        "tab_specific_signals": {},
    }
    
    score = 0
    
    # 1. Composite (25 pts)
    direction = composite_signal.get("direction", "NEUTRAL")
    conf = composite_signal.get("confidence", 0)
    if direction in ("NEUTRAL", "AVOID"):
        out["filter_rationale"].append(f"❌ Composite: {direction}")
        return out
    
    score += min(25, conf * 35)
    out["direction"] = direction
    out["confidence"] = conf
    
    # 2. 21d momentum (30 pts) — crypto is momentum-driven
    s = prices.get(ticker)
    if s is not None:
        try:
            import pandas as pd
            ser = pd.to_numeric(s, errors="coerce").dropna()
            if len(ser) > 21:
                mom_21d = float(ser.iloc[-1] / ser.iloc[-21] - 1)
                if direction == "LONG":
                    if mom_21d > 0.10:
                        mom_pts = 30
                        out["filter_rationale"].append(f"✓ Strong upside momentum +{mom_21d:.0%} 21d (+30pts)")
                    elif mom_21d > 0.03:
                        mom_pts = 20
                    elif mom_21d > 0:
                        mom_pts = 10
                    else:
                        mom_pts = 0
                        out["filter_rationale"].append(f"⚠️ Negative momentum {mom_21d:.0%} contradicts LONG")
                else:  # SHORT
                    if mom_21d < -0.10:
                        mom_pts = 30
                    elif mom_21d < -0.03:
                        mom_pts = 20
                    else:
                        mom_pts = 0
                score += mom_pts
                out["tab_specific_signals"]["momentum_21d_pct"] = round(mom_21d * 100, 2)
        except Exception:
            pass
    
    # 3. QQQ correlation (15 pts) — crypto correlated to risk-on
    qqq = prices.get("QQQ")
    if s is not None and qqq is not None:
        try:
            import pandas as pd
            ser = pd.to_numeric(s, errors="coerce").dropna()
            qqq_ser = pd.to_numeric(qqq, errors="coerce").dropna()
            joined = pd.concat([ser, qqq_ser], axis=1, join="inner").dropna()
            if len(joined) > 60:
                corr = float(joined.tail(60).pct_change().corr().iloc[0, 1])
                if direction == "LONG" and quad in ("Q1", "Q2") and corr > 0.3:
                    score += 15
                    out["filter_rationale"].append(f"✓ QQQ corr {corr:+.2f} aligned with risk-on {quad} (+15pts)")
                out["tab_specific_signals"]["qqq_corr_60d"] = round(corr, 3)
        except Exception:
            pass
    
    # 4. Markov regime fit (15 pts)
    if markov_v3:
        regime = markov_v3.get("current_regime", "")
        if direction == "LONG" and regime in ("Q1_GOLDILOCKS", "Q2_REFLATION"):
            score += 15
            out["filter_rationale"].append(f"✓ Markov {regime} supports crypto LONG (+15pts)")
        elif direction == "SHORT" and regime in ("Q4_DEFLATION", "Q5_CRASH"):
            score += 15
    
    # 5. Risk Range quality (15 pts)
    rr_quality = risk_range.get("quality", "C") if risk_range else "C"
    score += {"A+": 15, "A": 12, "B": 7, "C": 3}.get(rr_quality, 0)
    
    # Category
    for cat, tickers in CRYPTO_CATEGORIES.items():
        if ticker in tickers:
            out["tab_specific_signals"]["category"] = cat
            break
    
    out["filter_score"] = round(score, 1)
    out["passes_filter"] = score >= 35
    
    return out


# ════════════════════════════════════════════════════════════════════════
# FILTER 5: IHSG (different — USDIDR + commodity + Indonesia macro)
# ════════════════════════════════════════════════════════════════════════

IHSG_SECTOR_MAP = {
    "Coal": ["ADRO.JK", "ITMG.JK", "PTBA.JK", "INDY.JK"],
    "Nickel": ["NCKL.JK", "ANTM.JK", "INCO.JK", "MDKA.JK"],
    "Banks": ["BBCA.JK", "BBRI.JK", "BMRI.JK", "BBNI.JK"],
    "Consumer": ["UNVR.JK", "GGRM.JK", "HMSP.JK", "INDF.JK", "ICBP.JK"],
    "Telecom": ["TLKM.JK", "EXCL.JK", "ISAT.JK"],
    "Property": ["BSDE.JK", "CTRA.JK", "SMRA.JK", "PWON.JK"],
}


def filter_ihsg(
    ticker: str,
    composite_signal: Dict,
    risk_range: Dict,
    prices: Dict,
    quad: str,
) -> Dict:
    """IHSG filter — USDIDR + commodity correlation + sector context."""
    out = {
        "ticker": ticker,
        "passes_filter": False,
        "filter_score": 0,
        "filter_rationale": [],
        "tab_specific_signals": {},
    }
    
    score = 0
    
    # 1. Composite (30 pts)
    direction = composite_signal.get("direction", "NEUTRAL")
    conf = composite_signal.get("confidence", 0)
    if direction in ("NEUTRAL", "AVOID"):
        return out
    
    score += min(30, conf * 40)
    out["direction"] = direction
    out["confidence"] = conf
    
    # 2. USDIDR regime (20 pts)
    usdidr = prices.get("USDIDR=X")
    if usdidr is not None:
        try:
            import pandas as pd
            ser = pd.to_numeric(usdidr, errors="coerce").dropna()
            if len(ser) > 21:
                idr_strength = -(float(ser.iloc[-1] / ser.iloc[-21] - 1))  # Negative IDR ret = stronger IDR
                # Strong IDR good for consumer/banks (LONG bias)
                # Weak IDR good for commodity exporters (Coal/Nickel)
                sector = None
                for s, tickers in IHSG_SECTOR_MAP.items():
                    if ticker in tickers:
                        sector = s
                        break
                if sector in ("Coal", "Nickel") and idr_strength < 0:  # weak IDR
                    score += 20
                    out["filter_rationale"].append(f"✓ Weak IDR benefits {sector} exporter (+20pts)")
                elif sector in ("Banks", "Consumer") and idr_strength > 0:
                    score += 20
                    out["filter_rationale"].append(f"✓ Strong IDR benefits {sector} (+20pts)")
                out["tab_specific_signals"]["idr_21d_change_pct"] = round(idr_strength * 100, 2)
        except Exception:
            pass
    
    # 3. Commodity proxy (for resource stocks)
    sector = None
    for s, tickers in IHSG_SECTOR_MAP.items():
        if ticker in tickers:
            sector = s
            break
    
    if sector == "Coal":
        # Check CL=F or thermal coal proxy via crude oil
        cl = prices.get("CL=F")
        if cl is not None:
            try:
                import pandas as pd
                ser = pd.to_numeric(cl, errors="coerce").dropna()
                if len(ser) > 21:
                    cl_mom = float(ser.iloc[-1] / ser.iloc[-21] - 1)
                    if direction == "LONG" and cl_mom > 0.05:
                        score += 15
                        out["filter_rationale"].append(f"✓ Crude oil mom +{cl_mom:.0%} supports coal LONG (+15pts)")
            except Exception:
                pass
    elif sector == "Nickel":
        # Check nickel proxy (use HG=F copper as proxy)
        hg = prices.get("HG=F")
        if hg is not None:
            try:
                import pandas as pd
                ser = pd.to_numeric(hg, errors="coerce").dropna()
                if len(ser) > 21:
                    hg_mom = float(ser.iloc[-1] / ser.iloc[-21] - 1)
                    if direction == "LONG" and hg_mom > 0.03:
                        score += 15
                        out["filter_rationale"].append(f"✓ Copper proxy +{hg_mom:.0%} supports metals LONG (+15pts)")
            except Exception:
                pass
    
    # 4. Risk Range (15 pts)
    rr_quality = risk_range.get("quality", "C") if risk_range else "C"
    score += {"A+": 15, "A": 12, "B": 7, "C": 3}.get(rr_quality, 0)
    
    out["tab_specific_signals"]["sector"] = sector
    out["filter_score"] = round(score, 1)
    out["passes_filter"] = score >= 35
    
    return out


# ════════════════════════════════════════════════════════════════════════
# FILTER 6: ALPHA CENTER (cross-market top tier)
# ════════════════════════════════════════════════════════════════════════

def filter_alpha_center(
    ticker: str,
    composite_signal: Dict,
    thought_process: Dict,
    smart_money: Dict,  # kept for compat, not scored
    risk_range: Dict,
    market: str,
) -> Dict:
    """Alpha Center filter (Sprint 11 refactor) — cross-market TOP TIER.
    
    Replaces smart money endorsement bonus with methodology depth bonus.
    Smart money holdings = stale 13F lag. Methodology depth = forward-looking.
    """
    out = {
        "ticker": ticker,
        "passes_filter": False,
        "filter_score": 0,
        "filter_rationale": [],
        "market": market,
    }
    
    score = 0
    
    # 1. Composite must be STRONG (not just moderate)
    direction = composite_signal.get("direction", "NEUTRAL")
    conf = composite_signal.get("confidence", 0)
    if direction in ("NEUTRAL", "AVOID"):
        return out
    if conf < 0.4:
        return out  # Alpha center demands higher confidence
    
    score += min(35, conf * 50)
    
    # 2. Thesis must be HIGH (≥60)
    thesis_score = thought_process.get("thesis_score", 0)
    if thesis_score >= 80:
        score += 30
    elif thesis_score >= 60:
        score += 20
    else:
        return out  # need framework support
    
    # 3. Risk Range quality must be A or A+
    rr_quality = risk_range.get("quality", "C") if risk_range else "C"
    if rr_quality not in ("A+", "A"):
        return out
    score += {"A+": 20, "A": 15}.get(rr_quality, 0)
    
    # 4. Methodology depth bonus (replaces smart money 15pts)
    n_matches = thought_process.get("n_matches", 0)
    if n_matches >= 4:
        score += 15
        out["filter_rationale"].append(f"✓ Deep methodology consensus ({n_matches} frameworks)")
    elif n_matches >= 3:
        score += 10
    
    out["filter_score"] = round(score, 1)
    out["passes_filter"] = score >= 70  # Alpha Center high bar
    out["direction"] = direction
    out["confidence"] = conf
    out["thesis_score"] = thesis_score
    out["primary_role"] = thought_process.get("primary_role")
    out["n_methodology_matches"] = n_matches
    
    return out


# ════════════════════════════════════════════════════════════════════════
# Master dispatcher
# ════════════════════════════════════════════════════════════════════════

def apply_tab_filter(
    ticker: str,
    tab: str,
    snap: Dict,
    quad: str = "Q3",
) -> Dict:
    """Dispatch to appropriate tab-specific filter."""
    composite_signal = snap.get("composite_signals", {}).get(ticker, {})
    thought_process = snap.get("thought_process", {}).get(ticker, {})
    smart_money = snap.get("smart_money", {})
    risk_range = snap.get("risk_ranges", {}).get("asset_ranges", {}).get(ticker, {})
    prices = snap.get("_prices_ref", {})  # not stored but passed when needed
    cot_data = (snap.get("cot_oi", {}) or {}).get("cot", {})
    bonds_xau = snap.get("bonds_xau_regime", {})
    cascade = snap.get("cascade_analysis", {})
    markov = snap.get("markov_v3", {})
    fred = snap.get("_fred_ref", {})
    
    if tab in ("us_stocks", "🇺🇸 US Stocks"):
        return filter_us_stocks(ticker, composite_signal, thought_process, smart_money, risk_range, quad)
    elif tab in ("forex", "💱 Forex"):
        return filter_forex(ticker, composite_signal, risk_range, prices, fred, bonds_xau, quad)
    elif tab in ("commodities", "🛢️ Commodities"):
        return filter_commodities(ticker, composite_signal, risk_range, cot_data, bonds_xau, cascade, quad)
    elif tab in ("crypto", "₿ Crypto"):
        return filter_crypto(ticker, composite_signal, risk_range, prices, markov, quad)
    elif tab in ("ihsg", "🌍 IHSG"):
        return filter_ihsg(ticker, composite_signal, risk_range, prices, quad)
    elif tab in ("alpha_center", "⚡ Alpha Center"):
        # Determine market for alpha center
        from engines.market_classifier import classify_ticker
        market = classify_ticker(ticker)
        return filter_alpha_center(ticker, composite_signal, thought_process, smart_money, risk_range, market)
    else:
        return {"passes_filter": True, "filter_score": 50, "filter_rationale": ["default pass"]}
