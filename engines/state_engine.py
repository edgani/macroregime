
from __future__ import annotations
import numpy as np, pandas as pd

def last(s):
    try:
        x=pd.Series(s).dropna(); return float(x.iloc[-1]) if len(x) else np.nan
    except Exception:return np.nan

def pct_rank(s,years=10):
    try:
        x=pd.Series(s).dropna().sort_index(); x=x.loc[x.index>=x.index[-1]-pd.DateOffset(years=years)]
        return float((x<=x.iloc[-1]).mean()) if len(x)>=20 else np.nan
    except Exception:return np.nan

def delta(s,days):
    try:
        x=pd.Series(s).dropna().sort_index(); old=x.loc[:x.index[-1]-pd.Timedelta(days=days)]
        return float(x.iloc[-1]-old.iloc[-1]) if len(old) else np.nan
    except Exception:return np.nan

def pct_delta(s,days):
    try:
        x=pd.Series(s).dropna().sort_index(); old=x.loc[:x.index[-1]-pd.Timedelta(days=days)]
        return float(x.iloc[-1]/old.iloc[-1]-1) if len(old) and old.iloc[-1]!=0 else np.nan
    except Exception:return np.nan

def annualized_3m(idx):
    try:
        x=pd.Series(idx).dropna().sort_index(); old=x.loc[:x.index[-1]-pd.DateOffset(months=3)]
        return float((x.iloc[-1]/old.iloc[-1])**4-1) if len(old) and old.iloc[-1]>0 else np.nan
    except Exception:return np.nan

def volatility_state(vix):
    x=pd.Series(vix).dropna().sort_index()
    if len(x)<100:return {'state':'NO DATA','percentile':np.nan,'method':'rolling relative distribution'}
    p=pct_rank(x,years=5)
    # Conditioning states only, not directional signals. Quantile bands are relative, not fixed VIX levels.
    if p<=.20:s='CALM'
    elif p<=.75:s='NORMAL'
    elif p<=.95:s='STRESSED'
    else:s='DISLOCATED'
    return {'state':s,'percentile':p,'method':'5y empirical percentile; conditioning only'}

def current_state(fred):
    cpi=annualized_3m(fred.get('CPILFESL',[])); pce=annualized_3m(fred.get('PCEPILFE',[]))
    iv=[z for z in [cpi,pce] if np.isfinite(z)]
    return {
      'Growth':{'CFNAI':last(fred.get('CFNAI',[])),'Claims_13w_pct':pct_delta(fred.get('ICSA',[]),91),'Unemployment':last(fred.get('UNRATE',[]))},
      'Inflation':{'Core_3m_ann':float(np.mean(iv)) if iv else np.nan,'Breakeven_5Y':last(fred.get('T5YIE',[]))},
      'Policy/Rates':{'2Y':last(fred.get('DGS2',[])),'10Y':last(fred.get('DGS10',[])),'Real10Y':last(fred.get('DFII10',[])),
                      'Real10Y_13w_delta':delta(fred.get('DFII10',[]),91),'10Y3M':last(fred.get('T10Y3M',[])),'TermPremium':last(fred.get('THREEFYTP10',[]))},
      'Credit/Funding':{'HYOAS':last(fred.get('BAMLH0A0HYM2',[])),'HYOAS_13w_delta':delta(fred.get('BAMLH0A0HYM2',[]),91),
                        'NFCI':last(fred.get('NFCI',[])),'SLOOS':last(fred.get('DRTSCILM',[]))},
      'FX':{'TradeWeightedUSD':last(fred.get('DTWEXBGS',[]))},
      'Volatility':volatility_state(fred.get('VIXCLS',[])),
      'percentiles':{'HY':pct_rank(fred.get('BAMLH0A0HYM2',[])),'Real10Y':pct_rank(fred.get('DFII10',[])),'TermPremium':pct_rank(fred.get('THREEFYTP10',[]))}
    }
