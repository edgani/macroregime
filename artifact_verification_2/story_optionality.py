from __future__ import annotations

import math
from typing import Any, Dict, Mapping

import numpy as np
import pandas as pd


def _f(x: Any) -> float:
    try:
        v=float(x)
        return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _clip01(x: float) -> float:
    return max(0.0,min(1.0,float(x))) if math.isfinite(_f(x)) else math.nan


def _lin(x: float, lo: float, hi: float) -> float:
    x=_f(x)
    if not math.isfinite(x): return math.nan
    if hi==lo: return math.nan
    return _clip01((x-lo)/(hi-lo))


def _mean_known(*vals: float) -> float:
    xs=[_f(x) for x in vals if math.isfinite(_f(x))]
    return float(np.mean(xs)) if xs else math.nan


def classify_loss_type(row: Mapping[str, Any]) -> str:
    """Descriptive loss classification. Loss itself is never considered bullish."""
    nm=_f(row.get('net_margin')); eps=_f(row.get('eps_ttm'))
    loss=(math.isfinite(nm) and nm < 0) or (math.isfinite(eps) and eps < 0)
    if not loss:
        return 'PROFITABLE / NOT A LOSS STORY'

    rev=_f(row.get('revenue_growth_yoy'))
    gm=_f(row.get('gross_margin_change'))
    nmchg=_f(row.get('net_margin_change'))
    fcf=_f(row.get('fcf_ttm'))
    fcfg=_f(row.get('fcf_growth_yoy'))
    rd=_f(row.get('rd_to_revenue'))
    capex=_f(row.get('capex_to_revenue'))

    improving=sum([
        math.isfinite(rev) and rev > 0.08,
        math.isfinite(gm) and gm > 0.01,
        math.isfinite(nmchg) and nmchg > 0.02,
        math.isfinite(fcfg) and fcfg > 0.10,
        math.isfinite(fcf) and fcf > 0,
    ])
    deteriorating=sum([
        math.isfinite(rev) and rev < -0.05,
        math.isfinite(gm) and gm < -0.02,
        math.isfinite(nmchg) and nmchg < -0.03,
        math.isfinite(fcfg) and fcfg < -0.20,
    ])
    investment_intensity=max([x for x in [rd,capex] if math.isfinite(x)] or [0.0])

    if deteriorating >= 2 and improving == 0:
        return 'STRUCTURAL / BAD LOSS'
    if improving >= 3:
        return 'TURNAROUND LOSS'
    if improving >= 2 and investment_intensity >= 0.08:
        return 'INVESTMENT-LED LOSS'
    if improving >= 1:
        return 'EARLY INFLECTION / UNCLEAR LOSS'
    return 'UNCLASSIFIED LOSS'


def financing_risk(row: Mapping[str, Any]) -> Dict[str, Any]:
    cash=_f(row.get('total_cash'))
    debt=_f(row.get('total_debt'))
    fcf=_f(row.get('fcf_ttm'))
    shares_yoy=_f(row.get('shares_change_yoy'))

    runway=math.nan
    if math.isfinite(cash) and cash >= 0:
        if math.isfinite(fcf) and fcf < 0:
            runway=cash/abs(fcf) if abs(fcf)>1e-12 else math.nan
        elif math.isfinite(fcf) and fcf >= 0:
            runway=99.0
    debt_cash=debt/cash if math.isfinite(debt) and math.isfinite(cash) and cash>0 else math.nan

    risks=[]
    if math.isfinite(runway) and runway < 1.0: risks.append('cash runway <1y')
    elif math.isfinite(runway) and runway < 2.0: risks.append('cash runway <2y')
    if math.isfinite(debt_cash) and debt_cash > 2.0: risks.append('debt >2x cash')
    if math.isfinite(shares_yoy) and shares_yoy > 0.10: risks.append('share count +>10% YoY')
    elif math.isfinite(shares_yoy) and shares_yoy > 0.05: risks.append('share count +>5% YoY')

    if any(x in ' '.join(risks) for x in ['<1y','>2x','>10%']): state='HIGH'
    elif risks: state='MEDIUM'
    elif any(math.isfinite(x) for x in [cash,debt,fcf,shares_yoy]): state='LOW / MANAGEABLE'
    else: state='DATA GATED'
    return {'cash_runway_years':runway,'debt_to_cash':debt_cash,'financing_risk':state,'financing_risk_flags':'; '.join(risks) if risks else 'none detected from available fields'}


def analyst_revision_signal(row: Mapping[str, Any]) -> Dict[str, Any]:
    """US-only current analyst revision signal. Market Memory makes it PIT from first observation onward."""
    cur=_f(row.get('eps_estimate_next_year'))
    d30=_f(row.get('eps_estimate_next_year_30d_ago'))
    up=_f(row.get('eps_revisions_up_30d'))
    down=_f(row.get('eps_revisions_down_30d'))
    n=_f(row.get('analyst_count_next_year'))
    rev_growth=_f(row.get('revenue_estimate_growth_next_year'))

    trend=math.nan
    if math.isfinite(cur) and math.isfinite(d30):
        scale=max(abs(d30),0.10)
        trend=max(-1.0,min(1.0,(cur-d30)/scale))
    breadth=math.nan
    if math.isfinite(up) or math.isfinite(down):
        u=up if math.isfinite(up) else 0.0; d=down if math.isfinite(down) else 0.0
        breadth=(u-d)/max(1.0,u+d)
    growth_component=max(-1.0,min(1.0,rev_growth/0.30)) if math.isfinite(rev_growth) else math.nan
    raw=_mean_known(trend,breadth,growth_component)
    score=50+50*raw if math.isfinite(raw) else math.nan
    if not math.isfinite(score): state='DATA GATED'
    elif score >= 65 and (not math.isfinite(n) or n>=3): state='UPWARD REVISION'
    elif score <= 35 and (not math.isfinite(n) or n>=3): state='DOWNWARD REVISION'
    else: state='FLAT / MIXED'
    return {'expectation_revision_score':score,'expectation_revision_state':state}


