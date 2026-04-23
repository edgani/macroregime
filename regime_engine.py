"""
regime_engine.py v15.2i — Pure Data-Driven GIP, No Hardcoded Quarter
Growth: Real PCE YoY | Inflation: Headline CPI YoY | Policy: DFF+DGS10+DXY
v15.2i: Remove nominal PCE fallback + prob clamp + progress-safe
"""
import os, time, logging, glob, math
from datetime import datetime
from typing import Dict, Optional
import requests, yfinance as yf, pandas as pd, numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"
MAX_RETRIES = 3
TIMEOUT = 35

FRED_SERIES = {
    'real_pce': 'PCEC1',
    'real_pce_dpi': 'DSPIC96',
    'cpi': 'CPIAUCSL',
    'core_cpi': 'CPILFESL',
    'fed_funds': 'DFF',
    'treasury_10y': 'DGS10',
    'treasury_2y': 'DGS2',
    'dxy': 'DTWEXBGS',
    'ism_mfg': 'NAPM',
    'ism_mfg_backup1': 'NAPMNOI',
    'ism_mfg_backup2': 'NAPMPROD',
    'claims': 'ICSA',
    'breakeven_10y': 'T10YIE',
    'hy_oas': 'BAMLH0A0HYM2',
}

PRIMARY_SERIES = ['real_pce', 'cpi', 'fed_funds', 'treasury_10y', 'ism_mfg', 'claims', 'breakeven_10y', 'dxy']
FRED_SERIES_COUNT = len(PRIMARY_SERIES)

def get_fred_api_key() -> str:
    key = os.environ.get("FRED_API_KEY", "")
    if not key:
        try: key = __import__('streamlit').secrets.get("FRED_API_KEY", "")
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
            if r.status_code == 429: time.sleep(2**attempt + 3); continue
            if r.status_code != 200:
                logger.warning(f"FRED {sid} status {r.status_code}")
                continue
            data = r.json()
            if 'observations' not in data or not data['observations']:
                logger.warning(f"FRED {sid}: no observations")
                continue
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['value'])
            if df.empty:
                logger.warning(f"FRED {sid}: all values NaN")
                continue
            df = df.set_index('date').sort_index().drop_duplicates()
            s = df['value']
            if len(s) < 6:
                logger.warning(f"FRED {sid}: only {len(s)} pts")
                continue
            logger.info(f"FRED {sid}: {len(s)} pts, last={s.index[-1].date()}, val={s.iloc[-1]:.3f}")
            return s
        except Exception as e:
            logger.error(f"FRED {sid} err attempt {attempt+1}: {e}")
            time.sleep(2**attempt+1)
    logger.error(f"FRED {sid}: all retries failed")
    return None

def fetch_ism_proxy() -> Optional[pd.Series]:
    try:
        xli = yf.download("XLI", period="9mo", interval="1d", progress=False, auto_adjust=True)
        if xli.empty or 'Close' not in xli: return None
        c = xli['Close'].dropna()
        if len(c) < 130: return None
        m1 = (c.iloc[-1] / c.iloc[-22] - 1) * 100 if len(c) >= 22 else 0
        m3 = (c.iloc[-1] / c.iloc[-64] - 1) * 100 if len(c) >= 64 else 0
        latest = 50.0 + m1 * 1.5 + m3 * 0.6
        latest = max(35.0, min(70.0, latest))
        idx = pd.date_range(end=c.index[-1], periods=6, freq='MS')
        vals = [latest - i * 0.25 for i in range(6)]
        return pd.Series(vals, index=idx)
    except Exception as e:
        logger.warning(f"ISM proxy error: {e}")
        return None

