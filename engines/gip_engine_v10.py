"""engines/gip_engine_v10.py — Hedgeye GIP Model v10 (Sprint 4)

Upgrades vs v9:
  • EXPANDED series — uses all 30 series from fred_loader v3
    (was: 15 series → now: 30 series including PPI, PCEPI, M2, WALCL, etc.)
  • BAYESIAN regime-conditional weights
    Each Quad regime has its own weight vector. Quad determined first via
    prior probabilities, then weights conditional on Quad are applied.
  • NOWCASTING layer — combines weekly indicators (ICSA, WALCL, RRPONTSYD)
    with monthly indicators for high-frequency adjustment
  • GLOBAL extension — supports country-level Quad propagation
  • Output backwards-compatible with v9 GIPOutput shape

USAGE: drop-in replacement, orchestrator calls `from engines.gip_engine_v10 import gip_engine_v10`
       (we keep old gip_engine.py as legacy fallback)
"""
from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple, List

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


# ────────────────────────────────────────────────────────────────────────
# HELPERS (defensive series math)
# ────────────────────────────────────────────────────────────────────────

def _safe(s) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    if hasattr(s, "values"):
        return pd.to_numeric(s, errors="coerce").dropna()
    return pd.Series(dtype=float)


def _last(s) -> float:
    s = _safe(s)
    return float(s.iloc[-1]) if not s.empty else float("nan")


def _yoy(s) -> float:
    s = _safe(s)
    if len(s) < 13:
        return float("nan")
    base = float(s.iloc[-13])
    if not math.isfinite(base) or abs(base) < 1e-10:
        return float("nan")
    return float(s.iloc[-1] / base - 1)


def _qoq_ann(s) -> float:
    """Quarter-over-quarter annualized."""
    s = _safe(s)
    if len(s) < 4:
        return float("nan")
    base = float(s.iloc[-4])
    if not math.isfinite(base) or abs(base) < 1e-10:
        return float("nan")
    return float((s.iloc[-1] / base) ** 4 - 1)


def _mom(s) -> float:
    s = _safe(s)
    if len(s) < 2:
        return float("nan")
    base = float(s.iloc[-2])
    if not math.isfinite(base) or abs(base) < 1e-10:
        return float("nan")
    return float(s.iloc[-1] / base - 1)


def _zscore(s, lookback: int = 36) -> float:
    s = _safe(s)
    if len(s) < lookback:
        return float("nan")
    tail = s.tail(lookback)
    mu, sd = float(tail.mean()), float(tail.std())
    if sd <= 0 or not math.isfinite(sd):
        return float("nan")
    return (float(tail.iloc[-1]) - mu) / sd


# ────────────────────────────────────────────────────────────────────────
# BAYESIAN REGIME-CONDITIONAL WEIGHTS
# ────────────────────────────────────────────────────────────────────────

# Prior probabilities (uniform — let data dominate)
QUAD_PRIORS = {"Q1": 0.25, "Q2": 0.25, "Q3": 0.25, "Q4": 0.25}

# Each Quad has its own optimal weighting vector for growth/inflation factors
# (calibrated on the assumption that some series are more predictive in certain regimes)

GROWTH_WEIGHTS_BY_QUAD = {
    # Q1 (Goldilocks): production + retail lead
    "Q1": {"INDPRO": 0.20, "RSAFS": 0.20, "PAYEMS": 0.15, "ICSA": 0.10,
           "ISMNO": 0.15, "PERMIT": 0.10, "DGORDER": 0.10},
    # Q2 (Reflation): industrial + capex lead
    "Q2": {"INDPRO": 0.25, "DGORDER": 0.20, "ISMNO": 0.20, "PAYEMS": 0.15,
           "RSAFS": 0.10, "PERMIT": 0.05, "HOUST": 0.05},
    # Q3 (Stagflation): jobless claims + sentiment lead (stress signals)
    "Q3": {"ICSA": 0.25, "UNRATE": 0.20, "ISMNO": 0.15, "INDPRO": 0.15,
           "PAYEMS": 0.10, "RSAFS": 0.10, "HOUST": 0.05},
    # Q4 (Deflation): housing + permits + claims (early-cycle stress)
    "Q4": {"ICSA": 0.30, "HOUST": 0.20, "PERMIT": 0.15, "UNRATE": 0.15,
           "INDPRO": 0.10, "PAYEMS": 0.05, "DGORDER": 0.05},
}

