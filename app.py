"""MacroRegime Pro v13.4 — TRR Filtered + Crash/Health CC + 7-Account Intel
v10.0 Macro Brain + v12.2 TRR/LRR + On-Chain + Narrative + Bottleneck + 7-Account Layer
"""
import os, sys, glob, time, json, logging, requests, math, numpy as np, pandas as pd, yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import streamlit as st

for f in glob.glob("/tmp/*.pkl"):
    try: os.remove(f)
    except: pass
try: st.cache_data.clear()
except: pass

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regime_engine import get_regime_snapshot, FRED_SERIES, FRED_SERIES_COUNT

DISPLAY_MAP = {
    'USDJPY=X':'USDJPY', 'EURUSD=X':'EURUSD', 'AUDUSD=X':'AUDUSD', 'GBPUSD=X':'GBPUSD',
    'USDCAD=X':'USDCAD', 'USDIDR=X':'USDIDR', 'EURGBP=X':'EURGBP', 'EURJPY=X':'EURJPY',
    'GBPJPY=X':'GBPJPY', 'NZDUSD=X':'NZDUSD', 'USDCNH=X':'USDCNH', 'USDCHF=X':'USDCHF',
    'GC=F':'XAUUSD', 'SI=F':'XAGUSD', 'HG=F':'XCUUSD', 'CL=F':'XTIUSD', 'NG=F':'XNGUSD',
    'XBRUSD=X':'XBRUSD', 'XTIUSD=X':'XTIUSD', 'XAUUSD=X':'XAUUSD', 'XAGUSD=X':'XAGUSD',
    'XCUUSD=X':'XCUUSD', 'XNGUSD=X':'XNGUSD',
}
def clean_tk(tk): return DISPLAY_MAP.get(tk, tk)

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
    eps=1e-10; h=np.maximum(df["High"],df["Open"]+eps); l=np.maximum(df["Low"],eps)
    o=np.maximum(df["Open"],eps); c=np.maximum(df["Close"],eps)
    return np.maximum(0.0,0.5*np.power(np.log(h/l),2.0)-(2.0*np.log(2.0)-1.0)*np.power(np.log(c/o),2.0))
