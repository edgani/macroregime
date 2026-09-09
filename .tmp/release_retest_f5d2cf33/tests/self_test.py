from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
edges=pd.read_csv(ROOT/'data'/'causal_edges.csv')
uni=pd.read_csv(ROOT/'data'/'universe.csv')
acc=pd.read_csv(ROOT/'data'/'acceptance_tests.csv')

required_edges={'source','target','mechanism','sign','lag','role','validation','condition'}
assert required_edges.issubset(edges.columns), required_edges-set(edges.columns)
assert {'US','IHSG','FX','Commodity','Crypto'}.issubset(set(uni.market)), set(uni.market)
for case in ['SNDK','PLTR','VVV','ZEC','USDJPY intervention','ADES']:
    assert case in set(acc['case']), case
assert len(edges) >= 120, len(edges)

app=(ROOT/'app.py').read_text(encoding='utf-8').lower()
# These banned terms must not appear as executable signal methods. We only allow
# the words in explanatory "no technical indicators" text, so check common call patterns.
for bad in ['ta.rsi(', 'macd(', 'bollinger', 'stochastic(', 'ema(', 'sma(']:
    assert bad not in app, bad
print('SELF_TEST_PASS', {'edges':len(edges),'universe':len(uni),'acceptance_cases':len(acc)})
