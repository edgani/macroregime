from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from final_core.scenario_discovery import Evidence, discover

ev=[Evidence(**x) for x in json.loads((ROOT/'data/current/evidence.json').read_text())]
sc={s.scenario_id:s for s in discover(ev)}

# Acceptance 1: soft housing/labor + sticky inflation/policy conflict must NOT mechanically kill hawkish risk.
s=sc['SCN_POLICY_CONFLICTED_REACTION_FUNCTION']
text=' '.join(s.causal_chain+s.caveat.splitlines()).lower()
assert 'does not mechanically kill' in s.title.lower() or 'do not imply' in s.caveat.lower() or 'two-sided' in text
assert s.probability is None and s.probability_status=='UNKNOWN_UNCALIBRATED'
assert s.production_action=='RESEARCH_ONLY_NO_TRADE'

# Acceptance 2: mega IPO produces capital formation/index-flow scenario, not an obligation/conspiracy claim.
s=sc['SCN_MEGA_IPO_CAPITAL_SUPPLY_INDEX_REFLEXIVITY']
assert 'obligation' in s.caveat.lower() and 'unverified' in s.caveat.lower()
assert 'CAPITAL_FORMATION' in s.roles
assert s.probability is None

# Acceptance 3: data-center financing may be 2008 analogue candidate but not equivalence/inevitability.
s=sc['SCN_AI_DATACENTER_LEVERAGE_FRAGILITY']
assert s.analogue_status=='2008_ANALOGUE_CANDIDATE_NOT_EQUIVALENCE'
assert 'not a forecast' in s.caveat.lower()
assert {'FRAGILITY','CREDIT','FUNDING'}.issubset(set(s.roles))
assert s.probability is None

# Acceptance 4: GEX/options flow is timing/fragility/execution only, never directional macro alpha.
s=sc['SCN_DEALER_GAMMA_VOLATILITY_REGIME']
assert set(s.roles)=={'MARKET_STRUCTURE_TIMING_MODIFIER','FRAGILITY_MODIFIER','EXECUTION_CONTEXT'}
assert 'never become standalone directional macro alpha' in s.caveat.lower()
assert s.production_action=='RESEARCH_ONLY_NO_TRADE'

# Global guard: no uncalibrated numeric probabilities or forced trade actions.
for s in sc.values():
    assert s.probability is None
    assert s.production_action in {'RESEARCH_ONLY_NO_TRADE','WAIT','NO_QUALIFIED_OPPORTUNITY'}

print(f'PASS: {len(sc)} attachment-driven scenario acceptance cases')
