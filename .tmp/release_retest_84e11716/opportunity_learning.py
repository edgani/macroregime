from __future__ import annotations

import json
import math
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

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


def _json_obj(v: Any, default):
    if isinstance(v,type(default)): return v
    try:
        j=json.loads(v) if v else default
        return j if isinstance(j,type(default)) else default
    except Exception:
        return default


def _outcome_extra(v: Any) -> Dict[str,Any]:
    return _json_obj(v,{})


def pattern_statistics(events: pd.DataFrame, outcomes: pd.DataFrame, *, min_n: int = 5) -> pd.DataFrame:
    """Descriptive expectancy with explicit sample size + hierarchical shrinkage.

    Missing relative labels remain missing.  In particular, NaN benchmark alpha is not
    converted into a false loss when computing outperformance rates.
    """
    if events.empty or outcomes.empty: return pd.DataFrame()
    ev=events[[c for c in ["event_id","market","sector","theme","archetypes_json","macro_context_json"] if c in events]].copy()
    def macro_regime(v):
        j=v if isinstance(v,dict) else _json_obj(v,{})
        return str(j.get("regime") or j.get("action_label") or "UNKNOWN")
    def first_arch(v):
        j=v if isinstance(v,list) else _json_obj(v,[])
        return str(j[0]) if j else "UNKNOWN"
    ev["macro_regime"]=ev.get("macro_context_json",pd.Series(index=ev.index,dtype=object)).map(macro_regime)
    ev["archetype"]=ev.get("archetypes_json",pd.Series(index=ev.index,dtype=object)).map(first_arch)
    out=outcomes[pd.to_numeric(outcomes.get("completed",0),errors="coerce").fillna(0).astype(bool)].copy()
    if out.empty: return pd.DataFrame()
    extras=out.get("outcome_json",pd.Series(index=out.index,dtype=object)).map(_outcome_extra)
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
                alpha=pd.to_numeric(g.get("alpha_vs_benchmark"),errors="coerce").dropna()
                absret=pd.to_numeric(g.get("absolute_return"),errors="coerce").dropna()
                mae=pd.to_numeric(g.get("mae"),errors="coerce").dropna()
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
                alpha_valid=pd.to_numeric(g.get("alpha_vs_benchmark"),errors="coerce").dropna()
                sector_alpha=pd.to_numeric(g["alpha_vs_sector"],errors="coerce").dropna() if "alpha_vs_sector" in g.columns else pd.Series(dtype=float)
                outperf=(alpha_valid>0); sector_outperf=(sector_alpha>0)
                rows.append({
                    "level":level,"group":str(name),"horizon":horizon,"n":int(len(absret)),"relative_n":int(len(alpha_valid)),"sample_confidence":_confidence(len(absret)),
                    "shrink_parent":parent_name,"median_return":float(absret.median()),"median_alpha":float(alpha.median()) if len(alpha) else math.nan,
                    "median_mae":float(mae.median()) if len(mae) else math.nan,
                    "p_plus10_before_minus5":float(h10.mean()) if len(h10) else math.nan,
                    "p_plus20_before_minus10":p20,"p_plus50_before_minus15":float(h50.mean()) if len(h50) else math.nan,
                    "p_outperform_benchmark":float(outperf.mean()) if len(outperf) else math.nan,
                    "p_outperform_sector":float(sector_outperf.mean()) if len(sector_outperf) else math.nan,
                    "sector_relative_n":int(len(sector_alpha)),
                    "shrunk_p_plus20_before_minus10":shrunk,"p20_ci_low":lo,"p20_ci_high":hi,
                })
    return pd.DataFrame(rows)


def _label_available(outcome_row: Mapping[str,Any]) -> pd.Timestamp:
    ex=_outcome_extra(outcome_row.get("outcome_json"))
    raw=ex.get("label_available_at_utc") or outcome_row.get("horizon_end_utc")
    return pd.to_datetime(raw,utc=True,errors="coerce")


