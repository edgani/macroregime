from __future__ import annotations
from collections import defaultdict, deque
from .models import Evidence, Scenario

# Causal graph edges: source event -> (destination concept, mechanism sentence).
# These are hypotheses used to generate scenarios that must still be verified/calibrated.
GRAPH = {
 'INFLATION_SHOCK':[('POLICY','Sticky inflation constrains easing'),('RATES','Policy/term premium can stay higher'),('CREDIT','Higher financing cost can tighten credit')],
 'LABOR_SHOCK':[('DEMAND_SHOCK','Labor softness can weaken income/demand'),('POLICY','Labor deterioration changes reaction function'),('CREDIT','Income stress can raise delinquency/default risk')],
 'HOUSING':[('DEMAND_SHOCK','Housing weakness can reduce cyclical demand'),('CREDIT','Housing finance can transmit into lenders/households')],
 'POLICY':[('RATES','Policy changes discount/funding rates'),('CREDIT','Policy transmits into credit availability'),('LIQUIDITY','Policy implementation changes reserve/liquidity conditions')],
 'RATES':[('CREDIT','Higher/refinancing rates tighten borrower conditions'),('VALUATION','Discount-rate changes alter valuation context'),('FUNDING','Curve/term-premium changes can affect funding')],
 'CREDIT':[('DEMAND_SHOCK','Tighter credit can feed back into demand'),('FUNDING','Credit stress can impair funding/intermediation'),('CAPITAL_FORMATION','Credit availability changes investment capacity')],
 'LIQUIDITY':[('CREDIT','Liquidity can amplify or damp credit conditions'),('CRYPTO','Liquidity may transmit to crypto only if crypto-specific flows confirm'),('VALUATION','Liquidity can affect risk-bearing capacity')],
 'FISCAL':[('RATES','Issuance/term premium can affect rates'),('FUNDING','Collateral/dealer absorption can affect funding'),('LIQUIDITY','Treasury cash operations can affect system liquidity')],
 'FUNDING':[('CREDIT','Funding stress can tighten credit'),('LIQUIDITY','Funding stress can drain risk capacity')],
 'CAPITAL_FORMATION':[('CREDIT','Debt-funded capex can create refinancing dependence'),('CAPACITY','Capex can expand future capacity'),('VALUATION','Large financing needs can alter equity/debt supply')],
 'IPO':[('CAPITAL_FORMATION','IPO increases equity supply/capital formation'),('INDEX_MECHANICS','Eligibility can create mechanical passive flows')],
 'INDEX_MECHANICS':[('VALUATION','Mechanical flows can affect relative pricing/context')],
 'REGULATORY_CHANGE':[('SECURITIZATION','Rule interpretation can change financing structures')],
 'SECURITIZATION':[('CREDIT','Securitization redistributes credit exposure'),('FUNDING','Structure may create rollover/refinancing dependencies')],
 'SUPPLY_SHOCK':[('PHYSICAL_CONSTRAINT','Supply disruption can become bottleneck if inventory/capacity cannot respond'),('INFLATION_SHOCK','Supply disruption can raise input prices')],
 'PHYSICAL_CONSTRAINT':[('INFLATION_SHOCK','Physical scarcity can sustain price pressure'),('CAPITAL_FORMATION','Scarcity can trigger capacity investment')],
 'GEOPOLITICAL':[('SUPPLY_SHOCK','Geopolitical restrictions can alter supply/logistics'),('FUNDING','Sanctions/risk can alter funding/insurance')],
 'CHINA':[('INDUSTRIAL_METALS','China activity can change metals demand'),('COMMODITIES','China demand can change commodity balances')],
 'INDUSTRIAL_METALS':[('PHYSICAL_CONSTRAINT','Inventory/capacity determine whether demand becomes scarcity')],
 'ENERGY':[('INFLATION_SHOCK','Energy shock can affect headline and input inflation'),('PHYSICAL_CONSTRAINT','Capacity/inventory determine persistence')],
 'CRYPTO':[('FUNDING','Crypto leverage/funding can amplify volatility'),('LIQUIDITY','Stablecoin/ETF flows can create crypto-specific liquidity')],
 'MARKET_STRUCTURE':[('EXECUTION_CONTEXT','Dealer/options positioning may change realized-vol/execution context')],
}


def _uniq(xs): return list(dict.fromkeys(x for x in xs if x))

def _reachable(types, depth=3):
    paths=[]
    for t in types:
        q=deque([(t,[t],[])])
        seen={t}
        while q:
            node,nodes,mechs=q.popleft()
            if len(nodes)-1>=depth: continue
            for nxt,mech in GRAPH.get(node,[]):
                paths.append((t,nxt,nodes+[nxt],mechs+[mech]))
                if nxt not in seen:
                    seen.add(nxt); q.append((nxt,nodes+[nxt],mechs+[mech]))
    return paths


