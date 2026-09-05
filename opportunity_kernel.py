from __future__ import annotations

import json
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd


def _f(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, float(x))) if math.isfinite(_f(x)) else math.nan


@dataclass(frozen=True)
class FeatureSpec:
    name: str
    direction: int = 1           # +1 = higher is opportunity-positive, -1 = lower is positive
    family: str = "generic"
    hard_veto: bool = False


@dataclass
class ChangeReading:
    feature: str
    family: str
    current: float
    baseline_median: float
    robust_z: float
    delta: float
    velocity: float
    acceleration: float
    persistence: float
    novelty: float
    direction: int

    def signed_strength(self) -> float:
        z = self.robust_z * self.direction if math.isfinite(self.robust_z) else 0.0
        v = self.velocity * self.direction if math.isfinite(self.velocity) else 0.0
        a = self.acceleration * self.direction if math.isfinite(self.acceleration) else 0.0
        # z dominates; derivative terms only add bounded confirmation.
        return float(np.tanh(z / 3.0) + 0.30 * np.tanh(v) + 0.20 * np.tanh(a))


def robust_change_reading(history: Sequence[float], spec: FeatureSpec) -> ChangeReading:
    """PIT-safe descriptive change measurement.

    The last observation is treated as 'now'. Earlier observations form the baseline.
    This function does not forecast returns and does not use future observations.
    """
    s = pd.to_numeric(pd.Series(list(history)), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    cur = _f(s.iloc[-1]) if len(s) else math.nan
    if len(s) < 4:
        return ChangeReading(spec.name, spec.family, cur, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, math.nan, spec.direction)
    base = s.iloc[:-1]
    med = float(base.median())
    mad = float((base - med).abs().median())
    scale = 1.4826 * mad
    if not math.isfinite(scale) or scale <= 1e-12:
        std = float(base.std(ddof=1)) if len(base) >= 2 else math.nan
        scale = std if math.isfinite(std) and std > 1e-12 else math.nan
    rz = (cur - med) / scale if math.isfinite(scale) else 0.0
    d = s.diff()
    velocity = _f(d.iloc[-1])
    prev_v = _f(d.iloc[-2]) if len(d) >= 2 else math.nan
    accel = velocity - prev_v if math.isfinite(velocity) and math.isfinite(prev_v) else math.nan
    # Normalize derivatives to robust scale so cross-feature magnitudes are comparable.
    if math.isfinite(scale) and scale > 0:
        velocity = velocity / scale if math.isfinite(velocity) else math.nan
        accel = accel / scale if math.isfinite(accel) else math.nan
    recent = s.iloc[-min(5, len(s)):]
    if len(recent) >= 2:
        signs = np.sign(recent.diff().dropna().to_numpy(dtype=float)) * int(spec.direction)
        persistence = float((signs > 0).mean()) if len(signs) else math.nan
    else:
        persistence = math.nan
    novelty = min(1.0, abs(rz) / 3.0) if math.isfinite(rz) else math.nan
    return ChangeReading(spec.name, spec.family, cur, med, rz, _f(cur - _f(s.iloc[-2])), velocity, accel, persistence, novelty, spec.direction)


def aggregate_change(readings: Sequence[ChangeReading]) -> Dict[str, Any]:
    usable = [r for r in readings if math.isfinite(r.robust_z)]
    if not usable:
        return {
            "change_score": math.nan,
            "change_state": "BASELINE BUILDING",
            "change_breadth": math.nan,
            "change_persistence": math.nan,
            "change_acceleration": math.nan,
            "feature_count": 0,
        }
    strengths = np.array([r.signed_strength() for r in usable], dtype=float)
    positive = strengths > 0.35
    breadth = float(positive.mean())
    pers = [r.persistence for r in usable if math.isfinite(r.persistence)]
    acc = [r.acceleration * r.direction for r in usable if math.isfinite(r.acceleration)]
    core = 50.0 + 35.0 * float(np.tanh(np.median(strengths)))
    core += 10.0 * (breadth - 0.5)
    score = _clamp(core)
    p = float(np.mean(pers)) if pers else math.nan
    a = float(np.median(acc)) if acc else math.nan
    if score >= 78 and breadth >= 0.50:
        state = "ACCELERATING" if math.isfinite(a) and a > 0.15 else "EMERGING"
    elif score >= 62:
        state = "UNUSUAL"
    elif score <= 35:
        state = "DETERIORATING"
    else:
        state = "QUIET / NORMAL"
    return {
        "change_score": score,
        "change_state": state,
        "change_breadth": breadth,
        "change_persistence": p,
        "change_acceleration": a,
        "feature_count": len(usable),
    }


def infer_hype_state(change_state: str, *, quality_state: str = "UNKNOWN", crowding: float = math.nan) -> str:
    c = str(change_state).upper()
    q = str(quality_state).upper()
    crowd = _f(crowding)
    if math.isfinite(crowd) and crowd >= 80:
        return "CROWDED"
    if "DETERIOR" in c:
        return "DECAY"
    if "ACCELERAT" in c:
        return "VALIDATED" if q in {"HIGH", "PASS", "VALIDATED"} else "ACCELERATING"
    if "EMERGING" in c or "UNUSUAL" in c:
        return "EMERGING"
    if "BASELINE" in c:
        return "BASELINE BUILDING"
    return "QUIET"


def sequence_signature(states: Sequence[str], max_states: int = 8) -> str:
    """Compress consecutive duplicate states; preserves order, which is the intended edge hypothesis."""
    clean: List[str] = []
    for raw in states:
        s = str(raw or "").strip().upper()
        if not s:
            continue
        if not clean or clean[-1] != s:
            clean.append(s)
    return " → ".join(clean[-max_states:]) if clean else "NO HISTORY"


def earliness_from_components(*, attention_pct: float = math.nan, leverage_pct: float = math.nan,
                              price_discovery_pct: float = math.nan, participation_pct: float = math.nan) -> Dict[str, Any]:
    """Descriptive saturation/earliness; missing components stay missing rather than being imputed bullish."""
    vals = [_f(attention_pct), _f(leverage_pct), _f(price_discovery_pct), _f(participation_pct)]
    vals = [v for v in vals if math.isfinite(v)]
    if not vals:
        return {"earliness_score": math.nan, "crowding_score": math.nan, "earliness_state": "DATA GATED"}
    crowd = _clamp(100.0 * float(np.mean(vals)))
    early = _clamp(100.0 - crowd)
    state = "EARLY" if early >= 70 else ("MID" if early >= 40 else "LATE / CROWDED")
    return {"earliness_score": early, "crowding_score": crowd, "earliness_state": state}


VERTICAL_REQUIREMENTS: Dict[str, Dict[str, Tuple[str, ...]]] = {
    "On-chain": {
        "core": ("wallet_activity", "liquidity", "usage", "ecosystem", "quality", "memory"),
        "optional": ("social", "narrative", "developer_activity"),
    },
    "Crypto": {
        "core": ("spot_flow", "open_interest", "funding", "liquidations", "liquidity", "memory"),
        "optional": ("onchain_confirmation", "options", "narrative"),
    },
    "US": {
        "core": ("fundamentals", "estimate_revisions", "capital_flow", "causal_chain", "valuation", "memory"),
        "optional": ("options", "narrative", "macro", "expectation_optionality"),
    },
    "IHSG": {
        "core": ("fundamentals", "broker_flow", "foreign_flow", "corporate_actions", "valuation", "memory"),
        "optional": ("order_book", "commodity_link", "macro", "narrative_optionality"),
    },
    "FX": {
        "core": ("relative_rates", "macro_surprise", "central_bank", "positioning", "valuation", "memory"),
        "optional": ("options", "event_response", "cross_asset"),
    },
    "Commodity": {
        "core": ("supply", "demand", "inventory", "curve", "positioning", "memory"),
        "optional": ("shipping", "weather", "macro", "geopolitics"),
    },
}


def vertical_readiness(market: str, available_families: Iterable[str]) -> Dict[str, Any]:
    key = "On-chain" if str(market).lower() in {"onchain", "on-chain"} else str(market)
    req = VERTICAL_REQUIREMENTS.get(key, {"core": tuple(), "optional": tuple()})
    have = {str(x) for x in available_families}
    core = list(req.get("core", ()))
    missing = [x for x in core if x not in have]
    coverage = (len(core) - len(missing)) / len(core) if core else 0.0
    return {
        "vertical": key,
        "core_coverage": coverage,
        "missing_core": missing,
        "status": "READY" if not missing else ("PARTIAL" if coverage >= 0.5 else "GATED"),
    }
