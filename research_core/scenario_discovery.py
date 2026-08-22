from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'FINAL_HANDOFF'
OUT.mkdir(parents=True, exist_ok=True)

ALLOWED_EVENT_TYPES = {
    'DEMAND_SHOCK','INFLATION_SHOCK','LABOR_SHOCK','POLICY','REGULATORY_CHANGE',
    'SECURITIZATION','CAPITAL_FORMATION','IPO','INDEX_MECHANICS','FUNDING','CREDIT',
    'PHYSICAL_CONSTRAINT','GEOPOLITICAL','MARKET_STRUCTURE','HOUSING','FISCAL','SUPPLY_SHOCK',
    'LIQUIDITY','RATES','BANKING','ENERGY','INDUSTRIAL_METALS','GOLD','FX','CHINA','INDONESIA',
    'JAPAN','EUROZONE','CRYPTO','SHIPPING','INVENTORY','CAPACITY','EARNINGS','VALUATION'
}

@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    event_type: str
    as_of: str
    claim: str
    verified_fact: str | None
    source_class: str
    source: str
    verified: bool
    actor: str
    incentive: str
    constraint: str
    direction: str = 'MIXED'
    horizon: str = 'UNKNOWN'
    notes: str = ''

@dataclass
class Scenario:
    scenario_id: str
    title: str
    causal_chain: list[str]
    actors: list[str]
    incentives: list[str]
    constraints: list[str]
    prerequisites: list[str]
    confirming_evidence: list[str]
    contradicting_evidence: list[str]
    next_discriminating_data: list[str]
    probability: float | None
    probability_status: str
    timing: str
    duration: str
    beneficiaries: list[str]
    losers: list[str]
    priced_in_status: str
    production_action: str
    invalidation: list[str]
    roles: list[str]
    evidence_ids: list[str]
    analogue_status: str = 'NONE'
    caveat: str = ''
    discovery_mode: str = 'GENERAL_RULE_GRAPH'


def _uniq(xs: Iterable[str]) -> list[str]:
    return list(dict.fromkeys([str(x) for x in xs if x]))


def _mk(sid, title, ev, *, chain, prereq, confirm, contradict, next_data,
        beneficiaries=None, losers=None, roles=None, analogue='NONE', caveat=''):
    return Scenario(
        scenario_id=sid,title=title,causal_chain=chain,
        actors=_uniq([e.actor for e in ev]), incentives=_uniq([e.incentive for e in ev]),
        constraints=_uniq([e.constraint for e in ev]), prerequisites=prereq,
        confirming_evidence=confirm, contradicting_evidence=contradict,
        next_discriminating_data=next_data, probability=None,
        probability_status='UNKNOWN_UNCALIBRATED', timing='UNKNOWN_UNCALIBRATED',
        duration='UNKNOWN_UNCALIBRATED', beneficiaries=beneficiaries or [], losers=losers or [],
        priced_in_status='UNKNOWN_REQUIRES_PRICED_IN_ENGINE', production_action='RESEARCH_ONLY_NO_TRADE',
        invalidation=list(contradict), roles=roles or ['SCENARIO_DISCRIMINATOR'],
        evidence_ids=[e.evidence_id for e in ev], analogue_status=analogue, caveat=caveat,
    )