def _scenario(sid,title,evidence,chain,confirm,contradict,next_data,beneficiaries=None,losers=None,caveat=''):
    return Scenario(sid,title,'PROSPECTIVE_REQUIRES_CALIBRATION',chain,[e.evidence_id for e in evidence],confirm,contradict,next_data,
                    _uniq([e.actor for e in evidence]),_uniq([e.incentive for e in evidence]),_uniq([e.constraint for e in evidence]),
                    probability=None,probability_range=None,timing='UNKNOWN_UNCALIBRATED',duration='UNKNOWN_UNCALIBRATED',
                    beneficiaries=beneficiaries or [],losers=losers or [],priced_in='UNKNOWN',action='RESEARCHING',caveat=caveat)


def discover_verified(evidence:list[Evidence]):
    ev=[e for e in evidence if e.verified]
    types={e.event_type for e in ev}
    out=[]
    # Conflicted policy reaction is a specific high-value interaction.
    if {'INFLATION_SHOCK','LABOR_SHOCK','POLICY'}.issubset(types):
        x=[e for e in ev if e.event_type in {'INFLATION_SHOCK','LABOR_SHOCK','HOUSING','POLICY','RATES'}]
        out.append(_scenario('SCN_POLICY_CONFLICT','Policy reaction function is conflicted rather than mechanically dovish/hawkish',x,
            ['Labor/activity evidence changes growth risk','Inflation persistence constrains policy response','Policy must balance both sides of mandate','Rates/credit transmit the chosen reaction'],
            ['labor weakens further while inflation stays sticky','official communication remains restrictive','real rates remain restrictive'],
            ['broad disinflation plus labor stabilization','rapid easing with no inflation persistence'],
            ['core services inflation','payroll revisions/claims','FOMC communication','real consumption','term premium']))
    if {'FISCAL','RATES'}.issubset(types) or {'FISCAL','FUNDING'}.issubset(types):
        x=[e for e in ev if e.event_type in {'FISCAL','RATES','FUNDING','LIQUIDITY'}]
        out.append(_scenario('SCN_FISCAL_ABSORPTION','Large sovereign financing can become a duration/funding problem only if absorption weakens',x,
            ['Financing need increases duration/collateral supply','Dealer/investor balance sheet must absorb issuance','Weak absorption raises term premium/funding stress','Tighter conditions feed into credit'],
            ['weak auctions/dealer take','term-premium rise','repo/basis stress'],['strong auctions','ample reserves/dealer capacity'],
            ['Treasury auction tails','dealer take','foreign demand','term premium','repo/basis']))
    if {'LIQUIDITY','CREDIT'}.issubset(types):
        x=[e for e in ev if e.event_type in {'LIQUIDITY','CREDIT','RATES'}]
        out.append(_scenario('SCN_LIQUIDITY_CREDIT','Liquidity and credit can either cushion or amplify the macro state',x,
            ['System liquidity shapes intermediary risk capacity','Credit spreads/lending determine real-economy transmission','A divergence between liquidity and credit is itself informative'],
            ['liquidity tightens and HY spreads widen','bank standards tighten'],['liquidity expands and spreads remain contained'],['bank reserves','RRP/TGA','HY/IG OAS','SLOOS','loan growth']))
    # General graph-derived scenario candidates: create only meaningful 2+ hop paths from verified events.
    paths=_reachable(types,depth=3)
    grouped=defaultdict(list)
    for start,end,nodes,mechs in paths:
        if len(nodes)>=3: grouped[(start,end)].append((nodes,mechs))
    high_value={'CREDIT','FUNDING','LIQUIDITY','PHYSICAL_CONSTRAINT','INFLATION_SHOCK','CAPITAL_FORMATION','VALUATION','CRYPTO','INDUSTRIAL_METALS'}
    for (start,end),ps in grouped.items():
        if end not in high_value: continue
        # avoid dozens of duplicates; one shortest representative path per start/end
        nodes,mechs=sorted(ps,key=lambda z:len(z[0]))[0]
        sx=[e for e in ev if e.event_type==start]
        if not sx: continue
        sid=f'SCN_GRAPH_{start}_{end}'
        title=f'{start.replace("_"," ").title()} may transmit into {end.replace("_"," ").title()}'
        out.append(_scenario(sid,title,sx,mechs,
            [f'evidence appears in {end.lower().replace("_"," ")} channel'],[f'transmission into {end.lower().replace("_"," ")} fails to appear'],
            [f'direct factual measures of {end.lower().replace("_"," ")}'],caveat='Graph discovery is a causal hypothesis generator, not calibrated probability.'))
    # de-duplicate and cap to keep command center usable
    dedup={s.scenario_id:s for s in out}
    return list(dedup.values())[:12]


