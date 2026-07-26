from __future__ import annotations
import json, hashlib, math, pathlib, datetime
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm

ROOT=pathlib.Path(__file__).resolve().parents[2]
PROTOCOL=ROOT/'research_v66/protocols/V66_TSMOM_CRISIS_DEFENSE_PROTOCOL_FROZEN.json'
OUT=ROOT/'research_v66/results/V66_TSMOM_CRISIS_DEFENSE_RESULTS.json'


def file_sha(p: pathlib.Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()

def load_tsmom()->pd.Series:
    p=ROOT/'research_v58/data/Time-Series-Momentum-Factors-Monthly.xlsx'
    raw=pd.read_excel(p,sheet_name='TSMOM Factors',header=None)
    headers=list(raw.iloc[17,1:6])
    df=raw.iloc[18:,0:6].copy(); df.columns=['date']+headers
    df['date']=pd.to_datetime(df['date'],errors='coerce')
    for c in headers: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['date']).set_index('date')['TSMOM'].dropna().sort_index()

def load_global_mkt()->pd.Series:
    p=ROOT/'research_v58/data/Quality-Minus-Junk-Factors-Monthly.xlsx'
    raw=pd.read_excel(p,sheet_name='MKT',header=None)
    headers=list(raw.iloc[18,:30])
    df=raw.iloc[19:,:30].copy(); df.columns=headers
    df['DATE']=pd.to_datetime(df['DATE'],errors='coerce')
    for c in headers[1:]: df[c]=pd.to_numeric(df[c],errors='coerce')
    return df.dropna(subset=['DATE']).set_index('DATE')['Global'].dropna().sort_index()

def max_drawdown(r: np.ndarray)->float:
    wealth=np.cumprod(1.0+np.asarray(r,float))
    peak=np.maximum.accumulate(wealth)
    return float(np.min(wealth/peak-1.0)) if len(wealth) else float('nan')

def es5(r: np.ndarray)->float:
    x=np.sort(np.asarray(r,float))
    k=max(1,int(math.ceil(0.05*len(x))))
    return float(x[:k].mean())

def hac_mean(x: np.ndarray,lags:int=6):
    x=np.asarray(x,float)
    model=sm.OLS(x,np.ones((len(x),1))).fit(cov_type='HAC',cov_kwds={'maxlags':lags})
    return float(model.params[0]),float(model.bse[0]),float(model.tvalues[0])

def cp_lower(k:int,n:int,alpha:float)->float:
    if k<=0:return 0.0
    return float(stats.beta.ppf(alpha,k,n-k+1))

def moving_blocks(n:int, block:int, reps:int, rng:np.random.Generator):
    blocks=int(math.ceil(n/block))
    for _ in range(reps):
        starts=rng.integers(0,n,size=blocks)
        idx=np.concatenate([(np.arange(s,s+block)%n) for s in starts])[:n]
        yield idx

def bootstrap_stats(mkt:np.ndarray,ts:np.ndarray,reps:int=20000,block:int=12,seed:int=6601):
    rng=np.random.default_rng(seed)
    stress_means=[]; es_imps=[]; dd_imps=[]
    for idx in moving_blocks(len(mkt),block,reps,rng):
        m=mkt[idx]; t=ts[idx]
        st=t[m<=-0.05]
        if len(st)>=4: stress_means.append(float(st.mean()))
        ov=0.8*m+0.2*t
        es_imps.append(es5(ov)-es5(m))
        dd_imps.append(max_drawdown(ov)-max_drawdown(m))
    def q(v,p):return float(np.quantile(v,p))
    return {
      'stress_mean_lower_0_25pct':q(stress_means,0.0025) if stress_means else None,
      'stress_mean_positive_probability':float(np.mean(np.array(stress_means)>0)) if stress_means else None,
      'es_improvement_lower_0_25pct':q(es_imps,0.0025),
      'es_improvement_positive_probability':float(np.mean(np.array(es_imps)>0)),
      'drawdown_improvement_lower_0_25pct':q(dd_imps,0.0025),
      'drawdown_improvement_positive_probability':float(np.mean(np.array(dd_imps)>0)),
      'effective_reps_stress':len(stress_means),
    }

