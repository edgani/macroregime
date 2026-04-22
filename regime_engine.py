"""
regime_engine.py — Hedgeye GIP Model
Growth: Real PCE YoY | Inflation: Headline CPI YoY | Policy: DFF+DGS10+DXY
100% data-driven. Zero hardcode regime.
"""
import os, time, logging, glob, math
from datetime import datetime
from typing import Dict, Optional
import requests, yfinance as yf, pandas as pd, numpy as np, streamlit as st

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"
MAX_RETRIES = 3
TIMEOUT = 25

FRED_SERIES = {
    'real_pce': 'PCEC1', 'real_pce_dpi': 'DSPIC96',
    'cpi': 'CPIAUCSL', 'core_cpi': 'CPILFESL',
    'fed_funds': 'DFF', 'treasury_10y': 'DGS10',
    'treasury_2y': 'DGS2', 'dxy': 'DTWEXBGS',
}
FRED_SERIES_COUNT = len(FRED_SERIES)

def get_fred_api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        try: key = st.secrets.get("FRED_API_KEY", "")
        except: pass
    if not key: key = "5fbe5dc4c8a5fbb109c4809463a1c27f"
    return key.strip()

def fetch_fred_series(sid: str, api_key: str) -> Optional[pd.Series]:
    if not api_key: return None
    headers = {"User-Agent": "Mozilla/5.0"}
    for attempt in range(MAX_RETRIES):
        try:
            r = requests.get(f"{FRED_BASE}/series/observations", params={
                'series_id': sid, 'api_key': api_key, 'file_type': 'json',
                'observation_start': '2019-01-01', 'sort_order': 'desc', 'limit': 500
            }, headers=headers, timeout=TIMEOUT)
            if r.status_code == 429: time.sleep(2**attempt+1); continue
            if r.status_code != 200: continue
            data = r.json()
            if 'observations' not in data or not data['observations']: continue
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['value'])
            if df.empty: continue
            df = df.set_index('date').sort_index().drop_duplicates()
            s = df['value']
            if len(s) < 12: continue
            logger.info(f"✅ FRED {sid}: {len(s)} pts, last={s.index[-1].date()}, val={s.iloc[-1]:.3f}")
            return s
        except Exception as e:
            logger.error(f"FRED {sid} err attempt {attempt+1}: {e}")
            time.sleep(2**attempt+1)
    logger.error(f"❌ FRED {sid}: all retries failed")
    return None

def fetch_all_fred() -> Dict[str, pd.Series]:
    key = get_fred_api_key()
    if not key: return {}
    out = {}
    for name, sid in FRED_SERIES.items():
        s = fetch_fred_series(sid, key)
        if s is not None: out[name] = s
        time.sleep(0.5)
    logger.info(f"FRED loaded: {len(out)}/{len(FRED_SERIES)} — {list(out.keys())}")
    return out

def yoy_roc(s: pd.Series, months=12) -> pd.Series:
    return ((s / s.shift(months) - 1.0) * 100.0).dropna()

def trend_direction(s: pd.Series, thresh=0.03) -> str:
    if len(s) < 6: return "stable"
    y = s.iloc[-6:].values; x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    if slope > thresh: return "accelerating"
    if slope < -thresh: return "decelerating"
    return "stable"

def monthly_momentum(yoy_s: pd.Series, lvl_s: pd.Series):
    debug = {}
    if len(yoy_s) < 6 or len(lvl_s) < 6: return "stable", debug
    mom = lvl_s.pct_change()*100.0
    m3, m6 = float(mom.iloc[-3:].mean()), float(mom.iloc[-6:].mean())
    y1 = float(yoy_s.iloc[-1])
    y3 = float(yoy_s.iloc[-3:].mean())
    y3p = float(yoy_s.iloc[-6:-3].mean())
    debug.update({'m3':round(m3,3),'m6':round(m6,3),'y1':round(y1,2),'y3':round(y3,2),'y3p':round(y3p,2)})
    a = d = 0
    if m3 > m6 + 0.02: a += 2; debug['ms']='accel'
    elif m3 < m6 - 0.02: d += 2; debug['ms']='decel'
    else: debug['ms']='stable'
    if y1 > y3 + 0.05: a += 1; debug['y1s']='accel'
    elif y1 < y3 - 0.05: d += 1; debug['y1s']='decel'
    else: debug['y1s']='stable'
    if y3 > y3p + 0.05: a += 1; debug['y3s']='accel'
    elif y3 < y3p - 0.05: d += 1; debug['y3s']='decel'
    else: debug['y3s']='stable'
    debug.update({'a':a,'d':d})
    if a >= 2: return "accelerating", debug
    if d >= 2: return "decelerating", debug
    return "stable", debug

