from __future__ import annotations
import ast, pathlib
root=pathlib.Path(__file__).resolve().parents[1]
app=(root/'app.py').read_text(encoding='utf-8')
ui=(root/'opportunity_ui.py').read_text(encoding='utf-8')
macro=(root/'macro_embedded.py').read_text(encoding='utf-8')
for f in ['app.py','macro_embedded.py','decision_core.py','data_adapters.py','ihsg_transaction.py','opportunity_ui.py']:
    ast.parse((root/f).read_text(encoding='utf-8'))
for bad in ['ta.rsi','ta.macd','stochastic(','bollinger']:
    assert bad.lower() not in app.lower(),bad
assert 'neutral_percentile_rank' in app
assert 'entry_decision' in app and 'expression_decision' in app
assert 'DISCOVER → STARTER → CORE → ADD/HOLD → NO CHASE → TRIM/EXIT' in ui
assert 'macro_data_coverage < 0.55' in macro
assert 'HOLD / MACRO GATED' in macro
assert 'BTC-USD' in app and 'ETH-USD' in app and 'Deribit' in app
assert 'GATED / NEEDS RELATIVE-MACRO' in app
assert 'GATED / NEEDS PHYSICAL BALANCE' in app
print('TEST_STATIC_CONTRACT_PASS')
