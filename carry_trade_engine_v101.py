"""War Room OS V10.1 carry-trade state engine.

Causal inputs only: policy/money-market rate differentials, option-implied/global funding stress,
release-lagged CFTC positioning, official policy rates, and explicit data gaps. Price is only an
execution reference/outcome. The engine identifies direction and transmission; it does not claim
proven alpha until the separate historical/prospective proof gate passes.
"""
from __future__ import annotations
import json, math
from pathlib import Path
from typing import Any, Mapping

HERE=Path(__file__).resolve().parent
MAP=json.loads((HERE/'V101_CARRY_CAUSAL_MAP.json').read_text(encoding='utf-8'))
POLICY=json.loads((HERE/'V101_CARRY_POLICY.json').read_text(encoding='utf-8'))


def _f(v:Any)->float|None:
    try:
        x=float(v);return x if math.isfinite(x) else None
    except Exception:return None

def _clip(v:float,lo:float=0.0,hi:float=1.0)->float:return max(lo,min(hi,float(v)))
def _series(current:Mapping[str,Any],sid:str)->Mapping[str,Any]:
    row=(((current.get('macro') or {}).get('series') or {}).get(sid));return row if isinstance(row,Mapping) else {}
def _rate(current:Mapping[str,Any],currency:str)->tuple[float|None,float|None,str]:
    cfg=(MAP.get('currency_rates') or {}).get(currency) or {}
    if cfg.get('series'):
        r=_series(current,str(cfg['series']));return _f(r.get('value')),_f(r.get('change_3')),str(cfg.get('source') or '')
    row=((current.get('official_policy_rates') or {}).get('rates') or {}).get(cfg.get('official_key')) or {}
    return _f(row.get('value')),_f(row.get('change_3')),str(cfg.get('source') or '')

def _stress(current:Mapping[str,Any],macro_state:Mapping[str,Any]|None=None)->dict[str,Any]:
    st=POLICY['stress'];vix=_f(_series(current,'VIXCLS').get('value'));oas=_f(_series(current,'BAMLH0A0HYM2').get('value'))
    if vix is None:vix_score=None
    elif vix>=st['vix_high']:vix_score=1.0
    elif vix>=st['vix_elevated']:vix_score=.55+.45*(vix-st['vix_elevated'])/(st['vix_high']-st['vix_elevated'])
    elif vix<=st['vix_low']:vix_score=0.0
    else:vix_score=.55*(vix-st['vix_low'])/(st['vix_elevated']-st['vix_low'])
    if oas is None:oas_score=None
    elif oas>=st['hy_oas_high']:oas_score=1.0
    elif oas>=st['hy_oas_elevated']:oas_score=.5+.5*(oas-st['hy_oas_elevated'])/(st['hy_oas_high']-st['hy_oas_elevated'])
    else:oas_score=_clip(oas/st['hy_oas_elevated']*.5)
    liq=_f((macro_state or {}).get('liquidity_score'));risk=_f((macro_state or {}).get('risk_asset_score'))
    rows=[x for x in (vix_score,oas_score,(-liq+1)/2 if liq is not None else None,(-risk+1)/2 if risk is not None else None) if x is not None]
    score=sum(rows)/len(rows) if rows else None
    return {'score':score,'vix':vix,'vix_score':vix_score,'hy_oas':oas,'hy_oas_score':oas_score,'liquidity_score':liq,'risk_asset_score':risk}

