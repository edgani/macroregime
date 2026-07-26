"""CLI for the V6.6 monthly US broad-equity risk cap.

Example:
  python run_v66_risk_cap.py --csv monthly_prices.csv --as-of 2026-07-26
CSV columns: Date, Close (or SP500).
"""
from __future__ import annotations
import argparse,json
import pandas as pd
from us_equity_risk_cap_v66 import evaluate_monthly_risk_cap

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--csv',required=True);ap.add_argument('--as-of',required=True);ap.add_argument('--max-staleness-months',type=int,default=1);a=ap.parse_args()
    d=pd.read_csv(a.csv);date_col='Date' if 'Date' in d else 'observed_month';close_col='Close' if 'Close' in d else ('SP500' if 'SP500' in d else 'close')
    rows=[{'observed_month':str(x[date_col]),'close':x[close_col]} for _,x in d.iterrows()]
    out=evaluate_monthly_risk_cap(rows,as_of=a.as_of,max_staleness_months=a.max_staleness_months)
    print(json.dumps(out.to_dict(),indent=2,sort_keys=True))
if __name__=='__main__':main()
