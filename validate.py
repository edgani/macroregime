from __future__ import annotations
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'src'))
suite=unittest.defaultTestLoader.discover(str(ROOT/'tests'))
count=suite.countTestCases()
if count < 10:
    print(f'FAIL: only {count} tests discovered',file=sys.stderr); raise SystemExit(2)
result=unittest.TextTestRunner(verbosity=2).run(suite)
if not result.wasSuccessful(): raise SystemExit(1)
print(f'PASS: {count} tests discovered and passed')
