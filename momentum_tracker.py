"""
momentum_tracker.py — Hedgeye Momentum Stock Tracker
STANDALONE — no import from app.py to avoid circular import
"""
import os, sys, json, logging
from datetime import datetime
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
import yfinance as yf

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

MAG7 = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA"]
GATE_MAG7 = {"vm": 1.00, "qmin": 55, "amin": 40, "short": True, "agemax": 35}

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

def _fetch(ticker,period="3y"):
    try:
        df=yf.download(ticker,period=period,interval="1d",progress=False,auto_adjust=True)
        if isinstance(df.columns,pd.MultiIndex): df.columns=df.columns.get_level_values(0)
        df=df.dropna()
        if len(df)<300:
            df2=yf.download(ticker,period="5y",interval="1d",progress=False,auto_adjust=True)
            if isinstance(df2.columns,pd.MultiIndex): df2.columns=df2.columns.get_level_values(0)
            df2=df2.dropna()
            if len(df2)>=300: return df2
        return df if len(df)>=300 else None
    except: return None


class MomentumTracker:
    def __init__(self, tickers=None):
        self.tickers = tickers or MAG7
        self.engine = TRRLRREngine(TRR_PARAMS)

    def _grade(self, quality: float, activity: float, transition: bool) -> str:
        strength = quality * 0.6 + activity * 0.4 + (15 if transition else 0)
        if strength >= 80: return "S"
        if strength >= 65: return "A"
        if strength >= 50: return "B"
        return "C"

    def _regime_alignment(self, trend_phase: int, structural_quad: str) -> str:
        quad_bullish = {"Q1": [1], "Q2": [1], "Q3": [1, -1], "Q4": [-1]}
        allowed = quad_bullish.get(structural_quad, [1])
        return "ALIGNED" if trend_phase in allowed else "COUNTER"

    def scan(self, prices: Optional[Dict[str, pd.Series]] = None, regime_quad: str = "Q2") -> List[Dict]:
        results = []
        for t in self.tickers:
            try:
                if prices and t in prices:
                    df_raw = prices[t]
                    df = pd.DataFrame({
                        "Open": df_raw, "High": df_raw, "Low": df_raw,
                        "Close": df_raw, "Volume": pd.Series(0, index=df_raw.index)
                    })
                else:
                    df = _fetch(t, period="3y")
                    if df is None or len(df) < 300:
                        continue
                r = self.engine.latest(df, vm=GATE_MAG7["vm"])
                if not r: continue
                pr = float(df["Close"].iloc[-1])
                transition = r["trendTransUp"] or r["trendTransDown"] or r["tailTransUp"] or r["tailTransDown"]
                grade = self._grade(r["qualityScore"], r["activityScore"], transition)
                alignment = self._regime_alignment(r["trendPhase"], regime_quad)
                sig = "HOLD"
                if r["trendPhase"] == 1 and r["qualityScore"] >= 55:
                    sig = "BUY" if r["tradeBreakUp"] or r["trendTransUp"] else "ACCUMULATE"
                elif r["trendPhase"] == -1 and r["qualityScore"] >= 55:
                    sig = "SELL" if r["tradeBreakDown"] or r["trendTransDown"] else "REDUCE"
                elif r["trendPhase"] == 0:
                    sig = "WATCH"
                results.append({
                    "ticker": t, "price": round(pr, 2), "signal": sig, "grade": grade,
                    "strength": round(r["qualityScore"] * 0.6 + r["activityScore"] * 0.4 + (15 if transition else 0), 1),
                    "quality": round(r["qualityScore"], 1), "activity": round(r["activityScore"], 1),
                    "compression": round(r["compressionScore"], 1), "trend_phase": r["trendPhase"],
                    "trade_trr": round(r["tradeTRR"], 2), "trade_lrr": round(r["tradeLRR"], 2),
                    "trend_trr": round(r["trendTRR"], 2), "trend_lrr": round(r["trendLRR"], 2),
                    "tail_trr": round(r["tailTRR"], 2), "tail_lrr": round(r["tailLRR"], 2),
                    "transition": transition, "regime_alignment": alignment,
                    "vol_regime": "EXPANDING" if r["volRegimeConfirm"] else "NORMAL",
                    "timestamp": datetime.now().isoformat(),
                })
            except Exception as e:
                logger.warning(f"Momentum scan fail {t}: {e}")
                results.append({"ticker": t, "error": str(e)})
        results.sort(key=lambda x: x.get("strength", 0), reverse=True)
        return results


def get_momentum_snapshot(prices=None, regime_quad="Q2"):
    tracker = MomentumTracker()
    return tracker.scan(prices=prices, regime_quad=regime_quad)