from __future__ import annotations
import hashlib, json
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import norm

ROOT = Path(__file__).resolve().parents[2]
P = ROOT/'research_v65/protocols/V65_STABILITY_FALSIFICATION_PROTOCOL_FROZEN.json'
D = ROOT/'research_v58/data/PredictorLSretWide.csv'
O = ROOT/'research_v65/results/V65_STABILITY_FALSIFICATION_RESULTS.json'
L = ROOT/'research_v65/ledgers/V65_STABILITY_FALSIFICATION_LEDGER.csv'
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
proto=json.loads(P.read_text())
assert proto['input_sha256']==sha(D)
raw=pd.read_csv(D)
raw['date']=pd.to_datetime(raw['date'])
for c in raw.columns[1:]: raw[c]=pd.to_numeric(raw[c],errors='coerce')/100.0
raw=raw.set_index('date').sort_index()
controls=proto['factor_controls']
hurdle=float(proto['hurdle_monthly_decimal'])
z=float(norm.ppf(1-proto['familywise_alpha_one_sided']/proto['global_family_count']))
rng=np.random.default_rng(proto['bootstrap_seed'])

def candidate(spec):
    return raw[spec['members']].mean(axis=1,skipna=False).rename(spec['id'])

def alpha_test(series,start,end,reverse=False):
    s=(-series if reverse else series)-hurdle
    df=pd.concat([s.rename('candidate'),raw[controls]],axis=1).loc[start:end].dropna()
    if len(df)<60:
        return {'n':int(len(df)),'pass':False,'reason':'INSUFFICIENT'}
    y=df.pop('candidate'); X=sm.add_constant(df,has_constant='add')
    r=sm.OLS(y,X).fit(cov_type='HAC',cov_kwds={'maxlags':proto['hac_lag']},use_t=False)
    a=float(r.params['const']); se=float(r.bse['const']); lb=a-z*se
    return {'n':int(r.nobs),'alpha_monthly':a,'hac_se':se,'hac_t':a/se if se else None,
            'global_simultaneous_lower_bound':lb,'pass':bool(a>0 and lb>0)}

def rolling_stats(series,start,end):
    x=(series.loc[start:end]-hurdle).dropna()
    roll=x.rolling(proto['rolling_window_months'],min_periods=proto['rolling_window_months']).mean().dropna()
    share=float((roll>0).mean()) if len(roll) else 0.0
    return {'window_months':proto['rolling_window_months'],'n_windows':int(len(roll)),
            'positive_share':share,'minimum_mean':float(roll.min()) if len(roll) else None,
            'median_mean':float(roll.median()) if len(roll) else None,
            'pass':bool(share>=proto['rolling_positive_share_min'])}

def yearly_stats(series,start,end):
    x=(series.loc[start:end]-hurdle).dropna()
    g=x.groupby(x.index.year).agg(['mean','sum','count'])
    g=g[g['count']>=proto['minimum_months_per_calendar_year']]
    pos_share=float((g['mean']>0).mean()) if len(g) else 0.0
    pos_sums=g.loc[g['sum']>0,'sum']
    concentration=float(pos_sums.max()/pos_sums.sum()) if len(pos_sums) and pos_sums.sum()>0 else 1.0
    return {'eligible_years':int(len(g)),'positive_year_share':pos_share,
            'maximum_single_positive_year_profit_share':concentration,
            'yearly':{str(int(y)):{'mean':float(row['mean']),'sum':float(row['sum']),'months':int(row['count'])}
                      for y,row in g.iterrows()},
            'sign_pass':bool(pos_share>=proto['positive_calendar_year_share_min']),
            'concentration_pass':bool(concentration<=proto['maximum_single_year_profit_share'])}

def loo_stats(series,start,end):
    x=(series.loc[start:end]-hurdle).dropna()
    years=[]
    counts=x.groupby(x.index.year).size()
    eligible=[int(y) for y,n in counts.items() if n>=proto['minimum_months_per_calendar_year']]
    for y in eligible:
        zser=x[x.index.year!=y]
        years.append({'left_out_year':y,'mean':float(zser.mean()),'positive':bool(zser.mean()>0)})
    share=float(np.mean([r['positive'] for r in years])) if years else 0.0
    return {'eligible_years':len(years),'positive_share':share,'details':years,
            'pass':bool(share>=proto['leave_one_year_out_positive_share_min'])}