def chronological_walk_forward(events: pd.DataFrame, outcomes: pd.DataFrame, *, horizon: str = "3M", min_train: int = 20) -> pd.DataFrame:
    """Expanding chronological calibration with label-availability embargo.

    A training event is eligible only if its outcome label was actually observable by
    the start of the test year.  This closes the classic Dec-event/3M-label leak into a
    January test window.  Missing benchmark alpha stays UNKNOWN and is excluded.
    """
    if events.empty or outcomes.empty: return pd.DataFrame()
    out=outcomes[(outcomes.get("horizon","")==horizon) & pd.to_numeric(outcomes.get("completed",0),errors="coerce").fillna(0).astype(bool)].copy()
    if out.empty: return pd.DataFrame()
    out["label_available_at_utc"]=[_label_available(r) for _,r in out.iterrows()]
    cols=["event_id","first_seen_time","market","scores_json"]
    ev=events[[c for c in cols if c in events]].copy()
    mcols=[c for c in ["event_id","absolute_return","alpha_vs_benchmark","mae","peak_return","label_available_at_utc"] if c in out]
    df=ev.merge(out[mcols],on="event_id",how="inner")
    if df.empty: return pd.DataFrame()
    df["first_seen_time"]=pd.to_datetime(df["first_seen_time"],utc=True,errors="coerce")
    df["label_available_at_utc"]=pd.to_datetime(df["label_available_at_utc"],utc=True,errors="coerce")
    def score_of(x):
        j=x if isinstance(x,dict) else _json_obj(x,{})
        return _f(j.get("opportunity_score"))
    df["score"]=df.get("scores_json",pd.Series(index=df.index,dtype=object)).map(score_of)
    alpha=pd.to_numeric(df.get("alpha_vs_benchmark"),errors="coerce")
    df["win"]=alpha.map(lambda x: 1.0 if math.isfinite(_f(x)) and float(x)>0 else (0.0 if math.isfinite(_f(x)) else math.nan))
    df=df.sort_values("first_seen_time")
    rows=[]
    years=sorted(int(x) for x in df["first_seen_time"].dt.year.dropna().unique())
    for test_year in years:
        cutoff=pd.Timestamp(f"{test_year}-01-01",tz="UTC")
        train=df[(df["first_seen_time"]<cutoff) & (df["label_available_at_utc"]<=cutoff)].dropna(subset=["score","win","label_available_at_utc"])
        test=df[(df["first_seen_time"]>=cutoff) & (df["first_seen_time"]<pd.Timestamp(f"{test_year+1}-01-01",tz="UTC"))].dropna(subset=["score","win"])
        if len(train)<min_train or test.empty: continue
        q=np.nanquantile(train["score"],[.33,.66])
        def bucket(s): return "LOW" if s<q[0] else ("MID" if s<q[1] else "HIGH")
        train=train.copy(); test=test.copy(); train["bucket"]=train["score"].map(bucket); test["bucket"]=test["score"].map(bucket)
        cal=train.groupby("bucket")["win"].agg(["mean","count"])
        # Small buckets are not allowed to manufacture strong probabilities; shrink to
        # the full training rate with a transparent prior strength.
        global_rate=float(train["win"].mean()); prior_strength=20.0
        probs={b:(float(r["count"])*float(r["mean"])+prior_strength*global_rate)/(float(r["count"])+prior_strength) for b,r in cal.iterrows()}
        test["p_train"]=test["bucket"].map(probs)
        valid=test.dropna(subset=["p_train","win"])
        brier=float(np.mean((valid["p_train"]-valid["win"])**2)) if len(valid) else math.nan
        rows.append({
            "train_cutoff":cutoff.isoformat(),"train_end":int(train["first_seen_time"].dt.year.max()),"test_year":int(test_year),"train_n":len(train),"test_n":len(test),
            "test_win_rate":float(test["win"].mean()),"test_median_alpha":float(pd.to_numeric(test.get("alpha_vs_benchmark"),errors="coerce").median()),
            "brier":brier,"method":"expanding chronological; labels embargoed until observable; score buckets learned on prior data only",
        })
    return pd.DataFrame(rows)


