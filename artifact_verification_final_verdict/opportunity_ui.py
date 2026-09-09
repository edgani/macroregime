from __future__ import annotations

import html
import json
import math
from typing import Any, Dict, Mapping, Optional, Sequence

import pandas as pd

from opportunity_learning import learning_report
from opportunity_longitudinal import OpportunityMemory


def _f(x: Any) -> float:
    try:
        v=float(x); return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _pct(x: Any, digits: int=1) -> str:
    v=_f(x); return "—" if not math.isfinite(v) else f"{v*100:+.{digits}f}%"


def _num(x: Any, digits: int=0) -> str:
    v=_f(x); return "—" if not math.isfinite(v) else f"{v:,.{digits}f}"


def _money(x: Any, market: str="") -> str:
    v=_f(x)
    if not math.isfinite(v): return "—"
    if str(market).upper()=="IHSG": return f"Rp{v:,.0f}"
    if abs(v)>=1e9: return f"${v/1e9:,.2f}B"
    if abs(v)>=1e6: return f"${v/1e6:,.2f}M"
    return f"${v:,.2f}"


def _safe_json(v: Any) -> Dict[str,Any]:
    if isinstance(v,dict): return v
    try: return json.loads(v) if v else {}
    except Exception: return {}


def install_memequant_style(st) -> None:
    st.markdown("""
<style>
:root{--mq-bg:#031017;--mq-panel:#061923;--mq-panel2:#07131c;--mq-line:#0e4d5b;--mq-line2:#123541;--mq-cyan:#10f4cd;--mq-green:#19e8a0;--mq-red:#ff4d68;--mq-amber:#ffcc66;--mq-blue:#2ab8ff;--mq-text:#dff8fb;--mq-muted:#7396a2}
.stApp{background:radial-gradient(circle at 35% -10%,rgba(0,216,190,.05),transparent 28%),var(--mq-bg)!important;color:var(--mq-text)}
.block-container{max-width:1780px!important;padding:8px 12px 18px!important}
header[data-testid="stHeader"]{height:0;background:transparent}
[data-testid="stSidebar"]{display:none!important} [data-testid="collapsedControl"]{display:none!important}
.mq-top{display:grid;grid-template-columns:250px repeat(5,minmax(92px,1fr)) 2.1fr 150px;gap:8px;align-items:stretch;margin-bottom:8px}
.mq-brand{display:flex;align-items:center;gap:10px;padding:8px 10px}.mq-logo{font-size:29px;color:var(--mq-cyan);font-weight:950;letter-spacing:-8px}.mq-name{font-size:19px;font-weight:900}.mq-name span{color:var(--mq-cyan)}.mq-tag{font-size:8px;color:#7295a0;letter-spacing:.16em}
.mq-status,.mq-search,.mq-wallet{border:1px solid var(--mq-line);border-radius:8px;background:linear-gradient(180deg,#071a23,#05121a);padding:7px 10px}.mq-status b{display:block;color:var(--mq-cyan);font-size:10px;letter-spacing:.04em}.mq-status small{display:block;color:#8ab3bd;font-size:9px;margin-top:2px}.mq-search{display:flex;align-items:center;color:#789aa3;font-size:10px}.mq-wallet{text-align:center;color:var(--mq-cyan);font-weight:850;font-size:11px;display:flex;align-items:center;justify-content:center}
.mq-tabs{display:flex;gap:26px;border-bottom:1px solid var(--mq-line2);margin-bottom:8px;padding:0 8px}.mq-tab{font-size:10px;padding:8px 2px;color:#b6cbd0}.mq-tab.active{color:var(--mq-cyan);border-bottom:2px solid var(--mq-cyan);font-weight:800}
.mq-titlebar{border:1px solid var(--mq-line);border-radius:8px;background:#061722;padding:10px 12px;margin-bottom:8px;display:flex;justify-content:space-between;gap:14px}.mq-title{font-size:16px;font-weight:900}.mq-sub{font-size:9px;color:#91adb5;margin-top:2px}.mq-kpirow{display:flex;gap:8px;flex-wrap:wrap;justify-content:flex-end}.mq-kpi{border:1px solid var(--mq-line2);border-radius:7px;background:#05131b;padding:5px 8px;min-width:92px}.mq-kpi b{font-size:10px;color:var(--mq-cyan)}.mq-kpi strong{display:block;font-size:13px;margin-top:2px}.mq-kpi small{font-size:8px;color:#7899a2}
.mq-grid{display:grid;grid-template-columns:1.05fr 2.05fr 1fr;gap:8px}.mq-panel{border:1px solid var(--mq-line);border-radius:8px;background:linear-gradient(180deg,#061823,#04131b);overflow:hidden}.mq-ph{padding:8px 10px;border-bottom:1px solid var(--mq-line2);font-size:11px;font-weight:900;display:flex;justify-content:space-between}.mq-body{padding:8px 10px}.mq-row{display:grid;grid-template-columns:34px 1.4fr .8fr .8fr;gap:5px;padding:6px 0;border-bottom:1px solid rgba(31,90,100,.25);font-size:9px;align-items:center}.mq-row:last-child{border-bottom:0}.mq-sym{font-weight:900;color:#c9f7f4}.mq-up{color:var(--mq-green);font-weight:850}.mq-down{color:var(--mq-red);font-weight:850}.mq-pill{display:inline-block;border:1px solid var(--mq-line);border-radius:5px;padding:2px 5px;color:var(--mq-cyan);font-size:8px}.mq-pill.red{border-color:#7b2331;color:#ff5e73}.mq-pill.amber{border-color:#6d5b24;color:#ffd16e}.mq-hero{border:1px solid #0c6a65;border-radius:8px;background:#061b23;padding:10px;margin-bottom:8px}.mq-hero-top{display:flex;justify-content:space-between;gap:10px}.mq-hero h2{font-size:17px;margin:0;color:#e8ffff}.mq-meta{font-size:9px;color:#7fa1aa;margin-top:3px}.mq-thesis{font-size:10px;color:#b4d1d5;line-height:1.45;margin-top:8px}.mq-scores{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px}.mq-score{border-left:1px solid var(--mq-line2);padding-left:7px}.mq-score:first-child{border-left:0}.mq-score small{font-size:8px;color:#789aa3}.mq-score strong{font-size:13px;color:var(--mq-cyan);display:block}.mq-feed{font-size:9px}.mq-feedrow{display:grid;grid-template-columns:66px 78px 1fr;gap:6px;padding:6px 0;border-bottom:1px solid rgba(31,90,100,.22)}.mq-event{font-weight:850;color:var(--mq-cyan)}
.mq-mini-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:6px}.mq-mini{border:1px solid var(--mq-line2);border-radius:6px;background:#05141c;padding:7px}.mq-mini small{font-size:8px;color:#73959f}.mq-mini strong{display:block;font-size:12px;margin-top:2px}.mq-chain{font-size:9px;line-height:1.55;color:#acd2d4}.mq-arrow{color:var(--mq-cyan);font-weight:900}.mq-ledger{margin-top:8px;border:1px solid var(--mq-line);border-radius:8px;background:#04131b;padding:8px 10px;font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:9px;color:#70cfc3}.mq-section{font-size:9px;color:#79a2aa;text-transform:uppercase;letter-spacing:.12em;font-weight:900;margin:10px 0 6px}
.mq-empty{border:1px dashed var(--mq-line2);border-radius:7px;padding:12px;color:#75949d;font-size:9px}
.mq-bottom-grid{display:grid;grid-template-columns:1.25fr 1fr 1fr;gap:8px;margin-top:8px}
@media(max-width:1100px){.mq-top{grid-template-columns:1fr 1fr}.mq-grid,.mq-bottom-grid{grid-template-columns:1fr}.mq-scores{grid-template-columns:1fr 1fr}}

/* v3.2.2 unified shell: no legacy Streamlit visual language */
#MainMenu,footer,[data-testid="stToolbar"],[data-testid="stDecoration"]{display:none!important}
[data-testid="stAppViewContainer"]>.main{background:transparent}
div.stButton>button{background:#061923!important;color:#bfeff1!important;border:1px solid #0e4d5b!important;border-radius:7px!important;min-height:34px!important;font-size:10px!important;font-weight:800!important;letter-spacing:.02em!important;box-shadow:none!important}
div.stButton>button:hover{border-color:#10f4cd!important;color:#10f4cd!important;background:#07222b!important}
div.stButton>button[kind="primary"]{background:#09302f!important;color:#10f4cd!important;border-color:#10f4cd!important;box-shadow:inset 0 -2px 0 #10f4cd!important}
[data-baseweb="select"]>div,[data-baseweb="input"]>div,input,textarea{background:#05141c!important;color:#dff8fb!important;border-color:#123541!important;border-radius:7px!important}
[data-baseweb="tag"]{background:#0a4b4d!important;color:#bffff4!important;border:1px solid #13706e!important}
[data-testid="stDataFrame"]{border:1px solid var(--mq-line)!important;border-radius:8px!important;overflow:hidden!important;background:#04131b!important}
[data-testid="stAlert"]{background:#061923!important;border:1px solid #123541!important;color:#bcd6db!important;border-radius:8px!important}
[data-testid="stMetric"]{background:#061923!important;border:1px solid #123541!important;border-radius:8px!important;padding:8px!important}
.mq-scope{display:grid;grid-template-columns:1.5fr repeat(4,minmax(90px,.6fr));gap:8px;margin:7px 0 9px}.mq-scope-card{border:1px solid var(--mq-line2);border-radius:7px;background:#05141c;padding:6px 9px}.mq-scope-card small{font-size:8px;color:#73959f}.mq-scope-card strong{display:block;font-size:10px;color:#dff8fb;margin-top:2px}.mq-scope-card strong.ok{color:var(--mq-cyan)}
.mq-pagehead{display:flex;align-items:flex-start;justify-content:space-between;gap:14px;border:1px solid var(--mq-line);border-radius:8px;background:linear-gradient(180deg,#061a24,#05131b);padding:10px 12px;margin:8px 0}.mq-pagehead h1{font-size:17px;margin:0;color:#ecffff}.mq-pagehead p{font-size:9px;margin:3px 0 0;color:#7fa0aa}.mq-pagebadge{border:1px solid #0e645f;border-radius:6px;padding:4px 7px;color:var(--mq-cyan);font-size:9px;font-weight:850}
.mq-subnav-label{font-size:8px;letter-spacing:.12em;color:#648993;text-transform:uppercase;font-weight:900;margin:7px 0 4px}.mq-divider{height:1px;background:#123541;margin:8px 0}.mq-note{border:1px solid #123541;border-radius:7px;background:#05141c;padding:8px 10px;color:#87a8b0;font-size:9px;line-height:1.45}.mq-note b{color:#dff8fb}
.mq-vgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin:8px 0}.mq-vcard{border:1px solid var(--mq-line);border-radius:8px;background:#05151e;padding:9px}.mq-vcard small{font-size:8px;color:#70949d}.mq-vcard strong{display:block;font-size:12px;margin-top:3px}.mq-vcard p{font-size:8px;color:#7899a2;line-height:1.4;margin:5px 0 0}
.mq-list{border:1px solid var(--mq-line);border-radius:8px;overflow:hidden}.mq-lrow{display:grid;grid-template-columns:80px 1.2fr .8fr .8fr .9fr;gap:7px;padding:7px 9px;border-bottom:1px solid rgba(18,53,65,.7);font-size:9px;align-items:center}.mq-lrow:last-child{border-bottom:0}.mq-lhead{color:#6f929c;font-size:8px;text-transform:uppercase;letter-spacing:.06em;background:#071923}.mq-strong{font-weight:900;color:#dff8fb}
@media(max-width:1100px){.mq-scope,.mq-vgrid{grid-template-columns:1fr 1fr}.mq-lrow{grid-template-columns:70px 1fr 1fr}.mq-lrow>*:nth-child(n+4){display:none}}


/* v3.2.3: one visual system across every workspace; native dataframe skin removed from product surfaces */
.mq-table-wrap{border:1px solid var(--mq-line);border-radius:8px;overflow:auto;background:#04131b;scrollbar-color:#0e4d5b #04131b}
.mq-table{width:100%;border-collapse:collapse;min-width:760px;font-size:9px;color:#dff8fb}.mq-table thead th{position:sticky;top:0;z-index:2;background:#071923;color:#6f929c;text-transform:uppercase;letter-spacing:.055em;font-size:8px;text-align:left;padding:8px 9px;border-bottom:1px solid #123541;white-space:nowrap}.mq-table td{padding:7px 9px;border-bottom:1px solid rgba(18,53,65,.68);white-space:nowrap;max-width:340px;overflow:hidden;text-overflow:ellipsis}.mq-table tr:last-child td{border-bottom:0}.mq-table tbody tr:hover{background:#07212a}.mq-cell-up{color:var(--mq-green)!important;font-weight:850}.mq-cell-down{color:var(--mq-red)!important;font-weight:850}.mq-cell-amber{color:var(--mq-amber)!important;font-weight:800}
.mq-three{display:grid;grid-template-columns:1.25fr 1fr 1fr;gap:8px}.mq-statline{display:grid;grid-template-columns:repeat(4,1fr);gap:6px}.mq-stat{border:1px solid var(--mq-line2);border-radius:7px;background:#05141c;padding:8px}.mq-stat small{font-size:8px;color:#73959f}.mq-stat strong{display:block;font-size:12px;margin-top:2px;color:#e4ffff}
.mq-proof-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}.mq-proof{border:1px solid var(--mq-line);border-radius:8px;background:#05151e;padding:10px}.mq-proof small{font-size:8px;color:#70949d}.mq-proof strong{display:block;font-size:11px;color:var(--mq-cyan);margin-top:3px}.mq-proof p{font-size:8px;color:#7899a2;line-height:1.4;margin:5px 0 0}
.mq-chain-full{display:flex;align-items:center;gap:7px;overflow-x:auto}.mq-chain-full>span:not(.mq-arrow){min-width:118px}.mq-chain-full small{display:block;color:#628c96;font-size:7px;letter-spacing:.07em}.mq-chain-full b{display:block;margin-top:3px;font-size:9px;color:#dff8fb;white-space:normal}
[data-testid="stDataFrame"],[data-testid="stMetric"]{display:none!important}
@media(max-width:1100px){.mq-three,.mq-proof-grid,.mq-statline{grid-template-columns:1fr}}


/* control normalization: interactive native widgets keep functionality but visually belong to the same shell */
[data-testid="stMultiSelect"] [data-baseweb="tag"], [data-testid="stMultiSelect"] span[data-baseweb="tag"], div[data-baseweb="tag"], span[data-baseweb="tag"]{background:#073338!important;color:#bffff4!important;border:1px solid #0e756e!important;border-radius:6px!important}
[data-testid="stMultiSelect"] [data-baseweb="tag"] *{color:#bffff4!important}
[data-testid="stMultiSelect"] [data-baseweb="tag"] svg{fill:#10f4cd!important}
[data-baseweb="select"] svg,[data-baseweb="input"] svg{fill:#10f4cd!important;color:#10f4cd!important}
[data-testid="stSpinner"]{color:#8fb7bf!important;font-size:10px!important}
[data-testid="stTextInput"] input::placeholder{color:#638994!important}

</style>
""",unsafe_allow_html=True)


