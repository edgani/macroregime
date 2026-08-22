"""Macro + Bottleneck Decision Engine v2 — Streamlit entry point.

Run:
    streamlit run app.py

Design rules:
- strict real data only; no synthetic fallback
- no hard-coded regime->asset trades
- curated bottleneck JSON is discovery prior only
- scenarios are state interactions, not new independent votes
- projections are distributions with explicit data/validation status
- zero qualifying ticker candidates is a valid output
"""
from __future__ import annotations

import math
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st

from config.metric_registry_v2 import METRIC_FAMILIES
from data_layer_v2 import build_data_bundle, load_universes, _strict_yfinance_prices
from engines.scenario_matrix_v2 import current_state, evaluate_scenarios, library_frame, fed_research_series, ath_state
from engines.projection_engine_v2 import macro_analog_projection, spf_forecast_error_projection
from engines.bottleneck_engine_v2 import discovery_candidates, rank_candidates
from data.eia_physical import physical_snapshot

HERE=Path(__file__).resolve().parent

st.set_page_config(page_title="Macro + Bottleneck Engine v2", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.block-container{padding-top:1rem;padding-bottom:2rem;max-width:1600px}
div[data-testid="stMetric"]{border:1px solid rgba(128,128,128,.25);border-radius:10px;padding:10px 12px}
.small{font-size:.82rem;opacity:.76}.bad{color:#d9534f}.good{color:#3fa66b}.warn{color:#d39e00}
</style>
""",unsafe_allow_html=True)


def fmt(x, pct=False, d=2):
    try:
        if x is None or not np.isfinite(float(x)): return "N/A"
        return f"{float(x):.{d}%}" if pct else f"{float(x):.{d}f}"
    except Exception: return "N/A"


def source_badge(x):
    return "✅" if str(x).startswith("LIVE") else "🟡" if "BUNDLED" in str(x) else "❌"


def flatten_prices(market_bundle):
    out={}
    for _,d in (market_bundle.get("prices") or {}).items(): out.update(d or {})
    return out


def load_bundled_vix(market_bundle):
    """Use bundled real CBOE VIX history if Yahoo ^VIX is absent."""
    flat=flatten_prices(market_bundle)
    if "^VIX" in flat: return
    p=HERE/"research"/"vix.csv"
    try:
        d=pd.read_csv(p); d["DATE"]=pd.to_datetime(d["DATE"])
        s=d.set_index("DATE")["CLOSE"].astype(float).dropna()
        market_bundle.setdefault("prices",{}).setdefault("_bundled",{})["^VIX"]=s
    except Exception: pass


@st.cache_data(ttl=1800,show_spinner=False)
def get_bundle(markets, live_feeds, cap):
    return build_data_bundle(markets=list(markets),fetch_live_feeds=live_feeds,max_per_market=int(cap))


@st.cache_data(ttl=1800,show_spinner=False)
def get_single_price(ticker):
    p,o=_strict_yfinance_prices([ticker],days=5000)
    return p.get(ticker),o.get(ticker)


# ── Sidebar ───────────────────────────────────────────────────────────────
st.sidebar.title("Decision Engine v2")
markets=st.sidebar.multiselect("Load markets",["us","idx","crypto","commodity","fx"],default=["us","idx","crypto","commodity","fx"])
cap=st.sidebar.slider("Live tickers per market",5,80,35,5,help="Bulk live price context only; not the final cross-sectional proof universe.")
live_feeds=st.sidebar.toggle("Fetch specialized live feeds",value=False,help="CFTC/DeFiLlama/options/FINRA can be slower. Snapshot is used if present.")
if st.sidebar.button("↻ Refresh data"):
    st.cache_data.clear(); st.rerun()
st.sidebar.divider()
st.sidebar.caption("STRICT REAL ONLY · no synthetic fallback")
st.sidebar.caption("FRED_API_KEY in Streamlit Secrets is recommended. SEC_USER_AGENT is recommended for filing evidence.")

with st.spinner("Loading strict real/public data…"):
    bundle=get_bundle(tuple(markets),live_feeds,cap)
load_bundled_vix(bundle["market"])
fred=bundle.get("fred",{}).get("series",{})
state=current_state(fred,bundle.get("fed_research",{}),bundle.get("market",{}))
scenarios=evaluate_scenarios(state)

# ── Header ────────────────────────────────────────────────────────────────
st.title("Macro + Fundamental + Bottleneck Decision Engine")
st.caption("52-family research architecture · strict data lineage · scenario/state transitions · quality-first ticker selection")

fred_meta=bundle.get("fred",{}).get("meta",{})
market_sources=bundle.get("market",{}).get("sources",{})
loaded_markets=sum(int(v.get("loaded",0)) for v in market_sources.values()) if market_sources else 0
fed_live=sum(1 for x in bundle.get("fed_research",{}).values() if x.get("source")=="LIVE_OFFICIAL")

c1,c2,c3,c4,c5=st.columns(5)
c1.metric("FRED loaded",f"{fred_meta.get('loaded',0)}/{fred_meta.get('requested',0)}")
c2.metric("Market tickers live",loaded_markets)
c3.metric("Fed research datasets",f"{fed_live}/4 live")
c4.metric("Metric families",len(METRIC_FAMILIES))
c5.metric("Source policy","REAL ONLY")

if fred_meta.get("loaded",0)==0:
    st.error("FRED live data unavailable. The app will keep affected states as NO DATA; it will NOT synthesize a macro regime.")

T=st.tabs(["Command Center","Crash / Stress","Scenario Matrix","Forward Projection","Bottleneck Tickers","Cross-Market","Proof Center","Data Lineage","Asset-Specific Data"])

# ── Command Center ───────────────────────────────────────────────────────
with T[0]:
    st.subheader("Current observable state")
    g=state["growth"]; inf=state["inflation"]; r=state["rates"]; c=state["credit"]; sp=state["supply"]
    a,b,cx,d,e,f=st.columns(6)
    a.metric("CFNAI",fmt(g.get("cfnai")),help="0 ≈ historical-trend growth; this is state context, not a trade signal.")
    b.metric("Claims 13w",fmt(g.get("claims_13w_pct"),pct=True))
    cx.metric("Core inflation 3m ann.",fmt(inf.get("core_3m_ann"),pct=True))
    d.metric("10Y real yield",fmt(r.get("real10"),False),delta=fmt(r.get("real10_13w"),False)+" 13w")
    e.metric("HY OAS",fmt(c.get("hy_oas")),delta=fmt(c.get("hy_13w"))+" 13w")
    f.metric("EBP",fmt(c.get("ebp")),delta=fmt(c.get("ebp_13w"))+" 13w")

    st.markdown("### What is binding now?")
    active=scenarios[scenarios.status.astype(str).str.contains("ACTIVE|WATCH_FRAGILITY",regex=True,na=False)]
    if len(active): st.dataframe(active,use_container_width=True,hide_index=True)
    else: st.info("No supported scenario is currently ACTIVE under the loaded subset. This can mean benign conditions or missing inputs.")

    st.markdown("### Rates / credit / supply transmission")
    rows=[
        ["Yield curve 10Y-3M",r.get("curve"),r.get("curve_13w"),"Cycle state; never immediate short by itself"],
        ["10Y term premium",r.get("term_premium"),r.get("term_premium_13w"),"Long-end/fiscal-risk pressure"],
        ["NFCI",c.get("nfci"),np.nan,"Broad financial conditions"],
        ["FCI-G",c.get("fci_g"),np.nan,"Growth impact of financial conditions"],
        ["SCB sentiment",sp.get("scb"),sp.get("scb_6m"),"Near-term supply/inflation transition only"],
    ]
    df=pd.DataFrame(rows,columns=["Metric","Latest","Change","Placement"])
    st.dataframe(df,use_container_width=True,hide_index=True)

    st.warning("No hard-coded mapping exists here: e.g. high inflation does NOT automatically imply long gold/oil, and an inverted curve does NOT automatically imply short equities.")

    st.markdown("### Treasury / funding plumbing — raw observations")
    pl=bundle.get("treasury_plumbing",{}) or {}
    tga,rrp,sofr=pl.get("tga",{}),pl.get("rrp",{}),pl.get("sofr",{})
    pc1,pc2,pc3=st.columns(3)
    pc1.metric("TGA opening balance",fmt(tga.get("latest")),help="Raw US Treasury observation; no universal risk-asset mapping.")
    pc2.metric("ON RRP accepted",fmt(rrp.get("amount")),help="Raw NY Fed observation; no FedAssets-TGA-RRP trade rule.")
    pc3.metric("SOFR",fmt(sofr.get("sofr")),help="Raw NY Fed secured overnight rate.")
    if not any([tga.get("ok"),rrp.get("ok"),sofr.get("ok")]): st.caption("Treasury/NY Fed raw connector unavailable; state remains missing.")

# ── Crash / Stress ───────────────────────────────────────────────────────
with T[1]:
    st.subheader("Crash architecture: Fragility → Stress → Liquidation → Normalization")
    st.write("The engine intentionally avoids one additive magic CrashScore because the earlier multi-feature crash model was unstable OOS.")
    rp=state["research"]; stress=state["stress"]
    q1,q2,q3,q4,q5,q6=st.columns(6)
    q1.metric("HY percentile",fmt(rp.get("hy_percentile"),pct=True,d=0))
    q2.metric("EBP percentile",fmt(rp.get("ebp_percentile"),pct=True,d=0))
    q3.metric("FCI-G percentile",fmt(rp.get("fcig_percentile"),pct=True,d=0))
    q4.metric("Real-yield percentile",fmt(rp.get("real10_percentile"),pct=True,d=0))
    q5.metric("Term-premium percentile",fmt(rp.get("term_premium_percentile"),pct=True,d=0))
    corr=stress.get("cross_asset_corr",{})
    q6.metric("20d mean |corr|",fmt(corr.get("mean_abs_corr")) if corr.get("available") else "N/A")

    crash_names=["credit_deterioration","vol_without_credit_confirmation","credit_funding_stress_transition","forced_liquidation","post_liquidation_normalization","iwm_ath_state","spy_ath_state"]
    st.dataframe(scenarios[scenarios.scenario.isin(crash_names)],use_container_width=True,hide_index=True)

    # Official EBP recession-risk estimate is not a crash probability.
    rs=fed_research_series(bundle.get("fed_research",{}))
    if "EBP_RECESSION_PROB" in rs and len(rs["EBP_RECESSION_PROB"]):
        last=float(rs["EBP_RECESSION_PROB"].dropna().iloc[-1])
        dt=rs["EBP_RECESSION_PROB"].dropna().index[-1].date()
        st.metric("Fed EBP model recession risk",f"{last:.1%}",help=f"Official research-series estimate as of {dt}; recession risk ≠ market crash probability.")

    st.markdown("### Why Russell/IWM is only a scenario input")
    iwm=state["index"].get("IWM",{})
    if iwm.get("available"):
        st.write(f"IWM drawdown from loaded peak: **{iwm['drawdown']:.2%}** · near ATH: **{iwm['near_ath']}** · recent ATH-like closes: **{iwm['recent_ath_hits']}**.")
        st.caption("Production ATH continuation/failure test still requires breadth + PIT earnings revisions + flows. Price ATH alone has no directional vote.")
    else: st.info("IWM history unavailable from live feed.")

# ── Scenario Matrix ──────────────────────────────────────────────────────
with T[2]:
    st.subheader("Scenario/state-transition library")
    st.write("Scenarios can sit on macro, crash, rates, index, ticker, commodity, FX, crypto or fiscal engines. They are tested as minimal sufficient sets, not by stuffing all 52 metrics into every model.")
    lib=library_frame().copy()
    ev=scenarios[["scenario","status","evidence","confidence"]].copy()
    merged=lib.merge(ev,on="scenario",how="left")
    merged["status"]=merged["status"].fillna("DATA_GATED / NOT YET LIVE")
    st.dataframe(merged,use_container_width=True,hide_index=True,height=620)

    st.markdown("### Fed scenario-research benchmark")
    spf=bundle.get("fed_research",{}).get("spf_scenarios",{}).get("data",pd.DataFrame())
    proj=spf_forecast_error_projection(spf)
    if proj.get("available"):
        st.warning(proj["warning"])
        pc=st.columns(len(proj["probabilities"]))
        for col,(name,val) in zip(pc,proj["probabilities"].items()): col.metric(name.replace("_"," ").title(),f"{val:.1%}")
        qq=[]
        for k,v in proj["quantiles"].items(): qq.append([k,v["p10"],v["p50"],v["p90"]])
        st.dataframe(pd.DataFrame(qq,columns=["Variable","P10","Median","P90"]),use_container_width=True,hide_index=True)
    else: st.info("Fed SPF scenario research snapshot unavailable.")

    st.markdown("### Controlled scenario-validation evidence")
    svp=HERE/"research"/"scenario_validation_results_v2.csv"
    psp=HERE/"research"/"price_state_validation_results_v2.csv"
    try:
        sv=pd.read_csv(svp)
        st.caption("Expanding-OOS scenario classifier tests. Revised-history inputs mean PROMISING ≠ final PIT proof.")
        st.dataframe(sv,use_container_width=True,hide_index=True,height=300)
    except Exception as ex:
        st.info(f"Macro scenario validation unavailable: {ex}")
    try:
        ps=pd.read_csv(psp)
        focus=ps[ps["scenario"].isin([
            "first_ath_after_12m_gap",
            "repeated_ath_cluster",
            "ath_plus_long_rate_shock",
            "high_vol_without_credit_deterioration",
            "high_vol_plus_credit_deterioration",
            "credit_improving_near_ath",
        ])].copy()
        st.caption("Episode-clustered S&P price-state tests. These test ATH/stress placement, not Russell-specific alpha.")
        for c in ["mean_return","median_return","p_positive","p_gt_10","p_gt_25","p_lt_m10","p10_return","p90_return","median_max_dd","p_dd_lt_m10","delta_median_vs_baseline","delta_p_positive_vs_baseline"]:
            if c in focus: focus[c]=focus[c].map(lambda x:f"{x:.1%}" if np.isfinite(x) else "N/A")
        st.dataframe(focus,use_container_width=True,hide_index=True,height=340)
    except Exception as ex:
        st.info(f"Price-state validation unavailable: {ex}")

# ── Forward Projection ───────────────────────────────────────────────────
with T[3]:
    st.subheader("Forward distribution — macro-state analogs")
    symbol=st.text_input("Ticker / index / FX / crypto symbol","IWM").strip().upper()
    neighbors=st.slider("Historical analog count",8,40,20,1)
    flat=flatten_prices(bundle["market"])
    price=flat.get(symbol)
    if price is None:
        if st.button("Fetch selected symbol"):
            with st.spinner(f"Fetching {symbol}…"):
                price,_=get_single_price(symbol)
            st.session_state["selected_price"]=(symbol,price)
        if st.session_state.get("selected_price",(None,None))[0]==symbol:
            price=st.session_state["selected_price"][1]
    if price is not None and len(pd.Series(price).dropna()):
        stats,analogs,meta=macro_analog_projection(fred,bundle.get("fed_research",{}),price,neighbors)
        if len(stats):
            st.warning(meta.get("warning",""))
            show=stats.copy()
            for col in ["p_positive","p_10","p_25","p_50","p_100","p_loss10","p10","median","p90"]:
                show[col]=show[col].map(lambda x:f"{x:.1%}")
            st.dataframe(show,use_container_width=True,hide_index=True)
            st.markdown("**Remaining-upside questions are explicit:** P(+25%), P(+50%), P(+100%) are shown rather than declaring an arbitrary maximum target.")
            with st.expander("Closest historical macro states"):
                a=analogs.reset_index().rename(columns={analogs.index.name or "index":"month"})
                st.dataframe(a[[c for c in ["month","distance","1M","3M","6M","12M"] if c in a]],use_container_width=True,hide_index=True)
        else: st.info("Projection unavailable: "+meta.get("reason","insufficient overlapping history"))
    else:
        st.info("Symbol not present in the loaded market subset. Press Fetch selected symbol.")

# ── Bottleneck Tickers ───────────────────────────────────────────────────
with T[4]:
    st.subheader("Quality-first bottleneck / reload engine")
    st.write("Curated bottleneck files may nominate candidates but cannot give them a score. Verification requires SEC filing evidence + filed-date fundamental capture. Actionable LONG/SHORT still requires a defensible expectation-gap/valuation layer.")
    universes=load_universes(); prior=bundle.get("discovery_priors",{})
    seed=discovery_candidates(prior,universes.get("us",[]),limit=20)
    st.caption("Prior-only candidate seeds: "+(", ".join(seed) if seed else "none extracted"))
    manual=st.text_input("Candidates to verify (max 10)",value=", ".join(seed[:5]))
    use_sec=st.toggle("Verify latest SEC 10-Q/10-K bottleneck language",value=True)
    if st.button("Run bottleneck verification",type="primary"):
        tickers=[x.strip().upper() for x in manual.split(",") if x.strip()][:10]
        if not tickers: st.warning("Enter at least one ticker.")
        else:
            with st.spinner("Checking current fundamentals + filing evidence…"):
                ranked,details=rank_candidates(tickers,use_sec=use_sec,max_results=8)
            st.session_state["bn_ranked"]=ranked; st.session_state["bn_details"]=details
    ranked=st.session_state.get("bn_ranked")
    details=st.session_state.get("bn_details",{})
    if isinstance(ranked,pd.DataFrame) and len(ranked):
        st.dataframe(ranked,use_container_width=True,hide_index=True)
        qual=ranked[ranked.status=="BOTTLENECK_VERIFIED"]
        if len(qual)==0: st.warning("NO BOTTLENECK-VERIFIED CANDIDATE. Quality gate did not verify a full filing→capture→monetization chain.")
        selected=st.selectbox("Inspect reason",ranked.ticker.tolist())
        d=details.get(selected,{})
        st.markdown(f"### {selected} — {d.get('status','')}")
        st.write(d.get("reason","No verified reason"))
        cur=d.get("current",{})
        x1,x2,x3,x4=st.columns(4)
        x1.metric("Current",fmt(cur.get("current_price")))
        x2.metric("Drawdown from 5Y peak",fmt(cur.get("drawdown_from_peak"),pct=True))
        x3.metric("Analyst target upside proxy",fmt(cur.get("target_upside"),pct=True))
        x4.metric("RELOAD candidate",str(d.get("reload_candidate",False)))
        st.markdown("**Kill switches**")
        for k in d.get("kill_switches",[]): st.write("- "+k)
        sec=d.get("sec",{})
        sf=d.get("sec_facts",{})
        if sf.get("ok"):
            st.caption(f"SEC Company Facts latest filed evidence: {sf.get('latest_filed')} · uses filed-date lineage")
            sfrow=pd.DataFrame([{k:sf.get(k) for k in ["revenue_yoy","gross_profit_yoy","operating_income_yoy","net_income_yoy","gross_margin","operating_margin","gross_margin_yoy_delta","operating_margin_yoy_delta","fcf_diagnostic","revenue_points"]}])
            for col in ["revenue_yoy","gross_profit_yoy","operating_income_yoy","net_income_yoy","gross_margin","operating_margin","gross_margin_yoy_delta","operating_margin_yoy_delta"]:
                if col in sfrow: sfrow[col]=sfrow[col].map(lambda x:f"{x:.1%}" if np.isfinite(x) else "N/A")
            st.dataframe(sfrow,use_container_width=True,hide_index=True)
            st.caption(sf.get("note",""))
        elif use_sec:
            st.caption("SEC Company Facts: "+sf.get("reason","unavailable"))
        if sec.get("ok"):
            st.caption(f"SEC evidence: {sec.get('form')} filed {sec.get('filed')}")
            with st.expander("Filing evidence snippets"):
                for sn in sec.get("snippets",[]): st.write(f"**{sn['group']} / {sn['term']}** — {sn['snippet']}")
        st.markdown("**Own-history forward distribution (context only, not macro-conditioned)**")
        rr=[]
        for h,v in d.get("forward_own_history",{}).items():
            if v.get("available"): rr.append([f"{h}M",v["p25"],v["p50"],v["p100"],v["pneg20"],v["median"],v["p10"],v["p90"]])
        if rr:
            rr=pd.DataFrame(rr,columns=["Horizon","P>25%","P>50%","P>100%","P<-20%","Median","P10","P90"])
            for col in rr.columns[1:]: rr[col]=rr[col].map(lambda x:f"{x:.1%}")
            st.dataframe(rr,use_container_width=True,hide_index=True)

# ── Cross-Market ─────────────────────────────────────────────────────────
with T[5]:
    st.subheader("Cross-market state matrix")
    proxies={"US large":"SPY","US small":"IWM","IHSG":"^JKSE","Crypto":"BTC-USD","Gold":"GLD","Oil":"USO","USD":"UUP","Long bonds":"TLT"}
    flat=flatten_prices(bundle["market"]); rows=[]
    for name,tk in proxies.items():
        s=pd.Series(flat.get(tk,pd.Series(dtype=float))).dropna()
        if len(s)<60: rows.append([name,tk,"NO DATA",np.nan,np.nan,np.nan,np.nan]); continue
        def ret(days):
            old=s.loc[:s.index[-1]-pd.Timedelta(days=days)]
            return float(s.iloc[-1]/old.iloc[-1]-1) if len(old) else np.nan
        aa=ath_state(s)
        rv=float(s.pct_change().tail(20).std()*np.sqrt(252)) if len(s)>21 else np.nan
        rows.append([name,tk,"NEAR ATH" if aa.get("near_ath") else "BELOW ATH",aa.get("drawdown"),ret(91),ret(183),rv])
    mdf=pd.DataFrame(rows,columns=["Market","Proxy","Price state","DD from peak","3M","6M","20d ann vol"])
    for col in ["DD from peak","3M","6M","20d ann vol"]: mdf[col]=mdf[col].map(lambda x:f"{x:.1%}" if np.isfinite(x) else "N/A")
    st.dataframe(mdf,use_container_width=True,hide_index=True)
    st.caption("This matrix is observation, not a regime→asset playbook. Opportunity ranking requires asset-specific fundamentals/physical data and current pricing.")

# ── Proof Center ─────────────────────────────────────────────────────────
with T[6]:
    st.subheader("52 metric families — placement and proof status")
    reg=pd.DataFrame(METRIC_FAMILIES)
    st.dataframe(reg,use_container_width=True,hide_index=True,height=520)
    st.markdown("### Controlled validation results")
    p=HERE/"research"/"metric_validation_results_v2.csv"
    try:
        vr=pd.read_csv(p); st.dataframe(vr,use_container_width=True,hide_index=True,height=420)
    except Exception as ex: st.error(f"Proof registry missing: {ex}")

    st.markdown("### Scenario / state-transition tests")
    for fname,label in [("scenario_validation_results_v2.csv","Macro scenario expanding-OOS"),("price_state_validation_results_v2.csv","ATH / vol / credit episode tests")]:
        fp=HERE/"research"/fname
        try:
            tmp=pd.read_csv(fp)
            st.write(f"**{label}**")
            st.dataframe(tmp,use_container_width=True,hide_index=True,height=260)
        except Exception as ex:
            st.info(f"{label}: unavailable ({ex})")
    st.markdown("### Rejected mappings")
    for x in [
        "Fed assets − TGA − RRP → universal buy/sell",
        "CAPE high → immediate short",
        "yield-curve inversion → immediate short",
        "VIX threshold → crash",
        "inflation high → automatically buy gold/oil",
        "backlog headline → automatic winner",
        "dealer gamma estimate → deterministic direction",
        "tune until PLTR/SNDK appear",
        "all 52 metrics into every scenario",
    ]: st.write("✗ "+x)

# ── Data Lineage ─────────────────────────────────────────────────────────
with T[7]:
    st.subheader("Data lineage / availability")
    st.markdown("### FRED")
    st.json(fred_meta)
    st.markdown("### Market feeds")
    st.dataframe(pd.DataFrame([{**{"market":k},**v} for k,v in market_sources.items()]),use_container_width=True,hide_index=True)
    st.markdown("### Official Fed research data")
    fedrows=[]
    for k,v in bundle.get("fed_research",{}).items():
        fedrows.append([k,v.get("source"),len(v.get("data",[])),v.get("url")])
    st.dataframe(pd.DataFrame(fedrows,columns=["Dataset","Source","Rows","Official URL"]),use_container_width=True,hide_index=True)
    st.markdown("### Specialized feeds")
    st.json((bundle.get("feeds") or {}).get("_status",{}))
    st.markdown("### Bundled research files")
    st.dataframe(pd.DataFrame(bundle.get("research_meta",{}).get("files",[])),use_container_width=True,hide_index=True)
    st.markdown("### Treasury / NY Fed raw plumbing")
    st.json(bundle.get("treasury_plumbing",{}))
    st.caption("Only raw TGA/RRP/SOFR observations are used in v2. The legacy net-liquidity risk-on/off formula is intentionally not used.")
    st.markdown("### EIA physical-market connector")
    eps=physical_snapshot(bundle.get("eia_physical",{}))
    st.dataframe(eps,use_container_width=True,hide_index=True)
    st.caption("EIA requires a free EIA_API_KEY. No key means DATA_GATED; the app does not substitute price as physical inventory.")
    st.error("Still DATA-GATED for final proof: PIT analyst revisions, historical constituents/delistings, full macro vintages, historical options/dealer inventory, global commodity physical histories beyond the connected EIA seed set, cross-currency basis history, and token unlock/emission history.")

# ── Asset-Specific Data ──────────────────────────────────────────────────
with T[8]:
    st.subheader("Asset-specific observable layers")
    st.write("These inputs refine the common macro state. They are never hard-coded into regime→asset trades.")
    st.markdown("### Energy physical state — EIA")
    eps=physical_snapshot(bundle.get("eia_physical",{})).copy()
    for col in ["4w_change","13w_change","own_history_percentile"]:
        if col in eps:
            eps[col]=eps[col].map(lambda x:f"{x:.1%}" if np.isfinite(x) else "N/A")
    st.dataframe(eps,use_container_width=True,hide_index=True)
    st.caption("Raw physical state only. Seasonal normalization, curve/basis and CFTC positioning must be combined before a commodity trade can qualify.")

    st.markdown("### Specialized live/snapshot feeds")
    feeds=bundle.get("feeds",{}) or {}
    st.json(feeds.get("_status",{}))
    if feeds.get("onchain"):
        with st.expander("Crypto / DeFiLlama observable data"):
            st.json(feeds.get("onchain"))
    if feeds.get("cot"):
        with st.expander("CFTC positioning"):
            st.json(feeds.get("cot"))
    if feeds.get("gex"):
        with st.expander("Options/GEX estimates"):
            st.json(feeds.get("gex"))
    if feeds.get("finra"):
        with st.expander("FINRA off-exchange short-volume feed"):
            st.json(feeds.get("finra"))
    st.info("For IHSG, foreign-flow/Type-F history remains a separate live connector and should be cached before broad-universe scans; it is not treated as available when the connector did not return data.")

st.divider()
st.caption("v2 production-research build. Missing data lowers coverage; it never becomes a synthetic signal.")
