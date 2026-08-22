from __future__ import annotations
from pathlib import Path
import json, math, hashlib
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/'data'/'research'
OUT=ROOT/'FINAL_HANDOFF'
OUT.mkdir(parents=True, exist_ok=True)

RNG=np.random.default_rng(20260821)

def sha256(p:Path)->str:
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20), b''): h.update(b)
    return h.hexdigest()

def trailing_z(s, w=120, minp=36):
    return (s-s.rolling(w,min_periods=minp).mean())/s.rolling(w,min_periods=minp).std()

def expanding_pct(s,minp=60):
    vals=[]; out=[]
    for v in s.to_numpy(float):
        if np.isfinite(v): vals.append(v)
        out.append(np.mean(np.asarray(vals)<=v) if np.isfinite(v) and len(vals)>=minp else np.nan)
    return pd.Series(out,index=s.index)

def fwd_dd(s,H):
    v=s.to_numpy(float); o=np.full(len(v),np.nan)
    for i in range(len(v)-H):
        w=v[i:i+H+1]
        if not np.isfinite(w).all(): continue
        peak=np.maximum.accumulate(w); o[i]=np.min(w/peak-1)
    return pd.Series(o,index=s.index)

def bh(p):
    p=np.asarray(p,float); q=np.full(len(p),np.nan); ok=np.isfinite(p)
    pv=p[ok]
    if len(pv)==0:return q
    o=np.argsort(pv); ranks=np.arange(1,len(pv)+1)
    v=pv[o]*len(pv)/ranks; v=np.minimum.accumulate(v[::-1])[::-1]
    qq=np.empty(len(pv)); qq[o]=np.minimum(v,1); q[ok]=qq; return q

def rankcorr(x,y):
    x=np.asarray(x,float); y=np.asarray(y,float)
    return float(np.corrcoef(stats.rankdata(x),stats.rankdata(y))[0,1])

def block_perm_p(x,y,obs,block,n=800,seed=1):
    x=np.asarray(x,float); y=np.asarray(y,float); xr=stats.rankdata(x); N=len(y)
    blocks=[y[i:min(i+block,N)].copy() for i in range(0,N,block)]
    rng=np.random.default_rng(seed); cnt=0
    for _ in range(n):
        yp=np.concatenate([blocks[i] for i in rng.permutation(len(blocks))])[:N]
        r=float(np.corrcoef(xr,stats.rankdata(yp))[0,1])
        cnt += abs(r)>=abs(obs)
    return (cnt+1)/(n+1)

def era_ics(x):
    eras={'pre1946':('1900-01-01','1945-12-01'),'postwar':('1946-01-01','1989-12-01'),'modern':('1990-01-01','2023-09-01')}
    out={}
    for k,(a,b) in eras.items():
        d=x.loc[a:b]
        out[k]=rankcorr(d.f,d.sev) if len(d)>=24 else np.nan
    return out

def logistic_oos(train,test):
    if train.crash.nunique()<2 or test.crash.nunique()<2 or len(train)<80 or len(test)<30:
        return (np.nan,np.nan,np.nan)
    sc=StandardScaler(); Xtr=sc.fit_transform(train[['f']]); Xte=sc.transform(test[['f']])
    m=LogisticRegression(C=1.0,max_iter=500,class_weight=None).fit(Xtr,train.crash.astype(int))
    p=m.predict_proba(Xte)[:,1]
    return float(brier_score_loss(test.crash,p)),float(roc_auc_score(test.crash,p)),float(average_precision_score(test.crash,p))

def status_from(row):
    # deliberately conservative: one US market cannot be PROVEN_SCOPE_LIMITED per project doctrine
    if not np.isfinite(row['nonoverlap_p']): return 'CONTEXT_ONLY'
    signs=[row.get('era_ic_pre1946'),row.get('era_ic_postwar'),row.get('era_ic_modern')]
    signs=[x for x in signs if np.isfinite(x) and abs(x)>.02]
    signstable=len(signs)>=2 and (all(x>0 for x in signs) or all(x<0 for x in signs))
    fdr=row.get('fdr_q_nonoverlap', np.nan)
    if row['nonoverlap_p']<=0.05 and row['block_perm_p']<=0.05 and np.isfinite(fdr) and fdr<=0.10 and signstable:
        return 'HISTORICALLY_SUPPORTED_US_ONLY'
    if row['nonoverlap_p']<=0.10 and row['block_perm_p']<=0.10:
        return 'CONDITIONAL_US_ONLY'
    return 'CONTEXT_ONLY'

