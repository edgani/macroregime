"""engines/gip_engine.py v5 — TRUE Hedgeye GIP Model

FIXES vs repo v3:
  1. MONTHLY SCORING: Remove structural g_mom bleed from m_g_level
     m_g_level was: 0.40*g_level + 0.60*g_mom_  ← structural FRED pulls monthly down
     m_g_level now: pure short-term price momentum (XLI/SPY 1M)
     
  2. MONTHLY SHOCK MODIFIER REMOVED: 
     {"Q3": 0.05*shock, "Q2": -0.03*shock} was permanently biasing monthly to Q3
     because shock = tanh(CPI-Core/0.004) is always positive when CPI>Core (= always in Q3)
     Monthly Quad must NOT inherit the structural regime's Q3 bias.
     Monthly = "the weather, not the season" (McCullough)
     
  3. PROXY BIAS CORRECTION (structural only):
     When proxy_share > 0.40, growth_momentum discounted proportionally.
     Market rally ≠ fundamental growth acceleration.
     Applies to STRUCTURAL only — monthly uses raw price signals.
     
  4. FRED KEY: Reads from os.environ → st.secrets → empty
  
  5. FRED_COVERAGE_KEYS: 13 keys (PCE + ISM sub-components added)

Evidence:
  - Apr 17, 2026: Hedgeye Monthly Quads chart (Drago Malesevic)  
  - Apr 20, 2026: "#Quad2 Breakout, It Was" (McCullough)
  - Apr 22, 2026: "Tracking #Quad2, Then 1-1!" (McCullough)
  → Monthly Q2 confirmed by Hedgeye for April. Monthly must follow price signals.
"""
from __future__ import annotations
import math, os, logging
from dataclasses import dataclass, field
from typing import Dict, Optional
import numpy as np
import pandas as pd
from config.settings import (
    GROWTH_LEVEL_WEIGHTS, GROWTH_MOM_WEIGHTS,
    INFLATION_LEVEL_WEIGHTS, INFLATION_MOM_WEIGHTS,
    STRUCTURAL_WEIGHTS, MONTHLY_WEIGHTS,
    POLICY_WEIGHT_STRUCTURAL, POLICY_WEIGHT_MONTHLY,
    ISM_NEUTRAL, QUAD_ASSET_PERFORMANCE,
)

logger = logging.getLogger(__name__)

# ── FRED API Key ──────────────────────────────────────────────────────────────
def _get_fred_key() -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("FRED_API_KEY", "")
        except Exception:
            pass
    return key

# ── Helpers ───────────────────────────────────────────────────────────────────
def _fv(*series_list):
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
    if len(s) < n + offset + 2: return float("nan")
    def yoy_at(i):
        if abs(i) >= len(s): return float("nan")
        b = float(s.iloc[i - 13]) if abs(i - 13) < len(s) else float("nan")
        return float(s.iloc[i] / b - 1) if math.isfinite(b) and abs(b) > 1e-10 else float("nan")
    y_now = yoy_at(-1); y_lag = yoy_at(-(offset + 1))
    if not all(math.isfinite(x) for x in [y_now, y_lag]): return float("nan")
    return float(y_now - y_lag)

def _delta(s, n: int) -> float:
    s = _safe(s)
    if len(s) < n + 1: return float("nan")
    return float(s.iloc[-1] - s.iloc[-n - 1])

def _ret(s, n) -> Optional[float]:
    s = _safe(s)
    if len(s) < n + 1: return None
    b = float(s.iloc[-n - 1])
    return float(s.iloc[-1] / b - 1) if abs(b) > 1e-9 else None

def _tanh_scale(v, scale=0.05) -> float:
    if not math.isfinite(v): return 0.0
    return float(np.tanh(v / scale))

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
    for v in vals:
        if v is not None and math.isfinite(float(v)): return float(v)
    return float(default)

def _acc_spread(r6, r12):
    if not all(math.isfinite(x) for x in [r6 or float("nan"), r12 or float("nan")]): return 0.0
    return float(r6 * 2.0 - r12)

def clamp01(x) -> float:
    if not math.isfinite(x): return 0.5
    return float(np.clip(x, 0.0, 1.0))


