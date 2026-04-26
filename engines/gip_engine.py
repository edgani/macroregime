"""engines/gip_engine.py — TRUE Hedgeye GIP Model v3

ROOT CAUSE FIX (Structural Q3):
- Proxy growth was using 3M absolute return → bullish bias
- Now uses 6M vs 12M SPREAD (true 2nd derivative: accelerating/decelerating)
- Structural weights: inflation-dominant (55%) for Q3 accuracy
- Added ISMNO FRED series support
- FIX: Added missing clamp01() helper (was called but never defined)
"""
from __future__ import annotations
import math
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
import numpy as np
import pandas as pd
from config.settings import (
    GROWTH_LEVEL_WEIGHTS, GROWTH_MOM_WEIGHTS,
    INFLATION_LEVEL_WEIGHTS, INFLATION_MOM_WEIGHTS,
    STRUCTURAL_WEIGHTS, MONTHLY_WEIGHTS,
    POLICY_WEIGHT_STRUCTURAL, POLICY_WEIGHT_MONTHLY,
    ISM_NEUTRAL, QUAD_ASSET_PERFORMANCE,
)

# ── Safe helpers ─────────────────────────────────────────────────────────────

def _fv(*series_list):
    """Return first non-None, non-empty pd.Series from args."""
    for s in series_list:
        if s is not None:
            if isinstance(s, pd.Series):
                if not s.empty: return s
            else:
                return s
    return None

def _safe(s) -> pd.Series:
    if s is None: return pd.Series(dtype=float)
    return pd.to_numeric(s, errors="coerce").dropna()

def _last(s) -> float:
    s = _safe(s)
    return float(s.iloc[-1]) if not s.empty else float("nan")

def _yoy(s) -> float:
    s = _safe(s)
    if len(s) < 13: return float("nan")
    base = float(s.iloc[-13])
    if not math.isfinite(base) or abs(base) < 1e-10: return float("nan")
    return float(s.iloc[-1] / base - 1)

def _roc(s, n=12, offset=3) -> float:
    """True Hedgeye 2nd derivative: Δ(YoY RoC)."""
    s = _safe(s)
    if len(s) < n + offset + 1: return float("nan")
    try:
        r_now = float(s.iloc[-1] / s.iloc[-n-1] - 1)
        r_prev = float(s.iloc[-offset-1]/ s.iloc[-n-offset-1] - 1)
        if not (math.isfinite(r_now) and math.isfinite(r_prev)): return float("nan")
        return r_now - r_prev
    except: return float("nan")

def _delta(s, n) -> float:
    s = _safe(s)
    if len(s) < n + 1: return float("nan")
    return float(s.iloc[-1] - s.iloc[-n-1])

def _ret(s, n) -> float:
    s = _safe(s)
    if len(s) < n + 1: return float("nan")
    base = float(s.iloc[-n-1])
    if not math.isfinite(base) or abs(base) < 1e-10: return float("nan")
    r = float(s.iloc[-1] / base - 1)
    return r if math.isfinite(r) else float("nan")

def _tanh_scale(x, scale) -> float:
    if not math.isfinite(x): return float("nan")
    return float(np.tanh(x / scale))

def _wmean(inputs: Dict[str, float], weights: Dict[str, float]) -> float:
    total_w = total = 0.0
    for k, w in weights.items():
        v = inputs.get(k, float("nan"))
        if math.isfinite(v): total += w * v; total_w += w
    return total / total_w if total_w > 0.01 else 0.0

def _coverage(inputs: Dict[str, float]) -> float:
    valid = sum(1 for v in inputs.values() if math.isfinite(v))
    return valid / max(len(inputs), 1)

def _softmax(scores: Dict[str, float]) -> Dict[str, float]:
    keys = list(scores.keys())
    vals = np.clip([scores[k] for k in keys], -10, 10)
    e = np.exp(vals - np.max(vals)); e /= e.sum()
    return {k: float(v) for k, v in zip(keys, e)}

def _nan(v) -> float:
    return float(np.nan_to_num(v, nan=0.0))

