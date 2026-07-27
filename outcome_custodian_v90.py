"""Outcome custodian: outcomes cannot be opened until forecast/code/data hashes are frozen."""
from __future__ import annotations
from pathlib import Path
import hashlib,json
import pandas as pd

def sha(path: Path)->str: return hashlib.sha256(path.read_bytes()).hexdigest()

def open_outcomes(*, forecast_file: Path, outcome_file: Path, seal_file: Path) -> tuple[pd.DataFrame,dict]:
    seal=json.loads(seal_file.read_text(encoding="utf-8"))
    errors=[]
    if sha(forecast_file)!=seal.get("forecast_file_hash"): errors.append("forecast hash mismatch")
    if not seal.get("model_hash") or not seal.get("code_snapshot_hash") or not seal.get("global_trial_ledger_hash"): errors.append("incomplete pre-outcome seal")
    if errors: raise ValueError("; ".join(errors))
    frame=pd.read_csv(outcome_file)
    required={"forecast_id","horizon_end","realized_return","max_adverse_excursion","max_favorable_excursion"}
    if required-set(frame): raise ValueError(f"missing outcome columns: {sorted(required-set(frame))}")
    result={"schema":"warroom.v90.outcome_open_receipt.v1","forecast_hash":sha(forecast_file),"outcome_hash":sha(outcome_file),"rows":len(frame),"model_hash":seal["model_hash"]}
    result["receipt_hash"]=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return frame,result
