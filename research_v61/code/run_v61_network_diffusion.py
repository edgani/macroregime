from __future__ import annotations
import csv, hashlib, json, math, sys, time
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from parquet_compat import read_parquet_compat
R=ROOT/'research_v61'; P=R/'protocols'; O=R/'results'; L=R/'ledgers'; D=R/'data'
PROTO=P/'V61_NETWORK_DIFFUSION_PROTOCOL_FROZEN.json'; GRID=P/'V61_NETWORK_DIFFUSION_CANDIDATE_GRID_FROZEN.csv'

def future_roll(x,h,op):
    rev=x.shift(-1).iloc[::-1]; roll=rev.rolling(h,min_periods=h); return (roll.max() if op=='max' else roll.min()).iloc[::-1]
def rank(x): return x.rank(axis=1,pct=True,method='average').astype('float32')
def rolling_sum(x,h): return x.rolling(h,min_periods=h).sum()
def block_stats(x,block=21):
    x=np.asarray(x,float);x=x[np.isfinite(x)]
    if len(x)<block*5:return float(np.nanmean(x)) if len(x) else np.nan, np.inf, 0
    vals=[np.nanmean(x[i:i+block]) for i in range(0,len(x)-block+1,block)]
    vals=np.asarray(vals,float); vals=vals[np.isfinite(vals)]
    if len(vals)<5:return float(np.nanmean(x)),np.inf,len(vals)
    return float(vals.mean()),float(vals.std(ddof=1)/math.sqrt(len(vals))),len(vals)
def group_peer(mat,labels):
    arr=mat.to_numpy(dtype='float64'); out=np.full_like(arr,np.nan)
    for lab in np.unique(labels):
        idx=np.where(labels==lab)[0]
        sub=arr[:,idx]; ok=np.isfinite(sub); sm=np.nansum(sub,axis=1); ct=ok.sum(axis=1)
        for j in idx:
            val=arr[:,j]; v=np.isfinite(val); den=ct-v.astype(int); num=sm-np.where(v,val,0.0)
            out[:,j]=np.divide(num,den,out=np.full(len(den),np.nan),where=den>0)
    return pd.DataFrame(out,index=mat.index,columns=mat.columns)
def corr_neighbor_matrix(corr,k=20):
    a=np.asarray(corr,float); np.fill_diagonal(a,-np.inf); w=np.zeros_like(a)
    for i in range(len(a)):
        ix=np.argpartition(a[i],-k)[-k:]; vals=np.clip(a[i,ix],0,None)
        if vals.sum()<=0: vals=np.ones_like(vals)
        w[i,ix]=vals/vals.sum()
    return w
def weighted_peer(mat,w):
    arr=mat.to_numpy(dtype='float64'); valid=np.isfinite(arr); z=np.where(valid,arr,0.0)
    num=z@w.T; den=valid.astype(float)@w.T
    out=np.divide(num,den,out=np.full_like(num,np.nan),where=den>0)
    return pd.DataFrame(out,index=mat.index,columns=mat.columns)