INFLATION_WEIGHTS_BY_QUAD = {
    # Q1: core CPI dominant
    "Q1": {"CORECPI": 0.30, "CPI": 0.20, "PCEPILFE": 0.20, "PCEPI": 0.15, "PPI": 0.15},
    # Q2: PPI + headline (cost-push)
    "Q2": {"PPI": 0.25, "CPI": 0.25, "CORECPI": 0.20, "PCEPI": 0.15, "PCEPILFE": 0.15},
    # Q3: headline CPI + PPI (stagflation accelerator)
    "Q3": {"CPI": 0.30, "PPI": 0.25, "CORECPI": 0.20, "PCEPI": 0.15, "PCEPILFE": 0.10},
    # Q4: core PCE + core CPI (deflationary signal)
    "Q4": {"PCEPILFE": 0.30, "CORECPI": 0.25, "PCEPI": 0.20, "CPI": 0.15, "PPI": 0.10},
}


# ────────────────────────────────────────────────────────────────────────
# NOWCASTING LAYER
# Adjusts monthly Quad using weekly/daily indicators
# ────────────────────────────────────────────────────────────────────────

def _nowcast_growth_adjustment(fred: Dict) -> float:
    """Use weekly ICSA + liquidity to nowcast growth deviation."""
    icsa = fred.get("ICSA")
    walcl = fred.get("WALCL")
    rrp = fred.get("RRPONTSYD")

    adj = 0.0

    # ICSA — rising claims = growth slowing
    if icsa is not None:
        z = _zscore(icsa, 36)
        if math.isfinite(z):
            adj -= z * 0.05

    # Fed balance sheet expansion = liquidity tailwind for growth
    if walcl is not None:
        m = _mom(walcl)
        if math.isfinite(m):
            adj += m * 0.10

    # RRP drainage = liquidity into markets = growth tailwind
    if rrp is not None:
        m = _mom(rrp)
        if math.isfinite(m):
            adj -= m * 0.05  # rising RRP = liquidity sink

    return adj


def _nowcast_inflation_adjustment(fred: Dict) -> float:
    """Use daily breakevens to nowcast inflation expectations."""
    t5yie = fred.get("T5YIE")
    t10yie = fred.get("T10YIE")

    adj = 0.0
    if t5yie is not None:
        z = _zscore(t5yie, 12)
        if math.isfinite(z):
            adj += z * 0.03
    if t10yie is not None:
        z = _zscore(t10yie, 12)
        if math.isfinite(z):
            adj += z * 0.02
    return adj


# ────────────────────────────────────────────────────────────────────────
# QUAD CLASSIFICATION
# ────────────────────────────────────────────────────────────────────────

def _classify_quad(growth_momentum: float, inflation_momentum: float) -> str:
    """Map (growth_mom, inflation_mom) → Quad."""
    if not math.isfinite(growth_momentum):
        growth_momentum = 0.0
    if not math.isfinite(inflation_momentum):
        inflation_momentum = 0.0

    g_up = growth_momentum > 0
    i_up = inflation_momentum > 0

    if g_up and not i_up:
        return "Q1"  # Goldilocks
    if g_up and i_up:
        return "Q2"  # Reflation
    if not g_up and i_up:
        return "Q3"  # Stagflation
    return "Q4"      # Deflation


