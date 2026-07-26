from __future__ import annotations
import csv, hashlib, json, math, sys, time, warnings
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from parquet_compat import read_parquet_compat
R=ROOT/'research_v61';P=R/'protocols';O=R/'results';L=R/'ledgers';D=R/'data'
PROTO=P/'V61_NETWORK_DIFFUSION_PROTOCOL_FROZEN.json';GRID=P/'V61_NETWORK_DIFFUSION_CANDIDATE_GRID_FROZEN.csv'
warnings.filterwarnings('ignore',category=RuntimeWarning)

def future_roll(x,h,op):
    rev=x.shift(-1).iloc[::-1];roll=rev.rolling(h,min_periods=h);return (roll.max() if op=='max' else roll.min()).iloc[::-1]
def rank_np(df):return df.rank(axis=1,pct=True,method='average').to_numpy(dtype='float32')
def group_peer_np(arr,labels):
    out=np.full_like(arr,np.nan,dtype='float32')
    for lab in np.unique(labels):
        idx=np.where(labels==lab)[0];sub=arr[:,idx];ok=np.isfinite(sub);sm=np.nansum(sub,axis=1);ct=ok.sum(axis=1)
        for pos,j in enumerate(idx):
            val=sub[:,pos];v=np.isfinite(val);den=ct-v.astype(int);num=sm-np.where(v,val,0)
            out[:,j]=np.divide(num,den,out=np.full(len(den),np.nan),where=den>0)
    return out
def corr_w(corr,k=20):
    a=np.asarray(corr,float).copy();np.fill_diagonal(a,-np.inf);w=np.zeros_like(a,dtype='float32')
    for i in range(len(a)):
        ix=np.argpartition(a[i],-k)[-k:];vals=np.clip(a[i,ix],0,None)
        if vals.sum()<=0:vals=np.ones_like(vals)
        w[i,ix]=(vals/vals.sum()).astype('float32')
    return w
def weighted_peer_np(arr,w):
    ok=np.isfinite(arr);z=np.where(ok,arr,0).astype('float32');num=z@w.T;den=ok.astype('float32')@w.T
    return np.divide(num,den,out=np.full_like(num,np.nan),where=den>0)
