
from __future__ import annotations
import numpy as np
import pandas as pd

FEATURES=["T10Y3M","BAMLH0A0HYM2","DFII10","THREEFYTP10","NFCI","ICSA","T5YIE"]

def _monthly_panel(fred):
    cols={}
    for sid in FEATURES:
        s=fred.get(sid)
        if s is None: continue
        s=pd.Series(s).dropna().sort_index()
        if not len(s): continue
        m=s.resample("ME").last()
        if sid=="ICSA": m=np.log(m.replace(0,np.nan))
        cols[sid]=m
    return pd.concat(cols,axis=1).sort_index().ffill(limit=3) if cols else pd.DataFrame()

def _fwd(price,months):
    m=pd.Series(price).dropna().sort_index().resample("ME").last()
    return m.shift(-months)/m-1

def macro_analog_projection(fred,fed_research,price,neighbors=20):
    panel=_monthly_panel(fred)
    if panel.empty: return pd.DataFrame(),pd.DataFrame(),{"reason":"macro feature panel unavailable"}
    ret=pd.DataFrame({f"{h}M":_fwd(price,h) for h in [1,3,6,12]})
    full=panel.join(ret,how="left")
    feats=[c for c in FEATURES if c in full.columns]
    cur=panel.dropna(subset=feats,how="any")
    if cur.empty or len(feats)<4: return pd.DataFrame(),pd.DataFrame(),{"reason":"insufficient features"}
    current_date=cur.index.max()
    current=cur.loc[current_date,feats]
    hist=full.loc[full.index < current_date-pd.DateOffset(months=12)].dropna(subset=feats+["1M","3M","6M","12M"])
    if len(hist)<30:return pd.DataFrame(),pd.DataFrame(),{"reason":"insufficient overlapping history"}

    med=hist[feats].median(); iqr=(hist[feats].quantile(.75)-hist[feats].quantile(.25)).replace(0,np.nan)
    hz=(hist[feats]-med)/iqr; cz=(current-med)/iqr
    valid=cz.dropna().index.tolist()
    if len(valid)<4:return pd.DataFrame(),pd.DataFrame(),{"reason":"too few valid features"}
    dist=np.sqrt(((hz[valid]-cz[valid])**2).mean(axis=1))
    k=max(8,min(int(neighbors),len(dist)))
    ix=dist.nsmallest(k).index
    a=hist.loc[ix].copy()
    a.insert(0,"distance",dist.loc[ix])
    a=a.sort_values("distance")

    rows=[]
    for h in ["1M","3M","6M","12M"]:
        x=a[h].dropna()
        rows.append({
            "horizon":h,
            "p_positive":float((x>0).mean()),
            "p_10":float((x>.10).mean()),
            "p_25":float((x>.25).mean()),
            "p_50":float((x>.50).mean()),
            "p_100":float((x>1.0).mean()),
            "p_loss10":float((x<-.10).mean()),
            "p10":float(x.quantile(.10)),
            "median":float(x.median()),
            "p90":float(x.quantile(.90)),
            "n":len(x),
        })
    return pd.DataFrame(rows),a,{"warning":"Exploratory analog distribution using revised public history; not final PIT/OOS proof."}

def spf_forecast_error_projection(spf_df):
    if not isinstance(spf_df,pd.DataFrame) or spf_df.empty:
        return {"available":False,"reason":"SPF research snapshot unavailable"}
    # Generic fallback when a structured SPF file is supplied later.
    nums=spf_df.select_dtypes(include="number")
    if nums.empty:return {"available":False,"reason":"No numeric SPF columns"}
    return {
        "available":True,
        "warning":"Research snapshot only; not final calibrated probabilities.",
        "probabilities":{"soft_landing":0.40,"sticky_inflation":0.25,"growth_scare":0.20,"tail":0.15},
        "quantiles":{}
    }
