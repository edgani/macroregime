"""
MacroRegime Pro v4.1 — Fixed
============================
Fixes from v4.0:
- RESTORED price-based fallback proxy (when FRED fails, quad still runs correctly)
- FIXED HTML rendering in dataframes (plain text only)
- FIXED quad calibration — properly detects Q3/Q4 in current slowdown environment
- Added data quality banner (shows proxy vs real FRED coverage)
- FRED API key support via FRED_API_KEY env var

Free data: yfinance + FRED public CSV
Run: streamlit run macro_regime_pro_v4.py
"""

from __future__ import annotations
import datetime, math, os
from io import StringIO
from typing import Dict, Optional
import numpy as np
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide",
                   initial_sidebar_state="collapsed")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
html,[class*="css"]{font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Syne',sans-serif;letter-spacing:-0.02em}
#MainMenu,footer,header{visibility:hidden}
.block-container{padding-top:0.5rem;padding-bottom:2rem}
.qb{display:inline-block;padding:3px 12px;border-radius:20px;font-family:'DM Mono',monospace;font-weight:500;font-size:11px;letter-spacing:.05em}
.q1{background:#d4edda;color:#155724}.q2{background:#fff3cd;color:#856404}
.q3{background:#ffeeba;color:#7d4e00}.q4{background:#f8d7da;color:#721c24}
.qunk{background:#e2e3e5;color:#495057}
.mc{background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;padding:14px 16px;margin-bottom:6px}
.mc .lb{font-size:10px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;opacity:.4;margin-bottom:3px}
.mc .vl{font-family:'Syne',sans-serif;font-size:22px;font-weight:700;line-height:1.1;margin-bottom:1px}
.mc .sb{font-size:11px;opacity:.5}
.good{color:#3dbb6c}.warn{color:#e5a020}.bad{color:#e05252}.neu{color:#888}
.sh{font-size:10px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;opacity:.35;padding:10px 0 4px;border-bottom:1px solid rgba(255,255,255,0.06);margin-bottom:10px}
.rh{text-align:center;padding:24px 20px}
.rn{font-family:'Syne',sans-serif;font-size:34px;font-weight:800;letter-spacing:-.03em;line-height:1.1;margin-bottom:4px}
.rs{font-size:13px;opacity:.5;margin-bottom:12px}
.re{font-size:14px;line-height:1.7;max-width:500px;margin:0 auto;opacity:.8}
.gb{margin-bottom:8px}
.gb .gr{display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px}
.gb .bg{height:5px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden}
.gb .fl{height:100%;border-radius:3px}
.olong{border-left:3px solid #3dbb6c;padding-left:8px;margin:2px 0;font-size:12px}
.oshort{border-left:3px solid #e05252;padding-left:8px;margin:2px 0;font-size:12px}
.ohedge{border-left:3px solid #e5a020;padding-left:8px;margin:2px 0;font-size:12px}
.proxy-b{padding:8px 14px;border-radius:8px;font-size:12px;margin-bottom:12px;background:rgba(229,160,32,0.12);border:1px solid rgba(229,160,32,0.3);color:#e5a020}
.real-b{padding:8px 14px;border-radius:8px;font-size:12px;margin-bottom:12px;background:rgba(61,187,108,0.08);border:1px solid rgba(61,187,108,0.2);color:#3dbb6c}
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
CACHE_TTL = 3600
FRED_SERIES = {
    "INDPRO":   "INDPRO",    "PAYEMS":    "PAYEMS",   "UNRATE":    "UNRATE",
    "ICSA":     "ICSA",      "RSAFS":     "RSAFS",    "HOUST":     "HOUST",
    "PERMIT":   "PERMIT",    "ISM":       "NAPMNOI",  "LEI":       "USSLIND",
    "UMCSENT":  "UMCSENT",   "CPI":       "CPIAUCSL", "CORECPI":   "CPILFESL",
    "COREPCE":  "PCEPILFE",  "DGS2":      "DGS2",     "DGS10":     "DGS10",
    "DGS30":    "DGS30",     "REAL10":    "DFII10",   "BREAKEVEN": "T5YIE",
    "FEDFUNDS": "FEDFUNDS",  "HYOAS":     "BAMLH0A0HYM2", "IGSPR": "BAMLC0A0CM",
}
PRICE_TICKERS = [
    "SPY","QQQ","IWM","RSP","MDY",
    "XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC",
    "HYG","LQD","TLT","IEF","SHY","GLD","GC=F","SI=F","HG=F","CL=F","NG=F",
    "UUP","EEM","EFA","^VIX","^VXV","^VIX9D","BTC-USD","ETH-USD","SOL-USD",
]
QUAD_META = {
    "Q1": {"name":"Q1 — Growth↑ Inflation↓","color":"#d4edda","text":"#155724","label":"Risk-On Goldilocks",
           "explain":"Growth accelerating, inflation falling or contained. Best period for risk assets. Central banks can ease or hold. Equities broadly work — especially growth and cyclicals.",
           "long":["Growth equities (QQQ, XLK)","Cyclicals (XLY, XLI)","Credit (HYG)","EM equities (EEM)"],
           "hedge":["Gold (GLD)","Short duration (SHY)"],"avoid":["Energy commodities","USD longs (UUP)","Defensives (XLP, XLU)"]},
    "Q2": {"name":"Q2 — Growth↑ Inflation↑","color":"#fff3cd","text":"#856404","label":"Reflation / Boom",
           "explain":"Both growth and inflation rising. Real assets, energy, and cyclicals outperform. Value beats growth. Central banks tightening. Watch for Q2→Q3 inflection.",
           "long":["Energy (XLE, CL=F)","Materials (XLB, HG=F)","Financials (XLF)","Small caps (IWM)"],
           "hedge":["TIPS / inflation-linked","Commodity FX"],"avoid":["Long duration bonds (TLT)","High-multiple tech","IG credit"]},
    "Q3": {"name":"Q3 — Growth↓ Inflation↑","color":"#ffeeba","text":"#7d4e00","label":"Stagflation",
           "explain":"Growth slowing while inflation stays hot. The hardest quad. Central banks forced to tighten into weakness. Equities broadly suffer. Gold, energy, and cash are the few safe-ish longs.",
           "long":["Gold (GLD, GC=F)","Energy (XLE)","USD / cash (UUP, SHY)","Short equity ideas"],
           "hedge":["Gold (GLD)","USD (UUP)","Short-term Treasuries (SHY)"],
           "avoid":["Rate-sensitive tech (QQQ)","Consumer disc. (XLY)","EM (EEM)","Long bonds (TLT)","Junk credit (HYG)"]},
    "Q4": {"name":"Q4 — Growth↓ Inflation↓","color":"#f8d7da","text":"#721c24","label":"Quad 4 — Risk-Off / Deflation",
           "explain":"Growth slowing and inflation falling — the recession quad. Bonds rally hard. Defensives outperform. Central banks cut eventually. Capital preservation mode.",
           "long":["Long-duration bonds (TLT)","Gold (GLD)","Defensives (XLP, XLU, XLV)","USD (UUP)"],
           "hedge":["Treasury bonds (TLT)","Gold (GLD)"],
           "avoid":["Commodities (XLE, XLB)","Cyclicals (XLI, XLY)","Junk credit (HYG)","Small caps (IWM)","EM (EEM)"]},
}

# ── Math helpers ───────────────────────────────────────────────────────────────
def _s(s) -> pd.Series:
    if s is None: return pd.Series(dtype=float)
    return pd.to_numeric(s if isinstance(s,pd.Series) else pd.Series(s), errors="coerce").dropna()

def last(s) -> float:
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
def ts(s)->float:
    s=_s(s)
    if len(s)<50: return 0.5
    px=float(s.iloc[-1]); m20=float(s.rolling(20).mean().iloc[-1]); m50=float(s.rolling(50).mean().iloc[-1])
    return 0.5*(1 if px>m20 else 0)+0.5*(1 if px>m50 else 0)
def th(x:float,sc:float)->float:
    if not math.isfinite(x): return 0.0
    return float(math.tanh(x/max(sc,1e-9)))
def clamp(x:float,lo=0.0,hi=1.0)->float: return max(lo,min(hi,float(x or 0)))
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

# ── Data fetching ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL,show_spinner=False)
def fetch_fred(fred_id:str)->pd.Series:
    key=os.environ.get("FRED_API_KEY","")
    try: key=key or st.secrets.get("FRED_API_KEY","")
    except: pass
    urls=[f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={fred_id}"]
    if key: urls.append(f"https://api.stlouisfed.org/fred/series/observations?series_id={fred_id}&api_key={key}&file_type=json")
    sess=requests.Session(); sess.headers.update({"User-Agent":"Mozilla/5.0 MacroRegimePro/4.1"})
    for url in urls:
        try:
            r=sess.get(url,timeout=10); r.raise_for_status()
            if "fredgraph" in url or "csv" in url:
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

@st.cache_data(ttl=CACHE_TTL,show_spinner=False)
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
    except Exception as e:
        st.warning(f"yfinance error: {e}"); return {}

# ── Price-based macro proxy (CRITICAL fallback when FRED unavailable) ──────────
def build_proxy(prices:Dict[str,pd.Series])->Dict:
    """
    Approximates FRED macro series from market prices.
    Key relationships used:
    - XLI 3M → INDPRO proxy (industrials lead production)
    - IWM 3M → Payrolls / labor market proxy
    - XLY 3M → Retail sales proxy
    - CL=F 3M + GC=F 3M → Inflation proxy
    - HYG 1M → Credit spread proxy
    - TLT 1M → Rates / growth expectation proxy
    - HG=F / GC=F ratio → Growth vs inflation signal (copper/gold)
    """
    spy_3m = ret_n(prices.get("SPY",  pd.Series()), 63)
    xli_3m = ret_n(prices.get("XLI",  pd.Series()), 63)
    xly_3m = ret_n(prices.get("XLY",  pd.Series()), 63)
    iwm_3m = ret_n(prices.get("IWM",  pd.Series()), 63)
    uup_3m = ret_n(prices.get("UUP",  pd.Series()), 63)
    oil_3m = ret_n(prices.get("CL=F", pd.Series()), 63)
    gold_3m= ret_n(prices.get("GC=F", pd.Series()), 63)
    tlt_1m = ret_n(prices.get("TLT",  pd.Series()), 21)
    hyg_1m = ret_n(prices.get("HYG",  pd.Series()), 21)
    cop_3m = ret_n(prices.get("HG=F", pd.Series()), 63)
    eem_3m = ret_n(prices.get("EEM",  pd.Series()), 63)
    xle_3m = ret_n(prices.get("XLE",  pd.Series()), 63)
    xlp_3m = ret_n(prices.get("XLP",  pd.Series()), 63)

    def nf(x,d=0.0): return float(np.nan_to_num(x,nan=d))

    # Growth proxies
    indpro_p  = nf(0.55*xli_3m + 0.45*spy_3m)
    retail_p  = nf(0.60*xly_3m + 0.40*spy_3m)
    pay_p     = nf(0.50*iwm_3m + 0.50*spy_3m)
    unrate_p  = nf(-0.10*iwm_3m)              # rising IWM → falling unemployment
    claims_p  = nf(-10.0*iwm_3m)             # rising IWM → falling claims
    ism_p     = 50.0 + 20.0*nf(xli_3m)
    lei_p     = nf(0.40*xli_3m + 0.30*spy_3m + 0.30*iwm_3m)
    umcs_p    = 75.0 + 100.0*nf(xly_3m)
    # Inflation proxies
    cpi_p     = nf(0.025 + 0.35*oil_3m + 0.05*gold_3m)
    corecpi_p = nf(0.023 + 0.15*oil_3m - 0.05*uup_3m)
    corepce_p = nf(0.022 + 0.12*oil_3m - 0.04*uup_3m)
    bk_p      = 2.2 + 1.2*nf(oil_3m) + 0.4*nf(gold_3m) - 0.2*nf(uup_3m)
    bk1m_p    = nf(0.15*oil_3m/3 + 0.05*gold_3m/3)
    # Rates proxies
    real10_p  = 1.8 - 30.0*nf(tlt_1m) if math.isfinite(tlt_1m) else 1.8
    hy_p      = 350.0 - 1200.0*nf(hyg_1m)
    hy1m_p    = -200.0*nf(hyg_1m)
    # Copper/gold
    cg_3m     = nf(cop_3m - gold_3m) if (math.isfinite(cop_3m) and math.isfinite(gold_3m)) else 0.0

    return dict(
        indpro_yoy=indpro_p, retail_yoy=retail_p, payrolls_yoy=pay_p,
        unrate_3m_delta=unrate_p, unrate_6m_delta=unrate_p*2,
        claims_13w_delta=claims_p, claims_last=220000.0,
        ism_last=ism_p, housing_yoy=nf(iwm_3m*0.6),
        permits_yoy=nf(iwm_3m*0.5), lei_3m=lei_p, umcsent_last=umcs_p,
        cpi_yoy=cpi_p, cpi_mom=nf(oil_3m/12), corecpi_yoy=corecpi_p,
        corepce_yoy=corepce_p, breakeven=bk_p, breakeven_1m=bk1m_p,
        real_10y=real10_p, policy_rate=4.33, policy_rate_3m=0.0,
        dgs2=float("nan"), dgs10=float("nan"), dgs30=float("nan"),
        spread_2s10s=float("nan"), spread_10s30s=float("nan"),
        spread_2s10s_1m=float("nan"), spread_2s10s_3m=float("nan"),
        yield_curve_state="Unknown (proxy mode)", yield_curve_uninverting=False,
        hy_oas=hy_p, hy_oas_1m=hy1m_p, ig_oas=float("nan"), ig_oas_1m=float("nan"),
        copper_gold_ratio_3m=cg_3m, copper_gold_ratio_last=float("nan"),
        indpro_acc=None, payrolls_acc=None, retail_acc=None,
        lei_acc=None, cpi_acc=None, corepce_acc=None,
    )

# ── Macro feature builder ─────────────────────────────────────────────────────
def build_macro(fred:Dict[str,pd.Series], prices:Dict[str,pd.Series])->Dict:
    # Start from proxy, override with real FRED where available
    f=build_proxy(prices)
    loaded=0; total=0

    def ov(key:str,fk:str,fn,*args):
        nonlocal loaded,total
        total+=1
        s=fred.get(key,pd.Series())
        if not _s(s).empty:
            v=fn(s,*args)
            if math.isfinite(v): f[fk]=v; loaded+=1; return True
        return False

    ov("INDPRO","indpro_yoy",ret_n,12)
    ov("PAYEMS","payrolls_yoy",ret_n,12)
    ov("PAYEMS","payrolls_mom",ret_n,1)
    ov("UNRATE","unrate",last)
    ov("UNRATE","unrate_3m_delta",delta_n,3)
    ov("UNRATE","unrate_6m_delta",delta_n,6)
    ov("ICSA","claims_13w_delta",delta_n,13)
    ov("ICSA","claims_last",last)
    ov("ISM","ism_last",last)
    ov("RSAFS","retail_yoy",ret_n,12)
    ov("HOUST","housing_yoy",ret_n,12)
    ov("PERMIT","permits_yoy",ret_n,12)
    ov("LEI","lei_3m",ret_n,3)
    ov("UMCSENT","umcsent_last",last)
    ov("CPI","cpi_yoy",ret_n,12)
    ov("CPI","cpi_mom",ret_n,1)
    ov("CORECPI","corecpi_yoy",ret_n,12)
    ov("COREPCE","corepce_yoy",ret_n,12)
    ov("BREAKEVEN","breakeven",last)
    ov("BREAKEVEN","breakeven_1m",delta_n,1)
    ov("REAL10","real_10y",last)
    ov("FEDFUNDS","policy_rate",last)
    ov("FEDFUNDS","policy_rate_3m",delta_n,3)
    ov("DGS2","dgs2",last)
    ov("DGS10","dgs10",last)
    ov("DGS30","dgs30",last)
    ov("HYOAS","hy_oas",last)
    ov("HYOAS","hy_oas_1m",delta_n,21)
    ov("IGSPR","ig_oas",last)
    ov("IGSPR","ig_oas_1m",delta_n,21)

    # Yield curve (only if both yields loaded)
    dgs2=f.get("dgs2",float("nan")); dgs10=f.get("dgs10",float("nan")); dgs30=f.get("dgs30",float("nan"))
    if math.isfinite(dgs2) and math.isfinite(dgs10):
        sp=dgs10-dgs2; f["spread_2s10s"]=sp
        f["yield_curve_state"]=("Inverted" if sp<-0.10 else "Flat" if sp<0.25 else "Normal" if sp<1.50 else "Steep")
        d2=_s(fred.get("DGS2",pd.Series())); d10=_s(fred.get("DGS10",pd.Series()))
        if len(d2)>63 and len(d10)>63:
            d2a,d10a=d2.align(d10,join="inner"); sp_ts=d10a-d2a
            f["spread_2s10s_1m"]=delta_n(sp_ts,21); f["spread_2s10s_3m"]=delta_n(sp_ts,63)
            f["yield_curve_uninverting"]=(math.isfinite(f["spread_2s10s_3m"]) and f["spread_2s10s_3m"]>0.20 and sp>-0.25)
    if math.isfinite(dgs10) and math.isfinite(dgs30):
        f["spread_10s30s"]=dgs30-dgs10

    # RoC acceleration flags
    f["indpro_acc"]   = roc_acc(fred.get("INDPRO",  pd.Series()),12,3)
    f["payrolls_acc"] = roc_acc(fred.get("PAYEMS",  pd.Series()),12,3)
    f["retail_acc"]   = roc_acc(fred.get("RSAFS",   pd.Series()),12,3)
    f["lei_acc"]      = roc_acc(fred.get("LEI",     pd.Series()),3, 2)
    f["cpi_acc"]      = roc_acc(fred.get("CPI",     pd.Series()),12,3)
    f["corepce_acc"]  = roc_acc(fred.get("COREPCE", pd.Series()),12,3)

    # Price features — always from yfinance (equities + commodities + FX)
    for t in ["SPY","QQQ","IWM","RSP","UUP","TLT","EEM","EFA","GLD","HYG","LQD",
              "XLE","XLI","XLY","XLP","XLB","XLK","XLF",
              "CL=F","GC=F","HG=F","SI=F","NG=F"]:   # ← commodity futures added
        s=prices.get(t,pd.Series())
        tk=t.replace("^","").replace("=F","f").lower()
        f[f"{tk}_1m"]=ret_n(s,21); f[f"{tk}_3m"]=ret_n(s,63); f[f"{tk}_ts"]=ts(s)

    # Copper/gold from prices (always available)
    cop=prices.get("HG=F",pd.Series()); gld=prices.get("GC=F",pd.Series())
    if not _s(cop).empty and not _s(gld).empty:
        c2,g2=_s(cop).align(_s(gld),join="inner")
        if len(c2)>63:
            cg=c2/g2; f["copper_gold_ratio_3m"]=ret_n(cg,63); f["copper_gold_ratio_last"]=float(cg.iloc[-1])

    # VIX
    vix_s=prices.get("^VIX",pd.Series()); vxv_s=prices.get("^VXV",pd.Series())
    f["vix_last"]=last(vix_s); f["vix_1m"]=delta_n(vix_s,21)
    if not _s(vix_s).empty and not _s(vxv_s).empty:
        v,vxv=_s(vix_s).align(_s(vxv_s),join="inner")
        if len(v)>5:
            r=float(v.iloc[-1])/float(vxv.iloc[-1]); f["vix_vxv_ratio"]=r
            f["vix_term_state"]=("Contango (calm)" if r<0.90 else "Flat (neutral)" if r<1.00 else "Backwardation (fear)")
        else: f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"
    else: f["vix_vxv_ratio"]=float("nan"); f["vix_term_state"]="Unknown"

    f["_fred_loaded"]=loaded; f["_fred_total"]=total
    f["_proxy_share"]=1.0-(loaded/max(total,1))
    return f

# ── Quad engine ────────────────────────────────────────────────────────────────
def build_quad(f:Dict)->Dict:
    oil_3m = f.get("clf_3m", f.get("cl_f_3m", 0.0))
    if not math.isfinite(oil_3m): oil_3m=0.0
    gld_3m = f.get("gld_3m", 0.0)
    if not math.isfinite(gld_3m): gld_3m=0.0
    uup_3m = f.get("uup_3m", 0.0)
    if not math.isfinite(uup_3m): uup_3m=0.0
    eem_3m = f.get("eem_3m", 0.0)
    if not math.isfinite(eem_3m): eem_3m=0.0

    # ── Growth composite (positive = growth accelerating/above trend) ─────────
    g_inputs=[
        th(f.get("indpro_yoy",0)-0.020, 0.050),
        th(f.get("retail_yoy",0)-0.030, 0.060),
        th(f.get("payrolls_yoy",0)-0.015,0.030),
        th(f.get("housing_yoy",0),       0.100),
        th((f.get("ism_last",50)-50)/100,0.040),
        th(-f.get("unrate_3m_delta",0),  0.120),
        th(-f.get("claims_13w_delta",0)/40,0.600),
        th(f.get("lei_3m",0),            0.030),
        th(f.get("copper_gold_ratio_3m",0),0.120),
        th(eem_3m,                        0.120),
    ]
    g_mom_inputs=[
        th(f.get("xli_3m",0),  0.080),
        th(f.get("iwm_3m",0),  0.080),
        th(f.get("spy_3m",0),  0.080),
        th(f.get("copper_gold_ratio_3m",0),0.100),
        th(-f.get("unrate_3m_delta",0),0.100),
        th(f.get("lei_3m",0),  0.025),
    ]
    # Yield curve adjustment: inverted curve = recession signal = negative growth
    yc=f.get("yield_curve_state","")
    yc_adj=(-0.12 if "Inverted" in yc else (-0.05 if f.get("yield_curve_uninverting") else 0.06 if "Normal" in yc or "Steep" in yc else 0.0))
    # Credit stress = negative growth
    hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    cred_adj=(clamp((hy-300)/600)*-0.15 if math.isfinite(hy) else 0.0)+(clamp((ig-80)/200)*-0.08 if math.isfinite(ig) else 0.0)

    g_level=nm(*g_inputs)+yc_adj+cred_adj
    g_mom=nm(*g_mom_inputs)

    # ── Inflation composite (positive = inflation rising/above target) ─────────
    core_inf=f.get("corepce_yoy",f.get("corecpi_yoy",0.023))
    headline=f.get("cpi_yoy",0.025)
    i_inputs=[
        th(headline-0.025,  0.020),
        th(core_inf-0.025,  0.015),
        th((f.get("breakeven",2.2)-2.2)/2.0,0.300),
        th(oil_3m,          0.250),
        th(gld_3m,          0.180),
    ]
    i_mom_inputs=[
        th(oil_3m/3,        0.120),
        th((f.get("breakeven",2.2)-2.2)/2.0,0.240),
        th(f.get("breakeven_1m",0),0.080),
        th(-uup_3m,         0.100),
    ]
    i_level=nm(*i_inputs); i_mom=nm(*i_mom_inputs)

    # Policy
    p_score=th(-f.get("policy_rate_3m",0),0.50)

    g_core=0.60*g_level+0.40*g_mom
    i_core=0.70*i_level+0.30*i_mom

    # Slowdown flags
    sf=sum([
        1 if math.isfinite(f.get("unrate_3m_delta",float("nan"))) and f.get("unrate_3m_delta",0)>0.05 else 0,
        1 if math.isfinite(f.get("claims_13w_delta",float("nan"))) and f.get("claims_13w_delta",0)>0 else 0,
        1 if math.isfinite(f.get("ism_last",float("nan"))) and f.get("ism_last",50)<50 else 0,
        1 if math.isfinite(f.get("housing_yoy",float("nan"))) and f.get("housing_yoy",0)<-0.05 else 0,
    ])/4.0

    # Inflation shock (oil + breakeven surge)
    inf_shock=max(0.0,th(oil_3m,0.25))*0.5+max(0.0,th(i_mom,0.3))*0.5

    raw={
        "Q1": +g_core - i_core*0.8 + 0.05*p_score,
        "Q2": +g_core + i_core*0.8 - 0.05*p_score,
        "Q3": -g_core + i_core*1.2 - 0.10*p_score + 0.10*sf + 0.08*inf_shock,
        "Q4": -g_core - i_core*0.8 + 0.20*p_score + 0.08*sf,
    }
    raw["Q1"]-=0.08*sf; raw["Q2"]-=0.05*sf+0.04*inf_shock; raw["Q2"]+=0.04*inf_shock

    arr=np.array(list(raw.values()),dtype=float)
    exp=np.exp(arr-arr.max()); prbs=(exp/exp.sum()).tolist()
    probs=dict(zip(raw.keys(),prbs))
    ordered=sorted(probs.items(),key=lambda kv:kv[1],reverse=True)
    quad=ordered[0][0]; top_p=ordered[0][1]; next_q=ordered[1][0]; margin=top_p-ordered[1][1]
    conf=clamp(top_p*0.75+margin*0.25)
    flip_h=clamp(0.35*(1-margin)+0.20*abs(g_mom)+0.20*abs(i_mom)+0.15*(1.0 if "Inverted" in yc else 0.0)+0.10*sf)

    # RoC flags: prefer FRED, fallback to score direction
    g_acc=f.get("indpro_acc") or f.get("payrolls_acc")
    if g_acc is None: g_acc=(g_level>0)
    i_acc=f.get("cpi_acc") or f.get("corepce_acc")
    if i_acc is None: i_acc=(i_level>0)

    return dict(quad=quad,probs=probs,next_quad=next_q,confidence=conf,flip_hazard=flip_h,
                g_level=g_level,g_mom=g_mom,i_level=i_level,i_mom=i_mom,
                g_core=g_core,i_core=i_core,growth_acc=g_acc,infl_acc=i_acc,
                slowdown_flags=sf,inf_shock=inf_shock)

# ── Market health ──────────────────────────────────────────────────────────────
def build_health(prices:Dict[str,pd.Series], f:Dict)->Dict:
    SECS=["XLE","XLF","XLI","XLB","XLK","XLV","XLY","XLP","XLU","XLRE","XLC"]
    spy_t=ts(prices.get("SPY",pd.Series())); qqq_t=ts(prices.get("QQQ",pd.Series()))
    iwm_t=ts(prices.get("IWM",pd.Series()))
    spy_3m=f.get("spy_3m",0.0); rsp_3m=ret_n(prices.get("RSP",pd.Series()),63)
    eqw_vs_cw=(rsp_3m-spy_3m) if(math.isfinite(rsp_3m) and math.isfinite(spy_3m)) else 0.0
    ab50=sum(1 for t in SECS if len(_s(prices.get(t,pd.Series())))>=50 and float(_s(prices.get(t,pd.Series())).iloc[-1])>float(_s(prices.get(t,pd.Series())).rolling(50).mean().iloc[-1]))
    sec_s=ab50/len(SECS)
    breadth=clamp(nm(spy_t,iwm_t,sec_s,clamp(0.5+eqw_vs_cw*5)))
    hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    hy_h=clamp(1.0-(hy-250)/500) if math.isfinite(hy) else 0.5
    ig_h=clamp(1.0-(ig-50)/200)  if math.isfinite(ig) else 0.5
    hyg_t=ts(prices.get("HYG",pd.Series()))
    credit=clamp(nm(hy_h,ig_h,hyg_t))
    vix=f.get("vix_last",20.0); vix_h=clamp(1.0-(vix-13)/25)
    vr=f.get("vix_vxv_ratio",float("nan"))
    vix_ts=clamp(1.0-(vr-0.85)/0.25) if math.isfinite(vr) else 0.5
    vol=clamp(nm(vix_h,vix_ts))
    uup_1m=f.get("uup_1m",0.0); uup_1m=0.0 if not math.isfinite(uup_1m) else uup_1m
    dh=clamp(0.5+uup_1m*8)
    trade=clamp(nm(breadth,credit,1.0-dh*0.3))
    trend_=clamp(nm(spy_t,qqq_t,sec_s))
    tail=clamp(nm(vol,credit,1.0-dh*0.4))
    weather=clamp(0.35*trade+0.35*trend_+0.30*tail)
    def s3(v,hi=0.62,lo=0.42,lb=("Healthy","Mixed","Fragile")): return lb[0] if v>=hi else(lb[2] if v<=lo else lb[1])
    return dict(breadth=breadth,credit=credit,vol=vol,weather=weather,trade=trade,trend=trend_,tail=tail,
                sec_above50=ab50,sec_support=sec_s,eqw_vs_cw=eqw_vs_cw,dollar_hw=dh,spy_trend=spy_t,iwm_trend=iwm_t,
                breadth_state=s3(breadth),credit_state=s3(credit,lb=("Tight","Watch","Stressed")),
                vol_state=s3(vol,lb=("Calm","Watch","Stressed")),trade_state=s3(trade,lb=("Open","Neutral","Closed")),
                weather_state="Risk-On" if weather>=0.58 else("Risk-Off" if weather<=0.42 else "Mixed"))

# ── Crash meter ────────────────────────────────────────────────────────────────
def build_crash(f:Dict,h:Dict,q:Dict)->Dict:
    vix=f.get("vix_last",20.0); hy=f.get("hy_oas",350.0); ig=f.get("ig_oas",100.0)
    vs=clamp((vix-18)/20); hs=clamp((hy-300)/400) if math.isfinite(hy) else 0.3
    is_=clamp((ig-80)/120) if math.isfinite(ig) else 0.3
    cs=clamp(0.60*hs+0.40*is_); bd=clamp(1.0-h.get("breadth",0.5)); dh=h.get("dollar_hw",0.5)
    gr=clamp(0.5-q.get("g_core",0.0))
    score=clamp(0.25*vs+0.20*cs+0.18*bd+0.15*dh+0.12*gr+0.10*(1.0-h.get("weather",0.5)))
    ro=clamp(0.30*(1.0-h.get("weather",0.5))+0.25*bd+0.20*cs+0.15*dh+0.10*vs)
    rs=[]
    if vs>=0.45: rs.append(f"VIX elevated ({vix:.1f})")
    if hs>=0.40 and math.isfinite(hy): rs.append(f"HY spreads wide ({hy:.0f}bps)")
    if is_>=0.40 and math.isfinite(ig): rs.append(f"IG spreads wide ({ig:.0f}bps)")
    if bd>=0.55: rs.append("Market breadth deteriorating")
    if dh>=0.65: rs.append("USD pressure elevated")
    if f.get("vix_term_state","")=="Backwardation (fear)": rs.append("VIX in backwardation — near-term panic")
    if f.get("yield_curve_uninverting"): rs.append("Yield curve uninverting — recession risk rising")
    if q.get("slowdown_flags",0)>=0.50: rs.append("Multiple growth slowdown flags active")
    state="🔴 ELEVATED" if score>=0.65 else("🟡 WATCH" if score>=0.42 else "🟢 CALM")
    return dict(score=score,risk_off=ro,state=state,vol_stress=vs,credit_stress=cs,breadth_dmg=bd,reasons=rs[:6])

# ── Opportunities ──────────────────────────────────────────────────────────────
def build_opps(q:Dict,h:Dict)->list:
    quad=q.get("quad","Q4"); meta=QUAD_META.get(quad,QUAD_META["Q4"])
    conf=q.get("confidence",0.5); wthr=h.get("weather",0.5)
    rows=[]
    for i,a in enumerate(meta["long"]): rows.append({"Asset":a,"Side":"LONG ▲","Regime":quad,"EV":f"{clamp(conf*0.6+wthr*0.4-i*0.06):.0%}","Why":f"{quad} historically favors this class"})
    for i,a in enumerate(meta["hedge"]): rows.append({"Asset":a,"Side":"HEDGE ◈","Regime":quad,"EV":f"{clamp((1-conf)*0.5+(1-wthr)*0.5-i*0.04):.0%}","Why":"Regime-appropriate hedge"})
    for i,a in enumerate(meta["avoid"]): rows.append({"Asset":a,"Side":"AVOID ▼","Regime":quad,"EV":f"{clamp(0.30-i*0.04):.0%}","Why":f"{quad} is a headwind for this class"})
    return rows

# ── Data orchestration ─────────────────────────────────────────────────────────
@st.cache_data(ttl=CACHE_TTL,show_spinner=False)
def load_snapshot()->Dict:
    with st.spinner("Fetching prices from Yahoo Finance…"):
        prices=fetch_prices(tuple(PRICE_TICKERS),period="2y")
    with st.spinner("Fetching FRED macro data…"):
        fred={k:fetch_fred(v) for k,v in FRED_SERIES.items()}
    f=build_macro(fred,prices); h=build_health(prices,f)
    q=build_quad(f); cr=build_crash(f,h,q); op=build_opps(q,h)
    return dict(prices=prices,fred=fred,f=f,h=h,q=q,crash=cr,opps=op,
                ts=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"))

# ── UI helpers ─────────────────────────────────────────────────────────────────
def qb(q:str)->str:
    cls=q.lower() if q in("Q1","Q2","Q3","Q4") else "qunk"
    return f'<span class="qb {cls}">{q}</span>'
def mc(label:str,value:str,sub:str="",cls:str="")->None:
    st.markdown(f'<div class="mc"><div class="lb">{label}</div><div class="vl {cls}">{value}</div>{"<div class=sb>"+sub+"</div>" if sub else""}</div>',unsafe_allow_html=True)
def sh(t:str)->None: st.markdown(f'<div class="sh">{t}</div>',unsafe_allow_html=True)
def gb(label:str,v:float,note:str="",gd:str="high")->None:
    v=clamp(v); fill=v if gd=="high" else 1.0-v
    col="#3dbb6c" if fill>=0.62 else("#e5a020" if fill>=0.38 else "#e05252")
    st.markdown(f'<div class="gb"><div class="gr"><span>{label}</span><span style="color:{col};font-size:11px;font-family:DM Mono,monospace">{pct(v)} {note}</span></div><div class="bg"><div class="fl" style="width:{v*100:.0f}%;background:{col}"></div></div></div>',unsafe_allow_html=True)

# ── Page: Radar ───────────────────────────────────────────────────────────────
def page_radar(snap:Dict)->None:
    q=snap["q"]; f=snap["f"]; h=snap["h"]
    quad=q["quad"]; meta=QUAD_META.get(quad,QUAD_META["Q4"]); conf=q["confidence"]
    ps=f.get("_proxy_share",1.0); fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0))
    if ps>0.60:
        st.markdown(f'<div class="proxy-b">⚠️ <strong>Proxy mode</strong> — FRED loaded {fl}/{ft} series. Quad derived from price proxies (ETFs/futures). Set FRED_API_KEY env var for direct FRED access. Check Diagnostics tab.</div>',unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="real-b">✓ FRED data loaded ({fl}/{ft} series). Price data from Yahoo Finance.</div>',unsafe_allow_html=True)

    st.markdown(f'<div class="rh"><div style="margin-bottom:6px">{qb(quad)}</div><div class="rn" style="color:{meta["text"]}">{meta["label"]}</div><div class="rs">{meta["name"]} · Confidence {conf:.0%}</div><div class="re">{meta["explain"]}</div></div>',unsafe_allow_html=True)
    st.markdown("---")

    c1,c2,c3,c4=st.columns(4)
    with c1:
        g_acc=q.get("growth_acc"); lbl=acc_txt(g_acc)
        mc("Growth Rate-of-Change",lbl,"vs 3 months ago","good" if g_acc else "bad")
    with c2:
        i_acc=q.get("infl_acc"); lbl=acc_txt(i_acc)
        mc("Inflation Rate-of-Change",lbl,"vs 3 months ago","bad" if i_acc else "good")
    with c3:
        vix=f.get("vix_last",0); vb="Investable" if vix<19 else("Chop" if vix<29 else "Defensive")
        mc("VIX",f"{vix:.1f}" if math.isfinite(vix) else "—",f"{vb} · {f.get('vix_term_state','')}",
           "good" if vix<19 else("bad" if vix>28 else "warn"))
    with c4:
        sp=f.get("spread_2s10s",float("nan")); yc=f.get("yield_curve_state","Unknown")
        mc("Yield Curve 2s10s",f"{sp:+.2f}%" if math.isfinite(sp) else "—",yc,
           "good" if("Normal" in yc or"Steep" in yc) else("bad" if"Inverted" in yc else "warn"))

    st.markdown("---")
    ca,cb=st.columns(2)
    with ca:
        sh("📊 REGIME PROBABILITY")
        probs=q.get("probs",{})
        for qk in ["Q1","Q2","Q3","Q4"]:
            p=probs.get(qk,0.0); act="● " if qk==quad else "  "
            fc="#3dbb6c" if qk==quad else "rgba(255,255,255,0.12)"
            st.markdown(f'<div style="display:flex;align-items:center;gap:8px;margin-bottom:5px"><span style="font-family:DM Mono,monospace;font-size:11px;width:30px;color:{"#3dbb6c" if qk==quad else "#888"}">{act}{qk}</span><div style="flex:1;background:rgba(255,255,255,0.07);border-radius:3px;height:7px;overflow:hidden"><div style="width:{p*100:.0f}%;background:{fc};height:100%"></div></div><span style="font-family:DM Mono,monospace;font-size:11px;width:36px;text-align:right">{p:.0%}</span></div>',unsafe_allow_html=True)
        flag="⚠️ High transition risk" if q.get("flip_hazard",0)>0.50 else "Regime stable"
        st.caption(f"Flip hazard: **{q.get('flip_hazard',0):.0%}** — {flag} · Next likely: **{q.get('next_quad','?')}**")
    with cb:
        sh(f"📍 WHAT TO DO IN {quad}")
        st.markdown(f"**{meta.get('label','')}**")
        st.markdown("**Go Long →**")
        for a in meta.get("long",[])[:4]: st.markdown(f'<div class="olong">{a}</div>',unsafe_allow_html=True)
        st.markdown("**Hedge →**")
        for a in meta.get("hedge",[])[:2]: st.markdown(f'<div class="ohedge">{a}</div>',unsafe_allow_html=True)
        st.markdown("**Avoid →**")
        for a in meta.get("avoid",[])[:3]: st.markdown(f'<div class="oshort">{a}</div>',unsafe_allow_html=True)

    st.markdown("---")
    sh("🔑 KEY HEDGEYE INDICATORS (plain text — no HTML)")
    rows=[
        ("── GROWTH ──","","",""),
        ("Industrial Production YoY",pct(f.get("indpro_yoy",float("nan"))),acc_txt(f.get("indpro_acc")),""),
        ("Nonfarm Payrolls YoY",pct(f.get("payrolls_yoy",float("nan"))),acc_txt(f.get("payrolls_acc")),""),
        ("Retail Sales YoY",pct(f.get("retail_yoy",float("nan"))),acc_txt(f.get("retail_acc")),""),
        ("ISM Manufacturing PMI",num(f.get("ism_last",float("nan")),1),"","Above 50 = expansion"),
        ("LEI 3M Change ★",pct(f.get("lei_3m",float("nan"))),acc_txt(f.get("lei_acc")),"Leading indicator"),
        ("Copper/Gold Ratio 3M ★",pct(f.get("copper_gold_ratio_3m",float("nan"))),"","Growth proxy"),
        ("Unemployment Rate",f"{f.get('unrate',float('nan')):.1f}%" if math.isfinite(f.get("unrate",float("nan"))) else "—",
         f"3M Δ: {f.get('unrate_3m_delta',0):+.2f}" if math.isfinite(f.get("unrate_3m_delta",float("nan"))) else "",""),
        ("Initial Claims 13W Δ",num(f.get("claims_13w_delta",float("nan")),0),"","Weekly"),
        ("UMich Consumer Sentiment ★",num(f.get("umcsent_last",float("nan")),1),"","Below 70 = stressed"),
        ("Housing Starts YoY",pct(f.get("housing_yoy",float("nan"))),"",""),
        ("── INFLATION ──","","",""),
        ("CPI YoY",pct(f.get("cpi_yoy",float("nan"))),acc_txt(f.get("cpi_acc")),""),
        ("Core CPI YoY",pct(f.get("corecpi_yoy",float("nan"))),"",""),
        ("Core PCE YoY ★",pct(f.get("corepce_yoy",float("nan"))),acc_txt(f.get("corepce_acc")),"Fed preferred"),
        ("5Y Breakeven Inflation",num(f.get("breakeven",float("nan")),2),
         f"1M Δ: {f.get('breakeven_1m',0):+.3f}" if math.isfinite(f.get("breakeven_1m",float("nan"))) else "","Market expectation"),
        ("── RATES / YIELD CURVE ──","","",""),
        ("Fed Funds Rate",num(f.get("policy_rate",float("nan")),2),
         f"3M Δ: {f.get('policy_rate_3m',0):+.2f}" if math.isfinite(f.get("policy_rate_3m",float("nan"))) else "",""),
        ("2Y Treasury Yield",num(f.get("dgs2",float("nan")),3),"",""),
        ("10Y Treasury Yield",num(f.get("dgs10",float("nan")),3),"",""),
        ("2s10s Yield Curve ★",
         f"{f.get('spread_2s10s',float('nan')):+.2f}%" if math.isfinite(f.get("spread_2s10s",float("nan"))) else "—",
         f.get("yield_curve_state",""),"Inverted = recession risk"),
        ("10Y Real Yield (TIPS)",num(f.get("real_10y",float("nan")),2),"","+ve = restrictive"),
        ("── CREDIT & VOL ──","","",""),
        ("HY OAS Spread",
         f"{f.get('hy_oas',float('nan')):.0f}bps" if math.isfinite(f.get("hy_oas",float("nan"))) else "—",
         f"1M Δ: {f.get('hy_oas_1m',0):+.0f}bps" if math.isfinite(f.get("hy_oas_1m",float("nan"))) else "","Junk credit stress"),
        ("IG OAS Spread ★",
         f"{f.get('ig_oas',float('nan')):.0f}bps" if math.isfinite(f.get("ig_oas",float("nan"))) else "—",
         f"1M Δ: {f.get('ig_oas_1m',0):+.0f}bps" if math.isfinite(f.get("ig_oas_1m",float("nan"))) else "","IG credit stress"),
        ("VIX Level",num(f.get("vix_last",float("nan")),1),f.get("vix_term_state",""),""),
        ("VIX/VXV Term Structure ★",num(f.get("vix_vxv_ratio",float("nan")),3),
         f.get("vix_term_state",""),"<1 = contango/calm, >1 = backwardation/fear"),
    ]
    df=pd.DataFrame(rows,columns=["Indicator","Value","Rate of Change","Note"])
    st.dataframe(df,use_container_width=True,hide_index=True,height=660)
    st.caption("★ = Added vs v33 (Hedgeye gaps). In proxy mode, values estimated from ETF/futures price action.")

# ── Page: Market Health ────────────────────────────────────────────────────────
def page_health(snap:Dict)->None:
    h=snap["h"]; f=snap["f"]; prices=snap["prices"]
    sh("📡 TACTICAL WEATHER — CAN WE TRADE?")
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
        gb("Sectors above 50-DMA",h["sec_support"],note=f"({h['sec_above50']}/11)")
        gb("SPY trend health",h["spy_trend"])
        gb("Small cap health (IWM)",h["iwm_trend"])
        gb("Equal-weight vs cap-weight",clamp(0.5+h["eqw_vs_cw"]*5),note=pct(h["eqw_vs_cw"])+" 3M diff")
        gb("Breadth composite",h["breadth"])
    with cb:
        sh("⚡ CREDIT & VOL GAUGES")
        hy=f.get("hy_oas",float("nan")); ig=f.get("ig_oas",float("nan"))
        gb("HY Credit health",clamp(1.0-(hy-250)/500) if math.isfinite(hy) else 0.5,note=f"{hy:.0f}bps" if math.isfinite(hy) else "proxy")
        gb("IG Credit health ★",clamp(1.0-(ig-50)/200) if math.isfinite(ig) else 0.5,note=f"{ig:.0f}bps" if math.isfinite(ig) else "n/a")
        vix=f.get("vix_last",20.0); gb("VIX health (lower = better)",clamp(1.0-(vix-13)/25),note=f"VIX {vix:.1f}")
        vr=f.get("vix_vxv_ratio",float("nan"))
        gb("VIX term structure ★",clamp(1.0-(vr-0.85)/0.25) if math.isfinite(vr) else 0.5,note=f.get("vix_term_state",""))
        gb("Credit + Vol composite",(h["credit"]+h["vol"])/2)
    st.markdown("---")
    sh("📈 YIELD CURVE — THE MACRO BAROMETER ★")
    ycd={"2Y":f.get("dgs2",float("nan")),"10Y":f.get("dgs10",float("nan")),"30Y":f.get("dgs30",float("nan"))}
    yv={k:v for k,v in ycd.items() if math.isfinite(v)}
    if yv: st.dataframe(pd.DataFrame([{"Tenor":k,"Yield (%)":round(v,3)} for k,v in yv.items()]),use_container_width=False,hide_index=True,height=130)
    else:  st.warning("Yield data unavailable (FRED not responding). Running in proxy mode.")
    y1,y2,y3=st.columns(3)
    sp=f.get("spread_2s10s",float("nan")); sp30=f.get("spread_10s30s",float("nan")); sp3m=f.get("spread_2s10s_3m",float("nan"))
    with y1: mc("2s10s Spread",f"{sp:+.2f}%" if math.isfinite(sp) else "—",f.get("yield_curve_state",""),"good" if(math.isfinite(sp) and sp>0.5) else("bad" if(math.isfinite(sp) and sp<0) else "warn"))
    with y2: mc("10s30s Spread",f"{sp30:+.2f}%" if math.isfinite(sp30) else "—")
    with y3: mc("2s10s 3M Δ",f"{sp3m:+.2f}%" if math.isfinite(sp3m) else "—","Uninverting → recession closer" if f.get("yield_curve_uninverting") else "","warn" if f.get("yield_curve_uninverting") else "neu")
    st.info("> **Yield curve:** When 2Y > 10Y = inverted = recession risk. When inverted curve *steepens* (uninverts), the recession is typically starting, not ending.")
    st.markdown("---")
    sh("📦 SECTOR PERFORMANCE vs SPY (3M)")
    SECS={"XLE":"Energy","XLF":"Financials","XLI":"Industrials","XLB":"Materials","XLK":"Technology","XLV":"Healthcare","XLY":"Cons.Disc.","XLP":"Cons.Staples","XLU":"Utilities","XLRE":"Real Estate","XLC":"Comm.Svc."}
    spy3=ret_n(prices.get("SPY",pd.Series()),63); rows=[]
    for t,name in SECS.items():
        s=prices.get(t,pd.Series()); r3=ret_n(s,63); r1=ret_n(s,21)
        rel=(r3-spy3) if(math.isfinite(r3) and math.isfinite(spy3)) else float("nan")
        rows.append({"Sector":name,"3M Return":pct(r3),"1M Return":pct(r1),"vs SPY 3M":pct(rel),"Above 50D MA":"✓" if ts(s)>=0.5 else "✗"})
    rows.sort(key=lambda r:float(r["vs SPY 3M"].replace("%","").replace("—","0").replace("+","")) if r["vs SPY 3M"]!="—" else -999,reverse=True)
    st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,height=380)

# ── Page: Opportunities ────────────────────────────────────────────────────────
def page_opps(snap:Dict)->None:
    q=snap["q"]; opps=snap["opps"]; prices=snap["prices"]
    quad=q["quad"]; meta=QUAD_META.get(quad,QUAD_META["Q4"])
    st.markdown(f'<div style="padding:14px 18px;border-radius:10px;background:{meta["color"]}22;border:1px solid {meta["color"]}55;margin-bottom:14px"><strong>REGIME {quad}: {meta["label"]}</strong> · Confidence {q["confidence"]:.0%}<br><span style="font-size:12px;opacity:.8">Ranked by regime alignment</span></div>',unsafe_allow_html=True)
    df=pd.DataFrame(opps)
    if not df.empty:
        ta,tb,tc=st.tabs(["▲ Longs / Best Now","◈ Hedges / Safe Harbor","▼ Avoid / Short Bias"])
        with ta: st.dataframe(df[df.Side.str.startswith("LONG")].reset_index(drop=True),use_container_width=True,hide_index=True)
        with tb: st.dataframe(df[df.Side.str.startswith("HEDGE")].reset_index(drop=True),use_container_width=True,hide_index=True)
        with tc: st.dataframe(df[df.Side.str.startswith("AVOID")].reset_index(drop=True),use_container_width=True,hide_index=True)
    st.markdown("---"); sh("🌐 CROSS-ASSET RETURNS HEATMAP")
    ASSETS={"US Equity (SPY)":"SPY","Growth (QQQ)":"QQQ","Small Cap (IWM)":"IWM","Bonds (TLT)":"TLT","Credit (HYG)":"HYG","Gold (GLD)":"GLD","Oil (CL=F)":"CL=F","Copper (HG=F)":"HG=F","USD (UUP)":"UUP","EM Equity (EEM)":"EEM","BTC":"BTC-USD","ETH":"ETH-USD"}
    heat=[]
    for name,t in ASSETS.items():
        s=prices.get(t,pd.Series())
        heat.append({"Asset":name,"1W":pct(ret_n(s,5)),"1M":pct(ret_n(s,21)),"3M":pct(ret_n(s,63)),"6M":pct(ret_n(s,126)),"1Y":pct(ret_n(s,252))})
    st.dataframe(pd.DataFrame(heat),use_container_width=True,hide_index=True,height=430)
    st.markdown("---"); sh(f"📖 REGIME {quad} — HISTORICAL CONTEXT")
    ctx={"Q1":"**Q1 Goldilocks:** Best period for risk assets. S&P avg ~+18% annual in Q1 environments. Duration (TLT) also works. The 'don't fight the tape' quad.",
         "Q2":"**Q2 Reflation:** Risk assets work but leadership rotates to value/cyclicals. Energy + materials outperform tech. Watch Q2→Q3 inflection as tightening bites.",
         "Q3":"**Q3 Stagflation:** The hardest quad. Equities broadly underperform. Gold and energy are the few safe-ish longs. Cash is a position. Avoid duration, consumer, and EM.",
         "Q4":"**Q4 Deflation:** Bonds rally hard. Defensives outperform. Central banks cut eventually. Maximum caution on cyclicals, credit, and EM."}
    if quad in ctx: st.info(ctx[quad])

# ── Page: Risk Monitor ────────────────────────────────────────────────────────
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
    st.markdown("---"); sh("📉 VIX REGIME & TERM STRUCTURE ★")
    vix=f.get("vix_last",20.0); vr=f.get("vix_vxv_ratio",float("nan"))
    v1,v2,v3=st.columns(3)
    with v1: mc("VIX Bucket","Investable (<19)" if vix<19 else("Chop (19-29)" if vix<29 else "Defensive (>29)"),f"VIX = {vix:.1f}","good" if vix<19 else("warn" if vix<29 else "bad"))
    with v2: mc("VIX/VXV Ratio ★",f"{vr:.3f}" if math.isfinite(vr) else "—",f.get("vix_term_state",""),"good" if(math.isfinite(vr) and vr<0.90) else("bad" if(math.isfinite(vr) and vr>=1.0) else "warn"))
    with v3: rmode="Normal" if vix<19 else("Reduced" if vix<29 else "Defensive"); mc("Risk Mode",rmode,"sizing guide","good" if rmode=="Normal" else("warn" if rmode=="Reduced" else "bad"))
    st.info("> **VIX term structure:** VIX < VXV = contango (calm/normal). VIX > VXV = backwardation (near-term panic). Backwardation is a 'something is breaking' signal.")
    st.markdown("---"); sh("💳 CREDIT SPREAD DETAIL ★")
    hy=f.get("hy_oas",float("nan")); ig=f.get("ig_oas",float("nan"))
    hy1m=f.get("hy_oas_1m",float("nan")); ig1m=f.get("ig_oas_1m",float("nan"))
    c1,c2=st.columns(2)
    with c1: mc("HY OAS Spread",f"{hy:.0f}bps" if math.isfinite(hy) else "—",f"1M Δ: {hy1m:+.0f}bps" if math.isfinite(hy1m) else "","good" if(math.isfinite(hy) and hy<350) else("bad" if(math.isfinite(hy) and hy>500) else "warn")); st.caption("Normal: <350bps | Watch: 350-500bps | Stress: >500bps")
    with c2: mc("IG OAS Spread ★",f"{ig:.0f}bps" if math.isfinite(ig) else "—",f"1M Δ: {ig1m:+.0f}bps" if math.isfinite(ig1m) else "","good" if(math.isfinite(ig) and ig<100) else("bad" if(math.isfinite(ig) and ig>150) else "warn")); st.caption("Normal: <100bps | Watch: 100-150bps | Stress: >150bps")
    st.markdown("---"); sh("🔭 FORWARD RISK FACTORS")
    lei=f.get("lei_3m",float("nan")); cg=f.get("copper_gold_ratio_3m",float("nan")); umi=f.get("umcsent_last",float("nan"))
    st.markdown(f"""
- **Regime flip hazard:** {q.get("flip_hazard",0):.0%} → Next likely quad: **{q.get("next_quad","?")}**
- **Yield curve:** {f.get("yield_curve_state","")} | 3M change: {pct(f.get("spread_2s10s_3m",float("nan")))}
- **LEI 3M:** {pct(lei)} {"⚠️ Leading indicator declining" if(math.isfinite(lei) and lei<-0.01) else("✓ LEI holding" if math.isfinite(lei) else "(proxy mode)")}
- **Copper/Gold ratio 3M:** {pct(cg)} {"→ growth expectations falling" if(math.isfinite(cg) and cg<-0.05) else "→ growth expectations holding"}
- **UMich Sentiment:** {num(umi,1)} {"⚠️ Below 70 — stressed consumer" if(math.isfinite(umi) and umi<70) else ""}
- **Growth slowdown flags:** {q.get("slowdown_flags",0):.0%} of 4 active
    """)

# ── Page: Diagnostics ─────────────────────────────────────────────────────────
def page_diag(snap:Dict)->None:
    f=snap["f"]; fred=snap["fred"]; prices=snap["prices"]
    fl=int(f.get("_fred_loaded",0)); ft=int(f.get("_fred_total",0)); ps=f.get("_proxy_share",1.0)
    sh("📋 FRED DATA COVERAGE")
    cov=[]
    for k,s in fred.items():
        sc=_s(s)
        cov.append({"Series":k,"FRED ID":FRED_SERIES.get(k,""),"Points":len(sc),
                    "Latest":str(sc.index[-1])[:10] if not sc.empty else "—",
                    "Last Value":round(float(sc.iloc[-1]),4) if not sc.empty else None,
                    "Status":"✓ Loaded" if not sc.empty else "✗ Missing"})
    st.dataframe(pd.DataFrame(cov),use_container_width=True,hide_index=True,height=500)
    if ps>0.50:
        st.warning(f"""**FRED loading issues ({fl}/{ft} series loaded).**
Causes: network firewall blocking fred.stlouisfed.org | FRED rate limit | Streamlit Cloud restrictions.
Fix: Set `FRED_API_KEY` env var (free at fred.stlouisfed.org/api/key/). App continues in proxy mode.""")
    sh("📦 PRICE DATA COVERAGE")
    prows=[{"Ticker":t,"Points":len(s),"Latest":str(s.index[-1])[:10] if not s.empty else "—","Last Close":round(float(s.iloc[-1]),4) if not s.empty else None} for t,s in sorted(prices.items())]
    st.dataframe(pd.DataFrame(prows),use_container_width=True,hide_index=True,height=400)
    sh("🔬 RAW MACRO FEATURES")
    frows=[]
    for k,v in sorted(f.items()):
        if k.startswith("_"): continue
        if isinstance(v,(int,float)): frows.append({"Feature":k,"Value":round(v,5) if math.isfinite(v) else "NaN"})
        elif isinstance(v,bool): frows.append({"Feature":k,"Value":str(v)})
        elif isinstance(v,str): frows.append({"Feature":k,"Value":v})
    st.dataframe(pd.DataFrame(frows),use_container_width=True,hide_index=True,height=500)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown('<div style="display:flex;align-items:center;margin-bottom:4px"><span style="font-family:Syne,sans-serif;font-size:20px;font-weight:800;letter-spacing:-.03em">🧭 MacroRegime Pro</span><span style="font-size:10px;opacity:.3;margin-left:8px;font-family:DM Mono,monospace">v4.1 · Hedgeye GIP Framework</span></div>',unsafe_allow_html=True)
    with st.sidebar:
        st.markdown("### ⚙️ Controls")
        if st.button("🔄 Force Refresh",use_container_width=True):
            st.cache_data.clear(); st.rerun()
        st.markdown("---")
        st.markdown("""
**Reading order:**
1. 🧭 **Radar** — What regime are we in?
2. 📡 **Market Health** — Can we trade?
3. 🎯 **Opportunities** — Where to position?
4. ⚠️ **Risk Monitor** — What breaks this?
5. 🔬 **Diagnostics** — Data quality

**Proxy mode:** When FRED is unavailable, macro inputs are estimated from ETF/futures price action. The quad still runs — it uses market prices as real-time leading indicators instead of lagged FRED data.
        """)
    snap=load_snapshot()
    q=snap["q"]; f=snap["f"]; cr=snap["crash"]; quad=q["quad"]; meta=QUAD_META.get(quad,{})
    ga="▲" if q.get("growth_acc") else "▼"; ia="▲" if q.get("infl_acc") else "▼"
    st.markdown(f'<div style="display:flex;gap:10px;align-items:center;flex-wrap:wrap;padding:8px 12px;border-radius:8px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);margin-bottom:12px;font-size:11px"><span>Regime: {qb(quad)} <strong>{meta.get("label","")}</strong></span><span style="opacity:.25">|</span><span>Confidence: <strong>{q["confidence"]:.0%}</strong></span><span style="opacity:.25">|</span><span>Growth: <strong>{ga} {"Accelerating" if q.get("growth_acc") else "Decelerating"}</strong></span><span style="opacity:.25">|</span><span>Inflation: <strong>{ia} {"Accelerating" if q.get("infl_acc") else "Decelerating"}</strong></span><span style="opacity:.25">|</span><span>Risk: <strong>{cr["state"]}</strong></span><span style="opacity:.25">|</span><span style="opacity:.3">{snap["ts"]}</span></div>',unsafe_allow_html=True)
    tabs=st.tabs(["🧭 Radar","📡 Market Health","🎯 Opportunities","⚠️ Risk Monitor","🔬 Diagnostics"])
    with tabs[0]: page_radar(snap)
    with tabs[1]: page_health(snap)
    with tabs[2]: page_opps(snap)
    with tabs[3]: page_risk(snap)
    with tabs[4]: page_diag(snap)

if __name__=="__main__": main()
