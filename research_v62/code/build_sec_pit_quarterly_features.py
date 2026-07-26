"""Derive conservative PIT quarterly feature events from an SEC fact ledger.
No values are forward-filled before their `availability_date`; amendments are optional and off by default.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--ledger',required=True,type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--include-amendments',action='store_true');a=ap.parse_args()
    suffix=a.ledger.suffix.lower()
    if suffix=='.jsonl': df=pd.read_json(a.ledger,lines=True)
    elif suffix=='.csv': df=pd.read_csv(a.ledger)
    else:
        try: df=pd.read_parquet(a.ledger)
        except ImportError: raise SystemExit('Parquet engine unavailable; provide .csv or .jsonl ledger')
    df['availability_date']=pd.to_datetime(df['availability_date']);df['end']=pd.to_datetime(df['end']);df['start']=pd.to_datetime(df['start'])
    if not a.include_amendments:df=df[~df['is_amendment'].fillna(False)]
    # Keep facts with a clear reporting end and latest original accession filed on each availability date.
    df=df.dropna(subset=['ticker','end','value']).sort_values(['ticker','family','end','availability_date','accession'])
    df=df.drop_duplicates(['ticker','family','end'],keep='first')
    # Duration guard: use roughly quarterly observations for flows; instantaneous balance sheet items are allowed.
    duration=(df['end']-df['start']).dt.days
    flow={'revenue','gross_profit','operating_income','net_income','capex'}
    df=df[(~df['family'].isin(flow))|duration.between(70,110)]
    wide=df.pivot_table(index=['ticker','end','availability_date'],columns='family',values='value',aggfunc='last').reset_index().sort_values(['ticker','end'])
    g=wide.groupby('ticker',group_keys=False)
    for c in ['revenue','gross_profit','operating_income','net_income','inventory','capex','shares','debt_current','debt_long']:
        if c in wide:
            wide[f'{c}_yoy']=g[c].pct_change(4,fill_method=None)
            wide[f'{c}_qoq']=g[c].pct_change(1,fill_method=None)
    if {'gross_profit','revenue'}<=set(wide):wide['gross_margin']=wide['gross_profit']/wide['revenue'].replace(0,np.nan);wide['gross_margin_yoy_delta']=wide['gross_margin']-g['gross_margin'].shift(4)
    if {'operating_income','revenue'}<=set(wide):wide['operating_margin']=wide['operating_income']/wide['revenue'].replace(0,np.nan);wide['operating_margin_yoy_delta']=wide['operating_margin']-g['operating_margin'].shift(4)
    if {'inventory','revenue'}<=set(wide):wide['inventory_vs_revenue_yoy_gap']=wide.get('inventory_yoy')-wide.get('revenue_yoy')
    if {'shares'}<=set(wide):wide['share_supply_yoy']=wide.get('shares_yoy')
    wide['feature_availability_date']=wide['availability_date']
    a.output.parent.mkdir(parents=True,exist_ok=True)
    if a.output.suffix.lower()=='.csv': wide.to_csv(a.output,index=False)
    elif a.output.suffix.lower()=='.jsonl': wide.to_json(a.output,orient='records',lines=True,date_format='iso')
    else:
        try: wide.to_parquet(a.output,index=False)
        except ImportError: raise SystemExit('Parquet engine unavailable; use .csv or .jsonl output')
    print(json.dumps({'rows':len(wide),'tickers':wide.ticker.nunique(),'output':str(a.output),'availability_rule':'filing date only; no period-end lookahead'},indent=2))
if __name__=='__main__':main()