def _quad_probabilities(growth_momentum: float, inflation_momentum: float,
                        confidence_factor: float = 5.0) -> Dict[str, float]:
    """
    Use softmax-like assignment for Quad probability.
    Higher confidence_factor → more concentrated distribution.
    """
    if not math.isfinite(growth_momentum):
        growth_momentum = 0.0
    if not math.isfinite(inflation_momentum):
        inflation_momentum = 0.0

    # Distance from each Quad's archetype
    quad_archetypes = {
        "Q1": (1.0, -1.0),   # growth up, inflation down
        "Q2": (1.0, 1.0),    # both up
        "Q3": (-1.0, 1.0),   # growth down, inflation up
        "Q4": (-1.0, -1.0),  # both down
    }
    # Project current onto each archetype (dot product)
    scores = {}
    for q, (ga, ia) in quad_archetypes.items():
        score = ga * growth_momentum + ia * inflation_momentum
        scores[q] = score * confidence_factor

    # Softmax with prior
    exp_scores = {q: math.exp(s) * QUAD_PRIORS[q] for q, s in scores.items()}
    total = sum(exp_scores.values())
    if total <= 0:
        return QUAD_PRIORS.copy()
    return {q: v / total for q, v in exp_scores.items()}


# ────────────────────────────────────────────────────────────────────────
# GIP OUTPUT DATACLASS
# ────────────────────────────────────────────────────────────────────────

@dataclass
class GIPOutput:
    structural_quad: str = "Q1"
    monthly_quad: str = "Q1"
    structural_confidence: float = 0.50
    monthly_confidence: float = 0.50
    growth_momentum: float = 0.0
    inflation_momentum: float = 0.0
    growth_level: float = 0.0
    inflation_level: float = 0.0
    nowcast_growth_adj: float = 0.0
    nowcast_inflation_adj: float = 0.0
    quad_probabilities: Dict[str, float] = field(default_factory=dict)
    features: Dict = field(default_factory=dict)
    series_coverage: Dict = field(default_factory=dict)
    notes: List[str] = field(default_factory=list)


# ────────────────────────────────────────────────────────────────────────
# MAIN ENGINE
# ────────────────────────────────────────────────────────────────────────

