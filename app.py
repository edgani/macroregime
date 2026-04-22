"""MacroRegime Pro v12.0 — Fully Self-Contained"""
import os, sys, glob, time, json, logging, requests, numpy as np, pandas as pd, yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import streamlit as st

# Cache bust
for f in glob.glob("/tmp/*.pkl"):
    try: os.remove(f)
    except: pass
try: st.cache_data.clear()
except: pass

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regime_engine import get_regime_snapshot

# ═══════════════════════════════════════════════════════════════════════════════
# TRR/LRR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
TRR_PARAMS = {
    'tradeLen':15,'trendLen':63,'tailLen':756,'rvLen':20,'normLen':63,'volRocLen':5,'atrLen':14,
    'tradeATRMult':1.35,'trendATRMult':2.05,'tailATRMult':4.20,
    'shockBoost':0.22,'trendShockBoost':0.15,'tailShockBoost':0.12,
    'tradeThresh':0.20,'tradeNeutralBand':0.06,'trendThresh':0.14,'trendNeutralBand':0.05,
    'tailThresh':0.10,'tailNeutralBand':0.03,'trendFreezeTF':'M','tailFreezeTF':'3M',
    'stocksVolMult':1.00,'forexVolMult':0.35,'cryptoVolMult':0.80,'commodVolMult':1.00,
}

def _clip(x,lo,hi): return np.clip(x,lo,hi)
def _c01(x): return np.clip(x,0.0,1.0)
def _roc(s,n): return (s/s.shift(n)-1.0)*100.0
def _z(s,n):
    m=s.rolling(n).mean(); d=s.rolling(n).std()
    o=pd.Series(0.0,index=s.index); mask=d.notna()&(d!=0); o[mask]=(s[mask]-m[mask])/d[mask]; return o
def _er(s,n):
    den=s.diff().abs().rolling(n).sum(); num=s.diff(n).abs()
    o=pd.Series(0.0,index=s.index); mask=den.notna()&(den!=0); o[mask]=num[mask]/den[mask]; return o
def _kama(s,erlen,fast,slow):
    er=_er(s,erlen); fsc=2.0/(fast+1.0); ssc=2.0/(slow+1.0); sc=np.power(er*(fsc-ssc)+ssc,2.0)
    o=pd.Series(np.nan,index=s.index); o.iloc[0]=s.iloc[0]
    for i in range(1,len(s)):
        p=o.iloc[i-1]; o.iloc[i]=s.iloc[i] if np.isnan(p) or np.isnan(sc.iloc[i]) else p+sc.iloc[i]*(s.iloc[i]-p)
    return o
def _gk(df):
    eps=1e-10; h=np.maximum(df['High'],df['Open']+eps); l=np.maximum(df['Low'],eps)
    o=np.maximum(df['Open'],eps); c=np.maximum(df['Close'],eps)
    return np.maximum(0.0,0.5*np.power(np.log(h/l),2.0)-(2.0*np.log(2.0)-1.0)*np.power(np.log(c/o),2.0))
def _atr(df,n=14):
    h,l,c=df['High'],df['Low'],df['Close']
    tr=pd.concat([h-l,(h-c.shift(1)).abs(),(l-c.shift(1)).abs()],axis=1).max(axis=1)
    return tr.ewm(alpha=1.0/n,adjust=False,min_periods=n).mean()
def _tfreset(idx,tf):
    s=pd.Series(idx,index=idx); p=s.shift(1)
    if tf=='M': return pd.Series((s.dt.month!=p.dt.month).fillna(False).values,index=idx)
    if tf=='3M': return pd.Series(((s.dt.month!=p.dt.month)&(s.dt.month%3==0)).fillna(False).values,index=idx)
    return pd.Series((s.dt.year!=p.dt.year).fillna(False).values,index=idx)
def _hys(score,th,neu,prev):
    if score>th: return 1
    if score<-th: return -1
    if abs(score)<=neu: return 0
    return int(prev)

