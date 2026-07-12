from __future__ import annotations
import json,sys
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.data import load_canonical_csv
from warroom_v3.pipeline import build_research_observation
bars,_=load_canonical_csv(ROOT/'data/fixtures/aal_1d_engineering.csv',ingested_at=datetime(2026,7,12,tzinfo=timezone.utc))
reg=json.loads((ROOT/'evidence/formula_registry_active.json').read_text())
hashes={e['component']:e['formula_hash'] for e in reg['entries']}
ticket=build_research_observation(bars,formula_hashes=hashes)
payload=asdict(ticket)
payload['component_evidence']={k:v.value for k,v in ticket.component_evidence.items()}
out=ROOT/'artifacts/research_observation_aal_1d_engineering.json'
out.write_text(json.dumps(payload,indent=2,sort_keys=True)+"\n",encoding='utf-8')
print(out)
