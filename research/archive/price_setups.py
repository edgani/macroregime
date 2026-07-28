"""Descriptive price-context generator.

This module deliberately does *not* emit a trade watch or capital direction.  It creates a
bounded cross-sectional context screen from observed OHLCV so researchers can decide which
instruments deserve market-specific follow-up.  The equal-weight blend is a transparent
operational prior, not a fitted alpha formula, confidence score or probability.
"""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


LIQUIDITY_POLICY: dict[str, dict[str, Any]] = {
    # Operational research-universe floors, not performance-optimised thresholds.
    "us": {"metric": "median_dollar_volume_20", "minimum": 5_000_000.0, "currency": "USD"},
    "idx": {"metric": "median_dollar_volume_20", "minimum": 5_000_000_000.0, "currency": "IDR_NOTIONAL_PROXY"},
    "crypto": {"metric": "median_dollar_volume_20", "minimum": 2_000_000.0, "currency": "USD"},
    "commodity": {"metric": "median_contract_volume_20", "minimum": 1_000.0, "currency": "CONTRACTS"},
    "fx": {"metric": "venue_liquidity", "minimum": None, "currency": "UNKNOWN_WITH_DAILY_SPOT"},
}


def _round_price(value: Any) -> float | None:
    if value is None:
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    a = abs(x)
    digits = 2 if a >= 100 else 4 if a >= 1 else 6 if a >= 0.01 else 8
    return round(x, digits)


def _safe_phase(value: str) -> str:
    x = str(value or "MIXED").upper()
    if x in {"MARKUP", "ACCUMULATION", "ALIGNED_UP", "BULLISH_DIV", "POSITION_BUILDING", "POSITIVE_PRESSURE"}:
        return "POSITIVE_PRICE_VOLUME_CONTEXT"
    if x in {"MARKDOWN", "DISTRIBUTION", "ALIGNED_DOWN", "BEARISH_DIV", "LIQUIDATION", "NEGATIVE_PRESSURE"}:
        return "NEGATIVE_PRICE_VOLUME_CONTEXT"
    if x in {"RANGE", "BALANCED", "NEUTRAL", "FLAT", "MIXED"}:
        return "MIXED_PRICE_CONTEXT"
    return "UNVERIFIED_PRICE_PHASE"


def _market_from_ticker(ticker: str) -> str | None:
    t = str(ticker or "").upper()
    if t.endswith(".JK"):
        return "idx"
    if t.endswith("-USD"):
        return "crypto"
    if t.endswith("=F"):
        return "commodity"
    if t.endswith("=X") or t in {"DX-Y.NYB", "DXY"}:
        return "fx"
    return "us"


def _liquidity_state(market_id: str, dollar_volume: float | None, contract_volume: float | None) -> tuple[str, str]:
    policy = LIQUIDITY_POLICY.get(market_id, {})
    metric = policy.get("metric")
    minimum = policy.get("minimum")
    value = contract_volume if metric == "median_contract_volume_20" else dollar_volume
    if minimum is None:
        return "UNKNOWN", f"{metric} is not available from this daily spot feed"
    if value is None or not np.isfinite(value):
        return "UNKNOWN", f"{metric} missing"
    if value < float(minimum):
        return "BELOW_RESEARCH_FLOOR", f"{metric} {value:.4g} < operational floor {minimum:.4g}"
    return "ELIGIBLE", f"{metric} {value:.4g} >= operational floor {minimum:.4g}"


def _rank_center(series: pd.Series) -> pd.Series:
    """Map cross-sectional percentile to [-1, 1] without fitting a coefficient."""
    return series.rank(pct=True, method="average") * 2.0 - 1.0