class TRRLRREngine:
    def __init__(self,p=TRR_PARAMS): self.p=p
    def bundle(self,df,vm=1.0):
        p=self.p; c,h,l,o,v=df['Close'],df['High'],df['Low'],df['Open'],df['Volume'].fillna(0)
        atr14=_atr(df,p['atrLen']); lr=np.log(c/c.shift(1))
        rvf=lr.rolling(p['rvLen']).std()*np.sqrt(252); rvm=lr.rolling(max(p['rvLen']*2,30)).std()*np.sqrt(252)
        rvs=lr.rolling(max(p['rvLen']*4,60)).std()*np.sqrt(252); tel=max(63,min(p['tailLen'],756))
        tb=_kama(c,p['tradeLen'],2,p['tradeLen']); trb=_kama(c,p['trendLen'],3,p['trendLen'])
        tab=_kama(c,tel,5,tel); troc=_z(_roc(c,p['tradeLen']),p['normLen'])
        trroc=_z(_roc(c,p['trendLen']),p['normLen'])
        tar=_z(_roc(c,252).fillna(_roc(c,126)).fillna(_roc(c,63)).fillna(_roc(c,21)).fillna(0),p['normLen'])
        td=_z(((c/tb.replace(0,np.nan))-1.0)*100.0,p['normLen']); trd=_z(((c/trb.replace(0,np.nan))-1.0)*100.0,p['normLen'])
        tad=_z(((c/tab.replace(0,np.nan))-1.0)*100.0,p['normLen']); tsl=_z(_roc(tb,3),p['normLen'])
        trsl=_z(_roc(trb,10),p['normLen']); tas=_z(_roc(tab,21).fillna(_roc(tab,10)).fillna(_roc(tab,5)).fillna(0),p['normLen'])
        rv=_roc(v,p['volRocLen']); tv=_z(rv.ewm(span=2,adjust=False).mean(),p['normLen'])*vm
        trv=_z(rv.ewm(span=5,adjust=False).mean(),p['normLen'])*vm; tav=_z(rv.ewm(span=10,adjust=False).mean(),p['normLen'])*vm
        tp=_z(_er(c,max(5,int(round(p['tradeLen']*0.7)))),p['normLen']); trp=_z(_er(c,p['trendLen']),p['normLen'])
        tap=_z(_er(c,63),p['normLen']).fillna(_z(_er(c,21),p['normLen'])).fillna(0.0)
        rbf=rvf.rolling(50).mean().fillna(rvf); rbm=rvm.rolling(50).mean().fillna(rvm); rbs=rvs.rolling(50).mean().fillna(rvs)
        vf=pd.Series(np.where(rbf>0,(rvf/rbf)-1.0,0.0),index=c.index); vm_=pd.Series(np.where(rbm>0,(rvm/rbm)-1.0,0.0),index=c.index)
        vs=pd.Series(np.where(rbs>0,(rvs/rbs)-1.0,0.0),index=c.index)
        ts=0.30*troc+0.24*tsl+0.18*td+0.14*tp+0.10*tv-0.08*_z(vf,p['normLen'])
        trs=0.24*trroc+0.28*trsl+0.22*trd+0.14*trp+0.08*trv-0.06*_z(vm_,p['normLen'])
        tas_=0.18*tar+0.30*tas+0.24*tad+0.16*tap+0.06*tav-0.04*_z(vs,p['normLen'])
        ap=pd.Series(np.where(c!=0,atr14/c,0.0),index=c.index)
        tsh=_z(vf+0.60*_roc(ap,1),p['normLen']); trsh=_z(vm_+0.45*_roc(ap,3),p['normLen'])
        tash=_z(vs+0.30*_roc(ap,8),p['normLen']); gk=_gk(df)
        grv=np.sqrt(np.maximum(gk.rolling(p['rvLen']).mean()*252.0,0.0)); grb=grv.rolling(50).mean().fillna(grv)
        gv=grv.rolling(max(p['rvLen'],20)).std().fillna(0); gvb=gv.rolling(50).mean().fillna(np.maximum(gv,0.001))
        return pd.DataFrame({
            'atr':atr14.shift(1),'trdSc':ts.shift(1),'trdShk':tsh.shift(1),'trdBs':tb.shift(1),
            'trnSc':trs.shift(1),'trnShk':trsh.shift(1),'trnBs':trb.shift(1),
            'talSc':tas_.shift(1),'talShk':tash.shift(1),'talBs':tab.shift(1),
            'c1':c.shift(1),'c2':c.shift(2),'v1':v.shift(1),'vsma1':v.rolling(20).mean().shift(1),
            'gkRv':grv.shift(1),'gkRvBase':grb.shift(1),'gkVov':gv.shift(1),'gkVovBase':gvb.shift(1),
        },index=df.index)

    def latest(self,df,vm=1.0):
        p=self.p; b=self.bundle(df,vm); n=len(b); c=df['Close'].values
        if n<300: return None
        ac=_atr(df,14).values; atr=b['atr'].values; tsc=b['trdSc'].values; tsh=b['trdShk'].values; tbs=b['trdBs'].values
        trsc=b['trnSc'].values; trsh=b['trnShk'].values; trbs=b['trnBs'].values
        talsc=b['talSc'].values; talsh=b['talShk'].values; talbs=b['talBs'].values
        gkr=b['gkRv'].values; gkrb=b['gkRvBase'].values; gkv=b['gkVov'].values; gkvb=b['gkVovBase'].values
        tr=_tfreset(df.index,p['trendFreezeTF']).values; tar=_tfreset(df.index,p['tailFreezeTF']).values
        tph=np.zeros(n,dtype=int); trph=np.zeros(n,dtype=int); talph=np.zeros(n,dtype=int)
        ptb=np.full(n,np.nan); pta=np.full(n,np.nan); ptab=np.full(n,np.nan); ptar=np.full(n,np.nan)
        etb=np.full(n,np.nan); etab=np.full(n,np.nan); tage=np.zeros(n,dtype=int); talge=np.zeros(n,dtype=int)
        for i in range(n):
            if i==0:
                ptb[i]=trbs[i] if not np.isnan(trbs[i]) else c[i]; pta[i]=atr[i] if not np.isnan(atr[i]) else ac[i]
                ptab[i]=talbs[i] if not np.isnan(talbs[i]) else c[i]; ptar[i]=atr[i] if not np.isnan(atr[i]) else ac[i]
                continue
            if tr[i]: ptb[i]=trbs[i] if not np.isnan(trbs[i]) else c[i]; pta[i]=atr[i] if not np.isnan(atr[i]) else ac[i]
            else:
                ptb[i]=ptb[i-1] if not np.isnan(ptb[i-1]) else (trbs[i] if not np.isnan(trbs[i]) else c[i])
                pta[i]=pta[i-1] if not np.isnan(pta[i-1]) else (atr[i] if not np.isnan(atr[i]) else ac[i])
            if tar[i]: ptab[i]=talbs[i] if not np.isnan(talbs[i]) else c[i]; ptar[i]=atr[i] if not np.isnan(atr[i]) else ac[i]
            else:
                ptab[i]=ptab[i-1] if not np.isnan(ptab[i-1]) else (talbs[i] if not np.isnan(talbs[i]) else c[i])
                ptar[i]=ptar[i-1] if not np.isnan(ptar[i-1]) else (atr[i] if not np.isnan(atr[i]) else ac[i])
            grf=_clip(0.50+0.50*(gkr[i]/gkrb[i]),0.65,1.50) if gkrb[i]>0 else 1.0
            gvf=_clip(1.0+0.25*max((gkv[i]/gkvb[i])-1.0,0.0),1.0,1.25) if gkvb[i]>0 else 1.0
            pw=atr[i]*p['tradeATRMult']*grf*gvf*max(0.65,1.0+p['shockBoost']*max(tsh[i],0.0))
            ptr=tbs[i]+pw; plr=max(tbs[i]-pw,1e-10)
            trw=max(pta[i],atr[i])*p['trendATRMult']*grf*gvf*max(0.70,1.0+p['trendShockBoost']*max(trsh[i],0.0))
            ttr=ptb[i]+trw; tlr=max(ptb[i]-trw,1e-10)
            taw=max(ptar[i],atr[i])*p['tailATRMult']*grf*gvf*max(0.80,1.0+p['tailShockBoost']*max(talsh[i],0.0))
            ttrr=ptab[i]+taw; tlrr=max(ptab[i]-taw,1e-10)
            rt=_hys(tsc[i],p['tradeThresh'],p['tradeNeutralBand'],tph[i-1])
            rtr=_hys(trsc[i],p['trendThresh'],p['trendNeutralBand'],trph[i-1])
            rta=_hys(talsc[i],p['tailThresh'],p['tailNeutralBand'],talph[i-1])
            tph[i]=1 if c[i]>ptr else (-1 if c[i]<plr else rt)
            ttu=c[i]>ttr and trph[i-1]<=0; ttd=c[i]<tlr and trph[i-1]>=0
            if ttu: trph[i]=1; etb[i]=c[i]; pta[i]=ac[i]
            elif ttd: trph[i]=-1; etb[i]=c[i]; pta[i]=ac[i]
            else: trph[i]=rtr; etb[i]=etb[i-1] if not np.isnan(etb[i-1]) else ptb[i]
            tlu=c[i]>ttrr and talph[i-1]<=0; tld=c[i]<tlrr and talph[i-1]>=0
            if tlu: talph[i]=1; etab[i]=c[i]; ptar[i]=ac[i]
            elif tld: talph[i]=-1; etab[i]=c[i]; ptar[i]=ac[i]
            else: talph[i]=rta; etab[i]=etab[i-1] if not np.isnan(etab[i-1]) else ptab[i]
            tage[i]=0 if (tr[i] or ttu or ttd) else tage[i-1]+1
            talge[i]=0 if (tar[i] or tlu or tld) else talge[i-1]+1
        i=n-1; utb=etb[i] if not np.isnan(etb[i]) else ptb[i]; utab=etab[i] if not np.isnan(etab[i]) else ptab[i]
        fta=max(pta[i],atr[i]); ftar=max(ptar[i],atr[i])
        bb=0.35 if (c[i]>ptr or c[i]<plr) else 0.0; tbb=0.50 if (ttu or ttd) else 0.0; tabb=0.40 if (tlu or tld) else 0.0
        grf=_clip(0.50+0.50*(gkr[i]/gkrb[i]),0.65,1.50) if gkrb[i]>0 else 1.0
        gvf=_clip(1.0+0.25*max((gkv[i]/gkvb[i])-1.0,0.0),1.0,1.25) if gkvb[i]>0 else 1.0
        tw=atr[i]*p['tradeATRMult']*grf*gvf*max(0.65,1.0+(p['shockBoost']+bb)*max(tsh[i],0.0))
        ttr_=tbs[i]+tw; tlr_=max(tbs[i]-tw,1e-10)
        trw_=fta*p['trendATRMult']*grf*gvf*max(0.70,1.0+(p['trendShockBoost']+tbb)*max(trsh[i],0.0))
        ttr__=utb+trw_; tlr__=max(utb-trw_,1e-10)
        taw_=ftar*p['tailATRMult']*grf*gvf*max(0.80,1.0+(p['tailShockBoost']+tabb)*max(talsh[i],0.0))
        ttrr_=utab+taw_; tlrr_=max(utab-taw_,1e-10)
        cs=df['Close']; ach=cs.diff().abs(); erd=ach.rolling(20).sum()
        erv=pd.Series(np.where(erd==0,0.0,cs.diff(20).abs()/erd),index=df.index)
        i0=pd.Series(range(len(df)),index=df.index); cr=cs.rolling(30).corr(i0)
        r2=pd.Series(np.where(np.isnan(cr),0.0,cr**2),index=df.index)
        adx=ach.rolling(14).mean()/(df['High']-df['Low']).rolling(14).mean().replace(0,np.nan)
        an=_c01((adx.iloc[-1]-12.0)/28.0); en=_c01(erv.iloc[-1]); rn=_c01(r2.iloc[-1])
        qs=100.0*(0.45*an+0.35*en+0.20*rn)
        apv=np.where(cs.values!=0,(b['atr'].values/cs.values)*100.0,0.0); aps=pd.Series(apv,index=df.index)
        apb=aps.rolling(50).mean().fillna(aps); aatr=_c01(aps.iloc[-1]/(apb.iloc[-1]*1.25)) if apb.iloc[-1]>0 else 0.5
        rvn=np.log(cs/cs.shift(1)).rolling(p['rvLen']).std()*np.sqrt(252.0); rvb=rvn.rolling(50).mean().fillna(rvn)
        arv=_c01(rvn.iloc[-1]/(rvb.iloc[-1]*1.20)) if rvb.iloc[-1]>0 else 0.5
        vb=df['Volume'].rolling(20).mean().fillna(df['Volume'])
        avr=_c01(df['Volume'].iloc[-1]/(vb.iloc[-1]*1.35)) if vb.iloc[-1]>0 else 0.5
        av=0.35+0.65*avr*vm
        act=100.0*_clip(0.42*aatr+0.43*arv+0.15*av,0.0,1.0)
        cmp=100.0*_clip(1.0-(0.50*aatr+0.38*arv+0.12*av),0.0,1.0)
        return {
            'tradeTRR':float(ttr_),'tradeLRR':float(tlr_),'trendTRR':float(ttr__),'trendLRR':float(tlr__),
            'tailTRR':float(ttrr_),'tailLRR':float(tlrr_),'tradePhase':int(tph[i]),'trendPhase':int(trph[i]),'tailPhase':int(talph[i]),
            'trendTransUp':bool(ttu),'trendTransDown':bool(ttd),'tailTransUp':bool(tlu),'tailTransDown':bool(tld),
            'tradeBreakUp':bool(c[i]>ttr_),'tradeBreakDown':bool(c[i]<tlr_),'trendAge':int(tage[i]),'tailAge':int(talge[i]),
            'qualityScore':float(qs),'activityScore':float(act),'compressionScore':float(cmp),'volRegimeConfirm':bool(gkv[i]>gkvb[i]*1.30),
            'pubTradeScore':float(tsc[i]),'pubTrendScore':float(trsc[i]),'pubTailScore':float(talsc[i]),
        }

