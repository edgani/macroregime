from __future__ import annotations

import subprocess
import sys

import refresh_desk_supervisor as supervisor


def test_supervisor_timeout_is_reported(monkeypatch, tmp_path):
    states = []
    monkeypatch.setattr(supervisor, 'write_status', lambda **kwargs: states.append(kwargs) or kwargs)
    monkeypatch.setattr(supervisor, 'LOCK_PATH', tmp_path / 'refresh.lock')
    monkeypatch.setattr(subprocess, 'run', lambda *a, **k: (_ for _ in ()).throw(subprocess.TimeoutExpired(cmd='worker', timeout=1)))
    monkeypatch.setattr(sys, 'argv', ['refresh_desk_supervisor.py', '--markets', 'us', '--hard-timeout', '1'])
    result = supervisor.main()
    assert result == 124
    assert states[-1]['state'] == 'TIMEOUT'