def build():
    t=time.time();sp=read_parquet_compat(ROOT/'research'/'sp500_panel.parquet').copy();sp['date']=pd.to_datetime(sp['date'])
    panels={k:sp.pivot(index='date',columns='Name',values=k).sort_index().astype(float) for k in ['open','high','low','close','volume']}
    o,h,l,c,v=(panels[k] for k in ['open','high','low','close','volume']);r=c.pct_change(fill_method=None);prev=c.shift(1)
    tr=pd.DataFrame(np.maximum.reduce([(h-l).values,(h-prev).abs().values,(l-prev).abs().values]),index=c.index,columns=c.columns)
    overnight=o/prev-1;intraday=(h-l)/o.replace(0,np.nan);nr=r.shift(-1)
    corp=(r.abs()>=.45)&(((r*nr<0)&(nr.abs()>=.35))|((overnight.abs()>=.40)&(intraday<=.15)))
    valid=~(corp.rolling(252,min_periods=1).max().astype(bool)|future_roll(corp.astype(float),126,'max').fillna(0).astype(bool))
    disc=r.loc[:'2015-12-31'];good=disc.notna().sum()>=400;cols=list(c.columns[good]);c=c[cols];r=r[cols];v=v[cols];valid=valid[cols];o=o[cols];h=h[cols];l=l[cols];tr=tr[cols]
    base={hh:c.pct_change(hh,fill_method=None) for hh in [5,21,63]}
    selfdf={
      'self_ret_5':base[5],'self_ret_21':base[21],'self_ret_63':base[63],'self_mom_252_21':c.shift(21)/c.shift(252)-1,
      'self_atr_63':tr.rolling(63).mean()/c,'self_compression_20_63':-((h.rolling(20).max()-l.rolling(20).min())/(h.rolling(63).max()-l.rolling(63).min()).replace(0,np.nan)),
      'self_volume_ratio_5_20':v.rolling(5).mean()/v.rolling(20).mean(),'self_dist_high_63':c/c.rolling(63).max()-1,
      'self_range_loc_63':(c-c.rolling(63).min())/(c.rolling(63).max()-c.rolling(63).min()).replace(0,np.nan)}
    corr=disc[cols].corr(min_periods=200).fillna(0).clip(-1,1);np.fill_diagonal(corr.values,1);dist=np.sqrt(np.maximum(0,.5*(1-corr.values)));np.fill_diagonal(dist,0)
    labels={f'cluster{k}':AgglomerativeClustering(n_clusters=k,metric='precomputed',linkage='average').fit_predict(dist) for k in [24,48]};w=corr_w(corr.values,20)
    pd.DataFrame({'symbol':cols,'cluster24':labels['cluster24'],'cluster48':labels['cluster48']}).to_csv(D/'V61_DISCOVERY_NETWORK_CLUSTERS.csv',index=False)
    np.savez_compressed(D/'V61_DISCOVERY_CORR20_WEIGHTS.npz',symbols=np.array(cols),weights=w)
    raw={};bnp={hh:base[hh].to_numpy(dtype='float32') for hh in [5,21,63]};pos={hh:np.where(np.isfinite(bnp[hh]),(bnp[hh]>0).astype('float32'),np.nan) for hh in [5,21,63]}
    vr=selfdf['self_volume_ratio_5_20'].to_numpy(dtype='float32');bo=np.where(c.notna(),(c>=.98*c.rolling(63).max()).astype('float32'),np.nan).astype('float32')
    for method in ['cluster24','cluster48','corr20']:
        peer=(lambda x,lab=labels.get(method):group_peer_np(x,lab)) if method!='corr20' else (lambda x:weighted_peer_np(x,w))
        pr={hh:peer(bnp[hh]) for hh in [5,21,63]};pb={hh:peer(pos[hh]) for hh in [5,21,63]}
        for hh in [5,21,63]:raw[f'{method}_peer_ret_{hh}']=pr[hh];raw[f'{method}_peer_breadth_{hh}']=pb[hh];raw[f'{method}_follower_gap_{hh}']=pr[hh]-bnp[hh]
        raw[f'{method}_peer_accel_5_21']=pr[5]-pr[21];raw[f'{method}_peer_accel_21_63']=pr[21]-pr[63]
        raw[f'{method}_peer_volume_ratio_5_20']=peer(vr);raw[f'{method}_peer_breakout_share_63']=peer(bo)
        raw[f'{method}_network_residual_21']=bnp[21]-pr[21];raw[f'{method}_network_residual_63']=bnp[63]-pr[63]
    valid_np=valid.to_numpy(bool)
    ranks={k:rank_np(pd.DataFrame(a,index=c.index,columns=cols).where(valid)) for k,a in raw.items()}
    ranks.update({k:rank_np(df.where(valid)) for k,df in selfdf.items()})
    fmax={hh:future_roll(c,hh,'max')/c-1 for hh in [21,63,126]};fmin={hh:future_roll(c,hh,'min')/c-1 for hh in [21,63,126]};ep={hh:c.shift(-hh)/c-1 for hh in [21,63,126]}
    targ={
      'up20_21':np.where((valid&fmax[21].notna()).to_numpy(),(fmax[21]>=.20).to_numpy(dtype='float32'),np.nan),
      'up30_63':np.where((valid&fmax[63].notna()).to_numpy(),(fmax[63]>=.30).to_numpy(dtype='float32'),np.nan),
      'up50_126':np.where((valid&fmax[126].notna()).to_numpy(),(fmax[126]>=.50).to_numpy(dtype='float32'),np.nan),
      'down20_63':np.where((valid&fmin[63].notna()).to_numpy(),(fmin[63]<=-.20).to_numpy(dtype='float32'),np.nan)}
    outs={'up20_21':(ep[21],fmax[21],fmin[21]),'up30_63':(ep[63],fmax[63],fmin[63]),'up50_126':(ep[126],fmax[126],fmin[126]),'down20_63':(ep[63],fmax[63],fmin[63])}
    outs={k:tuple(x.to_numpy(dtype='float32') for x in vv) for k,vv in outs.items()}
    print(f'feature_build_seconds={time.time()-t:.1f} symbols={len(cols)} features={len(ranks)}',flush=True)
    return c.index,cols,ranks,targ,outs,valid_np,corr

def orient(a,s):return a if int(s)==1 else 1-a
def top5(score,avail):
    # Exact top 5% rounded up against the frozen 483-symbol universe.
    n=score.shape[2];topn=max(1,int(math.ceil(.05*n)))
    x=np.where(avail,score,-np.inf)
    ix=np.argpartition(x,n-topn,axis=2)[:,:,n-topn:]
    sel=np.zeros_like(avail,dtype=bool)
    np.put_along_axis(sel,ix,True,axis=2)
    return sel&avail