def story_optionality(row: Mapping[str, Any]) -> Dict[str, Any]:
    """Measure narrative/valuation optionality without rewarding losses by themselves.

    High scores require improving economics and survivable financing. A bad loss is penalized.
    """
    loss_type=classify_loss_type(row)
    nm=_f(row.get('net_margin')); eps=_f(row.get('eps_ttm'))
    is_loss=(math.isfinite(nm) and nm<0) or (math.isfinite(eps) and eps<0)
    fin=financing_risk(row)

    rev=_f(row.get('revenue_growth_yoy'))
    gm=_f(row.get('gross_margin_change'))
    nmchg=_f(row.get('net_margin_change'))
    fcfg=_f(row.get('fcf_growth_yoy'))
    fcf=_f(row.get('fcf_ttm'))
    rd=_f(row.get('rd_to_revenue'))
    capex=_f(row.get('capex_to_revenue'))
    runway=_f(fin.get('cash_runway_years'))

    growth=_lin(rev,-0.10,0.40)
    gross_inflect=_lin(gm,-0.05,0.08)
    net_inflect=_lin(nmchg,-0.08,0.12)
    fcf_inflect=_lin(fcfg,-0.50,1.00)
    if math.isfinite(fcf) and fcf>0:
        fcf_inflect=max(fcf_inflect if math.isfinite(fcf_inflect) else 0.0,0.75)
    investment=_lin(max([x for x in [rd,capex] if math.isfinite(x)] or [math.nan]),0.02,0.20)
    runway_score=_lin(runway,0.5,3.0) if math.isfinite(runway) and runway<90 else (1.0 if math.isfinite(runway) else math.nan)

    # Financial improvement drives the score. Loss status only creates optionality context, never positive evidence.
    improvement=_mean_known(growth,gross_inflect,net_inflect,fcf_inflect)
    credibility=_mean_known(improvement,runway_score)
    optionality=_mean_known(improvement,investment,runway_score)
    if not is_loss:
        # Still useful as an expectations module, but do not label profitable companies as loss-story candidates.
        optionality=(optionality*0.75 if math.isfinite(optionality) else math.nan)
    if loss_type=='STRUCTURAL / BAD LOSS' and math.isfinite(optionality): optionality*=0.35
    if str(fin.get('financing_risk'))=='HIGH' and math.isfinite(optionality): optionality*=0.55

    score=100*optionality if math.isfinite(optionality) else math.nan
    cred=100*credibility if math.isfinite(credibility) else math.nan
    if not math.isfinite(score): state='DATA GATED'
    elif loss_type=='STRUCTURAL / BAD LOSS': state='BAD LOSS / AVOID STORY BIAS'
    elif is_loss and score>=70 and cred>=60: state='EARLY STORY CANDIDATE'
    elif is_loss and score>=55: state='TURNAROUND WATCH'
    elif is_loss: state='LOSS / NO EDGE YET'
    else: state='PROFITABLE / EXPECTATION MODULE'

    return {
        'is_loss_making':bool(is_loss),
        'loss_type':loss_type,
        'story_optionality_score':score,
        'story_credibility_score':cred,
        'story_state':state,
        **fin,
    }


def apply_story_optionality(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty: return df
    out=df.copy()
    records=[]
    for _,r in out.iterrows():
        d=story_optionality(r)
        if str(r.get('market'))=='US':
            rev=analyst_revision_signal(r)
            d.update(rev)
            s=_f(d.get('story_optionality_score')); rs=_f(rev.get('expectation_revision_score'))
            d['expectation_optionality_score']=_mean_known(s,rs)
            if rev.get('expectation_revision_state')=='UPWARD REVISION' and math.isfinite(s) and s>=60:
                d['expectation_optionality_state']='INFLECTION + REVISIONS CONFIRM'
            elif math.isfinite(s) and s>=65:
                d['expectation_optionality_state']='OPTIONALITY HIGH / REVISIONS NOT CONFIRMED'
            elif rev.get('expectation_revision_state')=='DOWNWARD REVISION':
                d['expectation_optionality_state']='EXPECTATIONS DETERIORATING'
            else:
                d['expectation_optionality_state']='WATCH / INCOMPLETE'
        else:
            d.update({'expectation_revision_score':math.nan,'expectation_revision_state':'N/A','expectation_optionality_score':math.nan,'expectation_optionality_state':'N/A'})
        records.append(d)
    add=pd.DataFrame(records,index=out.index)
    for c in add.columns: out[c]=add[c]
    return out