def eval_split(df:pd.DataFrame,start:str,end:str|None,reverse:bool=False):
    x=df.loc[pd.Timestamp(start): (pd.Timestamp(end) if end else df.index.max())].copy()
    m=x['mkt'].to_numpy(float)
    t=x['tsmom'].to_numpy(float)
    if reverse:t=-t
    t10=t-0.001
    t25=t-0.0025
    stress=m<=-0.05
    st10=t10[stress]; st25=t25[stress]
    alpha=0.01/4
    mean,se,tval=hac_mean(st10,lags=min(6,max(0,len(st10)-1)))
    z=float(stats.norm.ppf(1-alpha))
    lb=mean-z*se
    k=int(np.sum(st10>0)); n=len(st10)
    hit=k/n if n else float('nan')
    hit_lb=cp_lower(k,n,alpha) if n else float('nan')
    overlay=0.8*m+0.2*t10
    mdd_base=max_drawdown(m); mdd_overlay=max_drawdown(overlay)
    es_base=es5(m); es_overlay=es5(overlay)
    b=bootstrap_stats(m,t10)
    return {
      'start':str(x.index.min().date()),'end':str(x.index.max().date()),'n_months':len(x),
      'stress_months':n,'stress_threshold':-0.05,
      'stress_net_10bps':{'mean_monthly':mean,'annualized_mean':12*mean,'hac_se':se,'hac_t':tval,'familywise_z':z,'familywise_lower_bound':lb,'hit_rate':hit,'clopper_pearson_familywise_lower':hit_lb},
      'stress_net_25bps':{'mean_monthly':float(st25.mean()) if n else None,'hit_rate':float(np.mean(st25>0)) if n else None},
      'portfolio_80_20_net_10bps':{
        'base_max_drawdown':mdd_base,'overlay_max_drawdown':mdd_overlay,'drawdown_improvement':mdd_overlay-mdd_base,
        'base_es5':es_base,'overlay_es5':es_overlay,'es5_improvement':es_overlay-es_base,
        'base_annualized_mean':float(m.mean()*12),'overlay_annualized_mean':float(overlay.mean()*12),
        'base_annualized_vol':float(m.std(ddof=1)*math.sqrt(12)),'overlay_annualized_vol':float(overlay.std(ddof=1)*math.sqrt(12)),
      },
      'moving_block_bootstrap':b,
      'gates':{
       'min_stress_months':n>=8,
       'stress_mean_familywise_lb_positive':lb>0,
       'stress_hit_rate_above_half':hit>0.5,
       'stress_hit_familywise_lb_above_half':hit_lb>0.5,
       'es5_improvement_positive':(es_overlay-es_base)>0,
       'drawdown_improvement_ge_5pct':(mdd_overlay-mdd_base)>=0.05,
       'bootstrap_stress_lb_positive':b['stress_mean_lower_0_25pct'] is not None and b['stress_mean_lower_0_25pct']>0,
       'bootstrap_es_lb_positive':b['es_improvement_lower_0_25pct']>0,
       'bootstrap_dd_lb_positive':b['drawdown_improvement_lower_0_25pct']>0,
      }
    }

def main():
    protocol=json.load(open(PROTOCOL))
    ts=load_tsmom(); mkt=load_global_mkt()
    df=pd.concat([mkt.rename('mkt'),ts.rename('tsmom')],axis=1).dropna().sort_index()
    val=eval_split(df,'2010-01-01','2017-12-31')
    lock=eval_split(df,'2018-01-01',None)
    rv=eval_split(df,'2010-01-01','2017-12-31',True)
    rl=eval_split(df,'2018-01-01',None,True)
    required=['min_stress_months','stress_mean_familywise_lb_positive','stress_hit_rate_above_half','es5_improvement_positive','drawdown_improvement_ge_5pct','bootstrap_stress_lb_positive','bootstrap_es_lb_positive']
    primary_pass=all(val['gates'][k] and lock['gates'][k] for k in required)
    reverse_fails=not all(rv['gates'][k] and rl['gates'][k] for k in required)
    result={
      'schema':'warroom.v66.crisis_defense_results.v1','created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'protocol_path':str(PROTOCOL.relative_to(ROOT)),'protocol_file_sha256':file_sha(PROTOCOL),'embedded_protocol_sha256':protocol['protocol_sha256'],
      'source_hashes':{
       'tsmom':file_sha(ROOT/'research_v58/data/Time-Series-Momentum-Factors-Monthly.xlsx'),
       'global_mkt':file_sha(ROOT/'research_v58/data/Quality-Minus-Junk-Factors-Monthly.xlsx')},
      'available_range':[str(df.index.min().date()),str(df.index.max().date())],
      'validation':val,'lockbox':lock,'reverse_sign_validation':rv,'reverse_sign_lockbox':rl,
      'adjudication':{
        'primary_pass':primary_pass,'reverse_sign_control_fails':reverse_fails,
        'scoped_market_claim':'SUPPORTED' if primary_pass and reverse_fails else 'NOT_PROVEN',
        'decision_permission':'RISK_REDUCTION_OR_DIVERSIFYING_SLEEVE_ONLY' if primary_pass and reverse_fails else 'NONE',
        'ticker_selection_permission':False,'capital_permission':'BLOCKED_PENDING_EXACT_EXECUTABLE_REPLICATION',
        'live_decision_weight':0.0,
      },
      'claim_limit':protocol['claim_limit']
    }
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,indent=2,sort_keys=True))
    print(json.dumps(result['adjudication'],indent=2))
    print('validation',val['gates'])
    print('lockbox',lock['gates'])
    print('stress',val['stress_net_10bps'],lock['stress_net_10bps'])
    print('overlay',val['portfolio_80_20_net_10bps'],lock['portfolio_80_20_net_10bps'])

if __name__=='__main__':main()