def _first_finite(*vals, default=0.0):
    """Return first arg that is not None and is finite."""
    for v in vals:
        if v is not None and math.isfinite(v):
            return float(v)
    return float(default)

def _acc_spread(r6, r12):
    """Hedgeye acceleration spread: annualized 6M vs annualized 12M."""
    if not all(math.isfinite(x) for x in [r6, r12]): return 0.0
    return float(r6 * 2.0 - r12)

# ── FIX: clamp01 was called but never defined ─────────────────────────────────
def clamp01(x):
    """Clamp value to [0, 1]."""
    if not math.isfinite(x): return 0.0
    return max(0.0, min(1.0, float(x)))

# ── Price proxy v3 (6M/12M spread = true 2nd derivative) ─────────────────────

def _price_proxy(prices: Dict) -> Dict[str, float]:
    """Market-implied G+I proxy.

    STRUCTURAL signals use 6M vs 12M spread (acceleration/deceleration).
    MONTHLY signals use 1M/3M (short-term momentum).
    """
    def r(t, n): return _ret(prices.get(t), n)

    # ── Short-term (monthly overlay signals) ──────────────────────────────
    spy1 = _first_finite(r("SPY",21)); spy3 = _first_finite(r("SPY",63))
    xli1 = _first_finite(r("XLI",21)); xli3 = _first_finite(r("XLI",63))
    xly1 = _first_finite(r("XLY",21)); xly3 = _first_finite(r("XLY",63))
    iwm1 = _first_finite(r("IWM",21)); iwm3 = _first_finite(r("IWM",63))
    xhb3 = _first_finite(r("XHB",63))
    uup1 = _first_finite(r("UUP",21)); uup3 = _first_finite(r("UUP",63))
    oil1 = _first_finite(r("CL=F",21), r("USO",21))
    oil3 = _first_finite(r("CL=F",63), r("USO",63))
    gld1 = _first_finite(r("GLD",21)); gld3 = _first_finite(r("GLD",63))
    tlt1 = _first_finite(r("TLT",21))

    # ── Long-term (structural signals) ────────────────────────────────────
    spy6 = _first_finite(r("SPY",126)); spy12 = _first_finite(r("SPY",252))
    xli6 = _first_finite(r("XLI",126)); xli12 = _first_finite(r("XLI",252))
    xly6 = _first_finite(r("XLY",126)); xly12 = _first_finite(r("XLY",252))
    iwm6 = _first_finite(r("IWM",126)); iwm12 = _first_finite(r("IWM",252))
    xhb6 = _first_finite(r("XHB",126)); xhb12 = _first_finite(r("XHB",252))
    oil6 = _first_finite(r("CL=F",126), r("USO",126))
    oil12 = _first_finite(r("CL=F",252), r("USO",252))
    gld6 = _first_finite(r("GLD",126)); gld12 = _first_finite(r("GLD",252))

    # ── Acceleration / Deceleration spreads (TRUE Hedgeye 2nd derivative) ───
    spy_acc = _acc_spread(spy6, spy12)
    xli_acc = _acc_spread(xli6, xli12)
    xly_acc = _acc_spread(xly6, xly12)
    iwm_acc = _acc_spread(iwm6, iwm12)
    xhb_acc = _acc_spread(xhb6, xhb12)
    oil_acc = _acc_spread(oil6, oil12)
    gld_acc = _acc_spread(gld6, gld12)

    # ── Credit/Quality signals: Q3 differentiators (6M horizon) ───────────
    hyg6 = _first_finite(r("HYG", 126), r("LQD", 126))
    tlt6 = _first_finite(r("TLT", 126))
    xlp6 = _first_finite(r("XLP", 126))
    xly6v = _first_finite(r("XLY", 126))
    spy6v = _first_finite(r("SPY", 126))
    iwm6v = _first_finite(r("IWM", 126))

    credit_stress_6 = _nan(spy6v - hyg6)
    quality_bid_6 = _nan(tlt6 - spy6v*0.5)
    consumer_stress_6 = _nan(xlp6 - xly6v)
    breadth_stress_6 = _nan(spy6v - iwm6v)

    q3_conf_raw = (
        max(0.0, credit_stress_6) * 2.0 +
        max(0.0, quality_bid_6) * 1.5 +
        max(0.0, consumer_stress_6) * 2.0 +
        max(0.0, breadth_stress_6) * 1.0
    )
    q3_modifier = float(np.tanh(q3_conf_raw / 0.12) * 0.40)
    credit_stress_12 = credit_stress_6
    quality_bid_12 = quality_bid_6
    consumer_stress_12 = consumer_stress_6
    breadth_stress_12 = breadth_stress_6

    return {
        "indpro_yoy": _nan(0.55*xli12 + 0.45*spy12),
        "retail_yoy": _nan(0.60*xly12 + 0.40*spy12),
        "payrolls_yoy": _nan(0.50*iwm12 + 0.50*spy12),
        "housing_yoy": _nan(0.70*xhb12 + 0.30*iwm12),
        "ism_norm": _nan(10.0*xli3),
        "unrate_inv": _nan(-0.10*iwm12),
        "claims_inv": _nan(-5.0*iwm3),

        "cpi_yoy": _nan(0.025 + 0.35*oil12 + 0.05*gld12),
        "core_cpi_yoy": _nan(0.023 + 0.15*oil12 - 0.05*uup3),
        "breakeven_5y": _nan(0.6*oil12 + 0.2*gld12),
        "ppi_yoy": _nan(0.03 + 0.55*oil12),
        "oil_3m": _nan(oil6*2.0),
        "gold_3m": _nan(gld6*2.0),

        "indpro_roc": _nan(0.60*xli_acc + 0.40*spy_acc),
        "retail_roc": _nan(0.60*xly_acc + 0.40*spy_acc),
        "payrolls_roc": _nan(0.50*iwm_acc + 0.50*spy_acc),
        "ism_delta": _nan(xli1*100),
        "unrate_delta": _nan(-iwm1),
        "claims_delta": 0.0,

        "cpi_roc": _nan(oil_acc*0.4 + gld_acc*0.1),
        "core_cpi_roc": _nan(oil_acc*0.2 - uup1*0.1),
        "breakeven_delta":_nan(oil_acc*0.3 + gld_acc*0.1),
        "oil_1m": oil1,
        "dxy_inv_1m": _nan(-uup1),
        "tlt_1m": tlt1,
        "dxy_3m": _nan(uup3),
        "policy_score": 0.0,
        "liquidity_score":0.0,

        "q3_credit_stress": _nan(credit_stress_12),
        "q3_quality_bid": _nan(quality_bid_12),
        "q3_consumer_stress": _nan(consumer_stress_12),
        "q3_breadth_stress": _nan(breadth_stress_12),
        "q3_modifier": q3_modifier,
    }

