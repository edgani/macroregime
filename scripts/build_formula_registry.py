from __future__ import annotations
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.hashing import canonical_hash, combined_file_hash, file_hash

ENTRIES=[
    {
      "component":"mqa_benchmarks","spec_id":"MQA-BENCHMARKS-V1-NEWZIP",
      "spec_path":"specs/mqa_benchmarks_v1.json","implementation_paths":["src/warroom_v3/sensors/mqa.py"],
      "status":"NOT_EVALUATED","claim_ceiling":"DESCRIPTIVE_ONLY",
      "allowed_use":["research_observation","engineering_validation"],
      "forbidden_use":["probability","entry","stop","target","paper","live"]
    },
    {
      "component":"momentum_axes","spec_id":"MOMENTUM-AXES-V1-NEWZIP",
      "spec_path":"specs/momentum_axes_v1.json","implementation_paths":["src/warroom_v3/sensors/momentum.py"],
      "status":"NOT_EVALUATED","claim_ceiling":"DESCRIPTIVE_ONLY",
      "allowed_use":["research_observation","engineering_validation"],
      "forbidden_use":["composite_alpha","probability","entry","stop","target","paper","live"]
    },
    {
      "component":"mtf_research","spec_id":"MTF-RESEARCH-V1-NEWZIP",
      "spec_path":"specs/mtf_research_v1.json","implementation_paths":["src/warroom_v3/mtf.py"],
      "status":"NOT_EVALUATED","claim_ceiling":"DESCRIPTIVE_ONLY",
      "allowed_use":["research_alignment"],
      "forbidden_use":["decision","paper","live"]
    }
]

def build():
    rows=[]
    for base in ENTRIES:
        e=dict(base)
        spec=ROOT/e.pop('spec_path')
        impl=[ROOT/p for p in e.pop('implementation_paths')]
        e['spec_sha256']=file_hash(spec)
        e['implementation_sha256']=combined_file_hash(impl,root=ROOT)
        e['formula_hash']=canonical_hash({"spec_sha256":e['spec_sha256'],"implementation_sha256":e['implementation_sha256']})
        rows.append(e)
    return {"entries":rows,"registry_hash":canonical_hash(rows)}

if __name__=='__main__':
    out=ROOT/'evidence/formula_registry_active.json'; expected=json.dumps(build(),indent=2,sort_keys=True)+"\n"
    if '--check' in sys.argv:
        if not out.exists() or out.read_text()!=expected: raise SystemExit('formula registry stale')
        print('PASS: formula registry')
    else:
        out.write_text(expected); print(out)
