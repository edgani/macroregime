from __future__ import annotations
from pathlib import Path
import pandas as pd, numpy as np, json, math
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'/'factual'; OUT=ROOT/'FINAL_HANDOFF'

def wilson(k,n,z=1.96):
    if n<=0:return [None,None]
    p=k/n; den=1+z*z/n; c=(p+z*z/(2*n))/den; h=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return [max(0,c-h),min(1,c+h)]

def run_lengths(mask):
    runs=[]; cur=0
    for x in mask:
        if x: cur+=1
        elif cur: runs.append(cur); cur=0
    if cur:runs.append(cur)
    return runs

def calibrate():
    d=pd.read_csv(DATA/'macrodata.csv')
    d['gdp_g4']=np.log(d.realgdp/d.realgdp.shift(4))*100; d['unemp_d4']=d.unemp-d.unemp.shift(4)
    # Preregistered-style broad definition: high inflation + weak/weakening real activity.
    cond=(d.infl>=3.0) & ((d.gdp_g4<2.0)|(d.unemp_d4>0))
    future_restrictive=(d.tbilrate.shift(-4)>=d.tbilrate).astype(float); future_restrictive[d.tbilrate.shift(-4).isna()]=np.nan
    z=pd.DataFrame({'c':cond,'y':future_restrictive}).dropna(); hits=z[z.c]
    k=int(hits.y.sum()); n=int(len(hits)); p=k/n if n else None
    runs=run_lengths(cond.fillna(False).tolist())
    cal={}
    if n>=30:
        cal['POLICY_CONFLICT']={'validated':True,'probability':p,'probability_range':wilson(k,n),
          'timing':'4Q outcome calibration; current-date start timing remains event-dependent',
          'duration':f'historical condition median {float(np.median(runs)) if runs else 0:.1f} quarters; not a forecast',
          'n_condition_obs':n,'successes':k,'definition':'infl>=3% AND (real GDP YoY<2% OR unemployment YoY change>0); outcome 3m T-bill >= current after 4 quarters',
          'scope':'US quarterly 1959Q1-2009Q3; historical base-rate calibration only; structural-break risk high'}
    else:
        cal['POLICY_CONFLICT']={'validated':False,'n_condition_obs':n,'reason':'INSUFFICIENT_EPISODES'}
    (OUT/'52_SCENARIO_CALIBRATION.json').write_text(json.dumps(cal,indent=2),encoding='utf-8')
    return cal
if __name__=='__main__': print(json.dumps(calibrate(),indent=2))
