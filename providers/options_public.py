
from __future__ import annotations
import math, numpy as np, pandas as pd
from datetime import datetime, timezone

def _nearest(df,target):
    if df is None or df.empty:return None
    x=df.copy();x['dist']=(pd.to_numeric(x['strike'],errors='coerce')-target).abs();x=x.dropna(subset=['dist','impliedVolatility'])
    return x.sort_values('dist').iloc[0] if len(x) else None

def snapshot(symbol,max_dte=90):
    try:import yfinance as yf
    except Exception as e:return {'ok':False,'reason':f'yfinance unavailable: {e}'}
    try:
        q=yf.Ticker(symbol); hist=q.history(period='5d',auto_adjust=True)
        if hist is None or hist.empty:return {'ok':False,'reason':'price unavailable'}
        spot=float(pd.to_numeric(hist['Close'],errors='coerce').dropna().iloc[-1]); exps=list(q.options or [])
        if not exps:return {'ok':False,'reason':'no listed options returned'}
        now=pd.Timestamp.utcnow().tz_localize(None)
        choices=[]
        for e in exps:
            dt=pd.Timestamp(e);dte=max(0,(dt-now.normalize()).days)
            if 1<=dte<=max_dte:choices.append((dte,e))
        if not choices:choices=[(max(1,(pd.Timestamp(exps[0])-now.normalize()).days),exps[0])]
        dte,exp=sorted(choices)[0]; chain=q.option_chain(exp); calls=chain.calls.copy();puts=chain.puts.copy()
        atm_c=_nearest(calls,spot);atm_p=_nearest(puts,spot)
        ivs=[]
        for row in [atm_c,atm_p]:
            if row is not None:
                try:
                    iv=float(row['impliedVolatility']);
                    if np.isfinite(iv) and iv>0:ivs.append(iv)
                except:pass
        atm_iv=float(np.mean(ivs)) if ivs else None
        em=spot*atm_iv*math.sqrt(dte/365) if atm_iv else None
        coi=float(pd.to_numeric(calls.get('openInterest'),errors='coerce').fillna(0).sum());poi=float(pd.to_numeric(puts.get('openInterest'),errors='coerce').fillna(0).sum())
        # symmetric 5% strike skew proxy; context only
        p95=_nearest(puts,spot*.95);c105=_nearest(calls,spot*1.05)
        skew=None
        try:skew=float(p95['impliedVolatility'])-float(c105['impliedVolatility'])
        except:pass
        # OI concentration: top 5 strikes share of total OI
        oi=pd.concat([calls[['strike','openInterest']],puts[['strike','openInterest']]],ignore_index=True);oi['openInterest']=pd.to_numeric(oi['openInterest'],errors='coerce').fillna(0);by=oi.groupby('strike')['openInterest'].sum().sort_values(ascending=False);tot=float(by.sum());conc=float(by.head(5).sum()/tot) if tot else None
        return {'ok':True,'symbol':symbol,'retrieved_at':datetime.now(timezone.utc).isoformat(),'spot':spot,'expiry':exp,'dte':dte,'atm_iv':atm_iv,'one_sigma_move':em,'put_call_oi':poi/coi if coi else None,'five_pct_skew_proxy':skew,'top5_oi_concentration':conc,'status':'CURRENT_CONTEXT_NOT_HISTORICALLY_CALIBRATED','note':'No dealer-sign/GEX directional claim is made.'}
    except Exception as e:return {'ok':False,'reason':str(e)[:200]}
