
from __future__ import annotations
import numpy as np,pandas as pd
CHAINS={'US Equities':'Policy → real yields/credit → discount rate + earnings → company cash flows','IHSG':'Global/local policy → IDR/funding/foreign flows + domestic growth → company cash flows','Commodities':'Growth/supply policy → physical demand/inventory/capacity → curve/processing economics','FX':'Relative policy/real yields → funding/external balance/intervention → exchange rate','Crypto':'Global funding + crypto-native liquidity → spot demand/leverage/supply → token economics'}
def mechanism_table():return pd.DataFrame([{'market':m,'causal_chain':c,'production_status':'Requires asset-specific evidence; no fixed sign mapping'} for m,c in CHAINS.items()])

def empirical_sensitivities(fred,prices):
    fac={}
    for sid in ['DFII10','BAMLH0A0HYM2','DTWEXBGS','T5YIE','THREEFYTP10']:
        s=fred.get(sid)
        if s is not None:fac[sid]=pd.Series(s).dropna().sort_index().resample('ME').last().diff()
    F=pd.concat(fac,axis=1).dropna() if fac else pd.DataFrame();out=[]
    if F.empty:return pd.DataFrame()
    for tk,p in prices.items():
        r=pd.Series(p).dropna().sort_index().resample('ME').last().pct_change().shift(-1).rename('ret');d=F.join(r).dropna()
        if len(d)<48:continue
        for f in F.columns:
            windows=[]
            for n in [60,120,len(d)]:
                z=d.tail(min(n,len(d)));vx=np.var(z[f]);beta=np.cov(z[f],z.ret)[0,1]/vx if vx>0 else np.nan;windows.append(beta)
            signs=[np.sign(x) for x in windows if np.isfinite(x) and x!=0];stable=bool(signs and all(s==signs[0] for s in signs))
            out.append({'instrument':tk,'macro_factor':f,'n':len(d),'beta_5y':windows[0],'beta_10y':windows[1],'beta_full':windows[2],'sign_stable_across_windows':stable,'status':'ASSOCIATION_ONLY_NOT_CAUSAL'})
    return pd.DataFrame(out)

def bottleneck_matrix(state):
    r=state.get('Policy/Rates',{});c=state.get('Credit/Funding',{});x=state.get('FX',{});k=state.get('Crypto Native',{})
    rows=[]
    def add(m,channel,evidence,status,nextobs):rows.append({'market':m,'candidate_binding_channel':channel,'evidence':evidence,'status':status,'next_discriminating_observation':nextobs})
    rp=r.get('Real10Y_percentile',np.nan);hy=c.get('HYOAS_percentile',np.nan);usd=x.get('USD_percentile',np.nan)
    add('US Equities','Long-rate / discount-rate pressure',f'Real10Y percentile={rp:.1%}' if np.isfinite(rp) else 'NO DATA','INVESTIGATE' if np.isfinite(rp) and rp>.75 else 'NO STRONG EVIDENCE','Earnings revisions + term premium + credit response')
    add('IHSG','Global USD/funding + local foreign flow',f'USD percentile={usd:.1%}' if np.isfinite(usd) else 'NO DATA','DATA_GATED' if not np.isfinite(usd) else 'PARTIAL','IDX Type-F flow + BI/Fed relative path + local earnings')
    add('Commodities','Physical inventory/capacity','Physical histories not loaded','DATA_GATED','EIA/IEA/OPEC/inventory/curve data')
    sc=k.get('Stablecoin_7d_pct',np.nan);add('Crypto','Native liquidity / leverage',f'Stablecoin 7d={sc:.2%}' if np.isfinite(sc) else 'NO DATA','PARTIAL' if np.isfinite(sc) else 'DATA_GATED','Spot/ETF flow + OI/funding + unlocks')
    add('FX','Relative policy + external funding','Cross-currency basis / relative curves incomplete','DATA_GATED','Relative OIS/real yields + basis + intervention')
    return pd.DataFrame(rows)
