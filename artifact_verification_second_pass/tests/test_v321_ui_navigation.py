from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(encoding='utf-8')
ui=(ROOT/'opportunity_ui.py').read_text(encoding='utf-8')
ast.parse(app); ast.parse(ui)

# Unified product shell only: no old pseudo-nav, sidebar, Decision Desk or nested tab maze.
assert 'def _render_workspace_nav()' in app
assert 'st.button(item' in app
assert 'on_click=_set_workspace' in app
assert 'decision_nav_v322' in app
assert 'nav=st.radio("Workspace"' not in app
assert 'st.sidebar' not in app
assert 'DECISION DESK' not in app
assert 'st.tabs(' not in ui

# Navigation is rendered before expensive automatic scanning so page changes stay immediate.
nav_pos=app.index('nav=_render_workspace_nav()')
scan_pos=app.index('if force_refresh or (need_auto and not skip_auto_scan_once):')
run_pos=app.index('_run_intelligence(scan_input,scan_signature', scan_pos)
assert nav_pos < scan_pos < run_pos
assert '_skip_auto_scan_once' in app

# Every exposed workspace uses the unified neon/dense shell.
for item in ['CONTROL ROOM','OPPORTUNITIES','VERTICALS','MACRO & EVENTS','LEARNING / REPLAY']:
    assert item in app
for token in ['mq-pagehead','mq-vgrid','mq-note','render_global_header','install_memequant_style(st)']:
    assert token in app or token in ui, token
assert 'Legacy research / validation' not in app
print('TEST_V322_UNIFIED_UI_NAVIGATION_PASS')
