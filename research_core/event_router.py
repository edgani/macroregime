"""Conservative text-to-event-family router.
Routes claims to verification candidates only. Never converts a headline directly into a fact, probability, asset or ticker.
"""
from __future__ import annotations
import re

RULES = [
 ('HOUSING',[r'homebuyer',r'home sales?',r'housing',r'mortgage',r'home starts?',r'pending home',r'home data']),
 ('INFLATION_SHOCK',[r'\bcpi\b',r'\bppi\b',r'inflation',r'prices?',r'breakeven']),
 ('LABOR_SHOCK',[r'\bnfp\b',r'payroll',r'unemployment',r'jobless',r'claims?',r'jolts',r'jobs?']),
 ('POLICY',[r'hawkish',r'dovish',r'\bfed\b',r'fomc',r'rate hike',r'rate cut',r'central bank',r'policy rate']),
 ('IPO',[r'\bipo\b',r'public offering',r'go public',r'listing']),
 ('CAPITAL_FORMATION',[r'revenue run rate',r'valuation',r'fundraising',r'capital',r'issuance',r'capex',r'project finance']),
 ('INDEX_MECHANICS',[r'index',r'nasdaq[- ]?100',r's&p 500',r'passive',r'rebalance',r'fast entry']),
 ('REGULATORY_CHANGE',[r'\bsec\b',r'regulat',r'disclosure',r'investor protection',r'no[- ]action',r'export control',r'sanction']),
 ('SECURITIZATION',[r'securiti[sz]ation',r'asset[- ]backed',r'\babs\b',r'\bspv\b',r'structured finance']),
 ('CREDIT',[r'credit',r'debt',r'bond',r'leverage',r'refinanc',r'default',r'downgrade',r'spread']),
 ('FUNDING',[r'repo',r'funding',r'basis',r'cross.?currency',r'swap spread',r'liquidity squeeze']),
 ('FISCAL',[r'fiscal',r'deficit',r'treasury issuance',r'auction',r'debt ceiling',r'government spending']),
 ('LIQUIDITY',[r'liquidity',r'bank reserves?',r'rrp',r'reverse repo',r'\btga\b',r'money supply',r'\bm2\b']),
 ('RATES',[r'yield curve',r'10.?year',r'2.?year',r'term premium',r'real yield']),
 ('MARKET_STRUCTURE',[r'\bgex\b',r'gamma',r'put.?call',r'options? flow',r'dealer',r'0dte',r'\bvix\b']),
 ('PHYSICAL_CONSTRAINT',[r'power grid',r'electricity',r'capacity',r'bottleneck',r'water',r'transformer',r'shortage',r'lead time']),
 ('SUPPLY_SHOCK',[r'supply shock',r'outage',r'production cut',r'strike',r'embargo',r'export ban',r'disruption']),
 ('DEMAND_SHOCK',[r'demand shock',r'demand collapse',r'orders? fall',r'consumption weak',r'sales decline']),
 ('GEOPOLITICAL',[r'war',r'conflict',r'geopolit',r'sanction',r'blockade',r'strait',r'tariff']),
 ('INVENTORY',[r'inventor(?:y|ies)',r'stockpile',r'warehouse stock',r'days.?of.?cover']),
 ('CAPACITY',[r'capacity',r'utilization',r'spare capacity',r'plant expansion']),
 ('SHIPPING',[r'freight',r'shipping',r'port congestion',r'canal',r'ton.?mile',r'vessel']),
 ('ENERGY',[r'\boil\b',r'\bwti\b',r'brent',r'natural gas',r'lng',r'opec',r'refinery']),
 ('INDUSTRIAL_METALS',[r'copper',r'aluminum',r'aluminium',r'nickel',r'zinc',r'lme']),
 ('GOLD',[r'\bgold\b',r'precious metal',r'central bank gold',r'sge']),
 ('FX',[r'fx',r'foreign exchange',r'usd',r'dollar index',r'reer',r'currency intervention']),
 ('CHINA',[r'china',r'pbo[c|c]',r'safe',r'caixin',r'china credit',r'tsf']),
 ('INDONESIA',[r'indonesia',r'bank indonesia',r'\bbi rate\b',r'\bidx\b',r'\bbps\b',r'\bojk\b']),
 ('JAPAN',[r'japan',r'boj',r'jgb',r'\byen\b',r'\bjpy\b']),
 ('EUROZONE',[r'eurozone',r'\becb\b',r'eurostat',r'\beur\b']),
 ('CRYPTO',[r'bitcoin',r'\bbtc\b',r'ethereum',r'\beth\b',r'stablecoin',r'defi',r'on.?chain']),
 ('EARNINGS',[r'earnings',r'revenue',r'margin',r'free cash flow',r'guidance',r'backlog']),
 ('VALUATION',[r'valuation',r'earnings yield',r'cape',r'free cash flow yield',r'erp']),
]

def route(text:str):
    t=text.lower(); hits=[]
    for event_type,patterns in RULES:
        m=[p for p in patterns if re.search(p,t,re.I)]
        if m:hits.append({'event_type':event_type,'matched_patterns':m,'status':'CANDIDATE_REQUIRES_VERIFICATION'})
    return {'raw_text':text,'candidate_event_types':hits,'production_eligible':False,
            'rule':'CLAIM -> EVENT CANDIDATES -> PRIMARY-SOURCE VERIFICATION -> CAUSAL SCENARIOS -> CALIBRATION -> ASSET/TICKER; never headline -> trade'}
