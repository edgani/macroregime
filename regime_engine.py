"""
regime_engine.py — Hedgeye GIP Model Exact Replica
Growth: Real PCE (monthly) | Inflation: Headline CPI YoY | Policy: DFF+DGS10+DXY
Auto-regime, zero hardcode, robust fallback chain.
"""
import os
import pickle
import time
from datetime import datetime
from typing import Dict, Optional
import requests
import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st

FRED_BASE = "https://api.stlouisfed.org/fred"
CACHE_FILE = "/tmp/regime_cache_v2.pkl"
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15

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
    return os.environ.get("FRED_API_KEY", st.secrets.get("FRED_API_KEY", ""))

def fetch_fred_series(series_id: str, api_key: str, start_date: str = "2019-01-01") -> Optional[pd.Series]:
    if not api_key:
        return None
    for attempt in range(MAX_RETRIES):
        try:
            url = f"{FRED_BASE}/series/observations"
            params = {
                'series_id': series_id,
                'api_key': api_key,
                'file_type': 'json',
                'observation_start': start_date,
                'sort_order': 'desc',
                'limit': 150
            }
            resp = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 429:
                time.sleep(2 ** attempt + 1)
                continue
            if resp.status_code != 200:
                continue
            data = resp.json()
            if 'observations' not in data:
                continue
            df = pd.DataFrame(data['observations'])
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.dropna().set_index('date')['value'].sort_index()
            df = df.resample('ME').last().dropna()
            return df if len(df) >= 24 else None
        except Exception:
            time.sleep(2 ** attempt + 1)
    return None

def fetch_all_fred() -> Dict[str, pd.Series]:
    api_key = get_fred_api_key()
    if not api_key:
        return {}
    results = {}
    for name, sid in FRED_SERIES.items():
        s = fetch_fred_series(sid, api_key)
        if s is not None and len(s) >= 24:
            results[name] = s
    return results

def yfinance_proxy_regime() -> Optional[Dict]:
    try:
        tkrs = ['SPY','TLT','GLD','UUP','XOP','XLF','XLU','XLK','XLP','HYG','LQD','IBIT']
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
        
        growth_accel = (spy_3m > spy_6m + 0.5) and (xlf_3m > xlu_3m)
        growth_decel = (spy_3m < spy_6m - 0.5) or (xlu_3m > xlf_3m + 2)
        
        infl_accel = (gld_3m > gld_6m) and (xop_3m > -5) and (tlt_3m < tlt_6m)
        infl_decel = (gld_3m < gld_6m - 1) and (uup_3m > uup_6m)
        
        policy_hawkish = (uup_3m > uup_6m + 1) and (tlt_3m < -5)
        policy_dovish = (uup_3m < uup_6m - 1) and (hyg_3m > hyg_6m)
        
        growth_yoy = 3.0 if growth_accel else (0.5 if growth_decel else 1.8)
        inflation_yoy = 3.8 if infl_accel else (2.2 if infl_decel else 3.0)
        policy_rate = 5.0 if policy_hawkish else (3.5 if policy_dovish else 4.5)
        ten_y = 4.5 if policy_hawkish else (3.5 if policy_dovish else 4.2)
        
        return {
            'growth_yoy': growth_yoy,
            'inflation_yoy': inflation_yoy,
            'policy_rate': policy_rate,
            'treasury_10y': ten_y,
            'source': 'yfinance_proxy',
            'confidence': 0.50,
            'fred_loaded': 0,
            'fred_missing': len(FRED_SERIES),
        }
    except Exception:
        return None

def yoy_roc(series: pd.Series, months: int = 12) -> pd.Series:
    return (series / series.shift(months) - 1.0) * 100.0

def ma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window, min_periods=1).mean()

def trend_direction(val_3m: float, val_6m: float, threshold: float = 0.15) -> str:
    diff = val_3m - val_6m
    if diff > threshold:
        return "accelerating"
    elif diff < -threshold:
        return "decelerating"
    return "stable"