def price_signal_setups(ohlcv: dict, top: int = 12, market_id: str | None = None) -> list[dict]:
    """Return unique descriptive price-context rows.

    Selection basis is explicit and deliberately simple:
      * 12-month relative return rank
      * legacy readiness proxy rank (descriptive only)
      * legacy OHLCV score rank (descriptive only)
      * current positive-minus-negative pressure flag

    The four inputs are equal-weighted. They are not assumed independent and the result is not
    a predictive score.  A dead zone prevents small differences from being labelled directional.
    """
    from engines import bandarmetrics_engine as BM
    from engines.inventory_transfer_engine import classify_phase
    from gcfis.engines.entry import run_entry

    raw_rows: list[dict] = []
    for ticker, frame in (ohlcv or {}).items():
        try:
            df = frame.dropna(how="all")
        except Exception:
            continue
        if len(df) < 200 or "Close" not in df:
            continue
        close = pd.to_numeric(df["Close"], errors="coerce").dropna()
        if len(close) < 200:
            continue
        mid = market_id or _market_from_ticker(ticker) or "us"
        rs = float(close.iloc[-1] / close.iloc[-252] - 1.0) if len(close) > 252 else float(close.iloc[-1] / close.iloc[0] - 1.0)
        try:
            bm = BM.compute(df)
            readiness_raw = bm.get("markup_readiness") or {}
            readiness = readiness_raw.get("readiness") if isinstance(readiness_raw, dict) else readiness_raw
            if readiness is None and isinstance(readiness_raw, dict):
                readiness = readiness_raw.get("score")
            positive_pressure = 1.0 if (bm.get("stealth_accumulation") or {}).get("is_stealth") else 0.0
            phase = str(bm.get("phase") or "NEUTRAL").upper()
            divergence = str(bm.get("divergence") or "FLAT").upper()
            bm_score = float(bm.get("score") if bm.get("score") is not None else 50.0)
        except Exception:
            readiness, positive_pressure, phase, divergence, bm_score = None, 0.0, "NEUTRAL", "FLAT", 50.0
        if readiness is None:
            continue
        negative_pressure = 1.0 if phase in {"DISTRIBUTION", "MARKDOWN"} or divergence in {"BEARISH_DIV", "ALIGNED_DOWN"} else 0.0
        try:
            volume = pd.to_numeric(df.get("Volume"), errors="coerce") if "Volume" in df else pd.Series(index=df.index, dtype=float)
            dollar_volume = (pd.to_numeric(df["Close"], errors="coerce") * volume).replace([np.inf, -np.inf], np.nan).dropna()
            median_dollar_volume_20 = float(dollar_volume.tail(20).median()) if len(dollar_volume) else None
            median_contract_volume_20 = float(volume.replace([np.inf, -np.inf], np.nan).dropna().tail(20).median()) if volume.notna().any() else None
        except Exception:
            median_dollar_volume_20 = None
            median_contract_volume_20 = None
        liquidity_state, liquidity_reason = _liquidity_state(mid, median_dollar_volume_20, median_contract_volume_20)
        raw_rows.append({
            "tk": str(ticker).upper(),
            "market": mid,
            "rs": rs,
            "mr": float(readiness),
            "positive_pressure": positive_pressure,
            "negative_pressure": negative_pressure,
            "bm_score": bm_score,
            "close": close,
            "df": df,
            "phase": phase,
            "liquidity_state": liquidity_state,
            "liquidity_reason": liquidity_reason,
            "median_dollar_volume_20": median_dollar_volume_20,
            "median_contract_volume_20": median_contract_volume_20,
        })
    if not raw_rows:
        return []

    ranked = pd.DataFrame(raw_rows)
    ranked["rs_component"] = _rank_center(ranked["rs"])
    ranked["readiness_component"] = _rank_center(ranked["mr"])
    ranked["ohlcv_component"] = _rank_center(ranked["bm_score"])
    ranked["pressure_component"] = ranked["positive_pressure"] - ranked["negative_pressure"]
    component_cols = ["rs_component", "readiness_component", "ohlcv_component", "pressure_component"]
    ranked["context_score"] = ranked[component_cols].mean(axis=1)
    ranked["component_dispersion"] = ranked[component_cols].std(axis=1).fillna(0.0)
    ranked["agreement_count"] = ranked[component_cols].apply(
        lambda r: max(sum(float(x) > 0.15 for x in r), sum(float(x) < -0.15 for x in r)), axis=1
    )
    ranked["selection_priority"] = ranked["liquidity_state"].map({"ELIGIBLE": 2, "UNKNOWN": 1, "BELOW_RESEARCH_FLOOR": 0}).fillna(0)
    ranked = ranked.sort_values(
        ["selection_priority", "agreement_count", "context_score"],
        ascending=[False, False, False],
        key=lambda col: col.abs() if col.name == "context_score" else col,
    ).head(max(2, top))

    out: list[dict] = []
    for _, row in ranked.iterrows():
        score = float(row["context_score"])
        pos_count = sum(float(row[c]) > 0.15 for c in component_cols)
        neg_count = sum(float(row[c]) < -0.15 for c in component_cols)
        # Conservative, non-fitted consensus gate: at least three of four components and the raw
        # 12-month return sign must agree. Two-versus-two and proxy/return disagreement are mixed.
        if pos_count >= 3 and float(row["rs"]) > 0:
            descriptive_direction = "long"
        elif neg_count >= 3 and float(row["rs"]) < 0:
            descriptive_direction = "short"
        else:
            descriptive_direction = "neutral"
        dead_zone = descriptive_direction == "neutral"
        phase_safe = _safe_phase(row["phase"])
        entry = {"valid": False, "entry_px": None, "stop": None, "target": None, "rr": None, "warning": ""}
        phase_info = {"ok": False}
        if descriptive_direction in {"long", "short"}:
            try:
                entry = run_entry(row["close"], descriptive_direction)
            except Exception:
                entry = {"valid": False, "entry_px": None, "stop": None, "target": None, "rr": None, "warning": "entry geometry unavailable"}
            try:
                phase_info = classify_phase(row["df"])
            except Exception:
                phase_info = {"ok": False}

        if dead_zone:
            action = "NO_TRADE_CONFLICTED"
            why = f"mixed price context; fewer than 3/4 components agree with the raw 12-month return sign (score {score:+.2f})"
        elif descriptive_direction == "long":
            action = "POSITIVE_PRICE_CONTEXT"
            why = f"positive descriptive context; 12M return {row['rs']*100:+.1f}%"
        else:
            action = "NEGATIVE_PRICE_CONTEXT"
            why = f"negative descriptive context; 12M return {row['rs']*100:+.1f}%"
        if row["liquidity_state"] == "BELOW_RESEARCH_FLOOR":
            action = "LOW_LIQUIDITY_CONTEXT_ONLY"
        why += f" · {phase_safe} · {row['liquidity_reason']}"

        rr = float(entry.get("rr")) if entry.get("rr") is not None else None
        execution_geometry = bool(entry.get("entry_px") is not None and entry.get("stop") is not None)
        execution_state = "REFERENCE_GEOMETRY_ONLY"
        if rr is not None and rr < 1.5:
            execution_state = "NO_TRADE_POOR_RR"
        elif not execution_geometry:
            execution_state = "NO_EXECUTABLE_GEOMETRY"
        elif row["liquidity_state"] != "ELIGIBLE":
            execution_state = "LIQUIDITY_NOT_CLEARED"

        setup_rank_pct = round(min(100.0, abs(score) * 100.0), 2)
        out.append({
            "tk": row["tk"],
            "market": row["market"],
            "act": action,
            "dir": descriptive_direction,
            "orientation_semantics": "DESCRIPTIVE_PRICE_CONTEXT_NOT_TRADE_DIRECTION",
            "setup_rank": setup_rank_pct,
            "conv": setup_rank_pct,  # backward-compatible field; UI must label it SETUP RANK.
            "e": _round_price(entry.get("entry_px")),
            "s": _round_price(entry.get("stop")),
            "t": _round_price(entry.get("target")),
            "rr": round(rr, 2) if rr is not None else None,
            "ty": "GENERIC_PRICE_CONTEXT",
            "valid": False,
            "directional_permission": False,
            "capital_permission": "BLOCKED",
            "claim_state": "DESCRIPTIVE_CONTROL",
            "execution_state": execution_state,
            "warn": entry.get("warning", ""),
            "phase": phase_safe,
            "phase_conf": phase_info.get("confidence") if phase_info.get("ok") else None,
            "why": why,
            "conflicted": dead_zone,
            "context_score": round(score, 4),
            "agreement_count": int(max(pos_count, neg_count)),
            "component_dispersion": round(float(row["component_dispersion"]), 4),
            "components": {
                "relative_return_rank": round(float(row["rs_component"]), 4),
                "readiness_proxy_rank": round(float(row["readiness_component"]), 4),
                "ohlcv_proxy_rank": round(float(row["ohlcv_component"]), 4),
                "pressure_flag": round(float(row["pressure_component"]), 4),
            },
            "liquidity_state": row["liquidity_state"],
            "liquidity_reason": row["liquidity_reason"],
            "median_dollar_volume_20": row.get("median_dollar_volume_20"),
            "median_contract_volume_20": row.get("median_contract_volume_20"),
            "evidence_dimensions": {
                "data_coverage": "OHLCV_ONLY",
                "setup_quality": "RELATIVE_RANK_ONLY",
                "thesis_evidence": "MISSING",
                "model_validation": "DESCRIPTIVE_ONLY",
                "execution_readiness": execution_state,
                "prospective_evidence": "MISSING",
            },
            "ranking_basis": "EQUAL_WEIGHT_FOUR_DESCRIPTIVE_COMPONENTS_WITH_DEAD_ZONE; NOT FITTED, NOT INDEPENDENT, NOT PREDICTIVE",
            "evidence_semantics": "DESCRIPTIVE_PRICE_CONTEXT_ONLY; not probability, ownership, intent, alpha proof or capital permission.",
        })

    out.sort(key=lambda x: (
        {"ELIGIBLE": 2, "UNKNOWN": 1, "BELOW_RESEARCH_FLOOR": 0}.get(str(x.get("liquidity_state")), 0),
        int(x.get("agreement_count") or 0),
        float(x.get("setup_rank") or 0.0),
    ), reverse=True)
    return out[: max(2, top)]
