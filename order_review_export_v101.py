"""Export shadow-eligible V10 packets for manual review.

This is not a broker submission file. It makes the system operational by producing a concrete,
human-readable decision worksheet with entry, stop, target and size. Systematic live export remains
proof- and HMAC-gated in the preserved control plane.
"""
from __future__ import annotations
import argparse,csv,datetime as dt,json
from pathlib import Path
from runtime_store import read_snapshot
HERE=Path(__file__).resolve().parent

def export(output:Path|None=None)->dict:
 snap=read_snapshot() or {}
 rows=[]
 for p in ((snap.get('alpha_center') or {}).get('shadow_candidates') or []):
  a=p.get('current_action') or {};r=a.get('risk_plan') or {};pr=a.get('projection') or {};perm=a.get('permissions') or {}
  rows.append({'market':p.get('market'),'ticker':p.get('ticker'),'research_action':a.get('direction'),'score':a.get('score'),'confidence':a.get('confidence'),'data_quality':a.get('data_quality'),'shadow_permission':perm.get('shadow_trading'),'systematic_live_permission':perm.get('systematic_live'),'side':r.get('side'),'entry_reference':r.get('entry'),'stop_reference':r.get('stop'),'target_reference':r.get('target'),'quantity_reference':r.get('quantity'),'notional_reference':r.get('notional'),'reward_risk':r.get('reward_risk'),'expected_return':pr.get('expected_return'),'horizon_days':pr.get('horizon_days'),'submission_state':'REVIEW_ONLY_NO_BROKER_SUBMISSION'})
 stamp=dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ');out=output or HERE/'runtime'/'v101_orders'/f'V101_REVIEW_{stamp}.csv';out.parent.mkdir(parents=True,exist_ok=True)
 fields=list(rows[0]) if rows else ['state','note']
 with out.open('w',newline='',encoding='utf-8-sig') as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows or [{'state':'NO_ELIGIBLE_SHADOW_CANDIDATES','note':'Refresh current data and review Alpha Center.'}])
 result={'schema':'warroom.v101.order_review_export.v1','created_at':stamp,'rows':len(rows),'path':str(out.relative_to(HERE)),'submission':'DISABLED','claim_limit':'Manual review worksheet only; no broker transmission.'}
 (out.with_suffix('.json')).write_text(json.dumps(result,indent=2),encoding='utf-8');return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output');a=p.parse_args();print(json.dumps(export(Path(a.output) if a.output else None),indent=2))
