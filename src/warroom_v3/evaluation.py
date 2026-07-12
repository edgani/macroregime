from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import json, math, random

from .hashing import canonical_hash
from .storage import atomic_replace, load_jsonl


def _rank(values: list[float]) -> list[float]:
    order=sorted(range(len(values)),key=lambda i:values[i])
    ranks=[0.0]*len(values); i=0
    while i<len(order):
        j=i+1
        while j<len(order) and values[order[j]]==values[order[i]]: j+=1
        avg=(i+j-1)/2+1
        for k in range(i,j): ranks[order[k]]=avg
        i=j
    return ranks


def pearson(x: list[float], y: list[float]) -> float | None:
    if len(x)!=len(y) or len(x)<3: return None
    mx=sum(x)/len(x); my=sum(y)/len(y)
    dx=[v-mx for v in x]; dy=[v-my for v in y]
    den=math.sqrt(sum(v*v for v in dx)*sum(v*v for v in dy))
    return None if den==0 else sum(a*b for a,b in zip(dx,dy))/den


def spearman(x: list[float], y: list[float]) -> float | None:
    return pearson(_rank(x),_rank(y))


def block_bootstrap_ci(x: list[float], y: list[float], *, reps: int=300, seed: int=20260712) -> tuple[float,float] | None:
    n=len(x)
    if n<20: return None
    block=max(2,int(math.sqrt(n)))
    rng=random.Random(seed); stats=[]
    for _ in range(reps):
        idx=[]
        while len(idx)<n:
            start=rng.randrange(n)
            idx.extend((start+j)%n for j in range(block))
        idx=idx[:n]
        value=spearman([x[i] for i in idx],[y[i] for i in idx])
        if value is not None and math.isfinite(value): stats.append(value)
    if len(stats)<reps//2: return None
    stats.sort(); return stats[int(.025*(len(stats)-1))],stats[int(.975*(len(stats)-1))]


def interval_score(y: float, lo: float, hi: float, alpha: float=.32) -> float:
    if not lo<=hi: raise ValueError('invalid interval')
    score=hi-lo
    if y<lo: score+=(2/alpha)*(lo-y)
    elif y>hi: score+=(2/alpha)*(y-hi)
    return score


@dataclass(frozen=True)
class ScopeEvaluation:
    scope_id: str
    horizon_bars: int
    observations: int
    verdict: str
    mqa: dict
    momentum: dict
    reason_codes: tuple[str,...]


def _load_tickets(root: Path) -> dict[str,dict]:
    out={}
    for entry in load_jsonl(root/'runtime/observations/journal.jsonl'):
        path=root/'runtime'/entry['ticket_path']
        if path.exists(): out[entry['ticket_sha256']]=json.loads(path.read_text(encoding='utf-8'))
    return out


def _finite(value) -> bool:
    return isinstance(value,(int,float)) and math.isfinite(float(value))