def baseline_comparison(events: pd.DataFrame, outcomes: pd.DataFrame, *, horizon: str = "3M", baseline_outcomes: Optional[pd.DataFrame]=None) -> pd.DataFrame:
    """Compare against prospective PIT baseline selections when they have matured."""
    rows=[]
    if not events.empty and not outcomes.empty:
        out=outcomes[(outcomes.get("horizon","")==horizon) & pd.to_numeric(outcomes.get("completed",0),errors="coerce").fillna(0).astype(bool)].copy()
        alpha=pd.to_numeric(out.get("alpha_vs_benchmark"),errors="coerce").dropna() if not out.empty else pd.Series(dtype=float)
        rows.append({"baseline":"Opportunity Engine","status":"OBSERVED STORED EVENTS" if len(alpha) else "NO RELATIVE MATURE OUTCOMES","median_alpha":float(alpha.median()) if len(alpha) else math.nan,"n":int(len(alpha))})
    else:
        rows.append({"baseline":"Opportunity Engine","status":"NO MATURE OUTCOMES","median_alpha":math.nan,"n":0})
    names=["Strongest 6M performer","Highest earnings growth","Cheapest valuation","Highest analyst revisions","Sector momentum"]
    bo=baseline_outcomes if baseline_outcomes is not None else pd.DataFrame()
    for name in names:
        g=bo[(bo.get("baseline",pd.Series(dtype=str))==name) & (bo.get("horizon",pd.Series(dtype=str))==horizon)] if not bo.empty else pd.DataFrame()
        a=pd.to_numeric(g.get("alpha_vs_benchmark"),errors="coerce").dropna() if not g.empty else pd.Series(dtype=float)
        rows.append({"baseline":name,"status":"PROSPECTIVE PIT SCANNED-UNIVERSE" if len(a) else "PROSPECTIVE PIT SCANNED-UNIVERSE DATA ACCUMULATING / GATED","median_alpha":float(a.median()) if len(a) else math.nan,"n":int(len(a))})
    return pd.DataFrame(rows)


def runner_recall_report(events: pd.DataFrame, missed: pd.DataFrame) -> pd.DataFrame:
    """Recall denominator comes only from explicitly audited runner cohorts.

    The system never infers that an un-audited future winner was 'found'.  A cohort row
    is either a stored miss classification or a stored FOUND classification created by
    the prospective runner auditor.
    """
    if missed is None or missed.empty:
        return pd.DataFrame([{"runner_definition":"ALL","audited_runners":0,"found":0,"missed":0,"runner_recall":math.nan,"status":"INSUFFICIENT AUDITED RUNNERS"}])
    x=missed.copy(); x["classification"]=x.get("classification","").astype(str).str.upper()
    rows=[]
    for definition,g in x.groupby("runner_definition",dropna=False):
        found=int(g["classification"].str.startswith("FOUND").sum())
        miss=int((~g["classification"].str.startswith("FOUND")).sum())
        n=found+miss
        rows.append({"runner_definition":definition,"audited_runners":n,"found":found,"missed":miss,"runner_recall":found/n if n else math.nan,"status":"OBSERVED AUDIT" if n else "INSUFFICIENT"})
    return pd.DataFrame(rows)


def learning_report(memory: OpportunityMemory, *, baseline_outcomes: Optional[pd.DataFrame]=None) -> Dict[str, Any]:
    events=memory.events_frame(limit=5000); outcomes=memory.outcomes_frame(); failures=memory.failures_frame(); missed=memory.missed_frame(); states=memory.states_frame(limit=5000)
    report={"events":events,"outcomes":outcomes,"failures":failures,"missed":missed,"states":states}
    report["patterns"]=pattern_statistics(events,outcomes)
    report["walk_forward"]=chronological_walk_forward(events,outcomes)
    report["baselines"]=baseline_comparison(events,outcomes,baseline_outcomes=baseline_outcomes)
    report["runner_recall"]=runner_recall_report(events,missed)
    return report