def render_global_header(st, *, scan_count: int=0, event_count: int=0, active_count: int=0, outcome_count: int=0, macro_regime: str="GATED", engine_version: str="v3.2.6") -> None:
    st.markdown(f"""
<div class='mq-top'>
 <div class='mq-brand'><div class='mq-logo'>◢◣</div><div><div class='mq-name'>Opportunity<span>OS</span></div><div class='mq-tag'>SCAN EARLY · FILTER NOISE · EXPLAIN ALPHA</div></div></div>
 <div class='mq-status'><b>◉ SCAN</b><small>{int(scan_count)} candidates</small></div>
 <div class='mq-status'><b>◆ MEMORY</b><small>{int(event_count)} events</small></div>
 <div class='mq-status'><b>◎ ENGINE</b><small>{html.escape(str(engine_version))}</small></div>
 <div class='mq-status'><b>◉ TRACKED</b><small>{int(active_count)} active</small></div>
 <div class='mq-status'><b>◇ OUTCOMES</b><small>{int(outcome_count)} matured</small></div>
 <div class='mq-search'>⌕ Search / inspect from the active workspace below</div>
 <div class='mq-wallet'>RISK · {html.escape(str(macro_regime)[:18])}</div>
</div>
""",unsafe_allow_html=True)


def _score_cards(scores: Mapping[str,Any]) -> str:
    items=[("INFLECTION",scores.get("inflection_score")),("CAPTURE",scores.get("capture_score")),("BOTTLENECK",scores.get("bottleneck_score")),("EXPECTATION",scores.get("expectation_gap_score"))]
    return "".join(f"<div class='mq-score'><small>{k}</small><strong>{_num(v,0)}</strong></div>" for k,v in items)