def fetch_all_fred() -> Dict[str, pd.Series]:
    key = get_fred_api_key()
    if not key: return {}
    out = {}
    for name, sid in FRED_SERIES.items():
        s = fetch_fred_series(sid, key)
        if s is not None:
            out[name] = s
        time.sleep(1.2)

    resolved = {}
    sources = {}

    # Growth: Real PCE only. NEVER fallback to nominal PCE.
    if 'real_pce' in out:
        resolved['real_pce'] = out['real_pce']; sources['real_pce'] = 'fred'
    elif 'real_pce_dpi' in out:
        resolved['real_pce'] = out['real_pce_dpi']; sources['real_pce'] = 'fred_dpi'

    if 'cpi' in out:
        resolved['cpi'] = out['cpi']; sources['cpi'] = 'fred'
    elif 'core_cpi' in out:
        resolved['cpi'] = out['core_cpi']; sources['cpi'] = 'fred_core'

    if 'ism_mfg' in out:
        resolved['ism_mfg'] = out['ism_mfg']; sources['ism_mfg'] = 'fred'
    elif 'ism_mfg_backup1' in out:
        resolved['ism_mfg'] = out['ism_mfg_backup1']; sources['ism_mfg'] = 'fred_napmnoi'
    elif 'ism_mfg_backup2' in out:
        resolved['ism_mfg'] = out['ism_mfg_backup2']; sources['ism_mfg'] = 'fred_napmprod'
    else:
        ism_proxy = fetch_ism_proxy()
        if ism_proxy is not None:
            resolved['ism_mfg'] = ism_proxy; sources['ism_mfg'] = 'xli_proxy'

    for k in ['fed_funds', 'treasury_10y', 'treasury_2y', 'dxy', 'claims', 'breakeven_10y', 'hy_oas']:
        if k in out:
            resolved[k] = out[k]; sources[k] = 'fred'

    out.update(resolved)
    out['_resolved'] = resolved
    out['_sources'] = sources
    logger.info(f"FRED resolved {len(resolved)}/{len(PRIMARY_SERIES)}: {sources}")
    return out

def get_vix() -> float:
    try:
        v = yf.download("^VIX", period="5d", interval="1d", progress=False, auto_adjust=True)
        if not v.empty and 'Close' in v:
            val = float(v['Close'].iloc[-1])
            if val > 5: return val
    except: pass
    try:
        v = yf.download("VIXY", period="5d", interval="1d", progress=False, auto_adjust=True)
        if not v.empty and 'Close' in v:
            val = float(v['Close'].iloc[-1])
            if val > 5: return val * 2.2
    except: pass
    return 20.0

def yoy_roc(s: pd.Series, months=12) -> pd.Series:
    return ((s / s.shift(months) - 1.0) * 100.0).dropna()

def trend_direction(s: pd.Series, thresh=0.015) -> str:
    if len(s) < 6:
        return "stable"
    y6 = s.iloc[-6:].values; x6 = np.arange(len(y6))
    slope6 = np.polyfit(x6, y6, 1)[0]
    y3 = s.iloc[-3:].values; x3 = np.arange(len(y3))
    slope3 = np.polyfit(x3, y3, 1)[0]
    diff = slope3 - slope6
    if diff > thresh:
        return "accelerating"
    if diff < -thresh:
        return "decelerating"
    return "stable"

def monthly_momentum(yoy_s: pd.Series):
    debug = {}
    if len(yoy_s) < 4:
        return "stable", debug
    m1 = float(yoy_s.iloc[-1])
    m3 = float(yoy_s.iloc[-3:].mean())
    debug.update({'m1': round(m1, 2), 'm3': round(m3, 2)})
    if len(yoy_s) >= 6:
        y6 = yoy_s.iloc[-6:].values; x6 = np.arange(6)
        slope6 = np.polyfit(x6, y6, 1)[0]
        y3 = yoy_s.iloc[-3:].values; x3 = np.arange(3)
        slope3 = np.polyfit(x3, y3, 1)[0]
        diff = slope3 - slope6
        debug.update({'slope3': round(slope3, 4), 'slope6': round(slope6, 4), 'diff': round(diff, 4)})
        if diff > 0.015:
            return "accelerating", debug
        if diff < -0.015:
            return "decelerating", debug
    if m1 > m3 + 0.12:
        return "accelerating", debug
    if m1 < m3 - 0.12:
        return "decelerating", debug
    return "stable", debug

