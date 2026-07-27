"""Normalize licensed/official CSV exports into the V8.9 point-in-time evidence contract.

Designed for sources whose legal access path is a downloaded exchange/vendor file rather than a
public API (for example IDX historical products, analyst estimates, stock lending or execution data).
The tool never guesses timestamps or fills missing identity fields.
"""
from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import uuid

import pandas as pd

REQUIRED_OUTPUT = [
    "record_id", "instrument_id", "observation_at", "available_at", "source_id",
    "source_record_id", "field_id", "value", "unit", "revision_id", "feature_domain",
    "synthetic", "test_fixture",
]


def normalize(input_path: Path, mapping_path: Path, output_path: Path) -> dict:
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    frame = pd.read_csv(input_path)
    columns = mapping.get("columns") or {}
    constants = mapping.get("constants") or {}
    missing_sources = sorted({src for src in columns.values() if src not in frame.columns})
    if missing_sources:
        raise ValueError("source columns missing: " + ",".join(missing_sources))
    out = pd.DataFrame(index=frame.index)
    for target in REQUIRED_OUTPUT:
        if target in columns:
            out[target] = frame[columns[target]]
        elif target in constants:
            out[target] = constants[target]
        elif target == "record_id":
            out[target] = [str(uuid.uuid5(uuid.NAMESPACE_URL, f"{input_path.resolve()}:{i}")) for i in range(len(frame))]
        elif target in {"synthetic", "test_fixture"}:
            out[target] = False
        else:
            raise ValueError(f"mapping missing required output: {target}")
    observed = pd.to_datetime(out["observation_at"], utc=True, errors="coerce")
    available = pd.to_datetime(out["available_at"], utc=True, errors="coerce")
    if observed.isna().any() or available.isna().any():
        raise ValueError("invalid observation_at or available_at; timestamps cannot be inferred")
    if out["instrument_id"].astype(str).str.strip().eq("").any():
        raise ValueError("instrument_id missing")
    if out["source_record_id"].astype(str).str.strip().eq("").any():
        raise ValueError("source_record_id missing")
    if out["value"].pipe(pd.to_numeric, errors="coerce").isna().all():
        raise ValueError("no numeric values")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output_path, index=False)
    return {
        "schema": "warroom.v89.external_table_normalization.v1",
        "input": str(input_path),
        "input_sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(),
        "mapping_sha256": hashlib.sha256(mapping_path.read_bytes()).hexdigest(),
        "output": str(output_path),
        "output_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
        "rows": len(out),
        "claim_limit": "Normalization only; source licensing, point-in-time meaning and trading proof remain separately adjudicated.",
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--mapping', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--receipt', required=True)
    args=parser.parse_args()
    result=normalize(Path(args.input),Path(args.mapping),Path(args.output))
    Path(args.receipt).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
