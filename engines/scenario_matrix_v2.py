
from __future__ import annotations
from typing import Dict
import numpy as np
import pandas as pd

SCENARIOS = [
("Macro","growth_scare_disinflation","4Q","Growth + credit + financial conditions","PROMISING"),
("Macro","overheating_reflation","4Q","Growth + inflation expectations","PROMISING_SIMPLE"),
("Macro","soft_landing","4Q","Growth + inflation distribution","RESEARCH"),
("Macro","stagflation","4Q","Growth + inflation distribution","SAMPLE_LIMITED"),
("Inflation","supply_chain_inflation","1M-1Q","Supply pressure + inflation pipeline","DATA_GATED"),
("Rates","bull_steepener","1-6M","Curve + front-end repricing","TEST"),
("Rates","bear_steepener_term_premium","1-6M","Long yield + term premium","TEST"),
("Rates","long_rate_shock","1-12M","Real yield + term premium","PROMISING_MODIFIER"),
("Credit","credit_deterioration","1-12M","HY velocity + EBP","TEST"),
("Crash","vol_without_credit_confirmation","Days-1M","Vol + credit","TEST"),
("Crash","credit_funding_stress_transition","Days-6M","Credit + funding + vol","TEST"),
("Crash","forced_liquidation","Days-1M","Correlation + funding + realized stress","DATA_GATED"),
("Crash","post_liquidation_normalization","Days-3M","Credit/funding normalization","DATA_GATED"),
("Index","iwm_ath_state","1-12M","ATH + rates + credit + breadth","RESEARCH"),
("Index","spy_ath_state","1-12M","ATH + rates + credit + breadth","RESEARCH"),
("Index","first_ath_after_long_gap","1-12M","Episode-clustered ATH state","PROMISING"),
("Index","repeated_ath_cluster","1-6M","Repeated ATH state","WEAK_STANDALONE"),
("Index","ath_plus_long_rate_shock","1-12M","ATH + long-rate pressure","PROMISING_NEGATIVE_MODIFIER"),
("Index","ath_plus_credit_deterioration","1-12M","ATH + credit velocity","TEST"),
("Ticker","price_lag_positive_revisions","1-6M","PIT revisions + pricing","DATA_GATED"),
("Ticker","backlog_profitable_monetization","1-12M","Orders + revenue + margin + FCF","CORE_RESEARCH"),
("Ticker","fake_backlog_no_monetization","1-12M","Backlog + cash conversion + margin","NEGATIVE_CONTROL"),
("Ticker","monster_winner_reload","1-6M","Correction + intact bottleneck + expectations gap","DATA_GATED"),
("Ticker","bottleneck_resolution","1-12M","Capacity + inventory + pricing","DATA_GATED"),
("Ticker","second_order_capex_bottleneck","3-18M","Capex-chain migration","CORE_RESEARCH"),
("Commodity","low_inventory_backwardation_demand","1-6M","Physical inventory + curve + demand","DATA_GATED"),
("Commodity","destock_to_restock","1-12M","Inventory + orders + utilization","DATA_GATED"),
("Commodity","capacity_catches_demand","1-12M","Capacity + inventory + lead time","DATA_GATED"),
("FX","rate_move_rejected_by_fx","Days-3M","Rate differential + FX reaction","DATA_GATED"),
("FX","dollar_funding_squeeze","Days-6M","USD + basis + credit","DATA_GATED"),
("Crypto","spot_stablecoin_led_rally","Days-3M","Spot + stablecoin + low leverage","DATA_GATED"),
("Crypto","leverage_only_rally","Days-1M","OI/funding + weak real demand","DATA_GATED"),
("Fiscal","fiscal_impulse_real_yield_shock","1-12M","Fiscal + term premium + real yield","DATA_GATED"),
("Market","credit_improving_near_ath","1-12M","Credit improvement + price state","TEST"),
("Market","high_vol_without_credit_deterioration","Days-3M","High vol + benign credit","PROMISING_BENIGN"),
("Market","high_vol_plus_credit_deterioration","Days-6M","High vol + worsening credit","PROMISING_STRESS"),
]

