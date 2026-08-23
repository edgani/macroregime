
from __future__ import annotations
import pandas as pd, numpy as np
CHAINS={
'US Equities':'Policy → real yields/credit → discount rate + earnings → equity cash flows',
'IHSG':'Global/local policy → IDR/funding/foreign flows + domestic growth → company cash flows',
'Commodities':'Growth/supply policy → physical demand/inventory/capacity → curve/processing economics',
'FX':'Relative policy/real yields → funding/external balance/intervention → exchange rate',
'Crypto':'Global funding + crypto-native liquidity → spot demand/leverage/supply → token economics',
}
def mechanism_table():
    return pd.DataFrame([{'market':m,'causal_chain':c,'production_status':'Requires asset-specific evidence; no fixed sign mapping'} for m,c in CHAINS.items()])

def empirical_sensitivities(fred,prices):
    # Price is outcome only. Associations are explicitly not causal proof and never become a trade by themselves.
    fac={}
    for sid in ['DFII10','BAMLH0A0HYM2','DTWEXBGS','T5YIE']:
        s=fred.get(sid)
        if s is not None:
            fac[sid]=pd.Series(s).dropna().sort_index().resample('ME').last().diff()
    F=pd.concat(fac,axis=1).dropna() if fac else pd.DataFrame()
    out=[]
    if F.empty:return pd.DataFrame()
    for tk,p in prices.items():
        r=pd.Series(p).dropna().sort_index().resample('ME').last().pct_change().shift(-1).rename('ret')
        d=F.join(r).dropna()
        if len(d)<36:continue
        for f in F.columns:
            x=d[f]; y=d['ret']; sx=x.std()
            beta=np.cov(x,y)[0,1]/np.var(x) if np.var(x)>0 else np.nan
            corr=x.corr(y)
            out.append({'instrument':tk,'macro_factor':f,'n':len(d),'next_month_beta':beta,'correlation':corr,'status':'ASSOCIATION_ONLY_NOT_CAUSAL'})
    return pd.DataFrame(out)