# ── FRED feature extraction ───────────────────────────────────────────────────

def _extract_fred_features(fred: Dict) -> Dict[str, float]:
    """Extract features from FRED."""
    f: Dict[str, float] = {}

    f["indpro_yoy"] = _yoy(fred.get("INDPRO"))
    f["retail_yoy"] = _yoy(fred.get("RSAFS"))
    f["payrolls_yoy"] = _yoy(fred.get("PAYEMS"))
    ism_s = _fv(fred.get("ISMNO"), fred.get("MANEMP"))
    ism = _last(ism_s)
    f["ism_norm"] = (ism - ISM_NEUTRAL) / ISM_NEUTRAL if math.isfinite(ism) else float("nan")
    f["housing_yoy"] = _yoy(fred.get("HOUST"))
    unrate_3m = _delta(fred.get("UNRATE"), 3)
    claims_d = _delta(fred.get("ICSA"), 13)
    f["unrate_inv"] = -float(np.tanh(unrate_3m / 0.2)) if math.isfinite(unrate_3m) else float("nan")
    f["claims_inv"] = -float(np.tanh(claims_d / 50000)) if math.isfinite(claims_d) else float("nan")

    f["indpro_roc"] = _roc(fred.get("INDPRO"), 12, 3)
    f["retail_roc"] = _roc(fred.get("RSAFS"), 12, 3)
    f["payrolls_roc"] = _roc(fred.get("PAYEMS"), 12, 3)
    f["ism_delta"] = _delta(ism_s, 3) / ISM_NEUTRAL if ism_s is not None else float("nan")
    f["unrate_delta"] = -unrate_3m / 0.2 if math.isfinite(unrate_3m) else float("nan")
    f["claims_delta"] = -claims_d / 50000 if math.isfinite(claims_d) else float("nan")

    f["cpi_yoy"] = _yoy(fred.get("CPIAUCSL"))
    f["core_cpi_yoy"] = _yoy(fred.get("CPILFESL"))
    f["ppi_yoy"] = _yoy(fred.get("PPIACO"))
    be5 = _last(fred.get("T5YIE"))
    f["breakeven_5y"] = (be5 - 2.2) / 2.0 if math.isfinite(be5) else float("nan")

    f["cpi_roc"] = _roc(fred.get("CPIAUCSL"), 12, 3)
    f["core_cpi_roc"] = _roc(fred.get("CPILFESL"), 12, 3)
    be5_d = _delta(fred.get("T5YIE"), 1)
    f["breakeven_delta"] = _nan(be5_d / 0.3) if math.isfinite(be5_d) else float("nan")

    ff_s = _fv(fred.get("FEDFUNDS"), fred.get("DFF"))
    ff_delta = _delta(ff_s, 3)
    f["policy_score"] = float(np.tanh(-_nan(ff_delta) / 0.5))
    m2_roc = _roc(fred.get("M2SL"), 12, 3)
    f["liquidity_score"] = float(np.tanh(_nan(m2_roc) / 0.05))

    return f

