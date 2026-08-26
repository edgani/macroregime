from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd


def safe_float(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else float('nan')
    except Exception:
        return float('nan')


def clamp(x: float, lo: float, hi: float) -> float:
    if not math.isfinite(x):
        return float('nan')
    return max(lo, min(hi, x))


def neutral_percentile_rank(values: Sequence[float], value: float) -> float:
    """Tie-neutral empirical percentile using mid-rank.

    Identical peers map to 0.50 rather than all mapping to 1.00.  This avoids
    manufacturing extreme evidence from ties.
    """
    x = pd.to_numeric(pd.Series(list(values)), errors="coerce").replace([np.inf, -np.inf], np.nan).dropna()
    if x.empty or not math.isfinite(safe_float(value)):
        return float('nan')
    v = float(value)
    below = float((x < v).sum())
    equal = float((x == v).sum())
    return (below + 0.5 * equal) / float(len(x))


def _macro_risk_off(macro: Dict[str, Any]) -> bool:
    label = str(macro.get("action_label", "")).upper()
    crash = str(macro.get("crash_state", "")).upper()
    return any(k in label for k in ("DEFENSIVE", "CRISIS", "MACRO GATED")) or "CRASH DANGER" in crash


def _data_quality_score(q: Any) -> int:
    return {"HIGH": 2, "MEDIUM": 1, "LOW": 0}.get(str(q).upper(), 0)


def compute_revision_edge(
    *, current_price: float, current_fv: float, prior_price: float = np.nan, prior_fv: float = np.nan
) -> Dict[str, float]:
    """Compare fair-value revision with the price already paid for that new information."""
    cp, cf, pp, pf = map(safe_float, (current_price, current_fv, prior_price, prior_fv))
    pr = cp / pp - 1.0 if math.isfinite(cp) and math.isfinite(pp) and pp > 0 else np.nan
    fr = cf / pf - 1.0 if math.isfinite(cf) and math.isfinite(pf) and pf > 0 else np.nan
    edge = fr - pr if math.isfinite(fr) and math.isfinite(pr) else np.nan
    return {"price_revision": pr, "fair_value_revision": fr, "revision_edge": edge}


def entry_decision(
    row: Dict[str, Any],
    valuation: Optional[Dict[str, Any]] = None,
    macro: Optional[Dict[str, Any]] = None,
    prior_checkpoint: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Detection -> entry policy.  Detection is intentionally NOT an entry signal.

    The policy is conservative and fail-closed.  It is not a calibrated alpha model;
    it is a production-safety contract until real PIT/OOS validation is available.
    """
    valuation = valuation or {}
    macro = macro or {}
    prior_checkpoint = prior_checkpoint or {}

    market = str(row.get("market", ""))
    research_action = str(row.get("research_action", "WATCH")).upper()
    model_status = str(row.get("market_model_status", "")).upper()
    quality = str(row.get("data_quality", "LOW")).upper()
    ev = int(safe_float(row.get("evidence_families")) if math.isfinite(safe_float(row.get("evidence_families"))) else 0)
    det = int(safe_float(row.get("deterioration_families")) if math.isfinite(safe_float(row.get("deterioration_families"))) else 0)
    price = safe_float(row.get("price"))
    fv = safe_float(valuation.get("fv_base"))
    gap = safe_float(valuation.get("expectation_gap"))
    vconf = str(valuation.get("valuation_confidence", row.get("valuation_confidence", "GATED"))).upper()

    prior_price = safe_float(prior_checkpoint.get("price"))
    prior_fv = safe_float(prior_checkpoint.get("fv_base"))
    rev = compute_revision_edge(current_price=price, current_fv=fv, prior_price=prior_price, prior_fv=prior_fv)

    reasons: List[str] = []
    gates: List[str] = []
    stage = "DISCOVER"
    action = "WATCH · EARLY DETECTION IS NOT ENTRY"
    allocation = "0%"

    if det >= 3 or any(k in research_action for k in ("SELL", "SHORT", "BEARISH", "AVOID")):
        return {
            "entry_stage": "EXIT / SHORT RESEARCH",
            "entry_action": "DO NOT START LONG",
            "allocation_guide": "0% long",
            "reasons": ["deterioration / bearish evidence dominates"],
            "gates": [],
            **rev,
        }

    if market in ("FX", "Commodity") and "RESEARCH READY" not in model_status:
        gates.append("dedicated asset-class causal model incomplete")
    if market == "Crypto" and "RESEARCH READY" not in model_status:
        gates.append("usage / holder capture / dilution evidence incomplete")
    if market in ("US", "IHSG") and (vconf == "GATED" or not math.isfinite(gap)):
        gates.append("valuation / expectation-gap evidence incomplete")
    if _data_quality_score(quality) == 0:
        gates.append("data quality low")

    if gates:
        return {
            "entry_stage": stage,
            "entry_action": action,
            "allocation_guide": allocation,
            "reasons": reasons,
            "gates": gates,
            **rev,
        }

    # For stocks, asymmetry is expectation-gap based. For other ready models, the research action
    # is the directional contract until a dedicated fair-value model exists.
    stock_like = market in ("US", "IHSG")
    attractive_gap = math.isfinite(gap) and gap >= 0.20
    exceptional_gap = math.isfinite(gap) and gap >= 0.35
    direction_ok = any(k in research_action for k in ("BUILD", "SELECTIVE ADD", "HOLD"))

    if ev >= 2 and direction_ok and (exceptional_gap if stock_like else True):
        stage = "STARTER"
        action = "STARTER ONLY · BUY INFORMATION, NOT FULL SIZE"
        allocation = "~15–30% of intended position"
        reasons.append("early asymmetry is large enough to justify a small information-paying position")

    if ev >= 3 and direction_ok and (attractive_gap if stock_like else True) and quality == "HIGH":
        stage = "CORE"
        action = "BUILD CORE"
        allocation = "~50–70% of intended position"
        reasons.append("causal/fundamental confirmation is stronger and data quality is high")

    # Add only if the new economics are at least keeping pace with the price paid.
    if stage == "CORE" and ev >= 4:
        edge = safe_float(rev.get("revision_edge"))
        if math.isfinite(edge):
            if edge >= -0.02:
                stage = "ADD"
                action = "ADD / COMPLETE POSITION"
                allocation = "up to intended full size"
                reasons.append("fair-value revision is keeping pace with or outrunning price")
            elif edge <= -0.15:
                stage = "NO CHASE"
                action = "HOLD / NO CHASE"
                allocation = "do not add"
                reasons.append("price has outrun fair-value revision")
        else:
            reasons.append("no prior checkpoint yet; keep CORE rather than auto-add")

    if _macro_risk_off(macro) and stage in ("CORE", "ADD"):
        # Thesis may remain valid, but macro changes sizing/expression.
        stage = "CORE · MACRO SIZED DOWN"
        action = "BUILD SMALLER / NO LEVERAGE"
        allocation = "cap below normal full size"
        reasons.append("macro/crash gate is defensive")

    if stage == "DISCOVER" and ev >= 2:
        reasons.append("interesting evidence exists but entry asymmetry/confirmation is not sufficient")

    return {
        "entry_stage": stage,
        "entry_action": action,
        "allocation_guide": allocation,
        "reasons": reasons,
        "gates": gates,
        **rev,
    }


def expression_decision(
    row: Dict[str, Any],
    entry: Dict[str, Any],
    macro: Optional[Dict[str, Any]] = None,
    option: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Choose expression after thesis + entry are earned. Never use option/leverage as discovery."""
    macro = macro or {}
    option = option or {}
    market = str(row.get("market", ""))
    stage = str(entry.get("entry_stage", "DISCOVER")).upper()
    research_action = str(row.get("research_action", "")).upper()
    status = str(row.get("market_model_status", "")).upper()
    q = str(row.get("data_quality", "LOW")).upper()
    ev = int(safe_float(row.get("evidence_families")) if math.isfinite(safe_float(row.get("evidence_families"))) else 0)

    if market == "IHSG":
        return {"best_expression": "CASH STOCK ONLY", "leverage_allowed": False, "option_allowed": False, "why": "IHSG product contract is cash ownership only"}

    if any(k in stage for k in ("DISCOVER", "NO CHASE")):
        return {"best_expression": "WATCH / CASH", "leverage_allowed": False, "option_allowed": False, "why": "entry not earned or price already outran fair value"}

    bearish = any(k in research_action for k in ("SHORT", "SELL", "BEARISH"))
    direction = "SHORT" if bearish else "LONG"
    leverage_ready = q == "HIGH" and ev >= 3 and "RESEARCH READY" in status and not (_macro_risk_off(macro) and direction == "LONG")

    # US model_status may be RESEARCH READY / FUNDAMENTALS; crypto requires its own ready status.
    if market == "US" and q == "HIGH" and ev >= 3:
        leverage_ready = not (_macro_risk_off(macro) and direction == "LONG")

    if market in ("FX", "Commodity") and "RESEARCH READY" not in status:
        leverage_ready = False

    option_allowed = False
    option_why = "option market/model not ready"
    if market == "US" or (market == "Crypto" and str(row.get("symbol", "")).upper() in ("BTC-USD", "ETH-USD")):
        err = option.get("error")
        liq = str(option.get("liquidity", "")).upper()
        spread = safe_float(option.get("spread"))
        iv = safe_float(option.get("iv"))
        implied_move = safe_float(option.get("implied_move"))
        # If no option snapshot is supplied, report adapter-eligible but not selected.
        if option:
            option_allowed = not err and (liq in ("GOOD", "OK", "HIGH") or (math.isfinite(spread) and spread <= 0.12)) and math.isfinite(iv)
            option_why = "liquid listed option passes basic IV/spread gate" if option_allowed else "live option liquidity/IV gate failed"
        else:
            option_why = "listed-option eligible; live IV/liquidity check required"

    if option_allowed:
        return {"best_expression": "PUT / DEFINED-RISK" if bearish else "CALL / DEFINED-RISK", "leverage_allowed": leverage_ready, "option_allowed": True, "why": option_why}
    if leverage_ready:
        return {"best_expression": "LEVERAGED SHORT" if bearish else "LEVERAGED LONG", "leverage_allowed": True, "option_allowed": False, "why": "causal/data/macro gates earned; option gate not superior/available"}
    return {"best_expression": "SPOT / STOCK", "leverage_allowed": False, "option_allowed": False, "why": option_why if (market == "US" or market == "Crypto") else "cash expression is safer until dedicated leverage model is ready"}


def state_dir(default_root: Optional[Path] = None) -> Path:
    env = os.environ.get("OIE_STATE_DIR", "").strip()
    p = Path(env) if env else (default_root or Path(__file__).resolve().parent / "state")
    p.mkdir(parents=True, exist_ok=True)
    return p


def checkpoint_path(default_root: Optional[Path] = None) -> Path:
    return state_dir(default_root) / "entry_memory.json"


def load_checkpoints(default_root: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    p = checkpoint_path(default_root)
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def get_prior_checkpoint(symbol: str, default_root: Optional[Path] = None) -> Dict[str, Any]:
    rec = load_checkpoints(default_root).get(str(symbol), {})
    if isinstance(rec, dict) and isinstance(rec.get("previous"), dict) and rec.get("previous"):
        return rec["previous"]
    return rec if isinstance(rec, dict) else {}


def save_checkpoint(symbol: str, *, price: float, fv_base: float, entry_stage: str, default_root: Optional[Path] = None) -> None:
    p = checkpoint_path(default_root)
    data = load_checkpoints(default_root)
    sym = str(symbol)
    old = data.get(sym, {}) if isinstance(data.get(sym, {}), dict) else {}
    new_price, new_fv = safe_float(price), safe_float(fv_base)
    previous = old.get("previous", {}) if isinstance(old.get("previous", {}), dict) else {}
    if old and (safe_float(old.get("price")) != new_price or safe_float(old.get("fv_base")) != new_fv):
        previous = {k: old.get(k) for k in ("price", "fv_base", "entry_stage", "updated_at_utc")}
    data[sym] = {
        "price": new_price,
        "fv_base": new_fv,
        "entry_stage": str(entry_stage),
        "updated_at_utc": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "previous": previous,
    }
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, allow_nan=True), encoding="utf-8")
    tmp.replace(p)


def earliest_executable_timestamp(
    published_at: datetime,
    *,
    market_timezone: str = "America/New_York",
    regular_open_hour: int = 9,
    regular_open_minute: int = 30,
    regular_close_hour: int = 16,
) -> datetime:
    """Conservative regular-session execution clock.

    This intentionally handles weekends but not exchange holidays. Historical PIT pipelines should
    replace it with an exchange calendar when one is available.
    """
    tz = ZoneInfo(market_timezone)
    dt = published_at if published_at.tzinfo else published_at.replace(tzinfo=tz)
    dt = dt.astimezone(tz)

    def next_weekday(d: datetime) -> datetime:
        d = d + timedelta(days=1)
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d

    open_dt = dt.replace(hour=regular_open_hour, minute=regular_open_minute, second=0, microsecond=0)
    close_dt = dt.replace(hour=regular_close_hour, minute=0, second=0, microsecond=0)
    if dt.weekday() >= 5:
        d = dt
        while d.weekday() >= 5:
            d += timedelta(days=1)
        return d.replace(hour=regular_open_hour, minute=regular_open_minute, second=0, microsecond=0)
    if dt < open_dt:
        return open_dt
    if dt >= close_dt:
        d = next_weekday(dt)
        return d.replace(hour=regular_open_hour, minute=regular_open_minute, second=0, microsecond=0)
    return dt


def purged_walkforward_splits(
    n: int, *, train_size: int, test_size: int, embargo: int = 0, step: Optional[int] = None
) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Rolling walk-forward splits with an explicit embargo between train and test."""
    if min(n, train_size, test_size) <= 0 or embargo < 0:
        raise ValueError("invalid split sizes")
    step = test_size if step is None else int(step)
    if step <= 0:
        raise ValueError("step must be positive")
    out: List[Tuple[np.ndarray, np.ndarray]] = []
    train_start = 0
    while True:
        train_end = train_start + train_size
        test_start = train_end + embargo
        test_end = test_start + test_size
        if test_end > n:
            break
        out.append((np.arange(train_start, train_end), np.arange(test_start, test_end)))
        train_start += step
    return out


def assert_no_lookahead(train_idx: Iterable[int], test_idx: Iterable[int], embargo: int = 0) -> None:
    tr = list(train_idx); te = list(test_idx)
    if not tr or not te:
        raise AssertionError("empty split")
    if max(tr) + embargo >= min(te):
        raise AssertionError("train/test overlap or embargo violation")
