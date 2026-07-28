"""Point-in-time carry research admission and anti-overfit preparation for V10.1.

The input panel must be created without look-ahead. This module does not download revised data and
pretend it was known historically. It prepares a complete registered candidate family for the V9.6
anti-overfit gate. A software PASS is never a market-proof PASS.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from typing import Any
import pandas as pd

HERE=Path(__file__).resolve().parent
POLICY=json.loads((HERE/'V101_CARRY_POLICY.json').read_text())
REQUIRED={'timestamp','available_at','pair','base_rate','quote_rate','stress_score','pair_spot_return','carry_accrual_return','execution_cost_return','regime','point_in_time','source_class'}
CANDIDATES={
 'carry_core_v101':{'min_spread':.75,'max_stress':.60,'parameter_index':1.0},
 'carry_conservative_v101':{'min_spread':1.50,'max_stress':.45,'parameter_index':0.0},
 'carry_broad_v101':{'min_spread':.50,'max_stress':.70,'parameter_index':2.0},
}

def _bool(v:Any)->bool:
 if isinstance(v,bool):return v
 if str(v).strip().lower() in {'true','1','yes'}:return True
 if str(v).strip().lower() in {'false','0','no',''}:return False
 raise ValueError(f'invalid boolean {v!r}')

def admit(path:Path)->pd.DataFrame:
 f=pd.read_csv(path);missing=REQUIRED-set(f.columns)
 if missing:raise ValueError('missing columns: '+', '.join(sorted(missing)))
 f['timestamp']=pd.to_datetime(f['timestamp'],utc=True,errors='coerce');f['available_at']=pd.to_datetime(f['available_at'],utc=True,errors='coerce')
 if f[['timestamp','available_at']].isna().any().any():raise ValueError('invalid timestamps')
 if (f['available_at']>f['timestamp']).any():raise ValueError('look-ahead: input available after decision timestamp')
 f['point_in_time']=f['point_in_time'].map(_bool)
 if not f['point_in_time'].all():raise ValueError('all rows must be point-in-time admitted')
 if not f['source_class'].astype(str).eq('POINT_IN_TIME_OFFICIAL').all():raise ValueError('source_class must be POINT_IN_TIME_OFFICIAL')
 for c in ('base_rate','quote_rate','stress_score','pair_spot_return','carry_accrual_return','execution_cost_return'):
  f[c]=pd.to_numeric(f[c],errors='coerce')
  if f[c].isna().any() or not f[c].map(math.isfinite).all():raise ValueError('invalid numeric '+c)
 if (f['stress_score'].lt(0)|f['stress_score'].gt(1)).any():raise ValueError('stress_score outside [0,1]')
 if f.duplicated(['timestamp','pair']).any():raise ValueError('duplicate timestamp/pair')
 return f.sort_values(['timestamp','pair']).reset_index(drop=True)

def prepare(panel:Path,out:Path)->dict[str,Any]:
 f=admit(panel);rows=[]
 for _,r in f.iterrows():
  spread=float(r.base_rate-r.quote_rate);sgn=1.0 if spread>=0 else -1.0;carry=abs(spread)
  realised=sgn*float(r.pair_spot_return)+float(r.carry_accrual_return)-float(r.execution_cost_return)
  for cid,cfg in CANDIDATES.items():
   active=carry>=cfg['min_spread'] and float(r.stress_score)<=cfg['max_stress']
   net=realised if active else 0.0
   stress_net=net-(float(r.execution_cost_return) if active else 0.0)
   rows.append({'timestamp':r.timestamp.isoformat(),'candidate_id':cid,'net_return':net,'stress_return':stress_net,'benchmark_return':0.0,'regime':str(r.regime),'family_id':'fx_carry_v101','parameter_index':cfg['parameter_index']})
 out.parent.mkdir(parents=True,exist_ok=True);pd.DataFrame(rows).to_csv(out,index=False)
 report={'schema':'warroom.v101.carry_return_matrix.v1','input_rows':len(f),'output_rows':len(rows),'candidate_family':list(CANDIDATES),'point_in_time_admitted':True,'capital_permission':'BLOCKED_PENDING_ANTI_OVERFIT_AND_PROSPECTIVE_PROOF'}
 report['hash']=hashlib.sha256(out.read_bytes()).hexdigest();return report

def main():
 p=argparse.ArgumentParser();p.add_argument('panel');p.add_argument('--out',default='runtime/v101_carry/candidate_returns.csv');a=p.parse_args();print(json.dumps(prepare(Path(a.panel),Path(a.out)),indent=2))
if __name__=='__main__':main()
