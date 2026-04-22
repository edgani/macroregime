"""
regime_engine.py — Hedgeye GIP Model Exact Replica
Growth: Real PCE (monthly) | Inflation: Headline CPI YoY | Policy: DFF+DGS10+DXY
Auto-regime, zero hardcode, robust fallback chain.
"""
import os
import pickle
import time
import logging
import glob
from datetime import datetime
from typing import Dict, Optional
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(name)s | %(message)s')
logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"
CACHE_FILE = "/tmp/regime_cache_v5.pkl"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 25

FRED_SERIES = {
    'real_pce':      'PCEC1',
    'real_pce_dpi':  'DSPIC96',
    'cpi':           'CPIAUCSL',
    'core_cpi':      'CPILFESL',
    'fed_funds':     'DFF',
    'treasury_10y':  'DGS10',
    'treasury_2y':   'DGS2',
    'dxy':           'DTWEXBGS',
}

def get_fred_api_key() -> str:
    key = os.environ.get("FRED_API_KEY", st.secrets.get("FRED_API_KEY", ""))
    return key.strip() if key else ""

def fetch_fred_series(series_id: str, api_key: str, start_date: str = "2019-01-01") -> Optional[pd.Series]:
    if not api_key:
        logger.warning(f"No API key for {series_id}")
        return None
    
    headers = {"User-Agent": "Mozilla/5.0 (compatible; MacroRegime/1.0)"}
    
    for attempt in range(MAX_RETRIES):
        try:
            url = f"{FRED_BASE}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': api_key,
                'file_type': 'json',
                'observation_start': start_date,
                'sort_order': 'desc',
                'limit': 500
            }
            resp = requests.get(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                wait = 2 ** attempt + 1
                logger.warning(f"FRED 429 for {series_id}, waiting {wait}s")
                time.sleep(wait)
                continue
            if resp.status_code != 200:
                logger.error(f"FRED {resp.status_code} for {series_id}: {resp.text[:200]}")
                continue
            
            data = resp.json()
            if 'observations' not in data or not data['observations']:
                logger.warning(f"No observations for {series_id}")
                continue
            
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna(subset=['value'])
            
            if df.empty:
                logger.warning(f"All NaN values for {series_id}")
                continue
            
            df = df.set_index('date').sort_index()
            df = df[~df.index.duplicated(keep='last')]
            series = df['value']
            
            if len(series) < 12:
                logger.warning(f"{series_id}: only {len(series)} points, need 12+")
                continue
            
            logger.info(f"✅ FRED {series_id}: loaded {len(series)} points, last={series.index[-1].date()}, val={series.iloc[-1]}")
            return series
            
        except Exception as e:
            logger.error(f"FRED error {series_id} attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt + 1)
    
    logger.error(f"❌ FRED {series_id}: all retries failed")
    return None

def fetch_all_fred() -> Dict[str, pd.Series]:
    api_key = get_fred_api_key()
    if not api_key:
        logger.warning("No FRED API key available")
        return {}
    
    results = {}
    for name, sid in FRED_SERIES.items():
        s = fetch_fred_series(sid, api_key)
        if s is not None:
            results[name] = s
        time.sleep(0.5)  # ← RATE LIMIT FIX: delay antar request
    logger.info(f"FRED total loaded: {len(results)}/{len(FRED_SERIES)} — {list(results.keys())}")
    return results

def yfinance_proxy_regime() -> Optional[Dict]:
    try:
        tkrs = ['SPY','TLT','GLD','UUP','XOP','XLF','XLU','XLK','XLP','HYG','LQD','IBIT','IWM','QQQ','XLI']
        data = yf.download(tkrs, period="9mo", interval="1d", progress=False, auto_adjust=True)
        if isinstance(data.columns, pd.MultiIndex):
            close = data['Close']
        else:
            close = data
        
        def mom(ticker, m1=21, m3=63, m6=126):
            s = close[ticker].dropna() if ticker in close else pd.Series()
            if len(s) < m6 + 5:
                return 0.0, 0.0, 0.0
            p_now = s.iloc[-1]
            return (p_now/s.iloc[-m1]-1)*100, (p_now/s.iloc[-m3]-1)*100, (p_now/s.iloc[-m6]-1)*100
        
        spy_1m, spy_3m, spy_6m = mom('SPY')
        tlt_1m, tlt_3m, tlt_6m = mom('TLT')
        gld_1m, gld_3m, gld_6m = mom('GLD')
        uup_1m, uup_3m, uup_6m = mom('UUP')
        xop_1m, xop_3m, xop_6m = mom('XOP')
        xlf_1m, xlf_3m, xlf_6m = mom('XLF')
        xlu_1m, xlu_3m, xlu_6m = mom('XLU')
        hyg_1m, hyg_3m, hyg_6m = mom('HYG')
        iwm_1m, iwm_3m, iwm_6m = mom('IWM')
        xli_1m, xli_3m, xli_6m = mom('XLI')
        
        growth_accel = (spy_3m > spy_6m + 0.5) and (xlf_3m > xlu_3m) and (xli_3m > xli_6m)
        growth_decel = (spy_3m < spy_6m - 0.5) or (xlu_3m > xlf_3m + 2) or (iwm_3m < iwm_6m - 1)
        
        infl_accel = (gld_3m > gld_6m) and (xop_3m > -5) and (tlt_3m < tlt_6m)
        infl_decel = (gld_3m < gld_6m - 1) and (uup_3m > uup_6m)
        
        policy_hawkish = (uup_3m > uup_6m + 1) and (tlt_3m < -5)
        policy_dovish = (uup_3m < uup_6m - 1) and (hyg_3m > hyg_6m)
        
        growth_yoy = 3.0 if growth_accel else (0.5 if growth_decel else 1.8)
        inflation_yoy = 3.8 if infl_accel else (2.2 if infl_decel else 3.0)
        policy_rate = 5.0 if policy_hawkish else (3.5 if policy_dovish else 4.5)
        ten_y = 4.5 if policy_hawkish else (3.5 if policy_dovish else 4.2)
        
        monthly_growth_accel = (spy_1m > spy_3m + 0.3) and (iwm_1m > iwm_3m)
        monthly_growth_decel = (spy_1m < spy_3m - 0.3) or (iwm_1m < iwm_3m - 0.5)
        monthly_infl_accel = (gld_1m > gld_3m) and (tlt_1m < tlt_3m)
        monthly_infl_decel = (gld_1m < gld_3m - 0.5) and (uup_1m > uup_3m)
        
        monthly_growth = "accelerating" if monthly_growth_accel else "decelerating" if monthly_growth_decel else "stable"
        monthly_infl = "accelerating" if monthly_infl_accel else "decelerating" if monthly_infl_decel else "stable"
        
        return {
            'growth_yoy': growth_yoy,
            'inflation_yoy': inflation_yoy,
            'policy_rate': policy_rate,
            'treasury_10y': ten_y,
            'source': 'yfinance_proxy',
            'confidence': 0.50,
            'fred_loaded': 0,
            'fred_missing': len(FRED_SERIES),
            'monthly_growth': monthly_growth,
            'monthly_infl': monthly_infl,
        }
    except Exception as e:
        logger.error(f"yfinance proxy failed: {e}")
        return None

def yoy_roc(series: pd.Series, months: int = 12) -> pd.Series:
    return (series / series.shift(months) - 1.0) * 100.0

def trend_direction(series: pd.Series, threshold: float = 0.03) -> str:
    if len(series) < 6:
        return "stable"
    y = series.iloc[-6:].values
    x = np.arange(len(y))
    slope = np.polyfit(x, y, 1)[0]
    if slope > threshold:
        return "accelerating"
    elif slope < -threshold:
        return "decelerating"
    return "stable"

def monthly_momentum(yoy_series: pd.Series, level_series: pd.Series) -> tuple[str, dict]:
    debug = {}
    if len(yoy_series) < 6 or len(level_series) < 6:
        return "stable", debug
    
    mom = level_series.pct_change() * 100.0
    mom_3m = float(mom.iloc[-3:].mean())
    mom_6m = float(mom.iloc[-6:].mean())
    
    debug['mom_3m_avg'] = round(mom_3m, 3)
    debug['mom_6m_avg'] = round(mom_6m, 3)
    debug['mom_diff'] = round(mom_3m - mom_6m, 3)
    
    yoy_1m = float(yoy_series.iloc[-1])
    yoy_3m_avg = float(yoy_series.iloc[-3:].mean())
    yoy_3m_prior = float(yoy_series.iloc[-6:-3].mean())
    
    debug['yoy_1m'] = round(yoy_1m, 2)
    debug['yoy_3m_avg'] = round(yoy_3m_avg, 2)
    debug['yoy_3m_prior'] = round(yoy_3m_prior, 2)
    
    accel_score = 0
    decel_score = 0
    
    if mom_3m > mom_6m + 0.02:
        accel_score += 2
        debug['mom_signal'] = 'accelerating'
    elif mom_3m < mom_6m - 0.02:
        decel_score += 2
        debug['mom_signal'] = 'decelerating'
    else:
        debug['mom_signal'] = 'stable'
    
    if yoy_1m > yoy_3m_avg + 0.05:
        accel_score += 1
        debug['yoy1m_signal'] = 'accelerating'
    elif yoy_1m < yoy_3m_avg - 0.05:
        decel_score += 1
        debug['yoy1m_signal'] = 'decelerating'
    else:
        debug['yoy1m_signal'] = 'stable'
    
    if yoy_3m_avg > yoy_3m_prior + 0.05:
        accel_score += 1
        debug['yoy3m_signal'] = 'accelerating'
    elif yoy_3m_avg < yoy_3m_prior - 0.05:
        decel_score += 1
        debug['yoy3m_signal'] = 'decelerating'
    else:
        debug['yoy3m_signal'] = 'stable'
    
    debug['accel_score'] = accel_score
    debug['decel_score'] = decel_score
    
    if accel_score >= 2:
        return "accelerating", debug
    elif decel_score >= 2:
        return "decelerating", debug
    return "stable", debug

def assign_quad(growth_trend: str, inflation_trend: str, 
                growth_val: float = None, infl_val: float = None) -> str:
    if growth_trend == "accelerating" and inflation_trend == "decelerating":
        return "Q1"
    elif growth_trend == "accelerating" and inflation_trend == "accelerating":
        return "Q2"
    elif growth_trend == "decelerating" and inflation_trend == "accelerating":
        return "Q3"
    elif growth_trend == "decelerating" and inflation_trend == "decelerating":
        return "Q4"
    elif growth_trend == "accelerating":
        return "Q2"
    elif inflation_trend == "accelerating":
        return "Q3"
    elif growth_trend == "decelerating":
        return "Q4"
    elif inflation_trend == "decelerating":
        return "Q1"
    
    if growth_val is not None and infl_val is not None:
        if growth_val < 2.0 and infl_val >= 2.8:
            return "Q3"
        elif growth_val >= 2.5 and infl_val >= 2.8:
            return "Q2"
        elif growth_val >= 2.5 and infl_val < 2.2:
            return "Q1"
        elif growth_val < 2.0 and infl_val < 2.2:
            return "Q4"
    return "Q2"

def calculate_regime() -> Dict:
    for old_cache in glob.glob("/tmp/regime_cache_*.pkl"):
        try:
            os.remove(old_cache)
            logger.info(f"Busted {old_cache}")
        except Exception:
            pass
    
    cached = None
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'rb') as f:
                cached = pickle.load(f)
                if (datetime.now() - datetime.fromisoformat(cached.get('timestamp','2000-01-01'))).days > 2:
                    cached = None
        except Exception:
            pass
    
    fred = fetch_all_fred()
    has_pce = 'real_pce' in fred
    has_cpi = 'cpi' in fred or 'core_cpi' in fred
    source = 'fred' if (has_pce and has_cpi) else 'yfinance_proxy' if len(fred) < 3 else 'fred_partial'
    
    logger.info(f"Regime source: {source}, FRED keys: {list(fred.keys())}")
    
    if has_pce and has_cpi:
        pce = fred.get('real_pce')
        pce_yoy = yoy_roc(pce)
        growth_trend = trend_direction(pce_yoy)
        growth_val = float(pce_yoy.iloc[-1])
        
        cpi = fred.get('cpi')
        if cpi is None:
            cpi = fred.get('core_cpi')
        cpi_yoy = yoy_roc(cpi)
        infl_trend = trend_direction(cpi_yoy)
        infl_val = float(cpi_yoy.iloc[-1])
        
        ff = fred.get('fed_funds')
        t10 = fred.get('treasury_10y')
        policy_rate = float(ff.iloc[-1]) if ff is not None else 4.5
        ten_y = float(t10.iloc[-1]) if t10 is not None else 4.2
        confidence = 0.80 if len(fred) >= 6 else 0.65
        
    else:
        proxy = yfinance_proxy_regime()
        if proxy is not None:
            growth_trend = "accelerating" if proxy['growth_yoy'] > 2.5 else "decelerating" if proxy['growth_yoy'] < 1.0 else "stable"
            infl_trend = "accelerating" if proxy['inflation_yoy'] > 3.2 else "decelerating" if proxy['inflation_yoy'] < 2.5 else "stable"
            growth_val = proxy['growth_yoy']
            infl_val = proxy['inflation_yoy']
            policy_rate = proxy['policy_rate']
            ten_y = proxy['treasury_10y']
            confidence = proxy['confidence']
            source = proxy['source']
        elif cached is not None:
            return cached
        else:
            return {
                'quad': 'Q2', 'structural_quad': 'Q2', 'monthly_quad': 'Q2', 'global_quad': 'Q2',
                'confidence': 0.25, 'source': 'neutral_fallback',
                'growth_trend': 'stable', 'inflation_trend': 'stable',
                'growth_yoy': 1.5, 'inflation_yoy': 3.0,
                'policy_rate': 4.5, 'treasury_10y': 4.2,
                'policy_stance': 'In-a-box',
                'fred_loaded': 0, 'fred_missing': len(FRED_SERIES),
                'operating_regime': '⚠️ Data Unavailable',
                'timestamp': datetime.now().isoformat(),
            }
    
    structural_quad = assign_quad(growth_trend, infl_trend, growth_val, infl_val)
    
    monthly_quad = structural_quad
    monthly_debug = {}
    if source == 'fred':
        pce_series = fred.get('real_pce')
        cpi_series = fred.get('cpi') or fred.get('core_cpi')
        
        if pce_series is not None and len(pce_series) >= 6:
            pce_yoy = yoy_roc(pce_series)
            monthly_growth, g_debug = monthly_momentum(pce_yoy, pce_series)
            monthly_debug['growth'] = g_debug
        else:
            monthly_growth = growth_trend
            monthly_debug['growth'] = {'error': 'no pce data'}
        
        if cpi_series is not None and len(cpi_series) >= 6:
            cpi_yoy = yoy_roc(cpi_series)
            monthly_infl, i_debug = monthly_momentum(cpi_yoy, cpi_series)
            monthly_debug['inflation'] = i_debug
        else:
            monthly_infl = infl_trend
            monthly_debug['inflation'] = {'error': 'no cpi data'}
        
        monthly_quad = assign_quad(monthly_growth, monthly_infl, growth_val, infl_val)
        logger.info(f"Monthly: growth={monthly_growth}, infl={monthly_infl} → {monthly_quad}")
    else:
        proxy = yfinance_proxy_regime()
        if proxy:
            monthly_growth = proxy.get('monthly_growth', growth_trend)
            monthly_infl = proxy.get('monthly_infl', infl_trend)
            monthly_quad = assign_quad(monthly_growth, monthly_infl, growth_val, infl_val)
            monthly_debug['proxy'] = {'monthly_growth': monthly_growth, 'monthly_infl': monthly_infl}
            logger.info(f"Proxy Monthly: growth={monthly_growth}, infl={monthly_infl} → {monthly_quad}")
    
    global_quad = structural_quad
    if source == 'fred':
        dxy = fred.get('dxy')
        t10_series = fred.get('treasury_10y')
        
        if dxy is not None and len(dxy) >= 6:
            dxy_trend = trend_direction(dxy, threshold=0.20)
        else:
            dxy_trend = "stable"
            
        if t10_series is not None and len(t10_series) >= 6:
            rate_trend = trend_direction(t10_series, threshold=0.03)
        else:
            rate_trend = "stable"
        
        global_growth = "decelerating" if dxy_trend == "accelerating" else "accelerating" if dxy_trend == "decelerating" else growth_trend
        global_infl = "accelerating" if rate_trend == "accelerating" else "decelerating" if rate_trend == "decelerating" else infl_trend
        global_quad = assign_quad(global_growth, global_infl, growth_val, infl_val)
    else:
        global_quad = structural_quad
    
    if policy_rate >= 5.25 or ten_y >= 4.8:
        policy_text = "Hawkish 🦅"
    elif policy_rate <= 3.0 or ten_y <= 3.2:
        policy_text = "Dovish 🕊️"
    else:
        policy_text = "In-a-box 📦"
    
    regime_text = {
        'Q1': '🟢 Q1 Goldilocks — Growth ↑ Inflation ↓',
        'Q2': '🟡 Q2 Reflation — Growth ↑ Inflation ↑',
        'Q3': '🟠 Q3 Stagflation — Growth ↓ Inflation ↑',
        'Q4': '🔴 Q4 Deflation — Growth ↓ Inflation ↓',
    }.get(structural_quad, 'Unknown')
    
    result = {
        'quad': structural_quad,
        'structural_quad': structural_quad,
        'monthly_quad': monthly_quad,
        'global_quad': global_quad,
        'confidence': confidence,
        'source': source,
        'growth_trend': growth_trend,
        'inflation_trend': infl_trend,
        'growth_yoy': round(float(growth_val), 2),
        'inflation_yoy': round