# Generic causal templates. These are mechanism hypotheses, not conclusions.
RULES = [
    ({'FISCAL','FUNDING'}, 'SCN_FISCAL_FUNDING_STRESS', 'Fiscal supply can transmit into funding and term-premium stress',
     ['Large financing need increases duration/collateral supply','Dealer/intermediary balance-sheet capacity can become binding','Funding/term premium can tighten financial conditions'],
     ['persistent issuance','limited balance-sheet absorption'], ['auction weakness','repo/basis stress','term-premium rise'], ['strong auctions','ample dealer/reserve capacity'], ['auction tails','dealer take','repo','basis','term premium'], ['FRAGILITY','FUNDING','FISCAL']),
    ({'SUPPLY_SHOCK','PHYSICAL_CONSTRAINT'}, 'SCN_PHYSICAL_SUPPLY_CONSTRAINT', 'Supply shock can become a persistent physical bottleneck',
     ['Supply shock reduces available flow','Low inventory/capacity limits substitution','Physical premium and downstream margin pressure can persist'],
     ['inventory/capacity genuinely tight'], ['inventory draw','utilization high','physical premium','lead-time extension'], ['rapid substitution','inventory rebuild','capacity response'], ['inventory','capacity','utilization','imports/exports','lead times'], ['PHYSICAL_CONSTRAINT','BOTTLENECK','ASSET_DRIVER']),
    ({'GEOPOLITICAL','SUPPLY_SHOCK'}, 'SCN_GEOPOLITICAL_SUPPLY_TRANSMISSION', 'Geopolitical shock can propagate through physical supply and logistics',
     ['Geopolitical restriction changes route/access/risk','Supply/logistics cost rises','Downstream users face margin/availability pressure'],
     ['material exposed supply share'], ['shipping reroutes','insurance/freight rise','exports fall'], ['route normalizes','spare capacity offsets loss'], ['exports','freight','insurance','spare capacity','inventory'], ['EARLY_WARNING','PHYSICAL_CONSTRAINT']),
    ({'DEMAND_SHOCK','CREDIT'}, 'SCN_DEMAND_CREDIT_FEEDBACK', 'Demand weakness can amplify through credit availability and balance sheets',
     ['Demand weakens cash flow','Lenders tighten as risk rises','Credit contraction feeds back into demand'],
     ['weak demand persists','credit-sensitive borrowers'], ['loan standards tighten','delinquencies rise','credit growth slows'], ['credit remains loose','income/cash flow recovers'], ['SLOOS','loan growth','delinquencies','defaults'], ['FRAGILITY','CREDIT','GROWTH']),
    ({'POLICY'}, 'SCN_POLICY_REACTION_FUNCTION', 'Policy path remains conditional on inflation, labor, growth and financial stability',
     ['Policy maker observes dual/mandate constraints','Reaction depends on persistence and balance of risks','Policy can remain restrictive or ease depending on new evidence'],
     ['credible policy reaction function'], ['official communication and realized data align'], ['policy communication/data diverge materially'], ['inflation','labor','growth','financial conditions','official communication'], ['POLICY_REACTION','STATE']),
    ({'CAPITAL_FORMATION','CREDIT'}, 'SCN_CAPITAL_FORMATION_CREDIT_CYCLE', 'Capital formation can create a credit-backed investment cycle with later refinancing risk',
     ['Investment boom raises financing demand','Credit funds capacity expansion','Returns depend on utilization/cash-flow realization','Refinancing risk rises if cash flows disappoint'],
     ['material debt-funded capex'], ['capex/backlog rise','credit issuance rises','utilization follows'], ['equity-funded capex','rapid cash-flow realization','deleveraging'], ['capex','issuance','backlog','utilization','interest coverage'], ['CAPITAL_FORMATION','CREDIT','FRAGILITY']),
    ({'LIQUIDITY','CRYPTO'}, 'SCN_CRYPTO_LIQUIDITY_TRANSMISSION', 'Liquidity conditions can transmit into crypto risk capacity',
     ['Liquidity/funding conditions alter marginal risk capacity','Stablecoin/ETF/on-chain flows determine crypto-specific transmission','Asset response requires independent validation'],
     ['measurable crypto-specific flow channel'], ['stablecoin/ETF inflows','basis/funding healthy'], ['liquidity rises without crypto flow','funding stress'], ['stablecoin supply','ETF flows','basis','funding','on-chain flows'], ['LIQUIDITY','ASSET_DRIVER']),
    ({'CHINA','INDUSTRIAL_METALS'}, 'SCN_CHINA_METALS_DEMAND', 'China activity/credit can transmit into industrial-metals demand if physical evidence confirms',
     ['China credit/activity changes end-demand','Inventory/imports/refining indicate physical transmission','Producer response determines duration'],
     ['China is material marginal demander'], ['imports rise','inventories draw','premiums strengthen'], ['imports fall','inventories build','supply response'], ['China credit','imports','warehouse inventory','premiums','treatment charges'], ['ASSET_DRIVER','PHYSICAL_DEMAND']),
]


