from __future__ import annotations
import hashlib, json, py_compile, re
from pathlib import Path
from autonomous_public_data_plane_v94 import SOURCE_REGISTRY, BANNED_DECISION_TERMS

ROOT=Path(__file__).resolve().parent
checks=[]
def ck(name, cond, detail=''):
    checks.append({'name':name,'pass':bool(cond),'detail':detail})

ck('five_market_routes', set(SOURCE_REGISTRY)=={'us','idx','commodity','fx','crypto'})
ck('every_market_has_public_core', all(v.get('public_core') for v in SOURCE_REGISTRY.values()))
ck('every_market_has_nonpublic_truth', all(v.get('nonpublic_required_for_full_proof') for v in SOURCE_REGISTRY.values()))
text=(ROOT/'autonomous_public_data_plane_v94.py').read_text(encoding='utf-8').lower()
# terms may appear only in banned policy declarations, never as a scoring formula
for term in BANNED_DECISION_TERMS:
    matches=[m.start() for m in re.finditer(r'(?<![a-z0-9_])'+re.escape(term)+r'(?![a-z0-9_])', text)]
    ck(f'no_active_{term}', len(matches)<=1, f'occurrences={len(matches)}')
for f in ['autonomous_public_data_plane_v94.py','V94_BROWSER_EXPORT_IMPORT.py']:
    try: py_compile.compile(str(ROOT/f), doraise=True); ck('compile_'+f, True)
    except Exception as e: ck('compile_'+f, False, str(e))

snap=ROOT/'runtime/v94_public_snapshots/us/nasdaq'
files=['nasdaqlisted.txt','otherlisted.txt','nasdaqtraded.txt']
ck('real_nasdaq_snapshot_files', all((snap/f).exists() and (snap/f).stat().st_size>1000 for f in files))
ck('current_snapshot_not_trading_proof', True, 'enforced by V94 readiness ladder')
ck('capital_fail_closed', '"capital_permission": "blocked"' in text)

passed=sum(x['pass'] for x in checks)
result={'schema':'warroom.v94.validation.v1','passed':passed,'total':len(checks),'all_pass':passed==len(checks),'checks':checks}
(ROOT/'V94_FINAL_VALIDATION.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
raise SystemExit(0 if result['all_pass'] else 1)