def evaluate_scope(rows: list[tuple[dict,dict]], *, scope_id: str, horizon: int, min_n: int) -> ScopeEvaluation:
    reasons=[]; n=len(rows)
    fixed_hits=[]; conformal_hits=[]; fixed_scores=[]; conformal_scores=[]
    axes={k:([],[]) for k in ('trend_context','acceleration','release_rank','signed_persistence','path_efficiency','noise_ratio','exhaustion_risk')}
    for ticket,outcome in rows:
        target=float(outcome['target_close']); mqa=ticket['component_states']['mqa_benchmarks']; mom=ticket['component_states']['momentum_axes']
        flo,fhi=mqa.get('fixed_lower'),mqa.get('fixed_upper'); clo,chi=mqa.get('conformal_lower'),mqa.get('conformal_upper')
        if _finite(flo) and _finite(fhi): fixed_hits.append(float(flo)<=target<=float(fhi)); fixed_scores.append(interval_score(target,float(flo),float(fhi)))
        if _finite(clo) and _finite(chi): conformal_hits.append(float(clo)<=target<=float(chi)); conformal_scores.append(interval_score(target,float(clo),float(chi)))
        ret=float(outcome['forward_return'])
        for key,(x,y) in axes.items():
            value=mom.get(key)
            if _finite(value): x.append(float(value)); y.append(ret)
    mqa_result={
        'fixed_n':len(fixed_scores),'fixed_coverage':None if not fixed_hits else sum(fixed_hits)/len(fixed_hits),
        'fixed_mean_interval_score':None if not fixed_scores else sum(fixed_scores)/len(fixed_scores),
        'conformal_n':len(conformal_scores),'conformal_coverage':None if not conformal_hits else sum(conformal_hits)/len(conformal_hits),
        'conformal_mean_interval_score':None if not conformal_scores else sum(conformal_scores)/len(conformal_scores),
        'target_coverage':.68,
    }
    momentum_result={}
    for key,(x,y) in axes.items():
        rho=spearman(x,y); ci=block_bootstrap_ci(x,y) if len(x)>=min_n else None
        momentum_result[key]={'n':len(x),'spearman':rho,'block_bootstrap_ci95':ci}
    if n<min_n:
        verdict='INSUFFICIENT_PROSPECTIVE_DATA'; reasons.append(f'MINIMUM_REQUIRED:{min_n}')
    else:
        mqa_ok=(mqa_result['conformal_coverage'] is not None and abs(mqa_result['conformal_coverage']-.68)<=.05 and
                mqa_result['fixed_mean_interval_score'] is not None and mqa_result['conformal_mean_interval_score']<=mqa_result['fixed_mean_interval_score'])
        significant=[k for k,v in momentum_result.items() if v['block_bootstrap_ci95'] and (v['block_bootstrap_ci95'][0]>0 or v['block_bootstrap_ci95'][1]<0)]
        verdict='RESEARCH_DIAGNOSTIC_PASS' if mqa_ok or significant else 'NO_INCREMENTAL_EVIDENCE'
        if not mqa_ok: reasons.append('MQA_DID_NOT_BEAT_FIXED_ATR_GATE')
        if not significant: reasons.append('MOMENTUM_AXES_NO_BLOCK_ROBUST_ASSOCIATION')
    reasons.extend(['NO_DECISION_POLICY_EVIDENCE','NO_PORTFOLIO_POLICY_EVIDENCE','PAPER_LIVE_NOT_AUTO_PROMOTED'])
    return ScopeEvaluation(scope_id,horizon,n,verdict,mqa_result,momentum_result,tuple(reasons))


def build_evaluation_report(root: str | Path, *, min_n_intraday: int=200, min_n_daily: int=100) -> dict:
    root=Path(root); tickets=_load_tickets(root); outcomes=load_jsonl(root/'runtime/outcomes/journal.jsonl')
    grouped={}
    for outcome in outcomes:
        ticket=tickets.get(outcome['ticket_sha256'])
        if ticket is None: continue
        scope=f"{outcome['asset']}:{outcome['timeframe']}"; horizon=int(outcome['horizon_bars'])
        grouped.setdefault((scope,horizon),[]).append((ticket,outcome))
    evaluations=[]
    for (scope,horizon),rows in sorted(grouped.items()):
        timeframe=scope.split(':',1)[1]; min_n=min_n_daily if timeframe=='1d' else min_n_intraday
        evaluations.append(asdict(evaluate_scope(rows,scope_id=scope,horizon=horizon,min_n=min_n)))
    report={
        'report_id':'WRV3-PROSPECTIVE-EVALUATION','claim_ceiling':'RESEARCH_EVIDENCE_ONLY',
        'scope_evaluations':evaluations,'outcomes_seen':len(outcomes),'tickets_seen':len(tickets),
        'paper_eligible':False,'live_eligible':False,
        'global_blockers':['NO_VALIDATED_DECISION_POLICY','NO_VALIDATED_PORTFOLIO_POLICY','NO_CALIBRATED_ACTION_PROBABILITY'],
    }
    report['report_hash']=canonical_hash(report)
    atomic_replace(root/'runtime/evaluation/latest.json',json.dumps(report,sort_keys=True,indent=2).encode())
    return report
