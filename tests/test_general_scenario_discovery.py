from final_core.scenario_discovery import Evidence, discover

def ev(i,t):
    return Evidence(str(i),t,'2026-08-22',t,t,'official','test',True,'actor','incentive','constraint')

CASES=[
    (['FISCAL','FUNDING'],'SCN_FISCAL_FUNDING_STRESS'),
    (['SUPPLY_SHOCK','PHYSICAL_CONSTRAINT'],'SCN_PHYSICAL_SUPPLY_CONSTRAINT'),
    (['GEOPOLITICAL','SUPPLY_SHOCK'],'SCN_GEOPOLITICAL_SUPPLY_TRANSMISSION'),
    (['DEMAND_SHOCK','CREDIT'],'SCN_DEMAND_CREDIT_FEEDBACK'),
    (['POLICY'],'SCN_POLICY_REACTION_FUNCTION'),
    (['CAPITAL_FORMATION','CREDIT'],'SCN_CAPITAL_FORMATION_CREDIT_CYCLE'),
    (['LIQUIDITY','CRYPTO'],'SCN_CRYPTO_LIQUIDITY_TRANSMISSION'),
    (['CHINA','INDUSTRIAL_METALS'],'SCN_CHINA_METALS_DEMAND'),
]

def test_generalized_cases():
    for j,(types,expected) in enumerate(CASES):
        out=discover([ev(f'{j}-{i}',t) for i,t in enumerate(types)])
        assert expected in {x.scenario_id for x in out}, (types,[x.scenario_id for x in out])
        s=[x for x in out if x.scenario_id==expected][0]
        assert s.probability is None
        assert s.production_action=='RESEARCH_ONLY_NO_TRADE'
        assert s.next_discriminating_data

if __name__=='__main__':
    test_generalized_cases(); print('GENERAL_SCENARIO_DISCOVERY: PASS',len(CASES),'cases')