def _cell_class(v: Any) -> str:
    s=str(v or "").upper()
    if any(k in s for k in ["READY","ACTIVE","HIGH CONVICTION","BUILD CANDIDATE","SELECTIVE ADD","PROVING","EMERGING","SUPPORTIVE","CALM","TAILWIND"]):
        return "mq-cell-up"
    if any(k in s for k in ["GATED","INVALIDATED","SELL","BEARISH","SHORT","POWDER KEG","DEFENSIVE","RISK OFF"]):
        return "mq-cell-down"
    if any(k in s for k in ["PARTIAL","WATCH","MIXED","BASELINE BUILDING","NEEDS MORE EVIDENCE","NEEDS BETTER PRICE"]):
        return "mq-cell-amber"
    return ""

def _display_value(v: Any) -> str:
    if v is None: return "—"
    try:
        if pd.isna(v): return "—"
    except Exception:
        pass
    if isinstance(v,float):
        if not math.isfinite(v): return "—"
        av=abs(v)
        if av>=1_000_000_000: return f"{v/1_000_000_000:,.2f}B"
        if av>=1_000_000: return f"{v/1_000_000:,.2f}M"
        if av>=1000: return f"{v:,.0f}"
        if av>=10: return f"{v:,.2f}"
        return f"{v:,.4f}".rstrip('0').rstrip('.')
    if isinstance(v,(dict,list,tuple)):
        try: return json.dumps(v,ensure_ascii=False,separators=(",",":"))
        except Exception: return str(v)
    return str(v)