def write_periodic_learning_reports(memory: OpportunityMemory, state_dir: Any, now: Any = None, baseline_outcomes: Optional[pd.DataFrame] = None) -> Dict[str,str]:
    """Write deterministic daily/weekly learning summaries from stored evidence only."""
    from pathlib import Path
    ts=pd.Timestamp(now or pd.Timestamp.utcnow())
    if ts.tzinfo is None: ts=ts.tz_localize('UTC')
    state=Path(state_dir); outdir=state/'learning_reports'; outdir.mkdir(parents=True,exist_ok=True)
    rep=learning_report(memory,baseline_outcomes=baseline_outcomes); counts=memory.counts()
    recent_states=rep['states'].copy()
    if not recent_states.empty: recent_states['observed_at_utc']=pd.to_datetime(recent_states['observed_at_utc'],utc=True,errors='coerce')
    def build(label: str, start: pd.Timestamp) -> str:
        ss=recent_states[recent_states['observed_at_utc']>=start] if not recent_states.empty else pd.DataFrame()
        lines=[f"# Opportunity Learning {label}","",f"As of: {ts.isoformat()}","",f"- Active opportunities: {counts['active']}",f"- Total frozen events: {counts['events']}",f"- Mature outcomes: {counts['outcomes']}",f"- Stored failures: {counts['failures']}",f"- Missed/runner audits: {counts['missed']}",""]
        lines += ["## State changes",""]
        if ss.empty: lines += ["No stored state changes in this window.",""]
        else:
            for _,r in ss.head(30).iterrows(): lines.append(f"- {r.get('observed_at_utc')} · {r.get('event_id')} · {r.get('lifecycle_state')} · {r.get('reason','')}")
            lines.append("")
        lines += ["## Learning status",""]
        lines.append("Historical expectancy: insufficient mature samples; no confidence number produced." if rep['patterns'].empty else f"Historical expectancy rows available: {len(rep['patterns'])}.")
        lines.append("Walk-forward: insufficient chronological history for a valid test window." if rep['walk_forward'].empty else f"Walk-forward windows completed: {len(rep['walk_forward'])}.")
        rr=rep['runner_recall']; lines.append("Runner recall: insufficient audited runner cohorts." if rr.empty or int(pd.to_numeric(rr.get('audited_runners'),errors='coerce').fillna(0).sum())==0 else f"Runner cohorts audited: {int(pd.to_numeric(rr['audited_runners'],errors='coerce').fillna(0).sum())}.")
        lines += ["", "## What worked", ""]
        pats=rep['patterns']
        if pats.empty: lines.append("No mature pattern has enough sample support yet.")
        else:
            pg=pats[(pats.get('level','')=='GLOBAL')].copy() if 'level' in pats else pats.copy()
            for _,r in pg.head(5).iterrows(): lines.append(f"- {r.get('horizon')} · N={r.get('n')} · median alpha={r.get('median_alpha')} · sample={r.get('sample_confidence')}")
        lines += ["", "## What failed", ""]
        ff=rep['failures']
        if ff.empty: lines.append("No explicit matured failure taxonomy records in this window.")
        else:
            for code,n in ff.get('failure_code',pd.Series(dtype=str)).astype(str).value_counts().head(8).items(): lines.append(f"- {code}: {n}")
        lines += ["", "## Missed winners / runner audit", ""]
        mm=rep['missed']
        if mm.empty: lines.append("No prospectively audited runner case has matured yet.")
        else:
            for code,n in mm.get('classification',pd.Series(dtype=str)).astype(str).value_counts().head(8).items(): lines.append(f"- {code}: {n}")
        lines += ["", "## Baseline comparison", ""]
        bb=rep['baselines']
        for _,r in bb.iterrows(): lines.append(f"- {r.get('baseline')}: {r.get('status')} · N={r.get('n')} · median alpha={r.get('median_alpha')}")
        lines += ["", "Production weights are unchanged. Any challenger requires chronological OOS promotion."]
        return "\n".join(lines)+"\n"
    day=ts.strftime('%Y-%m-%d'); iso=ts.isocalendar(); week=f"{iso.year}-W{iso.week:02d}"
    daily=outdir/f"daily_{day}.md"; weekly=outdir/f"weekly_{week}.md"
    if not daily.exists(): daily.write_text(build('DAILY',ts-pd.Timedelta(days=1)),encoding='utf-8')
    if not weekly.exists(): weekly.write_text(build('WEEKLY',ts-pd.Timedelta(days=7)),encoding='utf-8')
    return {'daily':str(daily),'weekly':str(weekly)}
