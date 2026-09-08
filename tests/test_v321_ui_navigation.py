from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
app=(ROOT/'app.py').read_text(encoding='utf-8')
ast.parse(app)

# Workspace navigation must be real native buttons, not a pseudo-tab radio row.
assert 'def _render_workspace_nav()' in app
assert 'st.button(item' in app
assert 'on_click=_set_workspace' in app
assert 'decision_nav_v321' in app
assert 'nav=st.radio("Workspace"' not in app

# Navigation is rendered before expensive automatic scanning so clicks do not feel dead.
nav_pos=app.index('nav=_render_workspace_nav()')
scan_pos=app.index('if force_refresh or (need_auto and not skip_auto_scan_once):')
run_pos=app.index('_run_intelligence(scan_input,scan_signature', scan_pos)
assert nav_pos < scan_pos < run_pos
assert '_skip_auto_scan_once' in app

# Control room must use the dense visual shell, not only the old metric/table layout.
control=app.split('def _render_control_room',1)[1].split('def _render_verticals',1)[0]
for token in ['install_memequant_style(st)','mq-top','mq-grid' if 'mq-grid' in control else 'st.columns([1.0,2.05,1.0]','Selected opportunity','Recent opportunity alerts']:
    assert token in control, token

# Route contract: all six workspaces still exist and Decision Desk is explicit.
for item in ['CONTROL ROOM','OPPORTUNITIES','DECISION DESK','VERTICALS','MACRO & EVENTS','RESEARCH / REPLAY']:
    assert item in app
assert 'elif nav=="DECISION DESK"' in app

print('TEST_V321_UI_NAVIGATION_PASS')
