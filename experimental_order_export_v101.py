"""Explicit experimental-manual order-ticket export for V10.1.

Disabled by default. This does not transmit to a broker and does not convert an unproven research
action into systematic alpha. It only creates a short-lived, HMAC-bound, micro-risk ticket after the
operator enables the environment gate and supplies the exact acknowledgement.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,hashlib,hmac,json,os
from pathlib import Path
from typing import Any
from runtime_store import read_snapshot
HERE=Path(__file__).resolve().parent;UTC=dt.timezone.utc
try:
 from dotenv import load_dotenv
 load_dotenv(HERE/'.env',override=False)
except Exception:pass

def canonical(v:Any)->bytes:return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=False,default=str).encode()
def export(ticker:str,approved_by:str)->dict:
 enabled=os.getenv('WARROOM_EXPERIMENTAL_LIVE','0').lower() in {'1','true','yes'}
 ack=os.getenv('WARROOM_EXPERIMENTAL_ACK','');required='I_ACCEPT_EXPERIMENTAL_UNPROVEN_ALPHA_RISK'
 secret=os.getenv('WARROOM_HUMAN_APPROVAL_SECRET','')
 if not enabled:raise PermissionError('WARROOM_EXPERIMENTAL_LIVE is not enabled')
 if ack!=required:raise PermissionError('exact experimental acknowledgement is missing')
 if len(secret)<24:raise PermissionError('WARROOM_HUMAN_APPROVAL_SECRET must contain at least 24 characters')
 snap=read_snapshot() or {};found=None
 for rows in (snap.get('ticker_packets') or {}).values():
  if ticker in (rows or {}):found=rows[ticker];break
 if not found:raise KeyError('ticker packet not found')
 a=found.get('current_action') or {};perm=a.get('permissions') or {}
 if not str(perm.get('experimental_manual') or '').startswith('ELIGIBLE'):raise PermissionError('packet is not experimental-manual eligible; refresh data and review gates')
 risk=a.get('experimental_manual_risk_plan') or {};q=a.get('quote_state') or {}
 if not risk.get('valid') or not q.get('fresh'):raise PermissionError('fresh quote and valid micro-risk plan are required')
 now=dt.datetime.now(UTC);expires=now+dt.timedelta(minutes=15)
 body={'schema':'warroom.v101.experimental_manual_ticket.v1','ticket_id':'V101X_'+hashlib.sha256(f'{ticker}|{now.isoformat()}'.encode()).hexdigest()[:20].upper(),'created_at':now.isoformat().replace('+00:00','Z'),'expires_at':expires.isoformat().replace('+00:00','Z'),'approved_by':approved_by,'market':found.get('market'),'ticker':ticker,'research_action':a.get('direction'),'score':a.get('score'),'confidence':a.get('confidence'),'side':risk.get('side'),'quantity':risk.get('quantity'),'entry_reference':risk.get('entry'),'stop_reference':risk.get('stop'),'target_reference':risk.get('target'),'notional_reference':risk.get('notional'),'risk_budget':risk.get('risk_budget'),'reward_risk':risk.get('reward_risk'),'systematic_live_proof':perm.get('systematic_live'),'execution_mode':'EXPERIMENTAL_MANUAL_MICRO_RISK','broker_submission':'DISABLED','operator_ack':required,'packet_hash':hashlib.sha256(canonical(found)).hexdigest(),'claim_limit':'Unproven experimental manual ticket; verify quote, contract, lot, currency, fees and broker details before any manual action.'}
 body['hmac_sha256']=hmac.new(secret.encode(),canonical(body),hashlib.sha256).hexdigest()
 outdir=HERE/'runtime'/'v101_orders';outdir.mkdir(parents=True,exist_ok=True);base=outdir/body['ticket_id']
 base.with_suffix('.json').write_text(json.dumps(body,indent=2,ensure_ascii=False),encoding='utf-8')
 fields=[k for k in body if k not in {'claim_limit'}]
 with base.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerow({k:body.get(k) for k in fields})
 return {'ticket_id':body['ticket_id'],'json':str(base.with_suffix('.json').relative_to(HERE)),'csv':str(base.with_suffix('.csv').relative_to(HERE)),'expires_at':body['expires_at'],'broker_submission':'DISABLED'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--ticker',required=True);p.add_argument('--approved-by',required=True);a=p.parse_args();print(json.dumps(export(a.ticker,a.approved_by),indent=2))
