from final_core.ticker_engine import qualify

def test():
    a=qualify([{'ticker':'ABC'}])[0]; assert a.action=='NO_RANK' and a.status=='NO_RANK'
    row={'ticker':'ABC','scenario_id':'S','asset':'A','revenue_exposure':.5,'margin_direction':'UP','fcf_quality':'GOOD','balance_sheet_quality':'GOOD','valuation_status':'NOT_FULLY_PRICED','catalyst':'X','price_data_status':'PIT','mechanism_validated':True,
         'p_mechanism_true':.7,'p_catalyst_within_horizon':.6,'p_not_fully_priced':.6,'p_trade_profitable_net':.6,'expected_win':.25,'expected_loss':-.12,'total_costs':.01}
    b=qualify([row])[0]; assert b.action=='BUILD' and b.ev_net>0
    row['p_not_fully_priced']=None; c=qualify([row])[0]; assert c.action=='NO_RANK'
if __name__=='__main__': test();print('TICKER_FAIL_CLOSED: PASS')