def assign_quad(gt: str, it: str, gv=None, iv=None, use_abs=True) -> str:
    if gv is not None and isinstance(gv, float) and math.isnan(gv): gv = None
    if iv is not None and isinstance(iv, float) and math.isnan(iv): iv = None

    if gt == "accelerating" and it == "decelerating": return "Q1"
    if gt == "accelerating" and it == "accelerating": return "Q2"
    if gt == "decelerating" and it == "accelerating": return "Q3"
    if gt == "decelerating" and it == "decelerating": return "Q4"

    if gt == "accelerating" and it == "stable": return "Q2"
    if gt == "stable" and it == "accelerating": return "Q3"
    if gt == "decelerating" and it == "stable": return "Q4"
    if gt == "stable" and it == "decelerating": return "Q1"

    if use_abs and gv is not None and iv is not None:
        gv = float(gv); iv = float(iv)
        if gv >= 2.5:
            if iv >= 2.2: return "Q2"
            else: return "Q1"
        elif gv >= 2.0:
            if iv >= 2.8: return "Q3"
            elif iv >= 2.2: return "Q2"
            else: return "Q1"
        else:
            if iv >= 2.2: return "Q3"
            else: return "Q4"
    return "Q2"

def _calc_probs(gv, iv, gt, it):
    base = {"Q1":0.20,"Q2":0.30,"Q3":0.30,"Q4":0.20}
    if gt=="accelerating" and it=="decelerating": base={"Q1":0.55,"Q2":0.25,"Q3":0.12,"Q4":0.08}
    elif gt=="accelerating" and it=="accelerating": base={"Q1":0.12,"Q2":0.50,"Q3":0.30,"Q4":0.08}
    elif gt=="decelerating" and it=="accelerating": base={"Q1":0.08,"Q2":0.15,"Q3":0.55,"Q4":0.22}
    elif gt=="decelerating" and it=="decelerating": base={"Q1":0.12,"Q2":0.08,"Q3":0.25,"Q4":0.55}
    elif gt=="stable" and it=="stable": base={"Q1":0.20,"Q2":0.30,"Q3":0.30,"Q4":0.20}
    elif gt=="stable" and it=="accelerating": base={"Q1":0.12,"Q2":0.18,"Q3":0.50,"Q4":0.20}
    elif gt=="stable" and it=="decelerating": base={"Q1":0.35,"Q2":0.25,"Q3":0.18,"Q4":0.22}
    elif gt=="accelerating" and it=="stable": base={"Q1":0.38,"Q2":0.35,"Q3":0.15,"Q4":0.12}
    elif gt=="decelerating" and it=="stable": base={"Q1":0.15,"Q2":0.18,"Q3":0.42,"Q4":0.25}

    if gv is not None and iv is not None:
        if gv >= 2.5:
            base["Q2"]+=0.08; base["Q1"]+=0.05; base["Q3"]-=0.08; base["Q4"]-=0.05
        elif gv < 2.0:
            base["Q3"]+=0.08; base["Q4"]+=0.05; base["Q1"]-=0.05; base["Q2"]-=0.08
        if iv >= 2.8:
            base["Q2"]+=0.05; base["Q3"]+=0.08; base["Q1"]-=0.05; base["Q4"]-=0.08
        elif iv < 2.2:
            base["Q1"]+=0.08; base["Q4"]+=0.05; base["Q2"]-=0.05; base["Q3"]-=0.08
    
    # Clamp and normalize
    base = {k: max(0.001, v) for k, v in base.items()}
    total = sum(base.values())
    out = {k: round(v/total, 3) for k, v in base.items()}
    # Final clamp to ensure valid probability
    return {k: max(0.0, min(1.0, v)) for k, v in out.items()}

def yf_proxy():
    try:
        tkrs = ['SPY','TLT','GLD','UUP','XOP','XLF','XLU','XLK','XLP','HYG','IWM','XLI','RSP']
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
        xli1,xli3,xli6 = mom('XLI'); rsp1,rsp3,rsp6 = mom('RSP')

        g_acc = (spy3 > spy6+0.5) and (xlf3 > xlu3+2) and (xli3 > xli6)
        g_dec = (spy3 < spy6-0.5) or (xlu3 > xlf3+0.5) or (iwm3 < iwm6-1) or (tlt3 > tlt6+1) or (rsp3 < spy3-0.5)
        i_acc = (gld3 > gld6) and (xop3 > -5) and (uup3 < uup6)
        i_dec = (gld3 < gld6-1.5) and (uup3 > uup6+1) and (tlt3 > tlt6)

        ph = (uup3 > uup6+1) and (tlt3 < -5)
        pd_ = (uup3 < uup6-1) and (hyg3 > hyg6)

        gy = 1.9 if g_dec else (2.8 if g_acc else 1.9)
        iy = 2.9 if i_acc else (2.3 if i_dec else 2.9)
        pr = 5.0 if ph else (3.5 if pd_ else 4.5)
        t10 = 4.5 if ph else (3.5 if pd_ else 4.2)

        mg = "decelerating" if g_dec else ("accelerating" if g_acc else "stable")
        mi = "accelerating" if i_acc else ("decelerating" if i_dec else "stable")

        return {'growth_yoy':gy,'inflation_yoy':iy,'policy_rate':pr,'treasury_10y':t10,
                'vix':get_vix(),'source':'yfinance_proxy','confidence':0.5,
                'fred_loaded':0,'fred_missing':len(PRIMARY_SERIES),
                'monthly_growth':mg,'monthly_infl':mi}
    except Exception as e:
        logger.error(f"yf_proxy fail: {e}")
        return None

