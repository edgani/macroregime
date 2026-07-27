"""Install a passed, signed, hash-bound V9.6 market proof run into the dashboard registry."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, tempfile
from pathlib import Path
from typing import Any

HERE=Path(__file__).resolve().parent
REGISTRY=HERE/'component_registry_v96.json'
MARKETS={'us','idx','commodity','fx','crypto'}

def sha(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def install(market:str,proof_run:Path)->dict[str,Any]:
    market=market.lower().strip()
    if market not in MARKETS: raise ValueError('unsupported market')
    run=json.loads(proof_run.read_text(encoding='utf-8'))
    reasons=[]
    if run.get('schema')!='warroom.v96.blind_proof_run.v1':reasons.append('wrong schema')
    if str(run.get('market') or '').lower()!=market:reasons.append('market mismatch')
    if run.get('trading_ready') is not True or run.get('capital_permission')!='LIMITED_PRODUCTION_ELIGIBLE':reasons.append('proof run did not pass')
    if run.get('errors'):reasons.append('proof run contains errors')
    if (run.get('signed_receipt_verification') or {}).get('valid') is not True:reasons.append('signed receipt invalid')
    if reasons: raise ValueError('; '.join(reasons))
    target=HERE/'runtime'/'v96_proof_runs'/f'{market}.json';target.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.NamedTemporaryFile('wb',delete=False,dir=target.parent) as tmp:
        tmp.write(proof_run.read_bytes());temp=Path(tmp.name)
    os.replace(temp,target);digest=sha(target)
    registry=json.loads(REGISTRY.read_text(encoding='utf-8'));component=f'{market}_bottleneck_price_projection_v96'
    if component not in registry.get('components',{}):raise ValueError('component missing from registry')
    registry['components'][component]['proof_run_path']=target.relative_to(HERE).as_posix();registry['components'][component]['proof_run_sha256']=digest
    temp_registry=REGISTRY.with_suffix('.json.tmp');temp_registry.write_text(json.dumps(registry,indent=2),encoding='utf-8');os.replace(temp_registry,REGISTRY)
    return {'schema':'warroom.v96.proof_run_install.v1','market':market,'component':component,'path':target.relative_to(HERE).as_posix(),'sha256':digest,'installed':True,'capital_permission':'PENDING_GLOBAL_REGISTRY_ADJUDICATION'}

def main()->None:
    p=argparse.ArgumentParser();p.add_argument('--market',required=True);p.add_argument('--proof-run',required=True);a=p.parse_args();print(json.dumps(install(a.market,Path(a.proof_run)),indent=2))
if __name__=='__main__':main()