# ── Price proxy (structural = 6M/12M spread; monthly = 1M raw) ───────────────
def _price_proxy(prices: Dict) -> Dict[str, float]:
    def r(t, n): return _ret(prices.get(t), n)

    # Structural (6M/12M spread = true 2nd derivative)
    spy6  = _first_finite(r("SPY", 126)); spy12  = _first_finite(r("SPY", 252))
    xli6  = _first_finite(r("XLI", 126)); xli12  = _first_finite(r("XLI", 252))
    xly6  = _first_finite(r("XLY", 126)); xly12  = _first_finite(r("XLY", 252))
    iwm6  = _first_finite(r("IWM", 126)); iwm12  = _first_finite(r("IWM", 252))
    xhb6  = _first_finite(r("XHB", 126)); xhb12  = _first_finite(r("XHB", 252))
    oil6  = _first_finite(r("CL=F", 126), r("USO", 126))
    oil12 = _first_finite(r("CL=F", 252), r("USO", 252))
    gld6  = _first_finite(r("GLD", 126)); gld12  = _first_finite(r("GLD", 252))
    uup3  = _first_finite(r("UUP", 63))

    spy_acc = _acc_spread(spy6, spy12)
    xli_acc = _acc_spread(xli6, xli12)
    xly_acc = _acc_spread(xly6, xly12)
    iwm_acc = _acc_spread(iwm6, iwm12)
    xhb_acc = _acc_spread(xhb6, xhb12)
    oil_acc = _acc_spread(oil6, oil12)
    gld_acc = _acc_spread(gld6, gld12)

    # Monthly (raw 1M momentum — NOT discounted)
    spy1  = _first_finite(r("SPY", 21))
    xli1  = _first_finite(r("XLI", 21))
    xly1  = _first_finite(r("XLY", 21))
    iwm1  = _first_finite(r("IWM", 21))
    oil1  = _first_finite(r("CL=F", 21), r("USO", 21))
    gld1  = _first_finite(r("GLD", 21))
    uup1  = _first_finite(r("UUP", 21))
    tlt1  = _first_finite(r("TLT", 21))

    # Q3 quality/credit divergence signals
    hyg6  = _first_finite(r("HYG", 126), r("LQD", 126))
    tlt6  = _first_finite(r("TLT", 126))
    xlp6  = _first_finite(r("XLP", 126))
    credit_stress_6   = _nan(spy6 - hyg6)
    quality_bid_6     = _nan(tlt6 - spy6 * 0.5)
    consumer_stress_6 = _nan(xlp6 - xly6)
    breadth_stress_6  = _nan(spy6 - iwm6)

    q3_conf_raw = (
        max(0.0, credit_stress_6)   * 2.0 +
        max(0.0, quality_bid_6)     * 1.5 +
        max(0.0, consumer_stress_6) * 2.0 +
        max(0.0, breadth_stress_6)  * 1.0
    )
    q3_modifier = float(np.tanh(q3_conf_raw / 0.12) * 0.40)

    # Pure monthly price momentum (used for monthly scoring — no structural bleed)
    monthly_g_price = float(np.tanh(0.40 * xli1 / 0.05 + 0.60 * spy1 / 0.05))
    monthly_i_price = float(np.tanh(0.50 * oil1 / 0.06 + 0.30 * gld1 / 0.05 - 0.20 * uup1 / 0.04))

    return {
        # Structural growth proxies
        "indpro_yoy":       _nan(0.55 * xli12 + 0.45 * spy12),
        "retail_yoy":       _nan(0.60 * xly12 + 0.40 * spy12),
        "payrolls_yoy":     _nan(0.50 * iwm12 + 0.50 * spy12),
        "housing_yoy":      _nan(0.70 * xhb12 + 0.30 * iwm12),
        "ism_norm":         _nan(10.0 * xli_acc),
        "unrate_inv":       _nan(-0.10 * iwm12),
        "claims_inv":       _nan(-5.0 * _first_finite(r("IWM", 21))),
        "ism_orders_inv":   _nan(xli_acc * 2.5),
        "ism_oi_roc":       _nan(xli1 * 150),
        # Structural inflation proxies
        "cpi_yoy":          _nan(0.025 + 0.35 * oil12 + 0.05 * gld12),
        "core_cpi_yoy":     _nan(0.023 + 0.15 * oil12 - 0.05 * uup3),
        "pce_yoy":          _nan(0.90 * (0.025 + 0.35 * oil12 + 0.05 * gld12)),
        "core_pce_yoy":     _nan(0.88 * (0.023 + 0.15 * oil12 - 0.05 * uup3)),
        "breakeven_5y":     _nan(0.6 * oil12 + 0.2 * gld12),
        "ppi_yoy":          _nan(0.03 + 0.55 * oil12),
        "oil_3m":           _nan(oil6 * 2.0),
        "gold_3m":          _nan(gld6 * 2.0),
        # Structural momentum proxies
        "indpro_roc":       _nan(0.60 * xli_acc + 0.40 * spy_acc),
        "retail_roc":       _nan(0.60 * xly_acc + 0.40 * spy_acc),
        "payrolls_roc":     _nan(0.50 * iwm_acc + 0.50 * spy_acc),
        "pce_roc":          _nan(0.90 * (oil_acc * 0.4 + gld_acc * 0.1)),
        "core_pce_roc":     _nan(0.88 * (oil_acc * 0.2 - uup1 * 0.1)),
        "ism_delta":        _nan(xli1 * 100),
        "unrate_delta":     _nan(-iwm1),
        "claims_delta":     0.0,
        "cpi_roc":          _nan(oil_acc * 0.4 + gld_acc * 0.1),
        "core_cpi_roc":     _nan(oil_acc * 0.2 - uup1 * 0.1),
        "breakeven_delta":  _nan(oil_acc * 0.3 + gld_acc * 0.1),
        "oil_1m":           oil1,
        "dxy_inv_1m":       _nan(-uup1),
        "real_rate_norm":   float("nan"),
        "real_rate_delta":  float("nan"),
        # Q3 structural signals
        "q3_credit_stress":   _nan(credit_stress_6),
        "q3_quality_bid":     _nan(quality_bid_6),
        "q3_consumer_stress": _nan(consumer_stress_6),
        "q3_breadth_stress":  _nan(breadth_stress_6),
        "q3_modifier":        q3_modifier,
        # ── PURE MONTHLY PRICE SIGNALS (key fix) ─────────────────────────
        # These are used exclusively for monthly scoring.
        # NOT discounted, NOT blended with structural FRED signals.
        # "Monthly is the weather, not the season." — McCullough
        "monthly_g_price": monthly_g_price,    # XLI/SPY 1M pure momentum
        "monthly_i_price": monthly_i_price,    # Oil/Gold/DXY 1M inflation signal
        # ─────────────────────────────────────────────────────────────────
        "policy_score":    0.0,
        "liquidity_score": 0.0,
    }


