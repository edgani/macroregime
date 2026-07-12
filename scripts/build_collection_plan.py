from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash

def build():
    scopes=[]
    for asset in ('BTCUSDT','ETHUSDT'):
        for timeframe in ('15m','1h','4h','1d'):
            scopes.append({
              'asset':asset,'timeframe':timeframe,'venue':'BINANCE_SPOT',
              'provider_id':'BINANCE_SPOT_PUBLIC_KLINES_V1','enabled':True,
              'bootstrap_rows':500,'collector_poll_seconds':300,
              'claim_ceiling':'DESCRIPTIVE_ONLY',
            })
    payload={'plan_id':'WRV3-COLLECTION-PLAN-20260712','scopes':scopes}
    payload['plan_hash']=canonical_hash(scopes)
    return payload
if __name__=='__main__':
    out=ROOT/'config/collection_plan.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+'\n'
    if '--check' in sys.argv:
        if not out.exists() or out.read_text()!=expected: raise SystemExit('collection plan stale')
        print('PASS: collection plan')
    else: out.write_text(expected); print(out)
