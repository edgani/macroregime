
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

def analog_distribution(fred,price,k=20):
    panel=monthly_panel(fred)
    if panel.empty:return pd.DataFrame(),pd.DataFrame(),{'status':'NO DATA'}
    y=pd.DataFrame({f'{h}M':fwd(price,h) for h in [1,3,6,12]}); full=panel.join(y,how='left'); feats=[c for c in FEATURES if c in full]
    cur=panel.dropna(subset=feats); 
    if cur.empty or len(feats)<4:return pd.DataFrame(),pd.DataFrame(),{'status':'NO DATA'}
    dt=cur.index[-1]; hist=full.loc[full.index<dt-pd.DateOffset(months=12)].dropna(subset=feats+['1M','3M','6M','12M'])
    if len(hist)<40:return pd.DataFrame(),pd.DataFrame(),{'status':'INSUFFICIENT HISTORY'}
    med=hist[feats].median(); iqr=(hist[feats].quantile(.75)-hist[feats].quantile(.25)).replace(0,np.nan); hz=(hist[feats]-med)/iqr; cz=(cur.iloc[-1][feats]-med)/iqr
    use=cz.dropna().index; dist=np.sqrt(((hz[use]-cz[use])**2).mean(axis=1)); ix=dist.nsmallest(max(8,min(k,len(dist)))).index; a=hist.loc[ix].copy();a.insert(0,'distance',dist.loc[ix])
    out=[]
    for h in ['1M','3M','6M','12M']:
        x=a[h]
        out.append({'horizon':h,'p_positive':(x>0).mean(),'p_gt25':(x>.25).mean(),'p_gt50':(x>.50).mean(),'p_gt100':(x>1).mean(),'p_loss10':(x<-.10).mean(),'p10':x.quantile(.1),'median':x.median(),'p90':x.quantile(.9),'n':len(x)})
    return pd.DataFrame(out),a,{'status':'EXPLORATORY_REVISED_HISTORY','calibration':'NOT CALIBRATED PIT','price_usage':'OUTCOME LABEL ONLY'}

def interval_calibration_stub():
    return {'status':'DATA_GATED','required':'Vintage-safe feature history + frozen rolling analog selection + OOS coverage test. Nominal 80% interval may not be called calibrated until ~80% OOS coverage is demonstrated.'}
