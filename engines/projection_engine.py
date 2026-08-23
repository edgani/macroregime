
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


def opportunity_radar(fred, prices, instruments, horizon='3M', k=20):
    """Cross-instrument payoff/downside research board using the same current macro analog state.
    No composite alpha score: Pareto dominance uses higher median and lower >10% loss frequency.
    """
    rows=[]
    for tk in instruments:
        p=prices.get(tk)
        if p is None: continue
        stats,_,meta=analog_distribution(fred,p,k)
        if stats is None or stats.empty: continue
        z=stats[stats['horizon'].astype(str)==str(horizon)]
        if z.empty: continue
        r=z.iloc[0]
        rows.append({'instrument':tk,'horizon':horizon,'median':r.get('median'),'p10':r.get('p10'),'p90':r.get('p90'),
                     'p_positive':r.get('p_positive'),'p_loss10':r.get('p_loss10'),'p_gt25':r.get('p_gt25'),
                     'n':r.get('n'),'status':meta.get('status')})
    d=pd.DataFrame(rows)
    if d.empty:return d
    for c in ['median','p10','p90','p_positive','p_loss10','p_gt25']:
        d[c]=pd.to_numeric(d[c],errors='coerce')
    d=d.dropna(subset=['median','p_loss10'])
    pareto=[]
    for i,r in d.iterrows():
        dominated=False
        for j,q in d.iterrows():
            if i==j:continue
            better_or_equal=(q['median']>=r['median']) and (q['p_loss10']<=r['p_loss10'])
            strictly_better=(q['median']>r['median']) or (q['p_loss10']<r['p_loss10'])
            if better_or_equal and strictly_better:
                dominated=True;break
        pareto.append(not dominated)
    d['pareto_candidate']=pareto
    d['research_priority']=np.where(d['pareto_candidate'],'PARETO — INSPECT FIRST','SECONDARY')
    return d.sort_values(['pareto_candidate','median'],ascending=[False,False])


def normalized_projection_path(stats):
    """Turn return quantiles into a 100-based forward fan for visualization only."""
    if stats is None or stats.empty:return pd.DataFrame()
    month_map={'1M':1,'3M':3,'6M':6,'12M':12}
    rows=[{'month':0,'p10':100.0,'median':100.0,'p90':100.0}]
    for _,r in stats.iterrows():
        h=str(r.get('horizon'))
        if h not in month_map:continue
        vals={k:pd.to_numeric(pd.Series([r.get(k)]),errors='coerce').iloc[0] for k in ['p10','median','p90']}
        if not all(np.isfinite(v) for v in vals.values()):continue
        rows.append({'month':month_map[h],'p10':100*(1+vals['p10']),'median':100*(1+vals['median']),'p90':100*(1+vals['p90'])})
    return pd.DataFrame(rows).sort_values('month')
