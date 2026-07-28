"""Build a hash-bound predictor manifest from actual files. Outcomes must live elsewhere."""
from __future__ import annotations
from pathlib import Path
import hashlib,json

def _sha(p:Path): return hashlib.sha256(p.read_bytes()).hexdigest()

def build(*, market:str, model_id:str, decision_times_file:str, role_files:dict[str,str], history_start:str, history_end:str, receipts:dict[str,str])->dict:
    forbidden={"outcome_prices","outcomes","realized_returns","future_returns"}
    if forbidden & set(role_files): raise ValueError("outcome role prohibited in predictor manifest")
    roles={}
    for role,path in role_files.items():
        p=Path(path).resolve()
        if not p.exists(): raise FileNotFoundError(p)
        roles[role]={"path":str(p),"sha256":_sha(p),"minimum_rows":1}
    payload={"schema":"warroom.v90.predictor_manifest.v1","market":market,"model_id":model_id,"evidence_mode":"REAL_POINT_IN_TIME_BLIND","synthetic_data":False,"test_fixture":False,"decision_times_file":decision_times_file,"decision_times_hash":_sha(Path(decision_times_file)),"history_start":history_start,"history_end":history_end,"roles":roles,**receipts}
    return payload
