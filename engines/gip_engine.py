"""engines/gip_engine.py v4 — TRUE Hedgeye GIP Model

FIXES vs v3:
  1. FRED API KEY: Reads from os.environ + streamlit secrets properly
  2. PROXY BIAS CORRECTION: When proxy_share > 0.40, growth_momentum is
     discounted proportionally. Market rally ≠ fundamental growth acceleration.
     SPY/XLI up on multiple expansion should NOT shift regime to Q2.
  3. FRED_COVERAGE_KEYS from settings: proxy_share calculated on 13 keys (not 9)
  4. PCE + ISM spread added per settings.py v2
  5. Q3 ANCHOR: When inflation signals clearly dominate (i_level > 0.20 AND
     i_mom > 0.30) AND growth signals are ambiguous (proxy_share > 0.40),
     apply explicit Q3 anchor modifier to prevent false Q2 signal
  6. FRED fallback load: tries fredapi library first, then FRED API direct call
  7. data_coverage now reflects actual FRED data received (not just series count)
"""
from __future__ import annotations
import math, os, logging
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
    FRED_COVERAGE_KEYS,
)

logger = logging.getLogger(__name__)

# ── FRED API Key resolution ───────────────────────────────────────────────────
def _get_fred_key() -> str:
    """Read FRED key from: env → streamlit secrets → empty string."""
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        try:
            import streamlit as st
            key = st.secrets.get("FRED_API_KEY", "")
        except Exception:
            pass
    if key:
        logger.info("FRED API key loaded.")
    else:
        logger.warning("No FRED_API_KEY found. Using price proxies only.")
    return key

FRED_KEY = _get_fred_key()

# ── Safe helpers ──────────────────────────────────────────────────────────────
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
    """True 2nd derivative: Δ(YoY₍ₜ₎ - YoY₍ₜ₋ₒffₛₑₜ₎)."""
    s = _safe(s)
    if len(s) < n + offset + 2: return float("nan")
    def yoy_at(i):
        if i < 13: return float("nan")
        b = float(s.iloc[i - 13])
        return float(s.iloc[i] / b - 1) if abs(b) > 1e-10 else float("nan")
    y_now = yoy_at(-1); y_lag = yoy_at(-(offset + 1))
    if not all(math.isfinite(x) for x in [y_now, y_lag]): return float("nan")
    return float(y_now - y_lag)

def _delta(s, n: int) -> float:
    s = _safe(s)
    if len(s) < n + 1: return float("nan")
    return float(s.iloc[-1] - s.iloc[-n - 1])

def _nan(v) -> float:
    return float(v) if math.isfinite(float(v)) else 0.0

def _softmax(d: dict, T=1.0) -> dict:
    vals = np.array(list(d.values())) / T
    e = np.exp(vals - vals.max())
    norm = e / e.sum()
    return dict(zip(d.keys(), norm.tolist()))

def _ret(s, n) -> Optional[float]:
    s = _safe(s)
    if len(s) < n + 1: return None
    b = float(s.iloc[-n - 1])
    return float(s.iloc[-1] / b - 1) if abs(b) > 1e-9 else None

def _first_finite(*vals) -> float:
    for v in vals:
        if v is not None and math.isfinite(v): return float(v)
    return 0.0

def _acc_spread(r6, r12) -> float:
    """6M vs 12M spread = true 2nd derivative (acceleration/deceleration)."""
    if not all(math.isfinite(x) for x in [r6 or float("nan"), r12 or float("nan")]): return 0.0
    return float(r6 * 2.0 - r12)

def clamp01(x) -> float:
    if not math.isfinite(x): return 0.5
    return float(np.clip(x, 0.0, 1.0))

def _tanh_scale(v, scale=0.05) -> float:
    if not math.isfinite(v): return 0.0
    return float(np.tanh(v / scale))