def dense_table_html(df: pd.DataFrame, columns=None, *, max_rows: int=40, height: int=420, labels: Optional[Mapping[str,str]]=None) -> str:
    if df is None or df.empty:
        return "<div class='mq-empty'>No rows available for this view.</div>"
    cols=list(columns) if columns else list(df.columns)
    cols=[c for c in cols if c in df.columns]
    labels=dict(labels or {})
    head=''.join(f"<th>{html.escape(str(labels.get(c,c)).replace('_',' '))}</th>" for c in cols)
    rows=[]
    for _,r in df.head(max_rows).iterrows():
        cells=[]
        for c in cols:
            val=_display_value(r.get(c))
            cls=_cell_class(val)
            title=html.escape(val)
            short=val if len(val)<=78 else val[:75]+"…"
            cells.append(f"<td class='{cls}' title='{title}'>{html.escape(short)}</td>")
        rows.append('<tr>'+''.join(cells)+'</tr>')
    return f"<div class='mq-table-wrap' style='max-height:{int(height)}px'><table class='mq-table'><thead><tr>{head}</tr></thead><tbody>{''.join(rows)}</tbody></table></div>"

def render_dense_table(st, df: pd.DataFrame, columns=None, *, max_rows: int=40, height: int=420, labels: Optional[Mapping[str,str]]=None) -> None:
    st.markdown(dense_table_html(df,columns,max_rows=max_rows,height=height,labels=labels),unsafe_allow_html=True)

