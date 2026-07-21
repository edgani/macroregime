"""Price-context setup generator.

Generates one descriptive directional research state per instrument from observed OHLCV.
The caller still owns market-direction alignment and long-only rules (IHSG). Scores are
ranking context, never calibrated probabilities or institutional-intent claims.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _round_price(value):
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
    if x in {"MARKUP", "ACCUMULATION", "ALIGNED_UP", "BULLISH_DIV", "POSITION_BUILDING"}:
        return "POSITIVE_PRESSURE"
    if x in {"MARKDOWN", "DISTRIBUTION", "ALIGNED_DOWN", "BEARISH_DIV", "LIQUIDATION"}:
        return "NEGATIVE_PRESSURE"
    if x in {"RANGE", "BALANCED", "NEUTRAL", "FLAT"}:
        return "MIXED"
    return "UNVERIFIED_PRICE_PHASE"


def price_signal_setups(ohlcv, top=12):
    """Return bounded, unique per-instrument price-context candidates.

    Long and short scores are computed symmetrically, but only the stronger side is retained.
    When the score gap is small the instrument is explicitly NO_TRADE rather than appearing
    twice with contradictory rows.
    """
    from engines import bandarmetrics_engine as BM
    from gcfis.engines.entry import run_entry
    from engines.inventory_transfer_engine import classify_phase

    rows = []
    for tk, frame in (ohlcv or {}).items():
        try:
            df = frame.dropna()
        except Exception:
            continue
        if len(df) < 200 or "Close" not in df:
            continue
        c = pd.to_numeric(df["Close"], errors="coerce").dropna()
        if len(c) < 200:
            continue
        rs = float(c.iloc[-1] / c.iloc[-252] - 1) if len(c) > 252 else float(c.iloc[-1] / c.iloc[0] - 1)
        try:
            bm = BM.compute(df)
            mr = bm.get("markup_readiness") or {}
            readiness = mr.get("readiness") if isinstance(mr, dict) else mr
            if readiness is None and isinstance(mr, dict):
                readiness = mr.get("score")
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
            vol = pd.to_numeric(df.get("Volume"), errors="coerce") if "Volume" in df else pd.Series(index=df.index, dtype=float)
            dollar_volume = (pd.to_numeric(df["Close"], errors="coerce") * vol).replace([np.inf, -np.inf], np.nan).dropna()
            median_dollar_volume_20 = float(dollar_volume.tail(20).median()) if len(dollar_volume) else None
        except Exception:
            median_dollar_volume_20 = None
        rows.append({
            "tk": tk, "rs": rs, "mr": float(readiness), "positive_pressure": positive_pressure,
            "negative_pressure": negative_pressure, "bm_score": bm_score, "c": c, "df": df,
            "phase": phase, "median_dollar_volume_20": median_dollar_volume_20,
        })
    if not rows:
        return []

    ranked = pd.DataFrame(rows)
    ranked["long_score"] = (
        0.40 * ranked["mr"].rank(pct=True)
        + 0.35 * ranked["rs"].rank(pct=True)
        + 0.15 * ranked["positive_pressure"]
        + 0.10 * ranked["bm_score"].rank(pct=True)
    )
    ranked["short_score"] = (
        0.40 * (-ranked["rs"]).rank(pct=True)
        + 0.25 * (-ranked["bm_score"]).rank(pct=True)
        + 0.20 * ranked["negative_pressure"]
        + 0.15 * (-ranked["mr"]).rank(pct=True)
    )
    ranked["score_gap"] = (ranked["long_score"] - ranked["short_score"]).abs()
    ranked["selection_score"] = 0.7 * ranked["score_gap"] + 0.3 * ranked[["long_score", "short_score"]].max(axis=1)
    ranked = ranked.sort_values("selection_score", ascending=False).head(max(2, top))

    out = []
    for _, row in ranked.iterrows():
        long_score = float(row["long_score"])
        short_score = float(row["short_score"])
        gap = abs(long_score - short_score)
        conflicted = gap < 0.08
        direction = "neutral" if conflicted else ("long" if long_score > short_score else "short")
        phase_safe = _safe_phase(row["phase"])
        e = {"valid": False, "entry_px": None, "stop": None, "target": None, "rr": None, "gamma_regime": "", "warning": ""}
        phase_info = {"ok": False}
        if direction in {"long", "short"}:
            e = run_entry(row["c"], direction)
            try:
                phase_info = classify_phase(row["df"])
            except Exception:
                phase_info = {"ok": False}
        valid = bool(e.get("valid", False)) and not conflicted
        if conflicted:
            act = "NO_TRADE"
            rationale = f"mixed price-pressure context · long/short score gap {round(gap * 100)} points"
        elif direction == "long":
            act = "BUILD_LONG" if valid else "WATCH_LONG"
            rationale = f"positive price-pressure proxy {round(row['mr'])} · 12M RS {round(row['rs'] * 100)}%"
        else:
            act = "BUILD_SHORT" if valid else "WATCH_SHORT"
            rationale = f"negative price-pressure proxy {round(100 - row['mr'])} · 12M RS {round(row['rs'] * 100)}%"
        rationale += f" · {phase_safe}"
        out.append({
            "tk": row["tk"], "act": act, "dir": direction,
            "conv": round(max(long_score, short_score) * 100),
            "e": _round_price(e.get("entry_px")),
            "s": _round_price(e.get("stop")),
            "t": _round_price(e.get("target")),
            "rr": round(float(e.get("rr")), 2) if e.get("rr") is not None else None,
            "ty": "PRICE-CONTEXT", "gm": e.get("gamma_regime", ""), "valid": valid,
            "warn": e.get("warning", ""), "phase": phase_safe,
            "phase_conf": phase_info.get("confidence") if phase_info.get("ok") else None,
            "why": rationale, "conflicted": conflicted,
            "long_score": round(long_score * 100, 2), "short_score": round(short_score * 100, 2),
            "score_gap": round(gap * 100, 2),
            "median_dollar_volume_20": row.get("median_dollar_volume_20"),
            "evidence_semantics": "DESCRIPTIVE_PRICE_CONTEXT_ONLY; not ownership, institutional intent, or calibrated probability.",
        })

    out.sort(key=lambda x: float(x.get("conv") or 0), reverse=True)
    return out[: max(2, top)]