CURRENCY_PATTERNS={
 'EUR':['EURO FX','EUROPEAN CURRENCY UNIT'], 'JPY':['JAPANESE YEN'], 'GBP':['BRITISH POUND STERLING','BRITISH POUND'],
 'AUD':['AUSTRALIAN DOLLAR'], 'CAD':['CANADIAN DOLLAR'], 'CHF':['SWISS FRANC'], 'USD':['U.S. DOLLAR INDEX','USD INDEX']
}
def _positioning(current:Mapping[str,Any])->dict[str,dict[str,Any]]:
    rows=((((current.get('positioning') or {}).get('datasets') or {}).get('tff') or {}).get('rows') or [])
    out:dict[str,dict[str,Any]]={}
    for row in rows:
        if not isinstance(row,Mapping):continue
        name=' '.join(str(row.get(k) or '') for k in ('market_and_exchange_names','contract_market_name','commodity_name')).upper()
        cur=next((c for c,pats in CURRENCY_PATTERNS.items() if any(p in name for p in pats)),None)
        if not cur:continue
        def pick(*keys:str)->Any:
            for key in keys:
                if key in row and row.get(key) is not None:
                    return row.get(key)
            return None
        oi=_f(pick('open_interest_all'));ll=_f(pick('lev_money_positions_long_all','lev_money_positions_long'));ls=_f(pick('lev_money_positions_short_all','lev_money_positions_short'))
        al=_f(pick('asset_mgr_positions_long_all','asset_mgr_positions_long'));ass=_f(pick('asset_mgr_positions_short_all','asset_mgr_positions_short'))
        lev=(ll-ls)/oi if None not in (oi,ll,ls) and oi else None;asset=(al-ass)/oi if None not in (oi,al,ass) and oi else None
        out[cur]={'leveraged_net_share':lev,'asset_manager_net_share':asset,'open_interest':oi,'report_date':row.get('report_date_as_yyyy_mm_dd'),'release_lagged':True,'market_name':name}
    return out

CURRENCY_ASSET_MAP={
 'USD':{'region':'United States','local_bonds':'US Treasury bills/notes','liquid_equities':'liquid US banks and domestically funded equities','exporters':'US exporters'},
 'EUR':{'region':'Euro area','local_bonds':'core/peripheral euro sovereign bonds after spread-risk review','liquid_equities':'liquid euro-area banks and domestic cyclicals','exporters':'euro-area exporters'},
 'JPY':{'region':'Japan','local_bonds':'Japanese government bonds after duration review','liquid_equities':'Japanese domestic financials and liquid equities','exporters':'Japanese exporters'},
 'GBP':{'region':'United Kingdom','local_bonds':'UK gilts after duration review','liquid_equities':'liquid UK banks and domestic equities','exporters':'UK exporters'},
 'AUD':{'region':'Australia','local_bonds':'Australian government bonds','liquid_equities':'Australian banks and domestic equities','exporters':'Australian exporters/resource producers'},
 'CAD':{'region':'Canada','local_bonds':'Canadian government bonds','liquid_equities':'Canadian banks and domestic equities','exporters':'Canadian exporters/resource producers'},
 'CHF':{'region':'Switzerland','local_bonds':'Swiss Confederation bonds','liquid_equities':'liquid Swiss domestic equities','exporters':'Swiss exporters'},
 'IDR':{'region':'Indonesia','local_bonds':'Indonesian government bonds after FX/liquidity review','liquid_equities':'liquid Indonesian banks and domestic-demand equities','exporters':'Indonesian exporters'},
}

def _opposite(direction:str)->str:
    return 'SHORT_PAIR' if direction=='LONG_PAIR' else 'LONG_PAIR'

def _beneficiaries(target:str,funding:str,state:str)->dict[str,Any]:
    tm=CURRENCY_ASSET_MAP.get(target,{});fm=CURRENCY_ASSET_MAP.get(funding,{})
    direct=[f'{target} currency',tm.get('local_bonds',f'{target} local government bonds'),tm.get('liquid_equities',f'liquid {target}-area banks/equities')]
    secondary=[fm.get('exporters',f'{funding}-area exporters'), 'high-beta equities only while funding stress remains contained', 'selected commodities and crypto only when global liquidity confirms']
    unwind_winners=[f'{funding} currency','volatility hedges','high-quality liquid assets and cash equivalents']
    unwind_losers=[f'{target} currency',tm.get('local_bonds',f'{target} local bonds'),tm.get('liquid_equities',f'{target} local equities'),'leveraged high-beta and crypto exposures',fm.get('exporters',f'{funding}-area exporters')]
    carry_active=state in {'CARRY_ON','SELECTIVE_CARRY','CROWDED_CARRY'}
    return {
      'beneficiaries':direct+secondary if carry_active else unwind_winners,
      'direct_beneficiaries':direct if carry_active else unwind_winners,
      'secondary_beneficiaries':secondary if carry_active else [],
      'at_risk':[f'{funding} currency','carry hedges/long volatility'] if carry_active else unwind_losers,
      'unwind_winners':unwind_winners,'unwind_losers':unwind_losers,
      'target_region':tm.get('region',target),'funding_region':fm.get('region',funding),
    }

