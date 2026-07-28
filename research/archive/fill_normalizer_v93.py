"""Canonical account-fill normalizer for V9.3.

The normalizer accepts a user-supplied mapping instead of guessing broker semantics. It rejects
market prices, paper fills and synthetic records from being labelled actual execution evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

REQUIRED_CANONICAL = [
    "account_id", "venue", "market", "instrument_id", "side", "quantity", "fill_price",
    "filled_at", "commission", "exchange_fee", "tax", "financing", "borrow_fee",
    "order_id", "fill_id", "currency", "is_live_fill",
]


def normalize(input_path: Path, mapping_path: Path, output_path: Path) -> dict[str, Any]:
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    if mapping.get("schema") != "warroom.v93.fill_mapping.v1":
        raise ValueError("Unsupported mapping schema")
    frame = pd.read_csv(input_path)
    columns = mapping.get("columns") or {}
    constants = mapping.get("constants") or {}
    output = pd.DataFrame(index=frame.index)
    for canonical in REQUIRED_CANONICAL:
        source = columns.get(canonical)
        if source:
            if source not in frame.columns:
                raise ValueError(f"Missing source column {source!r} for {canonical}")
            output[canonical] = frame[source]
        elif canonical in constants:
            output[canonical] = constants[canonical]
        else:
            raise ValueError(f"Missing mapping for required canonical field {canonical}")
    output["side"] = output["side"].astype(str).str.upper().str.strip()
    if not output["side"].isin(["BUY", "SELL"]).all():
        raise ValueError("side must normalize to BUY or SELL")
    for name in ["quantity", "fill_price", "commission", "exchange_fee", "tax", "financing", "borrow_fee"]:
        output[name] = pd.to_numeric(output[name], errors="raise")
    live = output["is_live_fill"].astype(str).str.lower().map({"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False})
    if live.isna().any() or not live.all():
        raise ValueError("Every admitted row must be an actual live fill; paper/synthetic rows are rejected")
    output["is_live_fill"] = True
    output["filled_at"] = pd.to_datetime(output["filled_at"], utc=True, errors="raise")
    if output["fill_id"].astype(str).duplicated().any():
        raise ValueError("Duplicate fill_id")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(output_path, index=False)
    digest = hashlib.sha256(output_path.read_bytes()).hexdigest()
    return {"rows": int(len(output)), "path": str(output_path.resolve()), "sha256": digest, "capital_permission": "BLOCKED_PENDING_PROOF"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--mapping", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    print(json.dumps(normalize(Path(args.input), Path(args.mapping), Path(args.output)), indent=2))


if __name__ == "__main__":
    main()
