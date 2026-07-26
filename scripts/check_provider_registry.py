from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT/'src'))
from warroom_v3.providers import ProviderRegistry
r=ProviderRegistry.load(ROOT/'config/providers.json')
if len(r.records)<2: raise SystemExit('provider registry incomplete')
print(f'PASS: provider registry ({len(r.records)} providers, hash={r.snapshot_hash})')
