"""Normalize public bootstrap sources without pretending they are historical proof."""
from __future__ import annotations
from pathlib import Path
import argparse
import hashlib
import json
import re

import pandas as pd


def _creation_time(path: Path) -> str:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    footer = next((line for line in reversed(lines) if line.startswith("File Creation Time:")), "")
    match = re.search(r"(\d{2})(\d{2})(\d{4})(\d{2}):(\d{2})", footer)
    if not match:
        raise ValueError(f"missing Nasdaq file creation time: {path}")
    month, day, year, hour, minute = match.groups()
    return f"{year}-{month}-{day}T{hour}:{minute}:00Z"


def normalize_nasdaq(nasdaq_path: Path, other_path: Path, out_path: Path) -> dict:
    available_at = max(_creation_time(nasdaq_path), _creation_time(other_path))
    nasdaq = pd.read_csv(nasdaq_path, sep="|")
    other = pd.read_csv(other_path, sep="|")
    nasdaq = nasdaq[~nasdaq["Symbol"].astype(str).str.startswith("File Creation Time:")].copy()
    other = other[~other["ACT Symbol"].astype(str).str.startswith("File Creation Time:")].copy()
    rows = []
    for frame, symbol_col, name_col, exchange_col, source_id in [
        (nasdaq, "Symbol", "Security Name", "Market Category", "NASDAQ_TRADER_NASDAQLISTED"),
        (other, "ACT Symbol", "Security Name", "Exchange", "NASDAQ_TRADER_OTHERLISTED"),
    ]:
        for index, row in frame.iterrows():
            symbol = str(row.get(symbol_col) or "").strip()
            if not symbol or symbol.lower() == "nan":
                continue
            exchange = str(row.get(exchange_col) or "").strip()
            name = str(row.get(name_col) or "").strip()
            rows.extend([
                {
                    "record_id": f"{source_id}:{symbol}:LISTED",
                    "instrument_id": symbol,
                    "observation_at": available_at,
                    "available_at": available_at,
                    "source_id": source_id,
                    "source_record_id": symbol,
                    "field_id": "SECURITY_LISTED_STATUS",
                    "value": 1.0,
                    "unit": "BOOLEAN",
                    "revision_id": available_at,
                    "feature_domain": "security_master",
                    "text_value": name,
                    "synthetic": False,
                    "test_fixture": False,
                },
                {
                    "record_id": f"{source_id}:{symbol}:EXCHANGE",
                    "instrument_id": symbol,
                    "observation_at": available_at,
                    "available_at": available_at,
                    "source_id": source_id,
                    "source_record_id": symbol,
                    "field_id": "EXCHANGE_CODE_PRESENT",
                    "value": 1.0,
                    "unit": exchange or "UNKNOWN",
                    "revision_id": available_at,
                    "feature_domain": "security_master",
                    "text_value": exchange,
                    "synthetic": False,
                    "test_fixture": False,
                },
            ])
    result = pd.DataFrame(rows).drop_duplicates(["record_id"]).sort_values(["instrument_id", "field_id"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(out_path, index=False)
    payload = {
        "schema": "warroom.v91.bootstrap_public_evidence.v1",
        "role": "security_master",
        "market": "us",
        "rows": len(result),
        "instruments": int(result["instrument_id"].nunique()),
        "available_at": available_at,
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "proof_ceiling": "CURRENT_SNAPSHOT_BOOTSTRAP_ONLY",
        "claim_limit": "Current Nasdaq symbol directories are real public evidence but are not survivor-free historical security-master proof.",
    }
    return payload


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--nasdaq", required=True)
    parser.add_argument("--other", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--receipt")
    args = parser.parse_args()
    result = normalize_nasdaq(Path(args.nasdaq), Path(args.other), Path(args.out))
    if args.receipt:
        Path(args.receipt).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
