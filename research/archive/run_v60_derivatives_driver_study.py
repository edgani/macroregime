"""Frozen derivatives/flow driver research harness.

Without a real point-in-time panel this module runs only planted-signal and null controls.
Real-data invocation requires a CSV matching research_v60/protocols/V60_DERIVATIVES_PANEL_SCHEMA.json.
No result from synthetic controls is market evidence.
"""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
R=ROOT/'research_v60'
PROTOCOL=R/'protocols'/'V60_DERIVATIVES_DRIVER_PROTOCOL_FROZEN.json'
OUT=R/'results'/'V60_DERIVATIVES_HARNESS_RESULTS.json'
LEDGER=R/'ledgers'/'V60_DERIVATIVES_HARNESS_LEDGER.csv'

CANDIDATES={
 'price_momentum_baseline':lambda d:d['momentum'],
 'origin_revision':lambda d:d['origin'],
 'vulnerability_only':lambda d:d['vulnerability'],
 'signed_taker_flow':lambda d:d['signed_flow'],
 'open_interest_change':lambda d:d['oi_change'],
 'funding_crowding':lambda d:d['funding'],
 'basis_crowding':lambda d:d['basis'],
 'realized_short_liquidation':lambda d:d['short_liq'],
 'realized_long_liquidation_inverse':lambda d:-d['long_liq'],
 'origin_x_vulnerability':lambda d:d['origin']*np.maximum(d['vulnerability'],0),
 'origin_plus_signed_flow':lambda d:d['origin']+d['signed_flow'],
 'origin_vulnerability_signed':lambda d:d['origin']+d['signed_flow']+d['origin']*np.maximum(d['vulnerability'],0),
 'oi_x_signed_flow':lambda d:d['oi_change']*d['signed_flow'],
 'oi_x_funding':lambda d:d['oi_change']*d['funding'],
 'crowding_composite':lambda d:d['funding']+d['basis']+d['vulnerability'],
 'liquidation_sum':lambda d:d['short_liq']-d['long_liq'],
}

def logistic(x):return 1/(1+np.exp(-np.clip(x,-30,30)))

def make_panel(seed:int, planted:bool, n:int=12000)->pd.DataFrame:
    rng=np.random.default_rng(seed)
    origin=rng.normal(size=n)
    vulnerability=rng.normal(size=n)
    signed=.45*origin+rng.normal(scale=.9,size=n) if planted else rng.normal(size=n)
    oi=.35*vulnerability+.2*np.abs(signed)+rng.normal(scale=.9,size=n)
    funding=.45*origin+.35*vulnerability+rng.normal(scale=.9,size=n) if planted else rng.normal(size=n)
    basis=.3*origin+.25*vulnerability+rng.normal(scale=.95,size=n) if planted else rng.normal(size=n)
    momentum=rng.normal(size=n)
    if planted:
        up_logit=-3.55+1.05*origin+.60*signed+.85*origin*np.maximum(vulnerability,0)
        dn_logit=-3.55-1.05*origin-.60*signed-.85*origin*np.maximum(vulnerability,0)
    else:
        up_logit=np.full(n,-3.55);dn_logit=np.full(n,-3.55)
    up=rng.binomial(1,logistic(up_logit));down=rng.binomial(1,logistic(dn_logit))
    # Realized liquidations are generated AFTER the event. Lagging them into t prevents them
    # from masquerading as a precursor of the same event.
    short_liq=np.r_[0,up[:-1]*rng.lognormal(mean=1.2,sigma=.6,size=n-1)]
    long_liq=np.r_[0,down[:-1]*rng.lognormal(mean=1.2,sigma=.6,size=n-1)]
    return pd.DataFrame({'t':np.arange(n),'origin':origin,'vulnerability':vulnerability,'signed_flow':signed,
        'oi_change':oi,'funding':funding,'basis':basis,'momentum':momentum,'short_liq':short_liq,'long_liq':long_liq,
        'future_up_event':up,'future_down_event':down})

def block_se(diff:np.ndarray, block:int=100)->tuple[float,float,int]:
    x=np.asarray(diff,float);x=x[np.isfinite(x)]
    if len(x)<block*5:return float(np.nanmean(x)),float('inf'),0
    blocks=np.array([x[i:i+block].mean() for i in range(0,len(x)-block+1,block)])
    if len(blocks)<5:return float(x.mean()),float('inf'),len(blocks)
    return float(blocks.mean()),float(blocks.std(ddof=1)/math.sqrt(len(blocks))),len(blocks)