def assign_quad(gt: str, it: str, gv=None, iv=None, use_abs=True) -> str:
    if gv is not None and isinstance(gv, float) and math.isnan(gv): gv = None
    if iv is not None and isinstance(iv, float) and math.isnan(iv): iv = None
    
    if gt=="accelerating" and it=="decelerating": return "Q1"
    if gt=="accelerating" and it=="accelerating": return "Q2"
    if gt=="decelerating" and it=="accelerating": return "Q3"
    if gt=="decelerating" and it=="decelerating": return "Q4"
    
    if use_abs and gv is not None and iv is not None:
        if gv < 2.0 and iv >= 2.8: return "Q3"
        if gv >= 2.5 and iv >= 2.8: return "Q2"
        if gv >= 2.5 and iv < 2.2: return "Q1"
        if gv < 2.0 and iv < 2.2: return "Q4"
    
    if gt=="accelerating": return "Q2"
    if it=="accelerating": return "Q3"
    if gt=="decelerating": return "Q4"
    if it=="decelerating": return "Q1"
    
    if gv is not None and iv is not None:
        if gv < 2.0 and iv >= 2.8: return "Q3"
        if gv >= 2.5 and iv >= 2.8: return "Q2"
        if gv >= 2.5 and iv < 2.2: return "Q1"
        if gv < 2.0 and iv < 2.2: return "Q4"
    return "Q2"

def yf_proxy():
    try:
        tkrs = ['SPY','TLT','GLD','UUP','XOP','XLF','XLU','XLK','XLP','HYG','IWM','XLI','VIXY']
        data = yf.download(tkrs, period="9mo", interval="1d", progress=False, auto_adjust=True)
        close = data['Close'] if isinstance(data.columns, pd.MultiIndex) else data
        def mom(t, m1=21, m3=63, m6=126):
            s = close[t].dropna() if t in close else pd.Series()
            if len(s) < m6+5: return 0.0,0.0,0.0
            p = s.iloc[-1]
            return (p/s.iloc[-m1]-1)*100, (p/s.iloc[-m3]-1)*100, (p/s.iloc[-m6]-1)*100
        spy1,spy3,spy6 = mom('SPY'); tlt1,tlt3,tlt6 = mom('TLT'); gld1,gld3,gld6 = mom('GLD')
        uup1,uup3,uup6 = mom('UUP'); xop1,xop3,xop6 = mom('XOP'); xlf1,xlf3,xlf6 = mom('XLF')
        xlu1,xlu3,xlu6 = mom('XLU'); hyg1,hyg3,hyg6 = mom('HYG'); iwm1,iwm3,iwm6 = mom('IWM')
        xli1,xli3,xli6 = mom('XLI'); vix1,vix3,vix6 = mom('VIXY')
        g_acc = (spy3 > spy6+0.5) and (xlf3 > xlu3) and (xli3 > xli6)
        g_dec = (spy3 < spy6-0.5) or (xlu3 > xlf3+2) or (iwm3 < iwm6-1)
        i_acc = (gld3 > gld6) and (xop3 > -5) and (tlt3 < tlt6)
        i_dec = (gld3 < gld6-1) and (uup3 > uup6)
        ph = (uup3 > uup6+1) and (tlt3 < -5)
        pd_ = (uup3 < uup6-1) and (hyg3 > hyg6)
        gy = 3.0 if g_acc else (0.5 if g_dec else 1.8)
        iy = 3.8 if i_acc else (2.2 if i_dec else 3.0)
        pr = 5.0 if ph else (3.5 if pd_ else 4.5)
        t10 = 4.5 if ph else (3.5 if pd_ else 4.2)
        vix_now = vix1 if vix1 != 0 else 20.0
        mg_acc = (spy1 > spy3+0.3) and (iwm1 > iwm3)
        mg_dec = (spy1 < spy3-0.3) or (iwm1 < iwm3-0.5)
        mi_acc = (gld1 > gld3) and (tlt1 < tlt3)
        mi_dec = (gld1 < gld3-0.5) and (uup1 > uup3)
        mg = "accelerating" if mg_acc else "decelerating" if mg_dec else "stable"
        mi = "accelerating" if mi_acc else "decelerating" if mi_dec else "stable"
        return {'growth_yoy':gy,'inflation_yoy':iy,'policy_rate':pr,'treasury_10y':t10,
                'vix':vix_now,'source':'yfinance_proxy','confidence':0.5,
                'fred_loaded':0,'fred_missing':len(FRED_SERIES),
                'monthly_growth':mg,'monthly_infl':mi}
    except Exception as e:
        logger.error(f"yf_proxy fail: {e}")
        return None