@st.cache_data(ttl=600)
def _fetch(ticker,period="3y"):
    try:
        df=yf.download(ticker,period=period,interval="1d",progress=False,auto_adjust=True)
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        df=df.dropna(); return df if len(df)>=300 else None
    except: return None

GATE={
    "US_STOCKS":{"vm":1.00,"qmin":55,"amin":40,"short":True,"agemax":35},
    "IHSG":{"vm":1.00,"qmin":50,"amin":35,"short":False,"agemax":30},
    "COMMODITIES":{"vm":1.00,"qmin":50,"amin":40,"short":True,"agemax":45},
    "FOREX":{"vm":0.35,"qmin":55,"amin":40,"short":True,"agemax":40},
    "CRYPTO":{"vm":0.80,"qmin":50,"amin":45,"short":True,"agemax":30},
}
_eng=TRRLRREngine()

def _eval(ticker,ac):
    cfg=GATE.get(ac,GATE["US_STOCKS"]); p="2y" if ac=="CRYPTO" else "3y"; df=_fetch(ticker,p)
    if df is None: return None
    try: r=_eng.latest(df,vm=cfg['vm'])
    except: return None
    if not r: return None
    pr=df['Close'].iloc[-1]
    lg=(r['tradeBreakUp'] or r['trendTransUp'] or r['tailTransUp']) and r['qualityScore']>=cfg['qmin'] and r['activityScore']>=cfg['amin'] and r['trendAge']<=cfg['agemax']
    sg=cfg['short'] and (r['tradeBreakDown'] or r['trendTransDown'] or r['tailTransDown']) and r['qualityScore']>=cfg['qmin'] and r['activityScore']>=cfg['amin'] and r['trendAge']<=cfg['agemax']
    if not lg and not sg: return None
    sig="LONG" if lg else "SHORT"
    cf=min(100,int(50+r['qualityScore']*0.3+r['activityScore']*0.2+(25 if (r['trendTransUp'] or r['trendTransDown'] or r['tailTransUp'] or r['tailTransDown']) else 0)))
    rs=[]
    if r['tradeBreakUp']: rs.append(f"Price>TradeTRR({r['tradeTRR']:.2f})")
    if r['tradeBreakDown']: rs.append(f"Price<TradeLRR({r['tradeLRR']:.2f})")
    if r['trendTransUp']: rs.append("TREND-UP")
    if r['trendTransDown']: rs.append("TREND-DOWN")
    if r['tailTransUp']: rs.append("TAIL-UP")
    if r['tailTransDown']: rs.append("TAIL-DOWN")
    return {'ticker':ticker,'signal':sig,'confidence':cf,'price':round(pr,4),'tradeTRR':round(r['tradeTRR'],4),'tradeLRR':round(r['tradeLRR'],4),'trendTRR':round(r['trendTRR'],4),'trendLRR':round(r['trendLRR'],4),'tailTRR':round(r['tailTRR'],4),'tailLRR':round(r['tailLRR'],4),'trendPhase':r['trendPhase'],'tailPhase':r['tailPhase'],'trendAge':r['trendAge'],'tailAge':r['tailAge'],'quality':round(r['qualityScore'],1),'activity':round(r['activityScore'],1),'compression':round(r['compressionScore'],1),'volRegime':"EXPANDING" if r['volRegimeConfirm'] else "NORMAL",'reason':" | ".join(rs)}