def calculate_regime() -> Dict:
    for old in glob.glob("/tmp/regime_cache_*.pkl"):
        try: os.remove(old)
        except: pass

    fred = fetch_all_fred()
    resolved = fred.get('_resolved', {})
    sources = fred.get('_sources', {})

    has_pce = 'real_pce' in resolved
    has_cpi = 'cpi' in resolved

    if has_pce and has_cpi:
        source = 'fred'
    elif len(resolved) >= 5:
        source = 'fred_partial'
    else:
        source = 'yfinance_proxy'

    vix = get_vix()
    macro_pulse = {}
    growth_trend = "stable"
    infl_trend = "stable"
    growth_val = 1.5
    infl_val = 3.0
    policy_rate = 4.5
    ten_y = 4.2
    treasury_2y = 3.7
    hy_oas = 350.0
    confidence = 0.25
    mg = "stable"
    mi = "stable"
    md = {}

    if has_pce and has_cpi:
        pce = resolved['real_pce']
        pce_yoy = yoy_roc(pce)
        growth_trend = trend_direction(pce_yoy)
        growth_val = float(pce_yoy.iloc[-1]) if len(pce_yoy)>0 else 0.0

        cpi = resolved['cpi']
        cpi_yoy = yoy_roc(cpi)
        infl_trend = trend_direction(cpi_yoy)
        infl_val = float(cpi_yoy.iloc[-1]) if len(cpi_yoy)>0 else 0.0

        ff = resolved.get('fed_funds'); t10 = resolved.get('treasury_10y')
        policy_rate = float(ff.iloc[-1]) if ff is not None else 4.5
        ten_y = float(t10.iloc[-1]) if t10 is not None else 4.2
        t2 = resolved.get('treasury_2y')
        treasury_2y = float(t2.iloc[-1]) if t2 is not None else (ten_y - 0.5)
        hy_s = resolved.get('hy_oas')
        hy_oas = float(hy_s.iloc[-1]) if hy_s is not None else 350.0
        confidence = 0.85 if len(resolved) >= 7 else 0.70

        ism = resolved.get('ism_mfg')
        if ism is not None and len(ism) >= 2:
            macro_pulse['ism_delta'] = round(float(ism.iloc[-1] - ism.iloc[-2]), 1)
            macro_pulse['ism_now'] = round(float(ism.iloc[-1]), 1)
            macro_pulse['ism_source'] = sources.get('ism_mfg','FRED')
        claims = resolved.get('claims')
        if claims is not None and len(claims) >= 2:
            macro_pulse['claims_delta'] = round(float(claims.iloc[-1] - claims.iloc[-2]), 0)
            macro_pulse['claims_now'] = round(float(claims.iloc[-1]), 0)
        be = resolved.get('breakeven_10y')
        if be is not None and len(be) >= 21:
            macro_pulse['be_1m'] = round(float(be.iloc[-1] - be.iloc[-21]), 2)
            macro_pulse['be_now'] = round(float(be.iloc[-1]), 2)

        ps = resolved.get('real_pce')
        cs = resolved.get('cpi')
        if ps is not None and len(ps)>=6:
            py = yoy_roc(ps); mg, gd = monthly_momentum(py); md['growth']=gd
        else: mg = growth_trend; md['growth']={'error':'no pce'}
        if cs is not None and len(cs)>=6:
            cy = yoy_roc(cs); mi, id_ = monthly_momentum(cy); md['inflation']=id_
        else: mi = infl_trend; md['inflation']={'error':'no cpi'}

    elif len(resolved) >= 5:
        source = 'fred_partial'
        confidence = 0.65
        if 'real_pce' in resolved:
            pce = resolved['real_pce']; pce_yoy = yoy_roc(pce)
            growth_trend = trend_direction(pce_yoy)
            growth_val = float(pce_yoy.iloc[-1]) if len(pce_yoy)>0 else 0.0
        if 'cpi' in resolved:
            cpi = resolved['cpi']; cpi_yoy = yoy_roc(cpi)
            infl_trend = trend_direction(cpi_yoy)
            infl_val = float(cpi_yoy.iloc[-1]) if len(cpi_yoy)>0 else 0.0
        ff = resolved.get('fed_funds'); t10 = resolved.get('treasury_10y')
        policy_rate = float(ff.iloc[-1]) if ff is not None else 4.5
        ten_y = float(t10.iloc[-1]) if t10 is not None else 4.2
        t2 = resolved.get('treasury_2y')
        treasury_2y = float(t2.iloc[-1]) if t2 is not None else (ten_y - 0.5)
        hy_s = resolved.get('hy_oas')
        hy_oas = float(hy_s.iloc[-1]) if hy_s is not None else 350.0

        ism = resolved.get('ism_mfg')
        if ism is not None and len(ism) >= 2:
            macro_pulse['ism_delta'] = round(float(ism.iloc[-1] - ism.iloc[-2]), 1)
            macro_pulse['ism_now'] = round(float(ism.iloc[-1]), 1)
            macro_pulse['ism_source'] = sources.get('ism_mfg','FRED')
        claims = resolved.get('claims')
        if claims is not None and len(claims) >= 2:
            macro_pulse['claims_delta'] = round(float(claims.iloc[-1] - claims.iloc[-2]), 0)
            macro_pulse['claims_now'] = round(float(claims.iloc[-1]), 0)
        be = resolved.get('breakeven_10y')
        if be is not None and len(be) >= 21:
            macro_pulse['be_1m'] = round(float(be.iloc[-1] - be.iloc[-21]), 2)
            macro_pulse['be_now'] = round(float(be.iloc[-1]), 2)

        ps = resolved.get('real_pce')
        cs = resolved.get('cpi')
        if ps is not None and len(ps)>=6:
            py = yoy_roc(ps); mg, gd = monthly_momentum(py); md['growth']=gd
        else: mg = growth_trend; md['growth']={'error':'no pce'}
        if cs is not None and len(cs)>=6:
            cy = yoy_roc(cs); mi, id_ = monthly_momentum(cy); md['inflation']=id_
        else: mi = infl_trend; md['inflation']={'error':'no cpi'}
    else:
        proxy = yf_proxy()
        if proxy:
            growth_trend = "decelerating" if proxy['growth_yoy']<2.0 else "accelerating" if proxy['growth_yoy']>2.5 else "stable"
            infl_trend = "accelerating" if proxy['inflation_yoy']>2.8 else "decelerating" if proxy['inflation_yoy']<2.3 else "stable"
            growth_val = proxy['growth_yoy']; infl_val = proxy['inflation_yoy']
            policy_rate = proxy['policy_rate']; ten_y = proxy['treasury_10y']
            treasury_2y = ten_y - 0.5
            hy_oas = 350.0
            vix = proxy.get('vix', 20.0)
            confidence = proxy['confidence']; source = proxy['source']
            mg = proxy['monthly_growth']; mi = proxy['monthly_infl']
        else:
            return {'quad':'Q2','structural_quad':'Q2','monthly_quad':'Q2','global_quad':'Q2',
                    'confidence':0.25,'source':'fallback','growth_trend':'stable','inflation_trend':'stable',
                    'growth_yoy':1.5,'inflation_yoy':3.0,'policy_rate':4.5,'treasury_10y':4.2,
                    'treasury_2y':3.7,'hy_oas':350.0,
                    'vix':vix,'policy_stance':'In-a-box 📦','fred_loaded':0,'fred_missing':len(PRIMARY_SERIES),
                    'operating_regime':'⚠️ Data Unavailable','monthly_debug':{},'macro_pulse':{},
                    'probs':{"Q1":0.20,"Q2":0.30,"Q3":0.30,"Q4":0.20},
                    'monthly_probs':{"Q1":0.20,"Q2":0.30,"Q3":0.30,"Q4":0.20},
                    'flip_hazard':0.0,'deepness':0.0,
                    'timestamp':datetime.now().isoformat(),
                    'fred_missing_keys': [k for k in PRIMARY_SERIES if k not in resolved]}

    sq = assign_quad(growth_trend, infl_trend, growth_val, infl_val, use_abs=True)
    mq = assign_quad(mg, mi, growth_val, infl_val, use_abs=True)

    gq = sq
    if 'dxy' in resolved:
        dxy = resolved['dxy']
        dxy_t = trend_direction(dxy, 0.20) if len(dxy) >= 6 else "stable"
        gg = "decelerating" if dxy_t=="accelerating" else "accelerating" if dxy_t=="decelerating" else growth_trend
        gi = infl_trend
        if 'treasury_10y' in resolved:
            t10s = resolved['treasury_10y']
            rt = trend_direction(t10s, 0.03) if len(t10s) >= 6 else "stable"
            gi = "accelerating" if rt=="accelerating" else "decelerating" if rt=="decelerating" else infl_trend
        gq = assign_quad(gg, gi, growth_val, infl_val, use_abs=True)
    elif 'treasury_10y' in resolved:
        t10s = resolved['treasury_10y']
        rt = trend_direction(t10s, 0.03) if len(t10s) >= 6 else "stable"
        gi = "accelerating" if rt=="accelerating" else "decelerating" if rt=="decelerating" else infl_trend
        gq = assign_quad(growth_trend, gi, growth_val, infl_val, use_abs=True)

    ps_text = "Hawkish 🦅" if policy_rate>=5.25 or ten_y>=4.8 else "Dovish 🕊️" if policy_rate<=3.0 or ten_y<=3.2 else "In-a-box 📦"
    rt = {'Q1':'🟢 Q1 Goldilocks','Q2':'🟡 Q2 Reflation','Q3':'🟠 Q3 Stagflation','Q4':'🔴 Q4 Deflation'}.get(sq,'Unknown')

    probs = _calc_probs(growth_val, infl_val, growth_trend, infl_trend)
    m_probs = _calc_probs(growth_val, infl_val, mg, mi)

    flip_hazard = 0.0
    if sq != mq:
        flip_hazard = min(0.85, 0.35 + 0.15 * abs({"Q1":1,"Q2":2,"Q3":3,"Q4":4}[sq] - {"Q1":1,"Q2":2,"Q3":3,"Q4":4}[mq]))
    if confidence < 0.5:
        flip_hazard = max(flip_hazard, 0.45)

    deepness = 0.0
    if sq == mq == gq:
        deepness = min(0.95, confidence * 0.8 + 0.15)
    elif sq == mq:
        deepness = min(0.75, confidence * 0.6 + 0.10)
    else:
        deepness = min(0.45, confidence * 0.3)

    fred_loaded = len([k for k in PRIMARY_SERIES if k in resolved])
    fred_missing_keys = [k for k in PRIMARY_SERIES if k not in resolved]

    return {
        'quad':sq,'structural_quad':sq,'monthly_quad':mq,'global_quad':gq,
        'confidence':confidence,'source':source,
        'growth_trend':growth_trend,'inflation_trend':infl_trend,
        'growth_yoy':round(float(growth_val),2),'inflation_yoy':round(float(infl_val),2),
        'policy_rate':round(float(policy_rate),2),'treasury_10y':round(float(ten_y),2),
        'treasury_2y':round(float(treasury_2y),2),'hy_oas':round(float(hy_oas),2),
        'vix':round(float(vix),2),'policy_stance':ps_text,
        'fred_loaded':fred_loaded,'fred_missing':len(PRIMARY_SERIES)-fred_loaded,
        'fred_missing_keys': fred_missing_keys,
        'operating_regime':rt,'monthly_debug':md,'macro_pulse':macro_pulse,
        'probs':probs,'monthly_probs':m_probs,
        'flip_hazard':round(flip_hazard,2),'deepness':round(deepness,2),
        'timestamp':datetime.now().isoformat()
    }

def get_regime_snapshot():
    return calculate_regime()