def build_features():
    sp=read_parquet_compat(ROOT/'research'/'sp500_panel.parquet').copy();sp['date']=pd.to_datetime(sp['date'])
    panels={k:sp.pivot(index='date',columns='Name',values=k).sort_index().astype(float) for k in ['open','high','low','close','volume']}
    o,h,l,c,v=(panels[k] for k in ['open','high','low','close','volume']); r=c.pct_change(fill_method=None); lr=np.log(c).diff(); prev=c.shift(1)
    tr=pd.DataFrame(np.maximum.reduce([(h-l).values,(h-prev).abs().values,(l-prev).abs().values]),index=c.index,columns=c.columns)
    overnight=o/prev-1; intraday=(h-l)/o.replace(0,np.nan); next_r=r.shift(-1)
    corp=(r.abs()>=.45)&(((r*next_r<0)&(next_r.abs()>=.35))|((overnight.abs()>=.40)&(intraday<=.15)))
    valid=~(corp.rolling(252,min_periods=1).max().astype(bool)|future_roll(corp.astype(float),126,'max').fillna(0).astype(bool))
    self_raw={
      'self_ret_5':c.pct_change(5,fill_method=None),'self_ret_21':c.pct_change(21,fill_method=None),'self_ret_63':c.pct_change(63,fill_method=None),
      'self_mom_252_21':c.shift(21)/c.shift(252)-1,'self_atr_63':tr.rolling(63).mean()/c,
      'self_compression_20_63':-((h.rolling(20).max()-l.rolling(20).min())/(h.rolling(63).max()-l.rolling(63).min()).replace(0,np.nan)),
      'self_volume_ratio_5_20':v.rolling(5).mean()/v.rolling(20).mean(),
      'self_dist_high_63':c/c.rolling(63).max()-1,
      'self_range_loc_63':(c-c.rolling(63).min())/(c.rolling(63).max()-c.rolling(63).min()).replace(0,np.nan),
    }
    disc=r.loc[:'2015-12-31']; good=disc.notna().sum()>=400; cols=list(c.columns[good]); c=c[cols];r=r[cols];v=v[cols];valid=valid[cols]
    self_raw={k:x[cols] for k,x in self_raw.items()}
    corr=disc[cols].corr(min_periods=200).fillna(0).clip(-1,1); np.fill_diagonal(corr.values,1)
    dist=np.sqrt(np.maximum(0,.5*(1-corr.values))); np.fill_diagonal(dist,0)
    cluster_maps={}
    for k in [24,48]:
        labels=AgglomerativeClustering(n_clusters=k,metric='precomputed',linkage='average').fit_predict(dist)
        cluster_maps[f'cluster{k}']=labels
    w=corr_neighbor_matrix(corr.values,20)
    # Save discovery-only network construction evidence.
    pd.DataFrame({'symbol':cols,'cluster24':cluster_maps['cluster24'],'cluster48':cluster_maps['cluster48']}).to_csv(D/'V61_DISCOVERY_NETWORK_CLUSTERS.csv',index=False)
    np.savez_compressed(D/'V61_DISCOVERY_CORR20_WEIGHTS.npz',symbols=np.array(cols),weights=w.astype('float32'))
    features={}
    base_h={h:c.pct_change(h,fill_method=None) for h in [5,21,63]}
    pos_h={h:(base_h[h]>0).astype(float).where(base_h[h].notna()) for h in [5,21,63]}
    volratio=self_raw['self_volume_ratio_5_20']; breakout=(c>=.98*c.rolling(63).max()).astype(float).where(c.notna())
    for method in ['cluster24','cluster48','corr20']:
        if method.startswith('cluster'):
            labels=cluster_maps[method]; peer=lambda x:group_peer(x,labels)
        else: peer=lambda x:weighted_peer(x,w)
        p_ret={h:peer(base_h[h]) for h in [5,21,63]}; p_br={h:peer(pos_h[h]) for h in [5,21,63]}
        for h0 in [5,21,63]:
            features[f'{method}_peer_ret_{h0}']=p_ret[h0]
            features[f'{method}_peer_breadth_{h0}']=p_br[h0]
            features[f'{method}_follower_gap_{h0}']=p_ret[h0]-base_h[h0]
        features[f'{method}_peer_accel_5_21']=p_ret[5]-p_ret[21]
        features[f'{method}_peer_accel_21_63']=p_ret[21]-p_ret[63]
        features[f'{method}_peer_volume_ratio_5_20']=peer(volratio)
        features[f'{method}_peer_breakout_share_63']=peer(breakout)
        features[f'{method}_network_residual_21']=base_h[21]-p_ret[21]
        features[f'{method}_network_residual_63']=base_h[63]-p_ret[63]
    ranks={k:rank(x.where(valid)) for k,x in {**features,**self_raw}.items()}
    # Targets and magnitude outcomes.
    fmax={h:future_roll(c,h,'max')/c-1 for h in [21,63,126]}; fmin63=future_roll(c,63,'min')/c-1
    endpoint={h:c.shift(-h)/c-1 for h in [21,63,126]}
    targets={
      'up20_21':(fmax[21]>=.20).astype(float).where(valid&fmax[21].notna()),
      'up30_63':(fmax[63]>=.30).astype(float).where(valid&fmax[63].notna()),
      'up50_126':(fmax[126]>=.50).astype(float).where(valid&fmax[126].notna()),
      'down20_63':(fmin63<=-.20).astype(float).where(valid&fmin63.notna()),
    }
    outcomes={
      'up20_21':{'endpoint':endpoint[21],'mfe':fmax[21],'mae':future_roll(c,21,'min')/c-1},
      'up30_63':{'endpoint':endpoint[63],'mfe':fmax[63],'mae':fmin63},
      'up50_126':{'endpoint':endpoint[126],'mfe':fmax[126],'mae':future_roll(c,126,'min')/c-1},
      'down20_63':{'endpoint':endpoint[63],'mfe':fmax[63],'mae':fmin63},
    }
    return c.index,cols,ranks,targets,outcomes,valid,corr