def _last(s):
    try:
        s=pd.Series(s).dropna()
        return float(s.iloc[-1]) if len(s) else np.nan
    except Exception: return np.nan

def _asof_change(s, days):
    try:
        s=pd.Series(s).dropna().sort_index()
        if len(s)<2:return np.nan
        target=s.index[-1]-pd.Timedelta(days=days)
        old=s.loc[:target]
        return float(s.iloc[-1]-old.iloc[-1]) if len(old) else np.nan
    except Exception:return np.nan

def _pct_change(s, days):
    try:
        s=pd.Series(s).dropna().sort_index()
        target=s.index[-1]-pd.Timedelta(days=days)
        old=s.loc[:target]
        if not len(old) or float(old.iloc[-1])==0:return np.nan
        return float(s.iloc[-1]/old.iloc[-1]-1)
    except Exception:return np.nan

def _percentile(s):
    try:
        s=pd.Series(s).dropna()
        if len(s)<20:return np.nan
        x=s.iloc[-min(len(s),3780):]
        return float((x<=x.iloc[-1]).mean())
    except Exception:return np.nan

def _infl_3m_ann(index_series):
    try:
        s=pd.Series(index_series).dropna().sort_index()
        if len(s)<5:return np.nan
        end=s.index[-1]; old=s.loc[:end-pd.DateOffset(months=3)]
        if not len(old) or old.iloc[-1]<=0:return np.nan
        return float((s.iloc[-1]/old.iloc[-1])**4-1)
    except Exception:return np.nan

def ath_state(series):
    s=pd.Series(series).dropna().sort_index()
    if len(s)<20:return {"available":False}
    peak=float(s.cummax().iloc[-1]); cur=float(s.iloc[-1])
    dd=cur/peak-1 if peak else np.nan
    recent=s.tail(min(63,len(s)))
    hits=int((recent >= recent.cummax()*0.995).sum())
    return {"available":True,"drawdown":dd,"near_ath":bool(dd>=-0.02),"recent_ath_hits":hits}

def fed_research_series(fed_research):
    out={}
    for k,v in (fed_research or {}).items():
        d=v.get("data")
        if not isinstance(d,pd.DataFrame) or d.empty: continue
        # best-effort numeric series extraction
        date_col=next((c for c in d.columns if "date" in c.lower()),None)
        nums=[c for c in d.columns if pd.api.types.is_numeric_dtype(d[c])]
        if date_col and nums:
            try:
                idx=pd.to_datetime(d[date_col],errors="coerce")
                for c in nums:
                    out[f"{k.upper()}_{c.upper()}"]=pd.Series(pd.to_numeric(d[c],errors="coerce").values,index=idx).dropna()
            except Exception: pass
    return out

