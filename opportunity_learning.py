from __future__ import annotations

import json
import math
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from opportunity_longitudinal import OpportunityMemory


def _f(x: Any) -> float:
    try:
        v=float(x); return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _confidence(n: int) -> str:
    if n >= 60: return "HIGH"
    if n >= 25: return "MEDIUM"
    return "LOW"


def _wilson(p: float, n: int, z: float = 1.96) -> Tuple[float,float]:
    if n<=0 or not math.isfinite(p): return (math.nan,math.nan)
    den=1+z*z/n; center=(p+z*z/(2*n))/den; half=z*math.sqrt((p*(1-p)+z*z/(4*n))/n)/den
    return max(0,center-half),min(1,center+half)


def pattern_statistics(events: pd.DataFrame, outcomes: pd.DataFrame, *, min_n: int = 5) -> pd.DataFrame:
    """Descriptive historical expectancy with hierarchical shrinkage.

    Exact narrow groups do not get high confidence from tiny N. Rates are shrunk
    toward a broader parent (global → market → sector/theme) with a transparent
    prior strength; raw continuous outcomes remain visible.
    """
    if events.empty or outcomes.empty: return pd.DataFrame()
    ev=events[[c for c in ["event_id","market","sector","theme","archetypes_json","macro_context_json"] if c in events]].copy()
    def macro_regime(v):
        if isinstance(v,dict): return str(v.get("regime") or v.get("action_label") or "UNKNOWN")
        try:
            j=json.loads(v) if v else {}; return str(j.get("regime") or j.get("action_label") or "UNKNOWN")
        except Exception: return "UNKNOWN"
    def first_arch(v):
        if isinstance(v,list): return str(v[0]) if v else "UNKNOWN"
        try:
            j=json.loads(v) if v else []; return str(j[0]) if isinstance(j,list) and j else "UNKNOWN"
        except Exception: return "UNKNOWN"
    ev["macro_regime"]=ev.get("macro_context_json",pd.Series(index=ev.index,dtype=object)).map(macro_regime)
    ev["archetype"]=ev.get("archetypes_json",pd.Series(index=ev.index,dtype=object)).map(first_arch)
    out=outcomes[outcomes.get("completed",0).astype(bool)].copy()
    if out.empty: return pd.DataFrame()
    def outcome_extra(v):
        if isinstance(v,dict): return v
        try: return json.loads(v) if v else {}
        except Exception: return {}
    extras=out.get("outcome_json",pd.Series(index=out.index,dtype=object)).map(outcome_extra)
    for key in ["success_plus10_before_minus5","success_plus20_before_minus10","success_plus50_before_minus15"]:
        out[key]=extras.map(lambda d: d.get(key) if isinstance(d,dict) else None)
    df=out.merge(ev,on="event_id",how="left")
    rows=[]; prior_strength=20.0
    for horizon,g0 in df.groupby("horizon"):
        global_hit=pd.to_numeric(g0["success_plus20_before_minus10"],errors="coerce").dropna()
        global_p=float(global_hit.mean()) if len(global_hit) else math.nan
        market_prior={k:float(pd.to_numeric(g["success_plus20_before_minus10"],errors="coerce").dropna().mean()) for k,g in g0.groupby("market") if pd.to_numeric(g["success_plus20_before_minus10"],errors="coerce").dropna().size}
        sector_prior={k:float(pd.to_numeric(g["success_plus20_before_minus10"],errors="coerce").dropna().mean()) for k,g in g0.groupby("sector") if pd.to_numeric(g["success_plus20_before_minus10"],errors="coerce").dropna().size}
        specs=[("GLOBAL",None),("MARKET","market"),("SECTOR","sector"),("REGIME","macro_regime"),("ARCHETYPE","archetype"),("THEME","theme")]
        for level,col in specs:
            groups=[("ALL",g0)] if col is None else list(g0.groupby(col,dropna=False))
            for name,g in groups:
                alpha=pd.to_numeric(g.get("alpha_vs_benchmark"),errors="coerce").dropna(); absret=pd.to_numeric(g.get("absolute_return"),errors="coerce").dropna(); mae=pd.to_numeric(g.get("mae"),errors="coerce").dropna()
                if len(absret)<min_n: continue
                h10=pd.to_numeric(g["success_plus10_before_minus5"],errors="coerce").dropna(); h20=pd.to_numeric(g["success_plus20_before_minus10"],errors="coerce").dropna(); h50=pd.to_numeric(g["success_plus50_before_minus15"],errors="coerce").dropna()
                p20=float(h20.mean()) if len(h20) else math.nan; lo,hi=_wilson(p20,len(h20)) if math.isfinite(p20) else (math.nan,math.nan)
                parent=global_p; parent_name="GLOBAL"
                if level in {"SECTOR","THEME","ARCHETYPE","REGIME"}:
                    mkts=g["market"].dropna().astype(str).unique().tolist()
                    if len(mkts)==1 and mkts[0] in market_prior: parent=market_prior[mkts[0]]; parent_name=f"MARKET:{mkts[0]}"
                if level=="THEME":
                    sectors=g["sector"].dropna().astype(str).unique().tolist()
                    if len(sectors)==1 and sectors[0] in sector_prior: parent=sector_prior[sectors[0]]; parent_name=f"SECTOR:{sectors[0]}"
                shrunk=((len(h20)*p20 + prior_strength*parent)/(len(h20)+prior_strength)) if len(h20) and math.isfinite(p20) and math.isfinite(parent) else p20
                outperf=(pd.to_numeric(g.get("alpha_vs_benchmark"),errors="coerce")>0).dropna()
                rows.append({
                    "level":level,"group":str(name),"horizon":horizon,"n":int(len(absret)),"sample_confidence":_confidence(len(absret)),
                    "shrink_parent":parent_name,"median_return":float(absret.median()),"median_alpha":float(alpha.median()) if len(alpha) else math.nan,
                    "median_mae":float(mae.median()) if len(mae) else math.nan,
                    "p_plus10_before_minus5":float(h10.mean()) if len(h10) else math.nan,
                    "p_plus20_before_minus10":p20,"p_plus50_before_minus15":float(h50.mean()) if len(h50) else math.nan,
                    "p_outperform_benchmark":float(outperf.mean()) if len(outperf) else math.nan,
                    "shrunk_p_plus20_before_minus10":shrunk,"p20_ci_low":lo,"p20_ci_high":hi,
                })
    return pd.DataFrame(rows)