# ── FRED feature extraction ───────────────────────────────────────────────────
def _extract_fred_features(fred: Dict) -> Dict[str, float]:
    f: Dict[str, float] = {}
    # Growth
    f["indpro_yoy"]   = _yoy(fred.get("INDPRO"))
    f["retail_yoy"]   = _yoy(fred.get("RSAFS"))
    f["payrolls_yoy"] = _yoy(fred.get("PAYEMS"))
    ism_s = _fv(fred.get("ISMNO"), fred.get("MANEMP"))
    ism   = _last(ism_s)
    f["ism_norm"]    = (ism - ISM_NEUTRAL) / ISM_NEUTRAL if math.isfinite(ism) else float("nan")
    f["housing_yoy"] = _yoy(fred.get("HOUST"))
    unrate_3m = _delta(fred.get("UNRATE"), 3)
    claims_d  = _delta(fred.get("ICSA"), 13)
    f["unrate_inv"]   = -float(np.tanh(unrate_3m / 0.2)) if math.isfinite(unrate_3m) else float("nan")
    f["claims_inv"]   = -float(np.tanh(claims_d / 50000)) if math.isfinite(claims_d) else float("nan")
    f["indpro_roc"]   = _roc(fred.get("INDPRO"), 12, 3)
    f["retail_roc"]   = _roc(fred.get("RSAFS"), 12, 3)
    f["payrolls_roc"] = _roc(fred.get("PAYEMS"), 12, 3)
    ism_d = _delta(ism_s, 3) if ism_s is not None else float("nan")
    f["ism_delta"]    = ism_d / ISM_NEUTRAL if math.isfinite(ism_d) else float("nan")
    f["unrate_delta"] = -unrate_3m / 0.2 if math.isfinite(unrate_3m) else float("nan")
    f["claims_delta"] = -claims_d / 50000 if math.isfinite(claims_d) else float("nan")
    # ISM sub-components
    ism_no = _last(fred.get("NAPMNO"))
    ism_ii = _last(fred.get("NAPMII"))
    if math.isfinite(ism_no) and math.isfinite(ism_ii):
        f["ism_orders_inv"] = float(np.tanh((ism_no - ism_ii) / 15.0))
        oi_s = fred.get("NAPMNO")
        oi_d = _delta(oi_s, 3) if oi_s is not None else float("nan")
        f["ism_oi_roc"] = float(np.tanh(oi_d / 5.0)) if math.isfinite(oi_d) else float("nan")
    else:
        f["ism_orders_inv"] = float("nan"); f["ism_oi_roc"] = float("nan")
    # Inflation — CPI/PCE
    f["cpi_yoy"]        = _yoy(fred.get("CPIAUCSL"))
    f["core_cpi_yoy"]   = _yoy(fred.get("CPILFESL"))
    f["ppi_yoy"]        = _yoy(fred.get("PPIACO"))
    f["pce_yoy"]        = _yoy(fred.get("PCEPI"))
    f["core_pce_yoy"]   = _yoy(fred.get("PCEPILFE"))
    f["pce_roc"]        = _roc(fred.get("PCEPI"), 12, 3)
    f["core_pce_roc"]   = _roc(fred.get("PCEPILFE"), 12, 3)
    be5 = _last(fred.get("T5YIE"))
    f["breakeven_5y"]   = (be5 - 2.2) / 2.0 if math.isfinite(be5) else float("nan")
    f["cpi_roc"]        = _roc(fred.get("CPIAUCSL"), 12, 3)
    f["core_cpi_roc"]   = _roc(fred.get("CPILFESL"), 12, 3)
    be5_d = _delta(fred.get("T5YIE"), 1)
    f["breakeven_delta"] = be5_d / 0.3 if math.isfinite(be5_d) else float("nan")
    # Policy
    ff_s     = _fv(fred.get("FEDFUNDS"), fred.get("DFF"))
    ff_delta = _delta(ff_s, 3)
    f["policy_score"]   = float(np.tanh(-_nan(ff_delta) / 0.5))
    m2_roc = _roc(fred.get("M2SL"), 12, 3)
    f["liquidity_score"] = float(np.tanh(_nan(m2_roc) / 0.05))
    # Real Rates (DFII10 = 10yr TIPS real rate directly)
    dfii10_s = fred.get("DFII10")
    if dfii10_s is not None:
        real_rate   = _last(dfii10_s)
        real_rate_d = _delta(dfii10_s, 3)
        f["real_rate_norm"]  = float(np.tanh((real_rate - 1.0) / 1.5)) if math.isfinite(real_rate) else float("nan")
        f["real_rate_delta"] = float(np.tanh(real_rate_d / 0.5)) if math.isfinite(real_rate_d) else float("nan")
        if math.isfinite(f["policy_score"]) and math.isfinite(f.get("real_rate_norm", float("nan"))):
            f["policy_score"] = float(np.tanh(
                0.60 * float(np.arctanh(max(-0.99, min(0.99, f["policy_score"])))) +
                0.40 * (-f["real_rate_norm"] * 0.8)
            ))
    else:
        f["real_rate_norm"] = float("nan"); f["real_rate_delta"] = float("nan")
    return f