def radar_from_news(news_leads):
    """Unverified scenario radar. News is a lead, never a production fact."""
    by=defaultdict(list)
    for x in news_leads.get('leads',[]): by[x.get('theme','OTHER')].append(x)
    map_={
      'POLICY_CONFLICT':('RADAR_POLICY_CONFLICT','Policy reaction conflict','Labor/growth weakness may coexist with inflation constraint', ['inflation','labor','FOMC','rates']),
      'AI_CAPITAL':('RADAR_AI_CAPITAL','AI mega-capital formation / IPO reflexivity','Large AI financing/IPO supply may alter capital formation, index/passive mechanics and liquidity rotation',['official filing','offering size','free float','index eligibility','passive AUM']),
      'AI_CREDIT':('RADAR_AI_CREDIT','AI infrastructure credit / securitization fragility','Debt-funded AI infrastructure can create refinancing/tenant/valuation fragility without implying a 2008 repeat',['issuance','LTV/DSCR','tenant concentration','lease tenor','spreads','defaults']),
      'CHINA_GOLD':('RADAR_CHINA_GOLD','China / official gold demand persistence','Official/physical demand may alter gold balance but must be reconciled with real yields, USD, ETF flows and supply',['SAFE/PBOC reserves','imports','SGE premium','ETF flows','mine/recycling supply']),
      'ENERGY_SUPPLY':('RADAR_ENERGY_SUPPLY','Energy supply / logistics shock','Supply disruption matters only if spare capacity, inventory and substitution cannot offset it',['OPEC capacity','inventories','exports','freight','refinery utilization']),
      'FISCAL_FUNDING':('RADAR_FISCAL_FUNDING','Treasury supply / funding absorption','Issuance becomes macro-relevant only if auction/dealer/repo/term-premium transmission weakens',['auction tails','dealer take','foreign demand','repo/basis','term premium']),
      'INDONESIA':('RADAR_INDONESIA','Indonesia macro / commodity / capital-flow transition','BI, rupiah, commodity terms-of-trade and FDI/credit can create local divergence from global state',['BI','BPS','OJK','IDX/KSEI flow','BKPM','trade/FX reserves']),
    }
    out=[]
    for theme,rows in by.items():
        if theme not in map_: continue
        sid,title,thesis,needs=map_[theme]
        out.append({'scenario_id':sid,'title':title,'status':'UNVERIFIED_LEAD','hypothesis':thesis,'article_count':len(rows),'latest_titles':[r.get('title') for r in rows[:3]],'needs_verification':needs,'action':'VERIFY_FIRST'})
    return out

def radar_from_news_general(news_leads):
    """Route arbitrary lead titles through the conservative event router and construct novel causal hypotheses.
    This never verifies a headline and never assigns trade probability.
    """
    from .event_router import route
    items=[]
    for lead in news_leads.get('leads',[]):
        title=lead.get('title') or ''
        rr=route(title)
        types=[x['event_type'] for x in rr.get('candidate_event_types',[])]
        if not types: continue
        # Generate graph paths from each routed event type.
        paths=_reachable(set(types),depth=3)
        reps=[]
        for start,end,nodes,mechs in paths:
            if len(nodes)>=3:
                reps.append({'start':start,'end':end,'nodes':nodes,'mechanisms':mechs})
        reps=sorted(reps,key=lambda x:len(x['nodes']))[:3]
        if not reps and len(types)>=2:
            reps=[{'start':types[0],'end':types[1],'nodes':types[:2],'mechanisms':['Observed concepts coexist; verify whether a causal transmission exists rather than assuming correlation.']}]
        for j,rp in enumerate(reps):
            sid=f"RADAR_GENERAL_{abs(hash((title,rp['start'],rp['end'])))%10**10}_{j}"
            items.append({'scenario_id':sid,'title':f"{rp['start'].replace('_',' ').title()} → {rp['end'].replace('_',' ').title()} candidate",'status':'UNVERIFIED_GENERAL_DISCOVERY','hypothesis':' → '.join(rp['mechanisms']),'article_count':1,'latest_titles':[title],'routed_event_types':types,'needs_verification':[f'primary-source verification of {x.lower().replace("_"," ")}' for x in set(rp['nodes'])],'action':'VERIFY_FIRST'})
    # Deduplicate by title/hypothesis and cap UI noise.
    out=[];seen=set()
    for x in items:
        k=(x['title'],x['hypothesis'])
        if k not in seen:seen.add(k);out.append(x)
    return out[:12]
