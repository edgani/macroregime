from __future__ import annotations
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash
ASSETS=['SPY','QQQ','IWM','GLD','ES','NQ','CL','EURUSD','GBPUSD','USDJPY','AUDUSD','XAUUSD','XAGUSD','USOIL','BTCUSDT','ETHUSDT','IHSG']
TIMEFRAMES=['15m','1h','4h','1d']

def build():
    scopes=[]
    for asset in ASSETS:
      for tf in TIMEFRAMES:
        scopes.append({"asset":asset,"timeframe":tf,"data_status":"REQUIRED_MISSING","evidence_status":"NOT_EVALUATED"})
    return {"frozen":True,"scope_count":len(scopes),"scopes":scopes,"matrix_hash":canonical_hash(scopes)}
if __name__=='__main__':
    out=ROOT/'validation/market_matrix.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+"\n"
    if '--check' in sys.argv:
      if not out.exists() or out.read_text()!=expected: raise SystemExit('market matrix stale')
      print('PASS: market matrix')
    else: out.write_text(expected); print(out)