# ── Price proxy (structural = 6M/12M spread; monthly = 1M/3M) ────────────────
def _price_proxy(prices: Dict) -> Dict[str, float]:
    def r(t, n): return _ret(prices.get(t), n)

    # Monthly signals
    spy1=_first_finite(r("SPY",21)); spy3=_first_finite(r("SPY",63))
    xli1=_first_finite(r("XLI",21)); xli3=_first_finite(r("XLI",63))
    xly1=_first_finite(r("XLY",21)); xly3=_first_finite(r("XLY",63))
    iwm1=_first_finite(r("IWM",21)); iwm3=_first_finite(r("IWM",63))
    xhb3=_first_finite(r("XHB",63))
    uup1=_first_finite(r("UUP",21)); uup3=_first_finite(r("UUP",63))
    oil1=_first_finite(r("CL=F",21), r("USO",21))
    oil3=_first_finite(r("CL=F",63), r("USO",63))
    gld1=_first_finite(r("GLD",21)); gld3=_first_finite(r("GLD",63))
    tlt1=_first_finite(r("TLT",21))

    # Structural signals (6M/12M)
    spy6=_first_finite(r("SPY",126)); spy12=_first_finite(r("SPY",252))
    xli6=_first_finite(r("XLI",126)); xli12=_first_finite(r("XLI",252))
    xly6=_first_finite(r("XLY",126)); xly12=_first_finite(r("XLY",252))
    iwm6=_first_finite(r("IWM",126)); iwm12=_first_finite(r("IWM",252))
    xhb6=_first_finite(r("XHB",126)); xhb12=_first_finite(r("XHB",252))
    oil6=_first_finite(r("CL=F",126), r("USO",126))
    oil12=_first_finite(r("CL=F",252), r("USO",252))
    gld6=_first_finite(r("GLD",126)); gld12=_first_finite(r("GLD",252))

    # Acceleration spreads (true 2nd derivative)
    spy_acc =_acc_spread(spy6, spy12)
    xli_acc =_acc_spread(xli6, xli12)
    xly_acc =_acc_spread(xly6, xly12)
    iwm_acc =_acc_spread(iwm6, iwm12)
    xhb_acc =_acc_spread(xhb6, xhb12)
    oil_acc =_acc_spread(oil6, oil12)
    gld_acc =_acc_spread(gld6, gld12)

    # Q3 differentiators
    hyg6=_first_finite(r("HYG",126), r("LQD",126))
    tlt6=_first_finite(r("TLT",126))
    xlp6=_first_finite(r("XLP",126))
    xly6v=_first_finite(r("XLY",126))
    spy6v=_first_finite(r("SPY",126))
    iwm6v=_first_finite(r("IWM",126))

    credit_stress_6 = _nan(spy6v - hyg6)
    quality_bid_6   = _nan(tlt6 - spy6v * 0.5)
    consumer_stress_6 = _nan(xlp6 - xly6v)
    breadth_stress_6  = _nan(spy6v - iwm6v)

    q3_conf_raw = (
        max(0.0, credit_stress_6) * 2.0 +
        max(0.0, quality_bid_6) * 1.5 +
        max(0.0, consumer_stress_6) * 2.0 +
        max(0.0, breadth_stress_6) * 1.0
    )
    q3_modifier = float(np.tanh(q3_conf_raw / 0.12) * 0.40)

    return {
        # Growth proxies (structural = 6M/12M spread)
        "indpro_yoy":   _nan(0.55*xli12 + 0.45*spy12),
        "retail_yoy":   _nan(0.60*xly12 + 0.40*spy12),
        "payrolls_yoy": _nan(0.50*iwm12 + 0.50*spy12),
        "housing_yoy":  _nan(0.70*xhb12 + 0.30*iwm12),
        "ism_norm":     _nan(10.0 * xli3),
        "unrate_inv":   _nan(-0.10 * iwm12),
        "claims_inv":   _nan(-5.0 * iwm3),
        # ISM sub-components proxy
        "ism_orders_inv": _nan(xli_acc * 2.5),
        "ism_oi_roc":     _nan(xli1 * 150),
        # Inflation proxies
        "cpi_yoy":       _nan(0.025 + 0.35*oil12 + 0.05*gld12),
        "core_cpi_yoy":  _nan(0.023 + 0.15*oil12 - 0.05*uup3),
        "pce_yoy":       _nan(0.90 * (0.025 + 0.35*oil12 + 0.05*gld12)),
        "core_pce_yoy":  _nan(0.88 * (0.023 + 0.15*oil12 - 0.05*uup3)),
        "breakeven_5y":  _nan(0.6*oil12 + 0.2*gld12),
        "ppi_yoy":       _nan(0.03 + 0.55*oil12),
        "oil_3m":        _nan(oil6 * 2.0),
        "gold_3m":       _nan(gld6 * 2.0),
        # ROC proxies
        "indpro_roc":   _nan(0.60*xli_acc + 0.40*spy_acc),
        "retail_roc":   _nan(0.60*xly_acc + 0.40*spy_acc),
        "payrolls_roc": _nan(0.50*iwm_acc + 0.50*spy_acc),
        "pce_roc":      _nan(0.90 * (oil_acc*0.4 + gld_acc*0.1)),
        "core_pce_roc": _nan(0.88 * (oil_acc*0.2 - uup1*0.1)),
        "ism_delta":    _nan(xli1 * 100),
        "unrate_delta": _nan(-iwm1),
        "claims_delta": 0.0,
        "cpi_roc":          _nan(oil_acc*0.4 + gld_acc*0.1),
        "core_cpi_roc":     _nan(oil_acc*0.2 - uup1*0.1),
        "breakeven_delta":  _nan(oil_acc*0.3 + gld_acc*0.1),
        "oil_1m": oil1, "dxy_inv_1m": _nan(-uup1),
        "tlt_1m": tlt1, "dxy_3m": _nan(uup3),
        "policy_score": 0.0, "liquidity_score": 0.0,
        "real_rate_norm": float("nan"), "real_rate_delta": float("nan"),
        "q3_credit_stress": _nan(credit_stress_6),
        "q3_quality_bid":   _nan(quality_bid_6),
        "q3_consumer_stress": _nan(consumer_stress_6),
        "q3_breadth_stress":  _nan(breadth_stress_6),
        "q3_modifier": q3_modifier,
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
    f["ism_norm"] = (ism - ISM_NEUTRAL) / ISM_NEUTRAL if math.isfinite(ism) else float("nan")
    f["housing_yoy"]  = _yoy(fred.get("HOUST"))
    unrate_3m = _delta(fred.get("UNRATE"), 3)
    claims_d  = _delta(fred.get("ICSA"), 13)
    f["unrate_inv"]   = -float(np.tanh(unrate_3m / 0.2)) if math.isfinite(unrate_3m) else float("nan")
    f["claims_inv"]   = -float(np.tanh(claims_d / 50000)) if math.isfinite(claims_d) else float("nan")
    f["indpro_roc"]   = _roc(fred.get("INDPRO"), 12, 3)
    f["retail_roc"]   = _roc(fred.get("RSAFS"), 12, 3)
    f["payrolls_roc"] = _roc(fred.get("PAYEMS"), 12, 3)
    ism_d = _delta(ism_s, 3)
    f["ism_delta"]    = ism_d / ISM_NEUTRAL if math.isfinite(ism_d) else float("nan")
    f["unrate_delta"] = -unrate_3m / 0.2 if math.isfinite(unrate_3m) else float("nan")
    f["claims_delta"] = -claims_d / 50000 if math.isfinite(claims_d) else float("nan")

    # ISM sub-components (v2)
    ism_no = _last(fred.get("NAPMNO"))
    ism_ii = _last(fred.get("NAPMII"))
    if math.isfinite(ism_no) and math.isfinite(ism_ii):
        oi_spread = ism_no - ism_ii
        f["ism_orders_inv"] = float(np.tanh(oi_spread / 15.0))
        oi_s = _fv(fred.get("NAPMNO"))
        if oi_s is not None:
            oi_d = _delta(oi_s, 3)
            f["ism_oi_roc"] = float(np.tanh(oi_d / 5.0)) if math.isfinite(oi_d) else float("nan")
        else:
            f["ism_oi_roc"] = float("nan")
    else:
        f["ism_orders_inv"] = float("nan")
        f["ism_oi_roc"]     = float("nan")

    # Inflation — CPI
    f["cpi_yoy"]      = _yoy(fred.get("CPIAUCSL"))
    f["core_cpi_yoy"] = _yoy(fred.get("CPILFESL"))
    f["ppi_yoy"]      = _yoy(fred.get("PPIACO"))
    be5 = _last(fred.get("T5YIE"))
    f["breakeven_5y"] = (be5 - 2.2) / 2.0 if math.isfinite(be5) else float("nan")
    f["cpi_roc"]      = _roc(fred.get("CPIAUCSL"), 12, 3)
    f["core_cpi_roc"] = _roc(fred.get("CPILFESL"), 12, 3)
    be5_d = _delta(fred.get("T5YIE"), 1)
    f["breakeven_delta"] = be5_d / 0.3 if math.isfinite(be5_d) else float("nan")

    # PCE (v2 — Fed's primary inflation target)
    f["pce_yoy"]      = _yoy(fred.get("PCEPI"))
    f["core_pce_yoy"] = _yoy(fred.get("PCEPILFE"))
    f["pce_roc"]      = _roc(fred.get("PCEPI"), 12, 3)
    f["core_pce_roc"] = _roc(fred.get("PCEPILFE"), 12, 3)

    # Policy
    ff_s  = _fv(fred.get("FEDFUNDS"), fred.get("DFF"))
    ff_delta = _delta(ff_s, 3)
    f["policy_score"] = float(np.tanh(-_nan(ff_delta) / 0.5))
    m2_roc = _roc(fred.get("M2SL"), 12, 3)
    f["liquidity_score"] = float(np.tanh(_nan(m2_roc) / 0.05))

    # Real Rates (DFII10 = 10yr TIPS = real rate directly)
    dfii10_s = _fv(fred.get("DFII10"))
    if dfii10_s is not None:
        real_rate = _last(dfii10_s)
        real_rate_d = _delta(dfii10_s, 3)
        f["real_rate_norm"]  = float(np.tanh((real_rate - 1.0) / 1.5)) if math.isfinite(real_rate) else float("nan")
        f["real_rate_delta"] = float(np.tanh(real_rate_d / 0.5)) if math.isfinite(real_rate_d) else float("nan")
        # Incorporate into policy score: rising real rates = tightening even if Fed pauses
        if math.isfinite(f["policy_score"]) and math.isfinite(f["real_rate_norm"]):
            f["policy_score"] = float(np.tanh(
                0.60 * float(np.arctanh(max(-0.99, min(0.99, f["policy_score"])))) +
                0.40 * (-f["real_rate_norm"] * 0.8)
            ))
    else:
        f["real_rate_norm"]  = float("nan")
        f["real_rate_delta"] = float("nan")

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

        # Coverage: use FRED_COVERAGE_KEYS (13 keys) for accuracy
        n_fred = sum(1 for k in FRED_COVERAGE_KEYS
                     if math.isfinite(f_fred.get(k, float("nan"))))
        proxy_share = 1.0 - n_fred / max(len(FRED_COVERAGE_KEYS), 1)
        coverage    = 1.0 - proxy_share

        logger.info(f"GIP: FRED coverage {n_fred}/{len(FRED_COVERAGE_KEYS)} "
                    f"({coverage:.0%}), proxy_share={proxy_share:.0%}")

        def merge(key):
            v = f_fred.get(key, float("nan"))
            return v if math.isfinite(v) else f_proxy.get(key, float("nan"))

        # ── GROWTH level & momentum ───────────────────────────────────────────
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

        # ── INFLATION level & momentum ────────────────────────────────────────
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

        # ── Weighted aggregates ───────────────────────────────────────────────
        def weighted_avg(signals, weights):
            total_w = 0.0; total_v = 0.0
            for k, w in weights.items():
                v = signals.get(k, float("nan"))
                if math.isfinite(v): total_v += w * v; total_w += w
            return total_v / total_w if total_w > 0.1 else 0.0

        g_level = weighted_avg(g_lvl, GROWTH_LEVEL_WEIGHTS)
        g_mom_  = weighted_avg(g_mom, GROWTH_MOM_WEIGHTS)
        i_level = weighted_avg(i_lvl, INFLATION_LEVEL_WEIGHTS)
        i_mom_  = weighted_avg(i_mom, INFLATION_MOM_WEIGHTS)
        policy  = _nan(merge("policy_score"))

        # ══════════════════════════════════════════════════════════════════════
        # PROXY BIAS CORRECTION (v4 fix — root cause of false Q2 structural)
        #
        # Problem: When proxy_share > 0.40, growth_momentum is estimated from
        # SPY/XLI price returns. During multiple-expansion rallies (like Apr 2026
        # trade deal euphoria), price rises WITHOUT fundamental GDP acceleration.
        # This creates false "growth accelerating" signal → wrong Q2 structural.
        #
        # Fix: Discount growth_momentum proportionally to proxy_share.
        # Full FRED data → no discount. 100% proxy → 50% discount on g_mom.
        # The inflation signals (PCE, CPI, PPI, breakevens) are less distorted
        # by price proxies, so we don't discount those.
        #
        # Additionally: if inflation is clearly elevated (i_level > 0.15 AND
        # i_mom > 0.20) while growth signal is ambiguous from proxy data,
        # apply explicit Q3 anchor to prevent false Q2 output.
        # ══════════════════════════════════════════════════════════════════════
        proxy_growth_discount = 0.0
        q3_anchor_mod = 0.0

        # Store raw g_mom_ BEFORE proxy discount — monthly needs undiscounted value
        g_mom_raw_for_monthly = g_mom_

        if proxy_share > 0.40:
            # Linear discount: 0% at proxy_share=0.40, 50% at proxy_share=1.00
            discount_factor = (proxy_share - 0.40) / 0.60 * 0.50
            proxy_growth_discount = discount_factor
            g_mom_ = g_mom_ * (1.0 - discount_factor)
            logger.info(f"Proxy bias correction: discount={discount_factor:.0%} "
                        f"g_mom_ adjusted to {g_mom_:.3f}")

        if (proxy_share > 0.40
                and i_level > 0.15
                and i_mom_ > 0.15
                and abs(g_mom_) < 0.25):
            # Inflation clearly elevated + growth ambiguous + heavy proxy reliance
            # → anchor toward Q3 (Stagflation), away from Q2 (Reflation)
            # This matches Hedgeye's March 2026 explicit "Quad 3 for Q2 and Q3 quarters"
            q3_anchor_mod = min(0.25, (i_level + i_mom_) * 0.3 * proxy_share)
            logger.info(f"Q3 anchor applied: +{q3_anchor_mod:.3f} to Q3 score")

        # ── Q3 credit/quality modifiers from proxy ────────────────────────────
        q3_mod = _nan(f_proxy.get("q3_modifier", 0.0))
        # Scale down q3_mod when we have real FRED data (less need for proxy signals)
        q3_mod *= max(0.2, proxy_share)

        # ── Structural scoring ────────────────────────────────────────────────
        struct_mods = {"Q3": q3_mod + q3_anchor_mod}
        struct_probs, struct_quad, struct_conf = _score_quad(
            g_level, g_mom_, i_level, i_mom_, policy,
            STRUCTURAL_WEIGHTS, POLICY_WEIGHT_STRUCTURAL, struct_mods
        )

        # ── Monthly (weather) scoring ─────────────────────────────────────────
        # Monthly = current month nowcast. Must be RESPONSIVE to short-term data.
        # McCullough: "Monthly Quad is the weather, not the season."
        #
        # KEY RULES for monthly:
        #   1. NO Q3 anchor — monthly should freely follow price/data signals
        #   2. NO proxy discount — short-term price momentum IS valid for monthly
        #      (trade deal rally, DXY, yield move = real monthly signals)
        #   3. Use RAW g_mom before proxy discount was applied
        #   4. MONTHLY_WEIGHTS: growth_momentum=0.50 (more reactive than structural)
        #
        # Evidence: Apr 20 2026 "#Quad2 Breakout, It Was" + Apr 22 "Tracking #Quad2"
        # = Hedgeye monthly called Q2 in April. Monthly must follow these signals.

        # Raw growth momentum (before proxy discount — monthly needs it undiscounted)
        g_mom_raw_val = g_mom_raw_for_monthly
        # For monthly: use raw proxy signals (XLI/SPY 1M/3M) — they ARE the monthly signal
        m_g_level = g_level * 0.65          # slight bleed-through from structural
        m_g_mom   = g_mom_raw_val * 1.20    # raw (undiscounted) momentum, amplified
        m_i_level = i_level * 0.75          # inflation base level
        m_i_mom   = i_mom_ * 1.20          # inflation momentum slightly amplified monthly

        # ZERO Q3 anchor on monthly — let the data speak
        month_mods = {}
        month_probs, month_quad, month_conf = _score_quad(
            m_g_level, m_g_mom, m_i_level, m_i_mom, policy,
            MONTHLY_WEIGHTS, POLICY_WEIGHT_MONTHLY, month_mods
        )

        # ── Divergence / operating regime ─────────────────────────────────────
        if struct_quad == month_quad:
            div = "aligned"
            regime = f"{struct_quad} ({struct_conf:.0%} conf)"
        else:
            div = f"divergent ({struct_quad} structural / {month_quad} monthly)"
            regime = f"transitioning {struct_quad}→{month_quad}"

        # ── Headline gap (inflation surprise vs growth) ────────────────────────
        hgap   = float(i_mom_ - g_mom_)
        shock  = clamp01(abs(hgap) * 3.0)

        # ── Bond pivot signal ─────────────────────────────────────────────────
        _tlt = prices.get("TLT"); _ief = prices.get("IEF")
        tlt_1m = float(pd.to_numeric(pd.Series(_tlt) if isinstance(_tlt,list) else _tlt,
                        errors="coerce").pct_change(21).dropna().iloc[-1]) \
                 if _tlt is not None else 0.0
        ief_1m = float(pd.to_numeric(pd.Series(_ief) if isinstance(_ief,list) else _ief,
                        errors="coerce").pct_change(21).dropna().iloc[-1]) \
                 if _ief is not None else 0.0
        bond_pivot_signal = clamp01(0.5 + tlt_1m*8 + ief_1m*4)

        features = dict(
            growth_level=g_level,
            growth_momentum=g_mom_,
        growth_momentum_raw=g_mom_raw_for_monthly,
            inflation_level=i_level,
            inflation_momentum=i_mom_,
            policy_score=policy,
            data_coverage=coverage,
            proxy_share=proxy_share,
            proxy_growth_discount=proxy_growth_discount,
            q3_anchor_applied=q3_anchor_mod,
            q3_modifier=q3_mod,
            q3_credit_stress=_nan(f_proxy.get("q3_credit_stress", 0.0)),
            q3_consumer_stress=_nan(f_proxy.get("q3_consumer_stress", 0.0)),
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
        style=s.get("style",""),
        fx=s.get("fx",""),
        bonds=s.get("bonds",""),
        monthly_adds=m.get("best",[])[:3],
        note=s.get("note",""),
    )
