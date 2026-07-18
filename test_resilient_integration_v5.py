from __future__ import annotations

from unittest.mock import patch
import numpy as np
import pandas as pd

import data_layer
from data.resilient_market_data import MarketBundle, TickerHealth


def frame(seed: int, n=280):
    rng=np.random.default_rng(seed)
    idx=pd.date_range('2025-01-01',periods=n,freq='B')
    close=100*np.exp(np.cumsum(rng.normal(0.0003,0.01,n)))
    return pd.DataFrame({'Open':close*0.999,'High':close*1.01,'Low':close*0.99,'Close':close,'Volume':1_000_000},index=idx)


def fake_bundle(tickers, market=None, days=756, force_refresh=False):
    frames={}
    health={}
    for i,t in enumerate(tickers):
        f=frame(i+10)
        frames[t]=f
        health[t]=TickerHealth(t,market,'LIVE_REFRESHED','unit','2026-07-18T00:00:00Z',f.index[-1].isoformat(),0.0,len(f),[])
    return MarketBundle(market,frames,health,{'unit':len(frames)},len(frames),0,0,0,len(frames),'2026-07-18T00:00:00Z')


def test_resilient_load_all_isolated_markets():
    import warroom.data as wd
    small_universe={
        'us':['AAPL','MSFT','SPY'], 'idx':['BBCA.JK','BMRI.JK'],
        'crypto':['BTC-USD','ETH-USD'], 'commodity':['CL=F','GC=F'],
        'fx':['EURUSD=X','USDJPY=X'],
    }
    with patch.object(wd,'US_UNIVERSE',small_universe['us']), \
         patch.object(wd,'IDX_UNIVERSE',small_universe['idx']), \
         patch.object(data_layer,'UNIVERSE',small_universe), \
         patch('data.loader.load_market',side_effect=fake_bundle), \
         patch('data.loader.clear_memory_cache'), \
         patch('data.fred_loader.load_fred_series',return_value={}), \
         patch.object(data_layer,'_load_feeds',return_value={'_status':{}}), \
         patch('gcfis.feeds.typef_idx.build_typef',return_value=({},'disabled')), \
         patch('engines.treasury_liquidity.analyze_liquidity',return_value={'ok':False}):
        data=data_layer.load_all(markets=list(small_universe),allow_live=True)
    assert data['overall_source']=='RESILIENT_DAILY'
    assert all(data['prices'][m] for m in small_universe)
    assert data['bench'] is not None
    assert all(data['market_meta'][m]['status']=='LIVE_REFRESHED' for m in small_universe)
