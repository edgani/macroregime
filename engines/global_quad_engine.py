"""engines/global_quad_engine.py

Per-country quad classification + global weighted quad.
Hedgeye runs GIP for 50+ countries covering 90% of global GDP.

Per-country methodology (from Hedgeye Monthly Macro Themes Monitor):
 Growth proxy: Manufacturing PMI + Services PMI + IP + Export growth
 Inflation proxy: CPI + commodity sensitivity * oil/commodity moves
 Acceleration/deceleration = second derivative of YoY RoC
 Country ETF performance vs USD = confirming/leading signal

Global quad = market-cap weighted average of country quads.

USD relationship:
 "Rising USD = deflationary for EM denominated in USD"
 "Global Q1+Q2 = USD weakens (synchronized recovery)"
 "Global Q3+Q4 divergences = USD strengthens"
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import COUNTRY_UNIVERSE

# Market cap weights (approximate 2026 GDP-proportional)
MARKET_CAP_WEIGHTS: Dict[str, float] = {
 "USA": 0.280, "China": 0.120, "Japan": 0.060, "Germany": 0.045,
 "India": 0.040, "UK": 0.035, "France": 0.030, "Canada": 0.025,
 "Korea": 0.022, "Australia": 0.020, "Brazil": 0.018, "Taiwan": 0.018,
 "Mexico": 0.015, "Indonesia": 0.012, "Saudi": 0.012, "Norway": 0.008,
 "Switzerland": 0.010, "Sweden": 0.008, "Hong_Kong": 0.012, "Argentina": 0.006,
 "Chile": 0.005, "Colombia": 0.004, "Poland": 0.006, "Turkey": 0.006,
 "Israel": 0.005, "UAE": 0.008, "South_Africa": 0.005, "Vietnam": 0.004,
 "Egypt": 0.003, "Nigeria": 0.003, "Peru": 0.004,
}

# Quad numeric codes for weighted averaging
QUAD_SCORE: Dict[str, float] = {"Q1": 1.0, "Q2": 2.0, "Q3": 3.0, "Q4": 4.0}

# ── Safe helpers (NEVER use `or` on pd.Series) ─────────────────────────────

def _get_series(prices: Dict[str, pd.Series], *keys) -> Optional[pd.Series]:
    """Return first non-None, non-empty pd.Series from keys."""
    for k in keys:
        s = prices.get(k)
        if s is not None and isinstance(s, pd.Series) and not s.empty:
            return s
    return None

def _ret(s: pd.Series, n: int) -> Optional[float]:
    if s is None or len(s) < n+1:
        return None
    try:
        r = float(s.iloc[-1] / s.iloc[-n-1] - 1)
        return r if math.isfinite(r) else None
    except Exception:
        return None

def _roc_acc(s: pd.Series) -> Optional[float]:
    """Is 6M annualised return accelerating vs 12M? Returns delta."""
    r6 = _ret(s, 126)
    r12 = _ret(s, 252)
    if r6 is None or r12 is None:
        return None
    return r6 * 2.0 - r12  # annualised 6M vs 12M

def _classify_country(
    etf_close: Optional[pd.Series],
    commodity_sens: float,
    usd_sens: float,
    oil_3m: float,
    usd_1m: float,
    global_growth_bias: float = 0.0,
    global_inflation_bias: float = 0.0,
) -> Tuple[str, float, str]:
    """
    Classify country quad using ETF price + macro sensitivity.

    Returns: (quad, confidence, rationale)
    """
    if etf_close is None or len(etf_close) < 63:
        # Fallback: use global bias
        if global_growth_bias > 0 and global_inflation_bias < 0:
            return "Q1", 0.35, "global_bias_only"
        elif global_growth_bias > 0 and global_inflation_bias > 0:
            return "Q2", 0.35, "global_bias_only"
        elif global_growth_bias < 0 and global_inflation_bias > 0:
            return "Q3", 0.35, "global_bias_only"
        else:
            return "Q4", 0.30, "global_bias_only"

    # Growth signal: ETF acceleration (6M annualised vs 12M)
    roc = _roc_acc(etf_close)
    growth_acc = roc is not None and roc > 0.03  # 3% annualised acceleration threshold
    growth_dec = roc is not None and roc < -0.03

    # Inflation signal: commodity sensitivity * oil move + USD sensitivity
    inf_push = commodity_sens * max(0.0, oil_3m) + 0.3 * max(0.0, -usd_1m)
    inf_release = commodity_sens * max(0.0, -oil_3m) + 0.3 * max(0.0, usd_1m)
    inflation_acc = inf_push > inf_release + 0.01

    # Classify
    if growth_acc and not inflation_acc:
        quad, conf = "Q1", 0.65
        rationale = f"ETF acc +{roc:.0%} ann, inflation easing"
    elif growth_acc and inflation_acc:
        quad, conf = "Q2", 0.60
        rationale = f"ETF acc +{roc:.0%} ann + commodity bid"
    elif (growth_dec or not growth_acc) and inflation_acc:
        quad, conf = "Q3", 0.60
        rationale = f"ETF dec, inflation acc (commodity_sens={commodity_sens:.0%})"
    elif (growth_dec or not growth_acc) and not inflation_acc:
        quad, conf = "Q4", 0.55
        rationale = f"ETF dec, inflation easing"
    else:
        quad, conf = "Q3", 0.35  # default to global bias
        rationale = "Mixed signals"

    # Reduce confidence if ETF signal is borderline
    if roc is not None and abs(roc) < 0.05:
        conf *= 0.75

    return quad, round(conf, 2), rationale

class GlobalQuadEngine:
    """
    Run Hedgeye-style GIP for 50 countries.
    Outputs per-country quad + global weighted quad.
    """

    def run(
        self,
        prices: Dict[str, pd.Series],
        us_gip_result = None,  # GIPResult from GIPEngine
        stress: Optional[Dict[str, float]] = None,
    ) -> Dict[str, object]:

        stress = stress or {}

        # FIXED: use _get_series instead of `or` on pd.Series
        usd_series = _get_series(prices, "DX-Y.NYB", "UUP")
        oil_series = _get_series(prices, "CL=F", "USO")

        usd_1m = 0.0
        if usd_series is not None:
            r = _ret(pd.to_numeric(usd_series, errors="coerce").dropna(), 21)
            usd_1m = r if r is not None else 0.0

        oil_3m = 0.0
        if oil_series is not None:
            r = _ret(pd.to_numeric(oil_series, errors="coerce").dropna(), 63)
            oil_3m = r if r is not None else 0.0

        # Global growth/inflation bias from US GIP (dominant signal per McCullough)
        g_bias = 0.0
        i_bias = 0.0
        if us_gip_result is not None:
            g_bias = float(us_gip_result.structural_g)
            i_bias = float(us_gip_result.structural_i)

        country_results: Dict[str, dict] = {}

        for country, (etf, region, commodity_sens, usd_sens) in COUNTRY_UNIVERSE.items():
            etf_raw = prices.get(etf)
            etf_close = pd.to_numeric(etf_raw, errors="coerce").dropna() if etf_raw is not None else None

            quad, conf, rationale = _classify_country(
                etf_close, commodity_sens, usd_sens,
                oil_3m, usd_1m, g_bias, i_bias,
            )

            # USD impact for EM countries
            # "Rising USD = deflationary for EM"
            usd_headwind = usd_sens * max(0.0, usd_1m) * 2.0  # 0-1 scale
            usd_tailwind = usd_sens * max(0.0, -usd_1m) * 2.0

            # ETF performance
            etf_1m = _ret(etf_close, 21) if etf_close is not None and len(etf_close)>21 else None
            etf_3m = _ret(etf_close, 63) if etf_close is not None and len(etf_close)>63 else None
            etf_6m = _ret(etf_close, 126) if etf_close is not None and len(etf_close)>126 else None
            etf_12m = _ret(etf_close, 252) if etf_close is not None and len(etf_close)>252 else None

            country_results[country] = dict(
                quad=quad, confidence=conf, rationale=rationale,
                etf=etf, region=region,
                commodity_sensitivity=commodity_sens,
                usd_sensitivity=usd_sens,
                usd_headwind=usd_headwind,
                usd_tailwind=usd_tailwind,
                etf_1m=etf_1m, etf_3m=etf_3m, etf_6m=etf_6m, etf_12m=etf_12m,
                roc_acc=_roc_acc(etf_close) if etf_close is not None and len(etf_close)>252 else None,
            )

        # Global weighted quad
        weighted_scores: Dict[str, float] = {"Q1":0.0,"Q2":0.0,"Q3":0.0,"Q4":0.0}
        total_w = 0.0
        for country, data in country_results.items():
            w = MARKET_CAP_WEIGHTS.get(country, 0.003)
            q = data["quad"]
            if q in weighted_scores:
                weighted_scores[q] += w * data["confidence"]
                total_w += w

        if total_w > 0:
            weighted_scores = {k: v/total_w for k,v in weighted_scores.items()}

        global_quad = max(weighted_scores, key=weighted_scores.get)
        global_conf = weighted_scores[global_quad]

        # Region breakdown
        regions = {}
        for country, data in country_results.items():
            r = data["region"]
            if r not in regions:
                regions[r] = []
            regions[r].append(data["quad"])
        region_quads = {r: max(set(qs), key=qs.count) for r,qs in regions.items()}

        # Divergence: are most major economies in same quad?
        quad_dist = {}
        for data in country_results.values():
            q = data["quad"]
            quad_dist[q] = quad_dist.get(q, 0) + 1
        dominant_share = max(quad_dist.values()) / max(sum(quad_dist.values()), 1)
        synchronized = dominant_share >= 0.55  # >55% in same quad = synchronized

        # USD interpretation
        if global_quad in ("Q1","Q2"):
            usd_bias = "bearish"  # synchronized recovery = USD down
            usd_rationale = "Global Q1/Q2 = synchronized recovery → USD weakens"
        else:
            usd_bias = "bullish"  # global divergences = USD up (flight to safety)
            usd_rationale = "Global Q3/Q4 divergences → USD strengthens"

        # EM assessment
        em_countries = {c:d for c,d in country_results.items() if d["region"] in ("em","asia") and c!="Japan"}
        em_in_q3 = sum(1 for d in em_countries.values() if d["quad"]=="Q3")
        em_headwind = em_in_q3 / max(len(em_countries), 1) > 0.5

        return dict(
            countries=country_results,
            global_quad=global_quad,
            global_probs=weighted_scores,
            global_conf=global_conf,
            region_quads=region_quads,
            quad_distribution=quad_dist,
            synchronized=synchronized,
            usd_bias=usd_bias,
            usd_rationale=usd_rationale,
            em_headwind=em_headwind,
            em_in_q3=em_in_q3,
            inputs=dict(usd_1m=usd_1m, oil_3m=oil_3m, g_bias=g_bias, i_bias=i_bias),
        )
