
from __future__ import annotations
import re, requests
import numpy as np
import pandas as pd

UA="MacroDecisionEngine research contact research@example.com"
HEAD={"User-Agent":UA}
TERMS={
    "constraint":["capacity constraint","supply constraint","shortage","lead time","capacity expansion","constrained"],
    "demand":["backlog","remaining performance obligations","rpo","bookings","orders","hyperscaler","data center","demand"],
    "monetization":["gross margin","operating margin","free cash flow","pricing","revenue growth"],
}

def discovery_candidates(prior, universe, limit=20):
    # Discovery prior only; never contributes to score.
    raw=[]
    if isinstance(prior,dict):
        raw += [str(x).upper() for x in prior.get("tickers",[]) if x]
    if not raw:
        raw += [x for x in universe if x not in ("SPY","IWM","QQQ","TLT","GLD","USO","UUP")][:limit]
    out=[]
    for x in raw:
        if x not in out: out.append(x)
    return out[:limit]

def _yf(t):
    try:
        import yfinance as yf
        tk=yf.Ticker(t)
        info=tk.info or {}
        h=tk.history(period="5y",auto_adjust=True)
        if h is None or h.empty:return {"ok":False,"reason":"no price history"}
        c=pd.to_numeric(h["Close"],errors="coerce").dropna()
        cur=float(c.iloc[-1]); peak=float(c.max())
        return {
            "ok":True,"current_price":cur,"drawdown_from_peak":cur/peak-1 if peak else np.nan,
            "revenue_growth":info.get("revenueGrowth"),"earnings_growth":info.get("earningsGrowth"),
            "gross_margin":info.get("grossMargins"),"operating_margin":info.get("operatingMargins"),
            "free_cashflow":info.get("freeCashflow"),"debt_to_equity":info.get("debtToEquity"),
            "target_upside":((info.get("targetMeanPrice")/cur)-1) if info.get("targetMeanPrice") and cur else np.nan,
            "history":c
        }
    except Exception as e:return {"ok":False,"reason":str(e)[:160]}

def _own_history(c):
    out={}
    s=pd.Series(c).dropna().sort_index()
    if len(s)<300:return out
    for h,days in [(1,21),(3,63),(6,126),(12,252)]:
        f=s.shift(-days)/s-1
        x=f.dropna()
        if len(x)<100:continue
        out[h]={"available":True,"p25":float((x>.25).mean()),"p50":float((x>.50).mean()),
                "p100":float((x>1).mean()),"pneg20":float((x<-.20).mean()),
                "median":float(x.median()),"p10":float(x.quantile(.10)),"p90":float(x.quantile(.90))}
    return out

def _sec_ticker_cik(ticker):
    try:
        r=requests.get("https://www.sec.gov/files/company_tickers.json",headers=HEAD,timeout=20); r.raise_for_status()
        d=r.json()
        for _,row in d.items():
            if str(row.get("ticker","")).upper()==ticker.upper():
                return str(row["cik_str"]).zfill(10)
    except Exception: pass
    return None

def _sec_filing_evidence(ticker):
    cik=_sec_ticker_cik(ticker)
    if not cik:return {"ok":False,"reason":"CIK unavailable"}
    try:
        sub=requests.get(f"https://data.sec.gov/submissions/CIK{cik}.json",headers=HEAD,timeout=20); sub.raise_for_status()
        j=sub.json(); recent=j.get("filings",{}).get("recent",{})
        forms=recent.get("form",[]); acc=recent.get("accessionNumber",[]); docs=recent.get("primaryDocument",[]); filed=recent.get("filingDate",[])
        pick=None
        for i,f in enumerate(forms):
            if f in ("10-Q","10-K"):
                pick=(i,f); break
        if not pick:return {"ok":False,"reason":"No recent 10-Q/10-K"}
        i,form=pick
        accession=acc[i].replace("-",""); doc=docs[i]
        url=f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{doc}"
        tx=requests.get(url,headers=HEAD,timeout=20); tx.raise_for_status()
        text=re.sub(r"\s+"," ",re.sub(r"<[^>]+>"," ",tx.text)).lower()
        snippets=[]
        hits={k:0 for k in TERMS}
        for group,terms in TERMS.items():
            for term in terms:
                pos=text.find(term)
                if pos>=0:
                    hits[group]+=1
                    snippets.append({"group":group,"term":term,"snippet":text[max(0,pos-170):pos+300][:470]})
        ok=hits["demand"]>0 and (hits["constraint"]>0 or hits["monetization"]>0)
        return {"ok":ok,"form":form,"filed":filed[i],"url":url,"hits":hits,"snippets":snippets[:8],
                "reason":"" if ok else "Filing lacks a complete constraint→capture/monetization chain"}
    except Exception as e:return {"ok":False,"reason":str(e)[:180]}