def discover(events: list[Evidence]) -> list[Scenario]:
    for e in events:
        if e.event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError(f'Unsupported event_type {e.event_type}')
    facts=[e for e in events if e.verified]
    types={e.event_type for e in facts}
    out=[]

    # General rule-graph discovery.
    for need,sid,title,chain,prereq,confirm,contradict,next_data,roles in RULES:
        if need.issubset(types):
            ev=[e for e in facts if e.event_type in need]
            out.append(_mk(sid,title,ev,chain=chain,prereq=prereq,confirm=confirm,contradict=contradict,next_data=next_data,roles=roles))

    # Attachment acceptance patterns remain explicit high-detail specializations.
    if {'HOUSING','LABOR_SHOCK','INFLATION_SHOCK'}.issubset(types):
        ev=[e for e in facts if e.event_type in {'HOUSING','LABOR_SHOCK','INFLATION_SHOCK','POLICY','FISCAL'}]
        out.append(_mk('SCN_POLICY_CONFLICTED_REACTION_FUNCTION','Weak activity does not mechanically kill hawkish policy risk',ev,
            chain=['Housing/labor softness reduces demand pressure','Inflation persistence keeps price-stability constraint active','Policy reaction becomes two-sided','Long-end/fiscal stress can tighten conditions without a policy hike'],
            prereq=['activity softness persists','inflation remains uncomfortable'],
            confirm=['further labor/housing weakness','sticky core/services inflation','hawkish communication'],
            contradict=['broad disinflation with weaker activity','rapid inflation-expectation normalization'],
            next_data=['core services inflation','claims/payroll revisions','real consumption','housing transactions','policy communication','term premium'],
            roles=['STATE','SCENARIO_DISCRIMINATOR','POLICY_REACTION'], caveat='Weak activity alone does not imply dovish policy.'))

    if 'IPO' in types:
        ev=[e for e in facts if e.event_type in {'IPO','INDEX_MECHANICS','CAPITAL_FORMATION'}]
        out.append(_mk('SCN_MEGA_IPO_CAPITAL_SUPPLY_INDEX_REFLEXIVITY','Mega IPO can alter equity supply, passive-flow mechanics and liquidity rotation',ev,
            chain=['Large issuer seeks public capital/liquidity','IPO adds equity supply','Index inclusion can create mechanical demand only if eligibility is met','Issuance may rotate liquidity from incumbents'],
            prereq=['IPO files/prices','valuation material','eligibility conditions met where relevant'],
            confirm=['official filing','book terms','index notice','rebalance flow'], contradict=['delay/cancel','valuation cut','eligibility failure','weak book'],
            next_data=['S-1/F-1','share count/free float','offering size','lockups','index methodology','passive AUM'],
            roles=['CAPITAL_FORMATION','FLOW','PRICED_IN_CONTEXT'], caveat='Any obligation to keep an index elevated is an unverified motive claim and must not enter production.'))

    if {'REGULATORY_CHANGE','SECURITIZATION'}.issubset(types) or {'SECURITIZATION','CREDIT'}.issubset(types):
        ev=[e for e in facts if e.event_type in {'REGULATORY_CHANGE','SECURITIZATION','CREDIT','CAPITAL_FORMATION','FUNDING'}]
        out.append(_mk('SCN_AI_DATACENTER_LEVERAGE_FRAGILITY','AI/data-center financing may build fragility without implying a 2008 repeat',ev,
            chain=['Infrastructure capex requires financing','Debt/SPV/securitization distributes exposure','Opacity/leverage can increase','If underwriting weakens and refinancing dependence rises losses can propagate','Crisis requires trigger + realized losses + forced transmission'],
            prereq=['rapid leverage growth','weak underwriting','opaque distribution','refinancing dependence'],
            confirm=['spread widening','downgrades/defaults','lease failure','refinancing stress'], contradict=['strong contracted cash flow','equity cushion','stable spreads'],
            next_data=['issuance','LTV/DSCR/covenants','tenant concentration','lease tenor vs debt tenor','credit spreads','defaults'],
            roles=['FRAGILITY','EARLY_WARNING','CREDIT','FUNDING'], analogue='2008_ANALOGUE_CANDIDATE_NOT_EQUIVALENCE',
            caveat='Analogue is an investigation trigger, not a forecast of another 2008.'))

    if 'MARKET_STRUCTURE' in types:
        ev=[e for e in facts if e.event_type=='MARKET_STRUCTURE']
        out.append(_mk('SCN_DEALER_GAMMA_VOLATILITY_REGIME','Dealer gamma may modify short-horizon volatility/execution, not macro direction',ev,
            chain=['Options positioning changes hedge sensitivity','Gamma state can amplify/dampen realized volatility','This is timing/execution context only'],
            prereq=['reliable PIT options history','validated methodology'], confirm=['OOS realized-vol relationship','cross-provider robustness'],
            contradict=['provider disagreement','unstable sign conventions','no OOS relationship'], next_data=['PIT OI/greeks','dealer assumptions','realized vol','0DTE share'],
            roles=['MARKET_STRUCTURE_TIMING_MODIFIER','FRAGILITY_MODIFIER','EXECUTION_CONTEXT'], caveat='Research diagnostic only; must never become standalone directional macro alpha.'))

    # De-duplicate by scenario_id; specializations win if duplicated later.
    dedup={s.scenario_id:s for s in out}
    return list(dedup.values())


def save(events, scenarios):
    (OUT/'32_CURRENT_EVIDENCE.json').write_text(json.dumps([asdict(x) for x in events],indent=2),encoding='utf-8')
    (OUT/'34_SCENARIO_REGISTRY.json').write_text(json.dumps([asdict(x) for x in scenarios],indent=2),encoding='utf-8')

if __name__=='__main__':
    p=ROOT/'data'/'current'/'evidence.json'
    raw=json.loads(p.read_text())
    ev=[Evidence(**x) for x in raw]
    sc=discover(ev); save(ev,sc); print(json.dumps([asdict(x) for x in sc],indent=2))
