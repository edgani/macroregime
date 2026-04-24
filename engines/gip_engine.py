"""engines/gip_engine.py — TRUE Hedgeye GIP Model.

=============================================================================
HEDGEYE METHODOLOGY (Verified)
=============================================================================

Core question: Is growth and inflation HEATING UP or COOLING DOWN?

Signal = YoY Rate of Change — then SECOND DERIVATIVE of that RoC.
"Are growth and inflation accelerating or decelerating?"

30 monthly data points → build nowcast for current quarter
90 quarterly data points → structural multi-quarter view

Quarterly Quad = CLIMATE (dominant macro backdrop)
Monthly Quad   = WEATHER (shorter-term overlay within the climate)

"The Quads are like seasons — they follow each other in a continuous loop."

Quad definitions:
  Q1: Growth ↑, Inflation ↓ → Goldilocks
  Q2: Growth ↑, Inflation ↑ → Reflation
  Q3: Growth ↓, Inflation ↑ → Stagflation
  Q4: Growth ↓, Inflation ↓ → Deflation

Policy is FRONT-RUN by getting G+I right — not an independent input.
"If I get Growth and Inflation right, I'm front-running the policy move."

=============================================================================
IMPLEMENTATION
=============================================================================

Inputs → Features → Scaled Scores → Quad Probabilities
- No hardcoded thresholds for what "is" Q1/Q2/Q3/Q4
- Softmax over scores → probability distribution
- Most probable quad = current regime
- Dual horizon: structural (quarterly) + monthly (weather)

Data quality tracking: every output carries a confidence and coverage metric.
When FRED data missing → market proxy fallback, clearly labeled.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import (
    GROWTH_LEVEL_WEIGHTS, GROWTH_MOM_WEIGHTS,
    INFLATION_LEVEL_WEIGHTS, INFLATION_MOM_WEIGHTS,
    STRUCTURAL_WEIGHTS, MONTHLY_WEIGHTS,
    POLICY_WEIGHT_STRUCTURAL, POLICY_WEIGHT_MONTHLY,
    ISM_NEUTRAL, QUAD_ASSET_PERFORMANCE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe(s: pd.Series) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    return pd.to_numeric(s, errors="coerce").dropna()


def _last(s: pd.Series) -> float:
    s = _safe(s)
    return float(s.iloc[-1]) if not s.empty else float("nan")


def _yoy(s: pd.Series) -> float:
    """YoY rate of change (12 months)."""
    s = _safe(s)
    if len(s) < 13:
        return float("nan")
    base = float(s.iloc[-13])
    if not math.isfinite(base) or abs(base) < 1e-10:
        return float("nan")
    return float(s.iloc[-1] / base - 1)


def _roc(s: pd.Series, n: int = 12, offset: int = 3) -> float:
    """
    TRUE Hedgeye second derivative:
    Δ(YoY RoC) = current YoY - prior YoY (offset months ago)

    Positive = accelerating (Quad trending UP on that axis)
    Negative = decelerating (Quad trending DOWN on that axis)
    """
    s = _safe(s)
    if len(s) < n + offset + 1:
        return float("nan")
    try:
        r_now  = float(s.iloc[-1]       / s.iloc[-n-1]        - 1)
        r_prev = float(s.iloc[-offset-1]/ s.iloc[-n-offset-1] - 1)
        if not (math.isfinite(r_now) and math.isfinite(r_prev)):
            return float("nan")
        return r_now - r_prev
    except Exception:
        return float("nan")


def _delta(s: pd.Series, n: int) -> float:
    s = _safe(s)
    if len(s) < n + 1:
        return float("nan")
    return float(s.iloc[-1] - s.iloc[-n-1])


def _ret(s: pd.Series, n: int) -> float:
    """n-bar return."""
    s = _safe(s)
    if len(s) < n + 1:
        return float("nan")
    base = float(s.iloc[-n-1])
    if not math.isfinite(base) or abs(base) < 1e-10:
        return float("nan")
    return float(s.iloc[-1] / base - 1)


def _tanh_scale(x: float, scale: float) -> float:
    """Map x to [-1,1] via tanh, with scale controlling sensitivity."""
    if not math.isfinite(x):
        return float("nan")
    return float(np.tanh(x / scale))


def _wmean(inputs: Dict[str, float], weights: Dict[str, float]) -> float:
    """Weighted mean of named inputs, skipping NaN."""
    total_w = 0.0
    total   = 0.0
    for k, w in weights.items():
        v = inputs.get(k, float("nan"))
        if math.isfinite(v):
            total   += w * v
            total_w += w
    if total_w < 0.01:
        return 0.0
    return total / total_w


def _coverage(inputs: Dict[str, float]) -> float:
    valid = sum(1 for v in inputs.values() if math.isfinite(v))
    return valid / max(len(inputs), 1)


def _softmax(scores: Dict[str, float]) -> Dict[str, float]:
    keys = list(scores.keys())
    vals = np.array([scores[k] for k in keys], dtype=float)
    vals = np.clip(vals, -10, 10)
    e = np.exp(vals - vals.max())
    s = e / e.sum()
    return {k: float(v) for k, v in zip(keys, s)}


# ---------------------------------------------------------------------------
# Price proxy fallback (when FRED missing)
# ---------------------------------------------------------------------------

def _price_proxy(prices: Dict[str, pd.Series]) -> Dict[str, float]:
    """Market-implied growth/inflation proxy from ETF prices."""
    spy_3m  = _ret(prices.get("SPY"), 63)
    xli_3m  = _ret(prices.get("XLI"), 63)
    xly_3m  = _ret(prices.get("XLY"), 63)
    iwm_3m  = _ret(prices.get("IWM"), 63)
    xhb_3m  = _ret(prices.get("XHB"), 63)
    uup_3m  = _ret(prices.get("UUP"), 63)
    oil_3m  = _ret(prices.get("GLD"), 63)   # use GLD not oil ETF for inflation signal quality
    gld_3m  = _ret(prices.get("GLD"), 63)
    tlt_1m  = _ret(prices.get("TLT"), 21)

    proxy = {}
    # Growth proxies
    proxy["indpro_yoy"]     = float(np.nan_to_num(0.55*xli_3m + 0.45*spy_3m,  nan=0.0))
    proxy["retail_yoy"]     = float(np.nan_to_num(0.60*xly_3m + 0.40*spy_3m,  nan=0.0))
    proxy["payrolls_yoy"]   = float(np.nan_to_num(0.50*iwm_3m + 0.50*spy_3m,  nan=0.0))
    proxy["housing_yoy"]    = float(np.nan_to_num(0.70*(xhb_3m or 0) + 0.30*(iwm_3m or 0), nan=0.0))
    proxy["ism_norm"]       = float(np.nan_to_num(0.0 + 10.0*(xli_3m or 0),   nan=0.0))  # delta around 0
    proxy["unrate_inv"]     = float(np.nan_to_num(-0.10*(iwm_3m or 0),         nan=0.0))
    proxy["claims_inv"]     = float(np.nan_to_num(-5.0*(iwm_3m or 0),          nan=0.0))
    # Inflation proxies
    proxy["cpi_yoy"]        = float(np.nan_to_num(0.025 + 0.35*(oil_3m or 0) + 0.05*(gld_3m or 0), nan=0.025))
    proxy["core_cpi_yoy"]   = float(np.nan_to_num(0.023 + 0.15*(oil_3m or 0) - 0.05*(uup_3m or 0), nan=0.023))
    proxy["breakeven_5y"]   = float(np.nan_to_num(2.2 + 1.2*(oil_3m or 0) + 0.4*(gld_3m or 0), nan=2.2))
    proxy["ppi_yoy"]        = float(np.nan_to_num(0.03 + 0.55*(oil_3m or 0),  nan=0.03))
    # RoC proxies (momentum)
    spy_1m  = _ret(prices.get("SPY"), 21)
    xli_1m  = _ret(prices.get("XLI"), 21)
    oil_1m  = _ret(prices.get("CL=F"), 21) or _ret(prices.get("USO"), 21) or 0.0
    gld_1m  = _ret(prices.get("GLD"), 21) or 0.0
    uup_1m  = _ret(prices.get("UUP"), 21) or 0.0
    proxy["indpro_roc"]     = float(np.nan_to_num(0.60*(xli_1m or 0) + 0.40*(spy_1m or 0), nan=0.0))
    proxy["retail_roc"]     = float(np.nan_to_num((xly_3m or 0) - (xly_3m or 0), nan=0.0))  # delta
    proxy["payrolls_roc"]   = float(np.nan_to_num((iwm_3m or 0) * 0.3, nan=0.0))
    proxy["ism_delta"]      = float(np.nan_to_num((xli_1m or 0) * 100, nan=0.0))
    proxy["unrate_delta"]   = float(np.nan_to_num(-(iwm_1m) if (iwm_1m := _ret(prices.get("IWM"), 21)) else 0.0, nan=0.0))
    proxy["claims_delta"]   = 0.0
    proxy["cpi_roc"]        = float(np.nan_to_num(oil_1m * 0.4 + gld_1m * 0.1, nan=0.0))
    proxy["core_cpi_roc"]   = float(np.nan_to_num(oil_1m * 0.2 - uup_1m * 0.1, nan=0.0))
    proxy["breakeven_delta"]= float(np.nan_to_num(oil_1m * 0.3 + gld_1m * 0.1, nan=0.0))
    proxy["oil_1m"]         = float(np.nan_to_num(oil_1m, nan=0.0))
    proxy["dxy_inv_1m"]     = float(np.nan_to_num(-(uup_1m), nan=0.0))
    proxy["oil_3m"]         = float(np.nan_to_num(oil_3m or 0.0, nan=0.0))
    proxy["gold_3m"]        = float(np.nan_to_num(gld_3m, nan=0.0))
    proxy["tlt_1m"]         = float(np.nan_to_num(tlt_1m, nan=0.0))
    proxy["dxy_3m"]         = float(np.nan_to_num(uup_3m, nan=0.0))
    return proxy


# ---------------------------------------------------------------------------
# Feature extraction from FRED
# ---------------------------------------------------------------------------

def _extract_fred_features(fred: Dict[str, pd.Series]) -> Dict[str, float]:
    f: Dict[str, float] = {}

    # Growth level (YoY)
    f["indpro_yoy"]    = _yoy(fred.get("INDPRO"))
    f["retail_yoy"]    = _yoy(fred.get("RSAFS"))
    f["payrolls_yoy"]  = _yoy(fred.get("PAYEMS"))
    ism = _last(fred.get("ISMNO") or fred.get("MANEMP"))  # fallback
    f["ism_norm"]      = (ism - ISM_NEUTRAL) / ISM_NEUTRAL if math.isfinite(ism) else float("nan")
    f["housing_yoy"]   = _yoy(fred.get("HOUST"))
    unrate_now = _last(fred.get("UNRATE"))
    unrate_3m  = _delta(fred.get("UNRATE"), 3)
    f["unrate_inv"]    = -float(np.tanh(unrate_3m / 0.2)) if math.isfinite(unrate_3m) else float("nan")
    claims_d = _delta(fred.get("ICSA"), 13)
    f["claims_inv"]    = -float(np.tanh(claims_d / 50000)) if math.isfinite(claims_d) else float("nan")

    # Growth momentum (2nd derivative — TRUE Hedgeye signal)
    f["indpro_roc"]    = _roc(fred.get("INDPRO"),  12, 3)
    f["retail_roc"]    = _roc(fred.get("RSAFS"),   12, 3)
    f["payrolls_roc"]  = _roc(fred.get("PAYEMS"),  12, 3)
    ism_s = fred.get("ISMNO") or fred.get("MANEMP")
    f["ism_delta"]     = _delta(ism_s, 3) / ISM_NEUTRAL if ism_s is not None else float("nan")
    f["unrate_delta"]  = -unrate_3m / 0.2 if math.isfinite(unrate_3m) else float("nan")
    f["claims_delta"]  = -claims_d / 50000 if math.isfinite(claims_d) else float("nan")

    # Inflation level (YoY)
    f["cpi_yoy"]       = _yoy(fred.get("CPIAUCSL"))
    f["core_cpi_yoy"]  = _yoy(fred.get("CPILFESL"))
    f["ppi_yoy"]       = _yoy(fred.get("PPIACO"))
    be5 = _last(fred.get("T5YIE"))
    f["breakeven_5y"]  = (be5 - 2.2) / 2.0 if math.isfinite(be5) else float("nan")

    # Inflation momentum (2nd derivative)
    f["cpi_roc"]       = _roc(fred.get("CPIAUCSL"),  12, 3)
    f["core_cpi_roc"]  = _roc(fred.get("CPILFESL"),  12, 3)
    be5_delta = _delta(fred.get("T5YIE"), 1)
    f["breakeven_delta"] = float(np.nan_to_num(be5_delta / 0.3, nan=float("nan")))

    # Policy
    ff_delta = _delta(fred.get("FEDFUNDS") or fred.get("DFF"), 3)
    f["policy_score"]  = float(np.tanh(-(ff_delta or 0.0) / 0.5))   # positive = easing
    m2_roc = _roc(fred.get("M2SL"), 12, 3)
    f["liquidity_score"] = float(np.tanh((m2_roc or 0.0) / 0.05))

    return f


# ---------------------------------------------------------------------------
# GIP output dataclass
# ---------------------------------------------------------------------------

@dataclass
class GIPResult:
    # Structural (quarterly climate)
    structural_quad:  str
    structural_probs: Dict[str, float]
    structural_conf:  float
    structural_g:     float   # growth score (-1 to 1)
    structural_i:     float   # inflation score (-1 to 1)

    # Monthly (weather overlay)
    monthly_quad:     str
    monthly_probs:    Dict[str, float]
    monthly_conf:     float
    monthly_g:        float
    monthly_i:        float

    # Meta
    divergence:       str     # 'aligned' | 'divergent'
    operating_regime: str     # human-readable
    policy_score:     float
    data_coverage:    float
    proxy_share:      float   # 0=all FRED, 1=all proxy
    features:         Dict[str, float] = field(default_factory=dict)

    @property
    def climate_label(self) -> str:
        return f"Q{self.structural_quad[-1]} {_quad_name(self.structural_quad)}"

    @property
    def weather_label(self) -> str:
        return f"Q{self.monthly_quad[-1]} {_quad_name(self.monthly_quad)} (monthly)"

    @property
    def flip_hazard(self) -> float:
        """Probability regime flips in next 4-8 weeks."""
        margin = self.structural_probs.get(self.structural_quad, 0.5) - sorted(
            self.structural_probs.values(), reverse=True
        )[1]
        return float(np.clip(0.5 - 0.8 * margin + 0.2 * (1.0 - self.data_coverage), 0.0, 1.0))


def _quad_name(q: str) -> str:
    return {"Q1": "Goldilocks", "Q2": "Reflation", "Q3": "Stagflation", "Q4": "Deflation"}.get(q, q)


# ---------------------------------------------------------------------------
# Core quad scorer
# ---------------------------------------------------------------------------

def _score_quad(
    g_level: float,
    g_mom:   float,
    i_level: float,
    i_mom:   float,
    policy:  float,
    sw: Dict[str, float],  # structural or monthly weights
    pw: float,             # policy weight
    modifiers: Dict[str, float] = None,
) -> Tuple[Dict[str, float], str, float]:
    """
    Compute raw quad scores, apply softmax, return probabilities.

    Logic: Hedgeye's quad is determined purely by direction of G and I.
    Q1: G↑I↓ → positive G, negative I
    Q2: G↑I↑ → positive G, positive I
    Q3: G↓I↑ → negative G, positive I
    Q4: G↓I↓ → negative G, negative I

    g_level, g_mom ∈ [-1, 1], i_level, i_mom ∈ [-1, 1]
    """
    modifiers = modifiers or {}

    # Composite G and I signals
    g = sw["growth_level"] * g_level + sw["growth_momentum"] * g_mom
    i = sw["inflation_level"] * i_level + sw["inflation_momentum"] * i_mom

    # Policy adjustment: easing supports Q1/Q4, tightening supports Q3
    p = pw * policy  # small contribution

    # Raw scores
    raw = {
        "Q1": +g - i + p * 0.60,   # easing confirms goldilocks
        "Q2": +g + i - p * 0.30,   # tightening expected but not decisive
        "Q3": -g + i - p * 0.80,   # tightening CONFIRMS stagflation
        "Q4": -g - i + p * 1.00,   # easing = policy response to deflation
    }

    # Optional modifiers (inflation shock, slowdown flags etc)
    for quad, delta in modifiers.items():
        if quad in raw:
            raw[quad] += delta

    probs = _softmax(raw)
    top = max(probs, key=probs.get)
    margin = probs[top] - sorted(probs.values(), reverse=True)[1]
    conf = float(np.clip(probs[top] * (0.65 + 0.35 * margin / 0.5), 0.0, 1.0))
    return probs, top, conf


# ---------------------------------------------------------------------------
# Main GIP Engine
# ---------------------------------------------------------------------------

class GIPEngine:
    """
    Hedgeye GIP Model implementation.

    Inputs:
      fred:   {series_id: pd.Series} from FRED
      prices: {ticker: pd.Series} for market proxies

    Outputs: GIPResult with structural + monthly quad assignments.
    """

    def run(
        self,
        fred: Dict[str, pd.Series],
        prices: Dict[str, pd.Series],
    ) -> GIPResult:

        # 1. Extract FRED features
        f_fred = _extract_fred_features(fred)

        # 2. Extract price proxy features
        f_proxy = _price_proxy(prices)

        # 3. Coverage tracking: which keys have FRED data?
        fred_keys = [
            "indpro_yoy","retail_yoy","payrolls_yoy","cpi_yoy","core_cpi_yoy",
            "ism_norm","housing_yoy","unrate_inv","claims_inv",
        ]
        n_fred = sum(1 for k in fred_keys if math.isfinite(f_fred.get(k, float("nan"))))
        proxy_share = 1.0 - n_fred / len(fred_keys)

        # 4. Merge: prefer FRED, fallback to proxy
        def merge(key: str) -> float:
            v = f_fred.get(key, float("nan"))
            if math.isfinite(v):
                return v
            return f_proxy.get(key, float("nan"))

        # Growth level inputs → scale to [-1, 1]
        g_lvl_inputs = {
            "indpro_yoy":   _tanh_scale(merge("indpro_yoy")   - 0.02, 0.05),
            "retail_yoy":   _tanh_scale(merge("retail_yoy")   - 0.03, 0.06),
            "payrolls_yoy": _tanh_scale(merge("payrolls_yoy") - 0.015, 0.03),
            "housing_yoy":  _tanh_scale(merge("housing_yoy"),   0.10),
            "ism_norm":     _tanh_scale(merge("ism_norm"),       0.10),
            "unrate_inv":   merge("unrate_inv"),
            "claims_inv":   merge("claims_inv"),
        }
        # Growth momentum inputs (2nd derivative)
        g_mom_inputs = {
            "indpro_roc":   _tanh_scale(merge("indpro_roc"),   0.025),
            "retail_roc":   _tanh_scale(merge("retail_roc"),   0.030),
            "payrolls_roc": _tanh_scale(merge("payrolls_roc"), 0.015),
            "ism_delta":    _tanh_scale(merge("ism_delta"),     0.05),
            "unrate_delta": _tanh_scale(merge("unrate_delta"),  1.0),
            "claims_delta": _tanh_scale(merge("claims_delta"),  1.0),
        }
        # Inflation level inputs
        i_lvl_inputs = {
            "cpi_yoy":      _tanh_scale(merge("cpi_yoy")     - 0.025, 0.020),
            "core_cpi_yoy": _tanh_scale(merge("core_cpi_yoy")- 0.025, 0.015),
            "breakeven_5y": merge("breakeven_5y"),
            "ppi_yoy":      _tanh_scale(merge("ppi_yoy")     - 0.025, 0.030),
            "oil_3m":       _tanh_scale(merge("oil_3m"),       0.25),
            "gold_3m":      _tanh_scale(merge("gold_3m"),       0.18),
        }
        # Inflation momentum inputs
        i_mom_inputs = {
            "cpi_roc":      _tanh_scale(merge("cpi_roc"),       0.012),
            "core_cpi_roc": _tanh_scale(merge("core_cpi_roc"),  0.010),
            "breakeven_delta": _tanh_scale(merge("breakeven_delta"), 1.0),
            "oil_1m":       _tanh_scale(merge("oil_1m"),         0.06),
            "dxy_inv_1m":   _tanh_scale(merge("dxy_inv_1m"),     0.06),
        }

        # 5. Weighted aggregation
        g_level = _wmean(g_lvl_inputs, GROWTH_LEVEL_WEIGHTS)
        g_mom   = _wmean(g_mom_inputs, GROWTH_MOM_WEIGHTS)
        i_level = _wmean(i_lvl_inputs, INFLATION_LEVEL_WEIGHTS)
        i_mom   = _wmean(i_mom_inputs, INFLATION_MOM_WEIGHTS)

        # Policy
        policy  = float(np.nan_to_num(merge("policy_score"), nan=0.0))

        # Overall data coverage
        all_inputs = {**g_lvl_inputs, **g_mom_inputs, **i_lvl_inputs, **i_mom_inputs}
        coverage = _coverage(all_inputs)

        # 6. Structural quad (quarterly climate)
        # Use structural-weighted combination
        struct_probs, struct_quad, struct_conf = _score_quad(
            g_level, g_mom, i_level, i_mom, policy,
            STRUCTURAL_WEIGHTS, POLICY_WEIGHT_STRUCTURAL,
        )

        # 7. Monthly quad (weather overlay)
        # More responsive: recent market signals dominate
        oil_1m  = _ret(prices.get("CL=F"), 21) or merge("oil_1m")
        gld_1m  = _ret(prices.get("GLD"),  21) or 0.0
        spy_1m  = _ret(prices.get("SPY"),  21) or 0.0
        xli_1m  = _ret(prices.get("XLI"),  21) or 0.0
        be_delta = merge("breakeven_delta")

        # Monthly growth = momentum-dominant + recent market confirmation
        monthly_g_level = 0.40 * g_level + 0.60 * g_mom
        monthly_g_mom   = 0.30 * g_mom + 0.70 * float(np.tanh(
            0.40 * (xli_1m or 0) / 0.05 + 0.60 * (spy_1m or 0) / 0.05
        ))
        # Monthly inflation = short-horizon forward signals
        monthly_i_level = 0.45 * i_level + 0.35 * i_mom + 0.20 * _tanh_scale(
            (oil_1m or 0), 0.06
        )
        monthly_i_mom   = 0.30 * i_mom + 0.70 * float(np.tanh(
            0.50 * (oil_1m or 0) / 0.06 + 0.30 * (gld_1m) / 0.05 + 0.20 * (be_delta or 0)
        ))

        # Inflation shock modifier for monthly (supply shocks)
        cpi_yoy = merge("cpi_yoy")
        core_yoy = merge("core_cpi_yoy")
        headline_gap = cpi_yoy - core_yoy if (math.isfinite(cpi_yoy) and math.isfinite(core_yoy)) else 0.0
        shock = max(0.0, _tanh_scale(headline_gap, 0.004))

        monthly_probs, monthly_quad, monthly_conf = _score_quad(
            monthly_g_level, monthly_g_mom, monthly_i_level, monthly_i_mom, policy,
            MONTHLY_WEIGHTS, POLICY_WEIGHT_MONTHLY,
            modifiers={"Q3": 0.05 * shock, "Q2": -0.03 * shock},
        )

        # 8. Divergence state
        if struct_quad == monthly_quad:
            divergence = "aligned"
            operating_regime = f"Fully Aligned {struct_quad}"
        else:
            divergence = "divergent"
            operating_regime = f"Monthly {monthly_quad} inside Structural {struct_quad}"

        # 9. Collect all features for transparency
        features = {
            "growth_level":   g_level,
            "growth_momentum": g_mom,
            "inflation_level": i_level,
            "inflation_momentum": i_mom,
            "policy_score":   policy,
            "data_coverage":  coverage,
            "proxy_share":    proxy_share,
            "monthly_g_level": monthly_g_level,
            "monthly_g_mom":   monthly_g_mom,
            "monthly_i_level": monthly_i_level,
            "monthly_i_mom":   monthly_i_mom,
            "headline_gap":    headline_gap,
            "inflation_shock": shock,
            **{f"raw_{k}": v for k, v in f_fred.items() if math.isfinite(v)},
        }

        return GIPResult(
            structural_quad=struct_quad,
            structural_probs=struct_probs,
            structural_conf=struct_conf,
            structural_g=g_level + g_mom,
            structural_i=i_level + i_mom,
            monthly_quad=monthly_quad,
            monthly_probs=monthly_probs,
            monthly_conf=monthly_conf,
            monthly_g=monthly_g_level + monthly_g_mom,
            monthly_i=monthly_i_level + monthly_i_mom,
            divergence=divergence,
            operating_regime=operating_regime,
            policy_score=policy,
            data_coverage=coverage,
            proxy_share=proxy_share,
            features=features,
        )


# ---------------------------------------------------------------------------
# Playbook lookup
# ---------------------------------------------------------------------------

def get_playbook(
    structural_quad: str,
    monthly_quad: str,
) -> dict:
    """Return asset class playbook for current quad combination."""
    s = QUAD_ASSET_PERFORMANCE.get(structural_quad, {})
    m = QUAD_ASSET_PERFORMANCE.get(monthly_quad,    {})
    combined_best = list(dict.fromkeys(s.get("best", []) + m.get("best", [])[:2]))
    return {
        "structural":      structural_quad,
        "monthly":         monthly_quad,
        "best_assets":     combined_best,
        "worst_assets":    s.get("worst", []),
        "sectors_ow":      s.get("sectors_overweight", []),
        "sectors_uw":      s.get("sectors_underweight", []),
        "style":           s.get("style", ""),
        "fx":              s.get("fx", ""),
        "bonds":           s.get("bonds", ""),
        "monthly_adds":    m.get("best", [])[:3],
        "note":            s.get("note", ""),
    }