def current_state(fred, fed_research, market):
    f=fred or {}
    claims=_pct_change(f.get("ICSA",[]),91)
    real10=_last(f.get("DFII10",[])); realchg=_asof_change(f.get("DFII10",[]),91)
    curve=_last(f.get("T10Y3M",[])); curvechg=_asof_change(f.get("T10Y3M",[]),91)
    tp=_last(f.get("THREEFYTP10",[])); tpchg=_asof_change(f.get("THREEFYTP10",[]),91)
    hy=_last(f.get("BAMLH0A0HYM2",[])); hychg=_asof_change(f.get("BAMLH0A0HYM2",[]),91)
    core_vals=[_infl_3m_ann(f.get("CPILFESL",[])),_infl_3m_ann(f.get("PCEPILFE",[]))]
    core=np.nanmean([x for x in core_vals if np.isfinite(x)]) if any(np.isfinite(x) for x in core_vals) else np.nan

    flat={}
    for _,d in (market.get("prices",{}) or {}).items():
        flat.update(d or {})
    idx={}
    for tk in ["IWM","SPY"]:
        idx[tk]=ath_state(flat.get(tk,[]))

    series_to_corr=[]
    for tk in ["SPY","TLT","GLD","USO","BTC-USD"]:
        s=pd.Series(flat.get(tk,[])).dropna()
        if len(s)>40: series_to_corr.append(s.pct_change().rename(tk))
    corr={"available":False}
    if len(series_to_corr)>=3:
        z=pd.concat(series_to_corr,axis=1).dropna().tail(20)
        if len(z)>=10:
            c=z.corr().values
            vals=np.abs(c[np.triu_indices_from(c,k=1)])
            corr={"available":True,"mean_abs_corr":float(np.nanmean(vals))}

    return {
        "growth":{"cfnai":_last(f.get("CFNAI",[])),"claims_13w_pct":claims},
        "inflation":{"core_3m_ann":core},
        "rates":{"real10":real10,"real10_13w":realchg,"curve":curve,"curve_13w":curvechg,
                 "term_premium":tp,"term_premium_13w":tpchg},
        "credit":{"hy_oas":hy,"hy_13w":hychg,"nfci":_last(f.get("NFCI",[])),
                  "ebp":np.nan,"ebp_13w":np.nan,"fci_g":np.nan},
        "supply":{"scb":np.nan,"scb_6m":np.nan},
        "research":{
            "hy_percentile":_percentile(f.get("BAMLH0A0HYM2",[])),
            "ebp_percentile":np.nan,"fcig_percentile":np.nan,
            "real10_percentile":_percentile(f.get("DFII10",[])),
            "term_premium_percentile":_percentile(f.get("THREEFYTP10",[])),
        },
        "stress":{"cross_asset_corr":corr},
        "index":idx,
    }

def evaluate_scenarios(state):
    rows=[]
    r=state["rates"]; c=state["credit"]; g=state["growth"]; s=state["stress"]; idx=state["index"]
    for eng,name,hor,features,prior_status in SCENARIOS:
        status="DATA_GATED / NOT ACTIVE"
        evidence=[]
        conf="LOW"

        if name=="long_rate_shock":
            if np.isfinite(r.get("real10_13w",np.nan)) and r["real10_13w"]>0.40:
                status="ACTIVE"; evidence.append("10Y real yield +>40bp over ~13w"); conf="MEDIUM"
        elif name=="credit_deterioration":
            if np.isfinite(c.get("hy_13w",np.nan)) and c["hy_13w"]>0.75:
                status="WATCH_FRAGILITY"; evidence.append("HY OAS widening materially"); conf="MEDIUM"
        elif name in ("iwm_ath_state","spy_ath_state"):
            tk="IWM" if name.startswith("iwm") else "SPY"
            a=idx.get(tk,{})
            if a.get("available") and a.get("near_ath"):
                status="ACTIVE"; evidence.append(f"{tk} within 2% of loaded peak"); conf="LOW"
        elif name=="vol_without_credit_confirmation":
            # VIX not stored separately in current state; remain gated.
            pass
        elif name=="high_vol_without_credit_deterioration":
            pass
        elif name=="forced_liquidation":
            cc=s.get("cross_asset_corr",{})
            if cc.get("available") and cc.get("mean_abs_corr",0)>0.75:
                status="WATCH_FRAGILITY"; evidence.append("Cross-asset correlations elevated"); conf="LOW"
        elif name=="growth_scare_disinflation":
            if np.isfinite(g.get("claims_13w_pct",np.nan)) and g["claims_13w_pct"]>0.15:
                status="WATCH_FRAGILITY"; evidence.append("Claims deteriorating"); conf="LOW"

        rows.append({"engine":eng,"scenario":name,"horizon":hor,"status":status,
                     "evidence":"; ".join(evidence) if evidence else prior_status,
                     "confidence":conf})
    return pd.DataFrame(rows)

def library_frame():
    return pd.DataFrame(SCENARIOS,columns=["engine","scenario","horizon","minimal_sufficient_set","research_status"])