def pair_state(pair:str,current:Mapping[str,Any],macro_state:Mapping[str,Any]|None=None)->dict[str,Any]:
    cfg=(MAP.get('pairs') or {}).get(pair)
    if not cfg:return {'state':'INCOMPLETE','pair':pair,'reason':'PAIR_NOT_MAPPED','directional_score':None}
    base,quote=cfg['base'],cfg['quote'];br,bc,bs=_rate(current,base);qr,qc,qs=_rate(current,quote)
    qrow=((((current.get('quotes') or {}).get('markets') or {}).get('fx') or {}).get(pair) or {})
    price=_f(qrow.get('price'));fresh=str(qrow.get('validation') or '')=='VALID_CURRENT_REFERENCE'
    pos=_positioning(current);stress=_stress(current,macro_state)
    if br is None or qr is None:
        return {'schema':'warroom.v101.carry_pair.v1','pair':pair,'base':base,'quote':quote,'state':'INCOMPLETE','reason':'POLICY_RATE_MISSING','base_rate':br,'quote_rate':qr,'price':price,'fresh_quote':fresh,'directional_score':None,'proof_state':'NOT_PROVEN'}
    spread=br-qr
    if spread>=0:target,funding=base,quote;pair_direction='LONG_PAIR';signed=1.0
    else:target,funding=quote,base;pair_direction='SHORT_PAIR';signed=-1.0
    carry=abs(spread);tchange=bc if target==base else qc;fchange=qc if funding==quote else bc
    widening=(tchange-fchange) if None not in (tchange,fchange) else None
    attractiveness=_clip((carry-POLICY['thresholds']['minimum_rate_spread_pct'])/max(.01,POLICY['thresholds']['strong_rate_spread_pct']))
    stress_score=_f(stress.get('score'))
    fund_pos=_f((pos.get(funding) or {}).get('leveraged_net_share'));target_pos=_f((pos.get(target) or {}).get('leveraged_net_share'))
    funding_short_crowd=_clip(-(fund_pos or 0.0)/.25) if fund_pos is not None else None
    target_long_crowd=_clip((target_pos or 0.0)/.25) if target_pos is not None else None
    compression=_clip(-(widening or 0.0)/1.0) if widening is not None else None
    unwind_rows=[x for x in (stress_score,funding_short_crowd,target_long_crowd,compression) if x is not None]
    unwind=sum(unwind_rows)/len(unwind_rows) if unwind_rows else None
    carry_rows=[attractiveness,1-(stress_score if stress_score is not None else .5),_clip(.5+(widening or 0.0)/2.0) if widening is not None else None]
    carry_score=sum(x for x in carry_rows if x is not None)/sum(x is not None for x in carry_rows)
    th=POLICY['thresholds']
    if carry<th['minimum_rate_spread_pct']:state='LOW_CARRY'
    elif (unwind or 0)>=th['unwind_active_score']:state='UNWIND_ACTIVE'
    elif (unwind or 0)>=th['unwind_risk_score']:state='UNWIND_RISK'
    elif carry_score>=th['crowded_score'] and max(funding_short_crowd or 0,target_long_crowd or 0)>=.65:state='CROWDED_CARRY'
    elif carry_score>=th['carry_on_score']:state='CARRY_ON'
    else:state='SELECTIVE_CARRY'
    confidence=.80
    missing=[]
    if not pos:confidence=min(confidence,POLICY['confidence_caps']['missing_positioning']);missing.append('CFTC_POSITIONING')
    confidence=min(confidence,POLICY['confidence_caps']['missing_basis']);missing.append('FORWARD_POINTS_OR_CROSS_CURRENCY_BASIS')
    confidence=min(confidence,POLICY['confidence_caps']['missing_external_balance']);missing.append('EXTERNAL_BALANCE_AND_RESERVES')
    confidence=min(confidence,POLICY['confidence_caps']['not_point_in_time']);missing.append('POINT_IN_TIME_HISTORY')
    directional=signed*carry_score
    if state in {'UNWIND_RISK','UNWIND_ACTIVE'}:directional*=(1-(unwind or 0)*1.5)
    unwind_direction=_opposite(pair_direction)
    if state=='UNWIND_ACTIVE': current_direction=unwind_direction;action='UNWIND_OR_REVERSE_CARRY'
    elif state=='UNWIND_RISK': current_direction='REDUCE_OR_HEDGE_CARRY';action='DE_RISK_AND_WAIT'
    elif state=='CROWDED_CARRY': current_direction=pair_direction;action='LATE_STAGE_CARRY_REDUCED_SIZE'
    elif state in {'CARRY_ON','SELECTIVE_CARRY'}: current_direction=pair_direction;action='CARRY_EXPRESSION_RESEARCH'
    else: current_direction='NO_TRADE';action='WAIT'
    stage={'CARRY_ON':'ACTIVE','SELECTIVE_CARRY':'EARLY_OR_MIXED','CROWDED_CARRY':'LATE_CROWDED','UNWIND_RISK':'EXIT_WARNING','UNWIND_ACTIVE':'UNWIND_ACTIVE','LOW_CARRY':'DORMANT'}.get(state,'INCOMPLETE')
    b=_beneficiaries(target,funding,state)
    return {'schema':'warroom.v101.carry_pair.v1','pair':pair,'base':base,'quote':quote,'base_rate':br,'quote_rate':qr,'rate_spread_pct':spread,'annual_carry_abs_pct':carry,
      'funding_currency':funding,'target_currency':target,'pair_direction':pair_direction,'carry_direction':pair_direction,'unwind_direction':unwind_direction,'current_direction':current_direction,'recommended_action':action,'stage':stage,
      'trade_expression':f'{current_direction} {pair.replace("_REFERENCE","")} / fund {funding} / own {target}',
      'state':state,'carry_score':carry_score,'unwind_risk_score':unwind,'directional_score':directional,'confidence_cap':confidence,'price':price,'fresh_quote':fresh,
      'policy_spread_change_3':widening,'global_stress':stress,'funding_positioning':pos.get(funding),'target_positioning':pos.get(target),**b,
      'transmission_chain':[f'fund or sell {funding}',f'buy {target} or {target}-currency assets',f'inflows support {target} FX/bonds and selected liquid risk assets',f'if stress rises, deleveraging buys back {funding} and sells {target} assets'],
      'missing_promotion_inputs':missing,'invalidation':['policy differential compresses materially','funding stress or volatility jumps','funding currency positioning becomes one-sided','target external balance/reserves deteriorate'],
      'proof_state':'NOT_PROVEN','claim_limit':'Current carry map and direction; systematic capital requires point-in-time historical and prospective proof.'}

