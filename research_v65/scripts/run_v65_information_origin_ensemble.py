from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'research_v65/protocols/V65_INFORMATION_ORIGIN_ENSEMBLE_PROTOCOL_FROZEN.json'
D=ROOT/'research_v58/data/PredictorLSretWide.csv'
O=ROOT/'research_v65/results/V65_INFORMATION_ORIGIN_ENSEMBLE_RESULTS.json'
L=ROOT/'research_v65/ledgers/V65_INFORMATION_ORIGIN_ENSEMBLE_LEDGER.csv'
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
proto=json.loads(P.read_text())
assert proto['input_sha256']==sha(D)
raw=pd.read_csv(D)
raw['date']=pd.to_datetime(raw['date'])
for c in raw.columns[1:]: raw[c]=pd.to_numeric(raw[c],errors='coerce')/100.0
raw=raw.set_index('date').sort_index()

def cap_weights(x, cap):
    x=np.asarray(x,float)
    if not np.isfinite(x).all() or x.sum()<=0: return np.full(len(x),1/len(x))
    w=x/x.sum()
    for _ in range(10):
        over=w>cap
        if not over.any(): break
        excess=(w[over]-cap).sum(); w[over]=cap
        under=~over
        if under.any(): w[under]+=excess*w[under]/w[under].sum()
    return w/w.sum()

def build_candidate(spec):
    m=spec['members']; x=raw[m].copy()
    if spec['method']=='equal_weight':
        return x.mean(axis=1,skipna=False)
    lb=int(spec['lookback_months']); mh=int(spec['min_history']); cap=float(spec['weight_cap'])
    out=[]
    for i,dt in enumerate(x.index):
        if i<mh: out.append(np.nan); continue
        hist=x.iloc[max(0,i-lb):i]
        if hist.notna().sum().min()<mh or x.iloc[i].isna().any(): out.append(np.nan); continue
        if spec['method']=='trailing_inverse_volatility':
            risk=hist.std(ddof=1).to_numpy()
        elif spec['method']=='trailing_inverse_downside_semideviation':
            vals=hist.to_numpy(); neg=np.minimum(vals,0.0); risk=np.sqrt(np.nanmean(neg*neg,axis=0))
        else: raise ValueError(spec['method'])
        inv=1/np.maximum(risk,1e-8); w=cap_weights(inv,cap)
        out.append(float(np.dot(w,x.iloc[i].to_numpy())))
    return pd.Series(out,index=x.index,name=spec['id'])

cands={s['id']:build_candidate(s) for s in proto['candidate_definitions']}
controls=proto['factor_controls']; z=float(norm.ppf(1-proto['familywise_alpha_one_sided']/proto['family_count']))

def fit(series,start,end,hurdle):
    df=pd.concat([series.rename('candidate'),raw[controls]],axis=1).loc[start:end].dropna()
    if len(df)<proto['minimum_observations']:
        return {'n':int(len(df)),'pass':False,'reason':'INSUFFICIENT_OBSERVATIONS'}
    y=df.pop('candidate')-hurdle; X=sm.add_constant(df,has_constant='add')
    r=sm.OLS(y,X).fit(cov_type='HAC',cov_kwds={'maxlags':proto['hac_lag']},use_t=False)
    a=float(r.params['const']); se=float(r.bse['const']); lb=a-z*se
    return {'n':int(r.nobs),'alpha_monthly':a,'annualized_alpha':12*a,'hac_se':se,'hac_t':a/se if se else None,'simultaneous_lower_bound':lb,'pass':bool(a>0 and lb>0),'raw_mean_monthly':float(y.mean())}

rows=[]; detail={}
for spec in proto['candidate_definitions']:
    cid=spec['id']; ser=cands[cid]
    val={str(h):fit(ser,*proto['validation'],h) for h in proto['hurdles_monthly_decimal']}
    lock={str(h):fit(ser,*proto['lockbox'],h) for h in proto['hurdles_monthly_decimal']}
    gross=val['0.0']['pass'] and lock['0.0']['pass']
    h10=val['0.001']['pass'] and lock['0.001']['pass']
    h25=val['0.0025']['pass'] and lock['0.0025']['pass']
    detail[cid]={'definition':spec,'validation':val,'lockbox':lock,'gross_pass':gross,'hurdle_10bp_pass':h10,'hurdle_25bp_pass':h25}
    rows.append({'candidate':cid,'gross_pass':gross,'hurdle_10bp_pass':h10,'hurdle_25bp_pass':h25,'validation_alpha':val['0.0'].get('alpha_monthly'),'validation_lb':val['0.0'].get('simultaneous_lower_bound'),'lockbox_alpha':lock['0.0'].get('alpha_monthly'),'lockbox_lb':lock['0.0'].get('simultaneous_lower_bound'),'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
led=pd.DataFrame(rows).sort_values(['hurdle_10bp_pass','gross_pass','lockbox_lb'],ascending=[False,False,False]); led.to_csv(L,index=False)
out={'schema':'warroom.v65.information_origin_ensemble.results.v1','protocol_sha256':sha(P),'input_sha256':sha(D),'zcrit':z,'candidate_count':len(rows),'gross_pass_count':int(led.gross_pass.sum()),'hurdle_10bp_pass_count':int(led.hurdle_10bp_pass.sum()),'hurdle_25bp_pass_count':int(led.hurdle_25bp_pass.sum()),'gross_survivors':led.loc[led.gross_pass,'candidate'].tolist(),'hurdle_10bp_survivors':led.loc[led.hurdle_10bp_pass,'candidate'].tolist(),'hurdle_25bp_survivors':led.loc[led.hurdle_25bp_pass,'candidate'].tolist(),'details':detail,'claim_limit':proto['claim_limit'],'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
O.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:out[k] for k in ['candidate_count','gross_pass_count','hurdle_10bp_pass_count','hurdle_25bp_pass_count','gross_survivors','hurdle_10bp_survivors','hurdle_25bp_survivors']},indent=2))
print(led.to_string(index=False))
