from __future__ import annotations
import json, math, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from cusp_fragility_v73 import (CuspEstimator,cusp_geometry,fit_logistic,probability_metrics,decision_metrics,gaussian_fit,gaussian_logpdf,quadratic_expand,simultaneous_bootstrap_lower,sha256_file)
from research_v55.flat_parquet_snappy import read_flat_parquet

PROTOCOL=ROOT/'research_v57/V74_BREADTH_CUSP_VOL_TRANSITION_PROTOCOL_FROZEN.json'
RECEIPT=ROOT/'research_v57/V74_LOCKBOX_OPEN_RECEIPT.json'
RESULT=ROOT/'research_v57/results/V74_BREADTH_CUSP_RESULTS.json'
PRED=ROOT/'research_v57/results/V74_DAILY_PREDICTIONS.csv'
BASE=['rv20','vix','breadth200','breadth_change5','drawdown63','trend63','dispersion20','adv_dec_volume5']
ALPHA=['breadth200','drawdown63','trend63']
BETA=['dispersion20','adv_dec_volume5','breadth_change5']

def future_rv(ret:pd.Series,h:int)->pd.Series:
    a=ret.to_numpy(float); o=np.full(len(a),np.nan)
    for i in range(len(a)-h): o[i]=float(np.sqrt(np.mean(a[i+1:i+h+1]**2))*np.sqrt(252.0))
    return pd.Series(o,index=ret.index)

def per_ll(y,p):
    p=np.clip(p,1e-6,0.999999); return -(y*np.log(p)+(1-y)*np.log(1-p))

def mask(idx,a,b): return (idx>=pd.Timestamp(a))&(idx<=pd.Timestamp(b))