def main():
    sh=pd.read_csv(DATA/'shiller.csv',parse_dates=['Date']).set_index('Date').sort_index()
    for c in sh.columns: sh[c]=pd.to_numeric(sh[c],errors='coerce')
    for c in ['SP500','Earnings','Consumer Price Index','Long Interest Rate','PE10','Dividend']:
        sh[c]=sh[c].replace(0,np.nan)
    sh=sh.loc[:'2023-09-01']
    spx=sh.SP500; cpi=sh['Consumer Price Index']; rate=sh['Long Interest Rate']; cape=sh.PE10; earn=sh.Earnings; div=sh.Dividend
    infl=cpi.pct_change(12,fill_method=None)
    ey=earn.pct_change(12,fill_method=None); dy=div.pct_change(12,fill_method=None)
    F={
      'cape_level':cape,
      'cape_expanding_pct':expanding_pct(cape),
      'rate10_level':rate,
      'rate10_chg_6m':rate.diff(6),
      'rate10_chg_12m':rate.diff(12),
      'inflation_yoy':infl,
      'inflation_accel_6m':infl.diff(6),
      'inflation_abs':infl.abs(),
      'real_rate_proxy':rate-infl*100,
      'earnings_yoy_negative':-ey,
      'earnings_decel_6m':-ey.diff(6),
      'earnings_decel_12m':-ey.diff(12),
      'dividend_yoy_negative':-dy,
      'dividend_decel_6m':-dy.diff(6),
    }
    # VIX is market-implied, not technical price alpha; monthly state/fragility input only.
    vix=pd.read_csv(DATA/'vix.csv',parse_dates=['DATE']).set_index('DATE').sort_index()['CLOSE']
    vm=pd.DataFrame({'vix_avg':vix.resample('MS').mean(),'vix_max':vix.resample('MS').max()})
    vm['vix_expanding_pct']=expanding_pct(vm.vix_avg,minp=36)
    vm['vix_chg_3m']=vm.vix_avg.diff(3)
    for c in vm.columns: F[c]=vm[c].reindex(sh.index)
    # Negative controls
    F['negative_control_noise']=pd.Series(RNG.normal(size=len(sh)),index=sh.index)
    F['negative_control_sine']=pd.Series(np.sin(np.arange(len(sh))*1.732),index=sh.index)

    rows=[]
    horizons=[6,12,24]
    for H in horizons:
        dd=fwd_dd(spx,H); sev=-dd; crash=(dd<=-0.20).astype(float); crash[dd.isna()]=np.nan
        for name,f in F.items():
            d=pd.concat([f.rename('f'),sev.rename('sev'),crash.rename('crash')],axis=1).dropna()
            if len(d)<120: continue
            cut=int(len(d)*.60); tr=d.iloc[:cut]; te=d.iloc[cut:]
            if len(te)<40: continue
            ic=rankcorr(te.f,te.sev)
            no=te.iloc[::max(H,1)]
            no_ic=rankcorr(no.f,no.sev) if len(no)>=8 else np.nan
            no_p=float(stats.spearmanr(no.f,no.sev).pvalue) if len(no)>=8 else np.nan
            bp=block_perm_p(te.f,te.sev,ic,block=max(H,6),n=600,seed=H+len(name))
            try: auc=float(roc_auc_score(te.crash,te.f)); pr=float(average_precision_score(te.crash,te.f))
            except: auc=pr=np.nan
            brier,lauc,lpr=logistic_oos(tr,te)
            eras=era_ics(d)
            rows.append(dict(metric=name,horizon_m=H,n=len(d),n_oos=len(te),base_rate=float(te.crash.mean()),oos_ic=ic,
                             block_perm_p=bp,n_nonoverlap=len(no),nonoverlap_ic=no_ic,nonoverlap_p=no_p,
                             raw_auc=auc,raw_pr_auc=pr,logit_brier=brier,logit_auc=lauc,logit_pr_auc=lpr,
                             era_ic_pre1946=eras['pre1946'],era_ic_postwar=eras['postwar'],era_ic_modern=eras['modern']))
    res=pd.DataFrame(rows)
    for H,g in res.groupby('horizon_m'):
        res.loc[g.index,'fdr_q_nonoverlap']=bh(g.nonoverlap_p)
    res['status']=res.apply(status_from,axis=1)
    res.to_csv(OUT/'11_UNIVARIATE_US_LONGRUN_RESULTS.csv',index=False)

    # Mechanism-bounded combos. Fixed equal weights only, no fitted weights.
    Z={k:trailing_z(v) for k,v in F.items() if not k.startswith('negative_control')}
    C={
      'inflation_pressure_eq':pd.concat([Z['inflation_yoy'],Z['inflation_accel_6m']],axis=1).mean(axis=1),
      'inflation_rate_shock_eq':pd.concat([Z['inflation_yoy'],Z['rate10_chg_6m']],axis=1).mean(axis=1),
      'valuation_inflation_eq':pd.concat([Z['cape_expanding_pct'],Z['inflation_accel_6m']],axis=1).mean(axis=1),
      'valuation_rate_eq':pd.concat([Z['cape_expanding_pct'],Z['rate10_chg_6m']],axis=1).mean(axis=1),
      'valuation_vix_eq':pd.concat([Z['cape_expanding_pct'],Z['vix_expanding_pct']],axis=1).mean(axis=1),
      'inflation_vix_eq':pd.concat([Z['inflation_accel_6m'],Z['vix_expanding_pct']],axis=1).mean(axis=1),
      'rate_vix_eq':pd.concat([Z['rate10_chg_6m'],Z['vix_expanding_pct']],axis=1).mean(axis=1),
    }
    crow=[]
    for H in horizons:
        dd=fwd_dd(spx,H); sev=-dd; crash=(dd<=-.20).astype(float); crash[dd.isna()]=np.nan
        for name,f in C.items():
            d=pd.concat([f.rename('f'),sev.rename('sev'),crash.rename('crash')],axis=1).dropna()
            if len(d)<120: continue
            cut=int(len(d)*.60); tr=d.iloc[:cut]; te=d.iloc[cut:]
            ic=rankcorr(te.f,te.sev); no=te.iloc[::H]
            no_ic=rankcorr(no.f,no.sev) if len(no)>=8 else np.nan
            no_p=float(stats.spearmanr(no.f,no.sev).pvalue) if len(no)>=8 else np.nan
            bp=block_perm_p(te.f,te.sev,ic,block=H,n=800,seed=100+H+len(name))
            brier,lauc,lpr=logistic_oos(tr,te); eras=era_ics(d)
            crow.append(dict(composite=name,horizon_m=H,n=len(d),n_oos=len(te),base_rate=float(te.crash.mean()),oos_ic=ic,
                             block_perm_p=bp,n_nonoverlap=len(no),nonoverlap_ic=no_ic,nonoverlap_p=no_p,
                             logit_brier=brier,logit_auc=lauc,logit_pr_auc=lpr,
                             era_ic_pre1946=eras['pre1946'],era_ic_postwar=eras['postwar'],era_ic_modern=eras['modern']))
    cres=pd.DataFrame(crow)
    for H,g in cres.groupby('horizon_m'): cres.loc[g.index,'fdr_q_nonoverlap']=bh(g.nonoverlap_p)
    cres['status']=cres.apply(status_from,axis=1)
    cres.to_csv(OUT/'12_MECHANISM_COMBO_US_LONGRUN_RESULTS.csv',index=False)

    # Summaries / acceptance science guard
    nc=res[res.metric.str.startswith('negative_control')]
    false_null=int(((nc.nonoverlap_p<=.05)&(nc.block_perm_p<=.05)).sum())
    candidates=pd.concat([
        res[~res.metric.str.startswith('negative_control')].rename(columns={'metric':'spec'})[['spec','horizon_m','nonoverlap_ic','nonoverlap_p','block_perm_p','fdr_q_nonoverlap','status']],
        cres.rename(columns={'composite':'spec'})[['spec','horizon_m','nonoverlap_ic','nonoverlap_p','block_perm_p','fdr_q_nonoverlap','status']]
    ],ignore_index=True)
    survivors=candidates[candidates.status.isin(['HISTORICALLY_SUPPORTED_US_ONLY','CONDITIONAL_US_ONLY'])].copy()
    survivors.to_csv(OUT/'13_SURVIVING_US_ONLY_CANDIDATES.csv',index=False)
    summary={
      'dataset_shiller_sha256':sha256(DATA/'shiller.csv'),
      'dataset_vix_sha256':sha256(DATA/'vix.csv'),
      'univariate_specs':int(len(res)), 'combo_specs':int(len(cres)),
      'negative_control_false_positive_count':false_null,
      'survivors_us_only':int(len(survivors)),
      'production_proven_count':0,
      'reason_no_proven':'Project doctrine requires cross-market/cross-regime validation before proven/final scientific status; this self-run environment only has directly readable long-run US Shiller/VIX factual data. Survivors are US-only evidence and are not production proof.'
    }
    (OUT/'14_SCIENTIFIC_VALIDATION_SUMMARY.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary,indent=2))
    print('\nTop survivors:')
    print(survivors.sort_values(['status','nonoverlap_p']).head(20).to_string(index=False))

if __name__=='__main__': main()
