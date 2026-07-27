"""Create a V9.5 pre-outcome forecast seal binding predictor data and projections."""
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, re
from pathlib import Path
from typing import Any

HEX64 = re.compile(r"^[0-9a-f]{64}$")

def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def valid(value: Any) -> bool:
    text=str(value or '').lower(); return bool(HEX64.fullmatch(text) and text!='0'*64)

def build(*, predictor_manifest: Path, projections: Path, model_hash: str, code_snapshot_hash: str, global_trial_ledger_hash: str, sealed_at: str|None=None) -> dict[str,Any]:
    for name,value in (("model_hash",model_hash),("code_snapshot_hash",code_snapshot_hash),("global_trial_ledger_hash",global_trial_ledger_hash)):
        if not valid(value): raise ValueError(f'invalid {name}')
    timestamp=sealed_at or dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds').replace('+00:00','Z')
    parsed=dt.datetime.fromisoformat(timestamp.replace('Z','+00:00'))
    if parsed.tzinfo is None: raise ValueError('sealed_at requires timezone')
    payload={
        'schema':'warroom.v95.forecast_seal.v1','sealed_at':timestamp,
        'predictor_manifest_hash':sha(predictor_manifest),'projection_file_hash':sha(projections),
        'model_hash':model_hash.lower(),'code_snapshot_hash':code_snapshot_hash.lower(),
        'global_trial_ledger_hash':global_trial_ledger_hash.lower(),
        'capital_permission':'BLOCKED',
        'claim_limit':'Seal proves pre-outcome immutability only, not predictive validity.'
    }
    payload['seal_hash']=hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    return payload

def main()->None:
    p=argparse.ArgumentParser(); p.add_argument('--predictor-manifest',required=True);p.add_argument('--projections',required=True)
    p.add_argument('--model-hash',required=True);p.add_argument('--code-snapshot-hash',required=True);p.add_argument('--global-trial-ledger-hash',required=True)
    p.add_argument('--sealed-at');p.add_argument('--out',required=True);a=p.parse_args()
    result=build(predictor_manifest=Path(a.predictor_manifest),projections=Path(a.projections),model_hash=a.model_hash,code_snapshot_hash=a.code_snapshot_hash,global_trial_ledger_hash=a.global_trial_ledger_hash,sealed_at=a.sealed_at)
    Path(a.out).write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