def main():
    if RESULT.exists(): raise SystemExit('V74 result exists; overwrite forbidden')
    rec=json.loads(RECEIPT.read_text())
    checks={
      'protocol':sha256_file(PROTOCOL)==rec['protocol_sha256'],
      'runner':sha256_file(__file__)==rec['runner_sha256'],
      'panel':sha256_file(ROOT/'research/sp500_panel.parquet')==rec['panel_sha256'],
      'vix':sha256_file(ROOT/'research/vix.csv')==rec['vix_sha256']}
    if not all(checks.values()): raise SystemExit(str(checks))
    panel=read_flat_parquet(ROOT/'research/sp500_panel.parquet')
    panel=panel[['date','close','volume','Name']].copy(); panel['date']=pd.to_datetime(panel['date'])
    close=panel.pivot(index='date',columns='Name',values='close').sort_index()
    vol=panel.pivot(index='date',columns='Name',values='volume').reindex(close.index)
    ret=close.pct_change(fill_method=None)
    market_ret=ret.mean(axis=1,skipna=True)
    ew_index=(1+market_ret.fillna(0)).cumprod()*100
    rms20=market_ret.shift(1).pow(2).rolling(20,min_periods=20).mean().pow(.5)
    ma200=close.rolling(200,min_periods=180).mean(); breadth200=(close>ma200).mean(axis=1)
    adv_vol=vol.where(ret>0).sum(axis=1,min_count=1); dec_vol=vol.where(ret<0).sum(axis=1,min_count=1)
    adv_dec=np.log((adv_vol+1)/(dec_vol+1)).rolling(5,min_periods=5).mean()
    dispersion=ret.std(axis=1,skipna=True).rolling(20,min_periods=20).mean()
    f=pd.DataFrame(index=close.index)
    f['market_ret']=market_ret
    f['state_z']=(market_ret/(rms20+1e-12)).clip(-5,5)
    f['rv20']=rms20*np.sqrt(252)
    f['breadth200']=breadth200
    f['breadth_change5']=breadth200-breadth200.shift(5)
    f['drawdown63']=ew_index/ew_index.rolling(63,min_periods=63).max()-1
    f['trend63']=np.log(ew_index/ew_index.shift(63))
    f['dispersion20']=dispersion
    f['adv_dec_volume5']=adv_dec
    vix=pd.read_csv(ROOT/'research/vix.csv',parse_dates=['DATE']).set_index('DATE')['CLOSE'].sort_index()
    f['vix']=vix.reindex(f.index).ffill(limit=3)
    f['future_rv20']=future_rv(market_ret,20)
    need=['state_z','future_rv20']+BASE+ALPHA+BETA
    f=f.dropna(subset=sorted(set(need))).copy()
    masks={'train':mask(f.index,'2014-01-02','2015-12-31'),'validation':mask(f.index,'2016-02-01','2016-12-30'),'lockbox':mask(f.index,'2017-02-01','2018-01-10')}
    tr=np.where(masks['train'])[0]; va=np.where(masks['validation'])[0]; lo=np.where(masks['lockbox'])[0]
    if min(map(len,[tr,va,lo]))<100: raise RuntimeError({k:int(v.sum()) for k,v in masks.items()})
    threshold=float(np.quantile(f['future_rv20'].to_numpy()[tr],.90))
    y=(f['future_rv20'].to_numpy()>=threshold).astype(int)
    est=CuspEstimator(); fit=est.fit(f['state_z'].to_numpy()[tr],f[ALPHA].to_numpy()[tr],f[BETA].to_numpy()[tr],starts=(0,1,2,3))
    alpha,beta=est.alpha_beta(fit,f[ALPHA].to_numpy(),f[BETA].to_numpy())
    ystate=fit.params[0]+math.exp(fit.params[1])*f['state_z'].to_numpy()
    geo=cusp_geometry(alpha,beta,ystate)
    controls=np.column_stack([f[ALPHA].to_numpy(),f[BETA].to_numpy()])
    cusp_lp=est.score_samples(fit,f['state_z'].to_numpy(),f[ALPHA].to_numpy(),f[BETA].to_numpy())
    lc,ls=gaussian_fit(controls[tr],f['state_z'].to_numpy()[tr]); llp=gaussian_logpdf(controls,f['state_z'].to_numpy(),lc,ls)
    qc,qs=gaussian_fit(quadratic_expand(controls)[tr],f['state_z'].to_numpy()[tr]); qlp=gaussian_logpdf(quadratic_expand(controls),f['state_z'].to_numpy(),qc,qs)
    structural={s:{'cusp':float(cusp_lp[ix].mean()),'linear':float(llp[ix].mean()),'quadratic':float(qlp[ix].mean())} for s,ix in [('validation',va),('lockbox',lo)]}
    structural_pass=all(structural[s]['cusp']>structural[s][c] for s in structural for c in ['linear','quadratic'])
    xb=f[BASE].to_numpy(); xc=np.column_stack([xb,geo]); xs=np.column_stack([xb,alpha,beta,alpha**2,beta**2,alpha*beta])
    rng=np.random.default_rng(740075); xsh=np.column_stack([xb,geo[rng.permutation(len(geo))]]); xshift=np.column_stack([xb,np.roll(geo,60,axis=0)])
    XX={'baseline':xb,'cusp':xc,'smooth':xs,'shuffle':xsh,'shift60':xshift}; models={k:fit_logistic(v[tr],y[tr]) for k,v in XX.items()}
    metrics={}; probs={}
    for k,m in models.items():
      pt=m.predict_proba(XX[k][tr])[:,1]; pv=m.predict_proba(XX[k][va])[:,1]; pl=m.predict_proba(XX[k][lo])[:,1]
      probs[k]={'train':pt,'validation':pv,'lockbox':pl}
      metrics[k]={'validation':{'probability':probability_metrics(y[va],pv),'decision':decision_metrics(y[tr],pt,y[va],pv,len(va))},'lockbox':{'probability':probability_metrics(y[lo],pl),'decision':decision_metrics(y[tr],pt,y[lo],pl,len(lo))}}
    def boot_for(k):
      arr=[(y[va]-probs['baseline']['validation'])**2-(y[va]-probs[k]['validation'])**2,per_ll(y[va],probs['baseline']['validation'])-per_ll(y[va],probs[k]['validation']),(y[lo]-probs['baseline']['lockbox'])**2-(y[lo]-probs[k]['lockbox'])**2,per_ll(y[lo],probs['baseline']['lockbox'])-per_ll(y[lo],probs[k]['lockbox'])]
      return simultaneous_bootstrap_lower(arr,resamples=3000,block=20,seed=740074)
    boot=boot_for('cusp'); bsh=boot_for('shuffle'); bsi=boot_for('shift60')
    gates={
      'structural_density_pass':structural_pass,
      'four_point_improvements_positive':all(x>0 for x in boot['observed']),
      'simultaneous_lower_positive':all(x>0 for x in boot['simultaneous_lower']),
      'not_worse_than_smooth':all(metrics['cusp'][s]['probability'][m]<=metrics['smooth'][s]['probability'][m]+1e-12 for s in ['validation','lockbox'] for m in ['brier','log_loss']),
      'placebo_shuffle_fails':not all(x>0 for x in bsh['simultaneous_lower']),
      'placebo_shift_fails':not all(x>0 for x in bsi['simultaneous_lower'])}
    narrow=all(gates.values())
    out={'study_id':'V74_BREADTH_CUSP_VOLATILITY_TRANSITION','receipt_checks':checks,'rows':{k:int(v.sum()) for k,v in masks.items()},'threshold_future_rv20':threshold,'positive_rows':{'train':int(y[tr].sum()),'validation':int(y[va].sum()),'lockbox':int(y[lo].sum())},'cusp_fit':{'success':fit.success,'nll':fit.nll,'params':fit.params.tolist(),'starts':fit.starts},'structural_fit':structural,'metrics':metrics,'bootstrap':boot,'placebos':{'shuffle':bsh,'shift60':bsi},'gates':gates,'narrow_mechanism_support':narrow,'promoted_live':False,'live_decision_weight':0.0,'capital_permission':'BLOCKED','verdict':'NARROW_MECHANISM_SUPPORT_NONPROMOTABLE' if narrow else 'NOT_PROVEN','limitations':['fixed constituent panel is survivorship-prone','short 2014-2018 period','volatility-transition claim is distinct from crash-direction claim']}
    RESULT.write_text(json.dumps(out,indent=2,sort_keys=True))
    pd.DataFrame({'target':y,'future_rv20':f['future_rv20'],'alpha':alpha,'beta':beta,'p_baseline':np.nan,'p_cusp':np.nan},index=f.index).to_csv(PRED,index_label='date')
    print(json.dumps({'verdict':out['verdict'],'rows':out['rows'],'positive_rows':out['positive_rows'],'gates':gates,'bootstrap':boot},indent=2))
if __name__=='__main__': main()