def block_vec(diff,idx,block=21):
    a=diff[:,idx];n=(a.shape[1]//block)*block
    if n<block*5:return np.nanmean(a,axis=1),np.full(a.shape[0],np.inf),np.zeros(a.shape[0],int)
    b=np.nanmean(a[:,:n].reshape(a.shape[0],-1,block),axis=2);cnt=np.isfinite(b).sum(axis=1);mean=np.nanmean(b,axis=1);sd=np.nanstd(b,axis=1,ddof=1);se=np.divide(sd,np.sqrt(cnt),out=np.full_like(sd,np.inf),where=cnt>=5);return mean,se,cnt
def daily_mean(sel,x):
    den=sel.sum(axis=2);num=np.nansum(np.where(sel,x[None],np.nan),axis=2);return np.divide(num,den,out=np.full_like(num,np.nan,dtype=float),where=den>0)
def make_selections(score,base1,base2,target):
    avail=np.isfinite(score)&np.isfinite(target)[None]
    cs=top5(score,avail)
    b1=top5(np.broadcast_to(base1[None],score.shape),avail&np.isfinite(base1)[None])
    b2=top5(np.broadcast_to(base2[None],score.shape),avail&np.isfinite(base2)[None])
    return cs,b1,b2
def eval_from_sel(cs,bs,target,outcomes,idx,z):
    yy=target>0.5;cd=cs.sum(axis=2);bd=bs.sum(axis=2)
    cp=np.divide((cs&yy[None]).sum(axis=2),cd,out=np.full(cd.shape,np.nan,float),where=cd>0)
    bp=np.divide((bs&yy[None]).sum(axis=2),bd,out=np.full(bd.shape,np.nan,float),where=bd>0)
    mean,se,blocks=block_vec(cp-bp,idx)
    seln=cs[:,idx].sum(axis=(1,2));events=(cs[:,idx]&yy[None,idx]).sum(axis=(1,2))
    bseln=bs[:,idx].sum(axis=(1,2));bevents=(bs[:,idx]&yy[None,idx]).sum(axis=(1,2))
    prec=np.divide(events,seln,out=np.full(events.shape,np.nan,float),where=seln>0)
    bprec=np.divide(bevents,bseln,out=np.full(bevents.shape,np.nan,float),where=bseln>0)
    ep,mfe,mae=outcomes
    em=np.nanmean(daily_mean(cs[:,idx],ep[idx]),axis=1);bem=np.nanmean(daily_mean(bs[:,idx],ep[idx]),axis=1)
    mm=np.nanmean(daily_mean(cs[:,idx],mfe[idx]),axis=1);am=np.nanmean(daily_mean(cs[:,idx],mae[idx]),axis=1)
    return {'selected_n':seln,'selected_events':events,'precision':prec,'baseline_precision':bprec,'precision_lift':prec-bprec,'daily_diff_mean':mean,'block_se':se,'adjusted_lb':mean-z*se,'blocks':blocks,'mean_endpoint_return':em,'baseline_mean_endpoint_return':bem,'mean_mfe':mm,'mean_mae':am}
def at(d,i):return {k:(int(v[i]) if k in {'selected_n','selected_events','blocks'} else float(v[i])) for k,v in d.items()}

def main():
    t0=time.time();grid=list(csv.DictReader(GRID.open()));dates,cols,ranks,targets,outs,valid,corr=build();datearr=np.asarray(dates)
    splitidx={'discovery':np.where((datearr>=np.datetime64('2013-02-08'))&(datearr<=np.datetime64('2015-12-31')))[0],
              'validation':np.where((datearr>=np.datetime64('2016-01-01'))&(datearr<=np.datetime64('2016-12-31')))[0],
              'lockbox':np.where((datearr>=np.datetime64('2017-01-01'))&(datearr<=np.datetime64('2018-02-07')))[0]}
    m=len(grid)*len(targets)*2;z=NormalDist().inv_cdf(1-.05/m);ledger=[];details=[];chunk=48
    for start in range(0,len(grid),chunk):
        rows=grid[start:start+chunk];sc=[]
        for row in rows:
            a=orient(ranks[row['network_feature']],row['network_orientation']).astype('float32',copy=False)
            if row['kind']=='single':s=a
            elif row['kind']=='pair':s=(a+orient(ranks[row['self_feature']],row['self_orientation']))/2
            else:s=(a+orient(ranks[row['self_feature']],row['self_orientation'])+orient(ranks[row['third_feature']],row['third_orientation']))/3
            sc.append(s)
        score=np.stack(sc,axis=0)
        for tname,target in targets.items():
            direction=-1 if tname.startswith('down') else 1;base1=orient(ranks['self_mom_252_21'],direction);base2=ranks['self_atr_63']
            cs,b1,b2=make_selections(score,base1,base2,target)
            splitres={s:{} for s in splitidx}
            for s,idx in splitidx.items():
                splitres[s]['vs_momentum']=eval_from_sel(cs,b1,target,outs[tname],idx,z)
                splitres[s]['vs_atr']=eval_from_sel(cs,b2,target,outs[tname],idx,z)
            for i,row in enumerate(rows):
                d={'claim_id':f"{tname}|{row['candidate_id']}",'target':tname,**row,'bonferroni_z':z,'splits':{}}
                for s in splitidx:d['splits'][s]={'vs_momentum':at(splitres[s]['vs_momentum'],i),'vs_atr':at(splitres[s]['vs_atr'],i)}
                ok=all(d['splits'][s][b]['adjusted_lb']>0 for s in ['validation','lockbox'] for b in ['vs_momentum','vs_atr']) and all(d['splits'][s]['vs_momentum']['selected_events']>=10 for s in ['validation','lockbox'])
                d['promoted_diagnostic']=bool(ok);details.append(d)
                ledger.append({'claim_id':d['claim_id'],'target':tname,'candidate_id':row['candidate_id'],'kind':row['kind'],
                 'validation_lb_vs_momentum':d['splits']['validation']['vs_momentum']['adjusted_lb'],'validation_lb_vs_atr':d['splits']['validation']['vs_atr']['adjusted_lb'],
                 'lockbox_lb_vs_momentum':d['splits']['lockbox']['vs_momentum']['adjusted_lb'],'lockbox_lb_vs_atr':d['splits']['lockbox']['vs_atr']['adjusted_lb'],
                 'validation_precision':d['splits']['validation']['vs_momentum']['precision'],'lockbox_precision':d['splits']['lockbox']['vs_momentum']['precision'],
                 'promoted_diagnostic':bool(ok),'production_promoted':False,'live_decision_weight':0.0,'capital_permission':'BLOCKED'})
        print(f'candidate {min(start+chunk,len(grid))}/{len(grid)} elapsed={time.time()-t0:.1f}s',flush=True)
    def key(d):return min(d['splits'][s][b]['adjusted_lb'] for s in ['validation','lockbox'] for b in ['vs_momentum','vs_atr'])
    best=sorted(details,key=lambda d:np.nan_to_num(key(d),nan=-999),reverse=True)[:50];prom=[d for d in details if d['promoted_diagnostic']]
    summary={'schema':'warroom.v61.network_diffusion_results','protocol_sha256':hashlib.sha256(PROTO.read_bytes()).hexdigest(),'candidate_count':len(grid),'target_count':len(targets),'registered_claims':len(details),'comparison_count':len(details)*2,'diagnostic_promoted_claims':len(prom),'production_promoted_claims':0,'panel_limit':'fixed survivor-biased 2013-2018 panel; pass cannot become live proof','best_50':best,'promoted':prom,'network_fit':{'symbols':len(cols),'discovery_corr_sha256':hashlib.sha256(np.asarray(corr,dtype='float64').tobytes()).hexdigest()},'runtime_seconds':time.time()-t0,'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
    (O/'V61_NETWORK_DIFFUSION_RESULTS.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');pd.DataFrame(ledger).to_csv(L/'V61_NETWORK_DIFFUSION_GLOBAL_LEDGER.csv',index=False)
    pd.DataFrame([{'claim_id':d['claim_id'],'target':d['target'],'candidate_id':d['candidate_id'],'kind':d['kind'],'score_floor':key(d),'validation_precision':d['splits']['validation']['vs_momentum']['precision'],'lockbox_precision':d['splits']['lockbox']['vs_momentum']['precision']} for d in best]).to_csv(O/'V61_NETWORK_DIFFUSION_BEST50.csv',index=False)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('best_50','promoted')},indent=2))
if __name__=='__main__':main()