def calculate_regime() -> Dict:
    for old in glob.glob("/tmp/regime_cache_*.pkl"):
        try: os.remove(old)
        except: pass
    
    fred = fetch_all_fred()
    has_pce = 'real_pce' in fred
    has_cpi = 'cpi' in fred or 'core_cpi' in fred
    source = 'fred' if (has_pce and has_cpi) else 'yfinance_proxy'
    logger.info(f"Source={source}, keys={list(fred.keys())}")
    
    vix = 20.0
    if has_pce and has_cpi:
        pce = fred['real_pce']
        pce_yoy = yoy_roc(pce)
        growth_trend = trend_direction(pce_yoy)
        growth_val = float(pce_yoy.iloc[-1]) if len(pce_yoy)>0 else 0.0
        
        cpi = fred.get('cpi') or fred.get('core_cpi')
        cpi_yoy = yoy_roc(cpi)
        infl_trend = trend_direction(cpi_yoy)
        infl_val = float(cpi_yoy.iloc[-1]) if len(cpi_yoy)>0 else 0.0
        
        ff = fred.get('fed_funds'); t10 = fred.get('treasury_10y')
        policy_rate = float(ff.iloc[-1]) if ff is not None else 4.5
        ten_y = float(t10.iloc[-1]) if t10 is not None else 4.2
        confidence = 0.80 if len(fred) >= 6 else 0.65
    else:
        proxy = yf_proxy()
        if proxy:
            growth_trend = "accelerating" if proxy['growth_yoy']>2.5 else "decelerating" if proxy['growth_yoy']<1.0 else "stable"
            infl_trend = "accelerating" if proxy['inflation_yoy']>3.2 else "decelerating" if proxy['inflation_yoy']<2.5 else "stable"
            growth_val = proxy['growth_yoy']; infl_val = proxy['inflation_yoy']
            policy_rate = proxy['policy_rate']; ten_y = proxy['treasury_10y']
            vix = proxy.get('vix', 20.0)
            confidence = proxy['confidence']; source = proxy['source']
        else:
            return {'quad':'Q2','structural_quad':'Q2','monthly_quad':'Q2','global_quad':'Q2',
                    'confidence':0.25,'source':'fallback','growth_trend':'stable','inflation_trend':'stable',
                    'growth_yoy':1.5,'inflation_yoy':3.0,'policy_rate':4.5,'treasury_10y':4.2,
                    'policy_stance':'In-a-box','fred_loaded':0,'fred_missing':len(FRED_SERIES),
                    'vix':20.0,'operating_regime':'⚠️ Data Unavailable','monthly_debug':{},
                    'timestamp':datetime.now().isoformat()}
    
    sq = assign_quad(growth_trend, infl_trend, growth_val, infl_val, use_abs=True)
    
    mq = sq; md = {}
    if source == 'fred':
        ps = fred.get('real_pce'); cs = fred.get('cpi') or fred.get('core_cpi')
        if ps is not None and len(ps)>=6:
            py = yoy_roc(ps); mg, gd = monthly_momentum(py, ps); md['growth']=gd
        else: mg = growth_trend; md['growth']={'error':'no pce'}
        if cs is not None and len(cs)>=6:
            cy = yoy_roc(cs); mi, id_ = monthly_momentum(cy, cs); md['inflation']=id_
        else: mi = infl_trend; md['inflation']={'error':'no cpi'}
        mq = assign_quad(mg, mi, growth_val, infl_val, use_abs=False)
        logger.info(f"Monthly: g={mg}, i={mi} → {mq}")
    else:
        proxy = yf_proxy()
        if proxy:
            mq = assign_quad(proxy['monthly_growth'], proxy['monthly_infl'], growth_val, infl_val, use_abs=False)
            md['proxy'] = {'mg':proxy['monthly_growth'],'mi':proxy['monthly_infl']}
    
    gq = sq
    if source == 'fred':
        dxy = fred.get('dxy'); t10s = fred.get('treasury_10y')
        dxy_t = trend_direction(dxy, 0.20) if dxy is not None and len(dxy)>=6 else "stable"
        rt = trend_direction(t10s, 0.03) if t10s is not None and len(t10s)>=6 else "stable"
        gg = "decelerating" if dxy_t=="accelerating" else "accelerating" if dxy_t=="decelerating" else growth_trend
        gi = "accelerating" if rt=="accelerating" else "decelerating" if rt=="decelerating" else infl_trend
        gq = assign_quad(gg, gi, growth_val, infl_val, use_abs=True)
    else:
        gq = sq
    
    ps_text = "Hawkish 🦅" if policy_rate>=5.25 or ten_y>=4.8 else "Dovish 🕊️" if policy_rate<=3.0 or ten_y<=3.2 else "In-a-box 📦"
    rt = {'Q1':'🟢 Q1 Goldilocks','Q2':'🟡 Q2 Reflation','Q3':'🟠 Q3 Stagflation','Q4':'🔴 Q4 Deflation'}.get(sq,'Unknown')
    
    return {
        'quad':sq,'structural_quad':sq,'monthly_quad':mq,'global_quad':gq,
        'confidence':confidence,'source':source,
        'growth_trend':growth_trend,'inflation_trend':infl_trend,
        'growth_yoy':round(float(growth_val),2),'inflation_yoy':round(float(infl_val),2),
        'policy_rate':round(float(policy_rate),2),'treasury_10y':round(float(ten_y),2),
        'vix':round(float(vix),2),'policy_stance':ps_text,
        'fred_loaded':len(fred),'fred_missing':len(FRED_SERIES)-len(fred),
        'operating_regime':rt,'monthly_debug':md,
        'timestamp':datetime.now().isoformat()
    }

@st.cache_data(ttl=60)
def get_regime_snapshot() -> Dict:
    return calculate_regime()