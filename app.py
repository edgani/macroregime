"""
MacroRegime Pro v5 — Full Restoration
======================================
Restores everything lost in v4.0 collapse:
- IHSG native engine (USD/IDR, asing flow, bank health, commodity spillover)
- Dual-horizon quad (structural + monthly, divergence state)
- Rotation engine (best trade, confirm/invalidate, petrodollar/EM flow)
- IHSG + US stock rankings
- Scenario Lab (what breaks this?)
- Execution mode (Add on Reset / Wait Reclaim / Defensive only)
- Multi-market: US, IHSG, FX, Commodities, Crypto
- Laypeople-readable: plain language throughout

Free data: yfinance + FRED public CSV
Run: streamlit run macro_regime_pro_v5.py
"""
from __future__ import annotations
import datetime,math,os
from io import StringIO
from typing import Dict,List,Optional,Tuple
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MacroRegime Pro",page_icon="🧭",layout="wide",initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html,[class*="css"]{font-family:'DM Sans',sans-serif}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:.5rem;padding-bottom:2rem}
.qb{display:inline-block;padding:3px 12px;border-radius:20px;font-family:'DM Mono',monospace;font-weight:500;font-size:11px;letter-spacing:.05em}
.q1{background:#d4edda;color:#155724}.q2{background:#fff3cd;color:#856404}
.q3{background:#ffeeba;color:#7d4e00}.q4{background:#f8d7da;color:#721c24}
.qunk{background:#e2e3e5;color:#495057}
.mc{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px 16px;margin-bottom:6px}
.mc .lb{font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:3px}
.mc .vl{font-family:'Syne',sans-serif;font-size:20px;font-weight:700;line-height:1.1;margin-bottom:1px}
.mc .sb{font-size:11px;opacity:.5}
.good{color:#3dbb6c}.warn{color:#e5a020}.bad{color:#e05252}.neu{color:#888}
.sh{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.35;padding:10px 0 4px;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:10px}
.proxy-b{padding:8px 14px;border-radius:8px;font-size:12px;margin-bottom:12px;background:rgba(229,160,32,0.12);border:1px solid rgba(229,160,32,0.3);color:#e5a020}
.real-b{padding:8px 14px;border-radius:8px;font-size:12px;margin-bottom:12px;background:rgba(61,187,108,0.08);border:1px solid rgba(61,187,108,0.2);color:#3dbb6c}
.rot-card{padding:12px 14px;border-radius:10px;margin-bottom:8px;border-left:4px solid}
.rot-best{background:rgba(61,187,108,0.08);border-left-color:#3dbb6c}
.rot-safe{background:rgba(229,160,32,0.08);border-left-color:#e5a020}
.rot-avoid{background:rgba(224,82,82,0.08);border-left-color:#e05252}
.gb{margin-bottom:8px}
.gb .gr{display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px}
.gb .bg{height:5px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden}
.gb .fl{height:100%;border-radius:3px}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:600;margin:1px;letter-spacing:.04em}
.tag-g{background:rgba(61,187,108,0.15);color:#3dbb6c}
.tag-r{background:rgba(224,82,82,0.15);color:#e05252}
.tag-y{background:rgba(229,160,32,0.15);color:#e5a020}
.tag-b{background:rgba(100,150,255,0.15);color:#6496ff}
</style>
""",unsafe_allow_html=True)

# ── Constants ─────────────────────────────────────────────────────────────────
TTL=3600

FRED_SERIES={"INDPRO":"INDPRO","PAYEMS":"PAYEMS","UNRATE":"UNRATE","ICSA":"ICSA",
    "RSAFS":"RSAFS","HOUST":"HOUST","PERMIT":"PERMIT","ISM":"NAPMNOI","LEI":"USSLIND",
    "UMCSENT":"UMCSENT","CPI":"CPIAUCSL","CORECPI":"CPILFESL","COREPCE":"PCEPILFE",
    "DGS2":"DGS2","DGS10":"DGS10","DGS30":"DGS30","REAL10":"DFII10","BREAKEVEN":"T5YIE",
    "FEDFUNDS":"FEDFUNDS","HYOAS":"BAMLH0A0HYM2","IGSPR":"BAMLC0A0CM"}

US_TICKERS=["SPY","QQQ","IWM","RSP","MDY","XLE","XLF","XLI","XLB","XLK","XLV","XLY",
    "XLP","XLU","XLRE","XLC","HYG","LQD","TLT","IEF","SHY","GLD","GC=F","SI=F",
    "HG=F","CL=F","NG=F","UUP","EEM","EFA","^VIX","^VXV","^VIX9D","BTC-USD","ETH-USD",
    "SOL-USD","XRP-USD","AAPL","MSFT","NVDA","AMZN","META","GOOGL","TSLA","AVGO","AMD"]

IHSG_TICKERS=["^JKSE","IDR=X","BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK",
    "TLKM.JK","ASII.JK","ADRO.JK","PTBA.JK","ANTM.JK","INCO.JK","MDKA.JK",
    "ICBP.JK","INDF.JK","KLBF.JK","AMRT.JK","ACES.JK","CTRA.JK","BSDE.JK",
    "JSMR.JK","PGAS.JK","EXCL.JK","ISAT.JK","HEAL.JK","MIKA.JK","AADI.JK",
    "ITMG.JK","HRUM.JK","TINS.JK","BRMS.JK","MEDC.JK","PGEO.JK","UNTR.JK"]

FX_TICKERS=["EURUSD=X","GBPUSD=X","AUDUSD=X","NZDUSD=X","JPY=X","CHF=X","CAD=X",
    "IDR=X","CNH=X","SGD=X","EURJPY=X","GBPJPY=X","AUDJPY=X"]

COMMODITY_TICKERS=["GC=F","SI=F","PL=F","CL=F","BZ=F","NG=F","HG=F","ZC=F","ZW=F","ZS=F",
    "DBC","GSG","DBA","DBB","URA"]

IHSG_BUCKETS={
    "Bank":["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK","BBTN.JK"],
    "Batu Bara/Energi":["ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","AADI.JK","BUMI.JK","MEDC.JK","PGEO.JK","AKRA.JK"],
    "Logam":["ANTM.JK","INCO.JK","MDKA.JK","TINS.JK","BRMS.JK"],
    "Telco/Infra":["TLKM.JK","EXCL.JK","ISAT.JK","JSMR.JK","PGAS.JK"],
    "Consumer":["ICBP.JK","INDF.JK","MYOR.JK","KLBF.JK","AMRT.JK","ACES.JK","ASII.JK"],
    "Properti/Health":["CTRA.JK","BSDE.JK","HEAL.JK","MIKA.JK","PWON.JK","SILO.JK"],
}

QUAD_META={
    "Q1":{"label":"Risk-On Goldilocks","desc":"Growth naik, inflasi turun/stabil. Terbaik untuk risk assets.",
          "color":"#d4edda","text":"#155724",
          "best":["XAUUSD / GLD","EEM (EM Equities)","IHSG (selective)","QQQ / Growth tech"],
          "safe":["Gold (GLD)","Short-duration (SHY)"],
          "avoid":["Energy commodities","USD longs","Defensives"],
          "confirm":"EEM > SPY 1M, breadth lebar, VIX < 18, hy spreads ketat.",
          "invalidate":"VIX spike >25, HY spreads lebar, USD re-accelerates."},
    "Q2":{"label":"Reflation / Boom","desc":"Growth dan inflasi sama-sama naik. Cyclicals dan real assets menang.",
          "color":"#fff3cd","text":"#856404",
          "best":["WTI / XLE (energi)","Copper / Materials (XLB)","IHSG exporter","Financials (XLF)"],
          "safe":["TIPS / inflation-linked","Commodity FX"],
          "avoid":["Long bonds (TLT)","High-multiple tech","IG credit"],
          "confirm":"Oil bertahan, commodities lebar, yields naik teratur.",
          "invalidate":"Oil rollback cepat, ISM turun balik bawah 50, tightening bites."},
    "Q3":{"label":"Stagflation","desc":"Growth melambat, inflasi masih tinggi. Quad paling sulit. Gold dan USD menang.",
          "color":"#ffeeba","text":"#7d4e00",
          "best":["Gold / XAUUSD (GLD, GC=F)","USD / Cash (UUP, SHY)","Energi (XLE) selektif","Short equity ideas"],
          "safe":["Gold (GLD)","USD (UUP)","T-bills (SHY, BIL)"],
          "avoid":["Rate-sensitive tech (QQQ)","Consumer disc (XLY)","EM (EEM)","Long bonds (TLT)","Junk credit (HYG)"],
          "confirm":"Gold > SPY 1M, USD kuat, ISM < 50, claims naik.",
          "invalidate":"Fed pivot kredibel, ISM rebound, credit spreads ketat kembali."},
    "Q4":{"label":"Deflasi / Resesi","desc":"Growth dan inflasi sama-sama turun. Obligasi panjang dan defensif menang.",
          "color":"#f8d7da","text":"#721c24",
          "best":["Long bonds (TLT)","Gold (GLD)","Defensives (XLP, XLU, XLV)","USD (UUP)"],
          "safe":["Treasury bonds (TLT)","Gold (GLD)"],
          "avoid":["Commodities (XLE, XLB)","Cyclicals (XLI, XLY)","Junk credit (HYG)","Small caps (IWM)","EM (EEM)"],
          "confirm":"Yields turun, credit ketat, defensifs outperform, TLT naik.",
          "invalidate":"Fed cut + fiscal stimulus besar, ISM rebound dari <45."},
}

ROUTE_META={
    "XAUUSD":{"why":"Hard-asset hedge paling bersih saat inflation pulse naik tapi growth rapuh.",
               "confirm":"Real yields tidak meledak dan breadth belum sembuh.",
               "invalidate":"Rates dan dollar sama-sama naik keras."},
    "USD":{"why":"Kas safety paling bersih saat dollar dan funding stress mendominasi.",
           "confirm":"DXY tetap kuat, breadth tetap lemah.",
           "invalidate":"Breadth melebar dan yields lebih tenang."},
    "TLT":{"why":"Duration jadi tempat kabur kalau growth scare menang.",
           "confirm":"Yields mulai adem dan credit tidak memburuk.",
           "invalidate":"Long-end pain lanjut."},
    "Defensives":{"why":"Cash-flow defensives lebih bersih saat broad beta belum sehat.",
                  "confirm":"Breadth tetap sempit dan quality outperforms.",
                  "invalidate":"Equal-weight dan small caps ikut konfirmasi."},
    "WTI":{"why":"Shock inflasi / supply masih dominan.",
           "confirm":"Oil impulse bertahan dan de-escalation belum kredibel.",
           "invalidate":"Oil rollback cepat."},
    "EEM":{"why":"Broad EM catch-up mulai hidup, bukan cuma selective exporter.",
           "confirm":"EEM > SPY di 1M dan 3M sambil USD adem.",
           "invalidate":"USD re-accelerates."},
    "IHSG":{"why":"Selective exporter + bank quality dalam EM. IDR stable.",
             "confirm":"IHSG > SPY dan commodity chain belum pecah. Asing nett beli.",
             "invalidate":"USD naik lagi dan commodity leadership luntur. Asing jual."},
}

# ── Math helpers ──────────────────────────────────────────────────────────────
def _s(s)->pd.Series:
    if s is None: return pd.Series(dtype=float)
    return pd.to_numeric(s if isinstance(s,pd.Series) else pd.Series(s),errors="coerce").dropna()
def last(s)->float:
    s=_s(s); return float(s.iloc[-1]) if not s.empty else float("nan")
def ret_n(s,n:int)->float:
    s=_s(s)
    if len(s)<n+1: return float("nan")
    b=float(s.iloc[-(n+1)])
    if not math.isfinite(b) or b==0: return float("nan")
    return float(s.iloc[-1]/b-1.0)
def delta_n(s,n:int)->float:
    s=_s(s)
    if len(s)<n+1: return float("nan")
    return float(s.iloc[-1]-s.iloc[-(n+1)])
def roc_acc(s,n:int,lag:int)->Optional[bool]:
    s=_s(s)
    if len(s)<n+lag+2: return None
    c=ret_n(s,n); p=ret_n(s.iloc[:-lag],n)
    if not(math.isfinite(c) and math.isfinite(p)): return None
    return c>p
def ts(s)->float:  # trend score 0-1
    s=_s(s)
    if len(s)<50: return 0.5
    px=float(s.iloc[-1]); m20=float(s.rolling(20).mean().iloc[-1]); m50=float(s.rolling(50).mean().iloc[-1])
    return 0.5*(1 if px>m20 else 0)+0.5*(1 if px>m50 else 0)
def th(x:float,sc:float)->float:
    if not math.isfinite(x): return 0.0
    return float(math.tanh(x/max(sc,1e-9)))
def clamp(x,lo=0.0,hi=1.0)->float: return max(lo,min(hi,float(x or 0)))
def nm(*v)->float:
    a=[x for x in v if math.isfinite(x)]
    return float(np.mean(a)) if a else 0.0
def pct(v,d=1)->str:
    if not math.isfinite(v): return "—"
    return f"{v*100:+.{d}f}%"
def num(v,d=2)->str:
    if not math.isfinite(v): return "—"
    return f"{v:.{d}f}"
def acc_txt(flag:Optional[bool])->str:
    if flag is True: return "▲ Accelerating"
    if flag is False: return "▼ Decelerating"
    return "– Unknown"
def score_color(v:float,hi=0.62,lo=0.38)->str:
    return "good" if v>=hi else("bad" if v<=lo else "warn")

# ── Data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=TTL,show_spinner=False)
def fetch_fred(sid:str)->pd.Series:
    key=os.environ.get("FRED_API_KEY","")
    try: key=key or st.secrets.get("FRED_API_KEY","")
    except: pass
    urls=[f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"]
    if key: urls.append(f"https://api.stlouisfed.org/fred/series/observations?series_id={sid}&api_key={key}&file_type=json")
    sess=requests.Session(); sess.headers.update({"User-Agent":"Mozilla/5.0 MacroRegimePro/5.0"})
    for url in urls:
        try:
            r=sess.get(url,timeout=10); r.raise_for_status()
            if "fredgraph" in url:
                df=pd.read_csv(StringIO(r.text),index_col=0,parse_dates=True)
                s=pd.to_numeric(df.iloc[:,0],errors="coerce").dropna()
                if len(s)>0: return s
            else:
                import json; data=json.loads(r.text)
                obs=data.get("observations",[])
                if obs:
                    idx=pd.to_datetime([o["date"] for o in obs])
                    vals=pd.to_numeric([o["value"] for o in obs],errors="coerce")
                    s=pd.Series(vals.values,index=idx).dropna()
                    if len(s)>0: return s
        except: continue
    return pd.Series(dtype=float)

@st.cache_data(ttl=TTL,show_spinner=False)
def fetch_prices(tickers:tuple,period:str="2y")->Dict[str,pd.Series]:
    try:
        import yfinance as yf
        raw=yf.download(list(tickers),period=period,auto_adjust=False,progress=False,threads=True,ignore_tz=True)
        out:Dict[str,pd.Series]={}
        if isinstance(raw.columns,pd.MultiIndex):
            close=raw.get("Close",pd.DataFrame())
            if isinstance(close,pd.DataFrame):
                for t in tickers:
                    if t in close.columns:
                        s=close[t].dropna()
                        if len(s)>5: out[t]=s
        return out
    except: return {}

# ── Price-based fallback macro proxies ───────────────────────────────────────
def build_proxy(prices:Dict[str,pd.Series])->Dict:
    spy_3m=ret_n(prices.get("SPY",pd.Series()),63); xli_3m=ret_n(prices.get("XLI",pd.Series()),63)
    xly_3m=ret_n(prices.get("XLY",pd.Series()),63); iwm_3m=ret_n(prices.get("IWM",pd.Series()),63)
    uup_3m=ret_n(prices.get("UUP",pd.Series()),63); oil_3m=ret_n(prices.get("CL=F",pd.Series()),63)
    gold_3m=ret_n(prices.get("GC=F",pd.Series()),63); tlt_1m=ret_n(prices.get("TLT",pd.Series()),21)
    hyg_1m=ret_n(prices.get("HYG",pd.Series()),21); cop_3m=ret_n(prices.get("HG=F",pd.Series()),63)
    def nf(x,d=0.0): return float(np.nan_to_num(x,nan=d))
    return dict(
        indpro_yoy=nf(0.55*xli_3m+0.45*spy_3m), retail_yoy=nf(0.60*xly_3m+0.40*spy_3m),
        payrolls_yoy=nf(0.50*iwm_3m+0.50*spy_3m), unrate_3m_delta=nf(-0.10*iwm_3m),
        claims_13w_delta=nf(-10.0*iwm_3m), ism_last=50.0+20.0*nf(xli_3m),
        housing_yoy=nf(iwm_3m*0.6), permits_yoy=nf(iwm_3m*0.5),
        lei_3m=nf(0.40*xli_3m+0.30*spy_3m+0.30*iwm_3m), umcsent_last=75.0+100.0*nf(xly_3m),
        cpi_yoy=nf(0.025+0.35*oil_3m+0.05*gold_3m), cpi_mom=nf(oil_3m/12),
        corecpi_yoy=nf(0.023+0.15*oil_3m-0.05*uup_3m), corepce_yoy=nf(0.022+0.12*oil_3m-0.04*uup_3m),
        breakeven=2.2+1.2*nf(oil_3m)+0.4*nf(gold_3m)-0.2*nf(uup_3m), breakeven_1m=nf(0.15*oil_3m/3),
        real_10y=1.8-30.0*nf(tlt_1m) if math.isfinite(tlt_1m) else 1.8,
        policy_rate=4.33, policy_rate_3m=0.0,
        dgs2=float("nan"),dgs10=float("nan"),dgs30=float("nan"),
        spread_2s10s=float("nan"),spread_10s30s=float("nan"),
        spread_2s10s_3m=float("nan"),yield_curve_state="Unknown (proxy)",yield_curve_uninverting=False,
        hy_oas=350.0-1200.0*nf(hyg_1m), hy_oas_1m=-200.0*nf(hyg_1m),
        ig_oas=float("nan"), ig_oas_1m=float("nan"),
        copper_gold_ratio_3m=nf(cop_3m-gold_3m) if(math.isfinite(cop_3m) and math.isfinite(gold_3m)) else 0.0,
        indpro_acc=None, payrolls_acc=None, retail_acc=None, lei_acc=None, cpi_acc=None, corepce_acc=None,
    )

# ── Macro features ────────────────────────────────────────────────────────────
def build_macro(fred:Dict[str,pd.Series],prices:Dict[str,pd.Series])->Dict:
    f=build_proxy(prices); loaded=0; total=0
    def ov(k,fk,fn,*args):
        nonlocal loaded,total; total+=1
        s=fred.get(k,pd.Series())
        if not _s(s).empty:
            v=fn(s,*args)
            if math.isfinite(v): f[fk]=v; loaded+=1; return True
        return False
    ov("INDPRO","indpro_yoy",ret_n,12); ov("PAYEMS","payrolls_yoy",ret_n,12)
    ov("PAYEMS","payrolls_mom",ret_n,1); ov("UNRATE","unrate",last)
    ov("UNRATE","unrate_3m_delta",delta_n,3); ov("UNRATE","unrate_6m_delta",delta_n,6)
    ov("ICSA","claims_13w_delta",delta_n,13); ov("ICSA","claims_last",last)
    ov("ISM","ism_last",last); ov("RSAFS","retail_yoy",ret_n,12)
    ov("HOUST","housing_yoy",ret_n,12); ov("PERMIT","permits_yoy",ret_n,12)
    ov("LEI","lei_3m",ret_n,3); ov("UMCSENT","umcsent_last",last)
    ov("CPI","cpi_yoy",ret_n,12); ov("CPI","cpi_mom",ret_n,1)
    ov("CORECPI","corecpi_yoy",ret_n,12); ov("COREPCE","corepce_yoy",ret_n,12)
    ov("BREAKEVEN","breakeven",last); ov("BREAKEVEN","breakeven_1m",delta_n,1)
    ov("REAL10","real_10y",last); ov("FEDFUNDS","policy_rate",last)
    ov("FEDFUNDS","policy_rate_3m",delta_n,3); ov("DGS2","dgs2",last)
    ov("DGS10","dgs10",last); ov("DGS30","dgs30",last)
    ov("HYOAS","hy_oas",last); ov("HYOAS","hy_oas_1m",delta_n,21)
    ov("IGSPR","ig_oas",last); ov("IGSPR","ig_oas_1m",delta_n,21)
    d2=f.get("dgs2",float("nan")); d10=f.get("dgs10",float("nan")); d30=f.get("dgs30",float("nan"))
    if math.isfinite(d2) and math.isfinite(d10):
        sp=d10-d2; f["spread_2s10s"]=sp
        f["yield_curve_state"]="Inverted" if sp<-0.10 else("Flat" if sp<0.25 else("Normal" if sp<1.50 else "Steep"))
        s2=_s(fred.get("DGS2",pd.Series())); s10=_s(fred.get("DGS10",pd.Series()))
        if len(s2)>63 and len(s10)>63:
            a2,a10=s2.align(s10,join="inner"); sp_ts=a10-a2
            f["spread_2s10s_3m"]=delta_n(sp_ts,63)
            f["yield_curve_uninverting"]=(math.isfinite(f.get("spread_2s10s_3m",float("nan"))) and f.get("spread_2s10s_3m",0)>0.20 and sp>-0.25)
    if math.isfinite(d10) and math.isfinite(d30): f["spread_10s30s"]=d30-d10
    f["indpro_acc"]=roc_acc(fred.get("INDPRO",pd.Series()),12,3)
    f["payrolls_acc"]=roc_acc(fred.get("PAYEMS",pd.Series()),12,3)
    f["retail_acc"]=roc_acc(fred.get("RSAFS",pd.Series()),12,3)
    f["lei_acc"]=roc_acc(fred.get("LEI",pd.Series()),3,2)
    f["cpi_acc"]=roc_acc(fred.get("CPI",pd.Series()),12,3)
    f["corepce_acc"]=roc_acc(fred.get("COREPCE",pd.Series()),12,3)
    for t in ["SPY","QQQ","IWM","RSP","UUP","TLT","EEM","EFA","GLD","HYG","LQD",
              "XLE","XLI","XLY","XLP","XLB","XLK","XLF","CL=F","GC=F","HG=F","SI=F"]:
        s=prices.get(t,pd.Series())
        tk=t.replace("^","").replace("=F","f").lower()
        f[f"{tk}_1m"]=ret_n(s,21); f[f"{tk}_3m"]=ret_n(s,63); f[f"{tk}_ts"]=ts(s)
    cop=prices.get("HG=F",pd.Series()); gld=prices.get("GC=F",pd.Series())
    if not _s(cop).empty and not _s(gld).empty:
        c2,g2=_s(cop).align(_s(gld),join="inner")
        if len(c2)>63:
            cg=c2/g2; f["copper_gold_ratio_3m"]=ret_n(cg,63)
    vix_s=prices.get("^VIX",pd.Series()); vxv_s=prices.get("^VXV",pd.Series())
    f["vix_last"]=last(vix_s); f["vix_1m"]=delta_n(vix_s,21)
    if not _s(vix_s).empty and not _s(vxv_s).empty:
        v,vxv=_s(vix_s).align(_s(vxv_s),join="inner")
        if len(v)>5:
            r=float(v.iloc[-1])/float(vxv.iloc[-1]); f["vix_vxv_ratio"]=r
            f["vix_term_state"]="Contango (calm)" if r<0.90 else("Flat (neutral)" if r<1.00 else "Backwardation (fear)")
        else: f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"
    else: f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"
    f["_fred_loaded"]=loaded; f["_fred_total"]=total; f["_proxy_share"]=1.0-(loaded/max(total,1))
    return f

# ── Dual-horizon quad engine ──────────────────────────────────────────────────
def _score_quad(g_level,g_mom,i_level,i_mom,sf,inf_sh,monthly=False)->Tuple[Dict,str,str,float]:
    oil_adj=float(np.nan_to_num(g_level*0.0,nan=0.0))  # placeholder
    g_core=0.60*g_level+0.40*g_mom; i_core=0.70*i_level+0.30*i_mom
    raw={"Q1":+g_core-i_core*0.8,"Q2":+g_core+i_core*0.8,
         "Q3":-g_core+i_core*1.2+0.10*sf+0.08*max(0.0,inf_sh),
         "Q4":-g_core-i_core*0.8+0.08*sf}
    if monthly:
        raw["Q3"]+=0.05*max(0.0,inf_sh); raw["Q2"]+=0.04*max(0.0,inf_sh)
    raw["Q1"]-=0.08*sf; raw["Q2"]-=0.05*sf
    arr=np.array(list(raw.values()),dtype=float); exp=np.exp(arr-arr.max()); prbs=(exp/exp.sum()).tolist()
    probs=dict(zip(raw.keys(),prbs))
    ordered=sorted(probs.items(),key=lambda kv:kv[1],reverse=True)
    quad=ordered[0][0]; top_p=ordered[0][1]; next_q=ordered[1][0]; margin=top_p-ordered[1][1]
    conf=clamp(top_p*0.75+margin*0.25)
    return probs,quad,next_q,conf

def build_quad(f:Dict)->Dict:
    oil_3m=f.get("clf_3m",0.0);
    if not math.isfinite(oil_3m): oil_3m=0.0
    gld_3m=f.get("gld_3m",0.0);
    if not math.isfinite(gld_3m): gld_3m=0.0
    uup_3m=f.get("uup_3m",0.0);
    if not math.isfinite(uup_3m): uup_3m=0.0

    g_inputs=[th(f.get("indpro_yoy",0)-0.020,0.050),th(f.get("retail_yoy",0)-0.030,0.060),
        th(f.get("payrolls_yoy",0)-0.015,0.030),th((f.get("ism_last",50)-50)/100,0.040),
        th(-f.get("unrate_3m_delta",0),0.120),th(-f.get("claims_13w_delta",0)/40,0.600),
        th(f.get("lei_3m",0),0.030),th(f.get("copper_gold_ratio_3m",0),0.120),
        th(f.get("eem_3m",0) if math.isfinite(f.get("eem_3m",float("nan"))) else 0,0.120)]
    g_mom_inputs=[th(f.get("xli_3m",0),0.080),th(f.get("iwm_3m",0),0.080),
        th(f.get("spy_3m",0),0.080),th(f.get("copper_gold_ratio_3m",0),0.100),
        th(-f.get("unrate_3m_delta",0),0.100)]
    yc=f.get("yield_curve_state","")
    yc_adj=-0.12 if "Inverted" in yc else(-0.05 if f.get("yield_curve_uninverting") else 0.06 if"Normal" in yc or"Steep" in yc else 0.0)
    hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    cred_adj=(clamp((hy-300)/600)*-0.15 if math.isfinite(hy) else 0.0)+(clamp((ig-80)/200)*-0.08 if math.isfinite(ig) else 0.0)
    g_level=nm(*g_inputs)+yc_adj+cred_adj; g_mom=nm(*g_mom_inputs)

    core_inf=f.get("corepce_yoy",f.get("corecpi_yoy",0.023)); headline=f.get("cpi_yoy",0.025)
    i_inputs=[th(headline-0.025,0.020),th(core_inf-0.025,0.015),
        th((f.get("breakeven",2.2)-2.2)/2.0,0.300),th(oil_3m,0.250),th(gld_3m,0.180)]
    i_mom_inputs=[th(oil_3m/3,0.120),th((f.get("breakeven",2.2)-2.2)/2.0,0.240),
        th(f.get("breakeven_1m",0),0.080),th(-uup_3m,0.100)]
    i_level=nm(*i_inputs); i_mom=nm(*i_mom_inputs)

    sf=sum([1 if math.isfinite(f.get("unrate_3m_delta",float("nan"))) and f.get("unrate_3m_delta",0)>0.05 else 0,
        1 if math.isfinite(f.get("claims_13w_delta",float("nan"))) and f.get("claims_13w_delta",0)>0 else 0,
        1 if math.isfinite(f.get("ism_last",float("nan"))) and f.get("ism_last",50)<50 else 0,
        1 if math.isfinite(f.get("housing_yoy",float("nan"))) and f.get("housing_yoy",0)<-0.05 else 0])/4.0
    inf_sh=max(0.0,th(oil_3m,0.25))*0.5+max(0.0,th(i_mom,0.3))*0.5

    # Structural (3-6 month horizon)
    s_probs,s_quad,s_next,s_conf=_score_quad(g_level,g_mom,i_level,i_mom,sf,inf_sh,monthly=False)
    # Monthly (4-6 week horizon) — more responsive to recent momentum
    g_m=nm(*g_mom_inputs)*1.2; i_m=nm(*i_mom_inputs)*1.2
    m_probs,m_quad,m_next,m_conf=_score_quad(g_m,g_mom,i_m,i_mom,sf,inf_sh,monthly=True)

    div="aligned" if s_quad==m_quad else "divergent"
    operating=f"Aligned {s_quad}" if div=="aligned" else f"Monthly {m_quad} inside Structural {s_quad}"

    ordered=sorted(s_probs.items(),key=lambda kv:kv[1],reverse=True)
    margin=ordered[0][1]-ordered[1][1]
    flip_h=clamp(0.30*(1-margin)+0.20*abs(g_mom)+0.20*abs(i_mom)+0.15*(1.0 if"Inverted"in yc else 0.0)+0.10*sf)

    g_acc=f.get("indpro_acc") or f.get("payrolls_acc")
    if g_acc is None: g_acc=(g_level>0)
    i_acc=f.get("cpi_acc") or f.get("corepce_acc")
    if i_acc is None: i_acc=(i_level>0)

    return dict(quad=s_quad,probs=s_probs,next_quad=s_next,confidence=s_conf,
                monthly_quad=m_quad,monthly_probs=m_probs,monthly_next=m_next,monthly_conf=m_conf,
                divergence=div,operating=operating,flip_hazard=flip_h,
                g_level=g_level,g_mom=g_mom,i_level=i_level,i_mom=i_mom,
                g_core=0.60*g_level+0.40*g_mom,i_core=0.70*i_level+0.30*i_mom,
                growth_acc=g_acc,infl_acc=i_acc,slowdown_flags=sf,inf_shock=inf_sh)

# ── Rotation engine ───────────────────────────────────────────────────────────
def build_rotation(q:Dict,h:Dict,f:Dict)->Dict:
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; conf=q["confidence"]
    uup_3m=f.get("uup_3m",0.0);
    if not math.isfinite(uup_3m): uup_3m=0.0
    oil_3m=f.get("clf_3m",0.0);
    if not math.isfinite(oil_3m): oil_3m=0.0
    gld_3m=f.get("gld_3m",0.0);
    if not math.isfinite(gld_3m): gld_3m=0.0
    hy=f.get("hy_oas",350.0); g_core=q.get("g_core",0.0); i_core=q.get("i_core",0.0)

    # Safe harbor scores — what to hold defensively
    safe_scores={"XAUUSD":{"Q1":0.30,"Q2":0.35,"Q3":0.72,"Q4":0.60}.get(s_quad,0.5),
                 "USD":{"Q1":0.35,"Q2":0.30,"Q3":0.50,"Q4":0.78}.get(s_quad,0.5),
                 "TLT":{"Q1":0.30,"Q2":0.28,"Q3":0.46,"Q4":0.74}.get(s_quad,0.5),
                 "Defensives":{"Q1":0.35,"Q2":0.30,"Q3":0.52,"Q4":0.64}.get(s_quad,0.5)}
    # Boost gold if inflation shock
    safe_scores["XAUUSD"]+=0.10*q.get("inf_shock",0.0)
    # Reduce TLT if yield curve inverted
    if "Inverted" in f.get("yield_curve_state",""):
        safe_scores["TLT"]*=0.85

    # Beneficiary scores — what to own for return
    ben_scores={"WTI":{"Q1":0.40,"Q2":0.60,"Q3":0.70,"Q4":0.28}.get(s_quad,0.5),
                "EEM":{"Q1":0.62,"Q2":0.68,"Q3":0.42,"Q4":0.30}.get(s_quad,0.5),
                "IHSG":{"Q1":0.58,"Q2":0.64,"Q3":0.56,"Q4":0.32}.get(s_quad,0.5),
                "XAUUSD":{"Q1":0.42,"Q2":0.46,"Q3":0.74,"Q4":0.62}.get(s_quad,0.5)}
    # Monthly overlay adjustments
    if m_quad!=s_quad:
        ben_scores["IHSG"]*=(1.10 if m_quad in("Q1","Q2") else 0.90)
        ben_scores["EEM"]*=(1.08 if m_quad in("Q1","Q2") else 0.92)
    # USD pressure on EM
    usd_penalty=clamp(uup_3m*5)
    ben_scores["IHSG"]*=(1.0-0.25*usd_penalty); ben_scores["EEM"]*=(1.0-0.20*usd_penalty)
    # Oil boost
    if oil_3m>0.05: ben_scores["WTI"]*=1.10; ben_scores["IHSG"]*=1.05

    # Credit stress dampens everything
    if math.isfinite(hy) and hy>400:
        for k in ben_scores: ben_scores[k]*=0.90

    safe_sorted=sorted(safe_scores.items(),key=lambda x:x[1],reverse=True)
    ben_sorted=sorted(ben_scores.items(),key=lambda x:x[1],reverse=True)
    top_safe=safe_sorted[0][0]; top_ben=ben_sorted[0][0]

    # EM rotation signal
    em_score=clamp(0.35*clamp(0.5+ret_n(f.get("eem_s",pd.Series()),21)*5 if False else 0.5)+0.30*ben_scores["EEM"]+0.35*(1-usd_penalty))
    em_state="Accumulate" if em_score>0.60 else("Wait" if em_score>0.45 else "Avoid")

    best_meta=ROUTE_META.get(top_ben,ROUTE_META["XAUUSD"])
    safe_meta=ROUTE_META.get(top_safe,ROUTE_META["USD"])

    # Scenario: what breaks this?
    scenarios=[
        {"name":"Fed pivot credibel","impact":"Q3→Q4: Gold bertahan, tapi growth scare menang. Dollar lemah, TLT naik.","prob":clamp(q.get("flip_hazard",0.3)*0.6)},
        {"name":"USD re-accelerates","impact":"EM crash (EEM, IHSG turun), commodity FX tertekan, goldilocks mati.","prob":clamp(usd_penalty*0.8+0.1)},
        {"name":"Oil supply shock naik","impact":"Q2/Q3 inflation deepens. Gold dan WTI naik, TLT hancur, EM pain.","prob":clamp(max(0,oil_3m)*2+0.1)},
        {"name":"ISM rebound ke >52","impact":"Q3→Q2 atau Q3→Q1: risk-on recovery. EEM, IHSG, cyclicals hidup.","prob":clamp(1-q.get("slowdown_flags",0.5))},
        {"name":"Credit stress / HY melebar >500bps","impact":"Semua risk assets turun. Q4 scare. Cash adalah posisi.","prob":clamp((hy-350)/400 if math.isfinite(hy) else 0.2)},
    ]
    scenarios.sort(key=lambda x:x["prob"],reverse=True)

    return dict(top_safe=top_safe,top_ben=top_ben,safe_score=safe_sorted[0][1],
                ben_score=ben_sorted[0][1],safe_meta=safe_meta,best_meta=best_meta,
                safe_rows=[{"route":k,"score":v} for k,v in safe_sorted[:3]],
                ben_rows=[{"route":k,"score":v} for k,v in ben_sorted[:3]],
                em_score=em_score,em_state=em_state,scenarios=scenarios)

# ── IHSG native engine ────────────────────────────────────────────────────────
def build_ihsg(prices:Dict[str,pd.Series],q:Dict,f:Dict)->Dict:
    jkse=prices.get("^JKSE",pd.Series())
    idr=prices.get("IDR=X",pd.Series())   # USD/IDR — naik = IDR lemah (buruk untuk IHSG)
    spy=prices.get("SPY",pd.Series())

    jkse_1m=ret_n(jkse,21); jkse_3m=ret_n(jkse,63); jkse_6m=ret_n(jkse,126)
    spy_1m=ret_n(spy,21); spy_3m=ret_n(spy,63)
    usd_idr_1m=ret_n(idr,21); usd_idr_3m=ret_n(idr,63)
    tlt_1m=f.get("tlt_1m",0.0)

    # Core IHSG-specific factors
    usd_idr_pressure=clamp(0.5+(usd_idr_1m/0.08)) if math.isfinite(usd_idr_1m) else 0.5
    idr_weakening=math.isfinite(usd_idr_1m) and usd_idr_1m>0.01

    # Bank health (BBCA, BBRI, BMRI are IHSG backbone)
    bank_scores=[]
    for t in ["BBCA.JK","BBRI.JK","BMRI.JK","BBNI.JK","BRIS.JK"]:
        s=prices.get(t,pd.Series())
        r=ret_n(s,21)
        if math.isfinite(r): bank_scores.append(r)
    bank_health=clamp(0.5+np.mean(bank_scores)/0.06) if bank_scores else 0.5

    # Commodity spillover (batubara, logam — IHSG sangat terpengaruh)
    coal_scores=[]
    for t in ["ADRO.JK","PTBA.JK","ITMG.JK","HRUM.JK","AADI.JK"]:
        s=prices.get(t,pd.Series())
        r=ret_n(s,21)
        if math.isfinite(r): coal_scores.append(r)
    metal_scores=[]
    for t in ["ANTM.JK","INCO.JK","MDKA.JK","TINS.JK"]:
        s=prices.get(t,pd.Series())
        r=ret_n(s,21)
        if math.isfinite(r): metal_scores.append(r)
    all_comm=(coal_scores+metal_scores)
    commodity_spillover=clamp(0.5+np.mean(all_comm)/0.07) if all_comm else 0.5

    # Foreign flow proxy (IHSG vs SPY relative momentum = asing masuk/keluar)
    rel_1m=(jkse_1m-spy_1m) if(math.isfinite(jkse_1m) and math.isfinite(spy_1m)) else 0.0
    foreign_flow=clamp(0.5+rel_1m/0.06)
    flow_state="Nett Beli" if foreign_flow>0.60 else("Nett Jual" if foreign_flow<0.40 else "Netral")

    # BI path proxy (Bank Indonesia policy)
    bi_path=clamp(0.60-0.35*usd_idr_pressure-0.20*(1.0-bank_health))
    bi_state="Potensi cut" if bi_path>0.60 else("Hold" if bi_path>0.42 else "Hawkish / hati-hati")

    # Breadth IHSG — berapa banyak sektor positif
    sector_pos=0; sector_total=0
    for bname,syms in IHSG_BUCKETS.items():
        rs=[ret_n(prices.get(t,pd.Series()),21) for t in syms if math.isfinite(ret_n(prices.get(t,pd.Series()),21))]
        if rs:
            sector_total+=1
            if np.mean(rs)>0: sector_pos+=1
    breadth_ihsg=sector_pos/max(sector_total,1)

    # Global risk for IHSG context
    g_risk_raw=q.get("g_core",0.0)
    em_regime_score={"Q1":0.65,"Q2":0.70,"Q3":0.52,"Q4":0.28}.get(q["quad"],0.5)

    # IHSG composite score
    ihsg_score=clamp(
        0.20*em_regime_score
        +0.18*foreign_flow
        +0.16*bank_health
        +0.14*(1.0-usd_idr_pressure)
        +0.14*commodity_spillover
        +0.10*breadth_ihsg
        +0.08*clamp(0.5+g_risk_raw)
    )

    # Execution mode
    if ihsg_score>=0.60: exec_mode="🟢 Add on Reset"
    elif ihsg_score>=0.47: exec_mode="🟡 Wait Reclaim"
    else: exec_mode="🔴 Defensive / Selective Only"

    # IHSG vs SPY relative state
    rel_state="IHSG > SPY (overperform)" if rel_1m>0.01 else("IHSG < SPY (underperform)" if rel_1m<-0.01 else "IHSG ≈ SPY (neutral)")

    # Top IHSG stocks by momentum
    stock_rows=[]
    for bname,syms in IHSG_BUCKETS.items():
        for t in syms:
            s=prices.get(t,pd.Series())
            r1=ret_n(s,21); r3=ret_n(s,63)
            tr=ts(s)
            if math.isfinite(r1):
                stock_rows.append({"Ticker":t.replace(".JK",""),"Sektor":bname,
                    "1M":pct(r1),"3M":pct(r3),"Trend":"▲" if tr>=0.5 else "▼",
                    "_r1":r1,"_tr":tr})
    stock_rows.sort(key=lambda x:x["_r1"],reverse=True)

    return dict(
        jkse_1m=jkse_1m, jkse_3m=jkse_3m, jkse_6m=jkse_6m,
        usd_idr_1m=usd_idr_1m, usd_idr_3m=usd_idr_3m,
        usd_idr_pressure=usd_idr_pressure, idr_weakening=idr_weakening,
        bank_health=bank_health, commodity_spillover=commodity_spillover,
        foreign_flow=foreign_flow, flow_state=flow_state,
        bi_path=bi_path, bi_state=bi_state,
        breadth_ihsg=breadth_ihsg, ihsg_score=ihsg_score,
        exec_mode=exec_mode, rel_state=rel_state,
        em_regime=em_regime_score, stock_rows=stock_rows[:30],
    )

# ── Market health ─────────────────────────────────────────────────────────────
def build_health(prices:Dict[str,pd.Series],f:Dict)->Dict:
    SECS=["XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC"]
    spy_t=ts(prices.get("SPY",pd.Series())); qqq_t=ts(prices.get("QQQ",pd.Series()))
    iwm_t=ts(prices.get("IWM",pd.Series()))
    spy_3m=f.get("spy_3m",0.0); rsp_3m=ret_n(prices.get("RSP",pd.Series()),63)
    eqw_vs_cw=(rsp_3m-spy_3m) if(math.isfinite(rsp_3m) and math.isfinite(spy_3m)) else 0.0
    ab50=sum(1 for t in SECS if len(_s(prices.get(t,pd.Series())))>=50 and
             float(_s(prices.get(t,pd.Series())).iloc[-1])>float(_s(prices.get(t,pd.Series())).rolling(50).mean().iloc[-1]))
    sec_s=ab50/len(SECS); breadth=clamp(nm(spy_t,iwm_t,sec_s,clamp(0.5+eqw_vs_cw*5)))
    hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    hy_h=clamp(1.0-(hy-250)/500) if math.isfinite(hy) else 0.5
    ig_h=clamp(1.0-(ig-50)/200) if math.isfinite(ig) else 0.5
    hyg_t=ts(prices.get("HYG",pd.Series())); credit=clamp(nm(hy_h,ig_h,hyg_t))
    vix=f.get("vix_last",20.0); vix_h=clamp(1.0-(vix-13)/25)
    vr=f.get("vix_vxv_ratio",float("nan"))
    vix_ts=clamp(1.0-(vr-0.85)/0.25) if math.isfinite(vr) else 0.5
    vol=clamp(nm(vix_h,vix_ts))
    uup_1m=f.get("uup_1m",0.0); uup_1m=0.0 if not math.isfinite(uup_1m) else uup_1m
    dh=clamp(0.5+uup_1m*8)
    trade=clamp(nm(breadth,credit,1.0-dh*0.3)); trend_=clamp(nm(spy_t,qqq_t,sec_s))
    tail=clamp(nm(vol,credit,1.0-dh*0.4)); weather=clamp(0.35*trade+0.35*trend_+0.30*tail)
    def s3(v,hi=0.62,lo=0.42,lb=("Healthy","Mixed","Fragile")): return lb[0] if v>=hi else(lb[2] if v<=lo else lb[1])
    return dict(breadth=breadth,credit=credit,vol=vol,weather=weather,trade=trade,trend=trend_,tail=tail,
                sec_above50=ab50,sec_support=sec_s,eqw_vs_cw=eqw_vs_cw,dollar_hw=dh,spy_trend=spy_t,iwm_trend=iwm_t,
                breadth_state=s3(breadth),credit_state=s3(credit,lb=("Tight","Watch","Stressed")),
                vol_state=s3(vol,lb=("Calm","Watch","Stressed")),trade_state=s3(trade,lb=("Open","Neutral","Closed")),
                weather_state="Risk-On" if weather>=0.58 else("Risk-Off" if weather<=0.42 else "Mixed"))

# ── Crash meter ───────────────────────────────────────────────────────────────
def build_crash(f:Dict,h:Dict,q:Dict)->Dict:
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    vs=clamp((vix-18)/20); hs=clamp((hy-300)/400) if math.isfinite(hy) else 0.3
    is_=clamp((ig-80)/120) if math.isfinite(ig) else 0.3
    cs=clamp(0.60*hs+0.40*is_); bd=clamp(1.0-h.get("breadth",0.5)); dh=h.get("dollar_hw",0.5)
    gr=clamp(0.5-q.get("g_core",0.0))
    score=clamp(0.25*vs+0.20*cs+0.18*bd+0.15*dh+0.12*gr+0.10*(1.0-h.get("weather",0.5)))
    rs=[]
    if vs>=0.45: rs.append(f"VIX elevated ({vix:.1f})")
    if hs>=0.40 and math.isfinite(hy): rs.append(f"HY spreads wide ({hy:.0f}bps)")
    if bd>=0.55: rs.append("Market breadth deteriorating")
    if dh>=0.65: rs.append("USD pressure elevated (risk-off signal)")
    if f.get("vix_term_state","")=="Backwardation (fear)": rs.append("VIX backwardation — near-term panic signal")
    if f.get("yield_curve_uninverting"): rs.append("Yield curve uninverting — recession risk rising")
    if q.get("slowdown_flags",0)>=0.50: rs.append("Multiple growth slowdown flags active")
    state="🔴 ELEVATED" if score>=0.65 else("🟡 WATCH" if score>=0.42 else "🟢 CALM")
    return dict(score=score,state=state,vol_stress=vs,credit_stress=cs,breadth_dmg=bd,reasons=rs[:6])

# ── Data orchestration ────────────────────────────────────────────────────────
@st.cache_data(ttl=TTL,show_spinner=False)
def load_all()->Dict:
    all_tickers=tuple(set(US_TICKERS+IHSG_TICKERS+FX_TICKERS+COMMODITY_TICKERS[:8]))
    with st.spinner("Fetching prices…"): prices=fetch_prices(all_tickers,period="2y")
    with st.spinner("Fetching FRED macro data…"): fred={k:fetch_fred(v) for k,v in FRED_SERIES.items()}
    f=build_macro(fred,prices); q=build_quad(f); h=build_health(prices,f)
    cr=build_crash(f,h,q); rot=build_rotation(q,h,f); ihsg=build_ihsg(prices,q,f)
    return dict(prices=prices,fred=fred,f=f,q=q,h=h,crash=cr,rotation=rot,ihsg=ihsg,
                ts=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

# ── UI helpers ────────────────────────────────────────────────────────────────
def qb(q:str,extra="")->str:
    cls=q.lower() if q in("Q1","Q2","Q3","Q4") else "qunk"
    return f'<span class="qb {cls}">{q}{extra}</span>'
def mc(label:str,value:str,sub:str="",cls:str="")->None:
    st.markdown(f'<div class="mc"><div class="lb">{label}</div><div class="vl {cls}">{value}</div>{"<div class=sb>"+sub+"</div>" if sub else""}</div>',unsafe_allow_html=True)
def sh(t:str)->None: st.markdown(f'<div class="sh">{t}</div>',unsafe_allow_html=True)
def gb(label:str,v:float,note:str="",gd:str="high")->None:
    v=clamp(v); fill=v if gd=="high" else 1.0-v
    col="#3dbb6c" if fill>=0.62 else("#e5a020" if fill>=0.38 else "#e05252")
    st.markdown(f'<div class="gb"><div class="gr"><span>{label}</span><span style="color:{col};font-size:11px;font-family:DM Mono,monospace">{v:.0%} {note}</span></div><div class="bg"><div class="fl" style="width:{v*100:.0f}%;background:{col}"></div></div></div>',unsafe_allow_html=True)
def tag(text:str,kind:str="b")->str: return f'<span class="tag tag-{kind}">{text}</span>'

# ── Page 1: Radar ─────────────────────────────────────────────────────────────
def page_radar(snap:Dict)->None:
    q=snap["q"]; f=snap["f"]; rot=snap["rotation"]
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])
    ps=f.get("_proxy_share",1.0); fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0))
    if ps>0.60:
        st.markdown(f'<div class="proxy-b">⚠️ <strong>Proxy mode</strong> — FRED {fl}/{ft} series. Quad dari price proxy. Set FRED_API_KEY env var untuk data lebih akurat.</div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="real-b">✓ FRED {fl}/{ft} series loaded.</div>',unsafe_allow_html=True)

    # Dual-horizon display
    div=q["divergence"]; div_col="#e5a020" if div=="divergent" else "#3dbb6c"
    st.markdown(f"""<div style="text-align:center;padding:20px 16px">
    <div style="margin-bottom:6px">{qb(s_quad)} <span style="opacity:.4;font-size:12px">Structural</span>
    {"&nbsp;&nbsp;↔&nbsp;&nbsp;"+qb(m_quad)+' <span style="opacity:.4;font-size:12px">Monthly</span>' if div=="divergent" else ""}
    </div>
    <div style="font-family:'Syne',sans-serif;font-size:30px;font-weight:800;letter-spacing:-.03em;color:{meta['text']};margin-bottom:2px">{meta['label']}</div>
    <div style="font-size:12px;opacity:.5;margin-bottom:4px">{q['operating']} · Conf {q['confidence']:.0%}</div>
    <div style="font-size:13px;opacity:.75;max-width:480px;margin:0 auto;line-height:1.7">{meta['desc']}</div>
    </div>""",unsafe_allow_html=True)

    if div=="divergent":
        st.info(f"🔄 **Divergensi:** Structural {s_quad} vs Monthly {m_quad}. Artinya: tren besar masih {s_quad} tapi bulan ini bergerak seperti {m_quad}. Gunakan Monthly sebagai trigger masuk/keluar, Structural sebagai arah besar.")

    st.markdown("---")
    c1,c2,c3,c4=st.columns(4)
    with c1:
        g_acc=q.get("growth_acc"); txt=acc_txt(g_acc)
        mc("Growth Rate-of-Change",txt,"vs 3 bulan lalu","good" if g_acc else "bad")
    with c2:
        i_acc=q.get("infl_acc"); txt=acc_txt(i_acc)
        mc("Inflasi Rate-of-Change",txt,"vs 3 bulan lalu","bad" if i_acc else "good")
    with c3:
        vix=f.get("vix_last",0); vb="Investable (<19)" if vix<19 else("Chop (19-29)" if vix<29 else "Defensive (>29)")
        mc("VIX",f"{vix:.1f}" if math.isfinite(vix) else "—",vb,"good" if vix<19 else("bad" if vix>28 else "warn"))
    with c4:
        sp=f.get("spread_2s10s",float("nan")); yc=f.get("yield_curve_state","Unknown")
        mc("Yield Curve 2s10s",f"{sp:+.2f}%" if math.isfinite(sp) else "—",yc,
           "good" if("Normal" in yc or"Steep" in yc) else("bad" if"Inverted" in yc else "warn"))

    st.markdown("---")
    ca,cb=st.columns([1,1])
    with ca:
        sh("📊 REGIME PROBABILITY")
        probs=q.get("probs",{}); m_probs=q.get("monthly_probs",{})
        for qk in ["Q1","Q2","Q3","Q4"]:
            p=probs.get(qk,0.0); pm=m_probs.get(qk,0.0)
            act="●" if qk==s_quad else("◉" if qk==m_quad else "")
            lbl=" S" if qk==s_quad else(" M" if qk==m_quad else "")
            fc="#3dbb6c" if qk==s_quad else("#e5a020" if qk==m_quad else "rgba(255,255,255,0.12)")
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px"><span style="font-family:DM Mono,monospace;font-size:11px;width:40px;color:{fc}">{act} {qk}</span><div style="flex:1;background:rgba(255,255,255,0.07);border-radius:3px;height:7px;overflow:hidden"><div style="width:{p*100:.0f}%;background:{fc};height:100%"></div></div><span style="font-family:DM Mono,monospace;font-size:11px;width:36px;text-align:right">{p:.0%}</span></div>',unsafe_allow_html=True)
        flag="⚠️ Transisi regime tinggi" if q.get("flip_hazard",0)>0.50 else "Regime stabil"
        st.caption(f"Flip hazard: **{q.get('flip_hazard',0):.0%}** — {flag} · Next: **{q.get('next_quad','?')}**")

    with cb:
        sh(f"🎯 TRADE TERBAIK SEKARANG ({s_quad})")
        # Best trade
        top_ben=rot["top_ben"]; top_safe=rot["top_safe"]
        best_m=rot["best_meta"]; safe_m=rot["safe_meta"]
        st.markdown(f"""<div class="rot-card rot-best">
        <div style="font-size:10px;opacity:.5;font-weight:700;letter-spacing:.08em">BEST LONG / BENEFICIARY</div>
        <div style="font-size:18px;font-weight:700;font-family:Syne,sans-serif;margin:2px 0">{top_ben}</div>
        <div style="font-size:11px;opacity:.75">{best_m['why']}</div>
        <div style="font-size:10px;opacity:.5;margin-top:4px">✓ Konfirmasi: {best_m['confirm']}</div>
        <div style="font-size:10px;opacity:.5">✗ Invalidasi: {best_m['invalidate']}</div>
        </div>""",unsafe_allow_html=True)
        st.markdown(f"""<div class="rot-card rot-safe">
        <div style="font-size:10px;opacity:.5;font-weight:700;letter-spacing:.08em">SAFE HARBOR / HEDGE</div>
        <div style="font-size:18px;font-weight:700;font-family:Syne,sans-serif;margin:2px 0">{top_safe}</div>
        <div style="font-size:11px;opacity:.75">{safe_m['why']}</div>
        <div style="font-size:10px;opacity:.5;margin-top:4px">✓ Konfirmasi: {safe_m['confirm']}</div>
        </div>""",unsafe_allow_html=True)
        # Avoid
        st.markdown("<div style='margin-top:8px;font-size:11px;opacity:.6'><strong>Hindari:</strong> "+"&nbsp;&nbsp;".join(tag(a,"r") for a in meta["avoid"])+"</div>",unsafe_allow_html=True)

    # Key indicators table
    st.markdown("---")
    sh("🔑 INDIKATOR KUNCI (Hedgeye framework)")
    rows=[
        ("── GROWTH ──","","",""),
        ("Industrial Production YoY",pct(f.get("indpro_yoy",float("nan"))),acc_txt(f.get("indpro_acc")),""),
        ("Nonfarm Payrolls YoY",pct(f.get("payrolls_yoy",float("nan"))),acc_txt(f.get("payrolls_acc")),""),
        ("Retail Sales YoY",pct(f.get("retail_yoy",float("nan"))),acc_txt(f.get("retail_acc")),""),
        ("ISM Manufacturing",num(f.get("ism_last",float("nan")),1),"","<50 = kontraksi"),
        ("LEI 3M ★",pct(f.get("lei_3m",float("nan"))),acc_txt(f.get("lei_acc")),"Leading indicator"),
        ("Copper/Gold Ratio 3M ★",pct(f.get("copper_gold_ratio_3m",float("nan"))),"","Growth vs inflasi"),
        ("Unemployment Rate",f"{f.get('unrate',float('nan')):.1f}%" if math.isfinite(f.get("unrate",float("nan"))) else "—",
         f"3M Δ: {f.get('unrate_3m_delta',0):+.2f}" if math.isfinite(f.get("unrate_3m_delta",float("nan"))) else "",""),
        ("── INFLASI ──","","",""),
        ("CPI YoY",pct(f.get("cpi_yoy",float("nan"))),acc_txt(f.get("cpi_acc")),""),
        ("Core PCE YoY ★",pct(f.get("corepce_yoy",float("nan"))),acc_txt(f.get("corepce_acc")),"Fed preferred"),
        ("5Y Breakeven",num(f.get("breakeven",float("nan")),2),"","Ekspektasi pasar"),
        ("── RATES / YIELD CURVE ──","","",""),
        ("Fed Funds Rate",num(f.get("policy_rate",float("nan")),2),
         f"3M Δ: {f.get('policy_rate_3m',0):+.2f}" if math.isfinite(f.get("policy_rate_3m",float("nan"))) else "",""),
        ("2s10s Yield Curve ★",f"{f.get('spread_2s10s',float('nan')):+.2f}%" if math.isfinite(f.get("spread_2s10s",float("nan"))) else "—",
         f.get("yield_curve_state",""),"<0 = inverted = resesi"),
        ("10Y Real Yield",num(f.get("real_10y",float("nan")),2),"","+ve = kebijakan ketat"),
        ("── CREDIT & VOL ──","","",""),
        ("HY OAS Spread",f"{f.get('hy_oas',float('nan')):.0f}bps" if math.isfinite(f.get("hy_oas",float("nan"))) else "—",
         f"1M Δ: {f.get('hy_oas_1m',0):+.0f}bps" if math.isfinite(f.get("hy_oas_1m",float("nan"))) else "","Normal<350"),
        ("IG OAS Spread ★",f"{f.get('ig_oas',float('nan')):.0f}bps" if math.isfinite(f.get("ig_oas",float("nan"))) else "—",
         f"1M Δ: {f.get('ig_oas_1m',0):+.0f}bps" if math.isfinite(f.get("ig_oas_1m",float("nan"))) else "","Normal<100"),
        ("VIX / Term Structure ★",num(f.get("vix_last",float("nan")),1),f.get("vix_term_state",""),""),
    ]
    st.dataframe(pd.DataFrame(rows,columns=["Indikator","Nilai","Rate of Change","Catatan"]),
                 use_container_width=True,hide_index=True,height=540)

# ── Page 2: IHSG ──────────────────────────────────────────────────────────────
def page_ihsg(snap:Dict)->None:
    ih=snap["ihsg"]; q=snap["q"]; f=snap["f"]
    sh("🇮🇩 IHSG — INDONESIAN MARKET ANALYSIS")

    score=ih["ihsg_score"]
    score_col="#3dbb6c" if score>=0.60 else("#e5a020" if score>=0.47 else "#e05252")
    st.markdown(f"""<div style="text-align:center;padding:18px 16px;border-radius:12px;
    border:1.5px solid {score_col}33;margin-bottom:14px">
    <div style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:4px">IHSG COMPOSITE SCORE</div>
    <div style="font-family:Syne,sans-serif;font-size:44px;font-weight:800;color:{score_col};line-height:1">{score:.0%}</div>
    <div style="font-size:16px;font-weight:700;color:{score_col};margin-top:4px">{ih['exec_mode']}</div>
    </div>""",unsafe_allow_html=True)

    c1,c2,c3,c4=st.columns(4)
    with c1:
        jk=ih["jkse_1m"]; cls="good" if(math.isfinite(jk) and jk>0) else("bad" if(math.isfinite(jk) and jk<-0.02) else "warn")
        mc("^JKSE 1M Return",pct(jk),f"3M: {pct(ih['jkse_3m'])}",cls)
    with c2:
        idr=ih["usd_idr_1m"]; cls="bad" if(math.isfinite(idr) and idr>0.02) else("good" if(math.isfinite(idr) and idr<-0.01) else "warn")
        mc("USD/IDR 1M",pct(idr),"Naik = IDR lemah = buruk",cls)
    with c3: mc("Asing Flow",ih["flow_state"],f"Score: {ih['foreign_flow']:.0%}","good" if ih["foreign_flow"]>0.60 else("bad" if ih["foreign_flow"]<0.40 else "warn"))
    with c4: mc("BI Policy Proxy",ih["bi_state"],f"Score: {ih['bi_path']:.0%}","good" if ih["bi_path"]>0.60 else("warn" if ih["bi_path"]>0.42 else "bad"))

    st.markdown("---")
    ca,cb=st.columns(2)
    with ca:
        sh("📊 FAKTOR UTAMA IHSG")
        gb("Bank Health (BBCA,BBRI,BMRI)",ih["bank_health"],"backbone IHSG")
        gb("Commodity Spillover",ih["commodity_spillover"],"batubara & logam")
        gb("Asing Flow",ih["foreign_flow"],"dana masuk/keluar")
        gb("USD/IDR Tekanan",1-ih["usd_idr_pressure"],"lebih tinggi = IDR lebih kuat")
        gb("Breadth Sektoral IHSG",ih["breadth_ihsg"],f"({sum(1 for s in IHSG_BUCKETS if True)}/7 sektors)")
        gb("EM Regime Score",ih["em_regime"],"global macro support untuk EM")
    with cb:
        sh("🧭 REGIME & MACRO IMPACT PADA IHSG")
        quad=q["quad"]
        impact_map={
            "Q1":"✅ Goldilocks = IHSG kondusif. Growth global naik, inflasi turun. EM & bank outperform. Asing cenderung beli.",
            "Q2":"⚡ Reflation = IHSG bisa kuat. Commodity (coal, CPO, metals) outperform. Waspadai tail jika Fed overtighten.",
            "Q3":"⚠️ Stagflasi = IHSG tertekan. USD kuat menekan IDR. Asing keluar EM. Hanya commodity exporter yang bisa bertahan.",
            "Q4":"🔴 Deflasi/Resesi = IHSG defensif. Semua sektor tertekan. Hold cash atau defensive quality (ICBP, KLBF).",
        }
        st.markdown(f"""<div class="mc"><div class="lb">Dampak {quad} pada IHSG</div>
        <div style="font-size:13px;line-height:1.7;padding-top:4px">{impact_map.get(quad,'')}</div></div>""",unsafe_allow_html=True)
        st.markdown(f"""<div class="mc"><div class="lb">IHSG vs SPY</div>
        <div class="vl">{ih['rel_state']}</div>
        <div class="sb">1M rel: {pct(ih.get('jkse_1m',float('nan')))}</div></div>""",unsafe_allow_html=True)
        st.markdown(f"""<div class="mc"><div class="lb">Execution Mode</div>
        <div class="vl" style="font-size:16px">{ih['exec_mode']}</div>
        <div class="sb">Composite score: {ih['ihsg_score']:.0%}</div></div>""",unsafe_allow_html=True)

    st.markdown("---")
    sh("📈 IHSG STOCK RANKINGS (by 1M momentum)")
    if ih["stock_rows"]:
        df=pd.DataFrame([{k:v for k,v in r.items() if not k.startswith("_")} for r in ih["stock_rows"]])
        # Color coding would be nice but keep plain text
        st.dataframe(df,use_container_width=True,hide_index=True,height=420)
    else:
        st.info("Data saham IHSG belum tersedia. Pastikan internet terhubung.")

    st.markdown("---")
    sh("📚 KEY IHSG PAIRS TO WATCH")
    pairs=[("BBCA.JK","Bank terbesar, kualitas premium. Leading IHSG di Q1/Q2.","Q1,Q2"),
           ("ADRO.JK","Coal king. Rally keras di Q2/Q3 (commodity shock).","Q2,Q3"),
           ("ANTM.JK","Gold/nickel proxy. Cocok di Q3 (stagflasi).","Q3"),
           ("TLKM.JK","Defensif. Cocok di Q4. Dividend play.","Q4"),
           ("IDR=X","USD/IDR: naik = buruk untuk IHSG (asing kabur).","All"),
           ("^JKSE vs EEM","Relative: IHSG outperform EEM = asing pilih Indonesia.","All")]
    for t,desc,regime in pairs[:6]:
        s=snap["prices"].get(t,pd.Series())
        r1=ret_n(s,21)
        perf=pct(r1) if math.isfinite(r1) else "—"
        cls="good" if(math.isfinite(r1) and r1>0) else("bad" if(math.isfinite(r1) and r1<-0.01) else "warn")
        st.markdown(f"""<div class="mc" style="display:flex;justify-content:space-between;align-items:start">
        <div><div class="lb">{t} — {" ".join(tag(r,"b") for r in regime.split(","))}</div>
        <div style="font-size:12px;opacity:.8">{desc}</div></div>
        <div class="vl {cls}" style="font-size:16px">{perf}</div></div>""",unsafe_allow_html=True)

# ── Page 3: Market Health ─────────────────────────────────────────────────────
def page_health(snap:Dict)->None:
    h=snap["h"]; f=snap["f"]; prices=snap["prices"]
    sh("📡 TACTICAL WEATHER — BISA TRADING SEKARANG?")
    c1,c2,c3,c4=st.columns(4)
    def mcard3(label,s,sub,states):
        cls="good" if s==states[0] else("bad" if s==states[-1] else "warn")
        mc(label,s,sub,cls)
    with c1: mcard3("Trade Environment",h["trade_state"],"breadth + credit + USD",("Open","Neutral","Closed"))
    with c2: mcard3("Overall Weather",h["weather_state"],"composite risk regime",("Risk-On","Mixed","Risk-Off"))
    with c3: mcard3("Volatility",h["vol_state"],f"VIX {f.get('vix_last',0):.1f}",("Calm","Watch","Stressed"))
    with c4: mcard3("Credit Health",h["credit_state"],"HY + IG spreads",("Tight","Watch","Stressed"))
    st.markdown("---")
    ca,cb=st.columns(2)
    with ca:
        sh("📊 BREADTH GAUGES")
        gb("Sektor di atas 50-DMA",h["sec_support"],note=f"({h['sec_above50']}/11)")
        gb("SPY trend health",h["spy_trend"])
        gb("Small cap (IWM)",h["iwm_trend"])
        gb("Equal-weight vs cap-weight",clamp(0.5+h["eqw_vs_cw"]*5),note=pct(h["eqw_vs_cw"])+" 3M diff")
        gb("Breadth composite",h["breadth"])
    with cb:
        sh("⚡ CREDIT & VOL")
        hy=f.get("hy_oas",float("nan")); ig=f.get("ig_oas",float("nan"))
        gb("HY Credit health",clamp(1.0-(hy-250)/500) if math.isfinite(hy) else 0.5,note=f"{hy:.0f}bps" if math.isfinite(hy) else "proxy")
        gb("IG Credit health ★",clamp(1.0-(ig-50)/200) if math.isfinite(ig) else 0.5,note=f"{ig:.0f}bps" if math.isfinite(ig) else "n/a")
        vix=f.get("vix_last",20.0); gb("VIX health",clamp(1.0-(vix-13)/25),note=f"VIX {vix:.1f}")
        vr=f.get("vix_vxv_ratio",float("nan"))
        gb("VIX term structure ★",clamp(1.0-(vr-0.85)/0.25) if math.isfinite(vr) else 0.5,note=f.get("vix_term_state",""))
        gb("Credit + Vol composite",(h["credit"]+h["vol"])/2)
    st.markdown("---"); sh("📈 YIELD CURVE ★")
    sp=f.get("spread_2s10s",float("nan")); sp30=f.get("spread_10s30s",float("nan")); sp3m=f.get("spread_2s10s_3m",float("nan"))
    y1,y2,y3=st.columns(3)
    with y1: mc("2s10s Spread",f"{sp:+.2f}%" if math.isfinite(sp) else "—",f.get("yield_curve_state",""),"good" if(math.isfinite(sp) and sp>0.5) else("bad" if(math.isfinite(sp) and sp<0) else "warn"))
    with y2: mc("10s30s Spread",f"{sp30:+.2f}%" if math.isfinite(sp30) else "—")
    with y3: mc("2s10s 3M Δ",f"{sp3m:+.2f}%" if math.isfinite(sp3m) else "—","Uninverting = resesi dimulai" if f.get("yield_curve_uninverting") else "","warn" if f.get("yield_curve_uninverting") else "neu")
    st.info("> **Yield curve:** 2Y > 10Y = inverted = sinyal resesi. Ketika curve mulai steepen (uninverting), itu tanda resesi sedang dimulai, bukan ending.")
    st.markdown("---"); sh("📦 SEKTOR US vs SPY (3-Bulan)")
    SECS={"XLE":"Energy","XLF":"Financials","XLI":"Industrials","XLB":"Materials","XLK":"Technology","XLV":"Healthcare","XLY":"Cons.Disc.","XLP":"Cons.Staples","XLU":"Utilities","XLRE":"Real Estate","XLC":"Comm.Svc."}
    spy3=ret_n(prices.get("SPY",pd.Series()),63); rows=[]
    for t,name in SECS.items():
        s=prices.get(t,pd.Series()); r3=ret_n(s,63); r1=ret_n(s,21)
        rel=(r3-spy3) if(math.isfinite(r3) and math.isfinite(spy3)) else float("nan")
        rows.append({"Sektor":name,"3M":pct(r3),"1M":pct(r1),"vs SPY 3M":pct(rel),"50DMA":"✓" if ts(s)>=0.5 else "✗"})
    rows.sort(key=lambda r:float(r["vs SPY 3M"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY 3M"]!="—" else -999,reverse=True)
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=360)

# ── Page 4: Playbook ──────────────────────────────────────────────────────────
def page_playbook(snap:Dict)->None:
    q=snap["q"]; rot=snap["rotation"]; prices=snap["prices"]
    s_quad=q["quad"]; m_quad=q["monthly_quad"]; meta=QUAD_META.get(s_quad,QUAD_META["Q4"])

    sh(f"🎯 FULL PLAYBOOK — {q['operating'].upper()}")
    # Rotation rows
    st.markdown("**BENEFICIARY (beli / long):**")
    for row in rot["ben_rows"]:
        rm=ROUTE_META.get(row["route"],{})
        st.markdown(f"""<div class="rot-card rot-best">
        <b>{row['route']}</b> <span style="font-size:11px;opacity:.5">EV score: {row['score']:.0%}</span><br>
        <span style="font-size:12px">{rm.get('why','')}</span><br>
        <span style="font-size:10px;opacity:.5">✓ {rm.get('confirm','')} &nbsp; ✗ {rm.get('invalidate','')}</span>
        </div>""",unsafe_allow_html=True)
    st.markdown("**SAFE HARBOR (hedge / lindung nilai):**")
    for row in rot["safe_rows"]:
        rm=ROUTE_META.get(row["route"],{})
        st.markdown(f"""<div class="rot-card rot-safe">
        <b>{row['route']}</b> <span style="font-size:11px;opacity:.5">EV score: {row['score']:.0%}</span><br>
        <span style="font-size:12px">{rm.get('why','')}</span>
        </div>""",unsafe_allow_html=True)
    st.markdown("**HINDARI:**")
    st.markdown("&nbsp;&nbsp;".join(tag(a,"r") for a in meta["avoid"]),unsafe_allow_html=True)

    # EM rotation
    st.markdown("---"); sh("🌏 EM ROTATION SIGNAL")
    em_col="good" if rot["em_score"]>0.60 else("bad" if rot["em_score"]<0.45 else "warn")
    mc("EM / IHSG Rotation",rot["em_state"],f"Score: {rot['em_score']:.0%}",em_col)
    if rot["em_state"]=="Accumulate":
        st.success("EEM dan IHSG aktif. USD adem, breadth US sehat, commodity chain hidup.")
    elif rot["em_state"]=="Wait":
        st.warning("EM mixed. Tunggu konfirmasi: EEM > SPY di 1M dan 3M, USD tidak re-accelerate.")
    else:
        st.error("EM bearish. USD kuat menekan EM. Hindari EEM dan IHSG untuk saat ini.")

    # Scenario Lab
    st.markdown("---"); sh("🔬 SCENARIO LAB — APA YANG BISA PECAH INI?")
    st.markdown("*Setiap scenario memiliki probabilitas dan dampaknya terhadap posisi saat ini.*")
    for sc in rot["scenarios"]:
        prob=sc["prob"]; col="#3dbb6c" if prob<0.25 else("#e5a020" if prob<0.50 else "#e05252")
        st.markdown(f"""<div class="mc" style="border-left:3px solid {col}33">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px">
        <div style="font-weight:600;font-size:13px">{sc['name']}</div>
        <div style="font-family:DM Mono,monospace;color:{col};font-size:12px">{prob:.0%}</div>
        </div>
        <div style="font-size:12px;opacity:.8">{sc['impact']}</div>
        </div>""",unsafe_allow_html=True)

    # Cross-asset heatmap
    st.markdown("---"); sh("🌐 CROSS-ASSET RETURNS HEATMAP")
    ASSETS={"US Equity (SPY)":"SPY","Growth (QQQ)":"QQQ","Small Cap (IWM)":"IWM","Long Bond (TLT)":"TLT",
            "Credit (HYG)":"HYG","Gold (GLD)":"GLD","Oil (CL=F)":"CL=F","Copper (HG=F)":"HG=F",
            "USD (UUP)":"UUP","EM Equity (EEM)":"EEM","IHSG (^JKSE)":"^JKSE",
            "BTC":"BTC-USD","ETH":"ETH-USD","XRP":"XRP-USD"}
    heat=[]
    for name,t in ASSETS.items():
        s=prices.get(t,pd.Series())
        heat.append({"Asset":name,"1W":pct(ret_n(s,5)),"1M":pct(ret_n(s,21)),"3M":pct(ret_n(s,63)),"6M":pct(ret_n(s,126)),"1Y":pct(ret_n(s,252))})
    st.dataframe(pd.DataFrame(heat),use_container_width=True,hide_index=True,height=480)

# ── Page 5: Risk Monitor ──────────────────────────────────────────────────────
def page_risk(snap:Dict)->None:
    cr=snap["crash"]; f=snap["f"]; q=snap["q"]
    sc=cr["score"]; col="#e05252" if sc>=0.65 else("#e5a020" if sc>=0.42 else "#3dbb6c")
    st.markdown(f'<div style="text-align:center;padding:24px 20px;border-radius:14px;border:1.5px solid {col}33;margin-bottom:18px"><div style="font-size:10px;letter-spacing:.1em;text-transform:uppercase;opacity:.45;margin-bottom:6px">CRASH / RISK-OFF METER</div><div style="font-family:Syne,sans-serif;font-size:56px;font-weight:800;color:{col};line-height:1">{sc:.0%}</div><div style="font-size:15px;font-weight:600;color:{col};margin-top:4px">{cr["state"]}</div></div>',unsafe_allow_html=True)
    r1,r2,r3=st.columns(3)
    def rm(label,v,sub):
        cls="bad" if v>=0.60 else("warn" if v>=0.35 else "good")
        mc(label,f"{v:.0%}",sub,cls)
    with r1: rm("Vol Stress",cr["vol_stress"],"VIX-based")
    with r2: rm("Credit Stress",cr["credit_stress"],"HY + IG OAS")
    with r3: rm("Breadth Damage",cr["breadth_dmg"],"market internals")
    if cr["reasons"]:
        st.markdown("---"); sh("⚠️ ACTIVE RISK FLAGS")
        for r in cr["reasons"]: st.markdown(f"- {r}")
    st.markdown("---"); sh("📉 VIX REGIME ★")
    vix=f.get("vix_last",20.0); vr=f.get("vix_vxv_ratio",float("nan"))
    v1,v2,v3=st.columns(3)
    with v1: mc("VIX Bucket","Investable (<19)" if vix<19 else("Chop (19-29)" if vix<29 else "Defensive (>29)"),f"VIX = {vix:.1f}","good" if vix<19 else("warn" if vix<29 else "bad"))
    with v2: mc("VIX/VXV Ratio ★",f"{vr:.3f}" if math.isfinite(vr) else "—",f.get("vix_term_state",""),"good" if(math.isfinite(vr) and vr<0.90) else("bad" if(math.isfinite(vr) and vr>=1.0) else "warn"))
    with v3: rmode="Normal" if vix<19 else("Reduced" if vix<29 else "Defensive"); mc("Risk Mode",rmode,"sizing guide","good" if rmode=="Normal" else("warn" if rmode=="Reduced" else "bad"))
    st.info("> **VIX term structure:** VIX < VXV = contango (tenang). VIX > VXV = backwardation = sinyal panik jangka pendek.")
    st.markdown("---"); sh("💳 CREDIT SPREAD ★")
    hy=f.get("hy_oas",float("nan")); ig=f.get("ig_oas",float("nan"))
    hy1m=f.get("hy_oas_1m",float("nan")); ig1m=f.get("ig_oas_1m",float("nan"))
    c1,c2=st.columns(2)
    with c1: mc("HY OAS",f"{hy:.0f}bps" if math.isfinite(hy) else "—",f"1M Δ: {hy1m:+.0f}bps" if math.isfinite(hy1m) else "","good" if(math.isfinite(hy) and hy<350) else("bad" if(math.isfinite(hy) and hy>500) else "warn")); st.caption("Normal<350bps | Watch 350-500 | Stress>500")
    with c2: mc("IG OAS ★",f"{ig:.0f}bps" if math.isfinite(ig) else "—",f"1M Δ: {ig1m:+.0f}bps" if math.isfinite(ig1m) else "","good" if(math.isfinite(ig) and ig<100) else("bad" if(math.isfinite(ig) and ig>150) else "warn")); st.caption("Normal<100bps | Watch 100-150 | Stress>150")
    st.markdown("---"); sh("🔭 FORWARD RISK FACTORS")
    lei=f.get("lei_3m",float("nan")); cg=f.get("copper_gold_ratio_3m",float("nan")); umi=f.get("umcsent_last",float("nan"))
    st.markdown(f"""
- **Regime flip hazard:** {q.get("flip_hazard",0):.0%} → Next likely: **{q.get("next_quad","?")}**
- **Dual-horizon divergence:** {q.get("operating","—")}
- **Yield curve:** {f.get("yield_curve_state","")} | 3M Δ: {pct(f.get("spread_2s10s_3m",float("nan")))}
- **LEI 3M:** {pct(lei)} {"⚠️ Leading indicator turun" if(math.isfinite(lei) and lei<-0.01) else("✓ LEI holding" if math.isfinite(lei) else "(proxy mode)")}
- **Copper/Gold 3M:** {pct(cg)} {"→ ekspektasi growth turun" if(math.isfinite(cg) and cg<-0.05) else "→ growth expectations holding"}
- **UMich Sentiment:** {num(umi,1)} {"⚠️ Below 70 = consumer stressed" if(math.isfinite(umi) and umi<70) else ""}
- **Growth slowdown flags:** {q.get("slowdown_flags",0):.0%} dari 4 aktif
    """)

# ── Page 6: Diagnostics ───────────────────────────────────────────────────────
def page_diag(snap:Dict)->None:
    f=snap["f"]; fred=snap["fred"]; prices=snap["prices"]
    fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0)); ps=f.get("_proxy_share",1.0)
    sh("📋 FRED DATA COVERAGE")
    cov=[{"Series":k,"FRED ID":FRED_SERIES.get(k,""),"Points":len(_s(s)),
          "Latest":str(_s(s).index[-1])[:10] if not _s(s).empty else "—",
          "Last Value":round(float(_s(s).iloc[-1]),4) if not _s(s).empty else None,
          "Status":"✓ Loaded" if not _s(s).empty else "✗ Missing"} for k,s in fred.items()]
    st.dataframe(pd.DataFrame(cov),use_container_width=True,hide_index=True,height=480)
    if ps>0.50:
        st.warning(f"**FRED issue ({fl}/{ft} loaded).** Penyebab: firewall/network block fred.stlouisfed.org, rate limit FRED, atau Streamlit Cloud restriction.\n\nFix: `export FRED_API_KEY=your_key` (daftar gratis di fred.stlouisfed.org/api/key/). App tetap jalan di proxy mode.")
    sh("📦 PRICE DATA COVERAGE")
    prows=[{"Ticker":t,"Points":len(s),"Latest":str(s.index[-1])[:10] if not s.empty else "—","Last Close":round(float(s.iloc[-1]),4) if not s.empty else None} for t,s in sorted(prices.items())]
    st.dataframe(pd.DataFrame(prows),use_container_width=True,hide_index=True,height=400)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown('<div style="display:flex;align-items:center;margin-bottom:4px"><span style="font-family:Syne,sans-serif;font-size:20px;font-weight:800;letter-spacing:-.03em">🧭 MacroRegime Pro</span><span style="font-size:10px;opacity:.3;margin-left:8px;font-family:DM Mono,monospace">v5.0 · Hedgeye GIP Framework</span></div>',unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Force Refresh",use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.markdown("---")
        st.markdown("""
**Cara baca (laypeople guide):**
1. 🧭 **Radar** — Kita di regime apa? Trade terbaik apa?
2. 🇮🇩 **IHSG** — Kondisi market Indonesia khusus
3. 📡 **Market Health** — Bisa masuk pasar sekarang?
4. 🎯 **Playbook** — Full strategy + skenario risiko
5. ⚠️ **Risk Monitor** — Crash meter + VIX + credit
6. 🔬 **Diagnostics** — Data quality check

**Data sources (free):**
- Yahoo Finance (prices, ETFs, futures, crypto, IHSG)
- FRED public CSV (macro: CPI, yields, etc.)

**Proxy mode:** FRED gagal → macro dihitung dari harga ETF/futures. Arah benar, angka lebih kasar.
        """)
    snap=load_all()
    q=snap["q"]; f=snap["f"]; cr=snap["crash"]
    quad=q["quad"]; m_quad=q["monthly_quad"]; meta=QUAD_META.get(quad,{})
    ga="▲" if q.get("growth_acc") else "▼"; ia="▲" if q.get("infl_acc") else "▼"
    div_badge=f" / M:{m_quad}" if q["divergence"]=="divergent" else ""
    st.markdown(f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 12px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);margin-bottom:12px;font-size:11px"><span>Regime: {qb(quad)}{div_badge} <strong>{meta.get("label","")}</strong></span><span style="opacity:.25">|</span><span>Conf: <strong>{q["confidence"]:.0%}</strong></span><span style="opacity:.25">|</span><span>Growth: <strong>{ga}</strong></span><span style="opacity:.25">|</span><span>Inflasi: <strong>{ia}</strong></span><span style="opacity:.25">|</span><span>Risk: <strong>{cr["state"]}</strong></span><span style="opacity:.25">|</span><span style="opacity:.3">{snap["ts"]}</span></div>',unsafe_allow_html=True)
    tabs=st.tabs(["🧭 Radar","🇮🇩 IHSG","📡 Market Health","🎯 Playbook","⚠️ Risk Monitor","🔬 Diagnostics"])
    with tabs[0]: page_radar(snap)
    with tabs[1]: page_ihsg(snap)
    with tabs[2]: page_health(snap)
    with tabs[3]: page_playbook(snap)
    with tabs[4]: page_risk(snap)
    with tabs[5]: page_diag(snap)

if __name__=="__main__": main()