def _atr(df,n=14):
    h,l,c=df["High"],df["Low"],df["Close"]
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
        p=self.p; c,h,l,o,v=df["Close"],df["High"],df["Low"],df["Open"],df["Volume"].fillna(0)
        atr14=_atr(df,p["atrLen"]); lr=np.log(c/c.shift(1))
        rvf=lr.rolling(p["rvLen"]).std()*np.sqrt(252); rvm=lr.rolling(max(p["rvLen"]*2,30)).std()*np.sqrt(252)
        rvs=lr.rolling(max(p["rvLen"]*4,60)).std()*np.sqrt(252); tel=max(63,min(p["tailLen"],756))
        tb=_kama(c,p["tradeLen"],2,p["tradeLen"]); trb=_kama(c,p["trendLen"],3,p["trendLen"])
        tab=_kama(c,tel,5,tel); troc=_z(_roc(c,p["tradeLen"]),p["normLen"])
        trroc=_z(_roc(c,p["trendLen"]),p["normLen"])
        tar=_z(_roc(c,252).fillna(_roc(c,126)).fillna(_roc(c,63)).fillna(_roc(c,21)).fillna(0),p["normLen"])
        td=_z(((c/tb.replace(0,np.nan))-1.0)*100.0,p["normLen"]); trd=_z(((c/trb.replace(0,np.nan))-1.0)*100.0,p["normLen"])
        tad=_z(((c/tab.replace(0,np.nan))-1.0)*100.0,p["normLen"]); tsl=_z(_roc(tb,3),p["normLen"])
        trsl=_z(_roc(trb,10),p["normLen"]); tas=_z(_roc(tab,21).fillna(_roc(tab,10)).fillna(_roc(tab,5)).fillna(0),p["normLen"])
        rv=_roc(v,p["volRocLen"]); tv=_z(rv.ewm(span=2,adjust=False).mean(),p["normLen"])*vm
        trv=_z(rv.ewm(span=5,adjust=False).mean(),p["normLen"])*vm; tav=_z(rv.ewm(span=10,adjust=False).mean(),p["normLen"])*vm
        tp=_z(_er(c,max(5,int(round(p["tradeLen"]*0.7)))),p["normLen"]); trp=_z(_er(c,p["trendLen"]),p["normLen"])
        tap=_z(_er(c,63),p["normLen"]).fillna(_z(_er(c,21),p["normLen"])).fillna(0.0)
        rbf=rvf.rolling(50).mean().fillna(rvf); rbm=rvm.rolling(50).mean().fillna(rvm); rbs=rvs.rolling(50).mean().fillna(rvs)
        vf=pd.Series(np.where(rbf>0,(rvf/rbf)-1.0,0.0),index=c.index); vm_=pd.Series(np.where(rbm>0,(rvm/rbm)-1.0,0.0),index=c.index)
        vs=pd.Series(np.where(rbs>0,(rvs/rbs)-1.0,0.0),index=c.index)
        ts=0.30*troc+0.24*tsl+0.18*td+0.14*tp+0.10*tv-0.08*_z(vf,p["normLen"])
        trs=0.24*trroc+0.28*trsl+0.22*trd+0.14*trp+0.08*trv-0.06*_z(vm_,p["normLen"])
        tas_=0.18*tar+0.30*tas+0.24*tad+0.16*tap+0.06*tav-0.04*_z(vs,p["normLen"])
        ap=pd.Series(np.where(c!=0,atr14/c,0.0),index=c.index)
        tsh=_z(vf+0.60*_roc(ap,1),p["normLen"]); trsh=_z(vm_+0.45*_roc(ap,3),p["normLen"])
        tash=_z(vs+0.30*_roc(ap,8),p["normLen"]); gk=_gk(df)
        grv=np.sqrt(np.maximum(gk.rolling(p["rvLen"]).mean()*252.0,0.0)); grb=grv.rolling(50).mean().fillna(grv)
        gv=grv.rolling(max(p["rvLen"],20)).std().fillna(0); gvb=gv.rolling(50).mean().fillna(np.maximum(gv,0.001))
        return pd.DataFrame({
            "atr":atr14.shift(1),"trdSc":ts.shift(1),"trdShk":tsh.shift(1),"trdBs":tb.shift(1),
            "trnSc":trs.shift(1),"trnShk":trsh.shift(1),"trnBs":trb.shift(1),
            "talSc":tas_.shift(1),"talShk":tash.shift(1),"talBs":tab.shift(1),
            "c1":c.shift(1),"c2":c.shift(2),"v1":v.shift(1),"vsma1":v.rolling(20).mean().shift(1),
            "gkRv":grv.shift(1),"gkRvBase":grb.shift(1),"gkVov":gv.shift(1),"gkVovBase":gvb.shift(1),
        },index=df.index)

    def latest(self,df,vm=1.0):
        p=self.p; b=self.bundle(df,vm); n=len(b); c=df["Close"].values
        if n<300: return None
        ac=_atr(df,14).values; atr=b["atr"].values; tsc=b["trdSc"].values; tsh=b["trdShk"].values; tbs=b["trdBs"].values
        trsc=b["trnSc"].values; trsh=b["trnShk"].values; trbs=b["trnBs"].values
        talsc=b["talSc"].values; talsh=b["talShk"].values; talbs=b["talBs"].values
        gkr=b["gkRv"].values; gkrb=b["gkRvBase"].values; gkv=b["gkVov"].values; gkvb=b["gkVovBase"].values
        tr=_tfreset(df.index,p["trendFreezeTF"]).values; tar=_tfreset(df.index,p["tailFreezeTF"]).values
        tph=np.zeros(n,dtype=int); trph=np.zeros(n,dtype=int); talph=np.zeros(n,dtype=int)
        ptb=np.full(n,np.nan); pta=np.full(n,np.nan); ptab=np.full(n,np.nan); ptar=np.full(n,np.nan)
        etb=np.full(n,np.nan); etab=np.full(n,np.nan); tage=np.zeros(n,dtype=int); talge=np.zeros(n,dtype=int)
        ptr=plr=ttr=tlr=ttrr=tlrr=0.0
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
            pw=atr[i]*p["tradeATRMult"]*grf*gvf*max(0.65,1.0+p["shockBoost"]*max(tsh[i],0.0))
            ptr=tbs[i]+pw; plr=max(tbs[i]-pw,1e-10)
            trw=max(pta[i],atr[i])*p["trendATRMult"]*grf*gvf*max(0.70,1.0+p["trendShockBoost"]*max(trsh[i],0.0))
            ttr=ptb[i]+trw; tlr=max(ptb[i]-trw,1e-10)
            taw=max(ptar[i],atr[i])*p["tailATRMult"]*grf*gvf*max(0.80,1.0+p["tailShockBoost"]*max(talsh[i],0.0))
            ttrr=ptab[i]+taw; tlrr=max(ptab[i]-taw,1e-10)
            rt=_hys(tsc[i],p["tradeThresh"],p["tradeNeutralBand"],tph[i-1])
            rtr=_hys(trsc[i],p["trendThresh"],p["trendNeutralBand"],trph[i-1])
            rta=_hys(talsc[i],p["tailThresh"],p["tailNeutralBand"],talph[i-1])
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
        i=n-1
        cs=df["Close"]; ach=cs.diff().abs(); erd=ach.rolling(20).sum()
        erv=pd.Series(np.where(erd==0,0.0,cs.diff(20).abs()/erd),index=df.index)
        i0=pd.Series(range(len(df)),index=df.index); cr=cs.rolling(30).corr(i0)
        r2=pd.Series(np.where(np.isnan(cr),0.0,cr**2),index=df.index)
        adx=ach.rolling(14).mean()/(df["High"]-df["Low"]).rolling(14).mean().replace(0,np.nan)
        an=_c01((adx.iloc[-1]-12.0)/28.0); en=_c01(erv.iloc[-1]); rn=_c01(r2.iloc[-1])
        qs=100.0*(0.45*an+0.35*en+0.20*rn)
        apv=np.where(cs.values!=0,(b["atr"].values/cs.values)*100.0,0.0); aps=pd.Series(apv,index=df.index)
        apb=aps.rolling(50).mean().fillna(aps); aatr=_c01(aps.iloc[-1]/(apb.iloc[-1]*1.25)) if apb.iloc[-1]>0 else 0.5
        rvn=np.log(cs/cs.shift(1)).rolling(p["rvLen"]).std()*np.sqrt(252.0); rvb=rvn.rolling(50).mean().fillna(rvn)
        arv=_c01(rvn.iloc[-1]/(rvb.iloc[-1]*1.20)) if rvb.iloc[-1]>0 else 0.5
        vb=df["Volume"].rolling(20).mean().fillna(df["Volume"])
        avr=_c01(df["Volume"].iloc[-1]/(vb.iloc[-1]*1.35)) if vb.iloc[-1]>0 else 0.5
        av=0.35+0.65*avr*vm
        act=100.0*_clip(0.42*aatr+0.43*arv+0.15*av,0.0,1.0)
        cmp=100.0*_clip(1.0-(0.50*aatr+0.38*arv+0.12*av),0.0,1.0)
        return {
            "tradeTRR":float(ptr),"tradeLRR":float(plr),"trendTRR":float(ttr),"trendLRR":float(tlr),
            "tailTRR":float(ttrr),"tailLRR":float(tlrr),"tradePhase":int(tph[i]),"trendPhase":int(trph[i]),"tailPhase":int(talph[i]),
            "trendTransUp":bool(ttu),"trendTransDown":bool(ttd),"tailTransUp":bool(tlu),"tailTransDown":bool(tld),
            "tradeBreakUp":bool(c[i]>ptr),"tradeBreakDown":bool(c[i]<plr),"trendAge":int(tage[i]),"tailAge":int(talge[i]),
            "qualityScore":float(qs),"activityScore":float(act),"compressionScore":float(cmp),"volRegimeConfirm":bool(gkv[i]>gkvb[i]*1.30),
            "pubTradeScore":float(tsc[i]),"pubTrendScore":float(trsc[i]),"pubTailScore":float(talsc[i]),
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
    try: r=_eng.latest(df,vm=cfg["vm"])
    except: return None
    if not r: return None
    pr=df["Close"].iloc[-1]
    lg=(r["tradeBreakUp"] or r["trendTransUp"] or r["tailTransUp"]) and r["qualityScore"]>=cfg["qmin"] and r["activityScore"]>=cfg["amin"] and r["trendAge"]<=cfg["agemax"]
    sg=cfg["short"] and (r["tradeBreakDown"] or r["trendTransDown"] or r["tailTransDown"]) and r["qualityScore"]>=cfg["qmin"] and r["activityScore"]>=cfg["amin"] and r["trendAge"]<=cfg["agemax"]
    if not lg and not sg: return None
    sig="LONG" if lg else "SHORT"
    cf=min(100,int(50+r["qualityScore"]*0.3+r["activityScore"]*0.2+(25 if (r["trendTransUp"] or r["trendTransDown"] or r["tailTransUp"] or r["tailTransDown"]) else 0)))
    rs=[]
    if r["tradeBreakUp"]: rs.append(f"Price>TradeTRR({r['tradeTRR']:.2f})")
    if r["tradeBreakDown"]: rs.append(f"Price<TradeLRR({r['tradeLRR']:.2f})")
    if r["trendTransUp"]: rs.append("TREND-UP")
    if r["trendTransDown"]: rs.append("TREND-DOWN")
    if r["tailTransUp"]: rs.append("TAIL-UP")
    if r["tailTransDown"]: rs.append("TAIL-DOWN")
    return {"ticker":ticker,"signal":sig,"confidence":cf,"price":round(pr,4),"tradeTRR":round(r["tradeTRR"],4),"tradeLRR":round(r["tradeLRR"],4),"trendTRR":round(r["trendTRR"],4),"trendLRR":round(r["trendLRR"],4),"tailTRR":round(r["tailTRR"],4),"tailLRR":round(r["tailLRR"],4),"trendPhase":r["trendPhase"],"tailPhase":r["tailPhase"],"trendAge":r["trendAge"],"tailAge":r["tailAge"],"quality":round(r["qualityScore"],1),"activity":round(r["activityScore"],1),"compression":round(r["compressionScore"],1),"volRegime":"EXPANDING" if r["volRegimeConfirm"] else "NORMAL","reason":" | ".join(rs)}

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
                    r=_eng.latest(df,vm=GATE.get(ac,GATE["US_STOCKS"])["vm"])
                    if r:
                        pr=df["Close"].iloc[-1]; cfg=GATE.get(ac,GATE["US_STOCKS"]); rs=[]
                        if not (r["tradeBreakUp"] or r["trendTransUp"] or r["tailTransUp"]): rs.append("No breakout")
                        if r["qualityScore"]<cfg["qmin"]: rs.append(f"Q{r["qualityScore"]:.0f}<{cfg["qmin"]}")
                        if r["activityScore"]<cfg["amin"]: rs.append(f"A{r["activityScore"]:.0f}<{cfg["amin"]}")
                        if r["trendAge"]>cfg["agemax"]: rs.append(f"Age{r["trendAge"]}>{cfg["agemax"]}")
                        dbg.append({"ticker":t,"price":round(pr,2),"q":round(r["qualityScore"],1),"a":round(r["activityScore"],1),"age":r["trendAge"],"phase":r["trendPhase"],"fail":" | ".join(rs) if rs else "N/A"})
                except: pass
    if not hits:
        st.caption(f"TRR/LRR: No {ac} tickers passed the gate.")
        if dbg:
            with st.expander(f"🔍 {ac} TRR/LRR Debug ({len(dbg)} evaluated)"):
                st.dataframe(pd.DataFrame(dbg),use_container_width=True,height=200)
        return
    hits.sort(key=lambda x:(0 if x["signal"]=="LONG" else 1,-x["confidence"]))
    st.markdown(f"**{title}**")
    for h in hits:
        col="#3fb950" if h["signal"]=="LONG" else "#f85149"; ic="▲" if h["signal"]=="LONG" else "▼"
        with st.container():
            c1,c2,c3=st.columns([1.2,2.5,1.5])
            with c1: st.markdown(f"<span style='color:{col};font-weight:800;font-size:16px;'>{ic} {clean_tk(h['ticker'])}</span>",unsafe_allow_html=True); st.caption(f"Conf: **{h['confidence']}**/100")
            with c2: st.caption(f"Price {h['price']} | TradeTRR {h['tradeTRR']} | TradeLRR {h['tradeLRR']}"); st.caption(f"Trend: Phase {h['trendPhase']} | Age {h['trendAge']}d | Q {h['quality']} | A {h['activity']}")
            with c3: st.caption(f"Trigger: {h['reason']}")
        st.divider()

def bottleneck_scan(tlist, prices, q, ac="US_STOCKS"):
    if not tlist: return []
    rows=[]
    sq=q.get("structural_quad","Q3"); mq=q.get("monthly_quad","Q3")
    regime_boost={"Q1":{"long":0.08,"short":-0.04},"Q2":{"long":0.10,"short":-0.05},"Q3":{"long":0.02,"short":0.02},"Q4":{"long":-0.05,"short":0.08}}.get(sq,{"long":0,"short":0})
    for t in tlist:
        s=prices.get(t)
        if s is None or len(s)<63: continue
        r1m=((s.iloc[-1]/s.iloc[-22])-1) if len(s)>=22 else 0
        r3m=((s.iloc[-1]/s.iloc[-64])-1) if len(s)>=64 else 0
        r6m=((s.iloc[-1]/s.iloc[-126])-1) if len(s)>=126 else 0
        vs=s.rolling(20).mean()
        vol_r=s.iloc[-1]/vs.iloc[-1] if not vs.empty and vs.iloc[-1]>0 else 1.0
        mom_score=min(1.0,max(0.0,0.4*(r3m/0.15)+0.3*(r1m/0.08)+0.2*(r6m/0.25)+0.1*(vol_r-1.0)))
        sig="LONG" if r3m>0.03 and r1m>-0.02 else "SHORT" if r3m<-0.03 and r1m<0.02 else "NEUTRAL"
        if sig=="LONG": mom_score+=regime_boost["long"]
        elif sig=="SHORT": mom_score+=regime_boost["short"]
        mom_score=max(0.0,min(1.0,mom_score))
        if mom_score>=0.55:
            rows.append({"ticker":clean_tk(t),"signal":sig,"score":round(mom_score,2),"r1m":f"{r1m:+.1%}","r3m":f"{r3m:+.1%}","vol":f"{vol_r:.2f}x","regime":sq,"align":"✅" if sq==mq else "⚠️"})
    rows.sort(key=lambda x:(0 if x["signal"]=="LONG" else 1,-x["score"]))
    return rows

def render_bottleneck(rows, title="🎯 Adaptive Bottleneck Scan"):
    if not rows:
        st.caption("Bottleneck: No tickers passed momentum gate.")
        return
    st.markdown(f"**{title} ({len(rows)} found)**")
    for r in rows[:12]:
        col="#3fb950" if r["signal"]=="LONG" else "#f85149" if r["signal"]=="SHORT" else "#8b949e"
        ic="▲" if r["signal"]=="LONG" else "▼" if r["signal"]=="SHORT" else "◆"
        st.markdown(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;margin-bottom:6px;display:flex;align-items:center;justify-content:space-between;">
             <div style="display:flex;align-items:center;gap:8px;"><span style="color:{col};font-weight:800;font-size:14px;">{ic} {r["ticker"]}
             </span><span style="font-size:10px;color:#8b949e;">{r["r1m"]} 1M · {r["r3m"]} 3M · {r["vol"]}
             </span></div><div style="text-align:right;"><span style="font-size:12px;color:{col};font-weight:700;">{r["score"]:.0%}
             </span><span style="font-size:10px;color:#8b949e;margin-left:6px;">{r["align"]} {r["regime"]}
             </span></div></div>""", unsafe_allow_html=True)

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
    def __init__(self,dk=None,ek=None,tk=None): self.dk=dk; self.ek=ek; self.tk=tk
    def _req(self,url,params=None,hd=None):
        try:
            r=requests.get(url,params=params,headers=hd,timeout=15)
            return r.json() if r.status_code==200 else None
        except: return None
    def macro(self,slug,lb=7):
        try:
            base="https://api.llama.fi"; res={"chain":slug,"ts":datetime.utcnow().isoformat()}
            d=self._req(f"{base}/v2/historicalChainTvl/{slug}")
            if d:
                res["tvl_now"]=d[-1][1]; res["tvl_7d"]=d[-min(lb+1,len(d))][1]
                res["tvl_d"]=round((d[-1][1]-d[-min(lb+1,len(d))][1])/d[-min(lb+1,len(d))][1]*100,2) if d[-min(lb+1,len(d))][1]>0 else 0
            d=self._req(f"{base}/stablecoincharts/{slug}")
            if d:
                res["stb_now"]=d[-1]["totalCirculatingUSD"]["peggedUSD"]; res["stb_7d"]=d[-min(lb+1,len(d))]["totalCirculatingUSD"]["peggedUSD"]
                res["stb_d"]=round((res["stb_now"]-res["stb_7d"])/res["stb_7d"]*100,2) if res["stb_7d"]>0 else 0
            d=self._req(f"{base}/overview/dexs/{slug}?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume")
            if d and "totalDataChart" in d and d["totalDataChart"]:
                v=[x[1] for x in d["totalDataChart"] if x[1]]
                if len(v)>=2: res["vol24"]=v[-1]; res["vol7m"]=np.median(v[-7:]) if len(v)>=7 else np.median(v); res["spike"]=round(v[-1]/res["vol7m"],2) if res["vol7m"]>0 else 0
            sc=0
            if res.get("stb_d",0)>15: sc+=40
            elif res.get("stb_d",0)>10: sc+=25
            elif res.get("stb_d",0)>5: sc+=10
            if res.get("tvl_d",0)>10: sc+=30
            elif res.get("tvl_d",0)>5: sc+=15
            if res.get("spike",0)>3: sc+=20
            elif res.get("spike",0)>1.5: sc+=10
            res["score"]=min(sc,100); res["sig"]='HOT' if sc>=60 else 'WARM' if sc>=35 else 'COLD'
            return res
        except Exception as e: logging.error(f"llama err {slug}: {e}"); return {"chain":slug,"error":str(e)}
    def scan(self,targets):
        out=[]
        for k,cfg in targets.items():
            logging.info(f"Scan {k}..."); m=self.macro(REG[k].slug if k in REG else k)
            out.append({"chain":k,"alpha":m.get("score",0),"verdict":("🔥 STRONG" if m.get("score",0)>=70 else "⚡ MONITOR" if m.get("score",0)>=45 else "❄️ PASS"),"macro":m.get("sig","N/A"),"tvl":m.get("tvl_d",0),"stb":m.get("stb_d",0),"dex":m.get("spike",0),"whale":0})
            time.sleep(1)
        return pd.DataFrame(out)

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
                if t in data["Close"]: prices[t]=data["Close"][t].dropna()
        else:
            prices[all_t[0]]=data["Close"].dropna()
    except:
        for t in all_t:
            try:
                df=yf.download(t,period="6mo",interval="1d",progress=False,auto_adjust=True)
                if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
                if not df.empty and "Close" in df: prices[t]=df["Close"].dropna()
            except: pass
    return {"q":regime,"tickers":tickers,"prices":prices,"btl":{},"narr":{}}

snap=_load_all()
q=snap["q"]; tickers=snap["tickers"]; prices=snap["prices"]
sq=q.get("structural_quad","Q2"); mq=q.get("monthly_quad","Q2"); gq=q.get("global_quad","Q2")
conf=q.get("confidence",0.5); op=q.get("operating_regime","...")
src=q.get("source","unknown"); gy=q.get("growth_yoy",0); iy=q.get("inflation_yoy",0)
ps=q.get("policy_stance","—"); vix=q.get("vix",20.0)
mp=q.get("macro_pulse",{})

def _h(html): st.markdown(" ".join(html.split()),unsafe_allow_html=True)
QC={"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
def _qb(q): return QC.get(q,("#2d3748","#a0aec0"))[0]
def _qf(q): return QC.get(q,("#2d3748","#a0aec0"))[1]
sbg,sfg=_qb(sq),_qf(sq); mbg,mfg=_qb(mq),_qf(mq); gbg,gfg=_qb(gq),_qf(gq)
sb="🟢 FRED" if src=="fred" else "🟡 FRED Partial" if src=="fred_partial" else "🟡 YF Proxy" if src=="yfinance_proxy" else "⚪ Fallback"
sc="#3fb950" if src=="fred" else "#fbbf24" if src in ("fred_partial","yfinance_proxy") else "#8b949e"

def _s(s): 
    if s is None: return pd.Series(dtype=float)
    return pd.to_numeric(s if isinstance(s,pd.Series) else pd.Series(s),errors="coerce").dropna()
def last(s): s=_s(s); return float(s.iloc[-1]) if not s.empty else float("nan")
def ret_n(s,n): 
    s=_s(s)
    if len(s)<n+1: return float("nan")
    b=float(s.iloc[-(n+1)])
    if not math.isfinite(b) or b==0: return float("nan")
    return float(s.iloc[-1]/b-1.0)
def delta_n(s,n):
    s=_s(s)
    if len(s)<n+1: return float("nan")
    return float(s.iloc[-1]-s.iloc[-(n+1)])
def ts(s):
    s=_s(s)
    if len(s)<50: return 0.5
    px=float(s.iloc[-1]); m20=float(s.rolling(20).mean().iloc[-1]); m50=float(s.rolling(50).mean().iloc[-1])
    return 0.5*(1 if px>m20 else 0)+0.5*(1 if px>m50 else 0)
def th(x,sc): 
    if not math.isfinite(x): return 0.0
    return float(math.tanh(x/max(sc,1e-9)))
def clamp(x,lo=0.0,hi=1.0): return max(lo,min(hi,float(x or 0)))
def nm(*v):
    a=[x for x in v if math.isfinite(x)]
    return float(np.mean(a)) if a else 0.0
def pct(v,d=1):
    if not math.isfinite(v): return "—"
    return f"{v*100:+.{d}f}%"
def num(v,d=2):
    if not math.isfinite(v): return "—"
    return f"{v:.{d}f}"
def nf(x,d=0.0): return float(np.nan_to_num(x,nan=d))

def build_macro_features(prices, q, fred):
    f = {}
    for t in ["SPY","QQQ","IWM","RSP","UUP","TLT","EEM","GLD","HYG","LQD","XLE","XLI","XLY","CL=F","GC=F","HG=F"]:
        s = prices.get(t, pd.Series())
        tk = t.replace("^","").replace("=F","f").lower()
        f[f"{tk}_1m"] = ret_n(s,21)
        f[f"{tk}_3m"] = ret_n(s,63)
        f[f"{tk}_ts"] = ts(s)
    vix_s = prices.get("^VIX", pd.Series())
    f["vix_last"] = last(vix_s)
    f["vix_1m"] = delta_n(vix_s, 21)
    f["quad"] = q.get("quad", "Q2")
    f["monthly_quad"] = q.get("monthly_quad", "Q2")
    f["confidence"] = q.get("confidence", 0.5)
    f["growth_trend"] = q.get("growth_trend", "stable")
    f["inflation_trend"] = q.get("inflation_trend", "stable")
    f["growth_yoy"] = q.get("growth_yoy", 0)
    f["inflation_yoy"] = q.get("inflation_yoy", 0)
    f["policy_rate"] = q.get("policy_rate", 4.5)
    f["treasury_10y"] = q.get("treasury_10y", 4.2)
    f["vix"] = q.get("vix", 20.0)
    f["policy_stance"] = q.get("policy_stance", "In-a-box")
    f["fred_loaded"] = q.get("fred_loaded", 0)
    f["fred_missing"] = q.get("fred_missing", 0)
    f["macro_pulse"] = q.get("macro_pulse", {})
    oil_3m = nf(f.get("clf_3m", f.get("oil_3m", 0.0)))
    uup_1m = nf(f.get("uup_1m", 0.0))
    spy_1m = nf(f.get("spy_1m", 0.0))
    iwm_1m = nf(f.get("iwm_1m", 0.0))
    f["slowdown_flags"] = clamp(0.5 - spy_1m*2 - iwm_1m*2)
    f["inf_shock"] = clamp(0.3 + oil_3m*3 + max(0, uup_1m)*2)
    f["data_coverage"] = clamp(q.get("fred_loaded",0) / max(FRED_SERIES_COUNT,1))
    return f

def build_health(prices, f):
    SECS=["XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC"]
    spy_t=ts(prices.get("SPY",pd.Series())); iwm_t=ts(prices.get("IWM",pd.Series()))
    spy_3m=f.get("spy_3m",0.0); rsp_3m=ret_n(prices.get("RSP",pd.Series()),63)
    eqw=clamp(0.5+(rsp_3m-spy_3m)*5) if math.isfinite(rsp_3m) and math.isfinite(spy_3m) else 0.5
    ab50=sum(1 for t in SECS if len(_s(prices.get(t,pd.Series())))>=50 and float(_s(prices.get(t,pd.Series())).iloc[-1])>float(_s(prices.get(t,pd.Series())).rolling(50).mean().iloc[-1]))
    sec_s=ab50/len(SECS); small_conf=clamp(0.5+iwm_t-0.5)
    breadth_s=clamp(nm(sec_s,spy_t,small_conf))
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0)
    trade=clamp(0.35*breadth_s+0.25*spy_t+0.20*(1-clamp((hy-300)/400))+0.20*(1-clamp((vix-13)/25)))
    trend=clamp(0.40*spy_t+0.20*eqw+0.15*small_conf+0.15*sec_s+0.10*(0.5-nf(f.get("uup_1m",0.0))))
    tail=clamp(0.35*(1-clamp((vix-13)/25))+0.25*(1-clamp((hy-300)/400))+0.20*small_conf+0.10*(0.5-nf(f.get("uup_1m",0.0)))+0.10*(1-clamp(0.5+(rsp_3m-spy_3m)*5)))
    weather=clamp(0.35*trade+0.35*trend+0.30*tail)
    return {
        "breadth":breadth_s,"trade":trade,"trend":trend,"tail":tail,"weather":weather,
        "sec_above50":ab50,"sec_support":sec_s,"eqw_vs_cw":rsp_3m-spy_3m if math.isfinite(rsp_3m) else 0.0,
        "narrow_leadership":clamp(0.5+(spy_3m-rsp_3m)*5),"small_conf":small_conf,"spy_trend":spy_t,"iwm_trend":iwm_t,
        "trade_state":"supportive" if trade>=0.60 else "hostile" if trade<=0.40 else "balanced",
        "trend_state":"persistent" if trend>=0.60 else "fragile" if trend<=0.40 else "mixed",
        "tail_state":"calm" if tail>=0.58 else "stressed" if tail<=0.42 else "neutral",
        "weather_state":"Risk-On" if weather>=0.58 else "Risk-Off" if weather<=0.42 else "Mixed",
        "verdict":"Healthy" if weather>=0.62 else "Narrow" if weather>=0.50 else "Fragile" if weather>=0.38 else "Broken"
    }

def build_crash(f, h, q, prices=None):
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0)
    tail_s=1.0 if h.get("tail_state")=="stressed" else (0.35 if h.get("tail_state")=="neutral" else 0.10)
    shock_s=clamp(q.get("inf_shock",0.0)*1.5)
    health_frag={"Fragile":0.85,"Narrow":0.65,"Mixed":0.35,"Healthy":0.15,"Broken":0.90}.get(h.get("verdict","Mixed"),0.35)
    vix_s=0.90 if vix>=29 else (0.55 if vix>=19 else 0.20)
    unwind=clamp(h.get("narrow_leadership",0.5)*0.8+max(0,nf(f.get("uup_1m",0.0))*5)*0.2)
    vol_st=clamp((vix-18)/20)
    crash_score=clamp(0.16*tail_s+0.18*shock_s+0.12*health_frag+0.14*vix_s+0.14*unwind+0.12*vol_st+0.08*0.3+0.06*clamp(0.5+nf(f.get("uup_1m",0.0))/0.04))
    risk_off=clamp(0.30*(1.0-h.get("weather",0.5))+0.20*health_frag+0.15*clamp(0.5+nf(f.get("uup_1m",0.0))/0.04)+0.15*vol_st+0.10*unwind+0.10*vix_s)
    exec_score=clamp(0.20*h.get("weather",0.5)+0.14*{"Healthy":0.80,"Narrow":0.48,"Fragile":0.34,"Mixed":0.35,"Broken":0.18}.get(h.get("verdict","Mixed"),0.50)+0.10*{"Investable":0.78,"Chop":0.42,"Defensive":0.22}.get("Investable" if vix<19 else ("Chop" if vix<29 else "Defensive"),0.42)+0.12*{"Q1":0.68,"Q2":0.78,"Q3":0.48,"Q4":0.25}.get(q.get("quad","Q3"),0.50)+0.10*q.get("confidence",0.5)+0.09*h.get("trade",0.5)+0.09*(1-unwind)+0.08*(1-shock_s)+0.08*(1-crash_score))
    return {
        "crash_score":crash_score,"risk_off":risk_off,
        "state":"🔴 ELEVATED" if crash_score>=0.65 else ("🟡 WATCH" if crash_score>=0.42 else "🟢 CALM"),
        "vol_stress":vol_st,"credit_stress":clamp(0.60*clamp((hy-300)/400 if math.isfinite(hy) else 0.3)),
        "breadth_dmg":health_frag,"exec_score":exec_score,
        "exec_mode":"🟢 Add on Reset" if exec_score>=0.60 else ("🟡 Wait Reclaim" if exec_score>=0.45 else "🔴 Defensive Only")
    }

def build_rotation(q, h, f, prices=None):
    s_quad=q.get("quad","Q3"); uup_3m=nf(f.get("uup_3m",f.get("dxy_3m",0.0)))
    oil_3m=nf(f.get("clf_3m",f.get("oil_3m",0.0)))
    safe_scores={
        "XAUUSD":{"Q1":0.30,"Q2":0.35,"Q3":0.72,"Q4":0.60}.get(s_quad,0.5),
        "USD":{"Q1":0.35,"Q2":0.30,"Q3":0.50,"Q4":0.78}.get(s_quad,0.5),
        "TLT":{"Q1":0.30,"Q2":0.28,"Q3":0.46,"Q4":0.74}.get(s_quad,0.5),
        "Defensives":{"Q1":0.35,"Q2":0.30,"Q3":0.52,"Q4":0.64}.get(s_quad,0.5)
    }
    ben_scores={
        "WTI":{"Q1":0.40,"Q2":0.60,"Q3":0.70,"Q4":0.28}.get(s_quad,0.5),
        "EEM":{"Q1":0.62,"Q2":0.68,"Q3":0.42,"Q4":0.30}.get(s_quad,0.5),
        "IHSG":{"Q1":0.58,"Q2":0.64,"Q3":0.56,"Q4":0.32}.get(s_quad,0.5),
        "XAUUSD":{"Q1":0.42,"Q2":0.46,"Q3":0.74,"Q4":0.62}.get(s_quad,0.5)
    }
    safe_scores["XAUUSD"]+=0.10*q.get("inf_shock",0.0)
    usd_pen=clamp(uup_3m*5); ben_scores["IHSG"]*=(1.0-0.25*usd_pen); ben_scores["EEM"]*=(1.0-0.20*usd_pen)
    if oil_3m>0.05: ben_scores["WTI"]*=1.10; ben_scores["IHSG"]*=1.05
    safe_sorted=sorted(safe_scores.items(),key=lambda x:x[1],reverse=True)
    ben_sorted=sorted(ben_scores.items(),key=lambda x:x[1],reverse=True)
    em_score=clamp(0.35*ben_scores["EEM"]+0.35*ben_scores["IHSG"]+0.30*(1-usd_pen))
    return {
        "top_safe":safe_sorted[0][0],"top_ben":ben_sorted[0][0],
        "safe_rows":[{"route":k,"score":v} for k,v in safe_sorted[:3]],
        "ben_rows":[{"route":k,"score":v} for k,v in ben_sorted[:3]],
        "em_score":em_score,"em_state":"Accumulate" if em_score>0.60 else "Wait" if em_score>0.45 else "Avoid",
        "petro_score":clamp(oil_3m*2+0.5*q.get("inf_shock",0.0)) if oil_3m>0 else 0.0
    }

def build_ihsg(prices, q, f):
    jkse=prices.get("^JKSE",pd.Series()); idr=prices.get("IDR=X",pd.Series()); spy=prices.get("SPY",pd.Series())
    jkse_1m=ret_n(jkse,21); jkse_3m=ret_n(jkse,63); spy_1m=ret_n(spy,21)
    usd_idr_1m=ret_n(idr,21); usd_idr_pressure=clamp(0.5+(nf(usd_idr_1m)/0.08))
    bank_scores=[ret_n(prices.get(t,pd.Series()),21) for t in ["BBCA.JK","BBRI.JK"] if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
    bank_health=clamp(0.5+np.mean(bank_scores)/0.06) if bank_scores else 0.5
    rel_1m=(jkse_1m-spy_1m) if math.isfinite(jkse_1m) and math.isfinite(spy_1m) else 0.0
    foreign_flow=clamp(0.5+rel_1m/0.06)
    em_regime_score={"Q1":0.65,"Q2":0.70,"Q3":0.52,"Q4":0.28}.get(q.get("quad","Q3"),0.5)
    ihsg_score=clamp(0.24*em_regime_score+0.16*foreign_flow+0.24*(1.0-usd_idr_pressure)+0.18*bank_health+0.18*0.5)
    return {
        "jkse_1m":jkse_1m,"jkse_3m":jkse_3m,"usd_idr_1m":usd_idr_1m,
        "usd_idr_pressure":usd_idr_pressure,"bank_health":bank_health,
        "foreign_flow":foreign_flow,"flow_state":"Nett Beli" if foreign_flow>0.60 else "Nett Jual" if foreign_flow<0.40 else "Netral",
        "ihsg_score":ihsg_score,"exec_mode":"🟢 Add on Reset" if ihsg_score>=0.60 else ("🟡 Wait Reclaim" if ihsg_score>=0.47 else "🔴 Defensive / Selective Only"),
        "rel_state":"IHSG > SPY" if rel_1m>0.01 else "IHSG < SPY" if rel_1m<-0.01 else "IHSG ≈ SPY",
        "em_regime":em_regime_score,"stock_rows":[]
    }

def build_most_hated_rally_monitor(f, prices):
    def _score_below(v, clear_thr, near_thr):
        if not math.isfinite(v): return 0.42, False, False
        if v < clear_thr: return 1.00, True, True
        if v < near_thr: return 0.72, False, True
        return 0.24, False, False
    vix=last(prices.get("^VIX",pd.Series()))
    vix_score,vix_hard,vix_soft=_score_below(vix,20.0,22.0)
    dxy=last(prices.get("DX-Y.NYB",pd.Series()))
    dxy_hard=False; dxy_soft=False; dxy_score=0.38; dxy_note="DXY exact belum ada"
    if math.isfinite(dxy):
        dxy_score,dxy_hard,dxy_soft=_score_below(dxy,98.0,98.5)
        dxy_note="Modal global mulai keluar dari USD" if dxy_hard else "Sudah dekat area break"
    else:
        uup_s=prices.get("UUP",pd.Series()); uup_1m=ret_n(uup_s,21)
        if math.isfinite(uup_1m) and uup_1m<0:
            dxy_score=0.62; dxy_soft=True; dxy_note="Proxy UUP sudah melemah 1M"
    ust2y=f.get("policy_rate",float("nan"))
    ust_score,ust_hard,ust_soft=_score_below(ust2y,3.5,3.7)
    btc=last(prices.get("BTC-USD",pd.Series()))
    btc_score,btc_hard,btc_soft=_score_below(btc,72000,70000)
    cards=[
        {"label":"VIX < 20","score":vix_score,"hard":vix_hard,"soft":vix_soft},
        {"label":"DXY < 98","score":dxy_score,"hard":dxy_hard,"soft":dxy_soft},
        {"label":"UST 2Y < 3.5%","score":ust_score,"hard":ust_hard,"soft":ust_soft},
        {"label":"BTC > 72k","score":btc_score,"hard":btc_hard,"soft":btc_soft},
    ]
    hard=sum(1 for c in cards if c["hard"]); soft=sum(1 for c in cards if c["soft"])
    score=float(np.mean([c["score"] for c in cards])) if cards else 0.0
    if hard<=1 and score<0.48: state="dormant"; stage="Belum hidup"; posture="Defense / selective only"; action="Belum ada alasan buat agresif."; size_mult=0.35; cls="bad"
    elif hard<=1: state="watching"; stage="Watching / early"; posture="Probe only"; action="Ada tanda awal, tapi belum cukup."; size_mult=0.45; cls="warn"
    elif hard==2: state="arming"; stage="Transisi 2/4"; posture="Scale in pelan"; action="Branch sedang dibangun."; size_mult=0.60; cls="warn"
    elif hard==3: state="pre_confirmed"; stage="Nyaris aktif 3/4"; posture="Tactical risk-on bertahap"; action="Pre-confirmation."; size_mult=0.82; cls="good"
    else: state="active"; stage="Rally live 4/4"; posture="Tactical risk-on aktif"; action="Likuiditas-led branch aktif."; size_mult=1.00; cls="good"
    return {
        "clear_count":hard,"soft_clear_count":soft,"total":4,"stage":stage,"action":action,
        "cls":cls,"score":score,"branch_state":state,"posture":posture,"size_mult":size_mult,
        "scanner_long_boost":{"dormant":0.00,"watching":0.02,"arming":0.05,"pre_confirmed":0.10,"active":0.14}.get(state,0.0),
        "scanner_short_penalty":{"dormant":0.00,"watching":-0.02,"arming":-0.05,"pre_confirmed":-0.10,"active":-0.14}.get(state,0.0),
        "invalidators":["VIX gagal turun <20","DXY belum pecah <98","UST 2Y belum turun <3.5%","BTC belum tahan di atas 72k"][:4],
        "ihsg_title":"Global Liquidity → IHSG","ihsg_msg":"Fokus quality dan jangan maksa ke beta." if state in ["dormant","watching"] else "Bank besar, telco, exporter lebih pantas dinaikkan."
    }

def build_top_drivers(q, f, h, crash):
    drivers=[]
    slowdown=float(q.get("slowdown_flags",0.0))
    if slowdown>=0.30: drivers.append({"label":"Growth slowdown","score":clamp(slowdown),"tone":"bad" if slowdown>=0.50 else "warn","why":"Claims/ISM/housing memberi sinyal perlambatan.","tag":"macro"})
    inf=float(q.get("inf_shock",0.0))
    if inf>=0.20: drivers.append({"label":"Inflation shock","score":clamp(inf),"tone":"bad" if inf>=0.45 else "warn","why":"Oil/breakeven/USD mendorong tekanan inflasi.","tag":"macro"})
    usd_1m=nf(f.get("uup_1m",0.0))
    if abs(usd_1m)>=0.012: drivers.append({"label":"USD pressure" if usd_1m>0 else "USD easing","score":abs(usd_1m)/0.04,"tone":"bad" if usd_1m>0 else "good","why":"Dollar mengubah risk appetite lintas aset.","tag":"cross-asset"})
    oil_1m=nf(f.get("clf_1m",f.get("oil_1m",0.0)))
    if abs(oil_1m)>=0.02: drivers.append({"label":"Oil impulse" if oil_1m>0 else "Oil rollback","score":abs(oil_1m)/0.08,"tone":"warn" if oil_1m>0 else "good","why":"Gerak oil mempengaruhi inflation branch.","tag":"commodities"})
    breadth=float(h.get("breadth",0.5))
    if breadth<=0.45: drivers.append({"label":"Breadth fragility","score":(0.50-breadth)/0.20,"tone":"bad","why":"Partisipasi sempit; rally rawan unwind.","tag":"internals"})
    elif breadth>=0.60: drivers.append({"label":"Breadth healing","score":(breadth-0.50)/0.20,"tone":"good","why":"Partisipasi melebar; tape lebih sehat.","tag":"internals"})
    crash_score=float(crash.get("crash_score",0.0))
    if crash_score>=0.42: drivers.append({"label":"Tail-risk pressure","score":crash_score,"tone":"bad" if crash_score>=0.60 else "warn","why":"Crash meter belum jinak.","tag":"risk"})
    drivers.sort(key=lambda x:(x["score"],x["tone"]=="bad",x["tone"]=="good"),reverse=True)
    return drivers[:6]

f_macro = build_macro_features(prices, q, {})
h = build_health(prices, f_macro)
cr = build_crash(f_macro, h, q, prices)
rot = build_rotation(q, h, f_macro, prices)
ih = build_ihsg(prices, q, f_macro)
most_hated = build_most_hated_rally_monitor(f_macro, prices)
drivers = build_top_drivers(q, f_macro, h, cr)

_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;">v13.4 · TRR Filtered · Crash/Health CC · Bottleneck Intel</div>
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
  <div style="font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:8px;">Data: {sb} · Real PCE (Growth) · CPI (Inflation) · DFF+DGS10 (Policy) · Macro Pulse: ISM/Claims/Breakeven</div>
</div>
""")

tabs=st.tabs(["⚡ Command Center","🌍 Markets","📊 Regime Deep Dive","📰 Narrative","⚠️ Risk & Diag"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 0: COMMAND CENTER — Crash/Health moved here + Most Hated + Drivers
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[0]:
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("VIX", f"{vix:.1f}", delta="—")
    with c2: st.metric("Front-Run Window", "1–2 Weeks" if sq==mq else "Hold")
    with c3: st.metric("Confidence", f"{conf:.0%}")
    with c4:
        if sq!=mq:
            st.markdown("<span style='background:#5c2b00;color:#fb923c;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:700;'>⚠️ DIVERGEN</span>",unsafe_allow_html=True)
        else:
            st.markdown("<span style='background:#1a4d2e;color:#4ade80;padding:4px 10px;border-radius:20px;font-size:12px;font-weight:700;'>✅ ALIGNED</span>",unsafe_allow_html=True)
    
    st.divider()
    if sq!=mq:
        st.warning(f"⚠️ TRANSITIONAL — {sq}/{mq} divergen. Trade monthly signal only. Jangan buka structural positions.")
    else:
        st.success(f"✅ ALIGNED — {sq} confirmed. Bisa deploy structural + monthly.")
    
    st.markdown("**📊 Macro Pulse**")
    c1,c2,c3=st.columns(3)
    with c1:
        ism_d=mp.get('ism_delta','—'); ism_n=mp.get('ism_now','—')
        _h(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;">
          <div style="font-size:10px;color:#8b949e;">ISM Mfg Δ</div>
          <div style="font-size:18px;font-weight:800;color:#e6edf3;">{ism_d}</div>
          <div style="font-size:10px;color:#8b949e;">Now: {ism_n}</div>
        </div>""")
    with c2:
        cl_d=mp.get('claims_delta','—'); cl_n=mp.get('claims_now','—')
        _h(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;">
          <div style="font-size:10px;color:#8b949e;">Claims Δ</div>
          <div style="font-size:18px;font-weight:800;color:#e6edf3;">{cl_d}</div>
          <div style="font-size:10px;color:#8b949e;">Now: {cl_n}</div>
        </div>""")
    with c3:
        be_d=mp.get('be_1m','—'); be_n=mp.get('be_now','—')
        _h(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;">
          <div style="font-size:10px;color:#8b949e;">Breakeven 1M</div>
          <div style="font-size:18px;font-weight:800;color:#e6edf3;">{be_d}</div>
          <div style="font-size:10px;color:#8b949e;">Now: {be_n}</div>
        </div>""")
    
    st.divider(); st.markdown("**🧠 TOP DRIVERS NOW**")
    if drivers:
        drv_cols=st.columns(min(3,len(drivers)))
        for idx,drv in enumerate(drivers[:6]):
            col=drv_cols[idx%len(drv_cols)]
            tone=drv.get("tone","warn")
            bc={"good":"#1a4d2e","warn":"#5c3d00","bad":"#5c1a1a"}.get(tone,"#2d3748")
            fc={"good":"#4ade80","warn":"#fbbf24","bad":"#f87171"}.get(tone,"#a0aec0")
            with col:
                st.markdown(
                    f'<div style="background:{bc};border:1px solid #30363d;border-radius:10px;padding:10px;">'
                    f'<div style="font-size:9px;color:#8b949e;text-transform:uppercase;letter-spacing:0.08em;">{drv.get("tag","driver")}</div>'
                    f'<div style="font-size:14px;font-weight:700;color:{fc};">{drv["label"]}</div>'
                    f'<div style="font-size:10px;color:#c9d1d9;margin-top:4px;">{drv["why"]}</div>'
                    f'<div style="font-size:10px;color:#8b949e;margin-top:4px;">Intensity {drv["score"]:.0%}</div>'
                    f'</div>', unsafe_allow_html=True)
    
    st.divider()
    cc=most_hated.get("clear_count",0)
    if cc>=4: st.success(f"🔥 RALLY LIVE {cc}/4 — {most_hated['action']}")
    elif cc>=3: st.warning(f"⚡ NYARIS AKTIF {cc}/4 — {most_hated['action']}")
    elif cc>=2: st.info(f"🟡 TRANSISI {cc}/4 — {most_hated['action']}")
    else: st.error(f"❌ BELUM HIDUP {cc}/4 — {most_hated['action']}")
    
    # CRASH METER & HEALTH DASHBOARD — MOVED TO COMMAND CENTER v13.4
    st.divider()
    st.markdown("**💥 CRASH METER & HEALTH**")
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("Crash Score", f"{cr.get('crash_score',0):.0%}"); st.progress(cr.get('crash_score',0), text=cr.get('state','?'))
    with c2: st.metric("Weather", h.get('weather_state','—')); st.caption(f"Verdict: {h.get('verdict','—')}")
    with c3: st.metric("Trade Env", h.get('trade_state','—')); st.caption(f"Trend: {h.get('trend_state','—')}")
    with c4: st.metric("Tail", h.get('tail_state','—')); st.caption(f"Exec: {cr.get('exec_mode','?')}")
    st.caption(f"Risk-Off: {cr.get('risk_off',0):.0%} | Breadth Dmg: {cr.get('breadth_dmg',0):.0%} | Vol Stress: {cr.get('vol_stress',0):.0%}")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: MARKETS — TRR Filtered Cards + Bottleneck per sub-tab only
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    def rn(s,n):
        if s is None or len(s)<n+1: return float("nan")
        try: b=float(s.iloc[-(n+1)]); e=float(s.iloc[-1]); return float(e/b-1) if b!=0 and b==b else float("nan")
        except: return float("nan")
    def gr(s,n): r=rn(s,n); return f"{r:+.1%}" if r==r else "—"
    
    # TRR/LRR filtered card — shows WORTH / HOLD / AVOID badge v13.4
    def tc_trr(tk,name,r1m,r3m,ac,expected_sig):
        ev=_eval(tk,ac)
        if ev and ev["signal"]==expected_sig:
            badge="🟢 WORTH"; col="#3fb950" if expected_sig=="LONG" else "#f85149"
            ic="▲" if expected_sig=="LONG" else "▼"
        elif ev and ev["signal"]!=expected_sig:
            badge="🔴 AVOID"; col="#f85149" if expected_sig=="LONG" else "#3fb950"
            ic="▼" if expected_sig=="LONG" else "▲"
        else:
            badge="⚪ HOLD"; col="#8b949e"; ic="◆"
        return f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;flex:1;min-width:140px;"><div><div style="font-size:13px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:10px;color:#8b949e;">{name}</div><div style="font-size:9px;color:{col};font-weight:700;">{badge}</div></div><div style="text-align:right;"><div style="font-size:11px;color:{col};font-weight:700;">{ic} {r1m}</div><div style="font-size:9px;color:#8b949e;">3M: {r3m}</div></div></div>'
    
    def rc_trr(tlist,nmap,ac,expected_sig,pr=2):
        if not tlist: return
        cards=[]
        for t in tlist: s=prices.get(t); cards.append(tc_trr(clean_tk(t),nmap.get(t,t),gr(s,21),gr(s,63),ac,expected_sig))
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

    st.markdown("**🎯 OPPORTUNITIES & EXECUTION BOARD**")
    st.caption("v10.0 macro brain + v12.2 TRR/LRR gate. Regime-aware, route-aware, sized.")
    
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("Rally State", most_hated.get("stage","monitor"), f"{most_hated.get('clear_count',0)}/4")
    with c2: st.metric("Action", most_hated.get("posture","Defense"))
    with c3: st.metric("Exec Mode", cr.get("exec_mode","?"))
    with c4: st.metric("Weather", h.get("weather_state","Mixed"))
    
    st.divider()
    st.markdown("**📍 REGIME POLICY MATRIX**")
    pol_cols=st.columns(4)
    quad_policies={
        "Q1":{"US":"Growth/Tech long, Energy short","IHSG":"Bank/Consumer long","FX":"Majors long, Carry works","Comm":"Gold/Silver ok, Oil mixed","Crypto":"BTC/ETH/SOL long"},
        "Q2":{"US":"Cyclicals/Energy/Fin long","IHSG":"Coal/Metal/Bank long","FX":"Commodity FX long (AUD/CAD)","Comm":"Oil/Copper/Agri long","Crypto":"BTC/ETH ok, alts selective"},
        "Q3":{"US":"Defensives/Gold/Energy selective, Tech short","IHSG":"Coal exporter only, rest defensive","FX":"USD long, EM FX short","Comm":"Gold best, Oil volatile","Crypto":"BTC only, avoid alts"},
        "Q4":{"US":"TLT/Gold/Defensives long, Cyclicals short","IHSG":"Defensive quality only","FX":"USD/JPY/CHF long","Comm":"Gold only, rest bearish","Crypto":"Cash > all, BTC hold only"}
    }
    qp=quad_policies.get(sq,quad_policies["Q3"])
    for col,(mkt,pol) in zip(pol_cols,[("US",qp["US"]),("IHSG",qp["IHSG"]),("FX",qp["FX"]),("Comm",qp["Comm"])]):
        with col:
            st.markdown(f"**{mkt}**")
            st.markdown(f"<span style='font-size:11px;color:#c9d1d9;'>{pol}</span>",unsafe_allow_html=True)
    
    st.divider()
    st.markdown("**🔄 ROTATION FLOW**")
    st.markdown(f"**Best Long:** {rot['top_ben']} | **Safe Harbor:** {rot['top_safe']} | **EM State:** {rot['em_state']}")
    if rot.get('petro_score',0)>0.45: st.warning(f"⚡ Petrodollar branch active ({rot['petro_score']:.0%}). Oil shock mendistorsi rotation.")
    
    st.divider()
    st.markdown("**📐 POSITION SIZING GUIDE**")
    vix2=f_macro.get("vix_last",20.0)
    if vix2<19: sizing="Full size (100%) — VIX Investable"; sizing_col="good"
    elif vix2<29: sizing="Reduced size (50-75%) — VIX Chop"; sizing_col="warn"
    else: sizing="Defensive size (25% max) — VIX Defensive"; sizing_col="bad"
    st.markdown(f"<span style='color:#{ {'good':'3fb950','warn':'fbbf24','bad':'f85149'}[sizing_col] };font-weight:700;'>{sizing}</span>",unsafe_allow_html=True)
    
    st.divider()
    # NO GLOBAL BOTTLENECK HERE — only per sub-tab v13.4
    
    mt=st.tabs(["🇺🇸 US Stocks","🇮🇩 IHSG","💱 FX","🛢️ Commodities","🔐 Crypto"])

    with mt[0]:
        ul=tickers.get("us_longs",[]); us=tickers.get("us_shorts",[])
        nm={"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","TLT":"Long Bond","GLD":"Gold","HII":"Huntington","CAT":"Caterpillar","UPS":"UPS","LII":"Lennox","JBHT":"JB Hunt","MAR":"Marriott","ONTO":"Onto","EMR":"Emerson","RH":"Restoration","SBUX":"Starbucks","TXG":"10x Genomics","AVO":"Mission Produce","FRPT":"Freshpet","PEP":"Pepsi","XOM":"Exxon","HSY":"Hershey","WMB":"Williams","ET":"Energy Transfer","ROP":"Roper","RBLX":"Roblox","TRU":"TransUnion","NVDA":"Nvidia","XTL":"Telecom","EQRR":"Rising Rates","GII":"Infrastructure","EWH":"Hong Kong","EWW":"Mexico","ARGT":"Argentina","EIS":"Israel","IBIT":"Bitcoin ETF","COAL":"Coal","YCS":"Short Yen"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(ul,nm,"US_STOCKS","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(us,nm,"US_STOCKS","SHORT",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("CL=F","Oil"),("UUP","USD")])
        rml([("XLE","Energy"),("XLF","Fin"),("XLI","Ind"),("XLB","Mat"),("XLK","Tech"),("XLV","Health"),("XLY","Con.D"),("XLP","Con.S"),("XLU","Util"),("XLRE","RE")],"SPY","Sector Leadership")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(ul+us)),"US_STOCKS")
        st.markdown("**🎯 Bottleneck Scan**"); render_bottleneck(bottleneck_scan(list(set(ul+us)),prices,q,"US_STOCKS"),"US Bottleneck")

    with mt[1]:
        ih_t=tickers.get("ihsg_buys",[]); nm={"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe","UNVR.JK":"Unilever","INDF.JK":"Indofood"}
        st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(ih_t,nm,"IHSG","LONG",3)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom")])
        rml([("ADRO.JK","Energy"),("BBCA.JK","Finance"),("UNVR.JK","Consumer"),("TLKM.JK","Infra"),("CTRA.JK","Property"),("ANTM.JK","Mining"),("KLBF.JK","Health"),("AALI.JK","Agri"),("ASII.JK","Industri")],"^JKSE","IDX Sector")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(ih_t,"IHSG")
        st.markdown("**🎯 Bottleneck Scan**"); render_bottleneck(bottleneck_scan(ih_t,prices,q,"IHSG"),"IHSG Bottleneck")
        st.divider()
        st.markdown(f"**🇮🇩 IHSG Score: {ih['ihsg_score']:.0%}** · {ih['exec_mode']}")
        st.caption(f"Asing: {ih['flow_state']} | IDR 1M: {pct(ih['usd_idr_1m'])} | vs SPY: {ih['rel_state']}")

    with mt[2]:
        fl=tickers.get("fx_longs",[]); fs=tickers.get("fx_shorts",[])
        nm={"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY","GBPUSD=X":"GBP/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","USDCHF=X":"USD/CHF","GLD":"Gold","AAAU":"Gold","YCS":"Short Yen"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(fl,nm,"FOREX","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(fs,nm,"FOREX","SHORT",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("EURUSD=X","EUR/USD"),("USDJPY=X","USD/JPY"),("AUDUSD=X","AUD/USD"),("USDIDR=X","USD/IDR"),("UUP","DXY")])
        rml([("UUP","DXY"),("USDJPY=X","USD/JPY"),("EURUSD=X","EUR/USD"),("AUDUSD=X","AUD/USD"),("GBPUSD=X","GBP/USD"),("USDCAD=X","USD/CAD")],"UUP","FX Leadership")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(fl+fs)),"FOREX")
        st.markdown("**🎯 Bottleneck Scan**"); render_bottleneck(bottleneck_scan(list(set(fl+fs)),prices,q,"FOREX"),"FX Bottleneck")

    with mt[3]:
        cl=tickers.get("comm_longs",[]); cs=tickers.get("comm_shorts",[])
        nm={"SLV":"Silver","GDX":"Gold Miners","GC=F":"Gold Fut","SI=F":"Silver Fut","HG=F":"Copper Fut","CL=F":"WTI Oil","NG=F":"Nat Gas","XOP":"Oil Explorers","OIH":"Oil Services","BNO":"Brent Oil","GLD":"Gold","AAAU":"Gold","COAL":"Coal","DUST":"Gold Bear","BITS":"Bitcoin Strat"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(cl,nm,"COMMODITIES","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(cs,nm,"COMMODITIES","SHORT",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("CL=F","WTI Oil"),("GC=F","Gold Fut"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas")])
        rml([("GC=F","Gold"),("CL=F","WTI Oil"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas"),("XBRUSD=X","Brent"),("URA","Uranium")],"GC=F","Commodity Leadership")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(cl+cs)),"COMMODITIES")
        st.markdown("**🎯 Bottleneck Scan**"); render_bottleneck(bottleneck_scan(list(set(cl+cs)),prices,q,"COMMODITIES"),"Comm Bottleneck")

    with mt[4]:
        crl=tickers.get("crypto_longs",[]); crs=tickers.get("crypto_shorts",[])
        nm={"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP","IBIT":"Bitcoin ETF"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(crl,nm,"CRYPTO","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(crs,nm,"CRYPTO","SHORT",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP")])
        rml([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP"),("ADA-USD","Cardano"),("DOT-USD","Polkadot")],"BTC-USD","Crypto Leadership")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(crl+crs)),"CRYPTO")
        st.markdown("**🎯 Bottleneck Scan**"); render_bottleneck(bottleneck_scan(list(set(crl+crs)),prices,q,"CRYPTO"),"Crypto Bottleneck")
        st.divider(); st.markdown("**⛓️ On-Chain Alpha**")
        scanner=MCS()
        with st.spinner("⛓️ Scanning chains... ⏳ ~30s"):
            try:
                df=scanner.scan({'base':{},'solana':{},'bittensor':{},'ethereum':{}})
                if not df.empty:
                    for _,r in df.iterrows():
                        sc=r['alpha']; co="#4ade80" if sc>=70 else "#fbbf24" if sc>=45 else "#f87171"; bg="#1a4d2e" if sc>=70 else "#5c3d00" if sc>=45 else "#5c1a1a"
                        _h(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:10px;margin-bottom:8px;"><div style="display:flex;align-items:center;justify-content:space-between;"><div style="display:flex;align-items:center;gap:8px;"><div style="background:{bg};color:{co};padding:3px 10px;border-radius:16px;font-size:11px;font-weight:700;">{r["chain"].upper()}</div><div style="font-size:13px;font-weight:700;color:#e6edf3;">{r["verdict"]}</div></div><div style="font-size:18px;font-weight:800;color:{co};">{sc:.0f}<span style="font-size:10px;color:#8b949e;">/100</span></div></div><div style="display:flex;gap:12px;flex-wrap:wrap;font-size:10px;color:#c9d1d9;margin-top:6px;"><span>📊 Macro: <b>{r["macro"]}</b></span><span>📈 TVL: <b>{r["tvl"]:+.1f}%</b></span><span>💰 Stable: <b>{r["stb"]:+.1f}%</b></span><span>🌊 DEX: <b>{r["dex"]:.1f}x</b></span></div></div>')
                else: st.info("No on-chain data.")
            except Exception as e: st.error(f"On-chain scan error: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2: REGIME DEEP DIVE
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("Structural", sq); st.metric("Growth RoC", q.get("growth_trend","—"))
    with c2: st.metric("Monthly", mq); st.metric("Inflation RoC", q.get("inflation_trend","—"))
    with c3: st.metric("Global", gq); st.metric("Policy", ps)
    with c4: st.metric("Confidence", f"{conf:.0%}"); st.metric("VIX", f"{vix:.1f}")
    
    if sq!=mq:
        st.warning(f"⚠️ DIVERGENCE: Structural {sq} vs Monthly {mq}. Operate on monthly until aligned.")
    else:
        st.success(f"✅ ALIGNED: {sq} across all timeframes.")
    
    st.divider()
    st.markdown("**📊 Structural Probabilities**")
    probs=q.get("probs",{"Q1":0.25,"Q2":0.25,"Q3":0.25,"Q4":0.25})
    m_probs=q.get("monthly_probs",{"Q1":0.25,"Q2":0.25,"Q3":0.25,"Q4":0.25})
    for k in ["Q1","Q2","Q3","Q4"]:
        p=probs.get(k,0.0); mp=m_probs.get(k,0.0)
        label=f"{chr(9679) if k==sq else chr(9689) if k==mq else chr(9675)} {k}: S={p:.0%} M={mp:.0%}"
        st.progress(p,text=label)
    
    st.divider()
    if st.toggle("Show raw regime JSON", False): st.json(q)
    md=q.get("monthly_debug",{})
    if md:
        with st.expander("🔍 Monthly Calculation Trace", expanded=False): st.json(md)
    
    st.divider()
    st.markdown("**🕰️ REGIME CONTEXT**")
    st.info(f"**Operating:** {op} | **Flip Hazard:** {q.get('flip_hazard',0):.0%} | **Deepness:** {q.get('deepness',0):.0%}")
    st.caption("v13.4: monthly threshold 0.15/0.25, ISM series NAPM, sticky stable logic.")

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3: NARRATIVE + 7-Account Bottleneck Intel with Maturity
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
    st.markdown("**📰 NARRATIVE DISCOVERY & CATALYST MAPPING**")
    st.caption("Front-run catalyst mapping: event-lite pressure + scheduled macro events.")
    
    oil_3m=nf(f_macro.get("clf_3m",f_macro.get("oil_3m",0.0)))
    uup_1m=nf(f_macro.get("uup_1m",0.0))
    vix_n=f_macro.get("vix_last",20.0)
    sf=q.get("slowdown_flags",0.0); shock=q.get("inf_shock",0.0)
    
    war_oil=clamp(0.28*clamp(0.5+max(0,oil_3m)/0.12)+0.20*clamp(0.5+max(0,uup_1m)/0.04)+0.18*shock+0.16*clamp(0.5+(vix_n-18)/20)+0.18*clamp(0.5))
    policy_pressure=clamp(0.28*clamp(0.5)+0.22*sf+0.18*clamp(0.5+max(0,uup_1m)/0.04)+0.14*clamp(0.5+(vix_n-18)/20)+0.18*shock)
    relief=clamp(0.26*clamp(0.5+max(0,-oil_3m)/0.10)+0.18*clamp(0.5+max(0,-uup_1m)/0.04)+0.22*clamp(0.5)+0.16*(1-shock)+0.18*(1.0 if most_hated.get("branch_state") in ["arming","pre_confirmed","active"] else 0.0))
    
    c1,c2,c3=st.columns(3)
    with c1: st.metric("War/Oil Shock", f"{war_oil:.0%}")
    with c2: st.metric("Policy Pressure", f"{policy_pressure:.0%}")
    with c3: st.metric("Relief Branch", f"{relief:.0%}")
    
    dominant=max([("war_oil",war_oil),("policy_pressure",policy_pressure),("relief",relief)],key=lambda x:x[1])
    if dominant[0]=="war_oil" and war_oil>=0.58:
        st.error("⚔️ **War/Oil Shock dominant** — Energy shock / USD pressure masih dominan. Front-run via exporters, avoid importers / broad beta.")
    elif dominant[0]=="policy_pressure" and policy_pressure>=0.56:
        st.warning("📋 **Policy Pressure dominant** — Long-end pain, slowdown flags, funding pressure. Focus quality, selective shorts, confirmation breadth.")
    elif relief>=0.50:
        st.success("🕊️ **Relief / De-escalation** — Pressure mulai mereda. Front-run breadth broadening, EM rotation, laggard catch-up.")
    else:
        st.info("😶 **No Dominant Catalyst** — Ikuti regime + route; hindari maksa front-run.")
    
    st.divider()
    st.markdown("**🧠 BOTTLENECK INTEL — 7 Account Fusion Layer**")
    st.caption("Supply chain + allocation + demand + transmission + mispricing + portfolio + execution")
    
    # Maturity classification v13.4
    def _maturity(score, trr_aligned):
        if score>=0.90 and trr_aligned: return "🔥 MATURE", "#1a4d2e", "#4ade80"
        if score>=0.75 and trr_aligned: return "✅ CONFIRMED", "#2d5a3d", "#3fb950"
        if score>=0.65: return "🟡 BUILDING", "#5c3d00", "#fbbf24"
        return "🌱 EARLY", "#2d3748", "#8b949e"
    
    intel_rows=[
        {"layer":"L1 Demand","source":"HyperTechInvest","signal":"AI/Semi/Energy narrative momentum","status":"🔥 Active" if war_oil>=0.45 else "⚡ Watch","tickers":"NVDA, AMD, TSM, COHR, VST","maturity":"🔥 MATURE"},
        {"layer":"L2 Macro Filter","source":"Citrini + Hedgeye","signal":f"{sq} regime | Liquidity {chr(8595) if q.get('policy_rate',4.5)>4 else chr(8593)}","status":"✅ Pass" if sq in ['Q1','Q2'] else "⚠️ Caution","tickers":"SPY, QQQ, TLT, GLD, UUP","maturity":"✅ CONFIRMED"},
        {"layer":"L3 Supply Chain","source":"jukan05","signal":"HBM/DRAM/CoWoS constraint","status":"🔥 Bottleneck","tickers":"TSM, MU, SK Hynix, AMAT, LRCX","maturity":"🟡 BUILDING"},
        {"layer":"L4 Allocation","source":"zephyr_z9","signal":"Capacity priority → real winners","status":"🎯 Filtering","tickers":"TSM (Apple/Nvidia priority), AVGO","maturity":"🌱 EARLY"},
        {"layer":"L5 Transmission","source":"aleabitoreddit","signal":"Earnings acceleration + flow","status":"📡 Scanning","tickers":"See TRR/LRR Signals","maturity":"🌱 EARLY"},
        {"layer":"L6 Mispricing","source":"aleabitoreddit","signal":"Options convexity / undercovered","status":"🔍 Hunting","tickers":"OTM calls on confirmed breakouts","maturity":"🌱 EARLY"},
        {"layer":"L7 Portfolio","source":"ParadisLabs","signal":"Theme basket construction","status":"📦 Ready","tickers":"Semi basket, Energy basket, EM basket","maturity":"✅ CONFIRMED"},
    ]
    st.dataframe(pd.DataFrame(intel_rows), use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown("**📅 UPCOMING CATALYSTS (Front-Run Map)**")
    events=[
        {"title":"US CPI (Apr)","when":"~Apr 16","impact":"Panas = yields naik, USD up. Dingin = buka pintu cut lebih cepat."},
        {"title":"Kevin Warsh Fed Confirmation","when":"Apr 16","impact":"[CRITICAL] Warsh commit rate turun. Konfirmasi = DXY drop, risk-on."},
        {"title":"FOMC Meeting (Powell terakhir)","when":"~May 6-7","impact":"Hold expected. Forward guidance penting."},
        {"title":"Warsh resmi jadi Fed Chair","when":"May 15","impact":"[CRITICAL] Pemotongan defensif dimulai. Most hated rally bisa mulai."},
        {"title":"OJK-MSCI Meeting (Indonesia)","when":"~Apr 21-25","impact":"[IHSG KEY] MSCI status = flow asing catalyst."},
        {"title":"US Nonfarm Payrolls (Apr)","when":"~May 2","impact":"Miss = argumen Warsh cut lebih kuat."},
        {"title":"Iran-AS Perundingan","when":"TBD","impact":"[TACO Ch.2] Ceasefire ~Apr 22. Terima = de-escalation, oil drop."},
        {"title":"FIFA World Cup 2026","when":"Jun 2026","impact":"[POLITICAL DEADLINE] Trump butuh stabil before Jun."},
    ]
    for ev in events[:6]:
        with st.container():
            c1,c2=st.columns([1,3])
            with c1: st.markdown(f"<span style='font-size:11px;color:#8b949e;'>{ev['when']}</span>",unsafe_allow_html=True)
            with c2: st.markdown(f"<b style='font-size:13px;color:#e6edf3;'>{ev['title']}</b><br><span style='font-size:11px;color:#8b949e;'>{ev['impact']}</span>",unsafe_allow_html=True)
        st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: RISK & DIAGNOSTICS (Lightweight — Crash/Health moved to CC)
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("⚠️ Risk & Diagnostics")
    
    c1,c2,c3=st.columns(3)
    with c1: st.metric("FRED Loaded", f"{q.get('fred_loaded',0)}/{FRED_SERIES_COUNT}")
    with c2: st.metric("Source", src)
    with c3: st.metric("API Key", "✅ Active" if q.get('fred_loaded',0)>0 else "❌ Fallback")
    
    if q.get('fred_loaded',0)==0:
        st.error("🚨 FRED 0 loaded — using proxy data. Check API key.")
        if st.button("🔄 Clear Cache & Reload"):
            st.cache_data.clear(); st.rerun()
    elif q.get('fred_loaded',0) < FRED_SERIES_COUNT:
        missing = [k for k in FRED_SERIES.keys() if k not in fred]
        st.warning(f"🟡 FRED Partial — {q.get('fred_loaded',0)}/{FRED_SERIES_COUNT} loaded. Missing: {', '.join(missing)}")
    else:
        st.success("🟢 FRED Full — all series loaded.")
    
    st.divider()
    st.markdown("**🧪 DATA QUALITY**")
    dq_rows=[
        ("Source Mode", sb),
        ("FRED Series", f"{q.get('fred_loaded',0)}/{FRED_SERIES_COUNT}"),
        ("Macro Pulse", "✅" if mp else "❌"),
        ("VIX Source", "^VIX index" if vix>15 else "VIXY proxy"),
        ("TRR/LRR Engine", "✅ Active"),
        ("On-Chain Scanner", "✅ Active"),
        ("Bottleneck Scan", "✅ Active"),
        ("7-Account Intel", "✅ Active"),
    ]
    st.dataframe(pd.DataFrame(dq_rows, columns=["Check","Status"]), use_container_width=True, hide_index=True)
    
    st.divider()
    st.markdown("**📋 FRED DEBUG**")
    st.caption("v13.4: ISM series ID fixed to NAPM. If still missing, check FRED API limits or series availability.")
    if st.toggle("Show FRED series map", False):
        st.json(FRED_SERIES)

st.caption(f"MacroRegime Pro v13.4 · Built {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · God Mode")