def chronological_walk_forward(events: pd.DataFrame, outcomes: pd.DataFrame, *, horizon: str = "3M", min_train: int = 20) -> pd.DataFrame:
    """True chronological calibration report; no random split.

    This is a calibration audit over stored event scores/outcomes. It does not alter production logic.
    """
    if events.empty or outcomes.empty: return pd.DataFrame()
    out=outcomes[(outcomes.get("horizon","")==horizon) & outcomes.get("completed",0).astype(bool)].copy()
    if out.empty: return pd.DataFrame()
    cols=["event_id","first_seen_time","market","scores_json"]
    ev=events[[c for c in cols if c in events]].copy()
    df=ev.merge(out[[c for c in ["event_id","absolute_return","alpha_vs_benchmark","mae","peak_return"] if c in out]],on="event_id",how="inner")
    if df.empty: return pd.DataFrame()
    df["first_seen_time"]=pd.to_datetime(df["first_seen_time"],utc=True,errors="coerce"); df=df.sort_values("first_seen_time")
    def score_of(x):
        if isinstance(x,dict): return _f(x.get("opportunity_score"))
        try: return _f(json.loads(x).get("opportunity_score"))
        except Exception: return math.nan
    df["score"]=df.get("scores_json",pd.Series(index=df.index,dtype=object)).map(score_of)
    df["win"]=(pd.to_numeric(df.get("alpha_vs_benchmark"),errors="coerce")>0).astype(float)
    rows=[]
    years=sorted(x for x in df["first_seen_time"].dt.year.dropna().unique())
    for test_year in years:
        train=df[df["first_seen_time"].dt.year < test_year].dropna(subset=["score","win"])
        test=df[df["first_seen_time"].dt.year == test_year].dropna(subset=["score","win"])
        if len(train)<min_train or test.empty: continue
        q=np.nanquantile(train["score"],[.33,.66])
        def bucket(s): return "LOW" if s<q[0] else ("MID" if s<q[1] else "HIGH")
        train=train.copy(); test=test.copy(); train["bucket"]=train["score"].map(bucket); test["bucket"]=test["score"].map(bucket)
        cal=train.groupby("bucket")["win"].mean().to_dict()
        test["p_train"]=test["bucket"].map(cal)
        brier=float(np.mean((test["p_train"]-test["win"])**2)) if test["p_train"].notna().any() else math.nan
        rows.append({
            "train_end":int(test_year-1),"test_year":int(test_year),"train_n":len(train),"test_n":len(test),
            "test_win_rate":float(test["win"].mean()),"test_median_alpha":float(pd.to_numeric(test.get("alpha_vs_benchmark"),errors="coerce").median()),
            "brier":brier,"method":"expanding chronological; score buckets learned on prior years only",
        })
    return pd.DataFrame(rows)


