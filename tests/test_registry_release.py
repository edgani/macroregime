import ast,json,tempfile,unittest
from pathlib import Path
from warroom_v3.registry import load_registry,canonical_hash
from warroom_v3.release import build_release_manifest
ROOT=Path(__file__).resolve().parents[1]
class RegistryReleaseTests(unittest.TestCase):
    def test_registry_hash_valid(self):
        r=load_registry(ROOT/'evidence/formula_registry.json');self.assertEqual(r['registry_hash'],canonical_hash(r['entries']))
    def test_legacy_mqa_is_rejected(self):
        r=load_registry(ROOT/'evidence/formula_registry.json');e=next(x for x in r['entries'] if x['component']=='legacy_mqa_risk_range');self.assertEqual(e['status'],'REJECTED')
    def test_entry_patch_is_not_production_default(self):
        r=load_registry(ROOT/'evidence/formula_registry.json');e=next(x for x in r['entries'] if x['component']=='legacy_entry_risk_range_integration');self.assertIn('production_default',e['forbidden_use'])
    def test_no_legacy_imports_in_src(self):
        forbidden=('gcfis','warroom','engines')
        for p in (ROOT/'src').rglob('*.py'):
            tree=ast.parse(p.read_text())
            for n in ast.walk(tree):
                if isinstance(n,ast.Import):
                    for a in n.names:self.assertFalse(a.name.startswith(forbidden),f'{p}: {a.name}')
                if isinstance(n,ast.ImportFrom) and n.module:self.assertFalse(n.module.startswith(forbidden),f'{p}: {n.module}')
    def test_release_hash_deterministic(self):
        paths=['src/warroom_v3/contracts.py','src/warroom_v3/gates.py','evidence/formula_registry.json']
        self.assertEqual(build_release_manifest(ROOT,paths),build_release_manifest(ROOT,paths))