def render_opportunity_tracker(
    st,
    ranked: pd.DataFrame,
    memory: OpportunityMemory,
    macro: Mapping[str,Any],
    *,
    search_query: str = "",
    selected_markets: Optional[Sequence[str]] = None,
) -> None:
    install_memequant_style(st)
    counts=memory.counts(); active=memory.events_frame(active_only=True,limit=200); alerts=memory.alerts_frame(limit=30); states=memory.states_frame(limit=80)
    active_scope=active.copy()
    if not active_scope.empty:
        if selected_markets is None:
            selected_markets=st.session_state.get("mq_market_scope_v322")
        if selected_markets is not None:
            allowed={str(x) for x in selected_markets}
            active_scope=active_scope[active_scope["market"].astype(str).isin(allowed)]
        query=str(search_query or st.session_state.get("mq_global_search_v322","")).strip().lower()
        if query:
            match=pd.Series(False,index=active_scope.index)
            for col in ["symbol","asset","theme","sector","industry"]:
                if col in active_scope:
                    match=match | active_scope[col].astype(str).str.lower().str.contains(query,regex=False,na=False)
            active_scope=active_scope[match]
    scoped_ids=set(active_scope["event_id"].astype(str)) if "event_id" in active_scope else set()
    if not alerts.empty: alerts=alerts[alerts["event_id"].astype(str).isin(scoped_ids)]
    if not states.empty: states=states[states["event_id"].astype(str).isin(scoped_ids)]
    quality=(ranked.get("data_quality",pd.Series(dtype=str)).astype(str).str.upper()=="HIGH").sum() if not ranked.empty else 0
    top_html=f"""
<div class='mq-pagehead'><div><h1>Longitudinal Opportunity Tracker</h1><p>Automatic discovery → immutable first detection → persistent watch → future outcomes → regime-specific learning.</p></div><div class='mq-pagebadge'>NO AUTOTRADING</div></div>
<div class='mq-kpirow'><div class='mq-kpi'><b>ACTIVE</b><strong>{len(active_scope)}</strong><small>in current scope</small></div><div class='mq-kpi'><b>HIGH DATA</b><strong>{int(quality)}</strong><small>current scan</small></div><div class='mq-kpi'><b>FAILURES</b><strong>{counts['failures']}</strong><small>kept for learning</small></div><div class='mq-kpi'><b>MISSED</b><strong>{counts['missed']}</strong><small>no hindsight claims</small></div></div>
"""
    st.markdown(top_html,unsafe_allow_html=True)
    st.markdown("<div class='mq-note'><b>LIFECYCLE</b> · DISCOVER → STARTER → CORE → ADD/HOLD → NO CHASE → TRIM/EXIT · invalidated ideas remain in memory for learning.</div>",unsafe_allow_html=True)

    # Build left entities from active memory; fall back to current scan without fabricating events.
    if not active_scope.empty:
        left=active_scope.copy()
        left["display_score"]=left["scores_json"].map(lambda x:_f(_safe_json(x).get("opportunity_score")))
        left=left.sort_values(["active","display_score","first_seen_time"],ascending=[False,False,False],na_position="last")
    else:
        left=pd.DataFrame()

    selected_event=None
    if not left.empty:
        options=left["event_id"].tolist()
        labels={r["event_id"]:f"{r.get('symbol','')} · {r.get('theme','')}" for _,r in left.iterrows()}
        selected_event=st.selectbox("Tracked opportunity",options,format_func=lambda x:labels.get(x,x),label_visibility="collapsed",key="mq_selected_event")
        er=left[left["event_id"]==selected_event].iloc[0]
    else:
        er=None

    left_rows=""
    if not left.empty:
        for i,(_,r) in enumerate(left.head(14).iterrows(),1):
            score=_f(_safe_json(r.get("scores_json")).get("opportunity_score")); state=str(r.get("last_state") or "DISCOVERED")
            cls="mq-up" if state not in {"INVALIDATED","CROWDED"} else ("mq-down" if state=="INVALIDATED" else "")
            left_rows+=f"<div class='mq-row'><div>{i}</div><div><div class='mq-sym'>{html.escape(str(r.get('symbol','')))}</div><div style='color:#6f929c'>{html.escape(str(r.get('market','')))} · {html.escape(str(r.get('theme',''))[:34])}</div></div><div><span class='mq-pill'>{html.escape(state.replace('_',' '))}</span></div><div class='{cls}'>{_num(score,0)}</div></div>"
    else:
        left_rows="<div class='mq-empty'>No frozen opportunity events yet. The engine will create one only after a meaningful evidence/change threshold is met.</div>"

    if er is not None:
        scores=_safe_json(er.get("scores_json")); macroj=_safe_json(er.get("macro_context_json")); exp=_safe_json(er.get("expectation_json"))
        arch=er.get("archetypes_json"); arch=arch if isinstance(arch,list) else _safe_json(arch) if isinstance(arch,dict) else (json.loads(arch) if isinstance(arch,str) and arch.startswith("[") else [])
        live_row=pd.DataFrame()
        if ranked is not None and not ranked.empty and {"symbol","market"}.issubset(ranked.columns):
            live_row=ranked[(ranked["symbol"].astype(str)==str(er.get("symbol",""))) & (ranked["market"].astype(str)==str(er.get("market","")))]
        current_price=_f(live_row.iloc[0].get("price")) if not live_row.empty else math.nan
        first_price=_f(er.get("first_seen_price"))
        move=(current_price/first_price-1.0) if math.isfinite(current_price) and math.isfinite(first_price) and first_price>0 else math.nan
        score_value=_f(scores.get("opportunity_score"))
        score_label=_num(score_value,0) if math.isfinite(score_value) else "GATED"
        hero=f"""<div class='mq-hero'><div class='mq-hero-top'><div><h2>{html.escape(str(er.get('symbol','')))} · {html.escape(str(er.get('asset','')))}</h2><div class='mq-meta'>{html.escape(str(er.get('market','')))} · first seen {html.escape(str(er.get('first_seen_time',''))[:19])}</div></div><div><span class='mq-pill'>{html.escape(str(er.get('last_state') or 'DISCOVERED').replace('_',' '))}</span></div></div><div class='mq-mini-grid'><div class='mq-mini'><small>DETECTION PRICE</small><strong>{_money(first_price,str(er.get('market','')))}</strong></div><div class='mq-mini'><small>CURRENT PRICE</small><strong>{_money(current_price,str(er.get('market','')))}</strong></div><div class='mq-mini'><small>MOVE SINCE DETECTION</small><strong>{_pct(move)}</strong></div><div class='mq-mini'><small>OPPORTUNITY SCORE</small><strong>{score_label}</strong></div></div><div class='mq-thesis'>{html.escape(str(er.get('thesis','')))}</div><div class='mq-scores'>{_score_cards(scores)}</div></div>"""
        chain_parts=[
            ("DRIVER",er.get("driver")),("FIRST ORDER",er.get("first_order_effect")),
            ("SECOND ORDER",er.get("second_order_effect")),("BOTTLENECK",er.get("bottleneck")),
            ("BENEFICIARY",er.get("beneficiary")),("REVENUE LINK",er.get("revenue_link")),
            ("MARGIN LINK",er.get("margin_link")),("CATALYST",er.get("catalyst")),
            ("INVALIDATION",er.get("invalidation")),
        ]
        chain="<div class='mq-chain mq-chain-full'>"+"<span class='mq-arrow'> → </span>".join(
            f"<span><small>{html.escape(label)}</small><b>{html.escape(str(value or 'UNAVAILABLE'))}</b></span>" for label,value in chain_parts
        )+"</div>"
        mini=f"""<div class='mq-mini-grid'><div class='mq-mini'><small>EXPECTATION</small><strong>{html.escape(str(exp.get('expectation_state','UNKNOWN')))}</strong></div><div class='mq-mini'><small>CATALYST</small><strong>{html.escape(str(er.get('catalyst',''))[:34])}</strong></div><div class='mq-mini'><small>MACRO</small><strong>{html.escape(str(macroj.get('regime') or macroj.get('action_label') or 'GATED')[:28])}</strong></div><div class='mq-mini'><small>ARCHETYPE</small><strong>{html.escape(', '.join(arch[:2]) if isinstance(arch,list) else '—')}</strong></div></div>"""
    else:
        hero="<div class='mq-empty'>No selected historical event.</div>"; chain=""; mini=""

    feed=""
    if not states.empty:
        sdf=states if selected_event is None else states[states["event_id"]==selected_event]
        for _,r in sdf.head(12).iterrows():
            feed+=f"<div class='mq-feedrow'><div>{html.escape(str(r.get('observed_at_utc',''))[11:19])}</div><div class='mq-event'>{html.escape(str(r.get('lifecycle_state','')).replace('_',' '))}</div><div>{html.escape(str(r.get('reason',''))[:68])}</div></div>"
    if not feed: feed="<div class='mq-empty'>Lifecycle feed will populate as tracked opportunities change state.</div>"

    right=""
    if er is not None:
        component_keys=[("Inflection","inflection_score"),("Economic capture","capture_score"),("Scarcity","bottleneck_score"),("Expectation gap","expectation_gap_score"),("Catalyst","catalyst_score"),("Valuation / asymmetry","valuation_score"),("Positioning / flow","positioning_score"),("Opportunity macro","macro_alignment")]
        components="".join(f"<div class='mq-feedrow'><div>{html.escape(label)}</div><div class='mq-event'>{_num(scores.get(key),0) if math.isfinite(_f(scores.get(key))) else 'UNAVAILABLE'}</div><div>{'OBSERVED' if math.isfinite(_f(scores.get(key))) else 'MISSING'}</div></div>" for label,key in component_keys)
        right=f"""<div class='mq-mini-grid'><div class='mq-mini'><small>HIGH CONV PRICE</small><strong>{_money(er.get('price_at_high_conviction'),str(er.get('market','')))}</strong></div><div class='mq-mini'><small>SCORE COVERAGE</small><strong>{_pct(scores.get('score_coverage'))}</strong></div><div class='mq-mini'><small>SOURCE QUALITY</small><strong>{html.escape(str(er.get('source_quality','—')))}</strong></div><div class='mq-mini'><small>CAPTURE GATE</small><strong>{'PASS' if scores.get('capture_required_pass') else 'GATED'}</strong></div></div><div class='mq-section'>Component availability</div><div class='mq-feed'>{components}</div><div class='mq-section'>Invalidation</div><div class='mq-chain'>{html.escape(str(er.get('invalidation','—')))}</div>"""
    else: right="<div class='mq-empty'>Select an event to inspect first-seen state, catalyst and invalidation.</div>"

    st.markdown(f"<div class='mq-grid'><div class='mq-panel'><div class='mq-ph'>Tracked Opportunities <span>{len(left)}</span></div><div class='mq-body'>{left_rows}</div></div><div><div class='mq-panel'><div class='mq-ph'>Opportunity Detail <span>{html.escape(str(er.get('last_state','')) if er is not None else '')}</span></div><div class='mq-body'>{hero}<div class='mq-section'>Causal transmission chain</div>{chain}<div class='mq-section'>Live context at first detection</div>{mini}</div></div><div class='mq-panel' style='margin-top:8px'><div class='mq-ph'>Lifecycle Activity Feed</div><div class='mq-body mq-feed'>{feed}</div></div></div><div class='mq-panel'><div class='mq-ph'>Memory & Risk</div><div class='mq-body'>{right}</div></div></div>",unsafe_allow_html=True)

    outs=memory.outcomes_frame(selected_event) if selected_event else memory.outcomes_frame()
    if selected_event is None and not outs.empty:
        outs=outs[outs["event_id"].astype(str).isin(scoped_ids)]
    st.markdown("<div class='mq-three'>",unsafe_allow_html=True)
    # Streamlit does not permit nesting markdown containers around later widgets, so each visual block is rendered independently.
    st.markdown("</div>",unsafe_allow_html=True)
    c1,c2,c3=st.columns([1.25,1,1],gap="small")
    with c1:
        st.markdown("<div class='mq-section'>Opportunity Radar · current scan</div>",unsafe_allow_html=True)
        cols=[c for c in ["market","symbol","stage","research_action","change_state","expectation_gap","data_quality"] if c in ranked]
        render_dense_table(st,ranked,cols,max_rows=30,height=350)
    with c2:
        st.markdown("<div class='mq-section'>Outcome Memory</div>",unsafe_allow_html=True)
        if outs.empty:
            st.markdown("<div class='mq-empty'>No mature forward horizon yet. Fresh memory stays blank rather than inventing performance.</div>",unsafe_allow_html=True)
        else:
            cols=[c for c in ["horizon","absolute_return","alpha_vs_benchmark","alpha_vs_sector","mfe","mae","completed"] if c in outs]
            render_dense_table(st,outs,cols,max_rows=24,height=350)
    with c3:
        st.markdown("<div class='mq-section'>Alerts / Proof Tape</div>",unsafe_allow_html=True)
        if alerts.empty:
            st.markdown("<div class='mq-empty'>No deduplicated state alerts yet.</div>",unsafe_allow_html=True)
        else:
            cols=[c for c in ["observed_at_utc","alert_type","message"] if c in alerts]
            render_dense_table(st,alerts,cols,max_rows=20,height=350)

    st.markdown("<div class='mq-section'>Theme Clusters · Best Expression First</div>",unsafe_allow_html=True)
    if active_scope.empty:
        st.markdown("<div class='mq-empty'>No active theme cluster yet.</div>",unsafe_allow_html=True)
    else:
        tmp=active_scope.copy()
        tmp["opportunity_score"]=tmp["scores_json"].map(lambda x:_f(_safe_json(x).get("opportunity_score")))
        cluster=[]
        for theme,g in tmp.groupby("theme",dropna=False):
            g=g.sort_values("opportunity_score",ascending=False,na_position="last")
            syms=g["symbol"].astype(str).tolist()
            cluster.append({"Theme":theme,"Best expression":syms[0] if syms else "—","Second-best":syms[1] if len(syms)>1 else "—","Alternative":syms[2] if len(syms)>2 else "—","Candidates":len(g),"Best score":g.iloc[0].get("opportunity_score") if len(g) else math.nan})
        cdf=pd.DataFrame(cluster).sort_values("Best score",ascending=False,na_position="last")
        render_dense_table(st,cdf,list(cdf.columns),max_rows=30,height=320)


