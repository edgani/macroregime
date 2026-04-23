"""
MacroRegime Pro v15.2c — Pure Data-Driven, Bottleneck Intel Only, Differentiated Markets
"""
import os, sys, glob, time, json, logging, math, numpy as np, pandas as pd, yfinance as yf
from datetime import datetime, timezone
from typing import Dict, List
import streamlit as st

for f in glob.glob("/tmp/*.pkl"):
    try: os.remove(f)
    except: pass
try: st.cache_data.clear()
except: pass

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from regime_engine import get_regime_snapshot, FRED_SERIES, FRED_SERIES_COUNT, PRIMARY_SERIES

SCANNER_AVAILABLE = False
btl_result = None
SCANNER_TICKERS = set()
try:
    from bottleneck_engine import UnifiedBottleneckScanner, SupplyChainGraph, SupplyNode, load_config
    SCANNER_AVAILABLE = True
    _cfg = load_config()
    SCANNER_TICKERS = set(_cfg.get("nodes", {}).keys())
except Exception as e:
    st.warning(f"Bottleneck engine not loaded: {e}")

DISPLAY_MAP = {
    'USDJPY=X':'USDJPY', 'EURUSD=X':'EURUSD', 'AUDUSD=X':'AUDUSD', 'GBPUSD=X':'GBPUSD',
    'USDCAD=X':'USDCAD', 'USDIDR=X':'USDIDR', 'EURGBP=X':'EURGBP', 'EURJPY=X':'EURJPY',
    'GBPJPY=X':'GBPJPY', 'NZDUSD=X':'NZDUSD', 'USDCNH=X':'USDCNH', 'USDCHF=X':'USDCHF',
    'GC=F':'XAUUSD', 'SI=F':'XAGUSD', 'HG=F':'XCUUSD', 'CL=F':'XTIUSD', 'NG=F':'XNGUSD',
    'XBRUSD=X':'XBRUSD', 'XTIUSD=X':'XTIUSD', 'XAUUSD=X':'XAUUSD', 'XAGUSD=X':'XAGUSD',
    'XCUUSD=X':'XCUUSD', 'XNGUSD=X':'XNGUSD', 'BTC-USD':'BTC', 'ETH-USD':'ETH', 'SOL-USD':'SOL',
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
                        if r["qualityScore"]<cfg["qmin"]: rs.append(f"Q{r['qualityScore']:.0f}<{cfg['qmin']}")
                        if r["activityScore"]<cfg["amin"]: rs.append(f"A{r['activityScore']:.0f}<{cfg['amin']}")
                        if r["trendAge"]>cfg["agemax"]: rs.append(f"Age{r['trendAge']}>{cfg['agemax']}")
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


# ═══════════════════════════════════════════════════════════════════════════════
# v15.2c BOTTLENECK INTEGRATION — Intel Tab Only
# ═══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def _run_bottleneck_scanner(regime, prices):
    if not SCANNER_AVAILABLE:
        return None
    try:
        scanner = UnifiedBottleneckScanner(regime)
        return scanner.scan(prices, run_options=True)
    except Exception as e:
        logging.error(f"Scanner run fail: {e}")
        return None

def render_bottleneck_intel(btl):
    if not btl:
        st.warning("Scanner unavailable — check feedparser install and config/supply_chain.json")
        return
    demand = btl.get("demand_pulse", {})
    basket = btl.get("basket", [])
    enriched = btl.get("enriched_signals", [])
    regime_info = btl.get("regime", {})
    st.markdown("**🧠 LIVE BOTTLENECK INTEL — 7 Layer Fusion**")
    st.caption(f"Regime mult: {regime_info.get('regime_mult', 1.0):.2f} | Aligned: {regime_info.get('aligned', False)} | Confidence: {regime_info.get('confidence', 0):.0%}")

    st.markdown("**L1 — Demand Detection (RSS Narrative)**")
    if demand:
        dcols = st.columns(min(len(demand), 4))
        for idx, (theme, data) in enumerate(demand.items()):
            with dcols[idx]:
                state = data.get("state", "❄️ COLD")
                sc = data.get("narrative_score", 0)
                bc = "#1a4d2e" if "HOT" in state else "#5c3d00" if "WARM" in state else "#2d3748"
                fc = "#4ade80" if "HOT" in state else "#fbbf24" if "WARM" in state else "#8b949e"
                st.markdown(f"""<div style="background:{bc};border:1px solid #30363d;border-radius:8px;padding:8px;text-align:center;">
                    <div style="font-size:10px;color:#8b949e;">{theme}</div>
                    <div style="font-size:16px;font-weight:800;color:{fc};">{state}</div>
                    <div style="font-size:10px;color:#c9d1d9;">{sc:.0%} ({data.get('mentions',0)} mentions)</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.caption("No narrative data.")
    st.divider()

    st.markdown("**L3→L6 — Supply Chain → Allocation → Transmission → Options**")
    if enriched:
        df_rows = []
        for e in enriched[:15]:
            opt = e.get("options_signal")
            df_rows.append({
                "Ticker": clean_tk(e["ticker"]), "Sector": e.get("sector", "-"), "Layer": e.get("layer", "-"),
                "BtlScore": f"{e.get('bottleneck_score', 0):.0%}", "Alloc": e.get("allocation_verdict", "-"),
                "Trans": e.get("transmission_note", "-"), "Fusion": f"{e.get('fusion_score', 0):.0%}",
                "Grade": e.get("fusion_grade", "C"),
                "Options": f"{opt['strike']}@{opt['exp']}" if opt else "—",
                "Conv": f"{opt['convexity_score']:.1f}" if opt else "—",
            })
        st.dataframe(pd.DataFrame(df_rows), use_container_width=True, hide_index=True)
    else:
        st.caption("No enriched signals.")
    st.divider()

    st.markdown("**L7 — Portfolio Basket (Uncorrelated Winners)**")
    if basket:
        for b in basket:
            opt = b.get("options_signal")
            with st.container():
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**🎯 {clean_tk(b['ticker'])} — {b.get('name', '')}**")
                    st.caption(f"{b.get('reasons', '-')} | {b.get('allocation_verdict', '-')} | {b.get('transmission_note', '-')
                    if opt:
                        st.caption(f"🎲 Options: {opt['strike']} Call @ {opt['exp']} (IV {opt['iv']:.0%}, γ {opt['gamma']})")
                with c2:
                    st.markdown(f"<span style='color:#58a6ff;font-weight:700;font-size:16px;'>{b.get('fusion_score', 0):.0%} {b.get('fusion_grade', 'C')}</span>", unsafe_allow_html=True)
    else:
        st.caption("No basket — regime filter too tight or no early signals.")
    st.divider()

    st.markdown("**L3 — Supply Chain Graph Explorer**")
    if SCANNER_AVAILABLE:
        graph = SupplyChainGraph()
        tickers_in_graph = list(graph.db.keys())
        selected = st.selectbox("Select node", tickers_in_graph, format_func=lambda x: f"{x} — {graph.db[x].name}")
        if selected:
            node = graph.db[selected]
            up = graph.upstream_map(selected)
            down = graph.downstream_map(selected)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown("**Upstream (Suppliers)**")
                for u in up:
                    uname = graph.db[u].name if u in graph.db else u
                    st.markdown(f"<span style='color:#8b949e;font-size:11px;'>← {u} ({uname})</span>", unsafe_allow_html=True)
                if not up: st.caption("Raw material / no upstream")
            with c2:
                st.markdown(f"**{selected}**")
                st.caption(f"{node.name} | {node.layer} | {node.sector}")
                bi = node.bottleneck_indicators
                st.caption(f"Cap: {bi.get('capacity_util', 0):.0%} | Demand: {bi.get('demand_growth', 0):.1f}x | Lead: {bi.get('lead_time_weeks', 0)}w")
            with c3:
                st.markdown("**Downstream (Customers)**")
                for d in down:
                    dname = graph.db[d].name if d in graph.db else d
                    st.markdown(f"<span style='color:#8b949e;font-size:11px;'>→ {d} ({dname})</span>", unsafe_allow_html=True)
                if not down: st.caption("End product / no downstream")
    st.divider()

    st.markdown("**L8 — Execution / Convexity Monitor**")
    opt_signals = [e for e in enriched if e.get("options_signal")]
    if opt_signals:
        st.success(f"🎲 {len(opt_signals)} names with options convexity detected")
        for o in opt_signals[:5]:
            opt = o["options_signal"]
            st.markdown(f"<span style='color:#fbbf24;font-size:12px;'>**{clean_tk(o['ticker'])}** {opt['strike']} Call (IV {opt['iv']:.0%}, γ {opt['gamma']}, δ {opt['delta']}) — Expected move: {opt['expected_move_pct']:.1f}%</span>", unsafe_allow_html=True)
    else:
        st.info("No high-convexity OTM calls — either priced-in or options data unavailable.")


# ═══════════════════════════════════════════════════════════════════════════════
# ON-CHAIN SCANNER (preserved)
# ═══════════════════════════════════════════════════════════════════════════════

from dataclasses import dataclass as _dataclass
from typing import Optional as _Optional

@_dataclass
class CC:
    name:str;slug:str;dune:_Optional[str]=None;eth:_Optional[str]=None;nt:str="";tc:_Optional[str]=None

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


# ═══════════════════════════════════════════════════════════════════════════════
# DATA LOADERS — CHUNKED DOWNLOAD
# ═══════════════════════════════════════════════════════════════════════════════

def _chunked_download(ticker_list, period="6mo", interval="1d", chunk=20):
    prices = {}
    for i in range(0, len(ticker_list), chunk):
        batch = ticker_list[i:i+chunk]
        try:
            data = yf.download(" ".join(batch), period=period, interval=interval, progress=False, auto_adjust=True)
            if isinstance(data.columns, pd.MultiIndex):
                for t in batch:
                    if t in data["Close"]: prices[t] = data["Close"][t].dropna()
            else:
                if len(batch) == 1 and "Close" in data:
                    prices[batch[0]] = data["Close"].dropna()
        except Exception as e:
            logging.warning(f"Batch fail {batch}: {e}")
            for t in batch:
                try:
                    df = yf.download(t, period=period, interval=interval, progress=False, auto_adjust=True)
                    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                    if not df.empty and "Close" in df: prices[t] = df["Close"].dropna()
                except: pass
        time.sleep(0.3)
    return prices

@st.cache_data(ttl=300)
def _load_all():
    regime = get_regime_snapshot()
    tickers = {
        "us_longs": ["IWM","XLI","ITB","XTL","EQRR","GII","EWH","EWW","ARGT","EIS","IBIT","HII","CAT","UPS","LII","JBHT","MAR","ONTO","EMR","RH","SBUX","TXG","AVO","FRPT","PEP","XOM","HSY","WMB","ET","COAL","YCS","DE","NUE","VST","NRG","CEG","BWXT","CWEN","AES","FSLR","ENPH","NOVA"],
        "us_shorts": ["XLK","XLF","XLY","IHF","PSCH","MAGS","CIBR","IVES","MSFO","DESK","GRNY","SKYY","MSTY","BTAL","XLP","TLT","ZROZ","ROP","RBLX","TRU","NVDA","META","AMZN","GOOGL","NFLX","CRM","NOW","SNOW","PLTR","OKTA"],
        "ihsg_buys": ["BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK","UNVR.JK","INDF.JK","KLBF.JK","BMRI.JK","BBNI.JK","ANTM.JK","ADRO.JK","ITMG.JK","PTBA.JK","MDKA.JK","INCO.JK","CPIN.JK","JPFA.JK","EXCL.JK","ISAT.JK","TBIG.JK","TOWR.JK","SMGR.JK","INTP.JK","CTRA.JK","PWON.JK","BSDE.JK","AMRT.JK","MPPA.JK","ACES.JK","ERAA.JK"],
        "fx_longs": ["USDJPY=X","GLD","AAAU","YCS","USDCNH=X","USDCHF=X","USDSEK=X","USDNOK=X"],
        "fx_shorts": ["EURUSD=X","AUDUSD=X","UUP","GBPUSD=X","NZDUSD=X","EURJPY=X","EURGBP=X","GBPJPY=X","CADJPY=X","AUDJPY=X"],
        "comm_longs": ["SLV","GDX","GC=F","SI=F","HG=F","CL=F","NG=F","XOP","OIH","BNO","GLD","AAAU","COAL","URA","PPLT","PA=F","PL=F","ZO=F","ZC=F","ZS=F","ZW=F","CC=F","KC=F","CT=F","SB=F","LBS=F"],
        "comm_shorts": ["DUST","BITS","SCO","KOLD"],
        "crypto_longs": ["BTC-USD","ETH-USD","IBIT","COIN","MSTR","RIOT","MARA","HUT","BITF","WGMI"],
        "crypto_shorts": ["SOL-USD","ADA-USD","XRP-USD","DOT-USD","AVAX-USD","MATIC-USD","LINK-USD","UNI-USD","AAVE-USD","CRV-USD"],
    }
    all_t = list(set([t for v in tickers.values() for t in v]))
    prices = _chunked_download(all_t, period="6mo", interval="1d", chunk=20)
    return {"q": regime, "tickers": tickers, "prices": prices}

snap = _load_all()
q = snap["q"]; tickers = snap["tickers"]; prices = snap["prices"]
sq = q.get("structural_quad", "Q2"); mq = q.get("monthly_quad", "Q2"); gq = q.get("global_quad", "Q2")
conf = q.get("confidence", 0.5); op = q.get("operating_regime", "...")
src = q.get("source", "unknown"); gy = q.get("growth_yoy", 0); iy = q.get("inflation_yoy", 0)
ps = q.get("policy_stance", "—"); vix = q.get("vix", 20.0)
mp = q.get("macro_pulse", {})

if not mp.get('ism_now') or (isinstance(mp.get('ism_now'), str) and mp.get('ism_now') == '—'):
    try:
        xli = prices.get("XLI", pd.Series())
        if len(xli) >= 22:
            xli_1m = (xli.iloc[-1] / xli.iloc[-22] - 1) * 100
            xli_3m = (xli.iloc[-1] / xli.iloc[-64] - 1) * 100 if len(xli) >= 64 else 0
            ism_proxy = 50.0 + xli_1m * 1.5 + xli_3m * 0.6
            mp['ism_now'] = round(max(35.0, min(70.0, ism_proxy)), 1)
            mp['ism_delta'] = round(xli_1m * 1.5, 1)
            mp['ism_source'] = 'XLI proxy (FRED missing)'
    except Exception as e:
        pass

btl_result = _run_bottleneck_scanner(q, prices) if SCANNER_AVAILABLE else None


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
def nf(x,d=0.0): return float(np.nan_to_num(x,nan=d))
def pct(v,d=1):
    if not math.isfinite(v): return "—"
    return f"{v*100:+.{d}f}%"


# ═══════════════════════════════════════════════════════════════════════════════
# MACRO FEATURE BUILDERS
# ═══════════════════════════════════════════════════════════════════════════════

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
    f["data_coverage"] = clamp(q.get("fred_loaded",0) / max(len(PRIMARY_SERIES),1))
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
    exec_score=clamp(0.20*h.get("weather",0.5)+0.14*{"Healthy":0.80,"Narrow":0.48,"Fragile":0.34,"Mixed":0.35,"Broken":0.18}.get(h.get("verdict","Mixed"),0.50)+0.10*{"Investable":0.78,"Chop":0.42,"Defensive":0.22}.get("Investable" if vix<19 else ("Chop" if vix<29 else "Defensive"),0.42)+0.12*{"Q1":0.68,"Q2":0.78,"Q3":0.48,"Q4":0.25}.get(q.get("quad","Q2"),0.50)+0.10*q.get("confidence",0.5)+0.09*h.get("trade",0.5)+0.09*(1-unwind)+0.08*(1-shock_s)+0.08*(1-crash_score))
    return {
        "crash_score":crash_score,"risk_off":risk_off,
        "state":"🔴 ELEVATED" if crash_score>=0.65 else ("🟡 WATCH" if crash_score>=0.42 else "🟢 CALM"),
        "vol_stress":vol_st,"credit_stress":clamp(0.60*clamp((hy-300)/400 if math.isfinite(hy) else 0.3)),
        "breadth_dmg":health_frag,"exec_score":exec_score,
        "exec_mode":"🟢 Add on Reset" if exec_score>=0.60 else ("🟡 Wait Reclaim" if exec_score>=0.45 else "🔴 Defensive Only")
    }

def build_rotation(q, h, f, prices=None):
    s_quad=q.get("quad","Q2"); uup_3m=nf(f.get("uup_3m",f.get("dxy_3m",0.0)))
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
    bank_scores=[ret_n(prices.get(t,pd.Series()),21) for t in ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK"] if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
    bank_health=clamp(0.5+np.mean(bank_scores)/0.06) if bank_scores else 0.5
    rel_1m=(jkse_1m-spy_1m) if math.isfinite(jkse_1m) and math.isfinite(spy_1m) else 0.0
    foreign_flow=clamp(0.5+rel_1m/0.06)
    em_regime_score={"Q1":0.65,"Q2":0.70,"Q3":0.52,"Q4":0.28}.get(q.get("quad","Q2"),0.5)
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
    def _score_above(v, clear_thr, near_thr):
        if not math.isfinite(v): return 0.42, False, False
        if v > clear_thr: return 1.00, True, True
        if v > near_thr: return 0.72, False, True
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
    btc_score,btc_hard,btc_soft=_score_above(btc,72000,70000)
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
    slowdown=float(f.get("slowdown_flags",0.0))
    if slowdown>=0.30: drivers.append({"label":"Growth slowdown","score":clamp(slowdown),"tone":"bad" if slowdown>=0.50 else "warn","why":"Claims/ISM/housing memberi sinyal perlambatan.","tag":"macro"})
    inf=float(f.get("inf_shock",0.0))
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


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════════

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
      <div style="font-size:11px;color:#8b949e;">v15.2c · Bottleneck Scanner · 7-Layer Fusion</div>
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

# ═══════════════════════════════════════════════════════════════════════════════
# TABS
# ═══════════════════════════════════════════════════════════════════════════════

tabs=st.tabs(["⚡ Command Center","🌍 Markets","🧠 Bottleneck Intel","📊 Regime Deep Dive","⚠️ Risk & Diag"])

# ═══════════════════════════════════════════════════════════════════════════════
# TAB 0: COMMAND CENTER
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
    if SCANNER_AVAILABLE and btl_result:
        st.success(f"🧠 Bottleneck Scanner ACTIVE — {len(btl_result.get('enriched_signals', []))} signals | {len(btl_result.get('basket', []))} basket names")
    else:
        st.warning("🧠 Bottleneck Scanner OFFLINE — install feedparser, check config/supply_chain.json")
    st.divider()
    if sq!=mq:
        st.warning(f"⚠️ TRANSITIONAL — {sq}/{mq} divergen. Trade monthly signal only. Jangan buka structural positions.")
    else:
        st.success(f"✅ ALIGNED — {sq} confirmed. Bisa deploy structural + monthly.")
    st.markdown("**📊 Macro Pulse**")
    c1,c2,c3=st.columns(3)
    with c1:
        ism_d=mp.get('ism_delta'); ism_n=mp.get('ism_now')
        ism_src = mp.get('ism_source', '')
        ism_d_str = f"{ism_d:+.1f}" if isinstance(ism_d,(int,float)) and math.isfinite(ism_d) else "—"
        ism_n_str = f"{ism_n:.1f}" if isinstance(ism_n,(int,float)) and math.isfinite(ism_n) else "—"
        src_note = f"<span style='font-size:9px;color:#fbbf24;'>⚠️ {ism_src}</span>" if ism_src else ""
        _h(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;">
          <div style="font-size:10px;color:#8b949e;">ISM Mfg Δ {src_note}</div>
          <div style="font-size:18px;font-weight:800;color:#e6edf3;">{ism_d_str}</div>
          <div style="font-size:10px;color:#8b949e;">Now: {ism_n_str}</div>
        </div>""")
    with c2:
        cl_d=mp.get('claims_delta'); cl_n=mp.get('claims_now')
        def fmt_claims(v):
            if isinstance(v,(int,float)) and math.isfinite(v):
                if abs(v)>=1000: return f"{v/1000:+.1f}K"
                return f"{v:+.0f}"
            return "—"
        cl_d_str=fmt_claims(cl_d); cl_n_str=fmt_claims(cl_n)
        _h(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;">
          <div style="font-size:10px;color:#8b949e;">Claims Δ</div>
          <div style="font-size:18px;font-weight:800;color:#e6edf3;">{cl_d_str}</div>
          <div style="font-size:10px;color:#8b949e;">Now: {cl_n_str}</div>
        </div>""")
    with c3:
        be_d=mp.get('be_1m'); be_n=mp.get('be_now')
        be_d_str = f"{be_d:+.2f}pp" if isinstance(be_d,(int,float)) and math.isfinite(be_d) else "—"
        be_n_str = f"{be_n:.2f}%" if isinstance(be_n,(int,float)) and math.isfinite(be_n) else "—"
        _h(f"""<div style="background:#0d1117;border:1px solid #30363d;border-radius:10px;padding:12px;">
          <div style="font-size:10px;color:#8b949e;">Breakeven 1M</div>
          <div style="font-size:18px;font-weight:800;color:#e6edf3;">{be_d_str}</div>
          <div style="font-size:10px;color:#8b949e;">Now: {be_n_str}</div>
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
    stage=most_hated.get("stage","monitor")
    action=most_hated.get("action","—")
    posture=most_hated.get("posture","Defense")
    size_mult=most_hated.get("size_mult",0.35)
    long_boost=most_hated.get("scanner_long_boost",0.0)
    short_pen=most_hated.get("scanner_short_penalty",0.0)
    invalidators=most_hated.get("invalidators",[])
    if cc>=4:
        banner_col="#1a4d2e"; text_col="#4ade80"; emoji="🔥"
    elif cc>=3:
        banner_col="#5c3d00"; text_col="#fbbf24"; emoji="⚡"
    elif cc>=2:
        banner_col="#5c3d00"; text_col="#fbbf24"; emoji="🟡"
    else:
        banner_col="#5c1a1a"; text_col="#f87171"; emoji="❌"
    _h(f"""
    <div style="background:{banner_col};border:1px solid #30363d;border-radius:12px;padding:14px;margin-bottom:10px;">
      <div style="font-size:16px;font-weight:800;color:{text_col};">{emoji} MOST HATED RALLY — {cc}/4 CLEAR</div>
      <div style="font-size:13px;color:#e6edf3;margin-top:6px;"><b>Stage:</b> {stage}</div>
      <div style="font-size:12px;color:#c9d1d9;margin-top:4px;"><b>Posture:</b> {posture}</div>
      <div style="font-size:12px;color:#c9d1d9;"><b>Action:</b> {action}</div>
      <div style="font-size:12px;color:#c9d1d9;"><b>Size Multiplier:</b> {size_mult:.0%}</div>
      <div style="font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:6px;">
        Scanner Long Boost: +{long_boost:.0%} | Short Penalty: {short_pen:.0%}<br>
        Invalidators: {', '.join(invalidators) if invalidators else 'None active'}
      </div>
    </div>
    """)
    st.divider()
    st.markdown("**💥 CRASH METER & HEALTH**")
    c1,c2,c3,c4=st.columns(4)
    with c1: st.metric("Crash Score", f"{cr.get('crash_score',0):.0%}"); st.progress(cr.get('crash_score',0), text=cr.get('state','?'))
    with c2: st.metric("Weather", h.get('weather_state','—')); st.caption(f"Verdict: {h.get('verdict','—')}")
    with c3: st.metric("Trade Env", h.get('trade_state','—')); st.caption(f"Trend: {h.get('trend_state','—')}")
    with c4: st.metric("Tail", h.get('tail_state','—')); st.caption(f"Exec: {cr.get('exec_mode','?')}")
    st.caption(f"Risk-Off: {cr.get('risk_off',0):.0%} | Breadth Dmg: {cr.get('breadth_dmg',0):.0%} | Vol Stress: {cr.get('vol_stress',0):.0%}")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1: MARKETS — DIFFERENTIATED LAYOUTS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[1]:
    def rn(s,n):
        if s is None or len(s)<n+1: return float("nan")
        try: b=float(s.iloc[-(n+1)]); e=float(s.iloc[-1]); return float(e/b-1) if b!=0 and b==b else float("nan")
        except: return float("nan")
    def gr(s,n): r=rn(s,n); return f"{r:+.1%}" if r==r else "—"
    def tc_trr(tk,name,r1m,r3m,ac,expected_sig):
        ev=_eval(tk,ac)
        if ev:
            actual = ev["signal"]
            if actual == expected_sig:
                badge = f"🟢 WORTH — TRR {actual}"; col = "#3fb950" if expected_sig=="LONG" else "#f85149"; ic = "▲" if expected_sig=="LONG" else "▼"
            else:
                badge = f"🔴 CONTRA — TRR {actual}"; col = "#f85149" if expected_sig=="LONG" else "#3fb950"; ic = "▼" if expected_sig=="LONG" else "▲"
        else:
            badge = "⚪ HOLD — No TRR Signal"; col = "#8b949e"; ic = "◆"
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
    st.caption("v15.2c macro brain + TRR/LRR gate. Regime-aware, route-aware, sized.")
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
    qp=quad_policies.get(sq,quad_policies["Q2"])
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
    mt=st.tabs(["🇺🇸 US Stocks","🇮🇩 IHSG","💱 FX","🛢️ Commodities","🔐 Crypto"])

    # ═════════════════════════════════════════════════════════════════
    # US STOCKS TAB
    # ═════════════════════════════════════════════════════════════════
    with mt[0]:
        ul=tickers.get("us_longs",[]); us=tickers.get("us_shorts",[])
        nm={"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","TLT":"Long Bond","GLD":"Gold","HII":"Huntington","CAT":"Caterpillar","UPS":"UPS","LII":"Lennox","JBHT":"JB Hunt","MAR":"Marriott","ONTO":"Onto","EMR":"Emerson","RH":"Restoration","SBUX":"Starbucks","TXG":"10x Genomics","AVO":"Mission Produce","FRPT":"Freshpet","PEP":"Pepsi","XOM":"Exxon","HSY":"Hershey","WMB":"Williams","ET":"Energy Transfer","ROP":"Roper","RBLX":"Roblox","TRU":"TransUnion","NVDA":"Nvidia","XTL":"Telecom","EQRR":"Rising Rates","GII":"Infrastructure","EWH":"Hong Kong","EWW":"Mexico","ARGT":"Argentina","EIS":"Israel","IBIT":"Bitcoin ETF","COAL":"Coal","YCS":"Short Yen","DE":"Deere","NUE":"Nucor","VST":"Vistra","NRG":"NRG","CEG":"Constellation","BWXT":"BWX","CWEN":"Clearway","AES":"AES","FSLR":"First Solar","ENPH":"Enphase","NOVA":"Sunnova"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(ul,nm,"US_STOCKS","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(us,nm,"US_STOCKS","SHORT",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("CL=F","Oil"),("UUP","USD")])
        st.divider()
        st.markdown("**📊 Factor Regime**")
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            rsp_s = prices.get("RSP", pd.Series()); spy_s = prices.get("SPY", pd.Series())
            if len(rsp_s)>63 and len(spy_s)>63:
                rel = (rsp_s.iloc[-1]/rsp_s.iloc[-64]-1) - (spy_s.iloc[-1]/spy_s.iloc[-64]-1)
                st.metric("Equal vs Cap Weight", f"{rel:+.1%}", delta="EQW Lead" if rel>0 else "CW Lead")
            else: st.caption("No RSP data")
        with fc2:
            vug = prices.get("VUG", pd.Series()); vtv = prices.get("VTV", pd.Series())
            if len(vug)>63 and len(vtv)>63:
                rel2 = (vug.iloc[-1]/vug.iloc[-64]-1) - (vtv.iloc[-1]/vtv.iloc[-64]-1)
                st.metric("Growth vs Value", f"{rel2:+.1%}", delta="Growth" if rel2>0 else "Value")
            else: st.caption("No VUG/VTV")
        with fc3:
            mtum = prices.get("MTUM", pd.Series()); usmv = prices.get("USMV", pd.Series())
            if len(mtum)>63 and len(usmv)>63:
                rel3 = (mtum.iloc[-1]/mtum.iloc[-64]-1) - (usmv.iloc[-1]/usmv.iloc[-64]-1)
                st.metric("Momentum vs LowVol", f"{rel3:+.1%}", delta="Momentum" if rel3>0 else "LowVol")
            else: st.caption("No MTUM/USMV")
        st.divider()
        rml([("XLE","Energy"),("XLF","Fin"),("XLI","Ind"),("XLB","Mat"),("XLK","Tech"),("XLV","Health"),("XLY","Con.D"),("XLP","Con.S"),("XLU","Util"),("XLRE","RE")],"SPY","Sector Leadership")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(ul+us)),"US_STOCKS")

    # ═════════════════════════════════════════════════════════════════
    # IHSG TAB — DISTINCT
    # ═════════════════════════════════════════════════════════════════
    with mt[1]:
        ih_t=tickers.get("ihsg_buys",[])
        nm={"BBCA.JK":"BCA","BBRI.JK":"BRI","BMRI.JK":"Mandiri","BBNI.JK":"BNI","ASII.JK":"Astra","TLKM.JK":"Telkom","UNVR.JK":"Unilever","INDF.JK":"Indofood","KLBF.JK":"Kalbe","ANTM.JK":"Antam","ADRO.JK":"Adaro","ITMG.JK":"Indomining","PTBA.JK":"Bukit Asam","MDKA.JK":"Merdeka","INCO.JK":"Vale","CPIN.JK":"Charoen","JPFA.JK":"Japfa","EXCL.JK":"XL","ISAT.JK":"Indosat","TBIG.JK":"Tower","TOWR.JK":"Tower Bersama","SMGR.JK":"Semen","INTP.JK":"Indocement","CTRA.JK":"Ciputra","PWON.JK":"Pakuwon","BSDE.JK":"Bumi Serpong","AMRT.JK":"Alfamart","MPPA.JK":"Matahari","ACES.JK":"Ace Hardware","ERAA.JK":"Erajaya"}
        st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(ih_t,nm,"IHSG","LONG",3)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom"),("BMRI.JK","Mandiri"),("BBNI.JK","BNI"),("ANTM.JK","Antam"),("ADRO.JK","Adaro")])
        st.divider()
        st.markdown("**🏭 IDX Sector Rotation**")
        sec_cols = st.columns(4)
        sectors = [
            ("Mining", [("ANTM.JK","Antam"),("ADRO.JK","Adaro"),("ITMG.JK","ITMG"),("MDKA.JK","MDKA"),("INCO.JK","INCO")]),
            ("Banking", [("BBCA.JK","BCA"),("BBRI.JK","BRI"),("BMRI.JK","Mandiri"),("BBNI.JK","BNI")]),
            ("Consumer", [("UNVR.JK","Unilever"),("INDF.JK","Indofood"),("KLBF.JK","Kalbe"),("CPIN.JK","CPIN"),("JPFA.JK","JPFA")]),
            ("Telco/Infra", [("TLKM.JK","Telkom"),("EXCL.JK","XL"),("ISAT.JK","Indosat"),("TBIG.JK","TBIG"),("TOWR.JK","TOWR")]),
        ]
        for col, (sec_name, sec_tickers) in zip(sec_cols, sectors):
            with col:
                st.markdown(f"**{sec_name}**")
                for tk, name in sec_tickers:
                    s = prices.get(tk)
                    if s is not None and len(s)>22:
                        r1 = rn(s,21)
                        color = "#4ade80" if r1>0 else "#f87171" if r1<0 else "#8b949e"
                        st.markdown(f"<span style='color:{color};font-size:11px;'>{name}: {r1:+.1%}</span>", unsafe_allow_html=True)
        st.divider()
        st.markdown("**🌏 Macro Linkages**")
        lk1, lk2, lk3 = st.columns(3)
        with lk1:
            jkse_s = prices.get("^JKSE", pd.Series()); spy_s = prices.get("SPY", pd.Series())
            if len(jkse_s)>63 and len(spy_s)>63:
                rel = (jkse_s.iloc[-1]/jkse_s.iloc[-64]-1) - (spy_s.iloc[-1]/spy_s.iloc[-64]-1)
                st.metric("IHSG vs SPY 3M", f"{rel:+.1%}", delta="IHSG Lead" if rel>0 else "SPY Lead")
            else: st.caption("No data")
        with lk2:
            idr_s = prices.get("IDR=X", pd.Series())
            if len(idr_s)>22:
                idr_1m = rn(idr_s, 21)
                st.metric("IDR 1M", f"{idr_1m:+.1%}", delta="Weaker" if idr_1m>0 else "Stronger")
            else: st.caption("No IDR")
        with lk3:
            coal_s = prices.get("ADRO.JK", pd.Series()) or prices.get("ITMG.JK", pd.Series())
            oil_s = prices.get("CL=F", pd.Series())
            if coal_s is not None and len(coal_s)>22 and oil_s is not None and len(oil_s)>22:
                c1m = rn(coal_s,21); o1m = rn(oil_s,21)
                st.metric("Coal vs Oil 1M", f"{c1m-o1m:+.1%}", delta="Coal Lead" if c1m>o1m else "Oil Lead")
            else: st.caption("No coal/oil")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(ih_t,"IHSG")
        st.divider()
        st.markdown(f"**🇮🇩 IHSG Score: {ih['ihsg_score']:.0%}** · {ih['exec_mode']}")
        st.caption(f"Asing: {ih['flow_state']} | IDR 1M: {pct(ih['usd_idr_1m'])} | vs SPY: {ih['rel_state']}")

    # ═════════════════════════════════════════════════════════════════
    # FX TAB — DISTINCT
    # ═════════════════════════════════════════════════════════════════
    with mt[2]:
        fl=tickers.get("fx_longs",[]); fs=tickers.get("fx_shorts",[])
        nm={"EURUSD=X":"EUR/USD","USDJPY=X":"USD/JPY","AUDUSD=X":"AUD/USD","USDIDR=X":"USD/IDR","UUP":"DXY","GBPUSD=X":"GBP/USD","USDCAD=X":"USD/CAD","NZDUSD=X":"NZD/USD","USDCHF=X":"USD/CHF","USDCNH=X":"USD/CNH","USDSEK=X":"USD/SEK","USDNOK=X":"USD/NOK","EURJPY=X":"EUR/JPY","EURGBP=X":"EUR/GBP","GBPJPY=X":"GBP/JPY","CADJPY=X":"CAD/JPY","AUDJPY=X":"AUD/JPY","GLD":"Gold","AAAU":"Gold","YCS":"Short Yen"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(fl,nm,"FOREX","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(fs,nm,"FOREX","SHORT",2)
        st.divider(); st.markdown("**🌍 DXY Components Heatmap**"); rh([("UUP","DXY"),("EURUSD=X","EUR"),("USDJPY=X","JPY"),("GBPUSD=X","GBP"),("USDCAD=X","CAD"),("AUDUSD=X","AUD"),("NZDUSD=X","NZD"),("USDCHF=X","CHF"),("USDSEK=X","SEK"),("USDNOK=X","NOK")])
        st.divider()
        st.markdown("**💱 Carry & Momentum Monitor**")
        fx_all = list(set(fl+fs))
        fx_rows = []
        for t in fx_all:
            s = prices.get(t)
            if s is not None and len(s)>22:
                fx_rows.append({"pair":clean_tk(t), "1m":rn(s,21), "3m":rn(s,63), "ts":ts(s)})
        if fx_rows:
            fx_df = pd.DataFrame(fx_rows).sort_values("1m", ascending=False)
            st.dataframe(fx_df.style.format({"1m":"{:+.1%}","3m":"{:+.1%}","ts":"{:.0%}"}), use_container_width=True, hide_index=True)
        else: st.caption("No FX data")
        st.divider()
        st.markdown("**🏛️ Safe Haven vs Risk**")
        sh1, sh2 = st.columns(2)
        with sh1:
            st.markdown("**Safe Haven**")
            rh([("USDJPY=X","USD/JPY"),("USDCHF=X","USD/CHF"),("GLD","Gold"),("UUP","DXY")])
        with sh2:
            st.markdown("**Risk / Commodity FX**")
            rh([("AUDUSD=X","AUD/USD"),("USDCAD=X","USD/CAD"),("NZDUSD=X","NZD/USD"),("EURUSD=X","EUR/USD")])
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(fl+fs)),"FOREX")

    # ═════════════════════════════════════════════════════════════════
    # COMMODITIES TAB — DISTINCT
    # ═════════════════════════════════════════════════════════════════
    with mt[3]:
        cl=tickers.get("comm_longs",[]); cs=tickers.get("comm_shorts",[])
        nm={"SLV":"Silver","GDX":"Gold Miners","GC=F":"Gold Fut","SI=F":"Silver Fut","HG=F":"Copper Fut","CL=F":"WTI Oil","NG=F":"Nat Gas","XOP":"Oil Explorers","OIH":"Oil Services","BNO":"Brent Oil","GLD":"Gold","AAAU":"Gold","COAL":"Coal","URA":"Uranium","PPLT":"Platinum","PA=F":"Palladium","PL=F":"Platinum Fut","ZO=F":"Oats","ZC=F":"Corn","ZS=F":"Soybeans","ZW=F":"Wheat","CC=F":"Cocoa","KC=F":"Coffee","CT=F":"Cotton","SB=F":"Sugar","LBS=F":"Lumber","DUST":"Gold Bear","BITS":"Bitcoin Strat","SCO":"Short Oil","KOLD":"Short Gas"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(cl,nm,"COMMODITIES","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(cs,nm,"COMMODITIES","SHORT",2)
        st.divider(); st.markdown("**🌍 Commodity Complex Heatmap**"); rh([("CL=F","WTI Oil"),("GC=F","Gold Fut"),("HG=F","Copper"),("SI=F","Silver"),("NG=F","Nat Gas"),("SLV","Silver ETF"),("URA","Uranium"),("PPLT","Platinum")])
        st.divider()
        st.markdown("**⚖️ Precious vs Industrial**")
        pvi1, pvi2 = st.columns(2)
        with pvi1:
            gld_s = prices.get("GC=F", pd.Series()); slv_s = prices.get("SI=F", pd.Series())
            if len(gld_s)>63 and len(slv_s)>63:
                ratio = (gld_s.iloc[-1]/gld_s.iloc[-64]-1) - (slv_s.iloc[-1]/slv_s.iloc[-64]-1)
                st.metric("Gold vs Silver 3M", f"{ratio:+.1%}", delta="Gold Lead" if ratio>0 else "Silver Lead")
            else: st.caption("No data")
        with pvi2:
            hgf = prices.get("HG=F", pd.Series()); gcf = prices.get("GC=F", pd.Series())
            if len(hgf)>63 and len(gcf)>63:
                ratio2 = (hgf.iloc[-1]/hgf.iloc[-64]-1) - (gcf.iloc[-1]/gcf.iloc[-64]-1)
                st.metric("Copper vs Gold 3M", f"{ratio2:+.1%}", delta="Copper Lead" if ratio2>0 else "Gold Lead")
            else: st.caption("No data")
        st.divider()
        st.markdown("**📈 Term Structure Proxy (Front vs Back momentum)**")
        term_rows = []
        for t in ["CL=F","GC=F","SI=F","HG=F","NG=F","ZW=F","ZC=F"]:
            s = prices.get(t)
            if s is not None and len(s)>64:
                term_rows.append({"contract":clean_tk(t), "front_1m":rn(s,21), "front_3m":rn(s,63)})
        if term_rows:
            st.dataframe(pd.DataFrame(term_rows).style.format({"front_1m":"{:+.1%}","front_3m":"{:+.1%}"}), use_container_width=True, hide_index=True)
        else: st.caption("No futures data")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(cl+cs)),"COMMODITIES")

    # ═════════════════════════════════════════════════════════════════
    # CRYPTO TAB — DISTINCT
    # ═════════════════════════════════════════════════════════════════
    with mt[4]:
        crl=tickers.get("crypto_longs",[]); crs=tickers.get("crypto_shorts",[])
        nm={"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP","ADA-USD":"Cardano","DOT-USD":"Polkadot","AVAX-USD":"Avalanche","MATIC-USD":"Polygon","LINK-USD":"Chainlink","UNI-USD":"Uniswap","AAVE-USD":"Aave","CRV-USD":"Curve","IBIT":"Bitcoin ETF","COIN":"Coinbase","MSTR":"MicroStrategy","RIOT":"Riot","MARA":"Marathon","HUT":"Hut 8","BITF":"Bitfarms","WGMI":"Bitcoin Miners"}
        c1,c2=st.columns(2)
        with c1: st.markdown("**📍 NOW — LONG (TRR Filtered)**"); rc_trr(crl,nm,"CRYPTO","LONG",2)
        with c2: st.markdown("**📍 NOW — SHORT (TRR Filtered)**"); rc_trr(crs,nm,"CRYPTO","SHORT",2)
        st.divider(); st.markdown("**🌍 Heatmap**"); rh([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP"),("ADA-USD","Cardano"),("DOT-USD","Polkadot"),("COIN","Coinbase"),("MSTR","MicroStrategy")])
        st.divider()
        st.markdown("**📊 Dominance & Correlation**")
        d1, d2, d3 = st.columns(3)
        with d1:
            btc_s = prices.get("BTC-USD", pd.Series()); eth_s = prices.get("ETH-USD", pd.Series())
            if len(btc_s)>63 and len(eth_s)>63:
                btc_3m = rn(btc_s,63); eth_3m = rn(eth_s,63)
                dom = btc_3m - eth_3m
                st.metric("BTC vs ETH 3M", f"{dom:+.1%}", delta="BTC Lead" if dom>0 else "ETH Lead")
            else: st.caption("No data")
        with d2:
            if len(btc_s)>63 and len(eth_s)>63:
                ratio = (eth_s.iloc[-1]/btc_s.iloc[-1]) / (eth_s.iloc[-64]/btc_s.iloc[-64]) - 1
                st.metric("ETH/BTC Ratio 3M", f"{ratio:+.1%}", delta="ETH↑" if ratio>0 else "BTC↑")
            else: st.caption("No data")
        with d3:
            nq = prices.get("QQQ", pd.Series())
            if len(btc_s)>63 and nq is not None and len(nq)>63:
                btc_3m = rn(btc_s,63); nq_3m = rn(nq,63)
                corr_proxy = btc_3m - nq_3m
                st.metric("Crypto vs NQ 3M", f"{corr_proxy:+.1%}", delta="Crypto Lead" if corr_proxy>0 else "NQ Lead")
            else: st.caption("No NQ")
        st.markdown("**🎯 TRR/LRR Signal Layer**"); _render_trr(list(set(crl+crs)),"CRYPTO")
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
# TAB 2: BOTTLENECK INTEL (consolidated, no duplication in Markets)
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[2]:
    render_bottleneck_intel(btl_result)
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
# TAB 3: REGIME DEEP DIVE
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[3]:
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
    probs=q.get("probs",{"Q1":0.20,"Q2":0.30,"Q3":0.30,"Q4":0.20})
    m_probs=q.get("monthly_probs",{"Q1":0.20,"Q2":0.30,"Q3":0.30,"Q4":0.20})
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
    st.caption("v15.2c: Pure data-driven. No hardcoded quarter. Bottleneck scanner v4.0 — real nodes only (19 nodes).")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 4: RISK & DIAGNOSTICS
# ═══════════════════════════════════════════════════════════════════════════════
with tabs[4]:
    st.subheader("⚠️ Risk & Diagnostics")
    c1,c2,c3=st.columns(3)
    with c1: st.metric("FRED Loaded", f"{q.get('fred_loaded',0)}/{len(PRIMARY_SERIES)}")
    with c2: st.metric("Source", src)
    with c3: st.metric("API Key", "✅ Active" if q.get('fred_loaded',0)>0 else "❌ Fallback")
    if q.get('fred_loaded',0)==0:
        st.error("🚨 FRED 0 loaded — using proxy data. Check API key.")
        if st.button("🔄 Clear Cache & Reload"):
            st.cache_data.clear(); st.rerun()
    elif q.get('fred_loaded',0) < len(PRIMARY_SERIES):
        missing_keys = q.get('fred_missing_keys', [])
        if missing_keys:
            st.warning(f"🟡 FRED Partial — {q.get('fred_loaded',0)}/{len(PRIMARY_SERIES)} loaded. Missing: {', '.join(missing_keys)}")
        else:
            st.warning(f"🟡 FRED Partial — {q.get('fred_loaded',0)}/{len(PRIMARY_SERIES)} loaded.")
    else:
        st.success("🟢 FRED Full — all primary series loaded.")
    st.divider()
    st.markdown("**🧠 BOTTLENECK SCANNER DIAGNOSTICS**")
    if SCANNER_AVAILABLE:
        st.success("✅ bottleneck_engine.py imported successfully")
        if btl_result:
            st.write(f"- Signals: {len(btl_result.get('enriched_signals', []))}")
            st.write(f"- Basket: {len(btl_result.get('basket', []))} names")
            st.write(f"- Demand themes: {list(btl_result.get('demand_pulse', {}).keys())}")
            st.write(f"- Supply chain nodes: {len(SCANNER_TICKERS)}")
        else:
            st.warning("⚠️ Scanner returned None — check config/supply_chain.json exists")
    else:
        st.error("❌ bottleneck_engine.py failed to import — install feedparser")
    st.divider()
    st.markdown("**🧪 DATA QUALITY**")
    dq_rows=[
        ("Source Mode", sb),
        ("FRED Series", f"{q.get('fred_loaded',0)}/{len(PRIMARY_SERIES)}"),
        ("Macro Pulse", "✅" if mp else "❌"),
        ("VIX Source", "^VIX index" if vix>15 else "VIXY proxy"),
        ("TRR/LRR Engine", "✅ Active"),
        ("On-Chain Scanner", "✅ Active"),
        ("Bottleneck Scanner", "✅ Active v4" if SCANNER_AVAILABLE and btl_result else "❌ Failed"),
        ("Options Convexity", "✅ Active" if SCANNER_AVAILABLE and btl_result and any(e.get('options_signal') for e in btl_result.get('enriched_signals', [])) else "⚠️ No signals"),
        ("External Config", "✅ ./config/supply_chain.json" if os.path.exists("./config/supply_chain.json") else "❌ Missing"),
        ("Scanner Nodes", f"{len(SCANNER_TICKERS)} real" if SCANNER_AVAILABLE else "❌ N/A"),
    ]
    st.dataframe(pd.DataFrame(dq_rows, columns=["Check","Status"]), use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("**📋 FRED DEBUG**")
    st.caption("v15.2c: ISM primary NAPM, fallback XLI proxy if FRED missing. Real PCE fallback to nominal PCE or DPI. Zero hardcoded quarter.")
    if st.toggle("Show FRED series map", False):
        st.json(FRED_SERIES)

st.caption(f"MacroRegime Pro v15.2c · Built {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC · God Mode")