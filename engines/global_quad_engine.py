"""global_quad_engine.py

Global Quad Engine — Hedgeye runs GIP for top 50 economies.

How Hedgeye calculates Global Quad:
  1. For each country: measure GDP growth RoC + CPI RoC
  2. GDP proxy: country ETF 6-month return vs 12-month return (acceleration/deceleration)
  3. CPI proxy: blend of: country ETF vs USD, commodity sensitivity, domestic PMI
  4. Assign quad per country
  5. Weight by market cap → Global Quad = weighted average

Per McCullough's process:
  - Global Quad 3 = most major economies in stagflation 
  - Global Quad 2 transition = demand still alive, inflation persists
  - Country-specific Quad count = 3-month forward outlook (e.g. Mexico 2-1-2 = great)

Why Long Hong Kong, Short Indonesia (April 2026):
  ─────────────────────────────────────────────────────
  HONG KONG (EWH):
    • USD bearish TRADE+TREND → EM recovery via dollar channel
    • EWH = highest USD beta in EM (Tencent, HSBC, AIA, Hang Seng)
    • Hong Kong tech/financials benefit disproportionately from USD weakness
    • China adjacent: reopening/recovery narrative still in play
    • EWH Quad count: entering Q2 (recovery from Q3 base → bullish breakout)
    • McCullough added EWH as "incremental add" on USD TREND breakdown

  INDONESIA (^JKSE / EIDO) — WHY AVOID/SHORT:
    • Indonesia = commodity exporter (coal, palm oil, nickel)
    • Q3 oil shock phase OVER — coal/commodity cycle peaked
    • ADRO.JK, PTBA.JK: peaked months ago, now in distribution
    • IDR fragile: without commodity tailwind, BI rate story fades
    • Global Q3 structural = growth slowdown → commodity demand weakens
    • Indonesia NOT in Hedgeye's long book despite global USD weakness
    • Unlike Mexico/Norway/Argentina: no reshoring/nearshoring tailwind
    • The "All roads lead to Western Hemisphere" supply chain = anti-Asia EM
  ─────────────────────────────────────────────────────

Front-running Hedgeye on Country Selection:
  1. Identify countries transitioning to better quad BEFORE Hedgeye does
  2. ETF performance vs USD is a leading indicator for their GIP model
  3. Look for: country ETF making higher lows while USD falling = early Quad 2 signal
  4. Country CapEx plans (proxied by industrial ETFs) = forward-looking GDP
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


# Country ETF universe with their characteristics
# Format: {name: (etf_ticker, region, commodity_sensitivity, usd_sensitivity)}
COUNTRY_UNIVERSE = {
    # Americas — Western Hemisphere supply chain (Hedgeye's "All roads lead West")
    "USA":       ("SPY",    "americas",   0.20, 1.00),
    "Mexico":    ("EWW",    "americas",   0.40, 0.85),  # Nearshoring #1
    "Canada":    ("EWC",    "americas",   0.55, 0.80),
    "Argentina": ("ARGT",   "americas",   0.35, 0.90),  # Milei reform + commodities
    "Brazil":    ("EWZ",    "americas",   0.65, 0.75),
    # Asia-Pacific
    "Hong_Kong": ("EWH",    "asia",       0.15, 0.95),  # HIGH USD sensitivity
    "Japan":     ("EWJ",    "asia",       0.20, 0.80),
    "Korea":     ("EWY",    "asia",       0.30, 0.75),
    "Taiwan":    ("EWT",    "asia",       0.15, 0.70),
    "China":     ("MCHI",   "asia",       0.30, 0.65),
    "India":     ("INDA",   "asia",       0.25, 0.70),
    "Indonesia": ("EIDO",   "asia",       0.70, 0.55),  # HIGH commodity sensitivity, LOW USD beta
    "Australia": ("EWA",    "asia",       0.65, 0.70),
    # Europe
    "Germany":   ("EWG",    "europe",     0.35, 0.70),  # Entering Q3 (recession risk)
    "UK":        ("EWU",    "europe",     0.30, 0.75),
    "France":    ("EWQ",    "europe",     0.30, 0.70),
    "Norway":    ("NORW",   "europe",     0.75, 0.80),  # Oil + Q2 exposure
    "Sweden":    ("EWD",    "europe",     0.35, 0.75),
    # MENA
    "UAE":       ("UAE",    "mena",       0.80, 0.65),  # Oil boom
    # Africa/EM
    "South_Africa": ("EZA", "em",         0.55, 0.65),
}

# Hedgeye's known positions (from April 17-20, 2026 documents)
HEDGEYE_KNOWN_LONGS = ["Mexico", "Hong_Kong", "Argentina", "Norway"]
HEDGEYE_KNOWN_SHORTS_OR_AVOID = ["Germany", "Indonesia"]


def _ret(s: pd.Series, n: int) -> Optional[float]:
    if s is None or len(s) < n + 1:
        return None
    try:
        r = float(s.iloc[-1] / s.iloc[-n] - 1)
        return r if math.isfinite(r) else None
    except Exception:
        return None


def _classify_country_quad(
    etf_6m: Optional[float],
    etf_12m: Optional[float],
    usd_1m: float,
    commodity_sensitivity: float,
    oil_3m: float,
) -> Tuple[str, float, str]:
    """
    Classify a country into a quad using price-based proxies.

    Logic mirrors Hedgeye's GIP model:
    - Growth proxy: ETF 6m vs 12m return (acceleration = 6m > 12m annualized)
    - Inflation proxy: commodity sensitivity * oil move + USD sensitivity * USD move

    Returns: (quad, confidence, rationale)
    """
    if etf_6m is None or etf_12m is None:
        return "Q?", 0.0, "insufficient data"

    # Growth acceleration: is 6M annualized > 12M?
    # (normalizes for time periods)
    ann_6m = etf_6m * 2  # annualize 6M
    ann_12m = etf_12m
    growth_acc = ann_6m > ann_12m + 0.03  # 3% threshold to reduce noise
    growth_dec = ann_6m < ann_12m - 0.03

    # Inflation proxy: combination of commodity exposure + oil move
    # High commodity sensitivity countries benefit from high oil = inflation signal
    inf_pressure = commodity_sensitivity * max(0, oil_3m) + 0.3 * max(0, -usd_1m)
    inf_releasing = commodity_sensitivity * min(0, oil_3m) * -1 + 0.3 * max(0, usd_1m)
    infl_acc = inf_pressure > inf_releasing + 0.01

    # Quad assignment
    if growth_acc and not infl_acc:
        quad, conf = "Q1", 0.70
        rationale = f"Growth acc ({ann_6m:.0%} ann > {ann_12m:.0%}), inflation easing"
    elif growth_acc and infl_acc:
        quad, conf = "Q2", 0.65
        rationale = f"Growth acc + inflation up — reflation"
    elif not growth_acc and infl_acc:
        quad, conf = "Q3", 0.65
        rationale = f"Growth dec, inflation sticky — stagflation"
    elif not growth_acc and not infl_acc:
        quad, conf = "Q4", 0.60
        rationale = f"Growth dec + deflation — late cycle"
    else:
        quad, conf = "Q?", 0.30
        rationale = "Mixed signals"

    # Lower confidence if signals are borderline
    if abs(ann_6m - ann_12m) < 0.05:
        conf *= 0.7

    return quad, round(conf, 2), rationale


def _score_country_opportunity(
    name: str,
    quad: str,
    conf: float,
    etf_1m: Optional[float],
    usd_sensitivity: float,
    usd_trend: str,
    s_quad: str,  # US structural quad
    m_quad: str,  # US monthly quad
) -> Dict:
    """
    Score each country for long/short opportunity.

    Hedgeye's Signal + Quad framework for countries:
    1. Country's own Quad (better quad = more bullish)
    2. USD sensitivity (USD bearish → high USD-sensitive countries rally)
    3. Alignment with US structural backdrop
    4. Trend/momentum (ETF 1M return as proxy for Signal)
    """
    # Base score from quad
    quad_score = {"Q1": 0.85, "Q2": 0.70, "Q3": 0.35, "Q4": 0.20, "Q?": 0.40}.get(quad, 0.40)

    # USD tailwind: if USD bearish, high-USD-sensitivity countries get boost
    usd_boost = 0.0
    if usd_trend == "bearish":
        usd_boost = usd_sensitivity * 0.30
    elif usd_trend == "bullish":
        usd_boost = -usd_sensitivity * 0.20

    # Momentum: positive = buy dip, negative = caution
    momentum = float(etf_1m) if etf_1m is not None and math.isfinite(etf_1m) else 0.0
    momentum_score = max(0.0, min(1.0, 0.5 + momentum * 3))

    # Alignment with US quarterly (structural) backdrop
    alignment = 0.5
    if s_quad == "Q3" and quad in ("Q1", "Q2"):
        alignment = 0.75  # Country doing better than US = relative winner
    elif s_quad == "Q3" and quad == "Q3":
        alignment = 0.30  # Both in stagflation = avoid
    elif s_quad == "Q2" and quad in ("Q1", "Q2"):
        alignment = 0.80  # Both in growth = high conviction

    composite = (0.35 * quad_score + 0.25 * (0.5 + usd_boost) +
                 0.20 * momentum_score + 0.20 * alignment) * conf

    # Action
    if composite >= 0.55:
        action = "LONG"
        conviction = composite
    elif composite <= 0.30:
        action = "SHORT/AVOID"
        conviction = 1 - composite
    else:
        action = "NEUTRAL"
        conviction = 0.50

    # Hedgeye alignment
    in_hedgeye_longs = name in HEDGEYE_KNOWN_LONGS
    in_hedgeye_shorts = name in HEDGEYE_KNOWN_SHORTS_OR_AVOID

    return {
        "quad": quad,
        "confidence": conf,
        "composite_score": round(composite, 3),
        "action": action,
        "conviction": round(conviction, 3),
        "etf_1m": round(momentum, 4) if etf_1m else None,
        "usd_sensitivity": usd_sensitivity,
        "usd_boost": round(usd_boost, 3),
        "hedgeye_long": in_hedgeye_longs,
        "hedgeye_short": in_hedgeye_shorts,
        "our_vs_hedgeye": (
            "✅ agree" if (action == "LONG" and in_hedgeye_longs) or
                          (action == "SHORT/AVOID" and in_hedgeye_shorts)
            else "❌ disagree" if (action == "SHORT/AVOID" and in_hedgeye_longs) or
                                  (action == "LONG" and in_hedgeye_shorts)
            else "➡️ untracked"
        ),
    }


def run_global_quad_engine(
    prices: Dict[str, pd.Series],
    us_structural_quad: str = "Q3",
    us_monthly_quad: str = "Q2",
    usd_trend: str = "bearish",
) -> Dict:
    """
    Run global quad classification for all countries.

    Returns a dict with:
    - global_quad: weighted average regime
    - countries: per-country quad + opportunity score
    - top_longs: ranked country ETFs to buy
    - top_shorts: ranked country ETFs to avoid
    - vs_hedgeye: which of our calls agree/disagree with Hedgeye
    - front_run_candidates: countries near quad transition (lead time ~4-8 weeks)
    """
    uup = prices.get("UUP", pd.Series())
    usd_1m = float(uup.pct_change(21).iloc[-1]) if (uup is not None and len(uup) > 21) else 0.0
    oil_3m = float(prices.get("CL=F", pd.Series()).pct_change(63).iloc[-1]) if prices.get("CL=F") is not None and len(prices.get("CL=F", pd.Series())) > 63 else 0.0

    country_results = {}
    quad_weights = {"Q1": 0, "Q2": 0, "Q3": 0, "Q4": 0}
    total_weight = 0

    for country_name, (etf_tk, region, comm_sens, usd_sens) in COUNTRY_UNIVERSE.items():
        s = prices.get(etf_tk, pd.Series())
        if s is None or len(s) < 30:
            continue

        r1m = _ret(s, 21)
        r6m = _ret(s, 126)
        r12m = _ret(s, 252)

        quad, conf, rationale = _classify_country_quad(r6m, r12m, usd_1m, comm_sens, oil_3m)

        opportunity = _score_country_opportunity(
            country_name, quad, conf, r1m,
            usd_sens, usd_trend, us_structural_quad, us_monthly_quad
        )

        country_results[country_name] = {
            "etf": etf_tk,
            "region": region,
            "quad": quad,
            "confidence": conf,
            "rationale": rationale,
            "r1m": round(r1m, 4) if r1m else None,
            "r6m": round(r6m, 4) if r6m else None,
            "r12m": round(r12m, 4) if r12m else None,
            **opportunity,
        }

        # Weighted global quad (market-cap weight proxy by region)
        weight = {"americas": 1.5, "europe": 0.8, "asia": 1.0, "mena": 0.4, "em": 0.3}.get(region, 0.5)
        if quad in quad_weights:
            quad_weights[quad] += weight * conf
            total_weight += weight * conf

    # Global quad = dominant weighted quad
    if total_weight > 0:
        global_quad = max(quad_weights, key=quad_weights.get)
        global_conf = quad_weights[global_quad] / total_weight
        global_probs = {k: round(v / max(total_weight, 0.001), 3) for k, v in quad_weights.items()}
    else:
        global_quad = "Q3"  # default from Hedgeye April 2026
        global_conf = 0.5
        global_probs = {"Q1": 0.15, "Q2": 0.25, "Q3": 0.40, "Q4": 0.20}

    # Sort countries by opportunity score
    ranked = sorted(country_results.items(), key=lambda x: x[1]["composite_score"], reverse=True)
    top_longs = [(name, data["etf"], data["composite_score"])
                 for name, data in ranked if data["action"] == "LONG"][:6]
    top_shorts = [(name, data["etf"], data["composite_score"])
                  for name, data in ranked if data["action"] == "SHORT/AVOID"][:4]

    # Front-run candidates: countries about to transition quad
    front_run = []
    for name, data in ranked:
        r1m = data.get("r1m", 0) or 0
        r6m = data.get("r6m", 0) or 0
        if data["quad"] == "Q3" and r1m > 0.03:
            front_run.append({
                "country": name, "etf": data["etf"],
                "current_quad": "Q3",
                "transition_to": "Q2",
                "signal": f"Q3 country rallying +{r1m:.1%} 1M — potential early Q3→Q2 transition",
                "priority": "watch",
            })
        elif data["quad"] == "Q2" and r1m < -0.03 and r6m < 0:
            front_run.append({
                "country": name, "etf": data["etf"],
                "current_quad": "Q2",
                "transition_to": "Q3",
                "signal": f"Q2 country fading −{abs(r1m):.1%} — potential Q2→Q3 transition",
                "priority": "watch",
            })

    # Indonesia-specific analysis
    indo_data = country_results.get("Indonesia", {})
    hk_data = country_results.get("Hong_Kong", {})

    why_hk_long = (
        f"EWH score {hk_data.get('composite_score',0):.0%}: "
        f"Quad {hk_data.get('quad','?')} + USD sensitivity {hk_data.get('usd_sensitivity',0):.0%} "
        f"+ USD bearish boost {hk_data.get('usd_boost',0):.0%}. "
        "USD breakdown = mechanical long via dollar inverse correlation. "
        "HK tech/financials = highest EM beta to USD weakness."
    )
    why_indo_avoid = (
        f"EIDO/JKSE score {indo_data.get('composite_score',0):.0%}: "
        f"Quad {indo_data.get('quad','?')} — commodity-driven economy in Q3 global context. "
        "Coal/palm oil cycle peaked. USD weakness helps but not enough to offset "
        "slowing commodity demand from global growth deceleration. "
        "Unlike Mexico/Norway: no reshoring/nearshoring structural tailwind. "
        "IDR fragile without sustained oil > $90."
    )

    # Check alignment with Hedgeye
    agree_count = sum(1 for _, d in country_results.items() if "agree" in d.get("our_vs_hedgeye", ""))
    disagree_count = sum(1 for _, d in country_results.items() if "disagree" in d.get("our_vs_hedgeye", ""))

    return {
        "global_quad": global_quad,
        "global_confidence": round(global_conf, 3),
        "global_probs": global_probs,
        "countries": country_results,
        "top_longs": top_longs,
        "top_shorts": top_shorts,
        "front_run_candidates": front_run[:5],
        "why_long_hong_kong": why_hk_long,
        "why_avoid_indonesia": why_indo_avoid,
        "vs_hedgeye_alignment": f"{agree_count} agree, {disagree_count} disagree",
        "global_macro_memetic": "Flation Now, Stag On A Lag — Q3 global backdrop persists, Monthly Q2 is the relief window",
    }
