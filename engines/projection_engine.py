
from __future__ import annotations
import numpy as np,pandas as pd
FEATURES=['T10Y3M','BAMLH0A0HYM2','DFII10','THREEFYTP10','NFCI','ICSA','T5YIE']

def monthly_panel(fred):
    z={}
    for sid in FEATURES:
        s=fred.get(sid)
        if s is None:continue
        x=pd.Series(s).dropna().sort_index().resample('ME').last()
        if sid=='ICSA':x=np.log(x.replace(0,np.nan))
        z[sid]=x
    return pd.concat(z,axis=1).sort_index().ffill(limit=3) if z else pd.DataFrame()
def fwd(price,m):
    x=pd.Series(price).dropna().sort_index().resample('ME').last();return x.shift(-m)/x-1

def _neighbor_forecast(hist,cur,feats,k):
    med=hist[feats].median();iqr=(hist[feats].quantile(.75)-hist[feats].quantile(.25)).replace(0,np.nan);hz=(hist[feats]-med)/iqr;cz=(cur[feats]-med)/iqr;use=cz.dropna().index
    if len(use)<4:return None,None
    dist=np.sqrt(((hz[use]-cz[use])**2).mean(axis=1));ix=dist.nsmallest(max(8,min(k,len(dist)))).index;return ix,dist.loc[ix]

def analog_distribution(fred,price,k=20):
    panel=monthly_panel(fred)
    if panel.empty:return pd.DataFrame(),pd.DataFrame(),{'status':'NO DATA'}
    y=pd.DataFrame({f'{h}M':fwd(price,h) for h in [1,3,6,12]});full=panel.join(y,how='left');feats=[c for c in FEATURES if c in full];cur=panel.dropna(subset=feats)
    if cur.empty or len(feats)<4:return pd.DataFrame(),pd.DataFrame(),{'status':'NO DATA'}
    dt=cur.index[-1];hist=full.loc[full.index<dt-pd.DateOffset(months=12)].dropna(subset=feats+['1M','3M','6M','12M'])
    if len(hist)<40:return pd.DataFrame(),pd.DataFrame(),{'status':'INSUFFICIENT HISTORY'}
    ix,dist=_neighbor_forecast(hist,cur.iloc[-1],feats,k)
    if ix is None:return pd.DataFrame(),pd.DataFrame(),{'status':'INSUFFICIENT FEATURES'}
    a=hist.loc[ix].copy();a.insert(0,'distance',dist);out=[]
    for h in ['1M','3M','6M','12M']:
        x=a[h];out.append({'horizon':h,'p_positive':(x>0).mean(),'p_gt25':(x>.25).mean(),'p_gt50':(x>.50).mean(),'p_gt100':(x>1).mean(),'p_loss10':(x<-.10).mean(),'p10':x.quantile(.1),'median':x.median(),'p90':x.quantile(.9),'n':len(x)})
    return pd.DataFrame(out),a,{'status':'EXPLORATORY_REVISED_HISTORY','calibration':'RUN WALK-FORWARD TAB FOR RELIABILITY','price_usage':'OUTCOME LABEL ONLY'}

def walkforward_calibration(fred,price,k=20,min_train=84,step=3):
    panel=monthly_panel(fred);results=[]
    if panel.empty:return pd.DataFrame(),{'status':'NO DATA'}
    ys={h:fwd(price,h) for h in [1,3,6,12]};full=panel.copy()
    for h,y in ys.items():full[f'{h}M']=y
    feats=[c for c in FEATURES if c in full]
    valid=full.dropna(subset=feats)
    if len(valid)<min_train+24:return pd.DataFrame(),{'status':'INSUFFICIENT HISTORY'}
    dates=list(valid.index)
    for h in [1,3,6,12]:
        col=f'{h}M';rows=[]
        for pos in range(min_train,len(dates),step):
            dt=dates[pos]
            if pd.isna(full.loc[dt,col]):continue
            # only train on dates whose h-month outcome was known before dt
            cutoff=dt-pd.DateOffset(months=h)
            hist=full.loc[full.index<=cutoff].dropna(subset=feats+[col])
            if len(hist)<min_train:continue
            ix,_=_neighbor_forecast(hist,full.loc[dt],feats,k)
            if ix is None:continue
            x=hist.loc[ix,col];rows.append({'date':dt,'actual':float(full.loc[dt,col]),'p_pos':float((x>0).mean()),'p10':float(x.quantile(.1)),'median':float(x.median()),'p90':float(x.quantile(.9))})
        if rows:
            d=pd.DataFrame(rows);brier=float(np.mean((d.p_pos-(d.actual>0).astype(float))**2));base=float(np.mean(((d.actual>0).mean()-(d.actual>0).astype(float))**2));coverage=float(((d.actual>=d.p10)&(d.actual<=d.p90)).mean());mae=float(np.mean(np.abs(d.actual-d['median'])));skill=1-brier/base if base>0 else np.nan
            results.append({'horizon':f'{h}M','n_oos':len(d),'interval_80_coverage':coverage,'brier_positive':brier,'brier_skill_vs_constant':skill,'median_mae':mae,'status':'RESEARCH_CALIBRATION_REVISED_HISTORY' if len(d)>=30 else 'LOW_SAMPLE'})
    return pd.DataFrame(results),{'status':'TEMPORAL_SAFE_BUT_REVISION_UNSAFE','warning':'Feature history is latest/revised, not PIT vintage. Never promote to PROVEN from this calibration alone.'}