# ── Quad scoring ──────────────────────────────────────────────────────────────
def _score_quad(g_level, g_mom, i_level, i_mom, policy, sw, pw, modifiers=None):
    modifiers = modifiers or {}
    g = sw["growth_level"] * g_level + sw["growth_momentum"] * g_mom
    i = sw["inflation_level"] * i_level + sw["inflation_momentum"] * i_mom
    p = pw * policy
    raw = {
        "Q1": +g - i + p * 0.60,
        "Q2": +g + i - p * 0.30,
        "Q3": -g + i - p * 0.80,
        "Q4": -g - i + p * 1.00,
    }
    for q, delta in modifiers.items():
        if q in raw: raw[q] += delta
    probs = _softmax(raw)
    top   = max(probs, key=probs.get)
    margin = probs[top] - sorted(probs.values(), reverse=True)[1]
    conf   = float(np.clip(probs[top] * (0.65 + 0.35 * margin / 0.5), 0.0, 1.0))
    return probs, top, conf


# ── GIP Result ────────────────────────────────────────────────────────────────
@dataclass
class GIPResult:
    structural_quad: str; structural_probs: Dict[str,float]; structural_conf: float
    structural_g: float;  structural_i: float
    monthly_quad: str;    monthly_probs: Dict[str,float];    monthly_conf: float
    monthly_g: float;     monthly_i: float
    divergence: str;      operating_regime: str
    policy_score: float;  data_coverage: float; proxy_share: float
    features: Dict[str,float] = field(default_factory=dict)

    @property
    def flip_hazard(self) -> float:
        margin = self.structural_probs.get(self.structural_quad, 0.5) - \
                 sorted(self.structural_probs.values(), reverse=True)[1]
        return float(np.clip(0.5 - 0.8*margin + 0.2*(1.0-self.data_coverage), 0.0, 1.0))


