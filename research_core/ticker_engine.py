from __future__ import annotations
from dataclasses import dataclass,asdict
import math

REQUIRED_FIELDS=['ticker','scenario_id','asset','revenue_exposure','margin_direction','fcf_quality','balance_sheet_quality','valuation_status','catalyst','price_data_status']

@dataclass
class TickerDecision:
    ticker:str; status:str; reason:str; p_mechanism_true:float|None=None; p_catalyst_within_horizon:float|None=None
    p_not_fully_priced:float|None=None; p_trade_profitable_net:float|None=None; ev_net:float|None=None; action:str='NO_RANK'

def qualify(rows):
    """Fail-closed company qualification. It never invents probabilities or EV.
    Rows must come from factual PIT company/market data and independently calibrated models.
    """
    out=[]
    for r in rows:
        t=str(r.get('ticker','UNKNOWN'))
        miss=[k for k in REQUIRED_FIELDS if r.get(k) in (None,'','UNKNOWN')]
        if miss:
            out.append(TickerDecision(t,'NO_RANK','MISSING_REQUIRED_EVIDENCE:'+','.join(miss))); continue
        if not bool(r.get('mechanism_validated',False)):
            out.append(TickerDecision(t,'REJECTED','COMPANY_MECHANISM_NOT_VALIDATED')); continue
        probs=[r.get(k) for k in ['p_mechanism_true','p_catalyst_within_horizon','p_not_fully_priced','p_trade_profitable_net']]
        if any(p is None or not (0<=float(p)<=1) for p in probs):
            out.append(TickerDecision(t,'NO_RANK','UNCALIBRATED_PROBABILITIES')); continue
        wins=r.get('expected_win'); loss=r.get('expected_loss'); costs=r.get('total_costs')
        if wins is None or loss is None or costs is None:
            out.append(TickerDecision(t,'NO_RANK','EV_INPUTS_MISSING')); continue
        p=float(r['p_trade_profitable_net']); ev=p*float(wins)+(1-p)*float(loss)-float(costs)
        action='BUILD' if ev>0 and float(r['p_mechanism_true'])>=.55 and float(r['p_not_fully_priced'])>=.50 else 'WAIT'
        out.append(TickerDecision(t,'QUALIFIED' if action=='BUILD' else 'WATCH_ONLY','CALIBRATED_PIPELINE',*[float(x) for x in probs],ev,action))
    return out