def _sec_facts(ticker):
    cik=_sec_ticker_cik(ticker)
    if not cik:return {"ok":False,"reason":"CIK unavailable"}
    try:
        r=requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",headers=HEAD,timeout=25); r.raise_for_status()
        j=r.json(); us=j.get("facts",{}).get("us-gaap",{})
        def units(tag):
            z=us.get(tag,{}).get("units",{}).get("USD",[])
            # Prefer actual quarter frames and filed-date lineage.
            rows=[]
            for x in z:
                if x.get("form") not in ("10-Q","10-K") or not x.get("filed"):continue
                frame=str(x.get("frame",""))
                if x.get("start") and x.get("end"):
                    try:
                        dur=(pd.Timestamp(x["end"])-pd.Timestamp(x["start"])).days
                    except Exception: dur=None
                else: dur=None
                quarter_like = ("Q" in frame and "YTD" not in frame) or (dur is not None and 70<=dur<=110)
                if quarter_like: rows.append(x)
            rows=sorted(rows,key=lambda x:(x.get("filed",""),x.get("end","")))
            return rows
        def yoy(tag):
            z=units(tag)
            if len(z)<5:return (np.nan,len(z),None)
            d=pd.DataFrame(z)
            d["filed"]=pd.to_datetime(d["filed"]); d["end"]=pd.to_datetime(d["end"]); d["val"]=pd.to_numeric(d["val"],errors="coerce")
            d=d.dropna(subset=["val","end"]).sort_values("end").drop_duplicates("end",keep="last")
            if len(d)<5:return (np.nan,len(d),d["filed"].max().date().isoformat() if len(d) else None)
            latest=d.iloc[-1]
            prev=d.iloc[:-1].iloc[(d.iloc[:-1]["end"]-(latest["end"]-pd.DateOffset(years=1))).abs().argmin()]
            return (float(latest["val"]/prev["val"]-1) if prev["val"] else np.nan,len(d),latest["filed"].date().isoformat())
        rev,n,fd=yoy("Revenues")
        if not np.isfinite(rev): rev,n,fd=yoy("RevenueFromContractWithCustomerExcludingAssessedTax")
        gp,_,_=yoy("GrossProfit"); op,_,_=yoy("OperatingIncomeLoss"); ni,_,_=yoy("NetIncomeLoss")
        return {"ok":bool(n>=4),"latest_filed":fd,"revenue_yoy":rev,"gross_profit_yoy":gp,
                "operating_income_yoy":op,"net_income_yoy":ni,"gross_margin":np.nan,"operating_margin":np.nan,
                "gross_margin_yoy_delta":np.nan,"operating_margin_yoy_delta":np.nan,
                "fcf_diagnostic":"DATA_GATED","revenue_points":n,
                "note":"SEC Company Facts uses filed-date lineage and quarter-like contexts; analyst revisions remain DATA-GATED."}
    except Exception as e:return {"ok":False,"reason":str(e)[:180]}

def rank_candidates(tickers,use_sec=True,max_results=8):
    rows=[]; details={}
    for t in tickers:
        cur=_yf(t)
        sec=_sec_filing_evidence(t) if use_sec else {"ok":False,"reason":"SEC check disabled"}
        facts=_sec_facts(t) if use_sec else {"ok":False,"reason":"SEC facts disabled"}

        # No analyst-target vote. Verification is evidence-based, not score-chasing.
        capture=0
        if cur.get("ok"):
            for k in ["revenue_growth","earnings_growth"]:
                v=cur.get(k)
                if v is not None and np.isfinite(v) and v>0: capture+=1
        if sec.get("ok"): capture+=2
        if facts.get("ok") and np.isfinite(facts.get("revenue_yoy",np.nan)) and facts["revenue_yoy"]>0: capture+=2

        verified=bool(sec.get("ok") and facts.get("ok") and capture>=4)
        status="BOTTLENECK_VERIFIED" if verified else "WATCH_DATA_GATED"
        score=min(100, 35 + 12*capture) if verified else min(69,20+8*capture)

        reason = (
            "Verified current filing evidence plus SEC filed-date fundamental capture. "
            "This verifies a bottleneck/capture chain, not a LONG recommendation."
            if verified else
            "Insufficient filing→fundamental evidence for bottleneck verification; keep as WATCH."
        )
        kills=[
            "Backlog/orders/RPO stop converting into revenue",
            "Revenue growth and margin/FCF capture deteriorate",
            "Capacity expands faster than underlying demand / bottleneck resolves",
            "Credit or funding stress invalidates the expected transmission",
            "Price reprices faster than defensible fundamental expectations",
        ]
        reload=False
        if cur.get("ok") and np.isfinite(cur.get("drawdown_from_peak",np.nan)):
            reload=bool(cur["drawdown_from_peak"]<=-.15 and facts.get("ok") and np.isfinite(facts.get("revenue_yoy",np.nan)) and facts["revenue_yoy"]>0)

        rows.append({"ticker":t,"status":status,"research_score":score,
                     "current_price":cur.get("current_price"),"drawdown_from_peak":cur.get("drawdown_from_peak"),
                     "revenue_growth":cur.get("revenue_growth"),"sec_verified":sec.get("ok"),
                     "sec_facts_verified":facts.get("ok"),"reload_candidate":reload})
        details[t]={"status":status,"reason":reason,"current":cur,"sec":sec,"sec_facts":facts,
                    "reload_candidate":reload,"kill_switches":kills,
                    "forward_own_history":_own_history(cur.get("history",[])) if cur.get("ok") else {}}
    df=pd.DataFrame(rows)
    if len(df): df=df.sort_values(["status","research_score"],ascending=[True,False]).head(max_results)
    return df,details
