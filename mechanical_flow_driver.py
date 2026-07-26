"""Fail-closed cross-market mechanical-flow attribution.

The engine distinguishes position creation, forced liquidation and transmission capacity.
It never treats total open interest as directional and never labels public OHLCV as
institutional accumulation. Outputs are descriptive research states with zero live weight.
"""
from __future__ import annotations
from math import isfinite
from typing import Any, Mapping

VERSION='V60_MECHANICAL_FLOW_DRIVER_1'
LIVE_DECISION_WEIGHT=0.0
CAPITAL_PERMISSION='BLOCKED'


def _n(x:Any)->float|None:
    try:
        if x is None or isinstance(x,bool): return None
        v=float(x);return v if isfinite(v) else None
    except (TypeError,ValueError):return None

def _get(o:Mapping[str,Any],*names:str)->float|None:
    for k in names:
        v=_n(o.get(k))
        if v is not None:return v
    return None

def _z_or_pct(v:float|None, threshold:float)->bool:
    return v is not None and abs(v)>=threshold


def classify_mechanical_driver(market:str, observations:Mapping[str,Any]|None)->dict[str,Any]:
    o=dict(observations or {})
    price=_get(o,'price_change_pct','return_pct','price_change')
    oi=_get(o,'open_interest_change_pct','oi_change_pct','oi_change')
    taker=_get(o,'aggressor_imbalance','taker_buy_sell_imbalance','signed_trade_imbalance','signed_flow')
    long_liq=_get(o,'long_liquidation_notional','long_liquidations','long_liq')
    short_liq=_get(o,'short_liquidation_notional','short_liquidations','short_liq')
    funding=_get(o,'funding_z','funding_percentile','funding_rate_z')
    basis=_get(o,'basis_z','basis_percentile','annualized_basis_z')
    depth=_get(o,'depth_notional','market_depth_notional','depth_1pct')
    adv=_get(o,'adv_notional','daily_dollar_volume','turnover_notional')
    oi_notional=_get(o,'open_interest_notional','oi_notional')
    spot_perp=_get(o,'spot_perp_lead','spot_minus_perp_return','spot_perp_divergence')
    participant_long=_get(o,'participant_long_change','managed_money_long_change','leveraged_long_change')
    participant_short=_get(o,'participant_short_change','managed_money_short_change','leveraged_short_change')
    inventory=_get(o,'inventory_surprise','inventory_change_z')
    physical_basis=_get(o,'physical_basis_change','cash_premium_change','curve_change')
    revision=_get(o,'revision_change','earnings_revision_z','guidance_surprise_z')
    broker_flow=_get(o,'broker_net_flow_z','foreign_net_flow_z','signed_broker_flow')

    evidence=[]
    for k,v in [('price_change_pct',price),('oi_change',oi),('aggressor_imbalance',taker),('long_liquidation',long_liq),('short_liquidation',short_liq),('funding_state',funding),('basis_state',basis),('participant_long_change',participant_long),('participant_short_change',participant_short)]:
        if v is not None:evidence.append(f'{k}={v:.4g}')

    # Normalized forced-flow intensity. Missing depth/ADV remains missing.
    forced_total=(max(long_liq or 0.0,0.0)+max(short_liq or 0.0,0.0)) if (long_liq is not None or short_liq is not None) else None
    forced_to_depth=(forced_total/depth) if forced_total is not None and depth and depth>0 else None
    forced_to_adv=(forced_total/adv) if forced_total is not None and adv and adv>0 else None
    leverage_to_depth=(oi_notional/depth) if oi_notional is not None and depth and depth>0 else None

    # Directly observed forced transmission takes precedence; it is usually contemporaneous.
    if long_liq is not None and short_liq is not None and max(long_liq,short_liq)>0:
        ratio=(max(long_liq,short_liq)+1e-12)/(min(long_liq,short_liq)+1e-12)
        if long_liq>short_liq and ratio>=2:
            state='FORCED_LONG_UNWIND';direction='DOWN';timing='MOVE_UNDERWAY_OR_AMPLIFYING';boundary='Observed long liquidations are mechanical sell flow, but do not prove the original trigger.'
        elif short_liq>long_liq and ratio>=2:
            state='FORCED_SHORT_SQUEEZE';direction='UP';timing='MOVE_UNDERWAY_OR_AMPLIFYING';boundary='Observed short liquidations are mechanical buy flow, but do not prove the original trigger.'
        else:
            state='TWO_SIDED_FORCED_DELEVERAGING';direction='MIXED';timing='MOVE_UNDERWAY';boundary='Both sides liquidated materially; direction must be resolved by signed flow and price impact.'
    elif long_liq is not None and long_liq>0:
        state='FORCED_LONG_UNWIND';direction='DOWN';timing='MOVE_UNDERWAY_OR_AMPLIFYING';boundary='Observed long liquidation is sell pressure, usually not an early warning by itself.'
    elif short_liq is not None and short_liq>0:
        state='FORCED_SHORT_SQUEEZE';direction='UP';timing='MOVE_UNDERWAY_OR_AMPLIFYING';boundary='Observed short liquidation is buy pressure, usually not an early warning by itself.'
    # Signed participant books can resolve build/cover/unwind.
    elif participant_long is not None or participant_short is not None:
        l=participant_long or 0.0;s=participant_short or 0.0;scale=max(abs(l),abs(s),1.0)
        if l>0 and s<0 and abs(s)>=2*abs(l):state,direction='SHORT_COVERING','UP'
        elif l>0 and s<0 and abs(l)>=2*abs(s):state,direction='NEW_LONG_BUILD','UP'
        elif l>0 and s<0:state,direction='BULLISH_REPOSITIONING','UP'
        elif l<0 and s>0 and abs(l)>=2*abs(s):state,direction='LONG_LIQUIDATION','DOWN'
        elif l<0 and s>0 and abs(s)>=2*abs(l):state,direction='NEW_SHORT_BUILD','DOWN'
        elif l<0 and s>0:state,direction='BEARISH_REPOSITIONING','DOWN'
        elif l>0 and s>0:state,direction='TWO_SIDED_POSITION_BUILD','MIXED'
        elif l<0 and s<0:state,direction='TWO_SIDED_DELEVERAGING','MIXED'
        elif l>0:state,direction='NEW_LONG_BUILD','UP'
        elif s>0:state,direction='NEW_SHORT_BUILD','DOWN'
        elif l<0:state,direction='LONG_LIQUIDATION','DOWN'
        elif s<0:state,direction='SHORT_COVERING','UP'
        else:state,direction='NO_MATERIAL_PARTICIPANT_CHANGE','MIXED'
        timing='PRE_MOVE_POSSIBLE' if (price is None or abs(price)<2) and state in {'NEW_LONG_BUILD','NEW_SHORT_BUILD','BULLISH_REPOSITIONING','BEARISH_REPOSITIONING'} else 'STATE_OR_MOVE_UNDERWAY'
        boundary='Participant buckets resolve book changes, not beneficial-owner information advantage or future return.'
    # Signed aggressor flow + OI is stronger than the classic price/OI quadrant.
    elif taker is not None and oi is not None:
        if taker>0 and oi>0:state,direction='AGGRESSIVE_BUYING_WITH_NEW_RISK','UP'
        elif taker<0 and oi>0:state,direction='AGGRESSIVE_SELLING_WITH_NEW_RISK','DOWN'
        elif taker>0 and oi<0:state,direction='BUYING_DURING_DELEVERAGING','UP'
        elif taker<0 and oi<0:state,direction='SELLING_DURING_DELEVERAGING','DOWN'
        else:state,direction='MIXED_SIGNED_FLOW','MIXED'
        timing='PRE_MOVE_POSSIBLE' if price is None or abs(price)<2 else 'MOVE_UNDERWAY'
        boundary='Signed aggressor flow identifies the initiating trade side, not ultimate owner or persistence.'
    # OI alone remains explicitly ambiguous.
    elif oi is not None and price is not None:
        if oi>0 and price>0:state='PRICE_UP_OI_UP_AMBIGUOUS_NEW_RISK'
        elif oi>0 and price<0:state='PRICE_DOWN_OI_UP_AMBIGUOUS_NEW_RISK'
        elif oi<0 and price>0:state='PRICE_UP_OI_DOWN_DELEVERAGING'
        elif oi<0 and price<0:state='PRICE_DOWN_OI_DOWN_DELEVERAGING'
        else:state='FLAT_PRICE_OI_GEOMETRY'
        direction='AMBIGUOUS';timing='DESCRIPTIVE_ONLY';boundary='Every open contract has one long and one short; total OI cannot identify the aggressive side.'
    elif oi is not None:
        state='OPEN_INTEREST_ONLY';direction='AMBIGUOUS';timing='DESCRIPTIVE_ONLY';boundary='OI level/change measures outstanding risk, not direction.'
    else:
        state='NO_DERIVATIVES_ATTRIBUTION';direction='UNKNOWN';timing='UNKNOWN';boundary='Required signed positioning or liquidation data are absent.'

    # Pre-move cascade vulnerability: leverage/crowding can lead; realized liquidation cannot.
    crowd_votes=0
    if funding is not None and abs(funding)>=1.5:crowd_votes+=1
    if basis is not None and abs(basis)>=1.5:crowd_votes+=1
    if leverage_to_depth is not None and leverage_to_depth>=10:crowd_votes+=1
    if oi is not None and oi>=3:crowd_votes+=1
    aligned=False;vuln_dir='MIXED'
    if taker is not None and funding is not None:
        aligned=(taker>0 and funding>0) or (taker<0 and funding<0);vuln_dir='LONG_CROWDED' if taker>0 and funding>0 else ('SHORT_CROWDED' if taker<0 and funding<0 else 'MIXED')
    elif funding is not None:vuln_dir='LONG_CROWDED' if funding>0 else 'SHORT_CROWDED'
    if crowd_votes>=2 and (price is None or abs(price)<3):
        vulnerability='PRE_MOVE_LIQUIDATION_VULNERABILITY'
    elif crowd_votes>=2:vulnerability='CASCADE_AMPLIFICATION_RISK'
    elif crowd_votes==1:vulnerability='EARLY_CROWDING_RISK'
    else:vulnerability='NO_PROVEN_LIQUIDATION_VULNERABILITY'

    # Non-derivatives causal layers can override or originate the move.
    origin_votes=[]
    if revision is not None and abs(revision)>=1:origin_votes.append('EXPECTATIONS_REVISION')
    if broker_flow is not None and abs(broker_flow)>=1.5:origin_votes.append('SIGNED_BROKER_OR_FOREIGN_FLOW')
    if inventory is not None and abs(inventory)>=1:origin_votes.append('PHYSICAL_INVENTORY_SHOCK')
    if physical_basis is not None and abs(physical_basis)>=1:origin_votes.append('PHYSICAL_BASIS_OR_CURVE')
    if spot_perp is not None and abs(spot_perp)>=1:origin_votes.append('SPOT_PERP_LEAD_DIVERGENCE')

    completeness=sum(v is not None for v in [price,oi,taker,long_liq,short_liq,funding,basis,depth,oi_notional])/9
    confidence='HIGH' if completeness>=.75 and direction not in {'AMBIGUOUS','UNKNOWN'} else ('MEDIUM' if completeness>=.45 else 'LOW')
    return {
      'version':VERSION,'market':str(market).lower(),'driver_state':state,'mechanical_direction':direction,'timing_role':timing,
      'liquidation_vulnerability':vulnerability,'crowding_direction':vuln_dir,'crowding_votes':crowd_votes,'crowding_alignment':aligned,
      'forced_flow_to_depth':forced_to_depth,'forced_flow_to_adv':forced_to_adv,'open_interest_to_depth':leverage_to_depth,
      'candidate_origin_layers':origin_votes,'confidence':confidence,'evidence':evidence,'claim_boundary':boundary,
      'live_decision_weight':LIVE_DECISION_WEIGHT,'capital_permission':CAPITAL_PERMISSION,'proof_state':'NOT_PROVEN',
      'required_for_direction':['signed participant changes or signed aggressor flow','side-specific liquidations','price impact/depth normalization'],
      'required_for_early_warning':['leverage/OI at risk before liquidation','funding/basis/crowding','liquidation-distance distribution','trigger/origin layer','prospective outcome validation'],
    }
