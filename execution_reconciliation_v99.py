"""Broker-neutral fill reconciliation and immutable execution ledger for War Room OS V9.9."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Mapping

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime" / "v99_trading"
LEDGER = RUNTIME / "order_ledger.jsonl"
FILLED_DIR = RUNTIME / "orders" / "filled"
PENDING_DIR = RUNTIME / "orders" / "pending"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UTC = dt.timezone.utc


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _load(path: str | Path) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("JSON root must be an object")
    return raw


def _time(value: Any) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _finite(value: Any, name: str, *, nonnegative: bool = False, positive: bool = False) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    if positive and number <= 0:
        raise ValueError(f"{name} must be positive")
    if nonnegative and number < 0:
        raise ValueError(f"{name} must be nonnegative")
    return number


def _last_hash() -> str:
    if not LEDGER.is_file():
        return "0" * 64
    lines = [line for line in LEDGER.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return "0" * 64
    row = json.loads(lines[-1])
    return str(row.get("event_hash") or "")


def _append(event: dict[str, Any]) -> dict[str, Any]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    previous = _last_hash()
    if not HEX64.fullmatch(previous):
        raise ValueError("execution ledger chain is invalid")
    row = {**event, "previous_hash": previous}
    row["event_hash"] = _hash(row)
    with LEDGER.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n")
        f.flush(); os.fsync(f.fileno())
    return row


def verify_ledger() -> dict[str, Any]:
    previous = "0" * 64
    events = 0
    errors: list[str] = []
    if not LEDGER.is_file():
        return {"valid": True, "events": 0, "last_hash": previous, "errors": []}
    for line_no, line in enumerate(LEDGER.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
            supplied = str(row.get("event_hash") or "")
            base = {k: v for k, v in row.items() if k != "event_hash"}
            if row.get("previous_hash") != previous:
                errors.append(f"line {line_no}: previous hash mismatch")
            if supplied != _hash(base):
                errors.append(f"line {line_no}: event hash mismatch")
            previous = supplied; events += 1
        except Exception as exc:
            errors.append(f"line {line_no}: {type(exc).__name__}: {exc}")
    return {"valid": not errors, "events": events, "last_hash": previous, "errors": errors}


def reconcile(order: Mapping[str, Any], fill: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if order.get("schema") != "warroom.v99.broker_neutral_order.v1":
        errors.append("wrong order schema")
    if fill.get("schema") != "warroom.v99.fill_receipt.v1":
        errors.append("wrong fill schema")
    if fill.get("live") is not True:
        errors.append("paper or synthetic fill rejected")
    if fill.get("source") not in {"BROKER_EXPORT", "EXCHANGE_ACCOUNT_EXPORT"}:
        errors.append("fill source is not an account execution source")
    for field in ("order_id", "account_id_hash", "market", "instrument", "venue"):
        if str(fill.get(field) or "") != str(order.get(field) or ""):
            errors.append(f"fill {field} mismatch")
    try:
        created = _time(order.get("created_at")); filled = _time(fill.get("filled_at"))
        if filled < created:
            errors.append("fill predates order export")
        if filled > dt.datetime.now(UTC) + dt.timedelta(minutes=5):
            errors.append("fill timestamp is in the future")
    except Exception as exc:
        errors.append(f"timestamp invalid: {type(exc).__name__}: {exc}")
    try:
        ordered_qty = _finite(order.get("quantity"), "ordered quantity", positive=True)
        filled_qty = _finite(fill.get("filled_quantity"), "filled quantity", positive=True)
        fill_price = _finite(fill.get("fill_price"), "fill price", positive=True)
        fees = _finite(fill.get("fees"), "fees", nonnegative=True)
        if filled_qty > ordered_qty + 1e-12:
            errors.append("overfill rejected")
        if str(fill.get("side") or "") != str(order.get("side") or ""):
            errors.append("fill side mismatch")
        limit = _finite(order.get("limit_price"), "limit price", positive=True)
        if order.get("side") == "BUY" and fill_price > limit * 1.001:
            errors.append("buy fill materially exceeded limit")
        if order.get("side") == "SELL" and fill_price < limit * 0.999:
            errors.append("sell fill materially below limit")
    except Exception as exc:
        errors.append(f"fill economics invalid: {type(exc).__name__}: {exc}")
    broker_id_hash = str(fill.get("broker_order_id_hash") or "")
    if not HEX64.fullmatch(broker_id_hash):
        errors.append("broker_order_id_hash must be SHA-256")
    if errors:
        return {"schema": "warroom.v99.reconciliation.v1", "status": "REJECTED", "errors": sorted(set(errors)), "order_id": order.get("order_id")}
    receipt_hash = _hash(fill)
    event = _append({
        "event_type": "FILL_RECONCILED",
        "event_at": _iso(dt.datetime.now(UTC)),
        "order_id": order.get("order_id"),
        "order_hash": order.get("order_hash"),
        "fill_receipt_hash": receipt_hash,
        "broker_order_id_hash": broker_id_hash,
        "filled_quantity": filled_qty,
        "fill_price": fill_price,
        "fees": fees,
    })
    FILLED_DIR.mkdir(parents=True, exist_ok=True)
    record = {
        "schema": "warroom.v99.reconciliation.v1",
        "status": "RECONCILED",
        "reconciled_at": _iso(dt.datetime.now(UTC)),
        "order": dict(order),
        "fill": dict(fill),
        "fill_receipt_hash": receipt_hash,
        "ledger_event_hash": event["event_hash"],
    }
    record["record_hash"] = _hash({k: v for k, v in record.items() if k != "record_hash"})
    out = FILLED_DIR / f"{order['order_id']}.json"
    temp = out.with_suffix(".json.tmp"); temp.write_text(json.dumps(record, indent=2, allow_nan=False), encoding="utf-8"); os.replace(temp, out)
    pending_json = PENDING_DIR / f"{order['order_id']}.json"
    pending_csv = PENDING_DIR / f"{order['order_id']}.csv"
    pending_json.unlink(missing_ok=True); pending_csv.unlink(missing_ok=True)
    return record


def import_fill_csv(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != 1:
        raise ValueError("fill CSV must contain exactly one row")
    row = rows[0]
    return {
        "schema": "warroom.v99.fill_receipt.v1",
        "order_id": row.get("order_id"),
        "broker_order_id_hash": row.get("broker_order_id_hash"),
        "account_id_hash": row.get("account_id_hash"),
        "market": row.get("market"),
        "instrument": row.get("instrument"),
        "venue": row.get("venue"),
        "side": row.get("side"),
        "filled_quantity": float(row.get("filled_quantity") or 0),
        "fill_price": float(row.get("fill_price") or 0),
        "fees": float(row.get("fees") or 0),
        "filled_at": row.get("filled_at"),
        "source": row.get("source"),
        "live": str(row.get("live") or "").strip().lower() in {"true", "1", "yes"},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_verify = sub.add_parser("verify-ledger")
    p_rec = sub.add_parser("reconcile"); p_rec.add_argument("--order", required=True); p_rec.add_argument("--fill", required=True); p_rec.add_argument("--fill-csv", action="store_true")
    args = parser.parse_args()
    if args.command == "verify-ledger": result = verify_ledger()
    else:
        fill = import_fill_csv(Path(args.fill)) if args.fill_csv else _load(args.fill)
        result = reconcile(_load(args.order), fill)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
