from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(encoding='utf-8')
ast.parse(app)
for fn in ['_render_expression_matrix','_render_opportunity_visuals','_render_evidence_flow_chart','_render_compact_selected','_render_macro_visual_room']:
    assert f'def {fn}(' in app, fn
# leverage/options surfaces must keep non-US markets visible rather than dropping them
block=app.split('def _expression_tables',1)[1].split('def _expression_readiness',1)[0]
assert '["US","FX","Commodity","Crypto"]' in block
assert 'BTC-USD' in block and 'ETH-USD' in block
assert 'WAIT · FX LEVERAGE GATED' in block
assert 'WAIT · COMMODITY LEVERAGE GATED' in block
assert 'WAIT · CRYPTO LEVERAGE GATED' in block
assert 'WAIT · BTC/ETH OPTION THESIS GATED' in block
# Visible product surface must use the unified shell only. Old Decision Desk is not routed.
assert 'mq-pagehead' in app
assert 'DECISION DESK' not in app
assert 'st.sidebar' not in app
print('TEST_VISUAL_CONTRACT_PASS')