# ── GIP Output ────────────────────────────────────────────────────────────────

@dataclass
class GIPResult:
    structural_quad: str; structural_probs: Dict[str,float]; structural_conf: float
    structural_g: float; structural_i: float
    monthly_quad: str; monthly_probs: Dict[str,float]; monthly_conf: float
    monthly_g: float; monthly_i: float
    divergence: str; operating_regime: str
    policy_score: float; data_coverage: float; proxy_share: float
    features: Dict[str,float] = field(default_factory=dict)

    @property
    def flip_hazard(self) -> float:
        margin = self.structural_probs.get(self.structural_quad, 0.5) -                  sorted(self.structural_probs.values(), reverse=True)[1]
        return float(np.clip(0.5 - 0.8*margin + 0.2*(1.0-self.data_coverage), 0.0, 1.0))

def _quad_name(q): return {"Q1":"Goldilocks","Q2":"Reflation","Q3":"Stagflation","Q4":"Deflation"}.get(q,q)

def _score_quad(g_level, g_mom, i_level, i_mom, policy, sw, pw, modifiers=None):
    modifiers = modifiers or {}
    g = sw["growth_level"]*g_level + sw["growth_momentum"]*g_mom
    i = sw["inflation_level"]*i_level + sw["inflation_momentum"]*i_mom
    p = pw * policy
    raw = {
        "Q1": +g - i + p*0.60,
        "Q2": +g + i - p*0.30,
        "Q3": -g + i - p*0.80,
        "Q4": -g - i + p*1.00,
    }
    for q, delta in modifiers.items():
        if q in raw: raw[q] += delta
    probs = _softmax(raw)
    top = max(probs, key=probs.get)
    margin= probs[top] - sorted(probs.values(), reverse=True)[1]
    conf = float(np.clip(probs[top]*(0.65+0.35*margin/0.5), 0.0, 1.0))
    return probs, top, conf

# ── Main Engine ───────────────────────────────────────────────────────────────

