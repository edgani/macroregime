"""Append-only prospective shadow ledger for War Room OS V6.6.

The ledger records frozen predictions before outcomes are known.  It never grants capital.
Rows are hash-chained and can be verified without trusting mutable application state.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable
import hashlib
import json
import os
import uuid

SCHEMA = "warroom.v66.prospective_shadow_row.v1"
GENESIS = "0" * 64


def _canonical(obj: dict[str, Any]) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _load(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows=[]
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try: rows.append(json.loads(line))
        except Exception as exc: raise ValueError(f"invalid ledger JSON at line {number}: {exc}") from exc
    return rows


def verify_shadow_ledger(path: str | Path) -> dict[str, Any]:
    path=Path(path); rows=_load(path); prev=GENESIS; ids=set()
    for idx,row in enumerate(rows,1):
        if row.get("schema") != SCHEMA: return {"valid":False,"rows":len(rows),"error":f"schema mismatch line {idx}"}
        if row.get("forecast_id") in ids: return {"valid":False,"rows":len(rows),"error":f"duplicate forecast_id line {idx}"}
        ids.add(row.get("forecast_id"))
        if row.get("previous_hash") != prev: return {"valid":False,"rows":len(rows),"error":f"chain mismatch line {idx}"}
        claimed=row.get("row_hash"); unsigned=dict(row); unsigned.pop("row_hash",None)
        actual=hashlib.sha256(_canonical(unsigned)).hexdigest()
        if claimed != actual: return {"valid":False,"rows":len(rows),"error":f"row hash mismatch line {idx}"}
        if row.get("capital_permission") != "SHADOW_ONLY_ZERO_CAPITAL": return {"valid":False,"rows":len(rows),"error":f"capital permission violation line {idx}"}
        prev=claimed
    return {"valid":True,"rows":len(rows),"head_hash":prev}


def append_shadow_forecast(
    path: str | Path,
    *,
    component_id: str,
    scope: str,
    instrument: str,
    orientation: str,
    horizon_days: int,
    feature_snapshot_sha256: str,
    data_snapshot_sha256: str,
    code_sha256: str,
    created_at_utc: str | None = None,
    forecast_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    state=verify_shadow_ledger(path)
    if not state["valid"]: raise ValueError(state["error"])
    for value,name in [(feature_snapshot_sha256,"feature_snapshot_sha256"),(data_snapshot_sha256,"data_snapshot_sha256"),(code_sha256,"code_sha256")]:
        if len(value)!=64 or any(c not in "0123456789abcdef" for c in value.lower()): raise ValueError(f"{name} must be a SHA-256 hex digest")
    if horizon_days <= 0: raise ValueError("horizon_days must be positive")
    created=created_at_utc or datetime.now(timezone.utc).isoformat()
    dt=datetime.fromisoformat(created.replace("Z","+00:00"))
    if dt > datetime.now(timezone.utc).replace(microsecond=999999): raise ValueError("future-created forecast is forbidden")
    fid=forecast_id or str(uuid.uuid4())
    if any(r.get("forecast_id")==fid for r in _load(path)): raise ValueError("duplicate forecast_id")
    row={
      "schema":SCHEMA,"forecast_id":fid,"created_at_utc":dt.astimezone(timezone.utc).isoformat(),
      "component_id":component_id,"scope":scope,"instrument":instrument,
      "orientation":orientation.upper(),"horizon_days":int(horizon_days),
      "feature_snapshot_sha256":feature_snapshot_sha256.lower(),"data_snapshot_sha256":data_snapshot_sha256.lower(),
      "code_sha256":code_sha256.lower(),"metadata":metadata or {},
      "outcome_state":"UNMATURED","capital_permission":"SHADOW_ONLY_ZERO_CAPITAL",
      "previous_hash":state["head_hash"],
    }
    row["row_hash"]=hashlib.sha256(_canonical(row)).hexdigest()
    encoded=json.dumps(row,sort_keys=True,separators=(",",":"),ensure_ascii=False)+"\n"
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_APPEND,0o600)
    try: os.write(fd,encoded.encode("utf-8")); os.fsync(fd)
    finally: os.close(fd)
    return row