def _render_trr(tlist,ac,title="🎯 TRR/LRR Live Signals"):
    if not tlist: return
    hits=[]; dbg=[]
    for t in tlist:
        ev=_eval(t,ac)
        if ev: hits.append(ev)
        else:
            df=_fetch(t,"2y" if ac=="CRYPTO" else "3y")
            if df is not None:
                try:
                    r=_eng.latest(df,vm=GATE.get(ac,GATE["US_STOCKS"])['vm'])
                    if r:
                        pr=df['Close'].iloc[-1]; cfg=GATE.get(ac,GATE["US_STOCKS"]); rs=[]
                        if not (r['tradeBreakUp'] or r['trendTransUp'] or r['tailTransUp']): rs.append("No breakout")
                        if r['qualityScore']<cfg['qmin']: rs.append(f"Q{r['qualityScore']:.0f}<{cfg['qmin']}")
                        if r['activityScore']<cfg['amin']: rs.append(f"A{r['activityScore']:.0f}<{cfg['amin']}")
                        if r['trendAge']>cfg['agemax']: rs.append(f"Age{r['trendAge']}>{cfg['agemax']}")
                        dbg.append({'ticker':t,'price':round(pr,2),'q':round(r['qualityScore'],1),'a':round(r['activityScore'],1),'age':r['trendAge'],'phase':r['trendPhase'],'fail':" | ".join(rs) if rs else "N/A"})
                except: pass
    if not hits:
        st.caption(f"TRR/LRR: No {ac} tickers passed the gate.")
        if dbg:
            with st.expander(f"🔍 {ac} TRR/LRR Debug ({len(dbg)} evaluated)"):
                st.dataframe(pd.DataFrame(dbg),use_container_width=True,height=200)
        return
    hits.sort(key=lambda x:(0 if x['signal']=='LONG' else 1,-x['confidence']))
    st.markdown(f"**{title}**")
    for h in hits:
        col="#3fb950" if h['signal']=='LONG' else "#f85149"; ic="▲" if h['signal']=='LONG' else "▼"
        with st.container():
            c1,c2,c3=st.columns([1.2,2.5,1.5])
            with c1: st.markdown(f"<span style='color:{col};font-weight:800;font-size:16px;'>{ic} {h['ticker']}</span>",unsafe_allow_html=True); st.caption(f"Conf: **{h['confidence']}**/100")
            with c2: st.caption(f"Price {h['price']} | TradeTRR {h['tradeTRR']} | TradeLRR {h['tradeLRR']}"); st.caption(f"Trend: Phase {h['trendPhase']} | Age {h['trendAge']}d | Q {h['quality']} | A {h['activity']}")
            with c3: st.caption(f"Trigger: {h['reason']}")
        st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# ON-CHAIN SCANNER
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(level=logging.INFO,format='%(asctime)s | %(levelname)s | %(message)s')
logger=logging.getLogger(__name__)

@dataclass
class CC:
    name:str;slug:str;dune:Optional[str]=None;eth:Optional[str]=None;nt:str="";tc:Optional[str]=None