def moving_block_boot(series,start,end):
    x=(series.loc[start:end]-hurdle).dropna().to_numpy(float)
    n=len(x); b=int(proto['moving_block_length_months']); reps=int(proto['bootstrap_replications'])
    if n<b or n<60: return {'n':n,'pass':False,'reason':'INSUFFICIENT'}
    starts=np.arange(0,n-b+1)
    means=np.empty(reps)
    blocks_needed=int(np.ceil(n/b))
    for i in range(reps):
        idx_starts=rng.choice(starts,size=blocks_needed,replace=True)
        sample=np.concatenate([x[j:j+b] for j in idx_starts])[:n]
        means[i]=sample.mean()
    prob=float((means>0).mean())
    return {'n':n,'block_length':b,'replications':reps,'positive_probability':prob,
            'bootstrap_mean':float(means.mean()),'p025':float(np.quantile(means,0.025)),
            'p50':float(np.quantile(means,0.5)),'p975':float(np.quantile(means,0.975)),
            'pass':bool(prob>=proto['bootstrap_positive_probability_min'])}

def split_eval(series,start,end):
    a=alpha_test(series,start,end)
    rev=alpha_test(series,start,end,reverse=True)
    rolling=rolling_stats(series,start,end)
    yearly=yearly_stats(series,start,end)
    loo=loo_stats(series,start,end)
    boot=moving_block_boot(series,start,end)
    reverse_pass=not rev.get('pass',False)
    allpass=bool(a.get('pass',False) and rolling['pass'] and yearly['sign_pass'] and yearly['concentration_pass'] and loo['pass'] and boot['pass'] and reverse_pass)
    return {'primary_alpha':a,'rolling':rolling,'calendar_year':yearly,'leave_one_year_out':loo,
            'moving_block_bootstrap':boot,'reverse_sign_primary_alpha':rev,'reverse_sign_control_pass':reverse_pass,
            'all_split_gates_pass':allpass}

rows=[]; details={}
for spec in proto['candidates']:
    s=candidate(spec)
    val=split_eval(s,*proto['validation']); lock=split_eval(s,*proto['lockbox'])
    final=bool(val['all_split_gates_pass'] and lock['all_split_gates_pass'])
    details[spec['id']]={'definition':spec,'validation':val,'lockbox':lock,'stability_pass':final}
    rows.append({'candidate':spec['id'],'validation_pass':val['all_split_gates_pass'],'lockbox_pass':lock['all_split_gates_pass'],
                 'stability_pass':final,'validation_alpha_lb':val['primary_alpha'].get('global_simultaneous_lower_bound'),
                 'lockbox_alpha_lb':lock['primary_alpha'].get('global_simultaneous_lower_bound'),
                 'validation_rolling_positive_share':val['rolling']['positive_share'],
                 'lockbox_rolling_positive_share':lock['rolling']['positive_share'],
                 'validation_bootstrap_positive_probability':val['moving_block_bootstrap'].get('positive_probability'),
                 'lockbox_bootstrap_positive_probability':lock['moving_block_bootstrap'].get('positive_probability'),
                 'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
led=pd.DataFrame(rows).sort_values(['stability_pass','lockbox_alpha_lb'],ascending=[False,False])
led.to_csv(L,index=False)
out={'schema':'warroom.v65.stability_falsification.results.v1','protocol_sha256':sha(P),'input_sha256':sha(D),
     'global_zcrit':z,'candidate_count':len(rows),'stability_pass_count':int(led.stability_pass.sum()),
     'stability_survivors':led.loc[led.stability_pass,'candidate'].tolist(),'details':details,
     'claim_limit':proto['claim_limit'],'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
O.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:out[k] for k in ['candidate_count','stability_pass_count','stability_survivors','global_zcrit']},indent=2))
print(led.to_string(index=False))
