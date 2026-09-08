from __future__ import annotations

import html
import json
import math
from typing import Any, Dict, Mapping, Optional

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
[data-testid="stSidebar"]{background:#05141c;border-right:1px solid var(--mq-line2)}
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
</style>
""",unsafe_allow_html=True)


def _score_cards(scores: Mapping[str,Any]) -> str:
    items=[("INFLECTION",scores.get("inflection_score")),("CAPTURE",scores.get("capture_score")),("BOTTLENECK",scores.get("bottleneck_score")),("EXPECTATION",scores.get("expectation_gap_score"))]
    return "".join(f"<div class='mq-score'><small>{k}</small><strong>{_num(v,0)}</strong></div>" for k,v in items)


def render_opportunity_tracker(st, ranked: pd.DataFrame, memory: OpportunityMemory, macro: Mapping[str,Any]) -> None:
    install_memequant_style(st)
    counts=memory.counts(); active=memory.events_frame(active_only=True,limit=200); alerts=memory.alerts_frame(limit=30); states=memory.states_frame(limit=80)
    quality=(ranked.get("data_quality",pd.Series(dtype=str)).astype(str).str.upper()=="HIGH").sum() if not ranked.empty else 0
    top_html=f"""
<div class='mq-top'>
 <div class='mq-brand'><div class='mq-logo'>◢◣</div><div><div class='mq-name'>Opportunity<span>OS</span></div><div class='mq-tag'>SCAN EARLY · EXPLAIN CAUSALLY · LEARN OOS</div></div></div>
 <div class='mq-status'><b>◉ DATA</b><small>{len(ranked)} scanned</small></div>
 <div class='mq-status'><b>◆ MEMORY</b><small>{counts['events']} events</small></div>
 <div class='mq-status'><b>◎ ENGINE</b><small>v3.2.1 UI hotfix</small></div>
 <div class='mq-status'><b>◉ ACTIVE</b><small>{counts['active']} tracked</small></div>
 <div class='mq-status'><b>◇ OUTCOMES</b><small>{counts['outcomes']} matured</small></div>
 <div class='mq-search'>⌕ Search opportunity / ticker / theme inside the tables below…</div>
 <div class='mq-wallet'>RISK · {html.escape(str(macro.get('regime','GATED'))[:18])}</div>
</div>
<div class='mq-titlebar'><div><div class='mq-title'>◉ Longitudinal Opportunity Tracker</div><div class='mq-sub'>Automatic discovery → immutable first detection → persistent watch → future outcomes → regime-specific learning. No autotrading.</div></div>
<div class='mq-kpirow'><div class='mq-kpi'><b>ACTIVE</b><strong>{counts['active']}</strong><small>persistent</small></div><div class='mq-kpi'><b>HIGH DATA</b><strong>{int(quality)}</strong><small>current scan</small></div><div class='mq-kpi'><b>FAILURES</b><strong>{counts['failures']}</strong><small>kept for learning</small></div><div class='mq-kpi'><b>MISSED</b><strong>{counts['missed']}</strong><small>no hindsight claims</small></div></div></div>
"""
    st.markdown(top_html,unsafe_allow_html=True)

    # Build left entities from active memory; fall back to current scan without fabricating events.
    if not active.empty:
        left=active.copy()
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
        hero=f"""<div class='mq-hero'><div class='mq-hero-top'><div><h2>{html.escape(str(er.get('symbol','')))} · {html.escape(str(er.get('asset','')))}</h2><div class='mq-meta'>{html.escape(str(er.get('market','')))} · first seen {html.escape(str(er.get('first_seen_time',''))[:19])} · {_money(er.get('first_seen_price'),str(er.get('market','')))}</div></div><div><span class='mq-pill'>{html.escape(str(er.get('last_state') or 'DISCOVERED').replace('_',' '))}</span></div></div><div class='mq-thesis'>{html.escape(str(er.get('thesis','')))}</div><div class='mq-scores'>{_score_cards(scores)}</div></div>"""
        chain=f"<div class='mq-chain'><b>{html.escape(str(er.get('driver','')))}</b> <span class='mq-arrow'>→</span> {html.escape(str(er.get('first_order_effect','')))} <span class='mq-arrow'>→</span> {html.escape(str(er.get('second_order_effect','')))} <span class='mq-arrow'>→</span> <b>{html.escape(str(er.get('bottleneck','')))}</b> <span class='mq-arrow'>→</span> {html.escape(str(er.get('beneficiary','')))}</div>"
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
        right=f"""<div class='mq-mini-grid'><div class='mq-mini'><small>FIRST PRICE</small><strong>{_money(er.get('first_seen_price'),str(er.get('market','')))}</strong></div><div class='mq-mini'><small>HIGH CONV PRICE</small><strong>{_money(er.get('price_at_high_conviction'),str(er.get('market','')))}</strong></div><div class='mq-mini'><small>SCORE COVERAGE</small><strong>{_pct(_safe_json(er.get('scores_json')).get('score_coverage'))}</strong></div><div class='mq-mini'><small>SOURCE QUALITY</small><strong>{html.escape(str(er.get('source_quality','—')))}</strong></div></div><div class='mq-section'>Invalidation</div><div class='mq-chain'>{html.escape(str(er.get('invalidation','—')))}</div>"""
    else: right="<div class='mq-empty'>Select an event to inspect first-seen state, catalyst and invalidation.</div>"

    st.markdown(f"<div class='mq-grid'><div class='mq-panel'><div class='mq-ph'>Tracked Opportunities <span>{len(left)}</span></div><div class='mq-body'>{left_rows}</div></div><div><div class='mq-panel'><div class='mq-ph'>Opportunity Detail <span>{html.escape(str(er.get('last_state','')) if er is not None else '')}</span></div><div class='mq-body'>{hero}<div class='mq-section'>Causal transmission chain</div>{chain}<div class='mq-section'>Live context at first detection</div>{mini}</div></div><div class='mq-panel' style='margin-top:8px'><div class='mq-ph'>Lifecycle Activity Feed</div><div class='mq-body mq-feed'>{feed}</div></div></div><div class='mq-panel'><div class='mq-ph'>Memory & Risk</div><div class='mq-body'>{right}</div></div></div>",unsafe_allow_html=True)

    # Native tables below the dense visual shell keep the page actually interactive/searchable.
    st.markdown("<div class='mq-bottom-grid'>",unsafe_allow_html=True)
    st.markdown("</div>",unsafe_allow_html=True)
    c1,c2,c3=st.columns([1.25,1,1])
    with c1:
        st.markdown("<div class='mq-section'>Opportunity Radar · current scan</div>",unsafe_allow_html=True)
        if ranked.empty: st.info("Current scan is empty / gated.")
        else:
            cols=[c for c in ["market","symbol","stage","research_action","change_state","evidence_families","deterioration_families","expectation_gap","data_quality"] if c in ranked]
            st.dataframe(ranked[cols].head(30),use_container_width=True,hide_index=True,height=390)
    with c2:
        st.markdown("<div class='mq-section'>Outcome Memory</div>",unsafe_allow_html=True)
        outs=memory.outcomes_frame(selected_event) if selected_event else memory.outcomes_frame()
        if outs.empty: st.caption("No mature forward horizon yet. This is correct on a fresh v3.2 database; the engine will not invent performance.")
        else:
            cols=[c for c in ["horizon","absolute_return","alpha_vs_benchmark","alpha_vs_sector","mfe","mae","completed"] if c in outs]
            st.dataframe(outs[cols],use_container_width=True,hide_index=True,height=390)
    with c3:
        st.markdown("<div class='mq-section'>Alerts / proof tape</div>",unsafe_allow_html=True)
        if alerts.empty: st.caption("No deduplicated state alerts yet.")
        else: st.dataframe(alerts[[c for c in ["observed_at_utc","alert_type","message"] if c in alerts]].head(20),use_container_width=True,hide_index=True,height=390)

    st.markdown("<div class='mq-section'>Theme clusters · best expression first</div>",unsafe_allow_html=True)
    if active.empty:
        st.caption("No active theme cluster yet.")
    else:
        tmp=active.copy()
        tmp["opportunity_score"]=tmp["scores_json"].map(lambda x:_f(_safe_json(x).get("opportunity_score")))
        cluster=[]
        for theme,g in tmp.groupby("theme",dropna=False):
            g=g.sort_values("opportunity_score",ascending=False,na_position="last")
            syms=g["symbol"].astype(str).tolist()
            cluster.append({"Theme":theme,"Best expression":syms[0] if syms else "—","Second-best":syms[1] if len(syms)>1 else "—","Alternative":syms[2] if len(syms)>2 else "—","Candidates":len(g),"Best score":g.iloc[0].get("opportunity_score") if len(g) else math.nan})
        st.dataframe(pd.DataFrame(cluster).sort_values("Best score",ascending=False,na_position="last"),use_container_width=True,hide_index=True)


def render_learning_lab(st, memory: OpportunityMemory) -> None:
    install_memequant_style(st)
    rep=learning_report(memory)
    st.markdown("<div class='mq-titlebar'><div><div class='mq-title'>Research / Outcome Learning Lab</div><div class='mq-sub'>Continuous outcomes first. Production weights stay stable until a challenger wins chronological OOS validation.</div></div></div>",unsafe_allow_html=True)
    tabs=st.tabs(["PATTERN EXPECTANCY","TRUE WALK-FORWARD","BASELINES","FAILURES","MISSED WINNERS"])
    with tabs[0]:
        if rep["patterns"].empty: st.info("Insufficient mature stored outcomes. No confidence number is manufactured.")
        else: st.dataframe(rep["patterns"],use_container_width=True,hide_index=True)
    with tabs[1]:
        if rep["walk_forward"].empty: st.info("Not enough chronological event/outcome history for a valid expanding walk-forward yet.")
        else: st.dataframe(rep["walk_forward"],use_container_width=True,hide_index=True)
    with tabs[2]: st.dataframe(rep["baselines"],use_container_width=True,hide_index=True)
    with tabs[3]:
        if rep["failures"].empty: st.caption("No explicit false-positive reason has matured yet.")
        else: st.dataframe(rep["failures"],use_container_width=True,hide_index=True)
    with tabs[4]:
        if rep["missed"].empty: st.info("Missed-runner audit has no PIT-reconstructable cases yet. Future-return winners are not backfilled into fake historical signals.")
        else: st.dataframe(rep["missed"],use_container_width=True,hide_index=True)
