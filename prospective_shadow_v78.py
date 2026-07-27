"""V7.8 append-only prospective forecast and outcome ledgers.

Unlike the V6.6 prototype, V7.8 rejects stale/backfilled creation timestamps, freezes the
outcome definition before maturity, and stores outcomes in a separate hash chain.  Neither
ledger can grant capital permission.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
import hashlib
import json
import math
import os
import uuid

FORECAST_SCHEMA = "warroom.v78.prospective_forecast.v1"
OUTCOME_SCHEMA = "warroom.v78.prospective_outcome.v1"
GENESIS = "0" * 64
ZERO_CAPITAL = "SHADOW_ONLY_ZERO_CAPITAL"
ALLOWED_ORIENTATIONS = {"LONG", "SHORT", "NEUTRAL", "RISK_REDUCE", "NO_ACTION"}
ALLOWED_MARKETS = {"US", "IHSG", "FX", "COMMODITY", "CRYPTO", "CROSS_MARKET"}


def _canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_utc(value: str, name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception as exc:
        raise ValueError(f"{name} must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{name} must include timezone")
    return parsed.astimezone(timezone.utc)


def _valid_sha(value: str, name: str) -> str:
    text = str(value or "").lower()
    if len(text) != 64 or any(ch not in "0123456789abcdef" for ch in text):
        raise ValueError(f"{name} must be SHA-256 hex")
    return text


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception as exc:
            raise ValueError(f"invalid JSON at {path}:{line_number}: {exc}") from exc
    return rows


def _append(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)


def _verify_chain(path: Path, schema: str, id_field: str) -> dict[str, Any]:
    try:
        rows = _load(path)
    except Exception as exc:
        return {"valid": False, "rows": 0, "error": str(exc)}
    previous = GENESIS
    ids: set[str] = set()
    for line, row in enumerate(rows, 1):
        if row.get("schema") != schema:
            return {"valid": False, "rows": len(rows), "error": f"schema mismatch line {line}"}
        row_id = str(row.get(id_field) or "")
        if not row_id or row_id in ids:
            return {"valid": False, "rows": len(rows), "error": f"missing/duplicate {id_field} line {line}"}
        ids.add(row_id)
        if row.get("previous_hash") != previous:
            return {"valid": False, "rows": len(rows), "error": f"chain mismatch line {line}"}
        if row.get("capital_permission") != ZERO_CAPITAL:
            return {"valid": False, "rows": len(rows), "error": f"capital violation line {line}"}
        claimed = row.get("row_hash")
        unsigned = dict(row)
        unsigned.pop("row_hash", None)
        actual = hashlib.sha256(_canonical(unsigned)).hexdigest()
        if claimed != actual:
            return {"valid": False, "rows": len(rows), "error": f"row hash mismatch line {line}"}
        previous = claimed
    return {"valid": True, "rows": len(rows), "head_hash": previous}


def verify_forecast_ledger(path: str | Path) -> dict[str, Any]:
    return _verify_chain(Path(path), FORECAST_SCHEMA, "forecast_id")


def verify_outcome_ledger(path: str | Path, forecast_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(path)
    state = _verify_chain(path, OUTCOME_SCHEMA, "outcome_id")
    if not state.get("valid") or forecast_path is None:
        return state
    forecasts = {row["forecast_id"]: row for row in _load(Path(forecast_path))}
    seen_forecasts: set[str] = set()
    for line, row in enumerate(_load(path), 1):
        forecast_id = row.get("forecast_id")
        if forecast_id not in forecasts:
            return {"valid": False, "rows": state["rows"], "error": f"unknown forecast_id line {line}"}
        if forecast_id in seen_forecasts:
            return {"valid": False, "rows": state["rows"], "error": f"duplicate outcome for forecast line {line}"}
        seen_forecasts.add(forecast_id)
        if row.get("forecast_row_hash") != forecasts[forecast_id].get("row_hash"):
            return {"valid": False, "rows": state["rows"], "error": f"forecast hash mismatch line {line}"}
    return state


def append_forecast(
    path: str | Path,
    *,
    component_id: str,
    market: str,
    instrument: str,
    orientation: str,
    decision_time_utc: str,
    data_cutoff_utc: str,
    horizon_days: int,
    outcome_definition: dict[str, Any],
    feature_snapshot_sha256: str,
    data_snapshot_sha256: str,
    code_sha256: str,
    predicted_probability: float | None = None,
    expected_return: float | None = None,
    lower_confidence_bound: float | None = None,
    entry_reference: float | None = None,
    target_reference: float | None = None,
    invalidation_reference: float | None = None,
    regime: str = "UNCLASSIFIED",
    created_at_utc: str | None = None,
    forecast_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    max_clock_skew_seconds: int = 300,
    max_recording_delay_seconds: int = 300,
) -> dict[str, Any]:
    path = Path(path)
    state = verify_forecast_ledger(path)
    if not state.get("valid"):
        raise ValueError(state.get("error"))
    wall_clock = _now()
    created = _parse_utc(created_at_utc, "created_at_utc") if created_at_utc else wall_clock
    if abs((wall_clock - created).total_seconds()) > max_clock_skew_seconds:
        raise ValueError("backfilled or future-created forecast is forbidden")
    decision = _parse_utc(decision_time_utc, "decision_time_utc")
    cutoff = _parse_utc(data_cutoff_utc, "data_cutoff_utc")
    if decision > created + timedelta(seconds=max_clock_skew_seconds):
        raise ValueError("decision_time_utc cannot be materially after record creation")
    if (created - decision).total_seconds() > max_recording_delay_seconds:
        raise ValueError("backfilled decision timestamp is forbidden")
    if cutoff > decision:
        raise ValueError("data_cutoff_utc is after decision_time_utc")
    if horizon_days <= 0:
        raise ValueError("horizon_days must be positive")
    market_u = str(market).upper()
    orientation_u = str(orientation).upper()
    if market_u not in ALLOWED_MARKETS:
        raise ValueError(f"unsupported market: {market}")
    if orientation_u not in ALLOWED_ORIENTATIONS:
        raise ValueError(f"unsupported orientation: {orientation}")
    if not component_id.strip() or not instrument.strip():
        raise ValueError("component_id and instrument are required")
    if not isinstance(outcome_definition, dict) or not outcome_definition.get("metric"):
        raise ValueError("outcome_definition.metric is required and must be frozen")
    if predicted_probability is not None and not 0.0 <= float(predicted_probability) <= 1.0:
        raise ValueError("predicted_probability must be in [0,1]")
    for value, name in ((expected_return, "expected_return"), (lower_confidence_bound, "lower_confidence_bound"),
                        (entry_reference, "entry_reference"), (target_reference, "target_reference"),
                        (invalidation_reference, "invalidation_reference")):
        if value is not None and not math.isfinite(float(value)):
            raise ValueError(f"{name} must be finite")
    fid = forecast_id or str(uuid.uuid4())
    if any(row.get("forecast_id") == fid for row in _load(path)):
        raise ValueError("duplicate forecast_id")
    row: dict[str, Any] = {
        "schema": FORECAST_SCHEMA,
        "forecast_id": fid,
        "created_at_utc": created.isoformat(),
        "decision_time_utc": decision.isoformat(),
        "data_cutoff_utc": cutoff.isoformat(),
        "matures_at_utc": (decision + timedelta(days=int(horizon_days))).isoformat(),
        "component_id": component_id.strip(),
        "market": market_u,
        "instrument": instrument.strip().upper(),
        "orientation": orientation_u,
        "horizon_days": int(horizon_days),
        "outcome_definition": outcome_definition,
        "predicted_probability": None if predicted_probability is None else float(predicted_probability),
        "expected_return": None if expected_return is None else float(expected_return),
        "lower_confidence_bound": None if lower_confidence_bound is None else float(lower_confidence_bound),
        "entry_reference": None if entry_reference is None else float(entry_reference),
        "target_reference": None if target_reference is None else float(target_reference),
        "invalidation_reference": None if invalidation_reference is None else float(invalidation_reference),
        "regime": str(regime or "UNCLASSIFIED").upper(),
        "feature_snapshot_sha256": _valid_sha(feature_snapshot_sha256, "feature_snapshot_sha256"),
        "data_snapshot_sha256": _valid_sha(data_snapshot_sha256, "data_snapshot_sha256"),
        "code_sha256": _valid_sha(code_sha256, "code_sha256"),
        "metadata": metadata or {},
        "outcome_state": "UNMATURED",
        "capital_permission": ZERO_CAPITAL,
        "previous_hash": state["head_hash"],
    }
    row["row_hash"] = hashlib.sha256(_canonical(row)).hexdigest()
    _append(path, row)
    return row


def append_outcome(
    outcome_path: str | Path,
    forecast_path: str | Path,
    *,
    forecast_id: str,
    realized_return: float,
    outcome_value: float,
    mae: float,
    mfe: float,
    resolved_at_utc: str | None = None,
    outcome_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    max_clock_skew_seconds: int = 300,
) -> dict[str, Any]:
    outcome_path, forecast_path = Path(outcome_path), Path(forecast_path)
    fstate = verify_forecast_ledger(forecast_path)
    ostate = verify_outcome_ledger(outcome_path, forecast_path)
    if not fstate.get("valid"):
        raise ValueError(fstate.get("error"))
    if not ostate.get("valid"):
        raise ValueError(ostate.get("error"))
    forecasts = {row["forecast_id"]: row for row in _load(forecast_path)}
    forecast = forecasts.get(forecast_id)
    if not forecast:
        raise ValueError("unknown forecast_id")
    if any(row.get("forecast_id") == forecast_id for row in _load(outcome_path)):
        raise ValueError("forecast already has an outcome")
    wall_clock = _now()
    resolved = _parse_utc(resolved_at_utc, "resolved_at_utc") if resolved_at_utc else wall_clock
    if abs((wall_clock - resolved).total_seconds()) > max_clock_skew_seconds:
        raise ValueError("backfilled or future-created outcome is forbidden")
    maturity = _parse_utc(forecast["matures_at_utc"], "matures_at_utc")
    if resolved < maturity:
        raise ValueError("outcome cannot be recorded before forecast maturity")
    values = {"realized_return": realized_return, "outcome_value": outcome_value, "mae": mae, "mfe": mfe}
    for name, value in values.items():
        if not math.isfinite(float(value)):
            raise ValueError(f"{name} must be finite")
    oid = outcome_id or str(uuid.uuid4())
    if any(row.get("outcome_id") == oid for row in _load(outcome_path)):
        raise ValueError("duplicate outcome_id")
    row: dict[str, Any] = {
        "schema": OUTCOME_SCHEMA,
        "outcome_id": oid,
        "forecast_id": forecast_id,
        "forecast_row_hash": forecast["row_hash"],
        "resolved_at_utc": resolved.isoformat(),
        "realized_return": float(realized_return),
        "outcome_value": float(outcome_value),
        "mae": float(mae),
        "mfe": float(mfe),
        "metadata": metadata or {},
        "capital_permission": ZERO_CAPITAL,
        "previous_hash": ostate["head_hash"],
    }
    row["row_hash"] = hashlib.sha256(_canonical(row)).hexdigest()
    _append(outcome_path, row)
    return row


def summarize_matured(forecast_path: str | Path, outcome_path: str | Path) -> dict[str, Any]:
    fstate = verify_forecast_ledger(forecast_path)
    ostate = verify_outcome_ledger(outcome_path, forecast_path)
    if not fstate.get("valid") or not ostate.get("valid"):
        return {"status": "FAIL", "forecast_validation": fstate, "outcome_validation": ostate, "capital_permission": ZERO_CAPITAL}
    forecasts = {row["forecast_id"]: row for row in _load(Path(forecast_path))}
    outcomes = _load(Path(outcome_path))
    signed_returns: list[float] = []
    brier: list[float] = []
    regimes: set[str] = set()
    for outcome in outcomes:
        forecast = forecasts[outcome["forecast_id"]]
        orientation = forecast["orientation"]
        realized = float(outcome["realized_return"])
        if orientation == "LONG":
            signed_returns.append(realized)
            event = 1.0 if realized > 0 else 0.0
        elif orientation == "SHORT":
            signed_returns.append(-realized)
            event = 1.0 if realized < 0 else 0.0
        else:
            event = 1.0 if abs(realized) <= float(forecast["outcome_definition"].get("neutral_band", 0.0)) else 0.0
        probability = forecast.get("predicted_probability")
        if probability is not None:
            brier.append((float(probability) - event) ** 2)
        regimes.add(str(forecast.get("regime") or "UNCLASSIFIED"))
    count = len(outcomes)
    return {
        "schema": "warroom.v78.prospective_summary.v1",
        "status": "PASS",
        "matured_forecasts": count,
        "distinct_regimes": len(regimes),
        "mean_signed_return": sum(signed_returns) / len(signed_returns) if signed_returns else None,
        "directional_hit_rate": sum(x > 0 for x in signed_returns) / len(signed_returns) if signed_returns else None,
        "brier_score": sum(brier) / len(brier) if brier else None,
        "automatic_promotion": False,
        "promotion_review_state": "INSUFFICIENT" if count < 200 or len(regimes) < 4 else "HUMAN_PROOF_REVIEW_REQUIRED",
        "capital_permission": ZERO_CAPITAL,
    }