class GIPEngine:
    def run(self, fred: Dict, prices: Dict) -> GIPResult:
        f_fred = _extract_fred_features(fred)
        f_proxy = _price_proxy(prices)

        fred_keys = ["indpro_yoy","retail_yoy","payrolls_yoy","cpi_yoy","core_cpi_yoy",
                     "ism_norm","housing_yoy","unrate_inv","claims_inv"]
        n_fred = sum(1 for k in fred_keys if math.isfinite(f_fred.get(k, float("nan"))))
        proxy_share = 1.0 - n_fred / len(fred_keys)

        def merge(key):
            v = f_fred.get(key, float("nan"))
            return v if math.isfinite(v) else f_proxy.get(key, float("nan"))

        g_lvl = {
            "indpro_yoy": _tanh_scale(merge("indpro_yoy") - 0.02, 0.05),
            "retail_yoy": _tanh_scale(merge("retail_yoy") - 0.03, 0.06),
            "payrolls_yoy": _tanh_scale(merge("payrolls_yoy") - 0.015, 0.03),
            "housing_yoy": _tanh_scale(merge("housing_yoy"), 0.10),
            "ism_norm": _tanh_scale(merge("ism_norm"), 0.10),
            "unrate_inv": merge("unrate_inv"),
            "claims_inv": merge("claims_inv"),
        }
        g_mom = {
            "indpro_roc": _tanh_scale(merge("indpro_roc"), 0.025),
            "retail_roc": _tanh_scale(merge("retail_roc"), 0.030),
            "payrolls_roc": _tanh_scale(merge("payrolls_roc"), 0.015),
            "ism_delta": _tanh_scale(merge("ism_delta"), 0.05),
            "unrate_delta": _tanh_scale(merge("unrate_delta"), 1.0),
            "claims_delta": _tanh_scale(merge("claims_delta"), 1.0),
        }
        i_lvl = {
            "cpi_yoy": _tanh_scale(merge("cpi_yoy") - 0.025, 0.020),
            "core_cpi_yoy": _tanh_scale(merge("core_cpi_yoy")- 0.025, 0.015),
            "breakeven_5y": merge("breakeven_5y"),
            "ppi_yoy": _tanh_scale(merge("ppi_yoy") - 0.025, 0.030),
            "oil_3m": _tanh_scale(merge("oil_3m"), 0.25),
            "gold_3m": _tanh_scale(merge("gold_3m"), 0.18),
        }
        i_mom = {
            "cpi_roc": _tanh_scale(merge("cpi_roc"), 0.012),
            "core_cpi_roc": _tanh_scale(merge("core_cpi_roc"), 0.010),
            "breakeven_delta": _tanh_scale(merge("breakeven_delta"), 1.0),
            "oil_1m": _tanh_scale(merge("oil_1m"), 0.06),
            "dxy_inv_1m": _tanh_scale(merge("dxy_inv_1m"), 0.06),
        }

        g_level = _wmean(g_lvl, GROWTH_LEVEL_WEIGHTS)
        g_mom_ = _wmean(g_mom, GROWTH_MOM_WEIGHTS)
        i_level = _wmean(i_lvl, INFLATION_LEVEL_WEIGHTS)
        i_mom_ = _wmean(i_mom, INFLATION_MOM_WEIGHTS)
        policy = _nan(merge("policy_score"))
        coverage= _coverage({**g_lvl, **g_mom, **i_lvl, **i_mom})

        q3_mod = float(_nan(merge("q3_modifier")))
        struct_modifiers = {}
        if q3_mod > 0.05:
            scale = 0.8 + 0.2 * proxy_share
            struct_modifiers = {"Q3": q3_mod * scale, "Q2": -q3_mod * scale * 0.4}
        struct_probs, struct_quad, struct_conf = _score_quad(
            g_level, g_mom_, i_level, i_mom_, policy,
            STRUCTURAL_WEIGHTS, POLICY_WEIGHT_STRUCTURAL,
            modifiers=struct_modifiers)

        oil1 = _ret(prices.get("CL=F"), 21)
        oil1 = oil1 if (oil1 is not None and math.isfinite(oil1)) else merge("oil_1m")
        gld1 = _first_finite(_ret(prices.get("GLD"), 21))
        spy1 = _first_finite(_ret(prices.get("SPY"), 21))
        xli1 = _first_finite(_ret(prices.get("XLI"), 21))
        be_d = merge("breakeven_delta")

        m_g_level = 0.40*g_level + 0.60*g_mom_
        m_g_mom = 0.30*g_mom_ + 0.70*float(np.tanh(0.40*_nan(xli1)/0.05 + 0.60*_nan(spy1)/0.05))
        cpi_yoy = merge("cpi_yoy"); core_yoy = merge("core_cpi_yoy")
        hgap = cpi_yoy - core_yoy if (math.isfinite(cpi_yoy) and math.isfinite(core_yoy)) else 0.0
        m_i_level = 0.45*i_level + 0.35*i_mom_ + 0.20*_tanh_scale(hgap, 0.004)
        m_i_mom = 0.30*i_mom_ + 0.70*float(np.tanh(0.50*_nan(oil1)/0.06 + 0.30*gld1/0.05 + 0.20*_nan(be_d if math.isfinite(be_d) else 0.0)/1.0))
        shock = max(0.0, _tanh_scale(hgap, 0.004))

        month_probs, month_quad, month_conf = _score_quad(
            m_g_level, m_g_mom, m_i_level, m_i_mom, policy,
            MONTHLY_WEIGHTS, POLICY_WEIGHT_MONTHLY,
            modifiers={"Q3": 0.05*shock, "Q2": -0.03*shock})

        div = "aligned" if struct_quad == month_quad else "divergent"
        regime = f"Aligned {struct_quad}" if div == "aligned" else f"Monthly {month_quad} inside Structural {struct_quad}"

        _tlt = prices.get("TLT"); _ief = prices.get("IEF")
        tlt_1m = float(pd.to_numeric(_tlt, errors="coerce").pct_change(21).dropna().iloc[-1]) if _tlt is not None and len(_tlt)>22 else 0.0
        ief_1m = float(pd.to_numeric(_ief, errors="coerce").pct_change(21).dropna().iloc[-1]) if _ief is not None and len(_ief)>22 else 0.0
        bond_pivot_signal = clamp01(0.5 + tlt_1m*8 + ief_1m*4)

        features = dict(
            growth_level=g_level, growth_momentum=g_mom_,
            inflation_level=i_level, inflation_momentum=i_mom_,
            policy_score=policy, data_coverage=coverage, proxy_share=proxy_share,
            q3_modifier=q3_mod, q3_credit_stress=_nan(merge("q3_credit_stress")),
            q3_consumer_stress=_nan(merge("q3_consumer_stress")),
            monthly_g_level=m_g_level, monthly_g_mom=m_g_mom,
            monthly_i_level=m_i_level, monthly_i_mom=m_i_mom,
            headline_gap=hgap, inflation_shock=shock,
            leading_indicator_composite=_nan(0.40*g_mom_+0.30*(-i_mom_)+0.30*policy),
            bond_pivot_signal=bond_pivot_signal, tlt_1m_trend=tlt_1m, ief_1m_trend=ief_1m,
            **{f"raw_{k}": v for k, v in f_fred.items() if math.isfinite(v)},
        )

        return GIPResult(
            structural_quad=struct_quad, structural_probs=struct_probs,
            structural_conf=struct_conf, structural_g=g_level+g_mom_,
            structural_i=i_level+i_mom_,
            monthly_quad=month_quad, monthly_probs=month_probs,
            monthly_conf=month_conf, monthly_g=m_g_level+m_g_mom,
            monthly_i=m_i_level+m_i_mom,
            divergence=div, operating_regime=regime,
            policy_score=policy, data_coverage=coverage,
            proxy_share=proxy_share, features=features,
        )

def get_playbook(sq, mq):
    s = QUAD_ASSET_PERFORMANCE.get(sq, {})
    m = QUAD_ASSET_PERFORMANCE.get(mq, {})
    return dict(
        structural=sq, monthly=mq,
        best_assets=list(dict.fromkeys(s.get("best",[])+m.get("best",[])[:2]))[:6],
        worst_assets=s.get("worst",[]),
        sectors_ow=s.get("sectors_overweight",[]),
        sectors_uw=s.get("sectors_underweight",[]),
        style=s.get("style",""), fx=s.get("fx",""), bonds=s.get("bonds",""),
        monthly_adds=m.get("best",[])[:3], note=s.get("note",""),
    )
