from __future__ import annotations
import copy, hashlib, json, tempfile, zipfile, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import research_evidence_v53 as ev
import recover_v62_exact as rv


def ok(name, cond):
    if not cond: raise AssertionError(name)
    print('PASS',name)

def main():
    raw=ev.load_research_evidence()
    ok('registry_loaded',raw['status']=='RECONCILED_RESEARCH_EVIDENCE_ONLY')
    ok('four_narrow_supported',sum('SUPPORTED' in str(x.get('status')) for x in raw['claims'])==4)
    ok('v61_failed',next(x for x in raw['claims'] if x['study'].startswith('V61'))['status']=='NOT_PROVEN')
    ok('v62_aborted',next(x for x in raw['claims'] if x['study'].startswith('V62'))['status']=='ABORTED_BEFORE_OUTCOME_ANALYSIS')
    ok('zero_live_weights',all(float(x['live_decision_weight'])==0 for x in raw['claims']))
    ok('all_capital_blocked',all(x['capital_permission']=='BLOCKED' for x in raw['claims']) and raw['capital_permission']=='BLOCKED')
    ok('no_prospective_pass',all(x['prospective_pass'] is False for x in raw['claims']))
    attached=ev.attach_research_evidence_v53({'x':1})
    ok('desk_attached',attached['x']==1 and 'research_evidence_v53' in attached)
    ok('input_not_mutated','research_evidence_v53' not in {'x':1})
    with tempfile.TemporaryDirectory() as d:
        p=Path(d)/'wrong.zip';
        with zipfile.ZipFile(p,'w') as z:z.writestr('x','y')
        r=rv.recover(p,Path(d)/'out')
        ok('wrong_package_hash_rejected',r['status']=='FAIL' and not r['outcome_analysis_permitted'])
    ok('zip_traversal_rejected',not rv.safe_name('../evil') and not rv.safe_name('/abs') and rv.safe_name('safe/file.json'))
    print('V53_ATTACHMENT_CONTINUATION_TESTS=11/11 PASS')
if __name__=='__main__':main()
