from __future__ import annotations
from typing import Dict

import numpy as np
import pandas as pd


def _safe_series(s) -> pd.Series:
    if s is None:
        return pd.Series(dtype=float)
    if isinstance(s, pd.Series):
        return pd.to_numeric(s, errors="coerce").dropna()
    return pd.Series(dtype=float)


def last(s) -> float:
    s = _safe_series(s)
    return float(s.iloc[-1]) if not s.empty else float("nan")


def ret_n(s, n: int) -> float:
    s = _safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    base = float(s.iloc[-(n + 1)])
    if not np.isfinite(base) or base == 0:
        return float("nan")
    return float(s.iloc[-1] / base - 1.0)


def delta_n(s, n: int) -> float:
    s = _safe_series(s)
    if len(s) < n + 1:
        return float("nan")
    return float(s.iloc[-1] - s.iloc[-(n + 1)])


def delta_ret_n(s, n: int, offset: int = 3) -> float:
    s = _safe_series(s)
    if len(s) < n + offset + 1:
        return float("nan")
    try:
        end_now = float(s.iloc[-1])
        base_now = float(s.iloc[-(n + 1)])
        end_offset = float(s.iloc[-(offset + 1)])
        base_offset = float(s.iloc[-(n + offset + 1)])
        if not (np.isfinite(base_now) and base_now != 0):
            return float("nan")
        if not (np.isfinite(base_offset) and base_offset != 0):
            return float("nan")
        current_roc = end_now / base_now - 1.0
        prior_roc = end_offset / base_offset - 1.0
        return float(current_roc - prior_roc)
    except Exception:
        return float("nan")


def _scaled(x: float, scale: float) -> float:
    if not np.isfinite(x):
        return float("nan")
    return float(np.tanh(x / scale))


def _nanmean_or(values, default: float = 0.0) -> float:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0 or not np.isfinite(arr).any():
        return float(default)
    return float(np.nanmean(arr))


def _fallback_price_proxy(prices: Dict[str, pd.Series]) -> dict:
    spy_3m = ret_n(prices.get("SPY"), 63)
    xli_3m = ret_n(prices.get("XLI"), 63)
    xly_3m = ret_n(prices.get("XLY"), 63)
    iwm_3m = ret_n(prices.get("IWM"), 63)
    xhb_3m = ret_n(prices.get("XHB"), 63)
    uup_3m = ret_n(prices.get("UUP"), 63)
    oil_3m = ret_n(prices.get("CL=F"), 63)
    gold_3m = ret_n(prices.get("GC=F"), 63)
    breakeven_proxy = (
        2.2
        + 1.2 * np.nan_to_num(oil_3m, nan=0.0)
        + 0.4 * np.nan_to_num(gold_3m, nan=0.0)
        - 0.2 * np.nan_to_num(uup_3m, nan=0.0)
    )
    return {
        "indpro_yoy": float(np.nan_to_num(0.55 * xli_3m + 0.45 * spy_3m, nan=0.0)),
        "retail_yoy": float(np.nan_to_num(0.60 * xly_3m + 0.40 * spy_3m, nan=0.0)),
        "payrolls_yoy": float(np.nan_to_num(0.50 * iwm_3m + 0.50 * spy_3m, nan=0.0)),
        "unrate_3m_delta": float(np.nan_to_num(-0.10 * iwm_3m, nan=0.0)),
        "claims_13w_delta": float(np.nan_to_num(-10.0 * iwm_3m, nan=0.0)),
        "ism_last": float(np.nan_to_num(50.0 + 20.0 * xli_3m, nan=50.0)),
        "housing_yoy": float(np.nan_to_num(0.70 * xhb_3m + 0.30 * iwm_3m, nan=0.0)),
        "cpi_yoy": float(np.nan_to_num(0.025 + 0.35 * oil_3m + 0.05 * gold_3m, nan=0.025)),
        "core_cpi_yoy": float(np.nan_to_num(0.023 + 0.15 * oil_3m - 0.05 * uup_3m, nan=0.023)),
        "breakeven_last": float(np.nan_to_num(breakeven_proxy, nan=2.2)),
    }


