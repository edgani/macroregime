from __future__ import annotations
from copy import deepcopy
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tempfile import TemporaryDirectory
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
import hashlib, json

from options_prospective_ledger_v71 import build_signed_row, append_row, read_rows, verify_rows, PROTOCOL, digest_row

checks=[]
def check(name, ok, detail=None):
    checks.append({'check':name,'status':'PASS' if ok else 'FAIL','detail':detail})
    if not ok: raise AssertionError(f'{name}: {detail}')

priv=Ed25519PrivateKey.generate(); pub=priv.public_key(); keys={'test-key':pub}
src='a'*64
pred=build_signed_row(private_key=priv,key_id='test-key',phase='PREDICTION',claim_id='V71_C1_VERIFIED_GAMMA_RESPONSE',observed_at='2026-07-24T14:31:00Z',market='us',underlying='SPX',venue='CBOE',option_contract='SPXW-20260724-6000-C',prediction_id='p1',source_payload_sha256=src,source_schema='fixture.v1',features_or_outcome={'dealer_sign_state':'VERIFIED_PROVENANCE','forecast':'AMPLIFICATION_CONTEXT','calibrated_probability':None},previous_row_sha256=None)
check('prediction_forces_zero_live_weight',pred['live_decision_weight']==0 and pred['capital_permission']=='BLOCKED')
check('protocol_hash_bound',pred['protocol_sha256']==hashlib.sha256(PROTOCOL.read_bytes()).hexdigest())
check('single_row_verifies',verify_rows([pred],keys)['status']=='PASS')

out=build_signed_row(private_key=priv,key_id='test-key',phase='OUTCOME',claim_id=pred['claim_id'],observed_at='2026-07-24T16:31:00Z',market='us',underlying='SPX',venue='CBOE',option_contract=pred['option_contract'],prediction_id='p1',source_payload_sha256='b'*64,source_schema='fixture.outcome.v1',features_or_outcome={'continuation_120m':True,'net_pnl':None},previous_row_sha256=pred['row_sha256'])
check('prediction_plus_forward_outcome_verifies',verify_rows([pred,out],keys)['status']=='PASS')

with TemporaryDirectory() as td:
    path=Path(td)/'ledger.jsonl'; append_row(path,pred); append_row(path,out)
    check('append_and_read_roundtrip',read_rows(path)==[pred,out])
    try: append_row(path,pred); rejected=False
    except ValueError: rejected=True
    check('append_rejects_chain_fork',rejected)

bad=deepcopy(pred); bad['evidence']['forecast']='DAMPING_CONTEXT'
check('content_tamper_rejected',verify_rows([bad],keys)['status']=='FAIL')
bad=deepcopy(pred); bad['signature']='AAAA'
check('signature_tamper_rejected',verify_rows([bad],keys)['status']=='FAIL')
bad=deepcopy(pred); bad['protocol_sha256']='0'*64
check('protocol_substitution_rejected',verify_rows([bad],keys)['status']=='FAIL')
bad=deepcopy(pred); bad['source_payload_sha256']='not-a-hash'; bad['row_sha256']=digest_row(bad)
check('bad_source_hash_rejected',verify_rows([bad],keys)['status']=='FAIL')
bad=deepcopy(pred); bad['capital_permission']='LIVE'; bad['row_sha256']=digest_row(bad)
check('permission_escalation_rejected',verify_rows([bad],keys)['status']=='FAIL')
bad=deepcopy(pred); bad['key_id']='unknown'; bad['row_sha256']=digest_row(bad)
check('unknown_key_rejected',verify_rows([bad],keys)['status']=='FAIL')
badout=deepcopy(out); badout['prediction_id']='missing'; badout['row_sha256']=digest_row(badout)
check('unmatched_outcome_rejected',verify_rows([pred,badout],keys)['status']=='FAIL')
badout=deepcopy(out); badout['observed_at']='2026-07-24T13:31:00Z'; badout['row_sha256']=digest_row(badout)
check('backdated_outcome_rejected',verify_rows([pred,badout],keys)['status']=='FAIL')
dup=deepcopy(pred); dup['previous_row_sha256']=pred['row_sha256']; dup['row_sha256']=digest_row(dup)
check('duplicate_prediction_id_rejected',verify_rows([pred,dup],keys)['status']=='FAIL')
try:
    build_signed_row(private_key=priv,key_id='test-key',phase='PREDICTION',claim_id='x',observed_at='2026-07-24T14:31:00Z',market='ihsg',underlying='JKSE',venue='IDX',option_contract='NONE',prediction_id='x',source_payload_sha256=src,source_schema='x',features_or_outcome={},previous_row_sha256=None)
    ihsg_rejected=False
except ValueError: ihsg_rejected=True
check('ihsg_disabled_in_builder', ihsg_rejected)
for field in ('option_contract','venue','source_schema'):
    kw=dict(private_key=priv,key_id='test-key',phase='PREDICTION',claim_id='x',observed_at='2026-07-24T14:31:00Z',market='us',underlying='SPX',venue='CBOE',option_contract='C',prediction_id='x',source_payload_sha256=src,source_schema='x',features_or_outcome={},previous_row_sha256=None);kw[field]=''
    try: build_signed_row(**kw); rejected=False
    except ValueError: rejected=True
    check(f'exact_scope_required_{field}',rejected)

report={'schema':'warroom.validation.options_prospective_v71','status':'PASS','checks_total':len(checks),'checks_passed':sum(x['status']=='PASS' for x in checks),'checks':checks,'prospective_observations_collected':0,'predictive_components_promoted':0,'live_decision_weight':0.0,'capital_permission':'BLOCKED'}
outpath=Path(__file__).resolve().parents[1]/'V71_OPTIONS_PROSPECTIVE_VALIDATION.json';outpath.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
print(json.dumps(report,indent=2))
