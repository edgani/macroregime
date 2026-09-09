from __future__ import annotations
from datetime import datetime, timezone
from data_adapters import *

sec={"0":{"cik_str":123,"ticker":"abc","title":"ABC Inc"},"1":{"cik_str":456,"ticker":"XYZ","title":"XYZ Co"}}
df=parse_sec_company_tickers(sec)
assert list(df['ticker'])==['ABC','XYZ'] and df.iloc[0]['cik']=='0000000123'

facts={"facts":{"us-gaap":{"Revenues":{"units":{"USD":[
 {"val":100,"end":"2025-03-31","filed":"2025-05-01","form":"10-Q"},
 {"val":200,"end":"2025-06-30","filed":"2025-08-01","form":"10-Q"}
]}}}}}
pit=companyfacts_pit_values(facts,'Revenues',datetime(2025,6,1,tzinfo=timezone.utc),'USD')
assert len(pit)==1 and pit.iloc[0]['value']==100

csv='DATE,TEST\n2025-01-01,1.0\n2025-02-01,.\n2025-03-01,2.0\n'
s=parse_fredgraph_csv(csv,'TEST')
assert len(s)==2 and float(s.iloc[-1])==2.0

idx={"data":[{"KodeEmiten":"BBCA","NamaEmiten":"Bank Central Asia"},{"KodeEmiten":"TLKM","NamaEmiten":"Telkom"}]}
i=parse_idx_company_profiles(idx)
assert set(i['ticker'])=={'BBCA.JK','TLKM.JK'}

u=idx_financial_report_url(2025,report_type='rdf',code='BBCA')
assert 'GetFinancialReport' in u and 'BBCA' in u
payload={"Results":[{"KodeEmiten":"BBCA","FileModified":"2025-04-30T10:00:00Z"}]}
r=parse_idx_financial_reports(payload)
assert len(r)==1 and r.iloc[0]['code']=='BBCA'
print('TEST_DATA_ADAPTERS_PASS')
