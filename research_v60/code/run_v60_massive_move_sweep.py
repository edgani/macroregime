from __future__ import annotations
import sys, os, json, hashlib, math, itertools, time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.metrics import average_precision_score, roc_auc_score, brier_score_loss

BASE=Path('/mnt/data/warroom_v60_work/src')
sys.path.insert(0,str(BASE))
from research_v55.flat_parquet_snappy import read_flat_parquet
OUT=BASE/'research_v60'
OUT.mkdir(exist_ok=True)
(OUT/'code').mkdir(exist_ok=True)
(OUT/'protocols').mkdir(exist_ok=True)
(OUT/'results').mkdir(exist_ok=True)
(OUT/'ledgers').mkdir(exist_ok=True)

# PRE-REGISTERED exact study design. No outcome-driven edits below this object.
PROTOCOL={
 'study_id':'V60_MASSIVE_MOVE_DISCOVERY_PRICE_VOLUME',
 'purpose':'Test whether observable pre-move price/volume/liquidity/volatility path states identify future extreme winners before the move.',
 'dataset':'bundled research/sp500_panel.parquet',
 'known_limits':['fixed panel likely survivorship-biased','OHLCV only','no point-in-time shares outstanding','2013-2018 short era','not cross-market'],
 'sampling':'last observation of each calendar month per ticker',
 'target_horizon_trading_days':63,
 'targets':{
   'absolute_winner':'future maximum close return over next 63 trading days >= 30%',
   'relative_winner':'top 5% future maximum close return within each monthly cross-section',
   'absolute_loser':'future minimum close return over next 63 trading days <= -20%',
 },
 'splits':{
   'train_end':'2015-01-31',
   'validation_start':'2015-02-01','validation_end':'2016-01-31',
   'lockbox_start':'2016-02-01','lockbox_end':'2017-11-30'
 },
 'purging':'month-end features use only contemporaneously available observations; targets use t+1..t+63; no fitted model uses validation or lockbox',
 'candidate_construction':'all univariate signed percentile ranks plus all pairwise signed additive rank combinations across predeclared base features; no outcome-based feature selection',
 'metrics':['AP','ROC_AUC','Brier','precision_at_10','recall_at_10','mean_forward_max_return_at_10','mean_lead_days_to_30pct_for_hits'],
 'baselines':['mom_63','mom_126','volume_acceleration','equal_random_expectation'],
 'promotion_gate':[
   'validation AP improvement over best baseline > 0',
   'validation monthly precision@10 improvement BH-FDR q<0.05 globally',
   'lockbox AP improvement > 0',
   'lockbox precision@10 improvement > 0',
   'lockbox mean forward max return@10 improvement > 0',
   'at least 8 nonempty validation months and 12 nonempty lockbox months',
   'no claim of live proof due dataset limitations'
 ]
}
proto_path=OUT/'protocols/V60_MASSIVE_MOVE_PROTOCOL_FROZEN.json'
proto_path.write_text(json.dumps(PROTOCOL,indent=2,sort_keys=True),encoding='utf-8')
proto_hash=hashlib.sha256(proto_path.read_bytes()).hexdigest()
(OUT/'protocols/V60_MASSIVE_MOVE_PROTOCOL_FROZEN.sha256').write_text(proto_hash+'  '+proto_path.name+'\n')

print('loading panel')
df=read_flat_parquet(BASE/'research/sp500_panel.parquet')
df['date']=pd.to_datetime(df['date'])
df=df.sort_values(['Name','date']).reset_index(drop=True)
for c in ['open','high','low','close','volume']:
    df[c]=pd.to_numeric(df[c],errors='coerce')

g=df.groupby('Name',group_keys=False)
df['ret1']=g['close'].pct_change()
df['logret']=np.log(df['close']).groupby(df['Name']).diff()
df['dollar_volume']=df['close']*df['volume']
df['clv']=((df['close']-df['low'])-(df['high']-df['close']))/(df['high']-df['low']).replace(0,np.nan)
df['signed_vol']=np.sign(df['ret1'].fillna(0))*df['volume']
df['adl_flow']=df['clv'].fillna(0)*df['volume']
df['true_range']=pd.concat([(df['high']-df['low']), (df['high']-g['close'].shift()).abs(), (df['low']-g['close'].shift()).abs()],axis=1).max(axis=1)

features={}
def add(name,s,family):
    features[name]=family
    df[name]=s.replace([np.inf,-np.inf],np.nan)

