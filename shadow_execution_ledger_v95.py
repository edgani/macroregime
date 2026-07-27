"""Tamper-evident prospective shadow-trading ledger for War Room OS V9.5.

This is an operational rehearsal lane, not proof of live profitability. Every forecast is frozen
before its outcome window; order intents and simulated fills remain capital-blocked and cannot be
consumed by the V9.5 realized live-fill gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")
FORECAST_ID = re.compile(r"^F95_[A-Z0-9_-]{8,80}$")
MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
DIRECTIONS = {"LONG", "SHORT", "NO_TRADE"}
RECORD_TYPES = {"FORECAST", "ORDER_INTENT", "SHADOW_FILL", "OUTCOME"}


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def parse_time(value: Any) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(dt.timezone.utc)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def valid_hash(value: Any) -> bool:
    text = str(value or "").lower()
    return bool(HEX64.fullmatch(text) and text != "0" * 64)


def _read(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"row {line_number} is not an object")
        rows.append(value)
    return rows


def verify(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    try:
        rows = _read(p)
    except Exception as exc:
        return {"valid": False, "rows": 0, "errors": [f"load failed: {type(exc).__name__}: {exc}"]}
    errors: list[str] = []
    previous = "GENESIS"
    forecasts: dict[str, dict[str, Any]] = {}
    order_ids: set[str] = set()
    fills_by_order: set[str] = set()
    outcome_ids: set[str] = set()
    for index, row in enumerate(rows):
        body = dict(row); recorded = str(body.pop("record_hash", ""))
        if row.get("schema") != "warroom.v95.shadow_ledger_record.v1":
            errors.append(f"row {index}: schema mismatch")
        if body.get("previous_hash") != previous:
            errors.append(f"row {index}: previous_hash mismatch")
        if hashlib.sha256(canonical(body)).hexdigest() != recorded:
            errors.append(f"row {index}: record_hash mismatch")
        record_type = str(body.get("record_type") or "")
        forecast_id = str(body.get("forecast_id") or "")
        if record_type not in RECORD_TYPES:
            errors.append(f"row {index}: invalid record_type")
        elif record_type == "FORECAST":
            if forecast_id in forecasts:
                errors.append(f"row {index}: duplicate forecast")
            forecasts[forecast_id] = body
        elif forecast_id not in forecasts:
            errors.append(f"row {index}: unknown forecast_id")
        elif record_type == "ORDER_INTENT":
            order_id = str(body.get("shadow_order_id") or "")
            if not order_id or order_id in order_ids:
                errors.append(f"row {index}: invalid or duplicate shadow_order_id")
            order_ids.add(order_id)
        elif record_type == "SHADOW_FILL":
            order_id = str(body.get("shadow_order_id") or "")
            if order_id not in order_ids or order_id in fills_by_order:
                errors.append(f"row {index}: fill does not map one-to-one to order intent")
            fills_by_order.add(order_id)
        elif record_type == "OUTCOME":
            if forecast_id in outcome_ids:
                errors.append(f"row {index}: duplicate outcome")
            outcome_ids.add(forecast_id)
        previous = recorded
    return {
        "schema": "warroom.v95.shadow_ledger_verification.v1",
        "valid": not errors,
        "rows": len(rows),
        "forecasts": len(forecasts),
        "order_intents": len(order_ids),
        "shadow_fills": len(fills_by_order),
        "outcomes": len(outcome_ids),
        "last_hash": previous,
        "errors": sorted(set(errors)),
        "capital_permission": "BLOCKED",
    }


def _append(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    current = verify(path)
    if path.exists() and not current.get("valid"):
        raise ValueError("existing shadow ledger failed verification")
    rows = _read(path)
    body = {
        "schema": "warroom.v95.shadow_ledger_record.v1",
        **payload,
        "recorded_at": utc_now(),
        "previous_hash": rows[-1]["record_hash"] if rows else "GENESIS",
        "capital_permission": "BLOCKED",
        "evidence_class": "PROSPECTIVE_SHADOW_ONLY",
    }
    body["record_hash"] = hashlib.sha256(canonical(body)).hexdigest()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(body, sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
    checked = verify(path)
    if not checked.get("valid"):
        raise RuntimeError("post-append verification failed")
    return body


def append_forecast(path: str | Path, forecast: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    required = {
        "forecast_id", "trial_id", "market", "security_id", "generated_at", "decision_at",
        "outcome_start", "outcome_end", "horizon", "direction", "probability", "expected_return",
        "expected_shortfall", "invalidation", "regime", "model_hash", "data_snapshot_hash",
        "code_snapshot_hash", "global_trial_ledger_hash", "projection_file_hash",
    }
    missing = sorted(required - set(forecast))
    if missing:
        raise ValueError("missing forecast fields: " + ", ".join(missing))
    forecast_id = str(forecast["forecast_id"])
    if not FORECAST_ID.fullmatch(forecast_id):
        raise ValueError("invalid forecast_id")
    market = str(forecast["market"]).lower()
    if market not in MARKETS:
        raise ValueError("unsupported market")
    direction = str(forecast["direction"]).upper()
    if direction not in DIRECTIONS:
        raise ValueError("direction must be LONG, SHORT or NO_TRADE")
    for field in ("model_hash", "data_snapshot_hash", "code_snapshot_hash", "global_trial_ledger_hash", "projection_file_hash"):
        if not valid_hash(forecast[field]):
            raise ValueError(f"invalid {field}")
    generated = parse_time(forecast["generated_at"]); decision = parse_time(forecast["decision_at"])
    outcome_start = parse_time(forecast["outcome_start"]); outcome_end = parse_time(forecast["outcome_end"])
    if abs((now - generated).total_seconds()) > 300:
        raise ValueError("backfilled or future forecast rejected")
    if decision < generated or outcome_start < decision or outcome_end <= outcome_start:
        raise ValueError("invalid prospective chronology")
    probability = float(forecast["probability"]); expected = float(forecast["expected_return"]); shortfall = float(forecast["expected_shortfall"])
    if not all(math.isfinite(x) for x in (probability, expected, shortfall)) or not 0 <= probability <= 1:
        raise ValueError("invalid probability/return fields")
    if shortfall > 0:
        raise ValueError("expected_shortfall must be zero or negative")
    if any(row.get("record_type") == "FORECAST" and row.get("forecast_id") == forecast_id for row in _read(Path(path))):
        raise ValueError("duplicate forecast_id")
    return _append(Path(path), {"record_type": "FORECAST", **forecast, "market": market, "direction": direction})


def append_order_intent(path: str | Path, order: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    required = {"forecast_id", "shadow_order_id", "created_at", "instrument_id", "side", "quantity", "order_type", "reference_price", "max_slippage_bps"}
    missing = sorted(required - set(order))
    if missing:
        raise ValueError("missing order fields: " + ", ".join(missing))
    rows = _read(Path(path)); forecast = next((r for r in rows if r.get("record_type") == "FORECAST" and r.get("forecast_id") == order["forecast_id"]), None)
    if forecast is None:
        raise ValueError("unknown forecast_id")
    if str(forecast.get("direction")) == "NO_TRADE":
        raise ValueError("NO_TRADE forecast cannot create order intent")
    created = parse_time(order["created_at"])
    if abs((now - created).total_seconds()) > 300:
        raise ValueError("backfilled or future order rejected")
    if created < parse_time(forecast["decision_at"]):
        raise ValueError("order predates decision")
    side = str(order["side"]).upper()
    expected_side = "BUY" if forecast["direction"] == "LONG" else "SELL"
    if side != expected_side:
        raise ValueError("order side conflicts with forecast direction")
    quantity = float(order["quantity"]); reference = float(order["reference_price"]); slippage = float(order["max_slippage_bps"])
    if not all(math.isfinite(x) and x > 0 for x in (quantity, reference)) or not math.isfinite(slippage) or not 0 <= slippage <= 500:
        raise ValueError("invalid order sizing or slippage")
    return _append(Path(path), {"record_type": "ORDER_INTENT", **order, "side": side, "execution_mode": "SHADOW_SIMULATION"})


def append_shadow_fill(path: str | Path, fill: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    required = {"forecast_id", "shadow_order_id", "filled_at", "quantity", "price", "commission", "fees", "spread_cost", "slippage_cost", "source_snapshot_hash"}
    missing = sorted(required - set(fill))
    if missing:
        raise ValueError("missing fill fields: " + ", ".join(missing))
    rows = _read(Path(path)); order = next((r for r in rows if r.get("record_type") == "ORDER_INTENT" and r.get("shadow_order_id") == fill["shadow_order_id"]), None)
    if order is None or order.get("forecast_id") != fill["forecast_id"]:
        raise ValueError("fill does not match an order intent")
    if any(r.get("record_type") == "SHADOW_FILL" and r.get("shadow_order_id") == fill["shadow_order_id"] for r in rows):
        raise ValueError("duplicate shadow fill")
    filled = parse_time(fill["filled_at"])
    if filled > now + dt.timedelta(minutes=5) or filled < parse_time(order["created_at"]):
        raise ValueError("invalid fill chronology")
    for field in ("quantity", "price"):
        if not math.isfinite(float(fill[field])) or float(fill[field]) <= 0:
            raise ValueError(f"invalid {field}")
    for field in ("commission", "fees", "spread_cost", "slippage_cost"):
        if not math.isfinite(float(fill[field])) or float(fill[field]) < 0:
            raise ValueError(f"invalid {field}")
    if not valid_hash(fill["source_snapshot_hash"]):
        raise ValueError("invalid source_snapshot_hash")
    return _append(Path(path), {"record_type": "SHADOW_FILL", **fill, "paper": True, "synthetic": True, "is_live": False, "execution_source": "SHADOW_SIMULATOR"})


def append_outcome(path: str | Path, outcome: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    required = {"forecast_id", "horizon_end", "realized_return", "max_adverse_excursion", "max_favorable_excursion", "outcome_source_hash"}
    missing = sorted(required - set(outcome))
    if missing:
        raise ValueError("missing outcome fields: " + ", ".join(missing))
    rows = _read(Path(path)); forecast = next((r for r in rows if r.get("record_type") == "FORECAST" and r.get("forecast_id") == outcome["forecast_id"]), None)
    if forecast is None:
        raise ValueError("unknown forecast_id")
    if any(r.get("record_type") == "OUTCOME" and r.get("forecast_id") == outcome["forecast_id"] for r in rows):
        raise ValueError("duplicate outcome")
    horizon_end = parse_time(outcome["horizon_end"])
    if horizon_end < parse_time(forecast["outcome_end"]) or now < horizon_end:
        raise ValueError("outcome has not matured")
    for field in ("realized_return", "max_adverse_excursion", "max_favorable_excursion"):
        if not math.isfinite(float(outcome[field])):
            raise ValueError(f"invalid {field}")
    if not valid_hash(outcome["outcome_source_hash"]):
        raise ValueError("invalid outcome_source_hash")
    return _append(Path(path), {"record_type": "OUTCOME", **outcome})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["verify", "forecast", "order", "fill", "outcome"])
    parser.add_argument("--ledger", default="runtime/v95_shadow/shadow_ledger.jsonl")
    parser.add_argument("--input")
    args = parser.parse_args(); path = Path(args.ledger)
    if args.command == "verify":
        result = verify(path)
    else:
        if not args.input:
            raise SystemExit("--input JSON is required")
        payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
        functions = {"forecast": append_forecast, "order": append_order_intent, "fill": append_shadow_fill, "outcome": append_outcome}
        result = functions[args.command](path, payload)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
