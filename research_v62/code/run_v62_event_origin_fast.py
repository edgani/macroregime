from __future__ import annotations
import csv, hashlib, json, math, sys, time
from pathlib import Path
from statistics import NormalDist
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from parquet_compat import read_parquet_compat
R=ROOT/'research_v62';P=R/'protocols';O=R/'results';L=R/'ledgers';D=R/'data'
PROTO=P/'V62_EVENT_ORIGIN_PROTOCOL_FROZEN.json';GRID=P/'V62_EVENT_ORIGIN_CANDIDATE_GRID_FROZEN.csv'

def future_roll(x,h,op):
    rev=x.shift(-1).iloc[::-1];roll=rev.rolling(h,min_periods=h);return (roll.max() if op=='max' else roll.min()).iloc[::-1]
def rank_np(df):return df.rank(axis=1,pct=True,method='average').to_numpy(dtype='float32')
def rolling_z(df,w=63):
    mu=df.rolling(w,min_periods=w).mean();sd=df.rolling(w,min_periods=w).std(ddof=0).replace(0,np.nan);return (df-mu)/sd

def build():
    t=time.time();sp=read_parquet_compat(ROOT/'research'/'sp500_panel.parquet').copy();sp['date']=pd.to_datetime(sp['date'])
    panels={k:sp.pivot(index='date',columns='Name',values=k).sort_index().astype(float) for k in ['open','high','low','close','volume']}
    o,h,l,c,v=(panels[k] for k in ['open','high','low','close','volume']);r=c.pct_change(fill_method=None);prev=c.shift(1)
    tr=pd.DataFrame(np.maximum.reduce([(h-l).values,(h-prev).abs().values,(l-prev).abs().values]),index=c.index,columns=c.columns)
    gap=o/prev-1;intraday=c/o-1;clv=(c-l)/(h-l).replace(0,np.nan);nr=r.shift(-1)
    corp=(r.abs()>=.45)&(((r*nr<0)&(nr.abs()>=.35))|((gap.abs()>=.40)&((h-l)/o.replace(0,np.nan)<=.15)))
    valid=~(corp.rolling(252,min_periods=1).max().astype(bool)|future_roll(corp.astype(float),126,'max').fillna(0).astype(bool))
    disc=r.loc[:'2015-12-31'];good=disc.notna().sum()>=400;cols=list(c.columns[good]);o=o[cols];h=h[cols];l=l[cols];c=c[cols];v=v[cols];r=r[cols];tr=tr[cols];gap=gap[cols];intraday=intraday[cols];clv=clv[cols];valid=valid[cols]
    gapz=rolling_z(gap,63).clip(-8,8);volz=rolling_z(np.log1p(v),63).clip(-8,8);vzpos=volz.clip(lower=0)
    posgap=gapz.clip(lower=0);neggap=(-gapz).clip(lower=0)
    posevent=posgap*vzpos*clv.clip(0,1);negevent=neggap*vzpos*(1-clv.clip(0,1))
    raw={}
    for w in [5,10,21]:
        raw[f'pos_gapz_max_{w}']=posgap.rolling(w,min_periods=max(3,w//2)).max()
        raw[f'neg_gapz_max_{w}']=neggap.rolling(w,min_periods=max(3,w//2)).max()
        raw[f'pos_event_max_{w}']=posevent.rolling(w,min_periods=max(3,w//2)).max()
        raw[f'neg_event_max_{w}']=negevent.rolling(w,min_periods=max(3,w//2)).max()
        raw[f'pos_event_sum_{w}']=posevent.rolling(w,min_periods=max(3,w//2)).sum()
        raw[f'neg_event_sum_{w}']=negevent.rolling(w,min_periods=max(3,w//2)).sum()
        raw[f'pos_event_ema_{w}']=posevent.ewm(span=w,min_periods=w,adjust=False).mean()
        raw[f'neg_event_ema_{w}']=negevent.ewm(span=w,min_periods=w,adjust=False).mean()
        den=gap.abs().rolling(w,min_periods=max(3,w//2)).sum().replace(0,np.nan)
        raw[f'gap_directional_persistence_{w}']=gap.rolling(w,min_periods=max(3,w//2)).sum()/den
        raw[f'event_volume_persistence_{w}']=(np.sign(gap)*vzpos).rolling(w,min_periods=max(3,w//2)).mean()
        raw[f'gap_hold_{w}']=c.pct_change(w,fill_method=None)-gap.rolling(w,min_periods=max(3,w//2)).sum()
        raw[f'gap_fill_pressure_{w}']=-(np.sign(gap)*intraday).rolling(w,min_periods=max(3,w//2)).mean()
    selfdf={
      'self_ret_5':c.pct_change(5,fill_method=None),'self_ret_21':c.pct_change(21,fill_method=None),'self_ret_63':c.pct_change(63,fill_method=None),'self_mom_252_21':c.shift(21)/c.shift(252)-1,
      'self_atr_63':tr.rolling(63).mean()/c,'self_compression_20_63':-((h.rolling(20).max()-l.rolling(20).min())/(h.rolling(63).max()-l.rolling(63).min()).replace(0,np.nan)),
      'self_volume_ratio_5_20':v.rolling(5).mean()/v.rolling(20).mean(),'self_dist_high_63':c/c.rolling(63).max()-1,
      'self_range_loc_63':(c-c.rolling(63).min())/(c.rolling(63).max()-c.rolling(63).min()).replace(0,np.nan)}
    ranks={k:rank_np(df.where(valid)) for k,df in raw.items()};ranks.update({k:rank_np(df.where(valid)) for k,df in selfdf.items()})
    fmax={hh:future_roll(c,hh,'max')/c-1 for hh in [21,63,126]};fmin={hh:future_roll(c,hh,'min')/c-1 for hh in [21,63,126]};ep={hh:c.shift(-hh)/c-1 for hh in [21,63,126]}
    targ={
      'up20_21':np.where((valid&fmax[21].notna()).to_numpy(),(fmax[21]>=.20).to_numpy(dtype='float32'),np.nan),
      'up30_63':np.where((valid&fmax[63].notna()).to_numpy(),(fmax[63]>=.30).to_numpy(dtype='float32'),np.nan),
      'up50_126':np.where((valid&fmax[126].notna()).to_numpy(),(fmax[126]>=.50).to_numpy(dtype='float32'),np.nan),
      'down20_63':np.where((valid&fmin[63].notna()).to_numpy(),(fmin[63]<=-.20).to_numpy(dtype='float32'),np.nan)}
    outs={'up20_21':(ep[21],fmax[21],fmin[21]),'up30_63':(ep[63],fmax[63],fmin[63]),'up50_126':(ep[126],fmax[126],fmin[126]),'down20_63':(ep[63],fmax[63],fmin[63])}
    outs={k:tuple(x.to_numpy(dtype='float32') for x in vv) for k,vv in outs.items()}
    print(f'feature_build_seconds={time.time()-t:.1f} symbols={len(cols)} features={len(ranks)}',flush=True)
    return c.index,cols,ranks,targ,outs,valid.to_numpy(bool)
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
    t0=time.time();grid=list(csv.DictReader(GRID.open()));dates,cols,ranks,targets,outs,valid=build();datearr=np.asarray(dates)
    splitidx={'discovery':np.where((datearr>=np.datetime64('2013-02-08'))&(datearr<=np.datetime64('2015-12-31')))[0],
              'validation':np.where((datearr>=np.datetime64('2016-01-01'))&(datearr<=np.datetime64('2016-12-31')))[0],
              'lockbox':np.where((datearr>=np.datetime64('2017-01-01'))&(datearr<=np.datetime64('2018-02-07')))[0]}
    m=len(grid)*len(targets)*2;z=NormalDist().inv_cdf(1-.05/m);ledger=[];details=[];chunk=48
    for start in range(0,len(grid),chunk):
        rows=grid[start:start+chunk];sc=[]
        for row in rows:
            a=orient(ranks[row['event_feature']],row['event_orientation']).astype('float32',copy=False)
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
    summary={'schema':'warroom.v62.event_origin_results','protocol_sha256':hashlib.sha256(PROTO.read_bytes()).hexdigest(),'candidate_count':len(grid),'target_count':len(targets),'registered_claims':len(details),'comparison_count':len(details)*2,'diagnostic_promoted_claims':len(prom),'production_promoted_claims':0,'panel_limit':'fixed survivor-biased 2013-2018 panel; OHLCV event proxies lack event labels and PIT fundamentals','best_50':best,'promoted':prom,'runtime_seconds':time.time()-t0,'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
    (O/'V62_EVENT_ORIGIN_RESULTS.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n');pd.DataFrame(ledger).to_csv(L/'V62_EVENT_ORIGIN_GLOBAL_LEDGER.csv',index=False)
    pd.DataFrame([{'claim_id':d['claim_id'],'target':d['target'],'candidate_id':d['candidate_id'],'kind':d['kind'],'score_floor':key(d),'validation_precision':d['splits']['validation']['vs_momentum']['precision'],'lockbox_precision':d['splits']['lockbox']['vs_momentum']['precision']} for d in best]).to_csv(O/'V62_EVENT_ORIGIN_BEST50.csv',index=False)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('best_50','promoted')},indent=2))
if __name__=='__main__':main()
