"""Build a point-in-time SEC fact ledger from official local bulk archives.

Inputs are deliberately local files. Download companyfacts.zip and submissions.zip from SEC
outside this restricted runtime, then run this script. It never uses period end as availability;
`filed` is the earliest legal availability timestamp. Amendments remain separate observations.
"""
from __future__ import annotations
import argparse, csv, io, json, re, zipfile
from pathlib import Path
from typing import Iterable

DEFAULT_TAGS={
 'revenue':['RevenueFromContractWithCustomerExcludingAssessedTax','SalesRevenueNet','Revenues'],
 'gross_profit':['GrossProfit'],
 'operating_income':['OperatingIncomeLoss'],
 'net_income':['NetIncomeLoss','ProfitLoss'],
 'inventory':['InventoryNet'],
 'capex':['PaymentsToAcquirePropertyPlantAndEquipment'],
 'cash':['CashAndCashEquivalentsAtCarryingValue','CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents'],
 'equity':['StockholdersEquity'],
 'shares':['CommonStockSharesOutstanding','EntityCommonStockSharesOutstanding'],
 'debt_current':['LongTermDebtCurrent','ShortTermBorrowings'],
 'debt_long':['LongTermDebtNoncurrent'],
}
FORMS={'10-Q','10-Q/A','10-K','10-K/A','8-K','8-K/A'}

def norm_cik(x): return str(x).strip().zfill(10)
def iter_json(z:zipfile.ZipFile):
    for name in z.namelist():
        if name.lower().endswith('.json') and not name.endswith('/'):
            try: yield name,json.loads(z.read(name))
            except Exception: continue

def ticker_map(path:Path):
    d=json.loads(path.read_text())
    rows=d.get('data',d) if isinstance(d,dict) else d
    fields=d.get('fields') if isinstance(d,dict) else None
    out={}
    if fields and isinstance(rows,list):
        for r in rows:
            x=dict(zip(fields,r));out[norm_cik(x.get('cik'))]={'ticker':x.get('ticker'),'name':x.get('name'),'exchange':x.get('exchange')}
    elif isinstance(rows,dict):
        for x in rows.values(): out[norm_cik(x.get('cik_str'))]={'ticker':x.get('ticker'),'name':x.get('title'),'exchange':None}
    return out

def facts_for_company(cik,obj,tmap,tags):
    meta=tmap.get(cik,{})
    units=obj.get('facts',{}).get('us-gaap',{})
    for family,aliases in tags.items():
        for tag in aliases:
            fact=units.get(tag)
            if not fact: continue
            for unit,obs in fact.get('units',{}).items():
                for x in obs:
                    form=x.get('form')
                    filed=x.get('filed')
                    if form not in FORMS or not filed or x.get('val') is None: continue
                    yield {
                      'cik':cik,'ticker':meta.get('ticker'),'company_name':meta.get('name') or obj.get('entityName'),
                      'exchange':meta.get('exchange'),'family':family,'tag':tag,'unit':unit,'value':x.get('val'),
                      'start':x.get('start'),'end':x.get('end'),'filed':filed,'form':form,'fy':x.get('fy'),'fp':x.get('fp'),
                      'frame':x.get('frame'),'accession':x.get('accn'),'availability_date':filed,
                      'is_amendment':form.endswith('/A'),'source':'SEC_COMPANYFACTS_OFFICIAL'
                    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--companyfacts-zip',required=True,type=Path)
    ap.add_argument('--ticker-map-json',required=True,type=Path,help='Official SEC company_tickers_exchange.json or company_tickers.json')
    ap.add_argument('--output',required=True,type=Path)
    ap.add_argument('--tags-json',type=Path)
    a=ap.parse_args();tags=DEFAULT_TAGS if not a.tags_json else json.loads(a.tags_json.read_text());tm=ticker_map(a.ticker_map_json)
    rows=[]
    with zipfile.ZipFile(a.companyfacts_zip) as z:
        for name,obj in iter_json(z):
            m=re.search(r'CIK(\d{10})',name,re.I);cik=m.group(1) if m else norm_cik(obj.get('cik',''))
            if not cik.strip('0'): continue
            rows.extend(facts_for_company(cik,obj,tm,tags))
    rows.sort(key=lambda x:(x['availability_date'],x['cik'],x['family'],x.get('end') or '',x['accession'] or ''))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    suffix=a.output.suffix.lower()
    if suffix=='.jsonl':
        with a.output.open('w') as f:
            for r in rows:f.write(json.dumps(r,sort_keys=True)+'\n')
    else:
        import pandas as pd
        frame=pd.DataFrame(rows)
        if suffix=='.csv': frame.to_csv(a.output,index=False)
        else:
            try: frame.to_parquet(a.output,index=False)
            except ImportError: raise SystemExit('Parquet engine unavailable; use --output .csv or .jsonl')
    print(json.dumps({'rows':len(rows),'companies':len({r['cik'] for r in rows}),'earliest_availability':rows[0]['availability_date'] if rows else None,'latest_availability':rows[-1]['availability_date'] if rows else None,'output':str(a.output)},indent=2))
if __name__=='__main__':main()
