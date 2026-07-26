from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path


class _Ctx:
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class _FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit')
        self.sidebar = _Ctx()
        self.rendered = []
    def set_page_config(self, **kwargs):
        return None
    def markdown(self, *args, **kwargs):
        return None
    def multiselect(self, label, options, default=None, **kwargs):
        return list(default or options)
    def checkbox(self, label, value=False, **kwargs):
        return False
    def select_slider(self, label, options=None, value=None, **kwargs):
        return value
    def columns(self, n):
        return [_Ctx() for _ in range(n)]
    def button(self, *args, **kwargs):
        return False
    def caption(self, *args, **kwargs):
        return None
    def expander(self, *args, **kwargs):
        return _Ctx()
    def code(self, *args, **kwargs):
        return None
    def divider(self):
        return None
    def text_input(self, *args, value='', **kwargs):
        return value
    def info(self, *args, **kwargs):
        return None
    def success(self, *args, **kwargs):
        return None
    def warning(self, *args, **kwargs):
        return None
    def error(self, *args, **kwargs):
        return None
    def rerun(self):
        return None


def test_first_render_does_not_call_provider_or_block(monkeypatch):
    root = Path(__file__).resolve().parent
    sys.path.insert(0, str(root))

    import desk_runtime
    import data.resilient_market_data as resilient

    monkeypatch.setattr(desk_runtime, 'repair_stale_runtime', lambda: {'state': 'IDLE'})
    monkeypatch.setattr(desk_runtime, 'load_desk', lambda: None)
    monkeypatch.setattr(desk_runtime, 'read_status', lambda: {'state': 'IDLE', 'message': 'idle'})
    monkeypatch.setattr(desk_runtime, 'is_running', lambda: False)
    monkeypatch.setattr(desk_runtime, 'cache_age_seconds', lambda: None)
    launches = []
    monkeypatch.setattr(desk_runtime, 'launch_refresh', lambda markets, force=False, scope='fast': (launches.append((markets, force, scope)) or True, 'started'))
    monkeypatch.setattr(resilient, 'read_health', lambda: {})

    fake_st = _FakeStreamlit()
    components = types.ModuleType('streamlit.components.v1')
    html_calls = []
    components.html = lambda *args, **kwargs: html_calls.append((args, kwargs))
    components_pkg = types.ModuleType('streamlit.components')
    components_pkg.v1 = components
    fake_st.components = components_pkg

    monkeypatch.setitem(sys.modules, 'streamlit', fake_st)
    monkeypatch.setitem(sys.modules, 'streamlit.components', components_pkg)
    monkeypatch.setitem(sys.modules, 'streamlit.components.v1', components)

    spec = importlib.util.spec_from_file_location('app_v7_test_instance', root / 'app.py')
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)

    assert launches and launches[0][2] == 'fast'
    assert len(html_calls) >= 2  # dashboard and reload timer
    assert 'window.DASHBOARD_DATA' in html_calls[0][0][0]