def oriented(r,sign): return r if int(sign)==1 else (1-r)
def selection(score,mask):
    rr=score.where(mask).rank(axis=1,pct=True,method='average');return (rr>=.95)&mask

def daily_precision(sel,y):
    yy=y>0.5;den=sel.sum(axis=1);num=(sel&yy).sum(axis=1);return (num/den.replace(0,np.nan)).astype(float)
def selected_mean(sel,x):
    den=sel.sum(axis=1);return x.where(sel).sum(axis=1,min_count=1)/den.replace(0,np.nan)
def eval_comparison(csel,bsel,y,outcome,date_mask,z):
    cs=csel.loc[date_mask];bs=bsel.loc[date_mask];yy=y.loc[date_mask];yyb=yy>0.5
    cp=daily_precision(cs,yy);bp=daily_precision(bs,yy);diff=(cp-bp).dropna();mean,se,blocks=block_stats(diff.values)
    ev=int((cs&yyb).sum().sum()); seln=int(cs.sum().sum()); precision=float((cs&yyb).sum().sum()/seln) if seln else np.nan
    bseln=int(bs.sum().sum()); bprecision=float((bs&yyb).sum().sum()/bseln) if bseln else np.nan
    em=selected_mean(cs,outcome['endpoint'].loc[date_mask]);bm=selected_mean(bs,outcome['endpoint'].loc[date_mask])
    mfe=selected_mean(cs,outcome['mfe'].loc[date_mask]);mae=selected_mean(cs,outcome['mae'].loc[date_mask])
    return {'selected_n':seln,'selected_events':ev,'precision':precision,'baseline_precision':bprecision,'precision_lift':precision-bprecision,
            'daily_diff_mean':mean,'block_se':se,'adjusted_lb':mean-z*se,'blocks':blocks,
            'mean_endpoint_return':float(np.nanmean(em)),'baseline_mean_endpoint_return':float(np.nanmean(bm)),
            'mean_mfe':float(np.nanmean(mfe)),'mean_mae':float(np.nanmean(mae))}

