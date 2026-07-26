import json, subprocess, sys, tempfile, zipfile
from pathlib import Path
import pandas as pd
ROOT=Path(__file__).resolve().parent
with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    tick={'fields':['cik','name','ticker','exchange'],'data':[[1,'Test Co','TEST','NYSE']]}
    (td/'tickers.json').write_text(json.dumps(tick))
    def obs(start,end,filed,val,accn,form='10-Q',fy=2020,fp='Q1'):
        return {'start':start,'end':end,'filed':filed,'val':val,'accn':accn,'form':form,'fy':fy,'fp':fp}
    facts={'cik':1,'entityName':'Test Co','facts':{'us-gaap':{
      'RevenueFromContractWithCustomerExcludingAssessedTax':{'units':{'USD':[
        obs('2020-01-01','2020-03-31','2020-05-05',100,'a1'),obs('2020-04-01','2020-06-30','2020-08-04',130,'a2',fy=2020,fp='Q2'),
        obs('2021-01-01','2021-03-31','2021-05-04',160,'a3',fy=2021,fp='Q1'),obs('2021-04-01','2021-06-30','2021-08-03',200,'a4',fy=2021,fp='Q2')] }},
      'GrossProfit':{'units':{'USD':[
        obs('2020-01-01','2020-03-31','2020-05-05',30,'b1'),obs('2020-04-01','2020-06-30','2020-08-04',45,'b2',fy=2020,fp='Q2'),
        obs('2021-01-01','2021-03-31','2021-05-04',64,'b3',fy=2021,fp='Q1'),obs('2021-04-01','2021-06-30','2021-08-03',90,'b4',fy=2021,fp='Q2')] }}
    }}}
    with zipfile.ZipFile(td/'facts.zip','w') as z:z.writestr('CIK0000000001.json',json.dumps(facts))
    ledger=td/'ledger.csv';features=td/'features.csv'
    p=subprocess.run([sys.executable,str(ROOT/'research_v62/code/build_sec_pit_fact_ledger.py'),'--companyfacts-zip',str(td/'facts.zip'),'--ticker-map-json',str(td/'tickers.json'),'--output',str(ledger)],capture_output=True,text=True)
    assert p.returncode==0,(p.stdout,p.stderr)
    q=subprocess.run([sys.executable,str(ROOT/'research_v62/code/build_sec_pit_quarterly_features.py'),'--ledger',str(ledger),'--output',str(features)],capture_output=True,text=True)
    assert q.returncode==0,(q.stdout,q.stderr)
    a=pd.read_csv(ledger);b=pd.read_csv(features)
    assert a.availability_date.min()=='2020-05-05'
    assert set(a.source)=={'SEC_COMPANYFACTS_OFFICIAL'}
    assert 'revenue_yoy' in b and 'gross_margin' in b
    assert (pd.to_datetime(b.feature_availability_date)>=pd.to_datetime(b.end)).all()
print('5/5 PASS')
