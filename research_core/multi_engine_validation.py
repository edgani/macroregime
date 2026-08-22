from __future__ import annotations
from pathlib import Path
import json, hashlib, math
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge, LogisticRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, roc_auc_score, brier_score_loss
ROOT=Path(__file__).resolve().parents[1]; DATA=ROOT/'data'/'factual'; OUT=ROOT/'FINAL_HANDOFF'; OUT.mkdir(exist_ok=True)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def bh(vals):
    p=np.array([1 if v is None or not np.isfinite(v) else float(v) for v in vals]); n=len(p); order=np.argsort(p); q=np.ones(n); prev=1
    for rank,idx in reversed(list(enumerate(order,1))):
        prev=min(prev,p[idx]*n/rank); q[idx]=prev
    return q

def reg(df,fs,t,min_train=25,hold=.2):
    z=df[fs+[t]].replace([np.inf,-np.inf],np.nan).dropna(); n=len(z)
    if n<min_train+10:return {'ok':False,'n':n,'reason':'INSUFFICIENT_SAMPLE'}
    X=z[fs].to_numpy(float); y=z[t].to_numpy(float); cut=max(min_train,int(n*(1-hold))); cut=min(cut,n-5)
    pp=[]; yy=[]
    for i in range(min_train,cut):
        m=Ridge(alpha=1).fit(X[:i],y[:i]); pp.append(m.predict(X[i:i+1])[0]); yy.append(y[i])
    if len(pp)<5:return {'ok':False,'n':n,'reason':'INSUFFICIENT_WF'}
    rho,p=spearmanr(pp,yy); m=Ridge(alpha=1).fit(X[:cut],y[:cut]); hp=m.predict(X[cut:]); hy=y[cut:]
    hr,hpval=spearmanr(hp,hy) if len(hy)>=4 else (np.nan,np.nan)
    base=np.repeat(np.mean(y[:cut]),len(hy))
    return {'ok':True,'n':n,'wf_spearman':None if not np.isfinite(rho) else float(rho),'wf_p':None if not np.isfinite(p) else float(p),
            'holdout_spearman':None if not np.isfinite(hr) else float(hr),'holdout_p':None if not np.isfinite(hpval) else float(hpval),
            'holdout_rmse':float(math.sqrt(mean_squared_error(hy,hp))),'naive_holdout_rmse':float(math.sqrt(mean_squared_error(hy,base))),
            'holdout_direction_acc':float(np.mean(np.sign(hp)==np.sign(hy)))}

def clf(df,fs,t,min_train=35,hold=.2):
    z=df[fs+[t]].replace([np.inf,-np.inf],np.nan).dropna(); n=len(z)
    if n<min_train+12 or z[t].nunique()<2:return {'ok':False,'n':n,'reason':'INSUFFICIENT_CLASS'}
    X=z[fs].to_numpy(float); y=z[t].to_numpy(int); cut=max(min_train,int(n*(1-hold))); cut=min(cut,n-6); pp=[]; yy=[]
    for i in range(min_train,cut):
        if len(np.unique(y[:i]))<2: continue
        m=LogisticRegression(C=.25,max_iter=2000,class_weight='balanced').fit(X[:i],y[:i]); pp.append(m.predict_proba(X[i:i+1])[0,1]); yy.append(y[i])
    if len(pp)<8 or len(set(yy))<2:return {'ok':False,'n':n,'reason':'INSUFFICIENT_WF_CLASS'}
    m=LogisticRegression(C=.25,max_iter=2000,class_weight='balanced').fit(X[:cut],y[:cut]); hp=m.predict_proba(X[cut:])[:,1]; hy=y[cut:]
    return {'ok':True,'n':n,'wf_auc':float(roc_auc_score(yy,pp)),'wf_brier':float(brier_score_loss(yy,pp)),
            'holdout_auc':float(roc_auc_score(hy,hp)) if len(np.unique(hy))>1 else None,'holdout_brier':float(brier_score_loss(hy,hp))}

