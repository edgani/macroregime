"""Normalize user-owned closed live trades into the strict V9.5 proof schema.

The input must already represent closed round trips. This tool never invents fill pairing, costs,
borrow status or forecast links. Sensitive account/order identifiers are HMAC-SHA256 pseudonymized.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from realized_performance_gate_v95 import LIVE_SOURCES, TRADE_REQUIRED, _strict_bool, validate_trade_ledger

RAW_ID_FIELDS = {"account_id": "account_id_hash", "entry_order_id": "entry_order_id_hash", "exit_order_id": "exit_order_id_hash"}
DIRECT_FIELDS = [c for c in TRADE_REQUIRED if c not in {"account_id_hash", "entry_order_id_hash", "exit_order_id_hash", "source_snapshot_hash"}]


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pseudonym(value: Any, salt: str) -> str:
    text = str(value).strip()
    if not text:
        raise ValueError("identifier is blank")
    return hmac.new(salt.encode("utf-8"), text.encode("utf-8"), hashlib.sha256).hexdigest()


def normalize(input_path: Path, mapping_path: Path, output_path: Path, *, salt: str) -> dict[str, Any]:
    if len(salt) < 16:
        raise ValueError("WARROOM_ID_HASH_SALT must contain at least 16 characters")
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if mapping.get("schema") != "warroom.v95.closed_trade_mapping.v1":
        raise ValueError("unsupported mapping schema")
    frame = pd.read_csv(input_path); columns = mapping.get("columns") or {}; constants = mapping.get("constants") or {}
    output = pd.DataFrame(index=frame.index)

    for canonical in DIRECT_FIELDS:
        source = columns.get(canonical)
        if source:
            if source not in frame.columns:
                raise ValueError(f"missing source column {source!r} for {canonical}")
            output[canonical] = frame[source]
        elif canonical in constants:
            output[canonical] = constants[canonical]
        else:
            raise ValueError(f"missing mapping for {canonical}")
    for raw_name, canonical in RAW_ID_FIELDS.items():
        source = columns.get(raw_name)
        if source:
            if source not in frame.columns:
                raise ValueError(f"missing source column {source!r} for {raw_name}")
            output[canonical] = frame[source].map(lambda x: pseudonym(x, salt))
        elif raw_name in constants:
            digest = pseudonym(constants[raw_name], salt); output[canonical] = digest
        else:
            raise ValueError(f"missing mapping for {raw_name}")

    output["source_snapshot_hash"] = sha(input_path)
    for field in ("is_live", "paper", "synthetic", "borrow_available"):
        output[field] = output[field].map(_strict_bool)
    output["direction"] = output["direction"].astype(str).str.upper().str.strip()
    output["market"] = output["market"].astype(str).str.lower().str.strip()
    output["execution_source"] = output["execution_source"].astype(str).str.upper().str.strip()
    if not output["execution_source"].isin(LIVE_SOURCES).all():
        raise ValueError("execution_source must be a recognized broker/exchange source")
    for field in ("entry_fill_at", "exit_fill_at"):
        output[field] = pd.to_datetime(output[field], utc=True, errors="raise").dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    numeric = ["quantity", "entry_price", "exit_price", "commission", "fees", "spread_cost", "slippage_cost", "impact_cost", "borrow_cost", "financing_cost", "taxes", "adv_notional"]
    for field in numeric:
        output[field] = pd.to_numeric(output[field], errors="raise")
    output = output[TRADE_REQUIRED]
    structural = validate_trade_ledger(output)
    if not structural.get("valid"):
        raise ValueError("normalized ledger failed structural gate: " + "; ".join(structural.get("errors", [])))
    output_path.parent.mkdir(parents=True, exist_ok=True); output.to_csv(output_path, index=False)
    receipt = {
        "schema": "warroom.v95.closed_trade_normalization_receipt.v1",
        "input_sha256": sha(input_path), "mapping_sha256": sha(mapping_path),
        "output_path": output_path.name, "output_sha256": sha(output_path), "rows": len(output),
        "market": structural.get("market"), "strategy_id": structural.get("strategy_id"),
        "account_id_hash": structural.get("account_id_hash"), "execution_source": structural.get("execution_source"),
        "ledger_structurally_valid": True, "all_live_profit_gates_pass": structural.get("all_trade_gates_pass", False),
        "capital_permission": "BLOCKED_PENDING_BOUND_PROOF",
        "claim_limit": "Normalization and structural validity are not evidence of profitability or source authenticity by themselves."
    }
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    output_path.with_suffix(output_path.suffix + ".receipt.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return receipt


def main() -> None:
    p = argparse.ArgumentParser(); p.add_argument("--input", required=True); p.add_argument("--mapping", required=True); p.add_argument("--output", required=True)
    args = p.parse_args(); salt = os.getenv("WARROOM_ID_HASH_SALT", "")
    print(json.dumps(normalize(Path(args.input), Path(args.mapping), Path(args.output), salt=salt), indent=2))


if __name__ == "__main__":
    main()