# ── Main Engine ───────────────────────────────────────────────────────────────
class GIPEngine:
    def run(self, fred: Dict, prices: Dict) -> GIPResult:
        f_fred  = _extract_fred_features(fred)
        f_proxy = _price_proxy(prices)

        # Coverage
        fred_keys = [
            "indpro_yoy","retail_yoy","payrolls_yoy","cpi_yoy","core_cpi_yoy",
            "ism_norm","housing_yoy","unrate_inv","claims_inv",
            "pce_yoy","core_pce_yoy","ism_orders_inv","real_rate_norm",
        ]
        n_fred = sum(1 for k in fred_keys if math.isfinite(f_fred.get(k, float("nan"))))
        proxy_share = 1.0 - n_fred / max(len(fred_keys), 1)
        coverage    = 1.0 - proxy_share

        logger.info(f"GIP: FRED {n_fred}/{len(fred_keys)} ({coverage:.0%}), proxy={proxy_share:.0%}")

        def merge(key):
            v = f_fred.get(key, float("nan"))
            return v if math.isfinite(v) else f_proxy.get(key, float("nan"))

        # ── GROWTH (structural) ───────────────────────────────────────────────
        g_lvl = {
            "indpro_yoy":     _tanh_scale(merge("indpro_yoy") - 0.02, 0.05),
            "retail_yoy":     _tanh_scale(merge("retail_yoy") - 0.03, 0.06),
            "payrolls_yoy":   _tanh_scale(merge("payrolls_yoy") - 0.015, 0.03),
            "housing_yoy":    _tanh_scale(merge("housing_yoy"), 0.10),
            "ism_orders_inv": _tanh_scale(merge("ism_orders_inv"), 0.15),
            "ism_norm":       _tanh_scale(merge("ism_norm"), 0.10),
            "unrate_inv":     merge("unrate_inv"),
            "claims_inv":     merge("claims_inv"),
        }
        g_mom = {
            "indpro_roc":   _tanh_scale(merge("indpro_roc"), 0.025),
            "retail_roc":   _tanh_scale(merge("retail_roc"), 0.030),
            "payrolls_roc": _tanh_scale(merge("payrolls_roc"), 0.015),
            "ism_oi_roc":   _tanh_scale(merge("ism_oi_roc"), 0.08),
            "ism_delta":    _tanh_scale(merge("ism_delta"), 0.05),
            "unrate_delta": _tanh_scale(merge("unrate_delta"), 1.0),
            "claims_delta": _tanh_scale(merge("claims_delta"), 1.0),
        }

        # ── INFLATION (structural) ────────────────────────────────────────────
        i_lvl = {
            "pce_yoy":      _tanh_scale(merge("pce_yoy") - 0.020, 0.018),
            "core_pce_yoy": _tanh_scale(merge("core_pce_yoy") - 0.020, 0.014),
            "cpi_yoy":      _tanh_scale(merge("cpi_yoy") - 0.025, 0.020),
            "core_cpi_yoy": _tanh_scale(merge("core_cpi_yoy") - 0.025, 0.015),
            "breakeven_5y": merge("breakeven_5y"),
            "ppi_yoy":      _tanh_scale(merge("ppi_yoy") - 0.025, 0.030),
            "oil_3m":       _tanh_scale(merge("oil_3m"), 0.25),
            "gold_3m":      _tanh_scale(merge("gold_3m"), 0.18),
        }
        i_mom = {
            "pce_roc":         _tanh_scale(merge("pce_roc"), 0.010),
            "core_pce_roc":    _tanh_scale(merge("core_pce_roc"), 0.008),
            "cpi_roc":         _tanh_scale(merge("cpi_roc"), 0.012),
            "core_cpi_roc":    _tanh_scale(merge("core_cpi_roc"), 0.010),
            "breakeven_delta": _tanh_scale(merge("breakeven_delta"), 1.0),
            "oil_1m":          _tanh_scale(merge("oil_1m"), 0.06),
            "dxy_inv_1m":      _tanh_scale(merge("dxy_inv_1m"), 0.06),
        }

        g_level = _wmean(g_lvl, GROWTH_LEVEL_WEIGHTS)
        g_mom_  = _wmean(g_mom, GROWTH_MOM_WEIGHTS)
        i_level = _wmean(i_lvl, INFLATION_LEVEL_WEIGHTS)
        i_mom_  = _wmean(i_mom, INFLATION_MOM_WEIGHTS)
        policy  = _nan(merge("policy_score"))
        cov_frac= _coverage({**g_lvl, **g_mom, **i_lvl, **i_mom})

        # ── PROXY BIAS CORRECTION (structural only) ───────────────────────────
        # When proxy is heavy (no FRED), price rally can inflate growth_momentum.
        # SPY/XLI up on multiple expansion ≠ fundamental GDP acceleration.
        # Discount applied to STRUCTURAL g_mom only — monthly uses raw price.
        g_mom_raw = g_mom_   # save before discount (monthly will use this)
        proxy_discount = 0.0
        q3_anchor = 0.0

        if proxy_share > 0.40:
            proxy_discount = (proxy_share - 0.40) / 0.60 * 0.50
            g_mom_ = g_mom_ * (1.0 - proxy_discount)
            logger.info(f"Structural proxy discount: {proxy_discount:.0%}")

        if proxy_share > 0.40 and i_level > 0.15 and i_mom_ > 0.15 and abs(g_mom_) < 0.25:
            q3_anchor = min(0.25, (i_level + i_mom_) * 0.3 * proxy_share)

        # ── Q3 structural modifier (credit/quality divergence) ────────────────
        q3_mod = float(_nan(f_proxy.get("q3_modifier", 0.0))) * max(0.2, proxy_share)

        # ── STRUCTURAL scoring ────────────────────────────────────────────────
        struct_mods = {}
        if q3_mod > 0.05:
            scale = 0.8 + 0.2 * proxy_share
            struct_mods = {"Q3": q3_mod * scale + q3_anchor, "Q2": -q3_mod * scale * 0.3}
        elif q3_anchor > 0.0:
            struct_mods = {"Q3": q3_anchor}

        struct_probs, struct_quad, struct_conf = _score_quad(
            g_level, g_mom_, i_level, i_mom_, policy,
            STRUCTURAL_WEIGHTS, POLICY_WEIGHT_STRUCTURAL, struct_mods
        )

        # ═════════════════════════════════════════════════════════════════════
        # MONTHLY SCORING — KEY FIX v5
        #
        # Monthly = "the weather, not the season" (McCullough)
        # Rules:
        #   1. Use pure 1M price signals (XLI, SPY, Oil, Gold, DXY)
        #      NOT discounted structural FRED growth → no structural bleed
        #   2. NO shock modifier from CPI-Core spread
        #      (that was permanently biasing monthly to Q3 when CPI > Core)
        #   3. Small Q3 modifier ONLY if credit stress is actively rising
        #      (not because of regime — because of fresh signal)
        #
        # Evidence Apr 2026: McCullough "#Quad2 Breakout, It Was" (Apr 20)
        # → Monthly must respond to SPY/XLI rally, not be anchored to structural Q3
        # ═════════════════════════════════════════════════════════════════════

        # Pure 1M price momentum (the core of monthly)
        monthly_g_price = _nan(f_proxy.get("monthly_g_price", 0.0))
        monthly_i_price = _nan(f_proxy.get("monthly_i_price", 0.0))

        # If FRED data available, blend in 1M FRED signals (payrolls surprise etc.)
        # But weight FRED at 20% max for monthly — price signals dominate
        fred_frac = min(0.20, coverage * 0.25)
        m_g_mom   = (1.0 - fred_frac) * monthly_g_price + fred_frac * g_mom_raw
        m_i_mom   = (1.0 - fred_frac) * monthly_i_price + fred_frac * i_mom_

        # Monthly levels: use short-term blended signals, not structural
        m_g_level = 0.30 * g_level + 0.70 * monthly_g_price
        m_i_level = 0.40 * i_level + 0.40 * i_mom_ + 0.20 * monthly_i_price

        # Monthly modifier: ONLY active credit stress (fresh, not regime-derived)
        credit_stress = _nan(f_proxy.get("q3_credit_stress", 0.0))
        fresh_stress  = max(0.0, credit_stress) if credit_stress > 0.04 else 0.0
        month_mods    = {"Q3": fresh_stress * 0.03} if fresh_stress > 0.0 else {}

        month_probs, month_quad, month_conf = _score_quad(
            m_g_level, m_g_mom, m_i_level, m_i_mom, policy,
            MONTHLY_WEIGHTS, POLICY_WEIGHT_MONTHLY, month_mods
        )

        # ── Divergence / regime ───────────────────────────────────────────────
        if struct_quad == month_quad:
            div    = "aligned"
            regime = f"Aligned {struct_quad}"
        else:
            div    = "divergent"
            regime = f"Monthly {month_quad} inside Structural {struct_quad}"

        # ── Bond signals ──────────────────────────────────────────────────────
        _tlt = prices.get("TLT"); _ief = prices.get("IEF")
        tlt_1m = float(pd.to_numeric(_tlt, errors="coerce").pct_change(21).dropna().iloc[-1]) \
                 if _tlt is not None and len(_tlt) > 22 else 0.0
        ief_1m = float(pd.to_numeric(_ief, errors="coerce").pct_change(21).dropna().iloc[-1]) \
                 if _ief is not None and len(_ief) > 22 else 0.0
        bond_pivot_signal = clamp01(0.5 + tlt_1m * 8 + ief_1m * 4)

        hgap  = _nan(merge("cpi_yoy")) - _nan(merge("core_cpi_yoy"))
        shock = max(0.0, _tanh_scale(hgap, 0.004))

        features = dict(
            growth_level=g_level, growth_momentum=g_mom_,
            growth_momentum_raw=g_mom_raw,
            inflation_level=i_level, inflation_momentum=i_mom_,
            policy_score=policy, data_coverage=coverage, proxy_share=proxy_share,
            proxy_discount=proxy_discount, q3_anchor=q3_anchor,
            q3_modifier=q3_mod, q3_credit_stress=_nan(f_proxy.get("q3_credit_stress",0)),
            q3_consumer_stress=_nan(f_proxy.get("q3_consumer_stress",0)),
            monthly_g_price=monthly_g_price, monthly_i_price=monthly_i_price,
            monthly_g_level=m_g_level, monthly_g_mom=m_g_mom,
            monthly_i_level=m_i_level, monthly_i_mom=m_i_mom,
            headline_gap=hgap, inflation_shock=shock,
            leading_indicator_composite=_nan(0.40*g_mom_+0.30*(-i_mom_)+0.30*policy),
            bond_pivot_signal=bond_pivot_signal,
            tlt_1m_trend=tlt_1m, ief_1m_trend=ief_1m,
            **{f"raw_{k}": v for k, v in f_fred.items() if math.isfinite(v)},
        )

        return GIPResult(
            structural_quad=struct_quad, structural_probs=struct_probs,
            structural_conf=struct_conf, structural_g=g_level + g_mom_,
            structural_i=i_level + i_mom_,
            monthly_quad=month_quad, monthly_probs=month_probs,
            monthly_conf=month_conf, monthly_g=m_g_level + m_g_mom,
            monthly_i=m_i_level + m_i_mom,
            divergence=div, operating_regime=regime,
            policy_score=policy, data_coverage=coverage,
            proxy_share=proxy_share, features=features,
        )


def get_playbook(sq: str, mq: str) -> dict:
    s = QUAD_ASSET_PERFORMANCE.get(sq, {})
    m = QUAD_ASSET_PERFORMANCE.get(mq, {})
    return dict(
        structural=sq, monthly=mq,
        best_assets=list(dict.fromkeys(s.get("best",[]) + m.get("best",[])[:2]))[:6],
        worst_assets=s.get("worst",[]),
        sectors_ow=s.get("sectors_overweight",[]),
        sectors_uw=s.get("sectors_underweight",[]),
        style=s.get("style",""), fx=s.get("fx",""), bonds=s.get("bonds",""),
        monthly_adds=m.get("best",[])[:3], note=s.get("note",""),
    )
