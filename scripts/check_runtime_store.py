from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.storage import verify_store,verify_chain,load_jsonl
from warroom_v3.trading import verify_paper_journal
errors=[]
for tier in ('bootstrap','prospective'):
    errors.extend(f'{tier}:{e}' for e in verify_store(ROOT/'runtime',tier))
for name in ('observations','outcomes'):
    path=ROOT/f'runtime/{name}/journal.jsonl'
    if name=='observations': errors.extend(f'{name}:{e}' for e in verify_chain(load_jsonl(path)))
errors.extend(f'paper:{e}' for e in verify_paper_journal(ROOT))
if errors: raise SystemExit('runtime store invalid: '+','.join(errors))
print('PASS: runtime stores')