def build_carry_book(current:Mapping[str,Any],macro_state:Mapping[str,Any]|None=None)->dict[str,Any]:
    pairs=[pair_state(p,current,macro_state) for p in MAP.get('pairs',{})]
    valid=[p for p in pairs if p.get('directional_score') is not None]
    valid.sort(key=lambda p:(p.get('state') not in {'CARRY_ON','CROWDED_CARRY'},-abs(float(p.get('directional_score') or 0))))
    unwind=[p for p in valid if p.get('state') in {'UNWIND_RISK','UNWIND_ACTIVE'}]
    carry=[p for p in valid if p.get('state') in {'CARRY_ON','CROWDED_CARRY','SELECTIVE_CARRY'}]
    funding=sorted({p['funding_currency'] for p in carry});targets=sorted({p['target_currency'] for p in carry})
    global_state='UNWIND_ACTIVE' if any(p['state']=='UNWIND_ACTIVE' for p in unwind) else 'UNWIND_RISK' if unwind else 'CARRY_ON' if carry else 'INCOMPLETE'
    beneficiaries=[]
    for p in carry[:5]:beneficiaries += [{'pair':p['pair'],'asset':x,'state':p['state']} for x in p.get('beneficiaries',[])[:4]]
    return {'schema':'warroom.v101.carry_book.v1','state':global_state,'pairs':pairs,'top_carry_trades':carry[:10],'unwind_alerts':unwind[:10],
      'funding_currencies':funding,'target_currencies':targets,'beneficiary_map':beneficiaries,'proof_state':'NOT_PROVEN',
      'claim_limit':'Carry direction is operational research; no pair is systematic-live eligible until the carry proof gate passes.'}
