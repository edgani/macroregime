from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(encoding='utf-8')
ui=(ROOT/'opportunity_ui.py').read_text(encoding='utf-8')
macro=(ROOT/'macro_embedded.py').read_text(encoding='utf-8')
ast.parse(app); ast.parse(ui); ast.parse(macro)

# Explicit route coverage: every top-level tab resolves to a current renderer.
route_map={
    'CONTROL ROOM':'_render_control_room(display_ranked,mg)',
    'OPPORTUNITIES':'render_opportunity_tracker(st, display_ranked, OPP_MEMORY, mg)',
    'VERTICALS':'_render_verticals(display_ranked)',
    'MACRO & EVENTS':'_render_macro_visual_room()',
    'LEARNING / REPLAY':'render_learning_lab(st, OPP_MEMORY, PROSPECTIVE.baseline_outcomes_frame())',
}
for tab,call in route_map.items():
    assert f'nav=="{tab}"' in app, tab
    assert call in app, (tab,call)

# The old visual stack cannot leak back through any current surface.
for token in ['st.dataframe','st.tabs(','st.metric','st.sidebar','st.expander','DECISION DESK','plainbox','decision-grid','info4']:
    assert token not in (app+ui), token
assert '<style>' not in macro

# Unified tables/panels used across control room, opportunities, verticals, macro, learning.
assert app.count('render_dense_table(') >= 6
assert ui.count('render_dense_table(') >= 5
assert 'mq-table-wrap' in ui and 'mq-panel' in ui and 'mq-pagehead' in ui
assert 'v3.2.6' in app or 'v3.2.6' in ui
print('TEST_V323_UNIFIED_UI_PASS')
