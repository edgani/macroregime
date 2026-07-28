from __future__ import annotations

import pickle
from pathlib import Path

import desk_runtime as runtime


def test_save_load_desk_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "DESK_CACHE", tmp_path / "desk.pkl")
    desk = {"meta": {"source": "TEST"}, "markets": {"us": {"funnel": {"loaded": 1}}}}
    runtime.save_desk(desk)
    loaded = runtime.load_desk()
    assert loaded is not None
    assert loaded["meta"]["desk_schema_version"] == runtime.DESK_SCHEMA_VERSION
    assert loaded["markets"]["us"]["funnel"]["loaded"] == 1


def test_status_atomic_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(runtime, "STATUS_PATH", tmp_path / "status.json")
    result = runtime.write_status(state="RUNNING", message="test")
    assert result["state"] == "RUNNING"
    assert runtime.read_status()["message"] == "test"


def test_app_has_no_blocking_provider_call():
    source = (Path(__file__).resolve().parent / "app.py").read_text(encoding="utf-8")
    assert "data_layer.load_all" not in source
    assert "@st.cache_data" not in source
    assert "launch_refresh(" in source
    assert "components.html(html" in source


def test_worker_has_schema_and_real_data_gate():
    source = (Path(__file__).resolve().parent / "refresh_desk_worker.py").read_text(encoding="utf-8")
    assert "loaded <= 0" in source
    assert "save_desk(desk)" in source
    assert "DESK_SCHEMA_VERSION" in source