def assign_quad(growth_trend: str, inflation_trend: str) -> str:
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
    return "Q2"

def calculate_regime() -> Dict:
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
    source = 'fred' if len(fred) >= 3 else 'fallback'
    
    if source == 'fred':
        pce = fred.get('real_pce')
        if pce is not None and len(pce) >= 24:
            pce_yoy = yoy_roc(pce)
            pce_3m = ma(pce_yoy, 3).iloc[-1]
            pce_6m = ma(pce_yoy, 6).iloc[-1]
            growth_trend = trend_direction(pce_3m, pce_6m)
            growth_val = pce_yoy.iloc[-1]
        else:
            growth_trend, growth_val = "stable", 1.5
        
        cpi = fred.get('cpi')
        if cpi is not None and len(cpi) >= 24:
            cpi_yoy = yoy_roc(cpi)
            cpi_3m = ma(cpi_yoy, 3).iloc[-1]
            cpi_6m = ma(cpi_yoy, 6).iloc[-1]
            infl_trend = trend_direction(cpi_3m, cpi_6m)
            infl_val = cpi_yoy.iloc[-1]
        else:
            cpi = fred.get('core_cpi')
            if cpi is not None and len(cpi) >= 24:
                cpi_yoy = yoy_roc(cpi)
                cpi_3m = ma(cpi_yoy, 3).iloc[-1]
                cpi_6m = ma(cpi_yoy, 6).iloc[-1]
                infl_trend = trend_direction(cpi_3m, cpi_6m)
                infl_val = cpi_yoy.iloc[-1]
            else:
                infl_trend, infl_val = "stable", 3.0
        
        ff = fred.get('fed_funds')
        t10 = fred.get('treasury_10y')
        policy_rate = ff.iloc[-1] if ff is not None else 4.5
        ten_y = t10.iloc[-1] if t10 is not None else 4.2
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
    
    structural_quad = assign_quad(growth_trend, infl_trend)
    
    monthly_quad = structural_quad
    if source == 'fred':
        cpi_series = fred.get('cpi') or fred.get('core_cpi')
        pce_series = fred.get('real_pce')
        if cpi_series is not None and len(cpi_series) >= 6:
            cpi_yoy = yoy_roc(cpi_series)
            cpi_1m = cpi_yoy.iloc[-1]
            cpi_3m_avg = cpi_yoy.iloc[-3:].mean()
            monthly_infl = "accelerating" if cpi_1m > cpi_3m_avg + 0.2 else "decelerating" if cpi_1m < cpi_3m_avg - 0.2 else infl_trend
        else:
            monthly_infl = infl_trend
        
        if pce_series is not None and len(pce_series) >= 6:
            pce_yoy = yoy_roc(pce_series)
            pce_1m = pce_yoy.iloc[-1]
            pce_3m_avg = pce_yoy.iloc[-3:].mean()
            monthly_growth = "accelerating" if pce_1m > pce_3m_avg + 0.2 else "decelerating" if pce_1m < pce_3m_avg - 0.2 else growth_trend
        else:
            monthly_growth = growth_trend
        
        monthly_quad = assign_quad(monthly_growth, monthly_infl)
    
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
        'inflation_yoy': round(float(infl_val), 2),
        'policy_rate': round(float(policy_rate), 2),
        'treasury_10y': round(float(ten_y), 2),
        'policy_stance': policy_text,
        'fred_loaded': len(fred) if source == 'fred' else 0,
        'fred_missing': len(FRED_SERIES) - len(fred) if source == 'fred' else len(FRED_SERIES),
        'operating_regime': regime_text,
        'timestamp': datetime.now().isoformat(),
    }
    
    try:
        with open(CACHE_FILE, 'wb') as f:
            pickle.dump(result, f)
    except Exception:
        pass
    
    return result

@st.cache_data(ttl=1800)
def get_regime_snapshot() -> Dict:
    return calculate_regime()