def render_learning_lab(st, memory: OpportunityMemory, baseline_outcomes: pd.DataFrame | None = None) -> None:
    install_memequant_style(st)
    rep=learning_report(memory, baseline_outcomes=baseline_outcomes)
    counts=memory.counts()
    st.markdown(f"""<div class='mq-pagehead'><div><h1>Learning / Replay Lab</h1><p>Chronological outcome learning, false-positive memory and missed-runner audits. Production weights never self-mutate.</p></div><div class='mq-pagebadge'>{counts.get('outcomes',0)} MATURE OUTCOMES</div></div>""",unsafe_allow_html=True)
    keys=[("PATTERN EXPECTANCY","patterns"),("TRUE WALK-FORWARD","walk_forward"),("BASELINES","baselines"),("RUNNER RECALL","runner_recall"),("FAILURES","failures"),("MISSED WINNERS","missed")]
    if st.session_state.get("mq_learning_view") not in [x[1] for x in keys]:
        st.session_state["mq_learning_view"]="patterns"
    def setv(v): st.session_state["mq_learning_view"]=v
    cols=st.columns(len(keys),gap="small")
    for col,(label,key) in zip(cols,keys):
        with col:
            st.button(label,key=f"learn_{key}",use_container_width=True,type="primary" if st.session_state["mq_learning_view"]==key else "secondary",on_click=setv,args=(key,))
    view=st.session_state["mq_learning_view"]
    notes={
        "patterns":"Historical expectancy is shown only when enough matured, comparable observations exist.",
        "walk_forward":"Training/calibration observations must precede each test window. No random shuffle.",
        "baselines":"Complex opportunity logic must beat transparent simple baselines OOS before promotion.",
        "runner_recall":"Recall is computed only from prospectively frozen cohorts whose future runner outcome has matured.",
        "failures":"Invalidated opportunities stay in memory and are classified by causal failure mode.",
        "missed":"Runner reconstruction is allowed only from information observable at the historical timestamp."
    }
    st.markdown(f"<div class='mq-note'><b>{html.escape(view.replace('_',' ').upper())}</b><br>{html.escape(notes[view])}</div>",unsafe_allow_html=True)
    df=rep.get(view,pd.DataFrame())
    if df is None or df.empty:
        msg={"patterns":"Insufficient mature stored outcomes. No confidence number is manufactured.","walk_forward":"Not enough chronological event/outcome history for a valid expanding walk-forward yet.","baselines":"No comparable baseline result is available yet.","runner_recall":"No prospectively audited runner cohort has matured yet.","failures":"No explicit false-positive reason has matured yet.","missed":"No PIT-reconstructable missed-runner case is available yet."}[view]
        st.markdown(f"<div class='mq-empty' style='margin-top:8px'>{html.escape(msg)}</div>",unsafe_allow_html=True)
    else:
        render_dense_table(st,df,list(df.columns),max_rows=80,height=520)
