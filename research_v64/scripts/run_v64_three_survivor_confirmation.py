from __future__ import annotations
import hashlib,json
from pathlib import Path
import numpy as np,pandas as pd
import statsmodels.api as sm
from scipy.stats import norm
ROOT=Path(__file__).resolve().parents[2]
P=ROOT/'research_v64/protocols/V64_THREE_SURVIVOR_CONFIRMATION_PROTOCOL_FROZEN.json'
OUT=ROOT/'research_v64/results/V64_THREE_SURVIVOR_CONFIRMATION_RESULTS.json'
LED=ROOT/'research_v64/ledgers/V64_PROVEN_CLAIM_LEDGER.csv'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load():
 d=pd.read_csv(ROOT/'research_v58/data/PredictorLSretWide.csv');d['date']=pd.to_datetime(d['date'])
 for c in d.columns[1:]:d[c]=pd.to_numeric(d[c],errors='coerce')/100.0
 return d

def reg(df,y,controls,z,hurdle=0):
 x=df[[y]+controls].dropna().copy(); n=len(x)
 if n<12:return {'n':n}
 Y=x[y]-hurdle; X=sm.add_constant(x[controls],has_constant='add')
 fit=sm.OLS(Y,X).fit(cov_type='HAC',cov_kwds={'maxlags':6},use_t=False)
 a=float(fit.params['const']);se=float(fit.bse['const'])
 return {'n':n,'alpha_monthly':a,'annualized_alpha':a*12,'hac_se':se,'hac_t':a/se if se else None,'simultaneous_lower_bound':a-z*se,
         'raw_mean_monthly':float(Y.mean()),'raw_annualized_mean':float(Y.mean()*12)}

def loo_decades(df,y,controls):
 z=norm.ppf(.95)
 decades=sorted(set((df['date'].dt.year//10)*10))
 vals=[]
 for dec in decades:
  sub=df[(df['date'].dt.year//10)*10!=dec]
  q=reg(sub,y,controls,z,0)
  if q.get('n',0)>=12: vals.append({'excluded_decade':int(dec),'alpha_monthly':q['alpha_monthly']})
 return {'runs':vals,'min_alpha_monthly':min((x['alpha_monthly'] for x in vals),default=None)}

def main():
 proto=json.loads(P.read_text());d=load(); cand=proto['candidates']; ctr=proto['factor_controls'];z=float(norm.ppf(1-0.05/12))
 orig=proto['tests']['original_post_sample_confirmation']['splits'];modern=proto['tests']['modern_all_stock_confirmation']
 rows=[];results={}
 for c in cand:
  results[c]={'original':{},'modern':{}}
  for view,spans in [('original',orig[c]),('modern',modern)]:
   pass_all=True
   for split,(a,b) in spans.items():
    sub=d[(d.date>=a)&(d.date<=b)]
    costs={str(h):reg(sub,c,ctr,z,h) for h in [0,0.001,0.0025]}
    q=costs['0']; passed=q.get('n',0)>=24 and q['alpha_monthly']>0 and q['simultaneous_lower_bound']>0
    obj={'date_start':a,'date_end':b,'pass_primary':bool(passed),'hurdles':costs}
    if split=='lockbox' and view=='original':
      obj['leave_one_decade_out']=loo_decades(sub,c,ctr)
      passed=passed and obj['leave_one_decade_out']['min_alpha_monthly'] is not None and obj['leave_one_decade_out']['min_alpha_monthly']>0
      obj['pass_primary']=bool(passed)
    results[c][view][split]=obj;pass_all=pass_all and passed
   results[c][view]['claim_proven']=bool(pass_all)
  hist=results[c]['original']['claim_proven']; mod=results[c]['modern']['claim_proven']
  scope='HISTORICAL_GROSS_MARKET_CLAIM_PROVEN' if hist else 'NOT_PROVEN'
  if hist and mod: scope='MODERN_ALL_STOCK_GROSS_MARKET_CLAIM_PROVEN'
  rows.append({'claim_id':c,'historical_gross_proven':hist,'modern_all_stock_gross_proven':mod,'proof_scope':scope,
               'modern_non_micro_investable_proven':False,'stock_level_pit_selector_proven':False,'operational_ready':False,'capital_permission':'BLOCKED'})
 out={'schema':'warroom.v64.three_survivor_confirmation.results.v1','protocol_sha256':sha(P),
      'input_sha256':sha(ROOT/'research_v58/data/PredictorLSretWide.csv'),'bonferroni_one_sided_z_12':z,
      'results':results,'claim_ledger':rows,'historical_gross_proven_count':sum(r['historical_gross_proven'] for r in rows),
      'modern_all_stock_gross_proven_count':sum(r['modern_all_stock_gross_proven'] for r in rows),
      'modern_non_micro_investable_proven_count':0,'stock_level_pit_selector_proven_count':0,
      'research_live_decision_weight':0.0,'capital_permission':'BLOCKED'}
 OUT.write_text(json.dumps(out,indent=2));pd.DataFrame(rows).to_csv(LED,index=False)
 print(json.dumps({k:out[k] for k in ['historical_gross_proven_count','modern_all_stock_gross_proven_count','modern_non_micro_investable_proven_count']},indent=2))
 for r in rows:print(r)
 for c in cand:
  for view in ['original','modern']:
   print('\n',c,view,'PROVEN',results[c][view]['claim_proven'])
   for sp in ['validation','lockbox']:
    q=results[c][view][sp]['hurdles']['0'];print(sp,q.get('n'),q.get('alpha_monthly'),q.get('simultaneous_lower_bound'))
if __name__=='__main__':main()