def build_macro_features(
    fred: Dict[str, pd.Series],
    prices: Dict[str, pd.Series],
    loader_meta: Dict[str, dict] | None = None,
) -> Dict[str, float]:
    loader_meta = loader_meta or {}
    fred_meta = loader_meta.get("fred", {}) if isinstance(loader_meta, dict) else {}
    price_meta = loader_meta.get("prices", {}) if isinstance(loader_meta, dict) else {}

    features = {
        "indpro_yoy": ret_n(fred.get("INDPRO"), 12),
        "retail_yoy": ret_n(fred.get("RSAFS"), 12),
        "payrolls_yoy": ret_n(fred.get("PAYEMS"), 12),
        "unrate_3m_delta": delta_n(fred.get("UNRATE"), 3),
        "claims_13w_delta": delta_n(fred.get("ICSA"), 13),
        "ism_last": last(fred.get("ISMNO")),
        "housing_yoy": ret_n(fred.get("HOUST"), 12),
        "cpi_yoy": ret_n(fred.get("CPI"), 12),
        "core_cpi_yoy": ret_n(fred.get("CORECPI"), 12),
        "corepce_yoy": ret_n(fred.get("COREPCE"), 12) if "COREPCE" in fred else float("nan"),
        "pce_yoy": ret_n(fred.get("PCE"), 12) if "PCE" in fred else float("nan"),
        "breakeven_last": last(fred.get("T5YIE")),
        "breakeven_1m_delta": delta_n(fred.get("T5YIE"), 1),
        "real_10y_last": last(fred.get("DFII10")),
        "policy_rate_level": last(fred.get("FEDFUNDS")),
        "policy_rate_3m_delta": delta_n(fred.get("FEDFUNDS"), 3),
        "indpro_roc_3m": delta_ret_n(fred.get("INDPRO"), 12, offset=3),
        "retail_roc_3m": delta_ret_n(fred.get("RSAFS"), 12, offset=3),
        "payrolls_roc_3m": delta_ret_n(fred.get("PAYEMS"), 12, offset=3),
        "cpi_roc_3m": delta_ret_n(fred.get("CPI"), 12, offset=3),
        "core_cpi_roc_3m": delta_ret_n(fred.get("CORECPI"), 12, offset=3),
        "corepce_roc_3m": delta_ret_n(fred.get("COREPCE"), 12, offset=3) if "COREPCE" in fred else float("nan"),
        "ism_3m_delta": delta_n(fred.get("ISMNO"), 3),
        "lei_3m": ret_n(fred.get("LEI"), 3) if "LEI" in fred else float("nan"),
        "m2_3m": ret_n(fred.get("M2SL"), 3) if "M2SL" in fred else float("nan"),
        "fed_bal_3m": ret_n(fred.get("WALCL"), 3) if "WALCL" in fred else float("nan"),
        "oil_3m": ret_n(prices.get("CL=F"), 63),
        "gold_3m": ret_n(prices.get("GC=F"), 63),
        "dxy_3m": ret_n(prices.get("UUP"), 63),
        "oil_1m": ret_n(prices.get("CL=F"), 21),
        "gold_1m": ret_n(prices.get("GC=F"), 21),
        "dxy_1m": ret_n(prices.get("UUP"), 21),
        "spy_1m": ret_n(prices.get("SPY"), 21),
        "xli_1m": ret_n(prices.get("XLI"), 21),
        "xly_1m": ret_n(prices.get("XLY"), 21),
        "iwm_1m": ret_n(prices.get("IWM"), 21),
        "xhb_1m": ret_n(prices.get("XHB"), 21),
        "tlt_1m": ret_n(prices.get("TLT"), 21),
        "eem_1m": ret_n(prices.get("EEM"), 21),
    }

    proxy = _fallback_price_proxy(prices)
    raw_macro_keys = [
        "indpro_yoy",
        "retail_yoy",
        "payrolls_yoy",
        "unrate_3m_delta",
        "claims_13w_delta",
        "ism_last",
        "housing_yoy",
        "cpi_yoy",
        "core_cpi_yoy",
        "breakeven_last",
    ]

    proxy_used = 0
    proxy_used_keys = []
    structural_proxy_keys = ["indpro_yoy", "payrolls_yoy", "ism_last"]

    for k in raw_macro_keys:
        if not np.isfinite(features[k]):
            if k in structural_proxy_keys:
                continue
            if np.isfinite(proxy[k]) and abs(proxy[k]) < 0.50:
                features[k] = proxy[k]
                proxy_used += 1
                proxy_used_keys.append(k)

    if not np.isfinite(features.get("corepce_yoy", float("nan"))):
        features["corepce_yoy"] = features.get("core_cpi_yoy", float("nan"))
    if not np.isfinite(features.get("corepce_roc_3m", float("nan"))):
        features["corepce_roc_3m"] = features.get("core_cpi_roc_3m", float("nan"))

    growth_level_inputs = [
        _scaled(features["indpro_yoy"] - 0.02, 0.05),
        _scaled(features["retail_yoy"] - 0.03, 0.06),
        _scaled(features["payrolls_yoy"] - 0.015, 0.03),
        _scaled(features["housing_yoy"], 0.10),
        _scaled((features["ism_last"] - 50.0) / 100.0, 0.04),
        _scaled(-(features["unrate_3m_delta"]), 0.12),
        _scaled(-(features["claims_13w_delta"] / 40.0), 0.60),
    ]

    growth_mom_inputs = [
        _scaled(features["indpro_roc_3m"], 0.025),
        _scaled(features["retail_roc_3m"], 0.030),
        _scaled(features["payrolls_roc_3m"], 0.012),
        _scaled(features["ism_3m_delta"] / 100.0, 0.04),
        _scaled(-(features["unrate_3m_delta"]), 0.10),
        _scaled(-(features["claims_13w_delta"] / 50.0), 0.50),
        _scaled(features["housing_yoy"], 0.08),
    ]

    inflation_level_inputs = [
        _scaled(features["cpi_yoy"] - 0.025, 0.020),
        _scaled(features["corepce_yoy"] - 0.025, 0.015),
        _scaled((features["breakeven_last"] - 2.2) / 2.0, 0.30),
        _scaled(features["oil_3m"], 0.25),
        _scaled(features["gold_3m"], 0.18),
    ]

    inflation_mom_inputs = [
        _scaled(features["cpi_roc_3m"], 0.012),
        _scaled(features["corepce_roc_3m"], 0.010),
        _scaled(features["breakeven_1m_delta"], 0.08),
        _scaled(features["oil_1m"], 0.06),
        _scaled(-features["dxy_1m"], 0.05),
    ]

    headline_core_gap = float(
        features["cpi_yoy"] - features["corepce_yoy"]
        if np.isfinite(features.get("cpi_yoy"))
        and np.isfinite(features.get("corepce_yoy"))
        else float("nan")
    )

    inflation_shock = _nanmean_or(
        [
            max(0.0, _scaled(features["oil_1m"], 0.06)),
            max(0.0, _scaled(features["gold_1m"], 0.05)),
            max(0.0, _scaled(headline_core_gap, 0.004)),
        ],
        0.0,
    )

    growth_level = _nanmean_or(growth_level_inputs, 0.0)
    growth_momentum = _nanmean_or(growth_mom_inputs, 0.0)
    inflation_level = _nanmean_or(inflation_level_inputs, 0.0)
    inflation_momentum = _nanmean_or(inflation_mom_inputs, 0.0)

    leading_indicator_composite = _nanmean_or(
        [
            _scaled(features["ism_3m_delta"] / 100.0, 0.04),
            _scaled(-(features["claims_13w_delta"] / 50.0), 0.50),
            _scaled(features["breakeven_1m_delta"], 0.08),
            _scaled(features["housing_yoy"], 0.08),
        ],
        0.0,
    )

    slowdown_flags = sum(
        [
            1
            if np.isfinite(features["unrate_3m_delta"])
            and features["unrate_3m_delta"] > 0.05
            else 0,
            1
            if np.isfinite(features["claims_13w_delta"])
            and features["claims_13w_delta"] > 0
            else 0,
            1 if np.isfinite(features["ism_last"]) and features["ism_last"] < 50 else 0,
            1
            if np.isfinite(features["housing_yoy"]) and features["housing_yoy"] < 0
            else 0,
        ]
    ) / 4.0

    liquidity_proxy = _nanmean_or(
        [
            _scaled(-features.get("dxy_3m", float("nan")), 0.12),
            _scaled(features.get("tlt_1m", float("nan")), 0.08),
        ],
        0.0,
    )
    policy_score = _scaled(-features.get("policy_rate_3m_delta", float("nan")), 0.50)
    liquidity_score = _scaled(liquidity_proxy, 0.50)

    data_points = [*growth_level_inputs, *inflation_level_inputs]
    coverage = (
        float(np.mean([1.0 if np.isfinite(x) else 0.0 for x in data_points]))
        if data_points
        else 0.75
    )
    raw_macro_real_share = 1.0 - (proxy_used / max(len(raw_macro_keys), 1))
    fred_real_share = (
        float(fred_meta.get("real_share", raw_macro_real_share))
        if isinstance(fred_meta, dict)
        else raw_macro_real_share
    )
    price_real_share = (
        float(price_meta.get("real_share", 0.0))
        if isinstance(price_meta, dict)
        else 0.0
    )
    macro_proxy_share = float(max(0.0, min(1.0, 1.0 - raw_macro_real_share)))
    macro_real_share = float(max(0.0, min(1.0, raw_macro_real_share)))
    monthly_real_share = float(
        max(
            0.0,
            min(
                1.0,
                np.mean(
                    [
                        1.0
                        if np.isfinite(features.get("oil_1m", float("nan")))
                        else 0.0,
                        1.0
                        if np.isfinite(features.get("gold_1m", float("nan")))
                        else 0.0,
                        1.0
                        if np.isfinite(features.get("dxy_1m", float("nan")))
                        else 0.0,
                        1.0
                        if np.isfinite(features.get("spy_1m", float("nan")))
                        else 0.0,
                        1.0
                        if np.isfinite(features.get("xli_1m", float("nan")))
                        else 0.0,
                        1.0
                        if np.isfinite(features.get("xly_1m", float("nan")))
                        else 0.0,
                        1.0
                        if np.isfinite(features.get("iwm_1m", float("nan")))
                        else 0.0,
                    ]
                ),
            ),
        )
    )
    structural_real_share = float(
        max(0.0, min(1.0, 0.70 * fred_real_share + 0.30 * macro_real_share))
    )
    monthly_data_coverage = float(
        max(
            0.0,
            min(
                1.0,
                0.60 * monthly_real_share
                + 0.25 * price_real_share
                + 0.15 * structural_real_share,
            ),
        )
    )
    data_coverage = float(
        max(0.0, min(1.0, 0.70 * structural_real_share + 0.30 * coverage))
    )
    macro_confidence_penalty = 0.35 * macro_proxy_share + 0.15 * max(
        0.0, 1.0 - fred_real_share
    )

    growth_structural_level = float(np.nan_to_num(growth_level, nan=0.0))
    growth_structural_momentum = float(np.nan_to_num(growth_momentum, nan=0.0))
    inflation_structural_level = float(np.nan_to_num(inflation_level, nan=0.0))
    inflation_structural_momentum = float(np.nan_to_num(inflation_momentum, nan=0.0))

    monthly_growth_signal = _nanmean_or(
        [
            _scaled(features["spy_1m"], 0.05),
            _scaled(features["xli_1m"], 0.05),
            _scaled(features["xly_1m"], 0.05),
            _scaled(features["iwm_1m"], 0.07),
            _scaled(features["xhb_1m"], 0.08),
            _scaled(-features["dxy_1m"], 0.06),
        ],
        0.0,
    )
    monthly_inflation_signal = _nanmean_or(
        [
            _scaled(headline_core_gap, 0.004),
            _scaled(features["oil_1m"], 0.06),
            _scaled(features["gold_1m"], 0.05),
            _scaled(features["breakeven_1m_delta"], 0.08),
            _scaled(-features["dxy_1m"], 0.05),
        ],
        0.0,
    )

    growth_monthly_level = float(
        np.nan_to_num(0.45 * growth_level + 0.55 * growth_momentum, nan=0.0)
    )
    growth_monthly_momentum = float(
        np.nan_to_num(0.35 * growth_momentum + 0.65 * monthly_growth_signal, nan=0.0)
    )
    inflation_monthly_level = float(
        np.nan_to_num(
            0.50 * inflation_level
            + 0.30 * inflation_momentum
            + 0.20 * _scaled(headline_core_gap, 0.004),
            nan=0.0,
        )
    )
    inflation_monthly_momentum = float(
        np.nan_to_num(
            0.35 * inflation_momentum + 0.65 * monthly_inflation_signal, nan=0.0
        )
    )

    monthly_policy_score = float(
        np.nan_to_num(
            0.60 * policy_score
            + 0.40 * _scaled(-features.get("policy_rate_3m_delta", float("nan")), 0.25),
            nan=0.0,
        )
    )
    monthly_liquidity_score = float(
        np.nan_to_num(
            0.50 * liquidity_score + 0.50 * _scaled(liquidity_proxy, 0.35), nan=0.0
        )
    )
    monthly_inflation_shock = float(
        np.nan_to_num(
            _nanmean_or(
                [
                    max(0.0, _scaled(headline_core_gap, 0.004))
                    if np.isfinite(_scaled(headline_core_gap, 0.004))
                    else float("nan"),
                    max(0.0, _scaled(features["oil_1m"], 0.06))
                    if np.isfinite(_scaled(features["oil_1m"], 0.06))
                    else float("nan"),
                    max(0.0, _scaled(features["breakeven_1m_delta"], 0.08))
                    if np.isfinite(_scaled(features["breakeven_1m_delta"], 0.08))
                    else float("nan"),
                ],
                0.0,
            ),
            nan=0.0,
        )
    )

    features.update(
        {
            "growth_level": float(np.nan_to_num(growth_level, nan=0.0)),
            "growth_momentum": float(np.nan_to_num(growth_momentum, nan=0.0)),
            "inflation_level": float(np.nan_to_num(inflation_level, nan=0.0)),
            "inflation_momentum": float(np.nan_to_num(inflation_momentum, nan=0.0)),
            "slowdown_flags": slowdown_flags,
            "inflation_shock": float(np.nan_to_num(inflation_shock, nan=0.0)),
            "leading_indicator_composite": float(
                np.nan_to_num(leading_indicator_composite, nan=0.0)
            ),
            "headline_core_gap": float(np.nan_to_num(headline_core_gap, nan=0.0)),
            "data_coverage_raw": coverage,
            "data_coverage": data_coverage,
            "proxy_used_count": int(proxy_used),
            "proxy_used_keys": proxy_used_keys,
            "macro_proxy_share": float(macro_proxy_share),
            "macro_real_share": float(macro_real_share),
            "fred_real_share": float(max(0.0, min(1.0, fred_real_share))),
            "price_real_share": float(max(0.0, min(1.0, price_real_share))),
            "structural_real_share": float(structural_real_share),
            "monthly_real_share": float(monthly_real_share),
            "monthly_data_coverage": float(monthly_data_coverage),
            "macro_confidence_penalty": float(macro_confidence_penalty),
            "policy_score": float(np.nan_to_num(policy_score, nan=0.0)),
            "liquidity_proxy": float(np.nan_to_num(liquidity_proxy, nan=0.0)),
            "liquidity_score": float(np.nan_to_num(liquidity_score, nan=0.0)),
            "macro_complete": int(
                sum(1 for k in raw_macro_keys if np.isfinite(features.get(k, float("nan"))))
            ),
            "growth_structural_level": growth_structural_level,
            "growth_structural_momentum": growth_structural_momentum,
            "inflation_structural_level": inflation_structural_level,
            "inflation_structural_momentum": inflation_structural_momentum,
            "growth_monthly_level": growth_monthly_level,
            "growth_monthly_momentum": growth_monthly_momentum,
            "inflation_monthly_level": inflation_monthly_level,
            "inflation_monthly_momentum": inflation_monthly_momentum,
            "monthly_policy_score": monthly_policy_score,
            "monthly_liquidity_score": monthly_liquidity_score,
            "monthly_inflation_shock": monthly_inflation_shock,
        }
    )
    return features
