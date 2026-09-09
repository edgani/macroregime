from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(encoding='utf-8')
ui=(ROOT/'opportunity_ui.py').read_text(encoding='utf-8')
macro=(ROOT/'macro_embedded.py').read_text(encoding='utf-8')
ast.parse(app); ast.parse(ui); ast.parse(macro)

# Five routed workspaces; every one uses the single v3.2.3 shell/components.
for fn in ['_render_control_room','_render_verticals','_render_macro_visual_room','_render_workspace_nav']:
    assert f'def {fn}(' in app, fn
for fn in ['render_opportunity_tracker','render_learning_lab','render_dense_table','dense_table_html']:
    assert f'def {fn}(' in ui, fn
assert 'NAV_ITEMS=["CONTROL ROOM","OPPORTUNITIES","VERTICALS","MACRO & EVENTS","LEARNING / REPLAY"]' in app
assert 'mq-pagehead' in app and 'mq-pagehead' in ui
assert 'mq-table-wrap' in ui and 'mq-vgrid' in ui and 'mq-kpirow' in ui

# Retired mixed UI must not be reachable or even injected.
for bad in ['DECISION DESK','st.sidebar','st.tabs(','st.dataframe','st.metric','st.expander']:
    assert bad not in (app+ui), bad
assert '<style>' not in macro, 'macro module must not inject the retired v3.1 stylesheet'

# Leverage/options research contracts stay visible in engine logic, not old UI renderers.
block=app.split('def _expression_tables',1)[1].split('def _expression_readiness',1)[0]
assert '["US","FX","Commodity","Crypto"]' in block
assert 'BTC-USD' in block and 'ETH-USD' in block
assert 'WAIT · FX LEVERAGE GATED' in block
assert 'WAIT · COMMODITY LEVERAGE GATED' in block
assert 'WAIT · CRYPTO LEVERAGE GATED' in block
assert 'WAIT · BTC/ETH OPTION THESIS GATED' in block
print('TEST_VISUAL_CONTRACT_PASS')
