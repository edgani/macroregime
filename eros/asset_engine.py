from __future__ import annotations

ASSET_MAP={
 'SCN_POLICY_CONFLICT':[('US Treasury duration','TLT','Rates/discount-rate transmission'),('US credit','HYG','Credit-spread transmission'),('USD','UUP','Relative policy/rate transmission')],
 'SCN_FISCAL_ABSORPTION':[('US Treasury duration','TLT','Term-premium/auction absorption'),('US credit','HYG','Funding-to-credit transmission'),('USD','UUP','Funding/rate differential context')],
 'SCN_LIQUIDITY_CREDIT':[('US credit','HYG','Liquidity-to-credit transmission'),('Bitcoin','BTC-USD','Liquidity can matter only with crypto-specific flow confirmation')],
 'RADAR_AI_CAPITAL':[('US AI equity complex','SMH','AI capital formation / equity-supply / earnings transmission'),('Power infrastructure','VRT/ETN','AI capacity buildout transmission')],
 'RADAR_AI_CREDIT':[('Data-center infrastructure','DLR/EQIX/VRT','Financing/refinancing/tenant exposure'),('US credit','HYG','Credit-spread transmission if stress broadens')],
 'RADAR_CHINA_GOLD':[('Gold','GC=F','Official/physical demand vs real-yield/USD/supply reconciliation')],
 'RADAR_ENERGY_SUPPLY':[('Oil','CL=F','Physical supply/inventory/spare-capacity transmission')],
 'RADAR_FISCAL_FUNDING':[('US Treasury duration','TLT','Auction/term-premium/funding transmission')],
 'RADAR_INDONESIA':[('IHSG','^JKSE','Local growth/FX/flow/commodity transmission'),('IDR','USDIDR=X','BI/reserve/current-account/flow transmission')],
}

def generate_assets(verified_scenarios,radar_scenarios):
    rows=[]
    allsc=[]
    for s in verified_scenarios: allsc.append((s.scenario_id,s.title,'VERIFIED_EVIDENCE'))
    for s in radar_scenarios: allsc.append((s.get('scenario_id'),s.get('title'),'UNVERIFIED_LEAD'))
    for sid,title,level in allsc:
        entries=ASSET_MAP.get(sid,[])
        # Generic graph fallbacks
        if not entries and sid and 'INDUSTRIAL_METALS' in sid: entries=[('Copper','HG=F','Physical-demand/inventory/capacity transmission')]
        if not entries and sid and 'CRYPTO' in sid: entries=[('Bitcoin','BTC-USD','Crypto-specific liquidity/funding transmission')]
        if not entries and sid and 'CREDIT' in sid: entries=[('US credit','HYG','Credit-spread transmission')]
        for asset,instrument,mechanism in entries:
            rows.append({'scenario_id':sid,'scenario_title':title,'asset':asset,'instrument':instrument,'mechanism':mechanism,'evidence_level':level,'conditional_payoff_validation':'REQUIRED','priced_in_status':'UNKNOWN','action':'VERIFY/RESEARCH' if level=='UNVERIFIED_LEAD' else 'WATCH/RESEARCH'})
    return rows
