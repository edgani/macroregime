from final_core.event_router import route
CASES={
 'Treasury auction tails as repo funding tightens':{'FISCAL','FUNDING'},
 'Copper inventories fall after mine outage and China demand':{'INDUSTRIAL_METALS','INVENTORY','SUPPLY_SHOCK','CHINA'},
 'Oil shipping disrupted by geopolitical conflict':{'ENERGY','SHIPPING','GEOPOLITICAL'},
 'Stablecoin liquidity expands with bitcoin ETF demand':{'CRYPTO','LIQUIDITY'},
 'Indonesia BI rate and IDX foreign flow':{'INDONESIA'},
}
def test():
  for txt,need in CASES.items():
    got={x['event_type'] for x in route(txt)['candidate_event_types']}; assert need.issubset(got),(txt,need,got)
    assert not route(txt)['production_eligible']
if __name__=='__main__':test();print('EVENT_ROUTER_GENERAL: PASS',len(CASES))
