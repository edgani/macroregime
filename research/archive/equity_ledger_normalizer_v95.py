"""Normalize a user-owned live account equity export into the strict V9.5 equity schema."""
from __future__ import annotations
import argparse, hashlib, hmac, json, os
from pathlib import Path
from typing import Any
import pandas as pd
from realized_performance_gate_v95 import EQUITY_REQUIRED, LIVE_SOURCES, _strict_bool


def sha(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def pseudonym(value: Any,salt:str)->str:
    text=str(value).strip()
    if not text: raise ValueError('identifier is blank')
    return hmac.new(salt.encode(),text.encode(),hashlib.sha256).hexdigest()

def normalize(input_path:Path,mapping_path:Path,output_path:Path,*,salt:str)->dict[str,Any]:
    if len(salt)<16: raise ValueError('WARROOM_ID_HASH_SALT must contain at least 16 characters')
    mapping=json.loads(mapping_path.read_text(encoding='utf-8'))
    if mapping.get('schema')!='warroom.v95.equity_mapping.v1': raise ValueError('unsupported mapping schema')
    frame=pd.read_csv(input_path); columns=mapping.get('columns') or {}; constants=mapping.get('constants') or {}; out=pd.DataFrame(index=frame.index)
    direct=[c for c in EQUITY_REQUIRED if c not in {'account_id_hash','source_snapshot_hash'}]
    for field in direct:
        source=columns.get(field)
        if source:
            if source not in frame.columns: raise ValueError(f'missing source column {source!r} for {field}')
            out[field]=frame[source]
        elif field in constants: out[field]=constants[field]
        else: raise ValueError(f'missing mapping for {field}')
    account_source=columns.get('account_id')
    if account_source:
        if account_source not in frame.columns: raise ValueError(f'missing account column {account_source!r}')
        out['account_id_hash']=frame[account_source].map(lambda x:pseudonym(x,salt))
    elif 'account_id' in constants: out['account_id_hash']=pseudonym(constants['account_id'],salt)
    else: raise ValueError('missing mapping for account_id')
    out['source_snapshot_hash']=sha(input_path)
    out['timestamp']=pd.to_datetime(out['timestamp'],utc=True,errors='raise').dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    for field in ('net_liquidation_value','stress_net_liquidation_value','external_cash_flow'): out[field]=pd.to_numeric(out[field],errors='raise')
    for field in ('is_live','paper','synthetic'): out[field]=out[field].map(_strict_bool)
    out['execution_source']=out['execution_source'].astype(str).str.upper().str.strip()
    if not out['execution_source'].isin(LIVE_SOURCES).all(): raise ValueError('invalid execution_source')
    out=out[EQUITY_REQUIRED]; output_path.parent.mkdir(parents=True,exist_ok=True);out.to_csv(output_path,index=False)
    receipt={'schema':'warroom.v95.equity_normalization_receipt.v1','input_sha256':sha(input_path),'mapping_sha256':sha(mapping_path),'output_path':output_path.name,'output_sha256':sha(output_path),'rows':len(out),'account_id_hashes':sorted(set(out.account_id_hash.astype(str))),'capital_permission':'BLOCKED_PENDING_BOUND_PROOF','claim_limit':'Normalization is not profitability proof.'}
    receipt['receipt_hash']=hashlib.sha256(json.dumps(receipt,sort_keys=True,separators=(',',':')).encode()).hexdigest();output_path.with_suffix(output_path.suffix+'.receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8');return receipt

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--mapping',required=True);p.add_argument('--output',required=True);a=p.parse_args();print(json.dumps(normalize(Path(a.input),Path(a.mapping),Path(a.output),salt=os.getenv('WARROOM_ID_HASH_SALT','')),indent=2))
if __name__=='__main__':main()
