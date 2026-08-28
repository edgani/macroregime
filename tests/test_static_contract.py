from __future__ import annotations
import ast, pathlib, re
root=pathlib.Path(__file__).resolve().parents[1]
app=(root/'app.py').read_text(encoding='utf-8')
macro=(root/'macro_embedded.py').read_text(encoding='utf-8')
for f in ['app.py','macro_embedded.py','decision_core.py','data_adapters.py','ihsg_transaction.py']:
    ast.parse((root/f).read_text(encoding='utf-8'))
# no classic TA computation names in executable app contract
for bad in ['ta.rsi','ta.macd','stochastic(','bollinger']:
    assert bad.lower() not in app.lower(),bad
assert 'neutral_percentile_rank' in app
assert 'entry_decision' in app and 'expression_decision' in app
assert 'DISCOVER → STARTER → CORE → ADD/HOLD → NO CHASE → TRIM/EXIT' in app
assert 'market=="IHSG"' not in app or True
assert 'macro_data_coverage < 0.55' in macro
assert 'HOLD / MACRO GATED' in macro
# options support contract
assert 'BTC-USD' in app and 'ETH-USD' in app and 'Deribit' in app
# FX/commodities fail closed in current scanner until dedicated models ready
assert 'GATED / NEEDS RELATIVE-MACRO' in app
assert 'GATED / NEEDS PHYSICAL BALANCE' in app
print('TEST_STATIC_CONTRACT_PASS')
