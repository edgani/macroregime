
from pathlib import Path
import ast,re,sys,pandas as pd
ROOT=Path(__file__).resolve().parents[1]
errors=[]
for p in ROOT.rglob('*.py'):
    try:ast.parse(p.read_text(encoding='utf-8'))
    except Exception as e:errors.append(f'Syntax {p}: {e}')
reg=pd.read_csv(ROOT/'config'/'metric_registry_v4.csv')
if len(reg)!=52:errors.append(f'Metric families !=52: {len(reg)}')
for c in ['actor','constraint','transmission','horizon','confirmation','contradiction','pricing','decision_improved']:
    if c not in reg or reg[c].isna().any():errors.append(f'Metric registry incomplete: {c}')
prod='\n'.join(p.read_text(encoding='utf-8',errors='ignore') for p in list((ROOT/'engines').glob('*.py'))+list((ROOT/'providers').glob('*.py'))+[ROOT/'data_layer_v4.py'])
for pat in [r'\bRSI\b',r'\bMACD\b',r'Bollinger',r'Fibonacci',r'candlestick']:
    if re.search(pat,prod,re.I):errors.append('Prohibited TA term in production code: '+pat)
if re.search(r'synthetic.{0,20}(price|fallback)|fallback.{0,20}synthetic',prod,re.I|re.S):errors.append('Synthetic fallback reference found')
if 'NO TRADE' not in (ROOT/'engines'/'opportunity_engine.py').read_text():errors.append('NO TRADE not first-class in opportunity engine')
cat=pd.read_csv(ROOT/'research'/'scenario_catalog.csv')
if len(cat)<30:errors.append('Scenario library unexpectedly small')
print('PASS' if not errors else 'FAIL')
for e in errors:print('-',e)
sys.exit(1 if errors else 0)