REG={
    'ethereum':CC('Ethereum','Ethereum','ethereum','api.etherscan.io','ETH','0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
    'base':CC('Base','Base','base','api.basescan.org','ETH','0x4200000000000000000000000000000000000006'),
    'arbitrum':CC('Arbitrum','Arbitrum','arbitrum','api.arbiscan.io','ETH','0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'),
    'optimism':CC('Optimism','Optimism','optimism','api-optimistic.etherscan.io','ETH','0x4200000000000000000000000000000000000006'),
    'solana':CC('Solana','Solana','solana',None,'SOL','So11111111111111111111111111111111111111112'),
    'bittensor':CC('Bittensor','Bittensor',None,None,'TAO',None),
    'avalanche':CC('Avalanche','Avalanche','avalanche','api.snowtrace.io','AVAX','0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'),
    'polygon':CC('Polygon','Polygon','polygon','api.polygonscan.com','MATIC','0x7D1AfA7B718fb893dB30A3abc0Cfc608AaCfeBB0'),
    'bnb':CC('BNB Chain','BSC','bsc','api.bscscan.com','BNB','0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'),
}

class MCS:
    def __init__(self,dk=None,ek=None,tk=None):
        self.dk=dk; self.ek=ek; self.tk=tk; self.le=0; self.ld=0; self.ls=0
    def _req(self,url,params=None,hd=None):
        try:
            r=requests.get(url,params=params,headers=hd,timeout=15)
            return r.json() if r.status_code==200 else None
        except: return None
    def macro(self,slug,lb=7):
        try:
            base="https://api.llama.fi"; res={'chain':slug,'ts':datetime.utcnow().isoformat()}
            d=self._req(f"{base}/v2/historicalChainTvl/{slug}")
            if d:
                res['tvl_now']=d[-1][1]; res['tvl_7d']=d[-min(lb+1,len(d))][1]
                res['tvl_d']=round((d[-1][1]-d[-min(lb+1,len(d))][1])/d[-min(lb+1,len(d))][1]*100,2) if d[-min(lb+1,len(d))][1]>0 else 0
            d=self._req(f"{base}/stablecoincharts/{slug}")
            if d:
                res['stb_now']=d[-1]['totalCirculatingUSD']['peggedUSD']; res['stb_7d']=d[-min(lb+1,len(d))]['totalCirculatingUSD']['peggedUSD']
                res['stb_d']=round((res['stb_now']-res['stb_7d'])/res['stb_7d']*100,2) if res['stb_7d']>0 else 0
            d=self._req(f"{base}/overview/dexs/{slug}?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume")
            if d and 'totalDataChart' in d and d['totalDataChart']:
                v=[x[1] for x in d['totalDataChart'] if x[1]]; 
                if len(v)>=2: res['vol24']=v[-1]; res['vol7m']=np.median(v[-7:]) if len(v)>=7 else np.median(v); res['spike']=round(v[-1]/res['vol7m'],2) if res['vol7m']>0 else 0
            sc=0
            if res.get('stb_d',0)>15: sc+=40
            elif res.get('stb_d',0)>10: sc+=25
            elif res.get('stb_d',0)>5: sc+=10
            if res.get('tvl_d',0)>10: sc+=30
            elif res.get('tvl_d',0)>5: sc+=15
            if res.get('spike',0)>3: sc+=20
            elif res.get('spike',0)>1.5: sc+=10
            res['score']=min(sc,100); res['sig']='HOT' if sc>=60 else 'WARM' if sc>=35 else 'COLD'
            return res
        except Exception as e: logger.error(f"llama err {slug}: {e}"); return {'chain':slug,'error':str(e)}
    def scan(self,targets):
        out=[]
        for k,cfg in targets.items():
            logger.info(f"Scan {k}..."); m=self.macro(REG[k].slug if k in REG else k)
            out.append({'chain':k,'alpha':m.get('score',0),'verdict':('🔥 STRONG' if m.get('score',0)>=70 else '⚡ MONITOR' if m.get('score',0)>=45 else '❄️ PASS'),'macro':m.get('sig','N/A'),'tvl':m.get('tvl_d',0),'stb':m.get('stb_d',0),'dex':m.get('spike',0),'whale':0})
            time.sleep(1)
        return pd.DataFrame(out)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADER
# ═══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=300)
def _load_all():
    regime=get_regime_snapshot()
    tickers={
        "us_longs":["IWM","XLI","ITB","XTL","EQRR","GII","EWH","EWW","ARGT","EIS","IBIT","HII","CAT","UPS","LII","JBHT","MAR","ONTO","EMR","RH","SBUX","TXG","AVO","FRPT","PEP","XOM","HSY","WMB","ET","COAL","YCS"],
        "us_shorts":["XLK","XLF","XLY","IHF","PSCH","MAGS","CIBR","IVES","MSFO","DESK","GRNY","SKYY","MSTY","BTAL","XLP","TLT","ZROZ","ROP","RBLX","TRU","NVDA"],
        "ihsg_buys":["BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK","UNVR.JK","INDF.JK","KLBF.JK"],
        "fx_longs":["USDJPY=X","GLD","AAAU","YCS"],"fx_shorts":["EURUSD=X","AUDUSD=X","UUP"],
        "comm_longs":["SLV","GDX","GC=F","SI=F","HG=F","CL=F","NG=F","XOP","OIH","BNO","GLD","AAAU","COAL"],
        "comm_shorts":["DUST","BITS"],"crypto_longs":["BTC-USD","ETH-USD","IBIT"],"crypto_shorts":["SOL-USD"],
    }
    all_t=list(set([t for v in tickers.values() for t in v]))
    prices={}
    try:
        data=yf.download(" ".join(all_t),period="6mo",interval="1d",progress=False,auto_adjust=True)
        if isinstance(data.columns,pd.MultiIndex):
            for t in all_t:
                if t in data['Close']: prices[t]=data['Close'][t].dropna()
        else:
            prices[all_t[0]]=data['Close'].dropna()
    except:
        for t in all_t:
            try:
                df=yf.download(t,period="6mo",interval="1d",progress=False,auto_adjust=True)
                if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                if not df.empty and 'Close' in df: prices[t]=df['Close'].dropna()
            except: pass
    return {"q":regime,"tickers":tickers,"prices":prices,"btl":{},"narr":{}}

snap=_load_all()
q=snap["q"]; tickers=snap["tickers"]; prices=snap["prices"]
sq=q.get("structural_quad","Q2"); mq=q.get("monthly_quad","Q2"); gq=q.get("global_quad","Q2")
conf=q.get("confidence",0.5); op=q.get("operating_regime","...")
src=q.get("source","unknown"); gy=q.get("growth_yoy",0); iy=q.get("inflation_yoy",0)
ps=q.get("policy_stance","—")

def _h(html): st.markdown(" ".join(html.split()),unsafe_allow_html=True)
QC={"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
def _qb(q): return QC.get(q,("#2d3748","#a0aec0"))[0]
def _qf(q): return QC.get(q,("#2d3748","#a0aec0"))[1]
sbg,sfg=_qb(sq),_qf(sq); mbg,mfg=_qb(mq),_qf(mq); gbg,gfg=_qb(gq),_qf(gq)
sb="🟢 FRED" if src=="fred" else "🟡 YF Proxy" if src=="yfinance_proxy" else "⚪ Fallback"
sc="#3fb950" if src=="fred" else "#fbbf24" if src=="yfinance_proxy" else "#8b949e"

_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;">v12.0 · Auto-Regime · TRR/LRR · On-Chain</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div style="font-size:11px;color:{sc};">{sb} · S:{sq} · M:{mq} · G:{gq}</div>
  </div>
</div>
""")

_h(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="background:{sbg};color:{sfg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">S:{sq}</span>
    <span style="background:{mbg};color:{mfg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">M:{mq}</span>
    <span style="background:{gbg};color:{gfg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">G:{gq}</span>
    <span style="margin-left:auto;color:#fb923c;font-size:13px;font-weight:600;">🔥 {op}</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Conf: <span style="color:#3fb950;font-weight:600;">{conf:.0%}</span></span>
    <span>Growth: <span style="color:#3fb950;">{gy:.1f}% YoY ({q.get('growth_trend','—')})</span></span>
    <span>Inflation: <span style="color:#fb923c;">{iy:.1f}% YoY ({q.get('inflation_trend','—')})</span></span>
    <span>Policy: <span style="color:#58a6ff;">{ps}</span></span>
  </div>
  <div style="font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:8px;">Data: {sb} · Real PCE (Growth) · CPI (Inflation) · DFF+DGS10 (Policy)</div>
</div>
""")

tabs=st.tabs(["⚡ Command Center","🌍 Markets","📊 Regime Deep Dive","⚠️ Risk & Diag"])

# ─── TAB 0: COMMAND CENTER ───
with tabs[0]:
    c1,c2,c3=st.columns(3)
    with c1: st.metric("Structural",sq); st.metric("Monthly",mq)
    with c2: st.metric("Global",gq); st.metric("Confidence",f"{conf:.0%}")
    with c3: st.metric("Growth",f"{gy:.1f}%"); st.metric("Inflation",f"{iy:.1f}%")
    st.divider()
    st.markdown("**📍 LIVE OPPORTUNITIES**")
    cl,cs=st.columns(2)
    with cl:
        st.markdown("▲ US Longs"); 
        for t in tickers['us_longs'][:5]: st.markdown(f"<span style='color:#3fb950;font-weight:600;'>{t}</span>",unsafe_allow_html=True)
        st.markdown("▲ IHSG"); 
        for t in tickers['ihsg_buys'][:5]: st.markdown(f"<span style='color:#fb923c;font-weight:600;'>{t}</span>",unsafe_allow_html=True)
    with cs:
        st.markdown("▼ US Shorts"); 
        for t in tickers['us_shorts'][:5]: st.markdown(f"<span style='color:#f85149;font-weight:600;'>{t}</span>",unsafe_allow_html=True)
    st.divider()
    if sq!=mq:
        st.warning(f"⚠️ TRANSITIONAL — {sq}/{mq} divergen. Trade monthly signal only, jangan buka structural positions.")
    else:
        st.success(f"✅ ALIGNED — {sq} confirmed. Bisa deploy structural + monthly.")

# ─── TAB 1: MARKETS ───
with tabs[1]:
    def rn(s,n):
        if s is None or len(s)<n+1: return float("nan")
        try: b=float(s.iloc[-(n+1)]); e=float(s.iloc[-1]); return float(e/b-1) if b!=0 else float("nan")
        except: return float("nan")
    def gr(s,n): r=rn(s,n); return f"{r:+.1%}" if r==r else "—"
    def tc(tk,name,r1m,r3m,sig):
        col="#3fb950" if sig=="long" else "#f85149" if sig=="short" else "#d29922"
        ic="▲" if sig=="long" else "▼" if sig=="short" else "⚡"
        return f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;flex:1;min-width:140px;"><div><div style="font-size:13px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:10px;color:#8b949e;">{name}</div></div><div style="text-align:right;"><div style="font-size:11px;color:{col};font-weight:700;">{ic} {r1m}</div><div style="font-size:9px;color:#8b949e;">3M: {r3m}</div></div></div>'
    def rc(tlist,nmap,sig,pr=2):
        if not tlist: return
        cards=[]
        for t in tlist: s=prices.get(t); cards.append(tc(t,nmap.get(t,t),gr(s,21),gr(s,63),sig))
        for i in range(0,len(cards),pr): _h('<div style="display:flex;gap:8px;margin-bottom:8px;">'+"".join(cards[i:i+pr])+'</div>')
    def rh(alist):
        if not prices: return
        h=['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for tk,name in alist:
            s=prices.get(tk)
            if s is not None:
                r1=rn(s,21); r3=rn(s,63)
                c="#1a4d2e" if r1>0.05 else "#2d5a3d" if r1>0 else "#5c1a1a" if r1<-0.05 else "#3d1a1a" if r1<0 else "#2d3748"
                txt="#4ade80" if r1>0 else "#f87171" if r1<0 else "#a0aec0"
                h.append(f'<div style="background:{c};padding:6px 10px;border-radius:6px;text-align:center;min-width:80px;"><div style="font-size:11px;color:#8b949e;">{name}</div><div style="font-size:13px;color:{txt};font-weight:700;">{r1:+.1%}</div><div style="font-size:9px;color:#8b949e;">3M {r3:+.1%}</div></div>')
        h.append('</div>'); _h("".join(h))
    def rml(al,bn=None,ti="Leadership"):
        br=rn(prices.get(bn),63) if bn else float("nan")
        rows=[]
        for tk,name in al:
            s=prices.get(tk)
            if s is not None and len(s)>63:
                r3=rn(s,63); rel=(r3-br) if br==br and r3==r3 else r3; rows.append({"name":name,"rel":rel})
        if not rows: st.caption(f"No data for {ti}"); return
        rows.sort(key=lambda r:r["rel"] if r["rel"]==r["rel"] else -999,reverse=True)
        st.markdown(f"**📊 {ti} (Top 5)**")
        for s in rows[:5]:
            rel=s["rel"]; rp=min(max((rel+0.15)/0.3*100,0),100) if rel==rel else 50; bc="#3fb950" if rel>0 else "#f85149" if rel<0 else "#8b949e"
            _h(f'<div style="display:flex;align-items:center;gap:8px;margin:4px 0;"><div style="width:70px;font-size:11px;color:#c9d1d9;">{s["name"]}</div><div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;"><div style="width:{rp}%;background:{bc};height:100%;border-radius:4px;"></div></div><div style="width:60px;text-align:right;font-size:11px;color:{bc};font-weight:600;">{rel:+.1%}</div></div>')

    FX={"USDJPY=X","EURUSD=X","AUDUSD=X","GBPUSD=X","USDCAD=X","USDIDR=X","UUP","DXY","EURGBP=X","EURJPY=X","GBPJPY=X","NZDUSD=X","USDCNH=X","USDCHF=X","AAAU","GLD","YCS"}
    COMM={"SLV","GDX","GC=F","SI=F","HG=F","CL=F","NG=F","XOP","OIH","BNO","GLD","AAAU","DUST","BITS","XAUUSD=X","XAGUSD=X","XTIUSD=X","XBRUSD=X","XCUUSD=X","XNGUSD=X","URA","COAL"}
    CRY={"BTC-USD","ETH-USD","SOL-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","MATIC-USD","LINK-USD","UNI-USD","LTC-USD","BCH-USD","ETC-USD","DOGE-USD","SHIB-USD","TON-USD","NEAR-USD","APT-USD","SUI-USD","IBIT"}

    def is_us(tk): return not any(x in tk for x in [".JK","-USD","=F"]) and tk not in ["^JKSE"] and tk not in FX and tk not in COMM and tk not in CRY
    def is_ih(tk): return ".JK" in tk or tk=="^JKSE"
    def is_fx(tk): return tk in FX
    def is_cm(tk): return tk in COMM
    def is_cr(tk): return tk in CRY

    def rb(filter_fn,market_name):
        mb=[]
        for tk in prices.keys():
            if filter_fn(tk):
                s=prices.get(tk)
                if s is not None and len(s)>21:
                    r1=rn(s,21); r3=rn(s,63)
                    sc=abs(r1)*2+abs(r3) if r1==r1 else 0
                    if sc>0.005:
                        stg="early" if r1>0.05 else "mature" if r1<-0.05 else "building"
                        mb.append({"ticker":tk,"sector":market_name,"score":round(sc,2),"stage":stg})
        if not mb:
            wl={"US":tickers.get("us_longs",[])+tickers.get("us_shorts",[]),"IHSG":tickers.get("ihsg_buys",[]),"FX":tickers.get("fx_longs",[])+tickers.get("fx_shorts",[]),"Commodities":tickers.get("comm_longs",[])+tickers.get("comm_shorts",[]),"Crypto":tickers.get("crypto_longs",[])+tickers.get("crypto_shorts",[])}
            for tk in wl.get(market_name,[]):
                if filter_fn(tk): mb.append({"ticker":tk,"sector":market_name,"score":0.0,"stage":"building"})
        if not mb: st.caption(f"No {market_name} bottleneck."); return
        mb=sorted(mb,key=lambda x:x["score"],reverse=True)[:12]
        fb=[x for x in mb if filter_fn(x.get("ticker",""))]
        if not fb: st.caption(f"No {market_name} bottleneck matched."); return
        h=['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for x in fb[:8]:
            tk=x.get("ticker","—"); sc=x.get("score",0); stg=x.get("stage","—")
            c={"mature":"#f85149","building":"#d29922","early":"#3fb950"}.get(stg,"#8b949e")
            h.append(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 10px;text-align:center;"><div style="font-size:12px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:10px;color:{c};">{stg} · {sc:.2f}</div></div>')
        h.append('</div>'); _h("".join(h))

    def rm(lk,sk,cl,cs,filter_fn,mn):
        at=[]
        for t in tickers.get(lk,[])[:4]: at.append((t,"Long",cl))
        if sk:
            for t in tickers.get(sk,[])[:4]: at.append((t,"Short",cs))
        if at:
            h=['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for t,s,c in at: h.append(f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:4px 8px;font-size:11px;color:{c};font-weight:600;">{t} <span style="color:#8b949e;font-size:9px;">{s}</span></div>')
            h.append('</div>'); _h("".join(h))
        else: st.caption(f"No {mn} tickers")

    mt=st.tabs(["🇺🇸 US Stocks","🇮🇩 IHSG","💱 FX","🛢️ Commodities","🔐 Crypto"])

    with mt[0]:
        ul=tickers.get("us_longs",[]); us=tickers.get("us_shorts",[])
        nm={"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","TLT":"Long Bond","GLD":"Gold","SMH":"Semis","HII":"Huntington","CAT":"Caterpillar","UPS":"UPS","LII":"Lennox","JBHT":"JB Hunt","MAR":"Marriott","ONTO":"Onto","EMR":"Emerson","RH":"Restoration","SBUX":"Starbucks","TXG":"10x Genomics","AVO":"Mission Produce","FRPT":"Freshpet","PEP":"Pepsi","XOM":"Exxon","HSY":"Hershey","WMB":"Williams","ET":"Energy Transfer","ROP":"Roper","RBLX":"Roblox","TRU":"TransUnion","NVDA":"Nvidia","XTL":"Telecom","EQRR":"Rising Rates","GII":"Infrastructure","EWH":"Hong Kong","EWW":"Mexico","ARGT":"Argentina","EIS":"Israel","IBIT":"Bitcoin ETF","COAL":"Coal","YCS":"Short Yen"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG**"); rc(ul,nm,"long",2)
        with c2: st.markdown("**📍 NOW — SHORT**"); rc(us,nm,"short",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("CL=F","Oil"),("UUP","USD")])
        rml([("XLE","Energy"),("XLF","Fin"),("XLI","Ind"),("XLB","Mat"),("XLK","Tech"),("XLV","Health"),("XLY","Con.D"),("XLP","Con.S"),("XLU","Util"),("XLRE","RE")],"SPY","Sector Leadership")
        st.markdown("**🔍 Bottleneck Scan**"); rb(is_us,"US")
        st.markdown("**📋 Master Board**"); rm("us_longs","us_shorts","#3fb950","#f85149",is_us,"US")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(ul+us)),"US_STOCKS")

    with mt[1]:
        ih=tickers.get("ihsg_buys",[]); nm={"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe","UNVR.JK":"Unilever","INDF.JK":"Indofood"}
        st.markdown("**📍 NOW — LONG**"); rc(ih,nm,"long",3)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom")])
        rml([("ADRO.JK","Energy"),("BBCA.JK","Finance"),("UNVR.JK","Consumer"),("TLKM.JK","Infra"),("CTRA.JK","Property"),("ANTM.JK","Mining"),("KLBF.JK","Health"),("AALI.JK","Agri"),("ASII.JK","Industri")],"^JKSE","IDX Sector")
        st.markdown("**🔍 Bottleneck Scan**"); rb(is_ih,"IHSG")
        st.markdown("**📋 Master Board**"); rm("ihsg_buys",None,"#fb923c","#f85149",is_ih,"IHSG")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(ih,"IHSG")

    with mt[2]:
        fl=tickers.get("fx_longs",[]); fs=tickers.get("fx_shorts",[])
        nm={"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY","GBPUSD=X":"GBP/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","USDCHF=X":"USD/CHF","GLD":"Gold","AAAU":"Gold","YCS":"Short Yen"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG**"); rc(fl,nm,"long",2)
        with c2: st.markdown("**📍 NOW — SHORT**"); rc(fs,nm,"short",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("EURUSD=X","EUR/USD"),("USDJPY=X","USD/JPY"),("AUDUSD=X","AUD/USD"),("USDIDR=X","USD/IDR"),("UUP","DXY")])
        rml([("UUP","DXY"),("USDJPY=X","USD/JPY"),("EURUSD=X","EUR/USD"),("AUDUSD=X","AUD/USD"),("GBPUSD=X","GBP/USD"),("USDCAD=X","USD/CAD")],"UUP","FX Leadership")
        st.markdown("**🔍 Bottleneck Scan**"); rb(is_fx,"FX")
        st.markdown("**📋 Master Board**"); rm("fx_longs","fx_shorts","#58a6ff","#f85149",is_fx,"FX")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(fl+fs)),"FOREX")

    with mt[3]:
        cl=tickers.get("comm_longs",[]); cs=tickers.get("comm_shorts",[])
        nm={"SLV":"Silver","GDX":"Gold Miners","GC=F":"Gold Fut","SI=F":"Silver Fut","HG=F":"Copper Fut","CL=F":"WTI Oil","NG=F":"Nat Gas","XOP":"Oil Explorers","OIH":"Oil Services","BNO":"Brent Oil","GLD":"Gold","AAAU":"Gold","COAL":"Coal","DUST":"Gold Bear","BITS":"Bitcoin Strat"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG**"); rc(cl,nm,"long",2)
        with c2: st.markdown("**📍 NOW — SHORT**"); rc(cs,nm,"short",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("CL=F","WTI Oil"),("GC=F","Gold Fut"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas")])
        rml([("GC=F","Gold"),("CL=F","WTI Oil"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas"),("XBRUSD=X","Brent"),("URA","Uranium")],"GC=F","Commodity Leadership")
        st.markdown("**🔍 Bottleneck Scan**"); rb(is_cm,"Commodities")
        st.markdown("**📋 Master Board**"); rm("comm_longs","comm_shorts","#fb923c","#f85149",is_cm,"Commodities")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(cl+cs)),"COMMODITIES")

    with mt[4]:
        crl=tickers.get("crypto_longs",[]); crs=tickers.get("crypto_shorts",[])
        nm={"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP","IBIT":"Bitcoin ETF"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG**"); rc(crl,nm,"long",2)
        with c2: st.markdown("**📍 NOW — SHORT**"); rc(crs,nm,"short",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP")])
        rml([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP"),("ADA-USD","Cardano"),("DOT-USD","Polkadot")],"BTC-USD","Crypto Leadership")
        st.markdown("**🔍 Bottleneck Scan**"); rb(is_cr,"Crypto")
        st.markdown("**📋 Master Board**"); rm("crypto_longs","crypto_shorts","#a371f7","#f85149",is_cr,"Crypto")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(crl+crs)),"CRYPTO")
        st.divider(); st.markdown("**⛓️ On-Chain Alpha**")
        dk=st.secrets.get("DUNE_SIM_KEY",""); ek=st.secrets.get("ETHERSCAN_KEY",""); tk=st.secrets.get("TAOSTATS_KEY","")
        with st.expander("🔑 API Keys",expanded=False):
            c1,c2,c3=st.columns(3)
            with c1: dk=st.text_input("Dune",value=dk,type="password",key="dune")
            with c2: ek=st.text_input("Etherscan",value=ek,type="password",key="eth")
            with c3: tk=st.text_input("TAOStats",value=tk,type="password",key="tao")
        scanner=MCS(dk,ek,tk)
        with st.spinner("⛓️ Scanning chains... ⏳ ~30s"):
            df=scanner.scan({'base':{},'solana':{},'bittensor':{},'ethereum':{}})
        if not df.empty:
            for _,r in df.iterrows():
                sc=r['alpha']; co="#4ade80" if sc>=70 else "#fbbf24" if sc>=45 else "#f87171"; bg="#1a4d2e" if sc>=70 else "#5c3d00" if sc>=45 else "#5c1a1a"
                _h(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:10px;margin-bottom:8px;"><div style="display:flex;align-items:center;justify-content:space-between;"><div style="display:flex;align-items:center;gap:8px;"><div style="background:{bg};color:{co};padding:3px 10px;border-radius:16px;font-size:11px;font-weight:700;">{r["chain"].upper()}</div><div style="font-size:13px;font-weight:700;color:#e6edf3;">{r["verdict"]}</div></div><div style="font-size:18px;font-weight:800;color:{co};">{sc:.0f}<span style="font-size:10px;color:#8b949e;">/100</span></div></div><div style="display:flex;gap:12px;flex-wrap:wrap;font-size:10px;color:#c9d1d9;margin-top:6px;"><span>📊 Macro: <b>{r["macro"]}</b></span><span>📈 TVL: <b>{r["tvl"]:+.1f}%</b></span><span>💰 Stable: <b>{r["stb"]:+.1f}%</b></span><span>🌊 DEX: <b>{r["dex"]:.1f}x</b></span></div></div>')
        else: st.info("No on-chain data.")

# ─── TAB 2: REGIME DEEP DIVE ───
with tabs[2]:
    if st.toggle("Show raw regime JSON",False): st.json(q)
    md=q.get("monthly_debug",{})
    if md:
        with st.expander("🔍 Monthly Calculation Trace",expanded=False): st.json(md)
    st.markdown("**Structural Probabilities**")
    for k in ["Q1","Q2","Q3","Q4"]:
        p=1.0 if k==sq else 0.0; mp=1.0 if k==mq else 0.0
        label=f"{'●' if k==sq else '◉' if k==mq else '○'} {k}: S={p:.0%} M={mp:.0%}"
        st.progress(p,text=label)

# ─── TAB 3: RISK & DIAG ───
with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
    c1,c2,c3=st.columns(3)
    with c1: st.metric("FRED Loaded",f"{q.get('fred_loaded',0)}/{len(FRED_PARAMS)}")
    with c2: st.metric("Source",src)
    with c3: st.metric("API Key","✅" if q.get('fred_loaded',0)>0 else "❌")
    if q.get('fred_loaded',0)==0:
        st.error("🚨 FRED 0 loaded — using proxy data.")
        if st.button("🔄 Clear Cache & Reload"):
            st.cache_data.clear(); st.rerun()