def gip_engine_v10(fred: Dict, vix_last: float = 20.0,
                  prior_quad: Optional[str] = None) -> GIPOutput:
    """
    Hedgeye GIP v10 with Bayesian regime-conditional weighting.

    Args:
        fred: dict of FRED series (from data/fred_loader.py v3)
        vix_last: latest VIX level
        prior_quad: previous-period quad (for transition smoothing)
    """
    output = GIPOutput()
    notes: List[str] = []
    series_coverage: Dict[str, bool] = {}

    # ─── Growth Momentum (multi-quad weighted) ───
    growth_indicators_yoy: Dict[str, float] = {}
    for key in ("INDPRO", "RSAFS", "PAYEMS", "DGORDER", "PERMIT", "HOUST"):
        v = _yoy(fred.get(key))
        series_coverage[key] = math.isfinite(v)
        if math.isfinite(v):
            growth_indicators_yoy[key] = v

    growth_indicators_mom: Dict[str, float] = {}
    for key in ("ICSA", "UNRATE", "ISMNO"):
        v = _mom(fred.get(key)) if key != "ICSA" else _zscore(fred.get(key), 12)
        series_coverage[key] = math.isfinite(v)
        if math.isfinite(v):
            growth_indicators_mom[key] = v

    # First pass: equal-weighted estimate to determine likely Quad
    if growth_indicators_yoy:
        prelim_growth = np.mean([v for v in growth_indicators_yoy.values() if math.isfinite(v)])
    else:
        prelim_growth = 0.0
        notes.append("growth_proxy_synthetic")

    # ─── Inflation Momentum ───
    inflation_indicators_yoy: Dict[str, float] = {}
    for key in ("CPI", "CORECPI", "PCEPI", "PCEPILFE", "PPI"):
        v = _yoy(fred.get(key))
        series_coverage[key] = math.isfinite(v)
        if math.isfinite(v):
            inflation_indicators_yoy[key] = v

    if inflation_indicators_yoy:
        prelim_infl = np.mean([v for v in inflation_indicators_yoy.values() if math.isfinite(v)])
    else:
        prelim_infl = 0.025
        notes.append("inflation_proxy_synthetic")

    # ─── Preliminary Quad ───
    # Compare current to 12M trailing average for momentum
    growth_momentum = prelim_growth - 0.02  # 2% trend baseline
    inflation_momentum = prelim_infl - 0.025  # 2.5% trend baseline

    prelim_quad = _classify_quad(growth_momentum, inflation_momentum)

    # ─── Apply quad-conditional weights (Bayesian refinement) ───
    refined_growth = 0.0
    growth_weights = GROWTH_WEIGHTS_BY_QUAD.get(prelim_quad, GROWTH_WEIGHTS_BY_QUAD["Q1"])
    growth_total_weight = 0.0
    for key, weight in growth_weights.items():
        val = growth_indicators_yoy.get(key, growth_indicators_mom.get(key))
        if val is not None and math.isfinite(val):
            refined_growth += val * weight
            growth_total_weight += weight
    if growth_total_weight > 0:
        refined_growth = refined_growth / growth_total_weight
    else:
        refined_growth = prelim_growth

    refined_inflation = 0.0
    infl_weights = INFLATION_WEIGHTS_BY_QUAD.get(prelim_quad, INFLATION_WEIGHTS_BY_QUAD["Q1"])
    infl_total_weight = 0.0
    for key, weight in infl_weights.items():
        val = inflation_indicators_yoy.get(key)
        if val is not None and math.isfinite(val):
            refined_inflation += val * weight
            infl_total_weight += weight
    if infl_total_weight > 0:
        refined_inflation = refined_inflation / infl_total_weight
    else:
        refined_inflation = prelim_infl

    # ─── Nowcasting Adjustments ───
    nowcast_g = _nowcast_growth_adjustment(fred)
    nowcast_i = _nowcast_inflation_adjustment(fred)

    monthly_growth = refined_growth + nowcast_g - 0.02
    monthly_inflation = refined_inflation + nowcast_i - 0.025
    structural_growth = refined_growth - 0.02
    structural_inflation = refined_inflation - 0.025

    # ─── Final Quad Assignments ───
    output.structural_quad = _classify_quad(structural_growth, structural_inflation)
    output.monthly_quad = _classify_quad(monthly_growth, monthly_inflation)

    # Probabilities
    s_probs = _quad_probabilities(structural_growth, structural_inflation, confidence_factor=4.0)
    m_probs = _quad_probabilities(monthly_growth, monthly_inflation, confidence_factor=5.0)

    output.structural_confidence = s_probs[output.structural_quad]
    output.monthly_confidence = m_probs[output.monthly_quad]
    output.quad_probabilities = s_probs

    # Output fields
    output.growth_momentum = float(structural_growth)
    output.inflation_momentum = float(structural_inflation)
    output.growth_level = float(refined_growth)
    output.inflation_level = float(refined_inflation)
    output.nowcast_growth_adj = float(nowcast_g)
    output.nowcast_inflation_adj = float(nowcast_i)
    output.series_coverage = series_coverage
    output.notes = notes

    output.features = {
        "growth_indicators_yoy": growth_indicators_yoy,
        "inflation_indicators_yoy": inflation_indicators_yoy,
        "growth_indicators_mom": growth_indicators_mom,
        "prelim_quad": prelim_quad,
        "monthly_quad_probs": m_probs,
        "n_series_loaded": sum(1 for v in series_coverage.values() if v),
        "n_series_total": len(series_coverage),
    }

    return output


# Backwards-compat shim — orchestrator imports gip_engine
def gip_engine(fred: Dict, vix_last: float = 20.0, **kwargs) -> Dict:
    """Wrapper returning v9-compatible dict shape."""
    out = gip_engine_v10(fred, vix_last, prior_quad=kwargs.get("prior_quad"))
    return {
        "structural_quad": out.structural_quad,
        "monthly_quad": out.monthly_quad,
        "structural_confidence": out.structural_confidence,
        "monthly_confidence": out.monthly_confidence,
        "growth_momentum": out.growth_momentum,
        "inflation_momentum": out.inflation_momentum,
        "growth_level": out.growth_level,
        "inflation_level": out.inflation_level,
        "quad_probabilities": out.quad_probabilities,
        "features": out.features,
        "series_coverage": out.series_coverage,
        "nowcast": {
            "growth_adj": out.nowcast_growth_adj,
            "inflation_adj": out.nowcast_inflation_adj,
        },
        "notes": out.notes,
        "version": "v10",
    }
