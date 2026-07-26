from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'research_v64/protocols/V64_MODERN_212_FACTOR_CONFIRMATION_PROTOCOL_FROZEN.json'
G=ROOT/'research_v64/protocols/V64_MODERN_212_FACTOR_GRID_FROZEN.csv'
D=ROOT/'research_v58/data/PredictorLSretWide.csv'
O=ROOT/'research_v64/results/V64_MODERN_212_FACTOR_CONFIRMATION_RESULTS.json'
L=ROOT/'research_v64/ledgers/V64_MODERN_212_FACTOR_CONFIRMATION_LEDGER.csv'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
proto=json.loads(P.read_text()); assert proto['candidate_grid_sha256']==sha(G) and proto['input_sha256']==sha(D)
cands=pd.read_csv(G).candidate.tolist(); controls=proto['controls']
df=pd.read_csv(D)
date_col=next(c for c in df.columns if c.lower()=='date')
df[date_col]=pd.to_datetime(df[date_col].astype(str),errors='coerce')
df=df.set_index(date_col).sort_index()/100.0
z=float(norm.ppf(1-0.05/(len(cands)*2)))

def fit(name,start,end,hurdle=0.0):
    cols=[name]+[c for c in controls if c in df.columns and c!=name]
    x=df.loc[start:end,cols].dropna().copy()
    if len(x) < 36:
        return {'n':int(len(x)),'alpha_monthly':None,'annualized_alpha':None,'hac_se':None,'hac_t':None,'simultaneous_lower_bound':None,'pass':False,'reason':'INSUFFICIENT_OBSERVATIONS'}
    y=x.pop(name)-hurdle
    X=sm.add_constant(x,has_constant='add')
    r=sm.OLS(y,X).fit(cov_type='HAC',cov_kwds={'maxlags':6})
    a=float(r.params['const']); se=float(r.bse['const'])
    return {'n':int(r.nobs),'alpha_monthly':a,'annualized_alpha':12*a,'hac_se':se,'hac_t':a/se if se else None,'simultaneous_lower_bound':a-z*se,'pass':bool(a>0 and a-z*se>0)}
rows=[]; detail={}
for c in cands:
    val={str(h):fit(c,*proto['validation'],h) for h in [0.0]+proto['sensitivity_hurdles_monthly_decimal']}
    lock={str(h):fit(c,*proto['lockbox'],h) for h in [0.0]+proto['sensitivity_hurdles_monthly_decimal']}
    gross=val['0.0']['pass'] and lock['0.0']['pass']
    h10=val['0.001']['pass'] and lock['0.001']['pass']
    h25=val['0.0025']['pass'] and lock['0.0025']['pass']
    detail[c]={'validation':val,'lockbox':lock,'modern_gross_claim_pass':gross,'flat_10bp_hurdle_pass':h10,'flat_25bp_hurdle_pass':h25}
    rows.append({'candidate':c,'modern_gross_claim_pass':gross,'flat_10bp_hurdle_pass':h10,'flat_25bp_hurdle_pass':h25,'val_alpha':val['0.0']['alpha_monthly'],'val_lb':val['0.0']['simultaneous_lower_bound'],'lock_alpha':lock['0.0']['alpha_monthly'],'lock_lb':lock['0.0']['simultaneous_lower_bound'],'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
ledger=pd.DataFrame(rows).sort_values(['modern_gross_claim_pass','lock_lb','val_lb'],ascending=[False,False,False])
ledger.to_csv(L,index=False)
out={'schema':'warroom.v64.modern_212_factor_confirmation.results.v1','protocol_sha256':sha(P),'grid_sha256':sha(G),'input_sha256':sha(D),'zcrit_one_sided_bonferroni':z,'candidate_count':len(cands),'modern_gross_claims_passed':int(ledger.modern_gross_claim_pass.sum()),'flat_10bp_hurdle_passed':int(ledger.flat_10bp_hurdle_pass.sum()),'flat_25bp_hurdle_passed':int(ledger.flat_25bp_hurdle_pass.sum()),'survivors':ledger[ledger.modern_gross_claim_pass].candidate.tolist(),'details':detail,'claim_limit':proto['claim_limit'],'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
O.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:out[k] for k in ['candidate_count','modern_gross_claims_passed','flat_10bp_hurdle_passed','flat_25bp_hurdle_passed','survivors']},indent=2))
