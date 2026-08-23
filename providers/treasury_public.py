
from __future__ import annotations
import json, urllib.request
from datetime import datetime, timezone
UA={"User-Agent":"MacroDecisionOS/4.0 research"}
TGA_URL=("https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/dts/operating_cash_balance"
         "?fields=record_date,open_today_bal,account_type&filter=account_type:eq:Treasury%20General%20Account%20(TGA)%20Opening%20Balance&sort=-record_date&page[size]=10")
RRP_URL="https://markets.newyorkfed.org/api/rp/reverserepo/all/latest.json"
SOFR_URL="https://markets.newyorkfed.org/api/rates/secured/sofr/last/2.json"

def _get(url,timeout=12):
    try:
        req=urllib.request.Request(url,headers=UA)
        with urllib.request.urlopen(req,timeout=timeout) as r:return json.loads(r.read().decode('utf-8'))
    except Exception as e:return {'_error':str(e)[:180]}

def fetch():
    out={'retrieved_at':datetime.now(timezone.utc).isoformat(),'source':'US Treasury + NY Fed','status':'PARTIAL'}
    d=_get(TGA_URL); rows=d.get('data',[]) if isinstance(d,dict) else []
    if rows:
        try:
            out['tga']={'ok':True,'date':rows[0].get('record_date'),'latest_mm':float(rows[0]['open_today_bal']),
                        'prev_mm':float(rows[1]['open_today_bal']) if len(rows)>1 else None}
        except Exception as e:out['tga']={'ok':False,'reason':str(e)[:120]}
    else:out['tga']={'ok':False,'reason':d.get('_error','no data') if isinstance(d,dict) else 'no data'}
    d=_get(RRP_URL); ops=((d.get('repo') or {}).get('operations',[]) if isinstance(d,dict) else []) or (d.get('operations',[]) if isinstance(d,dict) else [])
    if ops:
        op=ops[0]
        try:out['rrp']={'ok':True,'date':op.get('operationDate'),'amount_bn':float(op.get('totalAmtAccepted') or op.get('totalAmtSubmitted'))}
        except Exception as e:out['rrp']={'ok':False,'reason':str(e)[:120]}
    else:out['rrp']={'ok':False,'reason':d.get('_error','no data') if isinstance(d,dict) else 'no data'}
    d=_get(SOFR_URL); refs=d.get('refRates',[]) if isinstance(d,dict) else []
    if refs:
        try:out['sofr']={'ok':True,'date':refs[0].get('effectiveDate'),'rate':float(refs[0]['percentRate'])}
        except Exception as e:out['sofr']={'ok':False,'reason':str(e)[:120]}
    else:out['sofr']={'ok':False,'reason':d.get('_error','no data') if isinstance(d,dict) else 'no data'}
    out['status']='LIVE' if any(out.get(k,{}).get('ok') for k in ['tga','rrp','sofr']) else 'DATA_GATED'
    return out