def main():
    t0=time.time();proto=json.loads(PROTO.read_text());grid=list(csv.DictReader(GRID.open()))
    dates,cols,ranks,targets,outcomes,valid,corr=build_features()
    splits={'discovery':(dates>='2013-02-08')&(dates<='2015-12-31'),'validation':(dates>='2016-01-01')&(dates<='2016-12-31'),'lockbox':(dates>='2017-01-01')&(dates<='2018-02-07')}
    m=len(grid)*len(targets)*2;z=NormalDist().inv_cdf(1-.05/m)
    ledger=[];best=[];promoted=[]
    for i,row in enumerate(grid):
        score=oriented(ranks[row['network_feature']],row['network_orientation'])
        if row['kind'] in ('pair','triple'):
            score=score+oriented(ranks[row['self_feature']],row['self_orientation'])
            denom=2
            if row['kind']=='triple':score=score+oriented(ranks[row['third_feature']],row['third_orientation']);denom=3
            score=score/denom
        for tname,y in targets.items():
            direction=-1 if tname.startswith('down') else 1
            base_mom=oriented(ranks['self_mom_252_21'],direction)
            base_atr=ranks['self_atr_63']
            mask=valid & y.notna() & score.notna()
            csel=selection(score,mask); b1=selection(base_mom,mask&base_mom.notna()); b2=selection(base_atr,mask&base_atr.notna())
            result={'claim_id':f"{tname}|{row['candidate_id']}",'target':tname,**row,'bonferroni_z':z,'splits':{}}
            ok=True
            for s,dm in splits.items():
                r1=eval_comparison(csel,b1,y,outcomes[tname],dm,z);r2=eval_comparison(csel,b2,y,outcomes[tname],dm,z)
                result['splits'][s]={'vs_momentum':r1,'vs_atr':r2}
                if s in ('validation','lockbox'):
                    if not (r1['adjusted_lb']>0 and r2['adjusted_lb']>0 and r1['selected_events']>=10):ok=False
            result['promoted_diagnostic']=bool(ok)
            if ok:promoted.append(result)
            ledger.append({
              'claim_id':result['claim_id'],'target':tname,'candidate_id':row['candidate_id'],'kind':row['kind'],
              'validation_lb_vs_momentum':result['splits']['validation']['vs_momentum']['adjusted_lb'],
              'validation_lb_vs_atr':result['splits']['validation']['vs_atr']['adjusted_lb'],
              'lockbox_lb_vs_momentum':result['splits']['lockbox']['vs_momentum']['adjusted_lb'],
              'lockbox_lb_vs_atr':result['splits']['lockbox']['vs_atr']['adjusted_lb'],
              'validation_precision':result['splits']['validation']['vs_momentum']['precision'],
              'lockbox_precision':result['splits']['lockbox']['vs_momentum']['precision'],
              'promoted_diagnostic':bool(ok),'production_promoted':False,'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
            score_key=min(result['splits']['validation']['vs_momentum']['adjusted_lb'],result['splits']['validation']['vs_atr']['adjusted_lb'],result['splits']['lockbox']['vs_momentum']['adjusted_lb'],result['splits']['lockbox']['vs_atr']['adjusted_lb'])
            best.append((score_key,result))
        if (i+1)%100==0: print(f'candidate {i+1}/{len(grid)} elapsed={time.time()-t0:.1f}s',flush=True)
    best=sorted(best,key=lambda x:(-np.nan_to_num(x[0],nan=-999)) )[:50]
    summary={
      'schema':'warroom.v61.network_diffusion_results','protocol_sha256':hashlib.sha256(PROTO.read_bytes()).hexdigest(),
      'candidate_count':len(grid),'target_count':len(targets),'registered_claims':len(ledger),'comparison_count':len(ledger)*2,
      'diagnostic_promoted_claims':len(promoted),'production_promoted_claims':0,
      'panel_limit':'fixed survivor-biased 2013-2018 S&P-style panel; no production claim allowed',
      'best_50':[r for _,r in best],'promoted':promoted,
      'network_fit':{'symbols':len(cols),'discovery_corr_sha256':hashlib.sha256(np.asarray(corr,dtype='float64').tobytes()).hexdigest()},
      'runtime_seconds':time.time()-t0,'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
    (O/'V61_NETWORK_DIFFUSION_RESULTS.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    pd.DataFrame(ledger).to_csv(L/'V61_NETWORK_DIFFUSION_GLOBAL_LEDGER.csv',index=False)
    pd.DataFrame([{k:v for k,v in r.items() if k!='splits'}|{
      'validation_precision':r['splits']['validation']['vs_momentum']['precision'],
      'validation_lb_vs_momentum':r['splits']['validation']['vs_momentum']['adjusted_lb'],
      'validation_lb_vs_atr':r['splits']['validation']['vs_atr']['adjusted_lb'],
      'lockbox_precision':r['splits']['lockbox']['vs_momentum']['precision'],
      'lockbox_lb_vs_momentum':r['splits']['lockbox']['vs_momentum']['adjusted_lb'],
      'lockbox_lb_vs_atr':r['splits']['lockbox']['vs_atr']['adjusted_lb']} for _,r in best]).to_csv(O/'V61_NETWORK_DIFFUSION_BEST50.csv',index=False)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('best_50','promoted')},indent=2))
if __name__=='__main__':main()
