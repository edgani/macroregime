from __future__ import annotations
from .models import State, Evidence
import math


def _vals(macro,sid):
    x=macro.get('series',{}).get(sid,{}).get('values',[])
    return [float(v) for _,v in x if v is not None]

def _last(macro,sid):
    x=macro.get('series',{}).get(sid)
    return None if not x else x.get('last_value')

def _date(macro,sid):
    x=macro.get('series',{}).get(sid)
    return None if not x else x.get('last_date')

def _chg(vals,n):
    return None if len(vals)<=n or vals[-1] is None or vals[-1-n] in (None,0) else vals[-1]/vals[-1-n]-1

def _diff(vals,n):
    return None if len(vals)<=n else vals[-1]-vals[-1-n]

def _ann3(vals):
    if len(vals)<4 or vals[-4] in (None,0):return None
    return (vals[-1]/vals[-4])**4-1

def _fmt(x,pct=False):
    if x is None:return '—'
    return f'{x*100:.1f}%' if pct else f'{x:.2f}'


def derive_states(data):
    m=data.get('macro',{}); states=[]; ev=[]
    # Growth: observation-only composite
    ind=_vals(m,'INDPRO'); pay=_vals(m,'PAYEMS'); un=_vals(m,'UNRATE'); claims=_vals(m,'ICSA'); retail=_vals(m,'RSAFS')
    g_signals=[]; g_e=[]
    if len(ind)>3:
        d=_chg(ind,3); g_signals.append(1 if d and d>0 else -1); g_e.append(f'Industrial production 3m change {_fmt(d,True)}')
    if len(pay)>3:
        d=_chg(pay,3); g_signals.append(1 if d and d>0 else -1); g_e.append(f'Payroll level 3m change {_fmt(d,True)}')
    if len(un)>3:
        d=_diff(un,3); g_signals.append(-1 if d and d>0 else 1); g_e.append(f'Unemployment 3m change {_fmt(d)} pp')
    if len(retail)>3:
        d=_chg(retail,3); g_signals.append(1 if d and d>0 else -1); g_e.append(f'Retail sales 3m change {_fmt(d,True)}')
    gv=sum(g_signals) if g_signals else 0
    growth='IMPROVING' if gv>=2 else 'WEAKENING' if gv<=-2 else 'MIXED'
    states.append(State('GROWTH','Growth',growth,'UP' if growth=='IMPROVING' else 'DOWN' if growth=='WEAKENING' else 'MIXED','OBSERVED' if g_signals else 'NO_DATA',_date(m,'INDPRO'),g_e,next_data=['Payrolls','Claims','Industrial production','Retail sales']))
    if g_signals:
        ev.append(Evidence('EV_GROWTH','DEMAND_SHOCK',f'Growth state {growth}',True,'OFFICIAL_MACRO','FRED/primary-series mirror',_date(m,'INDPRO') or m.get('as_of',''),actor='Households/Firms',incentive='Income and demand',constraint='Financial conditions',direction='UP' if growth=='IMPROVING' else 'DOWN' if growth=='WEAKENING' else 'MIXED'))
    # Labor
    l_e=[]; score=0; n=0
    if len(un)>3:
        d=_diff(un,3); score += -1 if d and d>0.15 else 1 if d and d<-0.1 else 0; n+=1; l_e.append(f'Unemployment 3m Δ {_fmt(d)} pp')
    if len(claims)>4:
        d=_chg(claims,4); score += -1 if d and d>0.08 else 1 if d and d<-0.08 else 0; n+=1; l_e.append(f'Claims 4w Δ {_fmt(d,True)}')
    labor='TIGHT/RESILIENT' if score>0 else 'SOFTENING' if score<0 else 'MIXED'
    states.append(State('LABOR','Labor',labor,'UP' if score>0 else 'DOWN' if score<0 else 'MIXED','OBSERVED' if n else 'NO_DATA',_date(m,'UNRATE'),l_e,next_data=['Unemployment','Payrolls','Initial claims']))
    if n:
        ev.append(Evidence('EV_LABOR','LABOR_SHOCK',f'Labor state {labor}',True,'OFFICIAL_MACRO','BLS/FRED mirror',_date(m,'UNRATE') or m.get('as_of',''),actor='Workers/Employers',incentive='Hiring and income',constraint='Labor demand',direction='DOWN' if labor=='SOFTENING' else 'UP' if labor=='TIGHT/RESILIENT' else 'MIXED'))
    # Inflation: current level + recent direction
    cpi=_vals(m,'CPIAUCSL'); core=_vals(m,'CPILFESL'); ppi=_vals(m,'PPIACO')
    inf_e=[]; recent=[]
    for name,vals in [('CPI',cpi),('Core CPI',core),('PPI',ppi)]:
        if len(vals)>12:
            yoy=_chg(vals,12); m3=_ann3(vals); recent.append(m3 if m3 is not None else yoy); inf_e.append(f'{name} YoY {_fmt(yoy,True)} / 3m ann {_fmt(m3,True)}')
    if recent:
        med=sorted(recent)[len(recent)//2]
        inflation='HOT/STICKY' if med>0.03 else 'DISINFLATING' if med<0.02 else 'MODERATE'
    else: inflation='NO_DATA'
    states.append(State('INFLATION','Inflation',inflation,'UP' if inflation=='HOT/STICKY' else 'DOWN' if inflation=='DISINFLATING' else 'MIXED','OBSERVED' if recent else 'NO_DATA',_date(m,'CPIAUCSL'),inf_e,next_data=['Core CPI','Core PCE','PPI','Wages']))
    if recent:
        ev.append(Evidence('EV_INFLATION','INFLATION_SHOCK',f'Inflation state {inflation}',True,'OFFICIAL_MACRO','BLS/BEA/FRED mirror',_date(m,'CPIAUCSL') or m.get('as_of',''),actor='Households/Firms/Policy makers',incentive='Pricing and wage setting',constraint='Price stability mandate',direction='UP' if inflation=='HOT/STICKY' else 'DOWN' if inflation=='DISINFLATING' else 'MIXED'))
    # Policy / real stance
    ff=_last(m,'FEDFUNDS'); cpi_yoy=_chg(cpi,12) if len(cpi)>12 else None
    real=None if ff is None or cpi_yoy is None else ff/100-cpi_yoy
    if ff is None: pol='NO_DATA'
    elif real is not None and real>0.01: pol='RESTRICTIVE'
    elif real is not None and real<-0.005: pol='ACCOMMODATIVE'
    else: pol='NEUTRAL/MIXED'
    states.append(State('POLICY','Policy',pol,'MIXED','OBSERVED' if ff is not None else 'NO_DATA',_date(m,'FEDFUNDS'),[f'Fed funds {_fmt(ff)}%',f'Ex-post real stance {_fmt(real,True)}' if real is not None else 'Real stance —'],next_data=['FOMC','Inflation','Labor','Financial conditions']))
    if ff is not None:
        ev.append(Evidence('EV_POLICY','POLICY',f'Policy stance {pol}',True,'OFFICIAL_POLICY','Federal Reserve/FRED mirror',_date(m,'FEDFUNDS') or m.get('as_of',''),actor='Federal Reserve',incentive='Mandate stabilization',constraint='Inflation/employment/financial stability',direction='RESTRICTIVE' if pol=='RESTRICTIVE' else 'MIXED'))
    # Rates/curve
    y2=_last(m,'DGS2'); y10=_last(m,'DGS10'); r10=_last(m,'DFII10'); be=_last(m,'T10YIE'); curve=None if y2 is None or y10 is None else y10-y2
    rates='INVERTED' if curve is not None and curve<0 else 'STEEP/POSITIVE' if curve is not None and curve>0.5 else 'FLAT'
    states.append(State('RATES','Rates / Curve',rates,'MIXED','OBSERVED' if curve is not None else 'NO_DATA',_date(m,'DGS10'),[f'2Y {_fmt(y2)}%',f'10Y {_fmt(y10)}%',f'10s2s {_fmt(curve)} pp',f'Real 10Y {_fmt(r10)}%',f'10Y BE {_fmt(be)}%'],next_data=['Treasury curve','Term premium','Auction demand']))
    if curve is not None:
        ev.append(Evidence('EV_RATES','RATES',f'Rates/curve state {rates}',True,'OFFICIAL_RATES','US Treasury/Federal Reserve via public series',_date(m,'DGS10') or m.get('as_of',''),actor='Treasury market/Policy makers',incentive='Duration pricing and policy expectations',constraint='Inflation/growth/fiscal absorption',direction='MIXED'))
    # Credit
    hy=_vals(m,'BAMLH0A0HYM2'); hy_last=hy[-1] if hy else None; hy3=_diff(hy,3) if len(hy)>3 else None
    if hy_last is None: credit='NO_DATA'
    elif hy_last>5 or (hy3 is not None and hy3>0.75): credit='STRESS'
    elif hy_last<3.5 and (hy3 is None or hy3<=0.25): credit='EASY/COMPLACENT'
    else: credit='NORMAL'
    states.append(State('CREDIT','Credit',credit,'DOWN' if credit=='STRESS' else 'UP' if credit=='EASY/COMPLACENT' else 'MIXED','OBSERVED' if hy else 'NO_DATA',_date(m,'BAMLH0A0HYM2'),[f'HY OAS {_fmt(hy_last)}%',f'3-period Δ {_fmt(hy3)} pp'],next_data=['HY OAS','IG OAS','SLOOS','Defaults','Refinancing']))
    if hy:
        ev.append(Evidence('EV_CREDIT','CREDIT',f'Credit state {credit}',True,'MARKET_CREDIT','ICE BofA via FRED mirror',_date(m,'BAMLH0A0HYM2') or m.get('as_of',''),actor='Lenders/Borrowers',incentive='Risk-adjusted lending',constraint='Balance-sheet and default risk',direction='DOWN' if credit=='STRESS' else 'MIXED'))
    # Liquidity
    wal=_vals(m,'WALCL'); rrp=_vals(m,'RRPONTSYD'); tga=_vals(m,'WTREGEN')
    liq_e=[]; liqscore=0; lq_n=0
    if len(wal)>4:
        d=_diff(wal,4); liqscore += 1 if d and d>0 else -1 if d and d<0 else 0; lq_n+=1; liq_e.append(f'Fed assets 4-period Δ {_fmt(d)}')
    if len(rrp)>4:
        d=_diff(rrp,4); liqscore += 1 if d and d<0 else -1 if d and d>0 else 0; lq_n+=1; liq_e.append(f'RRP 4-period Δ {_fmt(d)}')
    if len(tga)>4:
        d=_diff(tga,4); liqscore += 1 if d and d<0 else -1 if d and d>0 else 0; lq_n+=1; liq_e.append(f'TGA 4-period Δ {_fmt(d)}')
    liquidity='EXPANDING' if liqscore>=2 else 'TIGHTENING' if liqscore<=-2 else 'MIXED'
    states.append(State('LIQUIDITY','Liquidity',liquidity,'UP' if liquidity=='EXPANDING' else 'DOWN' if liquidity=='TIGHTENING' else 'MIXED','OBSERVED' if lq_n else 'NO_DATA',_date(m,'WALCL'),liq_e,next_data=['Fed assets','RRP','TGA','Bank reserves','Funding']))
    if lq_n:
        ev.append(Evidence('EV_LIQUIDITY','LIQUIDITY',f'Liquidity state {liquidity}',True,'OFFICIAL_BALANCE_SHEET','Federal Reserve/Treasury series',_date(m,'WALCL') or m.get('as_of',''),actor='Fed/Treasury/MMFs/Banks',incentive='Cash and balance-sheet management',constraint='Reserve/funding conditions',direction='UP' if liquidity=='EXPANDING' else 'DOWN' if liquidity=='TIGHTENING' else 'MIXED'))
    # Housing
    hou=_vals(m,'HOUST'); per=_vals(m,'PERMIT'); h_e=[]; hs=[]
    for name,vals in [('Starts',hou),('Permits',per)]:
        if len(vals)>3:
            d=_chg(vals,3); hs.append(d); h_e.append(f'{name} 3m Δ {_fmt(d,True)}')
    if hs:
        avg=sum(x for x in hs if x is not None)/max(1,sum(x is not None for x in hs)); housing='WEAK' if avg<-0.05 else 'STRONG' if avg>0.05 else 'MIXED'
    else:housing='NO_DATA'
    states.append(State('HOUSING','Housing',housing,'DOWN' if housing=='WEAK' else 'UP' if housing=='STRONG' else 'MIXED','OBSERVED' if hs else 'NO_DATA',_date(m,'HOUST'),h_e,next_data=['Starts','Permits','Sales','Mortgage rates']))
    if hs:
        ev.append(Evidence('EV_HOUSING','HOUSING',f'Housing state {housing}',True,'OFFICIAL_MACRO','Census/FRED mirror',_date(m,'HOUST') or m.get('as_of',''),actor='Households/Builders/Lenders',incentive='Housing demand/supply',constraint='Rates and affordability',direction='DOWN' if housing=='WEAK' else 'UP' if housing=='STRONG' else 'MIXED'))
    # Fiscal debt observation
    tr=data.get('treasury',{}); debt=tr.get('debt') if isinstance(tr,dict) else None
    if debt:
        states.append(State('FISCAL','Fiscal / Treasury','HIGH_FINANCING_NEED_CONTEXT','MIXED','OBSERVED',debt.get('record_date'),[f"Debt outstanding {debt.get('tot_pub_debt_out_amt','—')}", 'Debt level alone is not a funding-stress signal.'],next_data=['Net issuance','Auctions','Dealer take','Term premium','Repo/basis']))
        ev.append(Evidence('EV_FISCAL','FISCAL','Large sovereign financing stock requires monitoring',True,'OFFICIAL_FISCAL','US Treasury Fiscal Data',debt.get('record_date') or tr.get('as_of',''),actor='US Treasury',incentive='Fund government obligations',constraint='Investor/dealer absorption and cost',direction='MIXED',note='Debt stock is context; funding stress requires transmission evidence.'))
    else:
        states.append(State('FISCAL','Fiscal / Treasury','NO_DATA','MIXED','NO_DATA'))
    return states,ev