def build_specs():
    specs=[]
    # US macro factual historical snapshot
    p=DATA/'macrodata.csv'; d=pd.read_csv(p)
    for c in ['realgdp','realcons','realinv','realdpi','m1','cpi']:
        d[c+'_g4']=np.log(d[c]/d[c].shift(4))*100
    d['unemp_d4']=d.unemp-d.unemp.shift(4); d['future_gdp']=np.log(d.realgdp.shift(-4)/d.realgdp)*100
    d['future_infl']=d.infl.shift(-1).rolling(4).mean().shift(-3); d['future_rate']=d.tbilrate.shift(-4)-d.tbilrate
    d['future_rec']=(d.future_gdp<0).astype(float); d.loc[d.future_gdp.isna(),'future_rec']=np.nan
    groups=[('GROWTH_TRACKING',['realcons_g4','realinv_g4','realdpi_g4','unemp_d4'],'future_gdp','reg'),('INFLATION_TRACKING',['m1_g4','realgdp_g4','unemp','tbilrate'],'future_infl','reg'),('POLICY_REACTION',['infl','realgdp_g4','unemp','realint'],'future_rate','reg'),('RECESSION_DETECTION',['realinv_g4','realcons_g4','unemp_d4','realint'],'future_rec','clf')]
    for e,f,t,k in groups:
        for fs in [[x] for x in f]+[f[:2],f]: specs.append((e,fs,t,k,d,p))
    # Denmark cross-country replication
    p=DATA/'danish_data.csv'; x=pd.read_csv(p); x['money_q']=x.lrm.diff();x['income_q']=x.lry.diff();x['price_q']=x.lpy.diff();x['future_income4']=x.lry.shift(-4)-x.lry;x['future_bond4']=x.ibo.shift(-4)-x.ibo
    for e,f,t in [('DENMARK_GROWTH_REPLICATION',['money_q','price_q','ibo','ide'],'future_income4'),('DENMARK_RATES_REPLICATION',['price_q','money_q','lry','ide'],'future_bond4')]:
        for fs in [[q] for q in f]+[f[:2],f]: specs.append((e,fs,t,'reg',x,p))
    # Copper physical/asset transmission, excluding lagged copper price features.
    p=DATA/'copper.csv'; c=pd.read_csv(p)
    for q in ['WORLDCONSUMPTION','INCOMEINDEX','ALUMPRICE','INVENTORYINDEX']: c[q+'_chg']=c[q].pct_change()
    c['future_copper']=c.COPPERPRICE.shift(-1)/c.COPPERPRICE-1;c['future_cons']=c.WORLDCONSUMPTION.shift(-1)/c.WORLDCONSUMPTION-1
    f=['INCOMEINDEX_chg','INVENTORYINDEX_chg','ALUMPRICE_chg','WORLDCONSUMPTION_chg']
    for e,t in [('COPPER_ASSET_TRANSMISSION','future_copper'),('COPPER_PHYSICAL_DEMAND','future_cons')]:
        for fs in [[q] for q in f]+[f[:2],f]: specs.append((e,fs,t,'reg',c,p))
    # US equity macro valuation transmission; price is outcome, valuation/macro as features.
    p=DATA/'shiller.csv'; s=pd.read_csv(p)
    s=s[(s['Real Price']>0)&(s['Consumer Price Index']>0)&(s['Long Interest Rate']>0)].copy(); s['earnings_yield']=np.where(s.PE10>0,1/s.PE10,np.nan);s['dividend_yield']=s.Dividend/s.SP500.replace(0,np.nan);s['infl_yoy']=np.log(s['Consumer Price Index']/s['Consumer Price Index'].shift(12))*100;s['fwd_real_return_12m']=s['Real Price'].shift(-12)/s['Real Price']-1
    f=['earnings_yield','dividend_yield','Long Interest Rate','infl_yoy']
    for fs in [[q] for q in f]+[f[:2],f]: specs.append(('US_EQUITY_ASSET_TRANSMISSION',fs,'fwd_real_return_12m','reg',s,p))
    return specs

def run():
    rows=[]
    for i,(e,fs,t,k,d,p) in enumerate(build_specs(),1):
        r=clf(d,fs,t) if k=='clf' else reg(d,fs,t,min_train=12 if 'COPPER' in e else 25,hold=.24 if 'COPPER' in e else .2)
        rows.append({'experiment_id':f'ME-{i:04d}','engine_id':e,'features':'|'.join(fs),'target':t,'model_kind':k,'data_origin':'FACTUAL','dataset':p.name,'dataset_sha256':sha(p),'result_json':json.dumps(r,sort_keys=True),'selection_p':r.get('wf_p',1.0) if r.get('ok') else 1.0})
    res=pd.DataFrame(rows);res['global_fdr_q']=bh(res.selection_p)
    def stat(row):
        r=json.loads(row.result_json)
        if not r.get('ok'):return 'BUSTED_AS_TESTED_INSUFFICIENT_SAMPLE'
        if row.model_kind=='clf':
            return 'HISTORICALLY_SUPPORTED_SCOPE_LIMITED' if (r.get('wf_auc') or 0)>=.60 and (r.get('holdout_auc') or 0)>=.55 else 'CONTEXT_ONLY_OR_BUSTED_AS_TESTED'
        dev=r.get('wf_spearman'); ho=r.get('holdout_spearman')
        return 'HISTORICALLY_SUPPORTED_SCOPE_LIMITED' if row.global_fdr_q<=.10 and dev is not None and ho is not None and np.sign(dev)==np.sign(ho) and abs(ho)>=.10 else 'CONTEXT_ONLY_OR_BUSTED_AS_TESTED'
    res['scientific_status']=res.apply(stat,axis=1);res.to_csv(OUT/'50_MULTI_ENGINE_FACTUAL_EXPERIMENTS.csv',index=False)
    summary={'experiments':len(res),'engine_count':int(res.engine_id.nunique()),'engines':sorted(res.engine_id.unique()),'dataset_count':int(res.dataset.nunique()),'datasets':sorted(res.dataset.unique()),'status_counts':res.scientific_status.value_counts().to_dict(),'production_proven_count':0,'scope_limitations':['not full PIT-vintage reconstruction','no IHSG/crypto/FX outcome panels in current runtime','historical packaged datasets are not current live feeds']}
    (OUT/'51_MULTI_ENGINE_VALIDATION_SUMMARY.json').write_text(json.dumps(summary,indent=2),encoding='utf-8');return summary
if __name__=='__main__': print(json.dumps(run(),indent=2))
