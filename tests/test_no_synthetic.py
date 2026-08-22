from pathlib import Path
root=Path(__file__).resolve().parents[1]
prod='\n'.join(p.read_text(errors='ignore') for p in (root/'eros').glob('*.py'))
assert '_synth(' not in prod
assert 'synthetic fallback' not in prod.lower()
print('NO_SYNTHETIC_PRODUCTION_PASS')