def evaluate(panel:pd.DataFrame,label:str)->dict:
    n=len(panel);cuts=(int(n*.6),int(n*.8));splits={'discovery':(0,cuts[0]),'validation':(cuts[0],cuts[1]),'lockbox':(cuts[1],n)}
    claims=[];m=len(CANDIDATES)*2;z=NormalDist().inv_cdf(1-.05/m)
    for target in ['future_up_event','future_down_event']:
      orient=1 if target.endswith('up_event') else -1
      for name,fn in CANDIDATES.items():
        score=np.asarray(fn(panel),float)*orient
        row={'dataset':label,'claim_id':f'{target}:{name}','target':target,'candidate':name,'bonferroni_z':z,'splits':{}}
        passes=True
        for s,(a,b) in splits.items():
            sc=score[a:b];y=panel[target].to_numpy()[a:b]
            q=np.nanquantile(sc,.90);sel=sc>=q
            base=np.nanmean(y);precision=np.nanmean(y[sel]) if sel.any() else np.nan
            # Per-observation lift representation enables block SE.
            diff=np.where(sel,y-base,0.0)/max(sel.mean(),1e-9)
            mean,se,nb=block_se(diff)
            lb=mean-z*se
            row['splits'][s]={'n':len(y),'events':int(y.sum()),'selected_n':int(sel.sum()),'base_rate':float(base),'precision':float(precision),'lift':float(precision-base),'block_mean_lift':mean,'block_se':se,'adjusted_lb':lb,'blocks':nb}
            if s in ('validation','lockbox') and not (np.isfinite(lb) and lb>0):passes=False
        row['promoted_in_control']=bool(passes)
        claims.append(row)
    return {'dataset':label,'registered_claims':len(claims),'control_survivors':sum(x['promoted_in_control'] for x in claims),'claims':claims}

def run_controls()->dict:
    planted=evaluate(make_panel(6060,True),'PLANTED_SIGNAL_CONTROL')
    null=evaluate(make_panel(6061,False),'NULL_CONTROL')
    planted_names={x['candidate'] for x in planted['claims'] if x['promoted_in_control']}
    liq_names={'realized_short_liquidation','realized_long_liquidation_inverse','liquidation_sum'}
    checks={
      'planted_origin_family_detected':bool(planted_names & {'origin_revision','origin_x_vulnerability','origin_plus_signed_flow','origin_vulnerability_signed'}),
      'null_has_zero_survivors':null['control_survivors']==0,
      'realized_liquidation_not_promoted_as_early_driver':not bool(planted_names & liq_names),
    }
    return {'schema':'warroom.v60.derivatives_harness_results','protocol_sha256':hashlib.sha256(PROTOCOL.read_bytes()).hexdigest(),
      'status':'PASS' if all(checks.values()) else 'FAIL','checks':checks,'planted':planted,'null':null,
      'market_evidence_status':'SYNTHETIC_CONTROL_ONLY_NOT_MARKET_PROOF','live_decision_weight':0.0,'capital_permission':'BLOCKED'}

def real_data_status(path:Path)->dict:
    required={'timestamp','market','symbol','close'}
    if not path.exists():return {'status':'BLOCKED_DATA_ABSENT','path':str(path),'missing':['file']}
    df=pd.read_csv(path,nrows=10)
    missing=sorted(required-set(df.columns))
    return {'status':'BLOCKED_SCHEMA_MISMATCH' if missing else 'REAL_DATA_RUNNER_NOT_OPENED_WITHOUT_FROZEN_SPLIT_MANIFEST','path':str(path),'missing':missing,'columns':list(df.columns)}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--real-panel',type=Path);args=ap.parse_args()
    result=run_controls()
    if args.real_panel:result['real_data']=real_data_status(args.real_panel)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    rows=[]
    for ds in ['planted','null']:
      for c in result[ds]['claims']:
        rows.append({'dataset':c['dataset'],'claim_id':c['claim_id'],'candidate':c['candidate'],'target':c['target'],'promoted_in_control':c['promoted_in_control'],
          'validation_lb':c['splits']['validation']['adjusted_lb'],'lockbox_lb':c['splits']['lockbox']['adjusted_lb'],'market_evidence_status':'SYNTHETIC_ONLY','live_decision_weight':0.0,'capital_permission':'BLOCKED'})
    pd.DataFrame(rows).to_csv(LEDGER,index=False)
    print(json.dumps({k:v for k,v in result.items() if k not in ('planted','null')},indent=2))
    return 0 if result['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(main())
