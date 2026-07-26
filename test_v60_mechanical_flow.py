from mechanical_flow_driver import classify_mechanical_driver as c

def check(name,obs,state,direction=None,vulnerability=None):
    r=c('crypto',obs);assert r['driver_state']==state,(name,r)
    if direction:assert r['mechanical_direction']==direction,(name,r)
    if vulnerability:assert r['liquidation_vulnerability']==vulnerability,(name,r)

check('oi only',{'open_interest_change_pct':5},'OPEN_INTEREST_ONLY','AMBIGUOUS')
check('price oi up',{'price_change_pct':3,'open_interest_change_pct':5},'PRICE_UP_OI_UP_AMBIGUOUS_NEW_RISK','AMBIGUOUS')
check('signed buy new risk',{'price_change_pct':.5,'open_interest_change_pct':4,'aggressor_imbalance':.7},'AGGRESSIVE_BUYING_WITH_NEW_RISK','UP')
check('signed sell new risk',{'price_change_pct':-.5,'open_interest_change_pct':4,'aggressor_imbalance':-.7},'AGGRESSIVE_SELLING_WITH_NEW_RISK','DOWN')
check('long liq',{'long_liquidation_notional':100,'short_liquidation_notional':10},'FORCED_LONG_UNWIND','DOWN')
check('short squeeze',{'long_liquidation_notional':10,'short_liquidation_notional':100},'FORCED_SHORT_SQUEEZE','UP')
check('two sided',{'long_liquidation_notional':100,'short_liquidation_notional':70},'TWO_SIDED_FORCED_DELEVERAGING','MIXED')
check('short covering',{'participant_long_change':10,'participant_short_change':-100},'SHORT_COVERING','UP')
check('new longs',{'participant_long_change':100,'participant_short_change':-10},'NEW_LONG_BUILD','UP')
check('new shorts',{'participant_long_change':-10,'participant_short_change':100},'NEW_SHORT_BUILD','DOWN')
check('long liquidation books',{'participant_long_change':-100,'participant_short_change':10},'LONG_LIQUIDATION','DOWN')
check('mixed build',{'participant_long_change':100,'participant_short_change':80},'TWO_SIDED_POSITION_BUILD','MIXED')
check('pre cascade',{'price_change_pct':.2,'open_interest_change_pct':5,'funding_z':2,'basis_z':2,'aggressor_imbalance':.6},'AGGRESSIVE_BUYING_WITH_NEW_RISK','UP','PRE_MOVE_LIQUIDATION_VULNERABILITY')
r=c('crypto',{'long_liquidation_notional':100,'short_liquidation_notional':0,'depth_notional':20,'adv_notional':1000});assert abs(r['forced_flow_to_depth']-5)<1e-9 and abs(r['forced_flow_to_adv']-.1)<1e-9
r=c('us',{'revision_change':2});assert 'EXPECTATIONS_REVISION' in r['candidate_origin_layers'] and r['live_decision_weight']==0
print('15/15 PASS')
