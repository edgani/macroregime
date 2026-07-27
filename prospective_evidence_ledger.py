"""Strict prospective forecast/outcome ledger for V8.5."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
SIGNAL_ID = re.compile(r"^SIG_[A-F0-9]{24}$")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _time(value: Any) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def verify(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        rows = _read(p)
    except Exception as exc:
        return {"valid": False, "count": 0, "reason": str(exc)}
    previous = "GENESIS"
    forecast_ids = set()
    outcome_ids = set()
    for index, row in enumerate(rows):
        body = dict(row)
        recorded = body.pop("record_hash", None)
        if body.get("previous_hash") != previous:
            return {"valid": False, "count": len(rows), "row": index, "reason": "previous_hash mismatch"}
        if hashlib.sha256(canonical(body)).hexdigest() != recorded:
            return {"valid": False, "count": len(rows), "row": index, "reason": "record_hash mismatch"}
        record_type = body.get("record_type")
        forecast_id = body.get("forecast_id")
        if record_type == "FORECAST":
            if forecast_id in forecast_ids:
                return {"valid": False, "count": len(rows), "row": index, "reason": "duplicate forecast"}
            forecast_ids.add(forecast_id)
        elif record_type == "OUTCOME":
            if forecast_id in outcome_ids or forecast_id not in forecast_ids:
                return {"valid": False, "count": len(rows), "row": index, "reason": "invalid outcome link"}
            outcome_ids.add(forecast_id)
        else:
            return {"valid": False, "count": len(rows), "row": index, "reason": "invalid record_type"}
        previous = str(recorded)
    return {"valid": True, "count": len(rows), "forecasts": len(forecast_ids), "outcomes": len(outcome_ids), "last_hash": previous}


def _append(path: Path, body: dict[str, Any]) -> dict[str, Any]:
    rows = _read(path)
    if rows and not verify(path).get("valid"):
        raise ValueError("Existing prospective ledger is invalid")
    body = dict(body)
    body["previous_hash"] = rows[-1]["record_hash"] if rows else "GENESIS"
    body["record_hash"] = hashlib.sha256(canonical(body)).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")
    return body


def append_forecast(path: str | Path, forecast: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    required = [
        "forecast_id", "trial_id", "opaque_signal_id", "market", "security_id", "generated_at",
        "decision_at", "outcome_start", "outcome_end", "horizon", "direction", "probability",
        "expected_return", "expected_shortfall", "invalidation", "regime", "model_hash",
        "data_snapshot_hash", "code_hash", "capital_permission", "mode",
    ]
    missing = [key for key in required if key not in forecast]
    if missing:
        raise ValueError(f"Missing forecast fields: {', '.join(missing)}")
    if not SIGNAL_ID.fullmatch(str(forecast["opaque_signal_id"])):
        raise ValueError("opaque_signal_id is invalid")
    for key in ("model_hash", "data_snapshot_hash", "code_hash"):
        if not HEX64.fullmatch(str(forecast[key])):
            raise ValueError(f"invalid {key}")
    generated = _time(forecast["generated_at"])
    decision = _time(forecast["decision_at"])
    outcome_start = _time(forecast["outcome_start"])
    outcome_end = _time(forecast["outcome_end"])
    if abs((now - generated).total_seconds()) > 300:
        raise ValueError("Backfilled or future forecast rejected")
    if decision < generated or outcome_start < decision or outcome_end <= outcome_start:
        raise ValueError("Invalid prospective chronology")
    if str(forecast["direction"]).upper() not in {"LONG", "SHORT", "NO_TRADE"}:
        raise ValueError("Invalid direction")
    probability = float(forecast["probability"])
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be in [0,1]")
    if forecast["capital_permission"] != "BLOCKED" or forecast["mode"] != "PROSPECTIVE_SHADOW_ONLY":
        raise ValueError("Forecast must be shadow-only and capital blocked")
    p = Path(path)
    if any(row.get("forecast_id") == forecast["forecast_id"] for row in _read(p)):
        raise ValueError("Duplicate forecast_id")
    return _append(p, {"record_type": "FORECAST", **forecast})


def append_outcome(path: str | Path, outcome: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    p = Path(path)
    rows = _read(p)
    forecast_id = outcome.get("forecast_id")
    forecasts = [row for row in rows if row.get("record_type") == "FORECAST" and row.get("forecast_id") == forecast_id]
    if len(forecasts) != 1:
        raise ValueError("Unknown forecast_id")
    if any(row.get("record_type") == "OUTCOME" and row.get("forecast_id") == forecast_id for row in rows):
        raise ValueError("Duplicate outcome")
    if now < _time(forecasts[0]["outcome_end"]):
        raise ValueError("Outcome has not matured")
    required = ["realized_return", "mae", "mfe", "realized_cost", "outcome_source_hash"]
    missing = [key for key in required if key not in outcome]
    if missing:
        raise ValueError(f"Missing outcome fields: {', '.join(missing)}")
    if not HEX64.fullmatch(str(outcome["outcome_source_hash"])):
        raise ValueError("invalid outcome_source_hash")
    body = {"record_type": "OUTCOME", **outcome, "recorded_at": now.isoformat().replace("+00:00", "Z")}
    return _append(p, body)
