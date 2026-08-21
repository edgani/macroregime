from __future__ import annotations
from dataclasses import dataclass,asdict
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

@dataclass
class AssetCandidate:
    scenario_id:str; asset:str; mechanism:str; required_engine:str; evidence_status:str
    priced_in_status:str='UNKNOWN'; conditional_payoff_status:str='UNVALIDATED'; action:str='RESEARCH_ONLY'

SCENARIO_ASSET_MAP={
 'SCN_PHYSICAL_SUPPLY_CONSTRAINT':[('COPPER','Physical scarcity may transmit to copper if inventory/demand evidence is copper-specific','COPPER_ASSET_TRANSMISSION')],
 'SCN_CHINA_METALS_DEMAND':[('COPPER','China physical demand may transmit through imports/inventory/premiums','COPPER_ASSET_TRANSMISSION')],
 'SCN_POLICY_CONFLICTED_REACTION_FUNCTION':[('US_EQUITY','Restrictive real/nominal rates can alter equity discount-rate and earnings transmission','US_EQUITY_ASSET_TRANSMISSION')],
 'SCN_POLICY_REACTION_FUNCTION':[('US_EQUITY','Policy affects discount rates and macro cash-flow conditions','US_EQUITY_ASSET_TRANSMISSION')],
}

def candidate_assets(scenarios,validation_summary_path=None):
    supported=set()
    if validation_summary_path and Path(validation_summary_path).exists():
        data=json.loads(Path(validation_summary_path).read_text()); supported=set(data.get('engines',[]))
    out=[]
    for s in scenarios:
        sid=s.scenario_id if hasattr(s,'scenario_id') else s.get('scenario_id')
        for asset,mechanism,eng in SCENARIO_ASSET_MAP.get(sid,[]):
            st='HISTORICAL_ENGINE_EXISTS_SCOPE_LIMITED' if eng in supported else 'NO_VALIDATED_TRANSMISSION_ENGINE'
            out.append(AssetCandidate(sid,asset,mechanism,eng,st))
    return out
