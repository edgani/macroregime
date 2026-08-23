
from __future__ import annotations
import numpy as np,pandas as pd

def _s(x):
    try:return pd.Series(x).dropna().sort_index()
    except:return pd.Series(dtype=float)
def last(x):
    z=_s(x);return float(z.iloc[-1]) if len(z) else np.nan
def delta(x,days):
    z=_s(x)
    if not len(z):return np.nan
    old=z.loc[:z.index[-1]-pd.Timedelta(days=days)];return float(z.iloc[-1]-old.iloc[-1]) if len(old) else np.nan
def pct_delta(x,days):
    z=_s(x)
    if not len(z):return np.nan
    old=z.loc[:z.index[-1]-pd.Timedelta(days=days)];return float(z.iloc[-1]/old.iloc[-1]-1) if len(old) and old.iloc[-1]!=0 else np.nan
def pct_rank(x,years=10):
    z=_s(x)
    if len(z)<20:return np.nan
    z=z.loc[z.index>=z.index[-1]-pd.DateOffset(years=years)];return float((z<=z.iloc[-1]).mean()) if len(z)>=20 else np.nan
def annualized_3m(x):
    z=_s(x)
    if not len(z):return np.nan
    old=z.loc[:z.index[-1]-pd.DateOffset(months=3)];return float((z.iloc[-1]/old.iloc[-1])**4-1) if len(old) and old.iloc[-1]>0 else np.nan

def relative_label(p,high='HIGH',low='LOW'):
    if not np.isfinite(p):return 'NO DATA'
    if p>=.9:return 'EXTREME '+high
    if p>=.75:return high
    if p<=.1:return 'EXTREME '+low
    if p<=.25:return low
    return 'MID-RANGE'

def volatility_state(fred,prices):
    v=fred.get('VIXCLS',[]);p=pct_rank(v,5);state=relative_label(p,'VOL','CALM')
    prox=(prices or {}).get('_proxies',{})
    v9=last(prox.get('^VIX9D',[]));v3=last(prox.get('^VIX3M',[]));vvix=last(prox.get('^VVIX',[]));move=last(prox.get('^MOVE',[]))
    slope=(v9/v3-1) if np.isfinite(v9) and np.isfinite(v3) and v3 else np.nan
    return {'VIX':last(v),'VIX_5y_percentile':p,'relative_state':state,'VIX9D':v9,'VIX3M':v3,'9D_3M_slope':slope,'VVIX':vvix,'MOVE':move,'use':'CONDITIONING / RISK ONLY'}

def current_state(bundle):
    fred=bundle.get('fred',{});prices=bundle.get('prices',{});treas=bundle.get('treasury',{});crypto=bundle.get('crypto_native',{})
    cpi=annualized_3m(fred.get('CPILFESL',[]));pce=annualized_3m(fred.get('PCEPILFE',[]));ivs=[x for x in [cpi,pce] if np.isfinite(x)]
    sofr=last(fred.get('SOFR',[]));iorb=last(fred.get('IORB',[]));effr=last(fred.get('EFFR',[]))
    tga=treas.get('tga',{}) if isinstance(treas,dict) else {};rrp=treas.get('rrp',{}) if isinstance(treas,dict) else {}
    stables=crypto.get('stablecoins',{}) if isinstance(crypto,dict) else {};dex=crypto.get('dex',{}) if isinstance(crypto,dict) else {};chains=crypto.get('chains',{}) if isinstance(crypto,dict) else {}
    return {
    'Growth':{'CFNAI':last(fred.get('CFNAI',[])),'CFNAI_percentile':pct_rank(fred.get('CFNAI',[])),'Claims_13w_pct':pct_delta(fred.get('ICSA',[]),91),'Unemployment':last(fred.get('UNRATE',[])),'BankCredit_13w_pct':pct_delta(fred.get('TOTLL',[]),91),'C&I_Loans_13w_pct':pct_delta(fred.get('BUSLOANS',[]),91)},
    'Inflation':{'Core_3m_ann':float(np.mean(ivs)) if ivs else np.nan,'Breakeven_5Y':last(fred.get('T5YIE',[])),'Breakeven_percentile':pct_rank(fred.get('T5YIE',[]))},
    'Policy/Rates':{'2Y':last(fred.get('DGS2',[])),'5Y':last(fred.get('DGS5',[])),'10Y':last(fred.get('DGS10',[])),'30Y':last(fred.get('DGS30',[])),'Real10Y':last(fred.get('DFII10',[])),'Real10Y_13w_delta':delta(fred.get('DFII10',[]),91),'Real10Y_percentile':pct_rank(fred.get('DFII10',[])),'10Y3M':last(fred.get('T10Y3M',[])),'10Y3M_13w_delta':delta(fred.get('T10Y3M',[]),91),'TermPremium':last(fred.get('THREEFYTP10',[])),'TermPremium_13w_delta':delta(fred.get('THREEFYTP10',[]),91)},
    'Credit/Funding':{'HYOAS':last(fred.get('BAMLH0A0HYM2',[])),'HYOAS_percentile':pct_rank(fred.get('BAMLH0A0HYM2',[])),'HYOAS_13w_delta':delta(fred.get('BAMLH0A0HYM2',[]),91),'IGOAS':last(fred.get('BAMLC0A0CM',[])),'CCCOAS':last(fred.get('BAMLH0A3HYC',[])),'NFCI':last(fred.get('NFCI',[])),'ANFCI':last(fred.get('ANFCI',[])),'SLOOS':last(fred.get('DRTSCILM',[])),'SOFR':sofr,'IORB':iorb,'SOFR_minus_IORB':sofr-iorb if np.isfinite(sofr) and np.isfinite(iorb) else np.nan,'EFFR_minus_IORB':effr-iorb if np.isfinite(effr) and np.isfinite(iorb) else np.nan},
    'Liquidity/Plumbing':{'ReserveBalances_13w_pct':pct_delta(fred.get('WRESBAL',[]),91),'FedAssets_13w_pct':pct_delta(fred.get('WALCL',[]),91),'FRED_TGA_13w_pct':pct_delta(fred.get('WTREGEN',[]),91),'FRED_RRP_13w_pct':pct_delta(fred.get('RRPONTSYD',[]),91),'Official_TGA_mm':tga.get('latest_mm') if tga.get('ok') else np.nan,'Official_RRP_bn':rrp.get('amount_bn') if rrp.get('ok') else np.nan,'note':'Components only; no universal net-liquidity trade mapping.'},
    'FX':{'TradeWeightedUSD':last(fred.get('DTWEXBGS',[])),'USD_13w_pct':pct_delta(fred.get('DTWEXBGS',[]),91),'USD_percentile':pct_rank(fred.get('DTWEXBGS',[]))},
    'Volatility':volatility_state(fred,prices),
    'Crypto Native':{'StablecoinMCap':stables.get('total_mcap') if stables.get('ok') else np.nan,'Stablecoin_7d_pct':stables.get('change_7d') if stables.get('ok') else np.nan,'Stablecoin_30d_pct':stables.get('change_30d') if stables.get('ok') else np.nan,'DEX_24h':dex.get('total24h') if dex.get('ok') else np.nan,'DEX_7d_change':dex.get('change_7d') if dex.get('ok') else np.nan,'ChainTVL':chains.get('total_tvl') if chains.get('ok') else np.nan},
    }
