"""MacroRegime Pro v11.6f — Auto-Regime (No Hardcode) + TRR/LRR + On-Chain"""
import os
import sys
import glob
import time
import json
import logging
import requests
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import defaultdict

import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════════
# CACHE BUST & FRED KEY — MUST BE FIRST (before regime_engine import)
# ═══════════════════════════════════════════════════════════════════════════════
if "FRED_API_KEY" in st.secrets:
    os.environ["FRED_API_KEY"] = st.secrets["FRED_API_KEY"]

for f in glob.glob("/tmp/fred_cache_*.pkl") + glob.glob("/tmp/price_cache_*.pkl") + glob.glob("/tmp/regime_cache_*.pkl"):
    try: os.remove(f)
    except: pass

try: st.cache_data.clear()
except: pass

st.set_page_config(page_title="MacroRegime Pro", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path: sys.path.insert(0, SCRIPT_DIR)

from orchestration.build_snapshot import build_snapshot
from ui.command_center_page import render_command_center
from ui.theme import _inject_theme
from regime_engine import get_regime_snapshot

_inject_theme()

# ═══════════════════════════════════════════════════════════════════════════════
# MQA TRR/LRR ENGINE v6
# ═══════════════════════════════════════════════════════════════════════════════

TRR_PARAMS = {
    'tradeLen': 15, 'trendLen': 63, 'tailLen': 756,
    'rvLen': 20, 'normLen': 63, 'volRocLen': 5, 'atrLen': 14,
    'tradeATRMult': 1.35, 'trendATRMult': 2.05, 'tailATRMult': 4.20,
    'shockBoost': 0.22, 'trendShockBoost': 0.15, 'tailShockBoost': 0.12,
    'tradeThresh': 0.20, 'tradeNeutralBand': 0.06,
    'trendThresh': 0.14, 'trendNeutralBand': 0.05,
    'tailThresh': 0.10, 'tailNeutralBand': 0.03,
    'trendFreezeTF': 'M', 'tailFreezeTF': '3M',
    'trendBreakATR': 0.50, 'tailBreakATR': 0.75,
    'requireDoubleClose': True,
    'stocksVolMult': 1.00, 'forexVolMult': 0.35,
    'cryptoVolMult': 0.80, 'commodVolMult': 1.00,
}

def f_clip(x, lo, hi):
    return np.clip(x, lo, hi)

def f_clamp01(x):
    return np.clip(x, 0.0, 1.0)

def roc_s(series: pd.Series, length: int) -> pd.Series:
    return (series / series.shift(length) - 1.0) * 100.0

def z_score_s(series: pd.Series, length: int) -> pd.Series:
    ma = series.rolling(length).mean()
    sd = series.rolling(length).std()
    out = pd.Series(0.0, index=series.index)
    mask = sd.notna() & (sd != 0)
    out[mask] = (series[mask] - ma[mask]) / sd[mask]
    return out

def eff_ratio_s(series: pd.Series, length: int) -> pd.Series:
    den = series.diff().abs().rolling(length).sum()
    num = series.diff(length).abs()
    out = pd.Series(0.0, index=series.index)
    mask = den.notna() & (den != 0)
    out[mask] = num[mask] / den[mask]
    return out

def kama_s(series: pd.Series, er_len: int, fast: int, slow: int) -> pd.Series:
    er = eff_ratio_s(series, er_len)
    fsc = 2.0 / (fast + 1.0)
    ssc = 2.0 / (slow + 1.0)
    sc = np.power(er * (fsc - ssc) + ssc, 2.0)
    out = pd.Series(np.nan, index=series.index)
    out.iloc[0] = series.iloc[0]
    for i in range(1, len(series)):
        prev = out.iloc[i-1]
        if np.isnan(prev) or np.isnan(sc.iloc[i]):
            out.iloc[i] = series.iloc[i]
        else:
            out.iloc[i] = prev + sc.iloc[i] * (series.iloc[i] - prev)
    return out

def gk_bar_s(df: pd.DataFrame) -> pd.Series:
    eps = 1e-10
    h = np.maximum(df['High'], df['Open'] + eps)
    l = np.maximum(df['Low'], eps)
    o = np.maximum(df['Open'], eps)
    c = np.maximum(df['Close'], eps)
    return np.maximum(0.0, 0.5 * np.power(np.log(h / l), 2.0) - (2.0 * np.log(2.0) - 1.0) * np.power(np.log(c / o), 2.0))

def atr_wilder_s(df: pd.DataFrame, length: int = 14) -> pd.Series:
    high, low, close = df['High'], df['Low'], df['Close']
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.ewm(alpha=1.0/length, adjust=False, min_periods=length).mean()

def tf_reset_s(index: pd.DatetimeIndex, tf: str) -> pd.Series:
    s = pd.Series(index, index=index)
    shifted = s.shift(1)
    if tf == 'W':
        cur = s.dt.isocalendar().week
        prev = shifted.dt.isocalendar().week
        return pd.Series((cur != prev).fillna(False).values, index=index)
    elif tf == 'M':
        return pd.Series((s.dt.month != shifted.dt.month).fillna(False).values, index=index)
    elif tf == '3M':
        return pd.Series(((s.dt.month != shifted.dt.month) & (s.dt.month % 3 == 0)).fillna(False).values, index=index)
    else:
        return pd.Series((s.dt.year != shifted.dt.year).fillna(False).values, index=index)

def state_hysteresis_s(score: float, th: float, neutral: float, prev: int) -> int:
    if score > th: return 1
    elif score < -th: return -1
    elif abs(score) <= neutral: return 0
    return int(prev)

class TRRLRREngine:
    def __init__(self, params: dict = TRR_PARAMS):
        self.p = params

    def calc_bundle(self, df: pd.DataFrame, vol_mult: float = 1.0) -> pd.DataFrame:
        p = self.p
        c = df['Close']; h, l, o = df['High'], df['Low'], df['Open']
        v = df['Volume'].fillna(0)
        atr14 = atr_wilder_s(df, p['atrLen'])
        log_ret = np.log(c / c.shift(1))
        rv_fast = log_ret.rolling(p['rvLen']).std() * np.sqrt(252.0)
        rv_mid = log_ret.rolling(max(p['rvLen'] * 2, 30)).std() * np.sqrt(252.0)
        rv_slow = log_ret.rolling(max(p['rvLen'] * 4, 60)).std() * np.sqrt(252.0)
        tail_eff_len = max(63, min(p['tailLen'], 756))
        trade_basis = kama_s(c, p['tradeLen'], 2, p['tradeLen'])
        trend_basis = kama_s(c, p['trendLen'], 3, p['trendLen'])
        tail_basis = kama_s(c, tail_eff_len, 5, tail_eff_len)
        trade_roc = z_score_s(roc_s(c, p['tradeLen']), p['normLen'])
        trend_roc = z_score_s(roc_s(c, p['trendLen']), p['normLen'])
        tail_roc_raw = roc_s(c, 252).fillna(roc_s(c, 126)).fillna(roc_s(c, 63)).fillna(roc_s(c, 21)).fillna(0)
        tail_roc = z_score_s(tail_roc_raw, p['normLen'])
        trade_dist = z_score_s(((c / trade_basis.replace(0, np.nan)) - 1.0) * 100.0, p['normLen'])
        trend_dist = z_score_s(((c / trend_basis.replace(0, np.nan)) - 1.0) * 100.0, p['normLen'])
        tail_dist = z_score_s(((c / tail_basis.replace(0, np.nan)) - 1.0) * 100.0, p['normLen'])
        trade_slope = z_score_s(roc_s(trade_basis, 3), p['normLen'])
        trend_slope = z_score_s(roc_s(trend_basis, 10), p['normLen'])
        tail_slope_raw = roc_s(tail_basis, 21).fillna(roc_s(tail_basis, 10)).fillna(roc_s(tail_basis, 5)).fillna(0)
        tail_slope = z_score_s(tail_slope_raw, p['normLen'])
        roc_vol = roc_s(v, p['volRocLen'])
        trade_vol = z_score_s(roc_vol.ewm(span=2, adjust=False).mean(), p['normLen']) * vol_mult
        trend_vol = z_score_s(roc_vol.ewm(span=5, adjust=False).mean(), p['normLen']) * vol_mult
        tail_vol = z_score_s(roc_vol.ewm(span=10, adjust=False).mean(), p['normLen']) * vol_mult
        trade_pers = z_score_s(eff_ratio_s(c, max(5, int(round(p['tradeLen'] * 0.7)))), p['normLen'])
        trend_pers = z_score_s(eff_ratio_s(c, p['trendLen']), p['normLen'])
        tail_pers_63 = z_score_s(eff_ratio_s(c, 63), p['normLen'])
        tail_pers_21 = z_score_s(eff_ratio_s(c, 21), p['normLen'])
        tail_pers = tail_pers_63.fillna(tail_pers_21).fillna(0.0)
        rv_base_fast = rv_fast.rolling(50).mean().fillna(rv_fast)
        rv_base_mid = rv_mid.rolling(50).mean().fillna(rv_mid)
        rv_base_slow = rv_slow.rolling(50).mean().fillna(rv_slow)
        vr_fast = pd.Series(np.where(rv_base_fast > 0, (rv_fast / rv_base_fast) - 1.0, 0.0), index=c.index)
        vr_mid = pd.Series(np.where(rv_base_mid > 0, (rv_mid / rv_base_mid) - 1.0, 0.0), index=c.index)
        vr_slow = pd.Series(np.where(rv_base_slow > 0, (rv_slow / rv_base_slow) - 1.0, 0.0), index=c.index)
        trade_score = (0.30 * trade_roc + 0.24 * trade_slope + 0.18 * trade_dist + 0.14 * trade_pers + 0.10 * trade_vol - 0.08 * z_score_s(vr_fast, p['normLen']))
        trend_score = (0.24 * trend_roc + 0.28 * trend_slope + 0.22 * trend_dist + 0.14 * trend_pers + 0.08 * trend_vol - 0.06 * z_score_s(vr_mid, p['normLen']))
        tail_score = (0.18 * tail_roc + 0.30 * tail_slope + 0.24 * tail_dist + 0.16 * tail_pers + 0.06 * tail_vol - 0.04 * z_score_s(vr_slow, p['normLen']))
        atr_pct = pd.Series(np.where(c != 0, atr14 / c, 0.0), index=c.index)
        trade_shock = z_score_s(vr_fast + 0.60 * roc_s(atr_pct, 1), p['normLen'])
        trend_shock = z_score_s(vr_mid + 0.45 * roc_s(atr_pct, 3), p['normLen'])
        tail_shock = z_score_s(vr_slow + 0.30 * roc_s(atr_pct, 8), p['normLen'])
        gk = gk_bar_s(df)
        gk_rv = np.sqrt(np.maximum(gk.rolling(p['rvLen']).mean() * 252.0, 0.0))
        gk_rv_base = gk_rv.rolling(50).mean().fillna(gk_rv)
        gk_vov = gk_rv.rolling(max(p['rvLen'], 20)).std().fillna(0)
        gk_vov_base = gk_vov.rolling(50).mean().fillna(np.maximum(gk_vov, 0.001))
        bundle = pd.DataFrame({
            'atr': atr14.shift(1),
            'trdSc': trade_score.shift(1), 'trdShk': trade_shock.shift(1), 'trdBs': trade_basis.shift(1),
            'trnSc': trend_score.shift(1), 'trnShk': trend_shock.shift(1), 'trnBs': trend_basis.shift(1),
            'talSc': tail_score.shift(1),  'talShk': tail_shock.shift(1),  'talBs': tail_basis.shift(1),
            'c1': c.shift(1), 'c2': c.shift(2),
            'v1': v.shift(1), 'vsma1': v.rolling(20).mean().shift(1),
            'gkRv': gk_rv.shift(1), 'gkRvBase': gk_rv_base.shift(1),
            'gkVov': gk_vov.shift(1), 'gkVovBase': gk_vov_base.shift(1),
        }, index=df.index)
        return bundle

    def calc_latest(self, df: pd.DataFrame, vol_mult: float = 1.0) -> Optional[dict]:
        p = self.p
        bundle = self.calc_bundle(df, vol_mult)
        if len(bundle) < 300: return None
        c = df['Close'].values
        atr14_current = atr_wilder_s(df, 14).values
        n = len(bundle)
        atr = bundle['atr'].values; trdSc = bundle['trdSc'].values; trdShk = bundle['trdShk'].values; trdBs = bundle['trdBs'].values
        trnSc = bundle['trnSc'].values; trnShk = bundle['trnShk'].values; trnBs = bundle['trnBs'].values
        talSc = bundle['talSc'].values; talShk = bundle['talShk'].values; talBs = bundle['talBs'].values
        gkRv = bundle['gkRv'].values; gkRvBase = bundle['gkRvBase'].values
        gkVov = bundle['gkVov'].values; gkVovBase = bundle['gkVovBase'].values
        trend_reset = tf_reset_s(df.index, p['trendFreezeTF']).values
        tail_reset = tf_reset_s(df.index, p['tailFreezeTF']).values
        trade_phase = np.zeros(n, dtype=int); trend_phase = np.zeros(n, dtype=int); tail_phase = np.zeros(n, dtype=int)
        pub_trend_basis = np.full(n, np.nan); pub_trend_atr = np.full(n, np.nan)
        pub_tail_basis = np.full(n, np.nan); pub_tail_atr = np.full(n, np.nan)
        eff_trend_basis = np.full(n, np.nan); eff_tail_basis = np.full(n, np.nan)
        trend_age = np.zeros(n, dtype=int); tail_age = np.zeros(n, dtype=int)
        for i in range(n):
            if i == 0:
                pub_trend_basis[i] = trnBs[i] if not np.isnan(trnBs[i]) else c[i]
                pub_trend_atr[i] = atr[i] if not np.isnan(atr[i]) else atr14_current[i]
                pub_tail_basis[i] = talBs[i] if not np.isnan(talBs[i]) else c[i]
                pub_tail_atr[i] = atr[i] if not np.isnan(atr[i]) else atr14_current[i]
                continue
            if trend_reset[i]:
                pub_trend_basis[i] = trnBs[i] if not np.isnan(trnBs[i]) else c[i]
                pub_trend_atr[i] = atr[i] if not np.isnan(atr[i]) else atr14_current[i]
            else:
                pub_trend_basis[i] = pub_trend_basis[i-1] if not np.isnan(pub_trend_basis[i-1]) else (trnBs[i] if not np.isnan(trnBs[i]) else c[i])
                pub_trend_atr[i] = pub_trend_atr[i-1] if not np.isnan(pub_trend_atr[i-1]) else (atr[i] if not np.isnan(atr[i]) else atr14_current[i])
            if tail_reset[i]:
                pub_tail_basis[i] = talBs[i] if not np.isnan(talBs[i]) else c[i]
                pub_tail_atr[i] = atr[i] if not np.isnan(atr[i]) else atr14_current[i]
            else:
                pub_tail_basis[i] = pub_tail_basis[i-1] if not np.isnan(pub_tail_basis[i-1]) else (talBs[i] if not np.isnan(talBs[i]) else c[i])
                pub_tail_atr[i] = pub_tail_atr[i-1] if not np.isnan(pub_tail_atr[i-1]) else (atr[i] if not np.isnan(atr[i]) else atr14_current[i])
            gk_rv_factor = f_clip(0.50 + 0.50 * (gkRv[i] / gkRvBase[i]), 0.65, 1.50) if gkRvBase[i] > 0 else 1.0
            gk_vov_factor = f_clip(1.0 + 0.25 * max((gkVov[i] / gkVovBase[i]) - 1.0, 0.0), 1.0, 1.25) if gkVovBase[i] > 0 else 1.0
            ptsw = 1.0 + p['shockBoost'] * max(trdShk[i], 0.0)
            pre_trade_w = atr[i] * p['tradeATRMult'] * gk_rv_factor * gk_vov_factor * max(0.65, ptsw)
            pre_trade_trr = trdBs[i] + pre_trade_w
            pre_trade_lrr = max(trdBs[i] - pre_trade_w, 1e-10)
            ptnsw = 1.0 + p['trendShockBoost'] * max(trnShk[i], 0.0)
            pre_trend_w = max(pub_trend_atr[i], atr[i]) * p['trendATRMult'] * gk_rv_factor * gk_vov_factor * max(0.70, ptnsw)
            pre_trend_trr = pub_trend_basis[i] + pre_trend_w
            pre_trend_lrr = max(pub_trend_basis[i] - pre_trend_w, 1e-10)
            ptlsW = 1.0 + p['tailShockBoost'] * max(talShk[i], 0.0)
            pre_tail_w = max(pub_tail_atr[i], atr[i]) * p['tailATRMult'] * gk_rv_factor * gk_vov_factor * max(0.80, ptlsW)
            pre_tail_trr = pub_tail_basis[i] + pre_tail_w
            pre_tail_lrr = max(pub_tail_basis[i] - pre_tail_w, 1e-10)
            raw_trade = state_hysteresis_s(trdSc[i], p['tradeThresh'], p['tradeNeutralBand'], trade_phase[i-1])
            raw_trend = state_hysteresis_s(trnSc[i], p['trendThresh'], p['trendNeutralBand'], trend_phase[i-1])
            raw_tail = state_hysteresis_s(talSc[i], p['tailThresh'], p['tailNeutralBand'], tail_phase[i-1])
            tbu = c[i] > pre_trade_trr; tbd = c[i] < pre_trade_lrr
            trade_phase[i] = 1 if tbu else (-1 if tbd else raw_trade)
            ttu = c[i] > pre_trend_trr and trend_phase[i-1] <= 0
            ttd = c[i] < pre_trend_lrr and trend_phase[i-1] >= 0
            if ttu:
                trend_phase[i] = 1; eff_trend_basis[i] = c[i]; pub_trend_atr[i] = atr14_current[i]
            elif ttd:
                trend_phase[i] = -1; eff_trend_basis[i] = c[i]; pub_trend_atr[i] = atr14_current[i]
            else:
                trend_phase[i] = raw_trend; eff_trend_basis[i] = eff_trend_basis[i-1] if not np.isnan(eff_trend_basis[i-1]) else pub_trend_basis[i]
            tlu = c[i] > pre_tail_trr and tail_phase[i-1] <= 0
            tld = c[i] < pre_tail_lrr and tail_phase[i-1] >= 0
            if tlu:
                tail_phase[i] = 1; eff_tail_basis[i] = c[i]; pub_tail_atr[i] = atr14_current[i]
            elif tld:
                tail_phase[i] = -1; eff_tail_basis[i] = c[i]; pub_tail_atr[i] = atr14_current[i]
            else:
                tail_phase[i] = raw_tail; eff_tail_basis[i] = eff_tail_basis[i-1] if not np.isnan(eff_tail_basis[i-1]) else pub_tail_basis[i]
            trend_age[i] = 0 if (trend_reset[i] or ttu or ttd) else trend_age[i-1] + 1
            tail_age[i] = 0 if (tail_reset[i] or tlu or tld) else tail_age[i-1] + 1
        i = n - 1
        use_trend_basis = eff_trend_basis[i] if not np.isnan(eff_trend_basis[i]) else pub_trend_basis[i]
        use_tail_basis = eff_tail_basis[i] if not np.isnan(eff_tail_basis[i]) else pub_tail_basis[i]
        final_trend_atr = max(pub_trend_atr[i], atr[i]); final_tail_atr = max(pub_tail_atr[i], atr[i])
        tbb = 0.35 if (c[i] > pre_trade_trr or c[i] < pre_trade_lrr) else 0.0
        trbb = 0.50 if (ttu or ttd) else 0.0
        tlbb = 0.40 if (tlu or tld) else 0.0
        gk_rv_factor = f_clip(0.50 + 0.50 * (gkRv[i] / gkRvBase[i]), 0.65, 1.50) if gkRvBase[i] > 0 else 1.0
        gk_vov_factor = f_clip(1.0 + 0.25 * max((gkVov[i] / gkVovBase[i]) - 1.0, 0.0), 1.0, 1.25) if gkVovBase[i] > 0 else 1.0
        tsw = 1.0 + (p['shockBoost'] + tbb) * max(trdShk[i], 0.0)
        trade_w = atr[i] * p['tradeATRMult'] * gk_rv_factor * gk_vov_factor * max(0.65, tsw)
        trade_trr = trdBs[i] + trade_w; trade_lrr = max(trdBs[i] - trade_w, 1e-10)
        trsw = 1.0 + (p['trendShockBoost'] + trbb) * max(trnShk[i], 0.0)
        trend_w = final_trend_atr * p['trendATRMult'] * gk_rv_factor * gk_vov_factor * max(0.70, trsw)
        trend_trr = use_trend_basis + trend_w; trend_lrr = max(use_trend_basis - trend_w, 1e-10)
        tlsw = 1.0 + (p['tailShockBoost'] + tlbb) * max(talShk[i], 0.0)
        tail_w = final_tail_atr * p['tailATRMult'] * gk_rv_factor * gk_vov_factor * max(0.80, tlsw)
        tail_trr = use_tail_basis + tail_w; tail_lrr = max(use_tail_basis - tail_w, 1e-10)
        c_series = df['Close']
        abs_chg = c_series.diff().abs()
        er_den = abs_chg.rolling(20).sum()
        er_val = pd.Series(np.where(er_den == 0, 0.0, c_series.diff(20).abs() / er_den), index=df.index)
        idx0 = pd.Series(range(len(df)), index=df.index)
        corr = c_series.rolling(30).corr(idx0)
        r2 = pd.Series(np.where(np.isnan(corr), 0.0, corr ** 2), index=df.index)
        adx_proxy = abs_chg.rolling(14).mean() / (df['High'] - df['Low']).rolling(14).mean().replace(0, np.nan)
        adx_norm = f_clip((adx_proxy.iloc[-1] - 12.0) / 28.0, 0.0, 1.0)
        er_norm = f_clip(er_val.iloc[-1], 0.0, 1.0)
        r2_norm = f_clip(r2.iloc[-1], 0.0, 1.0)
        quality_score = 100.0 * (0.45 * adx_norm + 0.35 * er_norm + 0.20 * r2_norm)
        atr_pct_vals = np.where(c_series.values != 0, (bundle['atr'].values / c_series.values) * 100.0, 0.0)
        atr_pct_ser = pd.Series(atr_pct_vals, index=df.index)
        atr_pct_base = atr_pct_ser.rolling(50).mean().fillna(atr_pct_ser)
        act_atr = f_clamp01(atr_pct_ser.iloc[-1] / (atr_pct_base.iloc[-1] * 1.25)) if atr_pct_base.iloc[-1] > 0 else 0.5
        rv_now = np.log(c_series / c_series.shift(1)).rolling(p['rvLen']).std() * np.sqrt(252.0)
        rv_base = rv_now.rolling(50).mean().fillna(rv_now)
        act_rv = f_clamp01(rv_now.iloc[-1] / (rv_base.iloc[-1] * 1.20)) if rv_base.iloc[-1] > 0 else 0.5
        vol_base20 = df['Volume'].rolling(20).mean().fillna(df['Volume'])
        act_vol_raw = f_clamp01(df['Volume'].iloc[-1] / (vol_base20.iloc[-1] * 1.35)) if vol_base20.iloc[-1] > 0 else 0.5
        act_vol = 0.35 + 0.65 * act_vol_raw * vol_mult
        activity_score = 100.0 * f_clip(0.42 * act_atr + 0.43 * act_rv + 0.15 * act_vol, 0.0, 1.0)
        compression_score = 100.0 * f_clip(1.0 - (0.50 * act_atr + 0.38 * act_rv + 0.12 * act_vol), 0.0, 1.0)
        vol_regime_confirm = gkVov[i] > gkVovBase[i] * 1.30
        return {
            'tradeTRR': float(trade_trr), 'tradeLRR': float(trade_lrr),
            'trendTRR': float(trend_trr), 'trendLRR': float(trend_lrr),
            'tailTRR': float(tail_trr), 'tailLRR': float(tail_lrr),
            'tradePhase': int(trade_phase[i]), 'trendPhase': int(trend_phase[i]), 'tailPhase': int(tail_phase[i]),
            'trendTransUp': bool(ttu), 'trendTransDown': bool(ttd),
            'tailTransUp': bool(tlu), 'tailTransDown': bool(tld),
            'tradeBreakUp': bool(c[i] > trade_trr), 'tradeBreakDown': bool(c[i] < trade_lrr),
            'trendAge': int(trend_age[i]), 'tailAge': int(tail_age[i]),
            'qualityScore': float(quality_score), 'activityScore': float(activity_score),
            'compressionScore': float(compression_score), 'volRegimeConfirm': bool(vol_regime_confirm),
            'pubTradeScore': float(trdSc[i]), 'pubTrendScore': float(trnSc[i]), 'pubTailScore': float(talSc[i]),
        }

@st.cache_data(ttl=600)
def _fetch_trr_data(ticker: str, period: str = "3y") -> Optional[pd.DataFrame]:
    try:
        df = yf.download(ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.dropna()
        return df if len(df) >= 300 else None
    except Exception:
        return None

GATE_CONFIG = {
    "US_STOCKS":  {"vol_mult": 1.00, "quality_min": 55, "activity_min": 40, "allow_short": True,  "max_trend_age": 35},
    "IHSG":       {"vol_mult": 1.00, "quality_min": 50, "activity_min": 35, "allow_short": False, "max_trend_age": 30},
    "COMMODITIES":{"vol_mult": 1.00, "quality_min": 50, "activity_min": 40, "allow_short": True,  "max_trend_age": 45},
    "FOREX":      {"vol_mult": 0.35, "quality_min": 55, "activity_min": 40, "allow_short": True,  "max_trend_age": 40},
    "CRYPTO":     {"vol_mult": 0.80, "quality_min": 50, "activity_min": 45, "allow_short": True,  "max_trend_age": 30},
}

_trr_engine = TRRLRREngine(TRR_PARAMS)

def evaluate_ticker(ticker: str, asset_class: str) -> Optional[dict]:
    cfg = GATE_CONFIG.get(asset_class, GATE_CONFIG["US_STOCKS"])
    period = "2y" if asset_class == "CRYPTO" else "3y"
    df = _fetch_trr_data(ticker, period)
    if df is None: return None
    try:
        r = _trr_engine.calc_latest(df, vol_mult=cfg['vol_mult'])
    except Exception:
        return None
    if not r: return None
    price = df['Close'].iloc[-1]
    long_gate = (r['tradeBreakUp'] or r['trendTransUp'] or r['tailTransUp']) and r['qualityScore'] >= cfg['quality_min'] and r['activityScore'] >= cfg['activity_min'] and r['trendAge'] <= cfg['max_trend_age']
    short_gate = cfg['allow_short'] and (r['tradeBreakDown'] or r['trendTransDown'] or r['tailTransDown']) and r['qualityScore'] >= cfg['quality_min'] and r['activityScore'] >= cfg['activity_min'] and r['trendAge'] <= cfg['max_trend_age']
    if not long_gate and not short_gate: return None
    signal = "LONG" if long_gate else "SHORT"
    conf = min(100, int(50 + r['qualityScore'] * 0.3 + r['activityScore'] * 0.2 + (25 if (r['trendTransUp'] or r['trendTransDown'] or r['tailTransUp'] or r['tailTransDown']) else 0)))
    reasons = []
    if r['tradeBreakUp']: reasons.append(f"Price > TradeTRR ({r['tradeTRR']:.2f})")
    if r['tradeBreakDown']: reasons.append(f"Price < TradeLRR ({r['tradeLRR']:.2f})")
    if r['trendTransUp']: reasons.append("TREND PHASE TRANSITION UP")
    if r['trendTransDown']: reasons.append("TREND PHASE TRANSITION DOWN")
    if r['tailTransUp']: reasons.append("TAIL PHASE TRANSITION UP")
    if r['tailTransDown']: reasons.append("TAIL PHASE TRANSITION DOWN")
    if r['trendPhase'] == 1: reasons.append("TrendPhase BULL")
    if r['trendPhase'] == -1: reasons.append("TrendPhase BEAR")
    return {
        'ticker': ticker, 'signal': signal, 'confidence': conf, 'price': round(price, 4),
        'tradeTRR': round(r['tradeTRR'], 4), 'tradeLRR': round(r['tradeLRR'], 4),
        'trendTRR': round(r['trendTRR'], 4), 'trendLRR': round(r['trendLRR'], 4),
        'tailTRR': round(r['tailTRR'], 4), 'tailLRR': round(r['tailLRR'], 4),
        'trendPhase': r['trendPhase'], 'tailPhase': r['tailPhase'],
        'trendAge': r['trendAge'], 'tailAge': r['tailAge'],
        'quality': round(r['qualityScore'], 1), 'activity': round(r['activityScore'], 1),
        'compression': round(r['compressionScore'], 1),
        'volRegime': "EXPANDING" if r['volRegimeConfirm'] else "NORMAL",
        'reason': " | ".join(reasons)
    }

def render_trr_section(ticker_list: List[str], asset_class: str, title: str = "🎯 TRR/LRR Live Signals"):
    if not ticker_list: return
    hits = []
    debug_rows = []
    for t in ticker_list:
        ev = evaluate_ticker(t, asset_class)
        if ev: 
            hits.append(ev)
        else:
            df = _fetch_trr_data(t, "2y" if asset_class == "CRYPTO" else "3y")
            if df is not None:
                try:
                    r = _trr_engine.calc_latest(df, vol_mult=GATE_CONFIG.get(asset_class, GATE_CONFIG["US_STOCKS"])['vol_mult'])
                    if r:
                        price = df['Close'].iloc[-1]
                        cfg = GATE_CONFIG.get(asset_class, GATE_CONFIG["US_STOCKS"])
                        reasons = []
                        if not (r['tradeBreakUp'] or r['trendTransUp'] or r['tailTransUp']): reasons.append("No breakout")
                        if r['qualityScore'] < cfg['quality_min']: reasons.append(f"Q{r['qualityScore']:.0f}<{cfg['quality_min']}")
                        if r['activityScore'] < cfg['activity_min']: reasons.append(f"A{r['activityScore']:.0f}<{cfg['activity_min']}")
                        if r['trendAge'] > cfg['max_trend_age']: reasons.append(f"Age{r['trendAge']}>{cfg['max_trend_age']}")
                        debug_rows.append({
                            'ticker': t, 'price': round(price, 2),
                            'q': round(r['qualityScore'], 1), 'a': round(r['activityScore'], 1),
                            'age': r['trendAge'], 'phase': r['trendPhase'],
                            'fail': " | ".join(reasons) if reasons else "Short not allowed" if not cfg['allow_short'] else "Unknown"
                        })
                except Exception:
                    pass
    
    if not hits:
        st.caption(f"TRR/LRR: No {asset_class} tickers passed the gate today.")
        if debug_rows:
            with st.expander(f"🔍 {asset_class} TRR/LRR Debug ({len(debug_rows)} tickers evaluated)"):
                st.dataframe(pd.DataFrame(debug_rows), use_container_width=True, height=200)
        return
    
    hits.sort(key=lambda x: (0 if x['signal'] == 'LONG' else 1, -x['confidence']))
    st.markdown(f"**{title}**")
    for h in hits:
        color = "#3fb950" if h['signal'] == 'LONG' else "#f85149"
        icon = "▲" if h['signal'] == 'LONG' else "▼"
        with st.container():
            c1, c2, c3 = st.columns([1.2, 2.5, 1.5])
            with c1:
                st.markdown(f"<span style='color:{color};font-weight:800;font-size:16px;'>{icon} {h['ticker']}</span>", unsafe_allow_html=True)
                st.caption(f"Conf: **{h['confidence']}**/100")
            with c2:
                st.caption(f"Price {h['price']} | TradeTRR {h['tradeTRR']} | TradeLRR {h['tradeLRR']}")
                st.caption(f"Trend: Phase {h['trendPhase']} | Age {h['trendAge']}d | Quality {h['quality']} | Activity {h['activity']}")
            with c3:
                st.caption(f"Trigger: {h['reason']}")
        st.divider()

# ═══════════════════════════════════════════════════════════════════════════════
# ON-CHAIN ALPHA SCANNER
# ═══════════════════════════════════════════════════════════════════════════════
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class ChainConfig:
    name: str
    chain_slug: str
    dune_chain_id: Optional[str] = None
    etherscan_subdomain: Optional[str] = None
    native_token: str = ""
    native_token_contract: Optional[str] = None

CHAIN_REGISTRY = {
    'ethereum': ChainConfig('Ethereum', 'Ethereum', 'ethereum', 'api.etherscan.io', 'ETH', '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2'),
    'base': ChainConfig('Base', 'Base', 'base', 'api.basescan.org', 'ETH', '0x4200000000000000000000000000000000000006'),
    'arbitrum': ChainConfig('Arbitrum', 'Arbitrum', 'arbitrum', 'api.arbiscan.io', 'ETH', '0x82aF49447D8a07e3bd95BD0d56f35241523fBab1'),
    'optimism': ChainConfig('Optimism', 'Optimism', 'optimism', 'api-optimistic.etherscan.io', 'ETH', '0x4200000000000000000000000000000000000006'),
    'solana': ChainConfig('Solana', 'Solana', 'solana', None, 'SOL', 'So11111111111111111111111111111111111111112'),
    'bittensor': ChainConfig('Bittensor', 'Bittensor', None, None, 'TAO', None),
    'avalanche': ChainConfig('Avalanche', 'Avalanche', 'avalanche', 'api.snowtrace.io', 'AVAX', '0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7'),
    'polygon': ChainConfig('Polygon', 'Polygon', 'polygon', 'api.polygonscan.com', 'MATIC', '0x7D1AfA7B718fb893dB30A3abc0Cfc608AaCfeBB0'),
    'bnb': ChainConfig('BNB Chain', 'BSC', 'bsc', 'api.bscscan.com', 'BNB', '0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c'),
}

class MultiChainAlphaScanner:
    def __init__(self, dune_key=None, etherscan_key=None, taostats_key=None):
        self.dune_sim_key = dune_key
        self.etherscan_key = etherscan_key
        self.taostats_key = taostats_key
        self._last_etherscan_call = 0
        self._last_dune_call = 0
        self._last_solscan_call = 0

    def get_chain_macro_flow(self, chain_slug: str, lookback_days: int = 7) -> Dict:
        try:
            base = "https://api.llama.fi"
            results = {'chain': chain_slug, 'timestamp': datetime.utcnow().isoformat()}
            tvl_url = f"{base}/v2/historicalChainTvl/{chain_slug}"
            tvl_res = requests.get(tvl_url, timeout=15)
            if tvl_res.status_code == 200:
                tvl_data = tvl_res.json()
                if tvl_data:
                    latest = tvl_data[-1]
                    past = tvl_data[-min(lookback_days+1, len(tvl_data))]
                    results['tvl_now'] = latest[1]
                    results['tvl_7d_ago'] = past[1]
                    results['tvl_delta_pct'] = round((latest[1] - past[1]) / past[1] * 100, 2) if past[1] > 0 else 0
            stb_url = f"{base}/stablecoincharts/{chain_slug}"
            stb_res = requests.get(stb_url, timeout=15)
            if stb_res.status_code == 200:
                stb_data = stb_res.json()
                if stb_data:
                    latest_stb = stb_data[-1]['totalCirculatingUSD']['peggedUSD']
                    past_stb = stb_data[-min(lookback_days+1, len(stb_data))]['totalCirculatingUSD']['peggedUSD']
                    results['stablecoin_now'] = latest_stb
                    results['stablecoin_delta_pct'] = round((latest_stb - past_stb) / past_stb * 100, 2) if past_stb > 0 else 0
            vol_url = f"{base}/overview/dexs/{chain_slug}?excludeTotalDataChart=false&excludeTotalDataChartBreakdown=true&dataType=dailyVolume"
            vol_res = requests.get(vol_url, timeout=15)
            if vol_res.status_code == 200:
                vol_data = vol_res.json()
                if 'totalDataChart' in vol_data and vol_data['totalDataChart']:
                    vols = [x[1] for x in vol_data['totalDataChart'] if x[1]]
                    if len(vols) >= 2:
                        results['dex_volume_24h'] = vols[-1]
                        results['dex_volume_median_7d'] = np.median(vols[-7:]) if len(vols) >= 7 else np.median(vols)
                        results['dex_volume_spike'] = round(vols[-1] / results['dex_volume_median_7d'], 2) if results['dex_volume_median_7d'] > 0 else 0
            fees_url = f"{base}/overview/fees/{chain_slug}?excludeTotalDataChart=false&dataType=dailyFees"
            fees_res = requests.get(fees_url, timeout=15)
            if fees_res.status_code == 200:
                fees_data = fees_res.json()
                if 'totalDataChart' in fees_data and fees_data['totalDataChart']:
                    fees = [x[1] for x in fees_data['totalDataChart'] if x[1]]
                    if fees:
                        results['fees_24h'] = fees[-1]
                        results['fees_median_7d'] = np.median(fees[-7:]) if len(fees) >= 7 else np.median(fees)
            score = 0
            if results.get('stablecoin_delta_pct', 0) > 15: score += 40
            elif results.get('stablecoin_delta_pct', 0) > 10: score += 25
            elif results.get('stablecoin_delta_pct', 0) > 5: score += 10
            if results.get('tvl_delta_pct', 0) > 10: score += 30
            elif results.get('tvl_delta_pct', 0) > 5: score += 15
            if results.get('dex_volume_spike', 0) > 3: score += 20
            elif results.get('dex_volume_spike', 0) > 1.5: score += 10
            results['macro_score'] = min(score, 100)
            results['macro_signal'] = 'HOT' if score >= 60 else 'WARM' if score >= 35 else 'COLD'
            return results
        except Exception as e:
            logger.error(f"DeFiLlama error for {chain_slug}: {e}")
            return {'chain': chain_slug, 'error': str(e)}

    def _dune_sim_request(self, endpoint: str, params: Dict) -> Optional[Dict]:
        if not self.dune_sim_key: return None
        elapsed = time.time() - self._last_dune_call
        if elapsed < 0.21: time.sleep(0.21 - elapsed)
        try:
            base = "https://api.dune.com/api/sim"
            headers = {"X-Dune-API-Key": self.dune_sim_key}
            res = requests.get(f"{base}{endpoint}", headers=headers, params=params, timeout=15)
            self._last_dune_call = time.time()
            if res.status_code == 200: return res.json()
            else: logger.warning(f"Dune Sim error {res.status_code}: {res.text[:200]}")
            return None
        except Exception as e:
            logger.error(f"Dune Sim request failed: {e}")
            return None

    def get_token_holders_dune(self, chain: str, token_contract: str, top_n: int = 50) -> pd.DataFrame:
        data = self._dune_sim_request("/token-holders", {"chain": chain, "contract": token_contract, "limit": top_n})
        if not data or 'holders' not in data: return pd.DataFrame()
        df = pd.DataFrame(data['holders'])
        df['chain'] = chain; df['token'] = token_contract
        return df

    def _etherscan_request(self, subdomain: str, params: Dict) -> Optional[Dict]:
        if not self.etherscan_key: return None
        elapsed = time.time() - self._last_etherscan_call
        if elapsed < 0.21: time.sleep(0.21 - elapsed)
        try:
            url = f"https://{subdomain}/api"
            params['apikey'] = self.etherscan_key
            res = requests.get(url, params=params, timeout=15)
            self._last_etherscan_call = time.time()
            if res.status_code == 200:
                data = res.json()
                if data.get('status') == '1': return data
                else: logger.warning(f"Etherscan msg: {data.get('result', data.get('message'))}")
            return None
        except Exception as e:
            logger.error(f"Etherscan error: {e}")
            return None

    def get_token_balance_etherscan(self, subdomain: str, token_contract: str, wallet: str) -> float:
        data = self._etherscan_request(subdomain, {'module': 'account', 'action': 'tokenbalance', 'contractaddress': token_contract, 'address': wallet, 'tag': 'latest'})
        if data and 'result' in data: return int(data['result']) / 1e18
        return 0.0

    def get_token_transfers_etherscan(self, subdomain: str, token_contract: str, wallet: str) -> pd.DataFrame:
        data = self._etherscan_request(subdomain, {'module': 'account', 'action': 'tokentx', 'contractaddress': token_contract, 'address': wallet, 'sort': 'desc'})
        if data and isinstance(data.get('result'), list):
            df = pd.DataFrame(data['result'])
            if not df.empty and 'value' in df.columns: df['value_float'] = df['value'].astype(float) / 1e18
            return df
        return pd.DataFrame()

    def _solscan_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        elapsed = time.time() - self._last_solscan_call
        if elapsed < 0.5: time.sleep(0.5 - elapsed)
        try:
            base = "https://public-api.solscan.io"
            res = requests.get(f"{base}/{endpoint}", params=params, timeout=15)
            self._last_solscan_call = time.time()
            if res.status_code == 200: return res.json()
            return None
        except Exception as e:
            logger.error(f"Solscan error: {e}")
            return None

    def get_solana_portfolio(self, wallet: str) -> Dict:
        return self._solscan_request(f"account/portfolio", {'address': wallet}) or {}

    def _taostats_request(self, endpoint: str) -> Optional[Dict]:
        if not self.taostats_key: return None
        try:
            base = "https://api.taostats.io/api"
            headers = {"Authorization": f"Bearer {self.taostats_key}"}
            res = requests.get(f"{base}/{endpoint}", headers=headers, timeout=15)
            if res.status_code == 200: return res.json()
            return None
        except Exception as e:
            logger.error(f"TAOStats error: {e}")
            return None

    def get_bittensor_overview(self) -> Dict:
        data = self._taostats_request("network/overview")
        return data or {}

    def get_bittensor_subnet_flows(self) -> pd.DataFrame:
        data = self._taostats_request("subnets")
        if data and 'data' in data: return pd.DataFrame(data['data'])
        return pd.DataFrame()

    def scan_chain_alpha(self, chain_key: str, token_contract: Optional[str] = None, whale_wallets: Optional[List[str]] = None) -> Dict:
        config = CHAIN_REGISTRY.get(chain_key)
        if not config: return {'error': f'Chain {chain_key} not supported'}
        result = {'chain': chain_key, 'timestamp': datetime.utcnow().isoformat(), 'layers': {}}
        macro = self.get_chain_macro_flow(config.chain_slug)
        result['layers']['macro'] = macro
        whale_score = 0
        whale_data = []
        if whale_wallets and config.etherscan_subdomain and token_contract:
            for wallet in whale_wallets:
                balance = self.get_token_balance_etherscan(config.etherscan_subdomain, token_contract, wallet)
                tx_df = self.get_token_transfers_etherscan(config.etherscan_subdomain, token_contract, wallet)
                net_flow = 0
                if not tx_df.empty and 'value_float' in tx_df.columns:
                    cutoff = (datetime.utcnow() - timedelta(days=7)).timestamp()
                    recent = tx_df[tx_df['timeStamp'].astype(int) > cutoff]
                    if not recent.empty:
                        inflow = recent[recent['to'].str.lower() == wallet.lower()]['value_float'].sum()
                        outflow = recent[recent['from'].str.lower() == wallet.lower()]['value_float'].sum()
                        net_flow = inflow - outflow
                whale_data.append({'wallet': wallet, 'balance': balance, 'net_flow_7d': net_flow, 'accumulating': net_flow > 0})
            if whale_data:
                accum_count = sum(1 for w in whale_data if w['accumulating'])
                total_flow = sum(w['net_flow_7d'] for w in whale_data if w['accumulating'])
                whale_score = min((accum_count / len(whale_data) * 50) + (min(total_flow / 10000, 50)), 100)
        elif whale_wallets and chain_key == 'solana' and token_contract:
            for wallet in whale_wallets:
                portfolio = self.get_solana_portfolio(wallet)
                balance = 0
                if portfolio and 'data' in portfolio:
                    for item in portfolio['data']:
                        if item.get('tokenAddress') == token_contract:
                            balance = item.get('balance', 0) / (10 ** item.get('decimals', 9))
                whale_data.append({'wallet': wallet, 'balance': balance, 'net_flow_7d': 0, 'accumulating': False})
            whale_score = min(sum(w['balance'] for w in whale_data) / 100000 * 10, 100)
        result['layers']['whale'] = {'wallets_tracked': len(whale_wallets) if whale_wallets else 0, 'whale_data': whale_data, 'whale_score': round(whale_score, 2)}
        dune_score = 0
        if self.dune_sim_key and token_contract and config.dune_chain_id:
            try:
                holders = self.get_token_holders_dune(config.dune_chain_id, token_contract, top_n=20)
                if not holders.empty and 'balance' in holders.columns:
                    total_top20 = holders['balance'].sum()
                    dune_score = min(total_top20 / 1000000 * 5, 40)
            except Exception as e:
                logger.warning(f"Dune layer error: {e}")
        result['layers']['dune_realtime'] = {'dune_score': round(dune_score, 2)}
        tao_score = 0
        if chain_key == 'bittensor':
            overview = self.get_bittensor_overview()
            subnets = self.get_bittensor_subnet_flows()
            if overview:
                tao_score = min((overview.get('staking_ratio', 0) * 30) + (subnets.shape[0] if not subnets.empty else 0) * 2, 100)
            result['layers']['bittensor'] = {'overview': overview, 'subnet_count': subnets.shape[0] if not subnets.empty else 0, 'tao_score': round(tao_score, 2)}
        weights = {'macro': 0.35, 'whale': 0.35, 'dune': 0.20, 'tao': 0.10 if chain_key == 'bittensor' else 0}
        composite = (weights['macro'] * macro.get('macro_score', 0) + weights['whale'] * whale_score + weights['dune'] * dune_score + weights['tao'] * tao_score)
        result['composite_alpha_score'] = round(composite, 2)
        result['verdict'] = ('🔥 STRONG ACCUMULATION' if composite >= 70 else '⚡ MONITOR CLOSELY' if composite >= 45 else '❄️ PASS / WAIT')
        return result

    def scan_all_chains(self, targets: Dict[str, Dict]) -> pd.DataFrame:
        results = []
        for chain_key, config in targets.items():
            logger.info(f"Scanning {chain_key}...")
            res = self.scan_chain_alpha(chain_key, token_contract=config.get('token'), whale_wallets=config.get('wallets'))
            results.append({
                'chain': chain_key,
                'alpha_score': res.get('composite_alpha_score', 0),
                'verdict': res.get('verdict', 'N/A'),
                'macro_signal': res.get('layers', {}).get('macro', {}).get('macro_signal', 'N/A'),
                'tvl_delta': res.get('layers', {}).get('macro', {}).get('tvl_delta_pct', 0),
                'stable_delta': res.get('layers', {}).get('macro', {}).get('stablecoin_delta_pct', 0),
                'dex_spike': res.get('layers', {}).get('macro', {}).get('dex_volume_spike', 0),
                'whale_score': res.get('layers', {}).get('whale', {}).get('whale_score', 0),
                'detail': res
            })
            time.sleep(1)
        return pd.DataFrame(results)

# =============================================================================
# SNAPSHOT LOADER — AUTO REGIME (NO HARDCODE)
# =============================================================================
@st.cache_data(ttl=300)
def _load_snapshot():
    try:
        snap = build_snapshot(force_refresh=True)
    except Exception as e:
        st.warning(f"build_snapshot error: {e}")
        snap = {}
    
    # ═══════════════════════════════════════════════════════════════════════
    # AUTO REGIME — 100% data-driven, zero hardcode
    # ═══════════════════════════════════════════════════════════════════════
    regime = get_regime_snapshot()
    
    q = snap.get("q", {})
    q["quad"] = regime['quad']
    q["structural_quad"] = regime['structural_quad']
    q["monthly_quad"] = regime['monthly_quad']
    q["global_quad"] = regime['global_quad']
    q["confidence"] = regime['confidence']
    q["operating_regime"] = regime['operating_regime']
    q["growth_yoy"] = regime['growth_yoy']
    q["inflation_yoy"] = regime['inflation_yoy']
    q["policy_rate"] = regime['policy_rate']
    q["treasury_10y"] = regime['treasury_10y']
    q["policy_stance"] = regime['policy_stance']
    q["source"] = regime['source']
    q["growth_trend"] = regime.get('growth_trend', '—')
    q["inflation_trend"] = regime.get('inflation_trend', '—')
    # DEBUG: forward monthly calculation trace (read-only, zero logic impact)
    q["monthly_debug"] = regime.get('monthly_debug', {})
    snap["q"] = q
    
    fred_meta = snap.get("fred_meta", {})
    fred_meta["loaded"] = regime['fred_loaded']
    fred_meta["missing"] = regime['fred_missing']
    fred_meta["api_key_present"] = bool(os.environ.get("FRED_API_KEY") or st.secrets.get("FRED_API_KEY"))
    fred_meta["source"] = regime['source']
    fred_meta["growth_yoy"] = regime['growth_yoy']
    fred_meta["inflation_yoy"] = regime['inflation_yoy']
    snap["fred_meta"] = fred_meta
    
    # Tickers watchlist — Hedgeye research picks (human-curated, not data-driven)
    rt = snap.get("regime_tickers", {})
    if not rt:
        rt = {
            "us_longs": ["IWM","XLI","ITB","XTL","EQRR","GII","EWH","EWW","ARGT","EIS","IBIT","HII","CAT","UPS","LII","JBHT","MAR","ONTO","EMR","RH","SBUX","TXG","AVO","FRPT","PEP","XOM","HSY","WMB","ET","COAL","YCS"],
            "us_shorts": ["XLK","XLF","XLY","IHF","PSCH","MAGS","CIBR","IVES","MSFO","DESK","GRNY","SKYY","MSTY","BTAL","XLP","TLT","ZROZ","ROP","RBLX","TRU","NVDA"],
            "ihsg_buys": ["BBCA.JK","BBRI.JK","TLKM.JK","ASII.JK","UNVR.JK","INDF.JK","KLBF.JK"],
            "fx_longs": ["USDJPY","GLD","AAAU","YCS"],
            "fx_shorts": ["EURUSD","AUDUSD","UUP"],
            "commodity_longs": ["SLV","GDX","SLX","CPER","PPLT","XOP","OIH","BNO","GLD","AAAU","COAL"],
            "commodity_shorts": ["DUST","BITS"],
            "crypto_longs": ["BTC-USD","ETH-USD","IBIT"],
            "crypto_shorts": ["SOL-USD"],
            "em_longs": ["EWW","UAE","GLIN","EIS","JPXN","TUR","ARGT","EWH"],
            "em_shorts": ["IDX"],
            "fi_longs": ["HYG","LQD","BUXX","CLOX"],
            "fi_shorts": ["TLT","ZROZ"],
        }
    snap["regime_tickers"] = rt
    return snap

snap = _load_snapshot()
q = snap.get("q", {})
f = snap.get("f", {})
quad = q.get("quad","Q2")
structural_quad = q.get("structural_quad", "Q2")
monthly_quad = q.get("monthly_quad", "Q2")
global_quad = q.get("global_quad", "Q2")
conf = q.get("confidence", 0.50)
vix = q.get("vix_last", 20.0)
operating_regime = q.get("operating_regime", "Calculating...")
source = q.get("source", "unknown")
growth_yoy = q.get("growth_yoy", 0.0)
inflation_yoy = q.get("inflation_yoy", 0.0)
policy_stance = q.get("policy_stance", "—")
tickers = snap.get("regime_tickers", {})
prices = snap.get("prices", {})
btl = snap.get("bottleneck_discovery", {})
narr = snap.get("narrative_discovery", {})

def _h(html): st.markdown(" ".join(html.split()), unsafe_allow_html=True)

QC = {"Q1":("#1a4d2e","#4ade80"),"Q2":("#5c3d00","#fbbf24"),"Q3":("#5c2b00","#fb923c"),"Q4":("#5c1a1a","#f87171")}
def _qbg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[0]
def _qfg(q_): return QC.get(q_, ("#2d3748","#a0aec0"))[1]

s_bg, s_fg = _qbg(structural_quad), _qfg(structural_quad)
m_bg, m_fg = _qbg(monthly_quad), _qfg(monthly_quad)
g_bg, g_fg = _qbg(global_quad), _qfg(global_quad)

source_badge = "🟢 FRED" if source == "fred" else "🟡 YF Proxy" if source == "yfinance_proxy" else "⚪ Fallback"
source_color = "#3fb950" if source == "fred" else "#fbbf24" if source == "yfinance_proxy" else "#8b949e"

_h(f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <div style="font-size:32px;">🧭</div>
    <div>
      <div style="font-size:24px;font-weight:800;color:#e6edf3;">MacroRegime <span style="color:#58a6ff;">Pro</span></div>
      <div style="font-size:11px;color:#8b949e;">v11.6f · Auto-Regime · TRR/LRR · On-Chain Alpha</div>
    </div>
  </div>
  <div style="text-align:right;">
    <div style="font-size:11px;color:#8b949e;">{datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M')} UTC</div>
    <div style="font-size:11px;color:{source_color};">{source_badge} · S:{structural_quad} · M:{monthly_quad} · G:{global_quad}</div>
  </div>
</div>
""")

_h(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:14px;padding:16px;margin-bottom:14px;">
  <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px;flex-wrap:wrap;">
    <span style="background:{s_bg};color:{s_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">S:{structural_quad}</span>
    <span style="background:{m_bg};color:{m_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">M:{monthly_quad}</span>
    <span style="background:{g_bg};color:{g_fg};padding:4px 10px;border-radius:20px;font-size:13px;font-weight:700;">G:{global_quad}</span>
    <span style="margin-left:auto;color:#fb923c;font-size:13px;font-weight:600;">🔥 {operating_regime}</span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>Conf: <span style="color:#3fb950;font-weight:600;">{conf:.0%}</span></span>
    <span>Growth: <span style="color:#3fb950;">{growth_yoy:.1f}% YoY ({q.get('growth_trend','—')})</span></span>
    <span>Inflation: <span style="color:#fb923c;">{inflation_yoy:.1f}% YoY ({q.get('inflation_trend','—')})</span></span>
    <span>Policy: <span style="color:#58a6ff;">{policy_stance}</span></span>
  </div>
  <div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;flex-wrap:wrap;font-size:12px;color:#c9d1d9;">
    <span>▲ Best Long: <span style="color:#3fb950;font-weight:600;">XTL · EQRR · IWM</span></span>
    <span>▼ Best Short: <span style="color:#f85149;font-weight:600;">TLT · XLK · XLP</span></span>
    <span>🛢️ Energy: <span style="color:#fb923c;font-weight:600;">XOP · OIH · BNO</span></span>
    <span>🥇 Gold: <span style="color:#fbbf24;font-weight:600;">AAAU · GLD · SLV</span></span>
  </div>
  <div style="font-size:11px;color:#8b949e;margin-top:8px;border-top:1px solid #30363d;padding-top:8px;">
    Data Source: {source_badge} · Real PCE (Growth) · CPI (Inflation) · DFF+DGS10 (Policy)
  </div>
</div>
""")

tabs = st.tabs(["⚡ Command Center", "🌍 Markets", "📊 Regime Deep Dive", "⚠️ Risk & Diag"])

with tabs[0]:
    render_command_center(snap)

with tabs[1]:
    prices = snap.get("prices", {})
    transition = snap.get("regime_transition", {})
    fw = transition.get("front_run_window", "—")
    btl = snap.get("bottleneck_discovery", {})
    narr = snap.get("narrative_discovery", {})

    def ret_n(s, n):
        if s is None or len(s) < n+1: return float("nan")
        try:
            b = float(s.iloc[-(n+1)]); e = float(s.iloc[-1])
            return float(e/b-1) if b != 0 else float("nan")
        except: return float("nan")

    def get_ret(s, n):
        r = ret_n(s, n)
        return f"{r:+.1%}" if r == r else "—"

    def ticker_card(tk, name, ret1m, ret3m, signal):
        color = "#3fb950" if signal == "long" else "#f85149" if signal == "short" else "#d29922"
        icon = "▲" if signal == "long" else "▼" if signal == "short" else "⚡"
        return f"""
        <div style="background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;flex:1;min-width:140px;">
          <div>
            <div style="font-size:13px;font-weight:700;color:#e6edf3;">{tk}</div>
            <div style="font-size:10px;color:#8b949e;">{name}</div>
          </div>
          <div style="text-align:right;">
            <div style="font-size:11px;color:{color};font-weight:700;">{icon} {ret1m}</div>
            <div style="font-size:9px;color:#8b949e;">3M: {ret3m}</div>
          </div>
        </div>
        """

    def render_cards(ticker_list, names_map, signal_type, per_row=2):
        if not ticker_list: return
        cards = []
        for t in ticker_list:
            s = prices.get(t)
            cards.append(ticker_card(t, names_map.get(t, t), get_ret(s, 21), get_ret(s, 63), signal_type))
        for i in range(0, len(cards), per_row):
            row = cards[i:i+per_row]
            _h(f'<div style="display:flex;gap:8px;margin-bottom:8px;">' + "".join(row) + '</div>')

    def render_heatmap(assets_list):
        if not prices: return
        heat_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for tk, name in assets_list:
            s = prices.get(tk)
            if s is not None:
                r1 = ret_n(s, 21); r3 = ret_n(s, 63)
                c = "#1a4d2e" if r1 > 0.05 else "#2d5a3d" if r1 > 0 else "#5c1a1a" if r1 < -0.05 else "#3d1a1a" if r1 < 0 else "#2d3748"
                txt = "#4ade80" if r1 > 0 else "#f87171" if r1 < 0 else "#a0aec0"
                heat_html.append(f'<div style="background:{c};padding:6px 10px;border-radius:6px;text-align:center;min-width:80px;"><div style="font-size:11px;color:#8b949e;">{name}</div><div style="font-size:13px;color:{txt};font-weight:700;">{r1:+.1%}</div><div style="font-size:9px;color:#8b949e;">3M {r3:+.1%}</div></div>')
        heat_html.append('</div>')
        _h("".join(heat_html))

    def render_market_leaders(asset_list, benchmark_tk=None, title="Market Leadership"):
        bench_ret = ret_n(prices.get(benchmark_tk), 63) if benchmark_tk else float("nan")
        rows = []
        for tk, name in asset_list:
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63)
                rel = (r3 - bench_ret) if bench_ret == bench_ret and r3 == r3 else r3
                rows.append({"name": name, "rel": rel, "tk": tk})
        if not rows:
            st.caption(f"No price data for {title}")
            return
        rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
        st.markdown(f"**📊 {title} (Top 5)**")
        for s in rows[:5]:
            rel = s["rel"]
            rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
            bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
            _h(f"""
            <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
              <div style="width:70px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
              <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
              </div>
              <div style="width:60px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
            </div>
            """)

    def render_sector_bars():
        SECS = {"XLE":"Energy","XLF":"Fin","XLI":"Ind","XLB":"Mat","XLK":"Tech","XLV":"Health","XLY":"Con.D","XLP":"Con.S","XLU":"Util","XLRE":"RE"}
        spy3 = ret_n(prices.get("SPY"), 63)
        sec_rows = []
        for tk, name in SECS.items():
            s = prices.get(tk)
            if s is not None and len(s) > 63:
                r3 = ret_n(s, 63); rel = (r3 - spy3) if spy3==spy3 and r3==r3 else float("nan")
                sec_rows.append({"name": name, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            st.markdown("**📊 Sector Leadership (Top 5)**")
            for s in sec_rows[:5]:
                rel = s["rel"]
                rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
                bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
                _h(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                  <div style="width:60px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
                  <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                    <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
                  </div>
                  <div style="width:50px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
                </div>
                """)

    def render_ihsg_sector_bars():
        SECTORS = {
            "Energy":   ["ADRO.JK", "ITMG.JK", "PTBA.JK"],
            "Finance":  ["BBCA.JK", "BBRI.JK", "BMRI.JK"],
            "Consumer": ["UNVR.JK", "INDF.JK", "ICBP.JK"],
            "Infra":    ["TLKM.JK", "PGAS.JK", "EXCL.JK"],
            "Property": ["CTRA.JK", "PWON.JK", "BSDE.JK"],
            "Mining":   ["ANTM.JK", "INCO.JK", "MDKA.JK"],
            "Health":   ["KLBF.JK", "SIDO.JK", "KAEF.JK"],
            "Agri":     ["AALI.JK", "LSIP.JK", "SGRO.JK"],
            "Industri": ["ASII.JK", "AUTO.JK", "MPMX.JK"],
        }
        jkse3 = ret_n(prices.get("^JKSE"), 63)
        sec_rows = []
        for name, proxies in SECTORS.items():
            rets = []
            for tk in proxies:
                s = prices.get(tk)
                if s is not None and len(s) > 63:
                    r = ret_n(s, 63)
                    if r == r: rets.append(r)
            if rets:
                avg = sum(rets) / len(rets)
                rel = (avg - jkse3) if jkse3 == jkse3 else avg
                sec_rows.append({"name": name, "rel": rel})
        if sec_rows:
            sec_rows.sort(key=lambda r: r["rel"] if r["rel"] == r["rel"] else -999, reverse=True)
            st.markdown("**📊 IDX Sector Leadership (Top 5)**")
            for s in sec_rows[:5]:
                rel = s["rel"]
                rel_pct = min(max((rel + 0.15) / 0.3 * 100, 0), 100) if rel == rel else 50
                bar_color = "#3fb950" if rel > 0 else "#f85149" if rel < 0 else "#8b949e"
                _h(f"""
                <div style="display:flex;align-items:center;gap:8px;margin:4px 0;">
                  <div style="width:60px;font-size:11px;color:#c9d1d9;">{s["name"]}</div>
                  <div style="flex:1;background:#21262d;border-radius:4px;height:16px;overflow:hidden;">
                    <div style="width:{rel_pct}%;background:{bar_color};height:100%;border-radius:4px;"></div>
                  </div>
                  <div style="width:50px;text-align:right;font-size:11px;color:{bar_color};font-weight:600;">{rel:+.1%}</div>
                </div>
                """)

    FX_TICKERS = {"USDJPY","EURUSD","AUDUSD","GBPUSD","USDCAD","USDIDR","UUP","DXY","EURGBP","EURJPY","GBPJPY","NZDUSD","USDCNH","USDCHF","AAAU","GLD","YCS"}
    COMM_TICKERS = {"SLV","GDX","SLX","CPER","PPLT","XOP","OIH","BNO","GLD","AAAU","DUST","BITS","XAUUSD","XAGUSD","XTIUSD","XBRUSD","XCUUSD","XNGUSD","URA","COAL"}
    CRYPTO_TICKERS = {"BTC-USD","ETH-USD","SOL-USD","XRP-USD","ADA-USD","AVAX-USD","DOT-USD","MATIC-USD","LINK-USD","UNI-USD","LTC-USD","BCH-USD","ETC-USD","DOGE-USD","SHIB-USD","TON-USD","NEAR-USD","APT-USD","SUI-USD","IBIT"}

    def is_us_ticker(tk):
        return not any(x in tk for x in [".JK","-USD"]) and tk not in ["^JKSE"] and tk not in FX_TICKERS and tk not in COMM_TICKERS and tk not in CRYPTO_TICKERS
    def is_ihsg_ticker(tk):
        return ".JK" in tk or tk == "^JKSE"
    def is_fx_ticker(tk):
        return tk in FX_TICKERS
    def is_comm_ticker(tk):
        return tk in COMM_TICKERS
    def is_crypto_ticker(tk):
        return tk in CRYPTO_TICKERS

    def render_bottleneck_filtered(filter_fn, market_name):
        # FALLBACK: kalo btl kosong atau cuma sedikit, generate dari price momentum
        if not btl or not btl.get("front_run_basket") or len(btl.get("front_run_basket", [])) < 3:
            momentum_basket = []
            for tk in prices.keys():
                if filter_fn(tk):
                    s = prices.get(tk)
                    if s is not None and len(s) > 21:
                        r1 = ret_n(s, 21)
                        r3 = ret_n(s, 63)
                        score = abs(r1) * 2 + abs(r3) if r1 == r1 else 0
                        if score > 0.05:
                            stage = "early" if r1 > 0.05 else "mature" if r1 < -0.05 else "building"
                            momentum_basket.append({
                                "ticker": tk, "sector": market_name, 
                                "bottleneck_score": round(score, 2), "stage": stage
                            })
            if momentum_basket:
                btl = {"front_run_basket": sorted(momentum_basket, key=lambda x: x["bottleneck_score"], reverse=True)[:12]}
            else:
                st.caption(f"No {market_name} bottleneck — adaptive + momentum scan empty.")
                return
        
        if btl.get("summary"): st.caption(btl["summary"])
        basket = btl.get("front_run_basket", [])
        total = len(basket)
        filtered = [item for item in basket if filter_fn(item.get("ticker", ""))]
        if not filtered:
            st.caption(f"No {market_name} bottleneck detected — adaptive scan returned {total} candidate(s), none matched {market_name} ticker patterns.")
            return
        b_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
        for item in filtered[:8]:
            tk = item.get("ticker","—")
            sec = item.get("sector","—")[:10]
            score = item.get("bottleneck_score",0)
            stage = item.get("stage","—")
            stage_c = {"mature":"#f85149","building":"#d29922","early":"#3fb950"}.get(stage, "#8b949e")
            b_html.append(f'<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:6px 10px;text-align:center;"><div style="font-size:12px;font-weight:700;color:#e6edf3;">{tk}</div><div style="font-size:9px;color:#8b949e;">{sec}</div><div style="font-size:10px;color:{stage_c};">{stage} · {score:.2f}</div></div>')
        b_html.append('</div>')
        _h("".join(b_html))

    def render_master_filtered(long_key, short_key, color_long, color_short, filter_fn, market_name):
        all_tickers = []
        for t in tickers.get(long_key, [])[:4]:
            all_tickers.append((t, "Long", color_long))
        if short_key:
            for t in tickers.get(short_key, [])[:4]:
                all_tickers.append((t, "Short", color_short))
        if btl and btl.get("front_run_basket"):
            for item in btl["front_run_basket"][:6]:
                tk = item.get("ticker","—")
                if filter_fn(tk) and tk not in [x[0] for x in all_tickers]:
                    all_tickers.append((tk, "Adap", "#58a6ff"))
        if narr and narr.get("active_narratives"):
            for n in narr["active_narratives"][:3]:
                for b in n.get("primary_beneficiaries", [])[:3]:
                    if filter_fn(b) and b not in [x[0] for x in all_tickers]:
                        all_tickers.append((b, "Narr", "#a371f7"))
        if all_tickers:
            m_html = ['<div style="display:flex;gap:6px;flex-wrap:wrap;">']
            for t, side, color in all_tickers:
                m_html.append(f'<div style="background:#0d1117;border:1px solid #30363d;border-radius:4px;padding:4px 8px;font-size:11px;color:{color};font-weight:600;">{t} <span style="color:#8b949e;font-size:9px;">{side}</span></div>')
            m_html.append('</div>')
            _h("".join(m_html))
        else:
            st.caption(f"No {market_name} tickers")

    mkt_tabs = st.tabs(["🇺🇸 US Stocks", "🇮🇩 IHSG", "💱 FX", "🛢️ Commodities", "🔐 Crypto"])

    with mkt_tabs[0]:
        us_longs = tickers.get("us_longs", [])
        us_shorts = tickers.get("us_shorts", [])
        names = {"SPY":"S&P 500","QQQ":"Nasdaq","IWM":"Russell 2K","XLE":"Energy","XLK":"Tech","XLF":"Finance","XLI":"Industrials","XLB":"Materials","XLV":"Health","XLY":"Consumer","XLP":"Staples","XLU":"Utilities","XLRE":"REITs","SPLV":"Low Vol","TLT":"Long Bond","GLD":"Gold","SMH":"Semis","HII":"Huntington","CAT":"Caterpillar","UPS":"UPS","LII":"Lennox","JBHT":"JB Hunt","MAR":"Marriott","ONTO":"Onto","EMR":"Emerson","RH":"Restoration","SBUX":"Starbucks","TXG":"10x Genomics","AVO":"Mission Produce","FRPT":"Freshpet","PEP":"Pepsi","XOM":"Exxon","HSY":"Hershey","WMB":"Williams","ET":"Energy Transfer","ROP":"Roper","RBLX":"Roblox","TRU":"TransUnion","NVDA":"Nvidia","XTL":"Telecom","EQRR":"Rising Rates","GII":"Infrastructure","EWH":"Hong Kong","EWW":"Mexico","ARGT":"Argentina","EIS":"Israel","IBIT":"Bitcoin ETF","COAL":"Coal","YCS":"Short Yen"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(us_longs, names, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(us_shorts, names, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell 2K"),("TLT","Bond"),("GLD","Gold"),("BTC-USD","BTC"),("XTIUSD","Oil"),("UUP","USD")])
        render_sector_bars()
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_us_ticker, "US")
        st.markdown("**📋 Master Board**")
        render_master_filtered("us_longs", "us_shorts", "#3fb950", "#f85149", is_us_ticker, "US")
        st.markdown("**🎯 TRR/LRR Signal Layer**")
        all_us = list(set(us_longs + us_shorts + [item.get("ticker","") for item in btl.get("front_run_basket", []) if is_us_ticker(item.get("ticker",""))]))
        render_trr_section(all_us, "US_STOCKS")

    with mkt_tabs[1]:
        ihsg_longs = tickers.get("ihsg_buys", [])
        names_ihsg = {"BBCA.JK":"BCA","BBRI.JK":"BRI","ASII.JK":"Astra","TLKM.JK":"Telkom","ADRO.JK":"Adaro","ANTM.JK":"Antam","PTBA.JK":"Bukit Asam","ITMG.JK":"Indomining","INCO.JK":"Vale","KLBF.JK":"Kalbe","UNVR.JK":"Unilever","INDF.JK":"Indofood"}
        st.markdown("**📍 NOW — LONG**")
        render_cards(ihsg_longs, names_ihsg, "long", 3)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("^JKSE","IHSG"),("BBCA.JK","BCA"),("BBRI.JK","BRI"),("ASII.JK","Astra"),("TLKM.JK","Telkom")])
        render_ihsg_sector_bars()
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_ihsg_ticker, "IHSG")
        st.markdown("**📋 Master Board**")
        render_master_filtered("ihsg_buys", None, "#fb923c", "#f85149", is_ihsg_ticker, "IHSG")
        st.markdown("**🎯 TRR/LRR Signal Layer**")
        all_ihsg = list(set(ihsg_longs + [item.get("ticker","") for item in btl.get("front_run_basket", []) if is_ihsg_ticker(item.get("ticker",""))]))
        render_trr_section(all_ihsg, "IHSG")

    with mkt_tabs[2]:
        fx_longs = tickers.get("fx_longs", [])
        fx_shorts = tickers.get("fx_shorts", [])
        names_fx = {"EURUSD":"EUR/USD","USDJPY":"USD/JPY","AUDUSD":"AUD/USD","USDIDR":"USD/IDR","UUP":"DXY","GBPUSD":"GBP/USD","USDCAD":"USD/CAD","NZDUSD":"NZD/USD","USDCHF":"USD/CHF","GLD":"Gold","AAAU":"Gold","YCS":"Short Yen"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(fx_longs, names_fx, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(fx_shorts, names_fx, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("EURUSD","EUR/USD"),("USDJPY","USD/JPY"),("AUDUSD","AUD/USD"),("USDIDR","USD/IDR"),("UUP","DXY")])
        render_market_leaders([("UUP","DXY"),("USDJPY","USD/JPY"),("EURUSD","EUR/USD"),("AUDUSD","AUD/USD"),("GBPUSD","GBP/USD"),("USDCAD","USD/CAD")], benchmark_tk="UUP", title="FX Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_fx_ticker, "FX")
        st.markdown("**📋 Master Board**")
        render_master_filtered("fx_longs", "fx_shorts", "#58a6ff", "#f85149", is_fx_ticker, "FX")
        st.markdown("**🎯 TRR/LRR Signal Layer**")
        all_fx = list(set(fx_longs + fx_shorts + [item.get("ticker","") for item in btl.get("front_run_basket", []) if is_fx_ticker(item.get("ticker",""))]))
        render_trr_section(all_fx, "FOREX")

    with mkt_tabs[3]:
        comm_longs = tickers.get("commodity_longs", [])
        comm_shorts = tickers.get("commodity_shorts", [])
        names_comm = {"SLV":"Silver","GDX":"Gold Miners","SLX":"Steel","CPER":"Copper","PPLT":"Platinum","XOP":"Oil Explorers","OIH":"Oil Services","BNO":"Brent Oil","GLD":"Gold","AAAU":"Gold","COAL":"Coal","DUST":"Gold Bear","BITS":"Bitcoin Strat","XTIUSD":"WTI Oil","XAUUSD":"Gold","XCUUSD":"Copper","XAGUSD":"Silver","XNGUSD":"Nat Gas"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(comm_longs, names_comm, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(comm_shorts, names_comm, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("XTIUSD","WTI Oil"),("XAUUSD","Gold"),("XCUUSD","Copper"),("XAGUSD","Silver"),("XNGUSD","Nat Gas")])
        render_market_leaders([("XAUUSD","Gold"),("XTIUSD","WTI Oil"),("XCUUSD","Copper"),("XAGUSD","Silver"),("XNGUSD","Nat Gas"),("XBRUSD","Brent"),("URA","Uranium")], benchmark_tk="XAUUSD", title="Commodity Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_comm_ticker, "Commodities")
        st.markdown("**📋 Master Board**")
        render_master_filtered("commodity_longs", "commodity_shorts", "#fb923c", "#f85149", is_comm_ticker, "Commodities")
        st.markdown("**🎯 TRR/LRR Signal Layer**")
        all_comm = list(set(comm_longs + comm_shorts + [item.get("ticker","") for item in btl.get("front_run_basket", []) if is_comm_ticker(item.get("ticker",""))]))
        render_trr_section(all_comm, "COMMODITIES")

    with mkt_tabs[4]:
        cry_longs = tickers.get("crypto_longs", [])
        cry_shorts = tickers.get("crypto_shorts", [])
        names_cry = {"BTC-USD":"Bitcoin","ETH-USD":"Ethereum","SOL-USD":"Solana","XRP-USD":"XRP","IBIT":"Bitcoin ETF"}
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**📍 NOW — LONG**")
            render_cards(cry_longs, names_cry, "long", 2)
        with c2:
            st.markdown("**📍 NOW — SHORT**")
            render_cards(cry_shorts, names_cry, "short", 2)
        st.divider()
        st.markdown("**🌍 Heatmap**")
        render_heatmap([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP")])
        render_market_leaders([("BTC-USD","Bitcoin"),("ETH-USD","Ethereum"),("SOL-USD","Solana"),("XRP-USD","XRP"),("ADA-USD","Cardano"),("DOT-USD","Polkadot")], benchmark_tk="BTC-USD", title="Crypto Leadership")
        st.markdown("**🔍 Bottleneck Scan**")
        render_bottleneck_filtered(is_crypto_ticker, "Crypto")
        st.markdown("**📋 Master Board**")
        render_master_filtered("crypto_longs", "crypto_shorts", "#a371f7", "#f85149", is_crypto_ticker, "Crypto")
        st.markdown("**🎯 TRR/LRR Signal Layer**")
        all_cry = list(set(cry_longs + cry_shorts + [item.get("ticker","") for item in btl.get("front_run_basket", []) if is_crypto_ticker(item.get("ticker",""))]))
        render_trr_section(all_cry, "CRYPTO")

        st.divider()
        st.markdown("**⛓️ On-Chain Alpha — Auto Scan**")
        st.caption("Multi-chain accumulation detection · Runs automatically when you open this tab")

        dune_key = st.secrets.get("DUNE_SIM_KEY", "")
        etherscan_key = st.secrets.get("ETHERSCAN_KEY", "")
        taostats_key = st.secrets.get("TAOSTATS_KEY", "")

        with st.expander("🔑 API Keys (simpan di secrets.toml untuk auto-run)", expanded=False):
            c1, c2, c3 = st.columns(3)
            with c1: dune_input = st.text_input("Dune Sim", value=dune_key, type="password", key="dune_crypto")
            with c2: eth_input = st.text_input("Etherscan", value=etherscan_key, type="password", key="eth_crypto")
            with c3: tao_input = st.text_input("TAOStats", value=taostats_key, type="password", key="tao_crypto")

        if dune_input: dune_key = dune_input
        if eth_input: etherscan_key = eth_input
        if tao_input: taostats_key = tao_input

        scanner = MultiChainAlphaScanner(dune_key=dune_key, etherscan_key=etherscan_key, taostats_key=taostats_key)

        crypto_targets = {
            'base': {'token': '0x4200000000000000000000000000000000000006', 'wallets': []},
            'solana': {'token': 'So11111111111111111111111111111111111111112', 'wallets': []},
            'bittensor': {'token': None, 'wallets': []},
            'ethereum': {'token': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'wallets': []},
        }

        with st.spinner("⛓️ Scanning on-chain flows (Base, Solana, Bittensor, Ethereum)... ⏳ ~30s"):
            df_crypto = scanner.scan_all_chains(crypto_targets)

        if not df_crypto.empty:
            hot = df_crypto[df_crypto['alpha_score'] >= 60]
            warm = df_crypto[(df_crypto['alpha_score'] >= 40) & (df_crypto['alpha_score'] < 60)]
            cold = df_crypto[df_crypto['alpha_score'] < 40]

            cols = st.columns(3)
            with cols[0]:
                _h(f'<div style="background:#1a4d2e;border:1px solid #30363d;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:20px;font-weight:800;color:#4ade80;">{len(hot)}</div><div style="font-size:10px;color:#8b949e;">🔥 HOT</div></div>')
            with cols[1]:
                _h(f'<div style="background:#5c3d00;border:1px solid #30363d;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:20px;font-weight:800;color:#fbbf24;">{len(warm)}</div><div style="font-size:10px;color:#8b949e;">⚡ WARM</div></div>')
            with cols[2]:
                _h(f'<div style="background:#5c1a1a;border:1px solid #30363d;border-radius:10px;padding:10px;text-align:center;"><div style="font-size:20px;font-weight:800;color:#f87171;">{len(cold)}</div><div style="font-size:10px;color:#8b949e;">❄️ COLD</div></div>')

            for _, row in df_crypto.iterrows():
                ch = row['chain']
                score = row['alpha_score']
                verdict = row['verdict']
                macro_sig = row['macro_signal']
                tvl_d = row['tvl_delta']
                stable_d = row['stable_delta']
                dex_spike = row['dex_spike']
                whale_s = row['whale_score']

                score_color = "#4ade80" if score >= 70 else "#fbbf24" if score >= 45 else "#f87171"
                score_bg = "#1a4d2e" if score >= 70 else "#5c3d00" if score >= 45 else "#5c1a1a"

                _h(f"""
                <div style="background:#161b22;border:1px solid #30363d;border-radius:10px;padding:10px;margin-bottom:8px;">
                  <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                    <div style="display:flex;align-items:center;gap:8px;">
                      <div style="background:{score_bg};color:{score_color};padding:3px 10px;border-radius:16px;font-size:11px;font-weight:700;">{ch.upper()}</div>
                      <div style="font-size:13px;font-weight:700;color:#e6edf3;">{verdict}</div>
                    </div>
                    <div style="font-size:18px;font-weight:800;color:{score_color};">{score:.0f}<span style="font-size:10px;color:#8b949e;">/100</span></div>
                  </div>
                  <div style="display:flex;gap:12px;flex-wrap:wrap;font-size:10px;color:#c9d1d9;">
                    <span>📊 Macro: <span style="color:#fb923c;font-weight:600;">{macro_sig}</span></span>
                    <span>📈 TVL: <span style="color:#3fb950;font-weight:600;">{tvl_d:+.1f}%</span></span>
                    <span>💰 Stable: <span style="color:#3fb950;font-weight:600;">{stable_d:+.1f}%</span></span>
                    <span>🌊 DEX: <span style="color:#58a6ff;font-weight:600;">{dex_spike:.1f}x</span></span>
                    <span>🐋 Whale: <span style="color:#a371f7;font-weight:600;">{whale_s:.0f}</span></span>
                  </div>
                </div>
                """)

            st.caption("📊 Stable Δ = dry powder · 📈 TVL Δ = smart money deposit · 🌊 DEX = momentum · 🐋 Whale = accumulation")
        else:
            st.info("On-chain scan returned no data — check API keys or network connectivity.")

with tabs[2]:
    show_raw = st.toggle("Show raw regime state JSON", value=False)
    if show_raw: st.markdown("**Regime State**"); st.json(q)
    
    # DEBUG: Monthly calculation trace (read-only, no logic impact)
    monthly_debug = q.get("monthly_debug", {})
    if monthly_debug:
        with st.expander("🔍 Monthly Calculation Trace (Debug)", expanded=False):
            st.caption("Read-only trace of how Monthly quad was derived. Zero impact on logic.")
            st.json(monthly_debug)
    
    st.markdown("**Structural Probabilities**")
    probs = q.get("structural_probs", {}); m_probs = q.get("monthly_probs", {})
    if probs:
        for k in ["Q1","Q2","Q3","Q4"]:
            p = probs.get(k, 0.0); mp = m_probs.get(k, 0.0) if m_probs else 0.0
            is_s = k == structural_quad; is_m = k == monthly_quad and not is_s
            label = f"{'●' if is_s else '◉' if is_m else '○'} {k}: S={p:.0%} M={mp:.0%}"
            st.progress(p, text=label)
    else: st.info("No probability data")

with tabs[3]:
    st.subheader("⚠️ Risk & Diagnostics")
    fred_meta = snap.get("fred_meta", {})
    if fred_meta:
        loaded = fred_meta.get("loaded", 0); missing = fred_meta.get("missing", 0)
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("FRED Loaded", f"{loaded}/{loaded+missing}")
        with c2: st.metric("Real Share", f"{fred_meta.get('real_share', 0):.0%}")
        with c3: st.metric("API Key", "✅" if fred_meta.get("api_key_present") else "❌")
        if missing > 0:
            mk = fred_meta.get("missing_keys", [])
            if mk: st.warning(f"Missing: {', '.join(mk[:10])}")
    else: st.error("FRED metadata unavailable")
    
    if fred_meta and fred_meta.get("loaded", 0) == 0:
        st.error("🚨 FRED 0 loaded — all proxy data.")
        if st.button("🔄 Force Clear Cache & Reload"):
            st.cache_data.clear()
            st.rerun()