def baseline_comparison(events: pd.DataFrame, outcomes: pd.DataFrame, *, horizon: str = "3M") -> pd.DataFrame:
    """Compare stored Opportunity Engine outcomes to simple *available* baselines.

    Baselines that require unavailable PIT features are reported as DATA GATED rather than fabricated.
    """
    if events.empty or outcomes.empty:
        return pd.DataFrame([{"baseline":"Existing Opportunity Engine","status":"NO MATURE OUTCOMES","median_alpha":math.nan,"n":0}])
    out=outcomes[(outcomes.get("horizon","")==horizon) & outcomes.get("completed",0).astype(bool)].copy()
    if out.empty:
        return pd.DataFrame([{"baseline":"Existing Opportunity Engine","status":"NO MATURE OUTCOMES","median_alpha":math.nan,"n":0}])
    alpha=pd.to_numeric(out.get("alpha_vs_benchmark"),errors="coerce").dropna()
    rows=[{"baseline":"Existing Opportunity Engine","status":"OBSERVED STORED EVENTS","median_alpha":float(alpha.median()) if len(alpha) else math.nan,"n":len(alpha)}]
    for name in ["Strongest 6M performer","Highest earnings growth","Cheapest valuation","Highest analyst revisions","Sector momentum"]:
        rows.append({"baseline":name,"status":"PIT BASELINE DATA GATED UNTIL HISTORICAL FEATURE STORE IS POPULATED","median_alpha":math.nan,"n":0})
    return pd.DataFrame(rows)


def learning_report(memory: OpportunityMemory) -> Dict[str, Any]:
    events=memory.events_frame(limit=5000); outcomes=memory.outcomes_frame(); failures=memory.failures_frame(); missed=memory.missed_frame()
    states=memory.states_frame(limit=5000)
    report={"events":events,"outcomes":outcomes,"failures":failures,"missed":missed,"states":states}
    report["patterns"]=pattern_statistics(events,outcomes)
    report["walk_forward"]=chronological_walk_forward(events,outcomes)
    report["baselines"]=baseline_comparison(events,outcomes)
    return report


def write_periodic_learning_reports(memory: OpportunityMemory, state_dir: Any, now: Any = None) -> Dict[str,str]:
    """Write deterministic daily/weekly learning summaries from stored evidence only."""
    from pathlib import Path
    ts=pd.Timestamp(now or pd.Timestamp.utcnow())
    if ts.tzinfo is None: ts=ts.tz_localize('UTC')
    state=Path(state_dir); outdir=state/'learning_reports'; outdir.mkdir(parents=True,exist_ok=True)
    rep=learning_report(memory); counts=memory.counts()
    recent_states=rep['states'].copy()
    if not recent_states.empty:
        recent_states['observed_at_utc']=pd.to_datetime(recent_states['observed_at_utc'],utc=True,errors='coerce')
    failures=rep['failures']; missed=rep['missed']
    def build(label: str, start: pd.Timestamp) -> str:
        ss=recent_states[recent_states['observed_at_utc']>=start] if not recent_states.empty else pd.DataFrame()
        lines=[f"# Opportunity Learning {label}","",f"As of: {ts.isoformat()}","",f"- Active opportunities: {counts['active']}",f"- Total frozen events: {counts['events']}",f"- Mature outcomes: {counts['outcomes']}",f"- Stored failures: {counts['failures']}",f"- Missed-runner audits: {counts['missed']}",""]
        lines += ["## State changes",""]
        if ss.empty: lines += ["No stored state changes in this window.",""]
        else:
            for _,r in ss.head(30).iterrows(): lines.append(f"- {r.get('observed_at_utc')} · {r.get('event_id')} · {r.get('lifecycle_state')} · {r.get('reason','')}")
            lines.append("")
        lines += ["## Learning status",""]
        if rep['patterns'].empty: lines.append("Historical expectancy: insufficient mature samples; no confidence number produced.")
        else: lines.append(f"Historical expectancy rows available: {len(rep['patterns'])}.")
        if rep['walk_forward'].empty: lines.append("Walk-forward: insufficient chronological history for a valid test window.")
        else: lines.append(f"Walk-forward windows completed: {len(rep['walk_forward'])}.")
        lines += ["", "Production weights are unchanged. Any challenger requires chronological OOS promotion."]
        return "\n".join(lines)+"\n"
    day=ts.strftime('%Y-%m-%d'); iso=ts.isocalendar(); week=f"{iso.year}-W{iso.week:02d}"
    daily=outdir/f"daily_{day}.md"; weekly=outdir/f"weekly_{week}.md"
    if not daily.exists(): daily.write_text(build('DAILY',ts-pd.Timedelta(days=1)),encoding='utf-8')
    if not weekly.exists(): weekly.write_text(build('WEEKLY',ts-pd.Timedelta(days=7)),encoding='utf-8')
    return {'daily':str(daily),'weekly':str(weekly)}
