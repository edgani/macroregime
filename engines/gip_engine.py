"""engines/gip_engine.py — Growth · Inflation · Policy (GIP) Quad Model

Framework: Hedgeye GIP Model (27yr backtest calibration)
- Growth: Industrial Production, Retail Sales, Payrolls, ISM, Housing, Unemployment, Claims
- Inflation: CPI, Core CPI, PCE, Core PCE, PPI, Breakevens, Oil, Gold
- Policy: Fed Funds, M2, Real Rates (TIPS)

Quad determination:
  Q1 = Growth ↑ + Inflation ↓  (Goldilocks)
  Q2 = Growth ↑ + Inflation ↑  (Reflation)
  Q3 = Growth ↓ + Inflation ↑  (Stagflation)
  Q4 = Growth ↓ + Inflation ↓  (Deflation)

v2 upgrades:
  + PCE & Core PCE (Fed's preferred inflation measures)
  + ISM Orders-Inventories spread (most leading ISM sub-component)
  + Real Rates from DFII10 (TIPS) for Q4 detection
  + 13 FRED coverage keys (was 9)
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from config.settings import (
    FRED_GROWTH_SERIES, FRED_INFLATION_SERIES, FRED_POLICY_SERIES,
    GROWTH_LEVEL_WEIGHTS, GROWTH_MOM_WEIGHTS,
    INFLATION_LEVEL_WEIGHTS, INFLATION_MOM_WEIGHTS,
    STRUCTURAL_WEIGHTS, MONTHLY_WEIGHTS,
    POLICY_WEIGHT_STRUCTURAL, POLICY_WEIGHT_MONTHLY,
    ISM_NEUTRAL, FRED_COVERAGE_KEYS,
    QUAD_ASSET_PERFORMANCE,
)

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _fv(series):
    """Extract numeric series from FRED dict entry (may be Series or scalar)."""
    if series is None:
        return None
    if isinstance(series, pd.Series):
        s = pd.to_numeric(series, errors="coerce").dropna()
        return s if not s.empty else None
    if isinstance(series, (list, tuple)) and len(series) > 0:
        return pd.Series([float(x) for x in series if x is not None])
    try:
        return pd.Series([float(series)])
    except Exception:
        return None

def _last(series):
    """Last valid value from a numeric series."""
    s = _fv(series)
    if s is None or s.empty:
        return float("nan")
    v = float(s.iloc[-1])
    return v if math.isfinite(v) else float("nan")

def _yoy(series, periods: int = 12):
    """Year-over-year change (assumes monthly data)."""
    s = _fv(series)
    if s is None or len(s) < periods + 1:
        return float("nan")
    try:
        return float(s.iloc[-1] / s.iloc[-periods - 1] - 1)
    except Exception:
        return float("nan")

def _roc(series, lookback: int = 12, smooth: int = 3):
    """Rate of change: (current / lag) - 1, optionally smoothed."""
    s = _fv(series)
    if s is None or len(s) < lookback + smooth:
        return float("nan")
    try:
        raw = s.pct_change(periods=lookback)
        if smooth > 1:
            raw = raw.rolling(smooth, min_periods=1).mean()
        v = float(raw.iloc[-1])
        return v if math.isfinite(v) else float("nan")
    except Exception:
        return float("nan")

def _delta(series, periods: int = 3):
    """Simple difference over N periods."""
    s = _fv(series)
    if s is None or len(s) < periods + 1:
        return float("nan")
    try:
        return float(s.iloc[-1] - s.iloc[-periods - 1])
    except Exception:
        return float("nan")

def _nan(val, default=0.0):
    """Return default if val is NaN or None."""
    if val is None:
        return default
    try:
        v = float(val)
        return v if math.isfinite(v) else default
    except Exception:
        return default

def _tanh_scale(val, scale: float = 1.0):
    """Tanh-normalize: maps any real → (-1, 1) with given scale as half-saturation."""
    if val is None:
        return 0.0
    try:
        v = float(val)
        if not math.isfinite(v):
            return 0.0
        return float(np.tanh(v / max(scale, 1e-9)))
    except Exception:
        return 0.0

# ─────────────────────────────────────────────────────────────────────────────
# FEATURE EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

def _extract_fred_features(fred: Dict, prices: Dict) -> Dict[str, float]:
    """Extract all GIP features from FRED macro data + price proxies."""
    f: Dict[str, float] = {}

    # ── Growth ─────────────────────────────────────────────────────────────
    f["indpro_yoy"] = _yoy(fred.get("INDPRO"))
    f["retail_yoy"] = _yoy(fred.get("RSAFS"))
    f["payrolls_yoy"] = _yoy(fred.get("PAYEMS"))
    f["housing_yoy"] = _yoy(fred.get("HOUST"))

    # ISM Manufacturing
    ism_s = _fv(fred.get("ISMNO"))
    if ism_s is not None:
        ism_last = _last(ism_s)
        f["ism_norm"] = float(np.tanh((ism_last - ISM_NEUTRAL) / 8.0)) if math.isfinite(ism_last) else 0.0
        f["ism_delta"] = float(np.tanh(_delta(ism_s, 3) / 3.0))
    else:
        f["ism_norm"] = 0.0
        f["ism_delta"] = 0.0

    # Unemployment (inverted: lower unemployment = higher growth signal)
    unrate_s = _fv(fred.get("UNRATE"))
    if unrate_s is not None:
        unrate_last = _last(unrate_s)
        f["unrate_inv"] = float(np.tanh((4.5 - unrate_last) / 2.0)) if math.isfinite(unrate_last) else 0.0
        f["unrate_delta"] = float(np.tanh(-_delta(unrate_s, 3) / 0.5))
    else:
        f["unrate_inv"] = 0.0
        f["unrate_delta"] = 0.0

    # Initial Claims (inverted: lower claims = higher growth)
    claims_s = _fv(fred.get("ICSA"))
    if claims_s is not None:
        claims_last = _last(claims_s)
        f["claims_inv"] = float(np.tanh((220000 - claims_last) / 80000)) if math.isfinite(claims_last) else 0.0
        f["claims_delta"] = float(np.tanh(-_delta(claims_s, 3) / 20000))
    else:
        f["claims_inv"] = 0.0
        f["claims_delta"] = 0.0

    # Growth ROCs
    f["indpro_roc"] = _roc(fred.get("INDPRO"), 12, 3)
    f["retail_roc"] = _roc(fred.get("RSAFS"), 12, 3)
    f["payrolls_roc"] = _roc(fred.get("PAYEMS"), 12, 3)

    # ── Inflation ──────────────────────────────────────────────────────────
    f["cpi_yoy"] = _yoy(fred.get("CPIAUCSL"))
    f["core_cpi_yoy"] = _yoy(fred.get("CPILFESL"))
    f["ppi_yoy"] = _yoy(fred.get("PPIACO"))

    # Breakevens
    t5y = _fv(fred.get("T5YIE"))
    f["breakeven_5y"] = _last(t5y) / 100.0 if t5y is not None else float("nan")
    t10y = _fv(fred.get("T10YIE"))
    f["breakeven_10y"] = _last(t10y) / 100.0 if t10y is not None else float("nan")
    f["breakeven_delta"] = _delta(t5y, 3) / 100.0 if t5y is not None else float("nan")

    # Oil & Gold from prices (3M returns as inflation proxies)
    cl = prices.get("CL=F")
    if cl is not None and len(cl) > 64:
        cl = pd.to_numeric(cl, errors="coerce").dropna()
        f["oil_3m"] = float(cl.iloc[-1] / cl.iloc[-64] - 1) if len(cl) > 64 else float("nan")
        f["oil_1m"] = float(cl.iloc[-1] / cl.iloc[-22] - 1) if len(cl) > 22 else float("nan")
    else:
        f["oil_3m"] = float("nan")
        f["oil_1m"] = float("nan")

    gld = prices.get("GLD")
    if gld is not None and len(gld) > 64:
        gld = pd.to_numeric(gld, errors="coerce").dropna()
        f["gold_3m"] = float(gld.iloc[-1] / gld.iloc[-64] - 1) if len(gld) > 64 else float("nan")
    else:
        f["gold_3m"] = float("nan")

    # DXY
    dxy = prices.get("DX-Y.NYB")
    if dxy is not None and len(dxy) > 22:
        dxy = pd.to_numeric(dxy, errors="coerce").dropna()
        f["dxy_inv_1m"] = float(-(dxy.iloc[-1] / dxy.iloc[-22] - 1))
    else:
        f["dxy_inv_1m"] = float("nan")

    # Inflation ROCs
    f["cpi_roc"] = _roc(fred.get("CPIAUCSL"), 12, 3)
    f["core_cpi_roc"] = _roc(fred.get("CPILFESL"), 12, 3)

    # ── v2: PCE (Fed's primary inflation target) ──────────────────────────
    f["pce_yoy"] = _yoy(fred.get("PCEPI"))
    f["core_pce_yoy"] = _yoy(fred.get("PCEPILFE"))
    f["pce_roc"] = _roc(fred.get("PCEPI"), 12, 3)
    f["core_pce_roc"] = _roc(fred.get("PCEPILFE"), 12, 3)

    # ── v2: ISM New Orders - Inventories Spread ───────────────────────────
    ism_no = _fv(fred.get("NAPMNO"))
    ism_ii = _fv(fred.get("NAPMII"))
    if ism_no is not None and ism_ii is not None:
        oi_series = ism_no - ism_ii
        oi_last = _last(oi_series)
        f["ism_orders_inv"] = float(np.tanh(oi_last / 15.0)) if math.isfinite(oi_last) else float("nan")
        oi_roc = _delta(oi_series, 3)
        f["ism_oi_roc"] = float(np.tanh(oi_roc / 5.0)) if math.isfinite(oi_roc) else float("nan")
    else:
        f["ism_orders_inv"] = f.get("ism_norm", float("nan")) * 1.2
        f["ism_oi_roc"] = f.get("ism_delta", float("nan")) * 1.1

    # ── v2: Real Rates (DFII10 = 10yr TIPS real rate) ──────────────────────
    dfii10_s = _fv(fred.get("DFII10"))
    if dfii10_s is not None:
        real_rate = _last(dfii10_s)
        real_rate_delta = _delta(dfii10_s, 3)
        f["real_rate_norm"] = float(np.tanh((real_rate - 1.0) / 1.5)) if math.isfinite(real_rate) else float("nan")
        f["real_rate_delta"] = float(np.tanh(real_rate_delta / 0.5)) if math.isfinite(real_rate_delta) else float("nan")
    else:
        f["real_rate_norm"] = float("nan")
        f["real_rate_delta"] = float("nan")

    # ── Policy ─────────────────────────────────────────────────────────────
    ff_s = _fv(fred.get("FEDFUNDS"))
    if ff_s is not None:
        ff_last = _last(ff_s)
        ff_delta = _delta(ff_s, 3)
        f["policy_score"] = float(np.tanh(-ff_delta / 0.5)) if math.isfinite(ff_delta) else 0.0
    else:
        f["policy_score"] = 0.0

    # v2: Incorporate real rates into policy score
    if "policy_score" in f and math.isfinite(f["policy_score"]) and math.isfinite(f.get("real_rate_norm", float("nan"))):
        try:
            ps = float(np.arctanh(max(-0.99, min(0.99, f["policy_score"]))))
            rr = f["real_rate_norm"]
            f["policy_score"] = float(np.tanh(0.60 * ps + 0.40 * (-rr * 0.8)))
        except Exception:
            pass

    # M2 Liquidity
    m2_roc = _roc(fred.get("M2SL"), 12, 3)
    f["liquidity_score"] = float(np.tanh(_nan(m2_roc) / 0.05))

    # Leading indicator composite (ISM orders-inventories + claims + breakevens)
    li_composite = (
        _nan(f.get("ism_orders_inv", 0.0)) * 0.40 +
        _nan(f.get("claims_inv", 0.0)) * 0.30 +
        _nan(f.get("breakeven_5y", 0.0)) * 0.30
    )
    f["leading_indicator_composite"] = float(np.tanh(li_composite))

    return f

# ─────────────────────────────────────────────────────────────────────────────
# PRICE PROXY (when FRED data is missing)
# ─────────────────────────────────────────────────────────────────────────────

def _price_proxy(prices: Dict) -> Dict[str, float]:
    """Create proxy macro features from price data when FRED is unavailable."""
    p: Dict[str, float] = {}

    def _s(ticker, lb):
        s = prices.get(ticker)
        if s is None or len(s) < lb + 5:
            return None
        return pd.to_numeric(s, errors="coerce").dropna()

    # Oil & Gold returns
    oil12 = None; oil_acc = None; oil1 = None
    cl = _s("CL=F", 252)
    if cl is not None:
        oil12 = float(cl.iloc[-1] / cl.iloc[-min(252, len(cl))] - 1)
        oil1 = float(cl.iloc[-1] / cl.iloc[-min(22, len(cl))] - 1) if len(cl) > 22 else 0.0
        oil_acc = float((cl.pct_change().dropna().tail(63) > 0).mean()) if len(cl) > 64 else 0.5

    gld12 = None; gld_acc = None
    gl = _s("GLD", 252)
    if gl is not None:
        gld12 = float(gl.iloc[-1] / gl.iloc[-min(252, len(gl))] - 1)
        gld_acc = float((gl.pct_change().dropna().tail(63) > 0).mean()) if len(gl) > 64 else 0.5

    # DXY
    uup3 = None; uup1 = None
    dxy = _s("DX-Y.NYB", 63)
    if dxy is not None:
        uup3 = float(dxy.iloc[-1] / dxy.iloc[-min(63, len(dxy))] - 1)
        uup1 = float(dxy.iloc[-1] / dxy.iloc[-min(22, len(dxy))] - 1) if len(dxy) > 22 else 0.0

    # XLI (industrials) as ISM proxy
    xli_acc = None; xli1 = None
    xli = _s("XLI", 63)
    if xli is not None:
        xli_acc = float((xli.pct_change().dropna().tail(63) > 0).mean()) if len(xli) > 64 else 0.5
        xli1 = float(xli.iloc[-1] / xli.iloc[-min(22, len(xli))] - 1) if len(xli) > 22 else 0.0

    # S&P as growth proxy
    spy = _s("SPY", 252)
    spy12 = float(spy.iloc[-1] / spy.iloc[-min(252, len(spy))] - 1) if spy is not None else 0.0

    # Proxy features
    p["indpro_yoy"] = _nan(spy12 * 0.8 + (oil12 or 0.0) * 0.2)
    p["retail_yoy"] = _nan(spy12 * 0.7)
    p["payrolls_yoy"] = _nan(spy12 * 0.6)
    p["housing_yoy"] = _nan((spy12 or 0.0) * 0.4 + (oil12 or 0.0) * 0.1)
    p["ism_norm"] = _nan((xli_acc or 0.5) * 2.0 - 1.0)
    p["ism_delta"] = _nan((xli1 or 0.0) * 50.0)
    p["unrate_inv"] = _nan((spy12 or 0.0) * 2.0)
    p["claims_inv"] = _nan((spy12 or 0.0) * 1.5)
    p["indpro_roc"] = _nan(spy12 * 0.5)
    p["retail_roc"] = _nan(spy12 * 0.4)
    p["payrolls_roc"] = _nan(spy12 * 0.3)
    p["ism_delta"] = _nan((xli1 or 0.0) * 30.0)
    p["unrate_delta"] = _nan(-(spy12 or 0.0) * 3.0)
    p["claims_delta"] = _nan(-(spy12 or 0.0) * 2.0)

    # Inflation proxies
    p["cpi_yoy"] = _nan(0.025 + 0.35 * (oil12 or 0.0) + 0.05 * (gld12 or 0.0))
    p["core_cpi_yoy"] = _nan(0.023 + 0.15 * (oil12 or 0.0) - 0.05 * (uup3 or 0.0))
    p["ppi_yoy"] = _nan(0.020 + 0.45 * (oil12 or 0.0))
    p["breakeven_5y"] = _nan(0.022 + 0.3 * (oil12 or 0.0) + 0.1 * (gld12 or 0.0))
    p["breakeven_delta"] = _nan((oil1 or 0.0) * 0.5 + (uup1 or 0.0) * 0.3)
    p["oil_3m"] = _nan(oil12)
    p["oil_1m"] = _nan(oil1)
    p["gold_3m"] = _nan(gld12)
    p["dxy_inv_1m"] = _nan(-(uup1 or 0.0))
    p["cpi_roc"] = _nan((oil_acc or 0.5) * 0.06 - 0.03)
    p["core_cpi_roc"] = _nan((oil_acc or 0.5) * 0.04 - 0.02)

    # v2 proxy additions
    p["pce_yoy"] = _nan(0.90 * (0.025 + 0.35 * (oil12 or 0.0) + 0.05 * (gld12 or 0.0)))
    p["core_pce_yoy"] = _nan(0.88 * (0.023 + 0.15 * (oil12 or 0.0) - 0.05 * (uup3 or 0.0)))
    p["pce_roc"] = _nan(0.90 * ((oil_acc or 0.5) * 0.4 + (gld_acc or 0.5) * 0.1))
    p["core_pce_roc"] = _nan(0.88 * ((oil_acc or 0.5) * 0.2 - (uup1 or 0.0) * 0.1))
    p["ism_orders_inv"] = _nan((xli_acc or 0.5) * 2.5)
    p["ism_oi_roc"] = _nan((xli1 or 0.0) * 150)
    p["real_rate_norm"] = float("nan")
    p["real_rate_delta"] = float("nan")

    # Policy / liquidity proxies
    p["policy_score"] = _nan(-(uup1 or 0.0) * 5.0)
    p["liquidity_score"] = _nan((spy12 or 0.0) * 2.0)
    p["leading_indicator_composite"] = _nan(p.get("ism_orders_inv", 0.0) * 0.4 + p.get("claims_inv", 0.0) * 0.3)

    return p

# ─────────────────────────────────────────────────────────────────────────────
# GIP ENGINE
# ─────────────────────────────────────────────────────────────────────────────

class GIPEngine:
    """
    Growth · Inflation · Policy rate-of-change model.
    Determines current macro Quad (Q1-Q4) from FRED + price data.
    """

    def run(self, fred: Optional[Dict] = None, prices: Optional[Dict] = None) -> object:
        fred = fred or {}
        prices = prices or {}

        # Extract features from FRED
        f_fred = _extract_fred_features(fred, prices)

        # Compute proxy features from prices (fallback)
        f_proxy = _price_proxy(prices)

        # Merge: FRED takes priority, proxy fills gaps
        f: Dict[str, float] = {}
        for k in set(list(f_fred.keys()) + list(f_proxy.keys())):
            v_fred = f_fred.get(k)
            v_proxy = f_proxy.get(k)
            if v_fred is not None and math.isfinite(v_fred):
                f[k] = v_fred
            elif v_proxy is not None and math.isfinite(v_proxy):
                f[k] = v_proxy
            else:
                f[k] = float("nan")

        # Coverage tracking
        n_fred = sum(1 for k in FRED_COVERAGE_KEYS if math.isfinite(f_fred.get(k, float("nan"))))
        proxy_share = 1.0 - n_fred / max(len(FRED_COVERAGE_KEYS), 1)
        data_coverage = n_fred / max(len(FRED_COVERAGE_KEYS), 1)

        # ── Compute sub-scores ───────────────────────────────────────────────
        def merge(key):
            return _nan(f.get(key, float("nan")))

        # Growth Level
        g_lvl = {
            "indpro_yoy": _tanh_scale(merge("indpro_yoy") - 0.02, 0.05),
            "retail_yoy": _tanh_scale(merge("retail_yoy") - 0.03, 0.06),
            "payrolls_yoy": _tanh_scale(merge("payrolls_yoy") - 0.015, 0.03),
            "housing_yoy": _tanh_scale(merge("housing_yoy"), 0.10),
            "ism_orders_inv": _tanh_scale(merge("ism_orders_inv"), 0.15),
            "ism_norm": _tanh_scale(merge("ism_norm"), 0.10),
            "unrate_inv": merge("unrate_inv"),
            "claims_inv": merge("claims_inv"),
        }
        growth_level = sum(g_lvl.get(k, 0.0) * GROWTH_LEVEL_WEIGHTS.get(k, 0.0) for k in g_lvl)

        # Growth Momentum
        g_mom = {
            "indpro_roc": _tanh_scale(merge("indpro_roc"), 0.025),
            "retail_roc": _tanh_scale(merge("retail_roc"), 0.030),
            "payrolls_roc": _tanh_scale(merge("payrolls_roc"), 0.015),
            "ism_oi_roc": _tanh_scale(merge("ism_oi_roc"), 0.08),
            "ism_delta": _tanh_scale(merge("ism_delta"), 0.05),
            "unrate_delta": _tanh_scale(merge("unrate_delta"), 1.0),
            "claims_delta": _tanh_scale(merge("claims_delta"), 1.0),
        }
        growth_momentum = sum(g_mom.get(k, 0.0) * GROWTH_MOM_WEIGHTS.get(k, 0.0) for k in g_mom)

        # Inflation Level
        i_lvl = {
            "pce_yoy": _tanh_scale(merge("pce_yoy") - 0.020, 0.018),
            "core_pce_yoy": _tanh_scale(merge("core_pce_yoy") - 0.020, 0.014),
            "cpi_yoy": _tanh_scale(merge("cpi_yoy") - 0.025, 0.020),
            "core_cpi_yoy": _tanh_scale(merge("core_cpi_yoy") - 0.025, 0.015),
            "breakeven_5y": merge("breakeven_5y"),
            "ppi_yoy": _tanh_scale(merge("ppi_yoy") - 0.025, 0.030),
            "oil_3m": _tanh_scale(merge("oil_3m"), 0.25),
            "gold_3m": _tanh_scale(merge("gold_3m"), 0.18),
        }
        inflation_level = sum(i_lvl.get(k, 0.0) * INFLATION_LEVEL_WEIGHTS.get(k, 0.0) for k in i_lvl)

        # Inflation Momentum
        i_mom = {
            "pce_roc": _tanh_scale(merge("pce_roc"), 0.010),
            "core_pce_roc": _tanh_scale(merge("core_pce_roc"), 0.008),
            "cpi_roc": _tanh_scale(merge("cpi_roc"), 0.012),
            "core_cpi_roc": _tanh_scale(merge("core_cpi_roc"), 0.010),
            "breakeven_delta": _tanh_scale(merge("breakeven_delta"), 1.0),
            "oil_1m": _tanh_scale(merge("oil_1m"), 0.06),
            "dxy_inv_1m": _tanh_scale(merge("dxy_inv_1m"), 0.06),
        }
        inflation_momentum = sum(i_mom.get(k, 0.0) * INFLATION_MOM_WEIGHTS.get(k, 0.0) for k in i_mom)

        # Policy
        policy_score = merge("policy_score")
        liquidity_score = merge("liquidity_score")

        # ── Composite scores ─────────────────────────────────────────────────
        structural_g = (
            STRUCTURAL_WEIGHTS["growth_level"] * growth_level +
            STRUCTURAL_WEIGHTS["growth_momentum"] * growth_momentum
        )
        structural_i = (
            STRUCTURAL_WEIGHTS["inflation_level"] * inflation_level +
            STRUCTURAL_WEIGHTS["inflation_momentum"] * inflation_momentum
        )
        monthly_g = (
            MONTHLY_WEIGHTS["growth_level"] * growth_level +
            MONTHLY_WEIGHTS["growth_momentum"] * growth_momentum
        )
        monthly_i = (
            MONTHLY_WEIGHTS["inflation_level"] * inflation_level +
            MONTHLY_WEIGHTS["inflation_momentum"] * inflation_momentum
        )

        # Add policy drag
        structural_g += POLICY_WEIGHT_STRUCTURAL * policy_score
        structural_i += POLICY_WEIGHT_STRUCTURAL * 0.3 * policy_score  # policy affects both
        monthly_g += POLICY_WEIGHT_MONTHLY * policy_score
        monthly_i += POLICY_WEIGHT_MONTHLY * 0.3 * policy_score

        # Normalize
        structural_g = float(np.clip(structural_g, -1.0, 1.0))
        structural_i = float(np.clip(structural_i, -1.0, 1.0))
        monthly_g = float(np.clip(monthly_g, -1.0, 1.0))
        monthly_i = float(np.clip(monthly_i, -1.0, 1.0))

        # ── Quad determination ───────────────────────────────────────────────
        def _quad(g, i):
            if g >= 0 and i < 0:
                return "Q1"
            elif g >= 0 and i >= 0:
                return "Q2"
            elif g < 0 and i >= 0:
                return "Q3"
            else:
                return "Q4"

        structural_quad = _quad(structural_g, structural_i)
        monthly_quad = _quad(monthly_g, monthly_i)

        # ── Probabilities (softmax over distance from quadrant boundaries) ───
        def _quad_probs(g, i):
            """Compute probability distribution over Q1-Q4."""
            # Distance from each quadrant center
            centers = {
                "Q1": (0.5, -0.5), "Q2": (0.5, 0.5),
                "Q3": (-0.5, 0.5), "Q4": (-0.5, -0.5),
            }
            dists = {}
            for q, (cg, ci) in centers.items():
                d = math.sqrt((g - cg) ** 2 + (i - ci) ** 2) + 1e-9
                dists[q] = 1.0 / d
            total = sum(dists.values())
            return {q: v / total for q, v in dists.items()}

        structural_probs = _quad_probs(structural_g, structural_i)
        monthly_probs = _quad_probs(monthly_g, monthly_i)

        # Confidence = probability of assigned quad
        structural_conf = structural_probs.get(structural_quad, 0.25)
        monthly_conf = monthly_probs.get(monthly_quad, 0.25)

        # Flip hazard = probability of transitioning to a different quad
        flip_hazard = 1.0 - max(structural_conf, monthly_conf)

        # ── Result object ────────────────────────────────────────────────────
        result = type("GIPResult", (), {})()
        result.structural_quad = structural_quad
        result.monthly_quad = monthly_quad
        result.structural_conf = round(structural_conf, 3)
        result.monthly_conf = round(monthly_conf, 3)
        result.structural_g = round(structural_g, 3)
        result.structural_i = round(structural_i, 3)
        result.structural_probs = {k: round(v, 3) for k, v in structural_probs.items()}
        result.monthly_probs = {k: round(v, 3) for k, v in monthly_probs.items()}
        result.features = {
            "growth_level": round(growth_level, 3),
            "growth_momentum": round(growth_momentum, 3),
            "inflation_level": round(inflation_level, 3),
            "inflation_momentum": round(inflation_momentum, 3),
            "policy_score": round(policy_score, 3),
            "liquidity_score": round(liquidity_score, 3),
            "proxy_share": round(proxy_share, 3),
            "data_coverage": round(data_coverage, 3),
            "leading_indicator_composite": round(merge("leading_indicator_composite"), 3),
            **{k: round(v, 4) if math.isfinite(v) else None for k, v in f.items()},
        }
        result.flip_hazard = round(flip_hazard, 3)
        result.data_coverage = round(data_coverage, 3)
        return result

# ─────────────────────────────────────────────────────────────────────────────
# PLAYBOOK
# ─────────────────────────────────────────────────────────────────────────────

def get_playbook(structural_quad: str, monthly_quad: Optional[str] = None) -> dict:
    """Return regime playbook: best/worst assets, sectors, styles, FX, bonds."""
    s_quad = structural_quad.upper()
    m_quad = (monthly_quad or s_quad).upper()

    base = QUAD_ASSET_PERFORMANCE.get(s_quad, {})
    monthly = QUAD_ASSET_PERFORMANCE.get(m_quad, {})

    # If monthly differs from structural, blend the playbooks
    if m_quad != s_quad:
        best = list(dict.fromkeys(base.get("best", []) + monthly.get("best", [])[:2]))
        worst = list(dict.fromkeys(base.get("worst", []) + monthly.get("worst", [])[:2]))
        style = base.get("style", "") + " | Monthly overlay: " + monthly.get("style", "")
        fx = base.get("fx", "") + " | Monthly: " + monthly.get("fx", "")
        bonds = base.get("bonds", "") + " | Monthly: " + monthly.get("bonds", "")
    else:
        best = base.get("best", [])
        worst = base.get("worst", [])
        style = base.get("style", "")
        fx = base.get("fx", "")
        bonds = base.get("bonds", "")

    return {
        "structural_quad": s_quad,
        "monthly_quad": m_quad,
        "best": best,
        "worst": worst,
        "style": style,
        "fx": fx,
        "bonds": bonds,
        "sectors_overweight": base.get("sectors_overweight", []),
        "sectors_underweight": base.get("sectors_underweight", []),
    }