# Returns, trend, acceleration
for w in [5,10,20,40,63,126,252]:
    add(f'mom_{w}',g['close'].pct_change(w),'trend')
for a,b in [(5,20),(10,40),(20,63),(40,126),(63,126),(63,252)]:
    add(f'accel_{a}_{b}',df[f'mom_{a}']-df[f'mom_{b}'],'trend_acceleration')
for w in [10,20,40,63,126]:
    add(f'positive_frac_{w}',g['ret1'].rolling(w,min_periods=max(5,w//2)).apply(lambda x: np.mean(x>0),raw=True).reset_index(level=0,drop=True),'trend_quality')
    add(f'trend_slope_{w}',g['close'].rolling(w,min_periods=max(5,w//2)).apply(lambda x: np.polyfit(np.arange(len(x)),np.log(np.maximum(x,1e-12)),1)[0],raw=True).reset_index(level=0,drop=True),'trend_quality')

# Volatility, shape, compression
for w in [5,10,20,40,63,126]:
    add(f'vol_{w}',g['logret'].rolling(w,min_periods=max(5,w//2)).std().reset_index(level=0,drop=True)*np.sqrt(252),'volatility')
    add(f'skew_{w}',g['logret'].rolling(w,min_periods=min(w,max(3,w//2))).skew().reset_index(level=0,drop=True),'distribution_shape')
    add(f'kurt_{w}',g['logret'].rolling(w,min_periods=min(w,max(3,w//2))).kurt().reset_index(level=0,drop=True),'distribution_shape')
    add(f'atrp_{w}',g['true_range'].rolling(w,min_periods=max(5,w//2)).mean().reset_index(level=0,drop=True)/df['close'],'volatility')
for a,b in [(5,20),(10,40),(20,63),(40,126)]:
    add(f'vol_ratio_{a}_{b}',df[f'vol_{a}']/df[f'vol_{b}'],'volatility_compression')
    add(f'atr_ratio_{a}_{b}',df[f'atrp_{a}']/df[f'atrp_{b}'],'volatility_compression')

# Location, breakout, drawdown
for w in [20,40,63,126,252]:
    hi=g['high'].rolling(w,min_periods=max(5,w//2)).max().reset_index(level=0,drop=True)
    lo=g['low'].rolling(w,min_periods=max(5,w//2)).min().reset_index(level=0,drop=True)
    add(f'dist_high_{w}',df['close']/hi-1,'price_location')
    add(f'dist_low_{w}',df['close']/lo-1,'price_location')
    add(f'range_pos_{w}',(df['close']-lo)/(hi-lo).replace(0,np.nan),'price_location')

# Volume/flow/attention
df['amihud_daily']=df['ret1'].abs()/df['dollar_volume'].replace(0,np.nan)
for w in [5,10,20,40,63,126]:
    vmean=g['volume'].rolling(w,min_periods=max(5,w//2)).mean().reset_index(level=0,drop=True)
    vstd=g['volume'].rolling(w,min_periods=max(5,w//2)).std().reset_index(level=0,drop=True)
    add(f'volume_z_{w}',(df['volume']-vmean)/vstd,'attention_volume')
    add(f'log_dvol_{w}',np.log1p(g['dollar_volume'].rolling(w,min_periods=max(5,w//2)).mean().reset_index(level=0,drop=True)),'liquidity_level')
    add(f'signed_volume_{w}',g['signed_vol'].rolling(w,min_periods=max(5,w//2)).sum().reset_index(level=0,drop=True)/g['volume'].rolling(w,min_periods=max(5,w//2)).sum().reset_index(level=0,drop=True),'signed_flow_proxy')
    add(f'adl_flow_{w}',g['adl_flow'].rolling(w,min_periods=max(5,w//2)).sum().reset_index(level=0,drop=True)/g['volume'].rolling(w,min_periods=max(5,w//2)).sum().reset_index(level=0,drop=True),'accumulation_proxy')
    add(f'amihud_{w}',g['amihud_daily'].rolling(w,min_periods=max(5,w//2)).mean().reset_index(level=0,drop=True),'illiquidity')
for a,b in [(5,20),(10,40),(20,63),(40,126)]:
    va=g['volume'].rolling(a,min_periods=max(5,a//2)).mean().reset_index(level=0,drop=True)
    vb=g['volume'].rolling(b,min_periods=max(5,b//2)).mean().reset_index(level=0,drop=True)
    add(f'volume_ratio_{a}_{b}',va/vb,'attention_acceleration')
    add(f'dvol_ratio_{a}_{b}',g['dollar_volume'].rolling(a,min_periods=max(5,a//2)).mean().reset_index(level=0,drop=True)/g['dollar_volume'].rolling(b,min_periods=max(5,b//2)).mean().reset_index(level=0,drop=True),'liquidity_acceleration')

# Gap and intraday pressure
prev_close=g['close'].shift()
df['gap']=df['open']/prev_close-1
df['intraday']=df['close']/df['open']-1
for w in [5,10,20,40,63]:
    add(f'gap_mean_{w}',g['gap'].rolling(w,min_periods=max(5,w//2)).mean().reset_index(level=0,drop=True),'overnight_information')
    add(f'intraday_mean_{w}',g['intraday'].rolling(w,min_periods=max(5,w//2)).mean().reset_index(level=0,drop=True),'intraday_pressure')
    add(f'gap_up_frac_{w}',g['gap'].rolling(w,min_periods=max(5,w//2)).apply(lambda x: np.mean(x>0.01),raw=True).reset_index(level=0,drop=True),'overnight_information')

# Market-relative features from equal-weight daily market.
market=df.groupby('date')['ret1'].mean().rename('mkt_ret')
df=df.join(market,on='date')
g=df.groupby('Name',group_keys=False)
df['ret_x_mkt']=df['ret1']*df['mkt_ret']
df['mkt_sq']=df['mkt_ret']**2
for w in [20,40,63,126]:
    minp=max(10,w//2)
    mktcum_series=(1+market).rolling(w,min_periods=max(5,w//2)).apply(np.prod,raw=True)-1
    mktcum=df['date'].map(mktcum_series)
    add(f'rel_mom_{w}',df[f'mom_{w}']-mktcum,'relative_strength')
    exy=g['ret_x_mkt'].rolling(w,min_periods=minp).mean().reset_index(level=0,drop=True)
    ex=g['ret1'].rolling(w,min_periods=minp).mean().reset_index(level=0,drop=True)
    ey=g['mkt_ret'].rolling(w,min_periods=minp).mean().reset_index(level=0,drop=True)
    ey2=g['mkt_sq'].rolling(w,min_periods=minp).mean().reset_index(level=0,drop=True)
    cov=exy-ex*ey; var=ey2-ey**2
    beta=cov/var.replace(0,np.nan)
    add(f'beta_{w}',beta,'market_exposure')
    add(f'idio_mom_{w}',df[f'mom_{w}']-beta*mktcum,'relative_strength')

# Forward targets, carefully t+1..t+63.
H=63
future_max=g['close'].transform(lambda s: s.shift(-1)[::-1].rolling(H,min_periods=H).max()[::-1])
future_min=g['close'].transform(lambda s: s.shift(-1)[::-1].rolling(H,min_periods=H).min()[::-1])
df['fwd_max_ret_63']=future_max/df['close']-1
df['fwd_min_ret_63']=future_min/df['close']-1
df['fwd_ret_63']=g['close'].shift(-H)/df['close']-1
# Lead time to first +30%, vectorized and restricted to the frozen 63-day horizon.
df['lead_30']=np.nan
for k in range(1,H+1):
    hit=(g['close'].shift(-k)/df['close']-1)>=0.30
    df.loc[df['lead_30'].isna() & hit,'lead_30']=k

# Monthly snapshots.
df['month']=df['date'].dt.to_period('M')
monthly=df.groupby(['Name','month'],as_index=False).tail(1).copy()
monthly['target_abs_up']=(monthly['fwd_max_ret_63']>=0.30).astype(int)
monthly['target_abs_down']=(monthly['fwd_min_ret_63']<=-0.20).astype(int)
monthly['target_rel_up']=monthly.groupby('month')['fwd_max_ret_63'].transform(lambda s: s>=s.quantile(.95)).astype(int)

feature_names=sorted(features)
# Drop features with too little usable data.
usable=[]
for f in feature_names:
    if monthly[f].notna().mean()>=0.60 and monthly[f].nunique(dropna=True)>=20:
        usable.append(f)
feature_names=usable

# Register exact candidates before reading target outcomes.
candidates=[]
for f in feature_names:
    for sign in [1,-1]:
        candidates.append({'candidate_id':f'U::{f}::{sign:+d}','f1':f,'s1':sign,'f2':None,'s2':None,'kind':'univariate','family1':features[f],'family2':None})
for i,f1 in enumerate(feature_names):
    for f2 in feature_names[i+1:]:
        # Pair all quadrants; simple mean percentile rank. Includes same-family and cross-family interactions.
        for s1,s2 in [(1,1),(1,-1),(-1,1),(-1,-1)]:
            candidates.append({'candidate_id':f'P::{f1}::{s1:+d}::{f2}::{s2:+d}','f1':f1,'s1':s1,'f2':f2,'s2':s2,'kind':'pair_additive_rank','family1':features[f1],'family2':features[f2]})
cand_df=pd.DataFrame(candidates)
cand_path=OUT/'protocols/V60_CANDIDATE_GRID_FROZEN.csv'
cand_df.to_csv(cand_path,index=False)
cand_hash=hashlib.sha256(cand_path.read_bytes()).hexdigest()
(OUT/'protocols/V60_CANDIDATE_GRID_FROZEN.sha256').write_text(cand_hash+'  '+cand_path.name+'\n')
print('features',len(feature_names),'candidates',len(candidates),'protocol',proto_hash[:12],'grid',cand_hash[:12])

# Cross-sectional percentile ranks computed separately each month, no future information.
ranks=monthly.groupby('month')[feature_names].rank(pct=True,method='average')
# neutral fill 0.5 only for scoring; coverage is tracked and candidates require sufficient rows.
ranks=ranks.fillna(0.5).astype('float32')
# Cache exact monthly cross-sectional ranks and outcomes for pre-registered alternate targets.
(OUT/'data').mkdir(exist_ok=True)
np.savez_compressed(OUT/'data/V60_MONTHLY_FEATURE_RANKS.npz', ranks=ranks.to_numpy(dtype=np.float32), feature_names=np.array(feature_names,dtype=object))
monthly[['Name','date','month','fwd_max_ret_63','fwd_min_ret_63','fwd_ret_63','lead_30','target_abs_up','target_abs_down','target_rel_up']].to_csv(OUT/'data/V60_MONTHLY_OUTCOMES.csv',index=False)

splits={
 'validation':(pd.Period('2015-02','M'),pd.Period('2016-01','M')),
 'lockbox':(pd.Period('2016-02','M'),pd.Period('2017-11','M')),
}

def score_candidate(c):
    s=(ranks[c.f1] if c.s1==1 else 1-ranks[c.f1]).to_numpy(dtype=np.float32)
    if c.f2 is not None:
        s2=(ranks[c.f2] if c.s2==1 else 1-ranks[c.f2]).to_numpy(dtype=np.float32)
        s=(s+s2)/2
    return s

def eval_score(score,target_name,start,end):
    mask=(monthly['month']>=start)&(monthly['month']<=end)&monthly[target_name].notna()&monthly['fwd_max_ret_63'].notna()
    y=monthly.loc[mask,target_name].to_numpy(int)
    sc=score[mask.to_numpy()]
    if len(np.unique(y))<2: return None
    out={'n':int(len(y)),'events':int(y.sum()),'ap':float(average_precision_score(y,sc)),'auc':float(roc_auc_score(y,sc)),'brier':float(brier_score_loss(y,np.clip(sc,0,1)))}
    tmp=monthly.loc[mask,['month','fwd_max_ret_63','lead_30']].copy(); tmp['y']=y; tmp['score']=sc
    rows=[]
    for m,x in tmp.groupby('month'):
        top=x.nlargest(min(10,len(x)),'score')
        ev=int(x['y'].sum()); hit=int(top['y'].sum())
        rows.append({'month':str(m),'precision10':hit/len(top),'recall10':hit/ev if ev else np.nan,'mean_fwd_max10':top['fwd_max_ret_63'].mean(),'lead30':top.loc[top['y']==1,'lead_30'].mean()})
    md=pd.DataFrame(rows)
    out.update({'months':int(len(md)),'precision10':float(md['precision10'].mean()),'recall10':float(md['recall10'].mean()),'mean_fwd_max10':float(md['mean_fwd_max10'].mean()),'lead30':float(md['lead30'].mean()) if md['lead30'].notna().any() else None,'monthly_precision':md['precision10'].tolist()})
    return out

# Baselines evaluated first.
baselines={}
for b in ['mom_63','mom_126','volume_ratio_20_63','rel_mom_63']:
    if b in feature_names:
        sc=ranks[b].to_numpy(dtype=np.float32)
        baselines[b]={sp:eval_score(sc,'target_abs_up',*rng) for sp,rng in splits.items()}
print('baselines',json.dumps(baselines,indent=2)[:2000])
# choose best validation AP baseline, frozen among declared baseline set.
best_base=max(baselines,key=lambda b: baselines[b]['validation']['ap'])
base_val=baselines[best_base]['validation']; base_lock=baselines[best_base]['lockbox']

# Candidate evaluation: validation screen for the entire frozen grid; lockbox opens only for globally corrected validation survivors.
base_score=ranks[best_base].to_numpy(dtype=np.float32)

def split_arrays(start,end):
    mask=((monthly['month']>=start)&(monthly['month']<=end)&monthly['fwd_max_ret_63'].notna()).to_numpy()
    pos=np.flatnonzero(mask)
    mons=monthly.loc[mask,'month'].astype(str).to_numpy()
    groups=[np.flatnonzero(mons==m) for m in pd.unique(mons)]
    return pos,groups,monthly.loc[mask,'target_abs_up'].to_numpy(np.int8),monthly.loc[mask,'fwd_max_ret_63'].to_numpy(float),monthly.loc[mask,'lead_30'].to_numpy(float),list(pd.unique(mons))

vpos,vgroups,vy,vret,vlead,vmonths=split_arrays(*splits['validation'])
lpos,lgroups,ly,lret,llead,lmonths=split_arrays(*splits['lockbox'])

def month_top_metrics(sc,y,rets,leads,groups):
    prec=[]; recall=[]; meanret=[]; lead=[]
    for ix in groups:
        k=min(10,len(ix)); local=sc[ix]
        topix=ix[np.argpartition(local,-k)[-k:]]
        hits=y[topix]
        ev=int(y[ix].sum())
        prec.append(float(hits.mean()))
        recall.append(float(hits.sum()/ev) if ev else np.nan)
        meanret.append(float(np.nanmean(rets[topix])))
        hl=leads[topix][hits==1]
        lead.append(float(np.nanmean(hl)) if np.isfinite(hl).any() else np.nan)
    return np.array(prec),np.array(recall),np.array(meanret),np.array(lead)

base_v_sc=base_score[vpos]
base_v_prec,base_v_rec,base_v_ret,base_v_lead=month_top_metrics(base_v_sc,vy,vret,vlead,vgroups)
base_l_sc=base_score[lpos]
base_l_prec,base_l_rec,base_l_ret,base_l_lead=month_top_metrics(base_l_sc,ly,lret,llead,lgroups)

records=[]
start_time=time.time()
rank_arrays={f:ranks[f].to_numpy(dtype=np.float32) for f in feature_names}
for idx,c in enumerate(cand_df.itertuples(index=False),start=1):
    a=rank_arrays[c.f1]
    sc=(a if c.s1==1 else 1-a)
    if isinstance(c.f2,str) and c.f2:
        b=rank_arrays[c.f2]
        sc=(sc+(b if c.s2==1 else 1-b))/2
    vsc=sc[vpos]
    vp,vr,vm,vl=month_top_metrics(vsc,vy,vret,vlead,vgroups)
    diffs=vp-base_v_prec
    finite=np.isfinite(diffs)
    p=float(stats.ttest_1samp(diffs[finite],0,alternative='greater').pvalue) if finite.sum()>=8 and np.nanstd(diffs[finite],ddof=1)>0 else 1.0
    records.append({
      'candidate_id':c.candidate_id,'kind':c.kind,'f1':c.f1,'s1':int(c.s1),'f2':c.f2 if isinstance(c.f2,str) else '', 's2':int(c.s2) if pd.notna(c.s2) else 0,
      'family1':c.family1,'family2':c.family2 if isinstance(c.family2,str) else '',
      'val_precision10':float(np.nanmean(vp)),'val_recall10':float(np.nanmean(vr)),'val_mean_fwd_max10':float(np.nanmean(vm)),'val_lead30':float(np.nanmean(vl)) if np.isfinite(vl).any() else np.nan,
      'val_precision_improvement':float(np.nanmean(diffs)),'val_p_precision_improvement':p,
    })
    if idx%5000==0: print('validation screened',idx,'elapsed',round(time.time()-start_time,1),flush=True)
ledger=pd.DataFrame(records)
# Global BH-FDR over every registered trial.
p=ledger['val_p_precision_improvement'].to_numpy(); order=np.argsort(p); q=np.empty_like(p); m=len(p); prev=1.0
for rank,ix in reversed(list(enumerate(order,start=1))):
    val=min(prev,p[ix]*m/rank); q[ix]=val; prev=val
ledger['val_q_global']=q
ledger['validation_screen_pass']=(ledger['val_q_global']<.05)&(ledger['val_precision_improvement']>0)

# Only validation-screen survivors may open the untouched lockbox.
for col in ['val_ap','val_auc','lock_ap','lock_auc','lock_precision10','lock_recall10','lock_mean_fwd_max10','lock_lead30','val_ap_improvement','lock_ap_improvement','lock_precision_improvement','lock_return_improvement']:
    ledger[col]=np.nan
selected=np.flatnonzero(ledger['validation_screen_pass'].to_numpy())
for j in selected:
    c=cand_df.iloc[j]
    a=rank_arrays[c.f1]; sc=(a if c.s1==1 else 1-a)
    if isinstance(c.f2,str) and c.f2:
        b=rank_arrays[c.f2]; sc=(sc+(b if c.s2==1 else 1-b))/2
    vsc=sc[vpos]; lsc=sc[lpos]
    ledger.at[j,'val_ap']=average_precision_score(vy,vsc); ledger.at[j,'val_auc']=roc_auc_score(vy,vsc)
    lp,lr,lm,ll=month_top_metrics(lsc,ly,lret,llead,lgroups)
    ledger.at[j,'lock_ap']=average_precision_score(ly,lsc); ledger.at[j,'lock_auc']=roc_auc_score(ly,lsc)
    ledger.at[j,'lock_precision10']=np.nanmean(lp); ledger.at[j,'lock_recall10']=np.nanmean(lr); ledger.at[j,'lock_mean_fwd_max10']=np.nanmean(lm); ledger.at[j,'lock_lead30']=np.nanmean(ll) if np.isfinite(ll).any() else np.nan
    ledger.at[j,'val_ap_improvement']=ledger.at[j,'val_ap']-base_val['ap']
    ledger.at[j,'lock_ap_improvement']=ledger.at[j,'lock_ap']-base_lock['ap']
    ledger.at[j,'lock_precision_improvement']=ledger.at[j,'lock_precision10']-base_lock['precision10']
    ledger.at[j,'lock_return_improvement']=ledger.at[j,'lock_mean_fwd_max10']-base_lock['mean_fwd_max10']
ledger['passes_statistical_gate']=ledger['validation_screen_pass']&(ledger['val_ap_improvement']>0)&(ledger['lock_ap_improvement']>0)&(ledger['lock_precision_improvement']>0)&(ledger['lock_return_improvement']>0)
ledger=ledger.sort_values(['passes_statistical_gate','validation_screen_pass','val_q_global','val_precision_improvement'],ascending=[False,False,True,False])
ledger.to_csv(OUT/'ledgers/V60_MASSIVE_MOVE_GLOBAL_TRIAL_LEDGER.csv',index=False)

summary={
 'study_id':PROTOCOL['study_id'],'protocol_sha256':proto_hash,'candidate_grid_sha256':cand_hash,
 'panel_rows':int(len(df)),'tickers':int(df['Name'].nunique()),'monthly_rows':int(len(monthly)),'base_features':len(feature_names),'candidates_registered':int(len(cand_df)),'candidates_tested':int(len(ledger)),
 'best_declared_baseline':best_base,'baseline_validation':base_val,'baseline_lockbox':base_lock,
 'global_fdr_survivors_validation':int((ledger['val_q_global']<.05).sum()),'full_gate_survivors':int(ledger['passes_statistical_gate'].sum()),
 'top_candidates':ledger.head(20).to_dict('records'),
 'claim_status':'DISCOVERY_ONLY_NOT_LIVE_PROOF','live_decision_weight':0.0,'capital_permission':'BLOCKED',
 'reasons_blocked':PROTOCOL['known_limits']+['pairwise search on a short panel is not prospective evidence','fundamentals/revisions/ownership/derivatives inputs absent']
}
(OUT/'results/V60_MASSIVE_MOVE_RESULTS.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
print(json.dumps({k:summary[k] for k in ['base_features','candidates_registered','candidates_tested','best_declared_baseline','global_fdr_survivors_validation','full_gate_survivors']},indent=2))
print('top',ledger.head(10)[['candidate_id','val_ap_improvement','val_q_global','lock_ap_improvement','lock_precision_improvement','lock_return_improvement','passes_statistical_gate']].to_string(index=False))
