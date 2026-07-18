from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
checks = {}

def run(name, command, timeout=180):
    proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    checks[name] = {
        'pass': proc.returncode == 0,
        'command': ' '.join(command),
        'stdout_tail': proc.stdout[-3000:],
        'stderr_tail': proc.stderr[-3000:],
    }

run('compile', [sys.executable, '-m', 'py_compile', 'app.py', 'desk_runtime.py', 'refresh_desk_worker.py', 'refresh_desk_supervisor.py', 'data_layer.py', 'data/resilient_market_data.py', 'run.py', 'consistency_guard.py'])
run('nonblocking_and_feed_tests', [sys.executable, '-m', 'pytest', '-q', 'test_nonblocking_runtime_v7.py', 'test_app_first_render_v7.py', 'test_supervisor_timeout_v7.py', 'test_resilient_feeds.py', 'test_resilient_integration.py', 'alpha_foundry/tests/test_pipeline.py'])
run('hardcode_audit', [sys.executable, 'audit_no_hardcoded_outputs.py'])
run('runtime_audit', [sys.executable, 'audit_v7.py'])
run('gcfis_suite', [sys.executable, 'gcfis/tests/test_all.py'], timeout=240)

html = (ROOT / 'dashboard.html').read_text(encoding='utf-8')
checks['fourteen_tabs'] = {'pass': len(re.findall(r'<div class="tab(?: on| core)?" data-v=', html)) == 14}
checks['no_blocking_provider_in_app'] = {'pass': 'data_layer.load_all' not in (ROOT / 'app.py').read_text(encoding='utf-8')}
checks['hard_timeout_supervisor'] = {'pass': 'timeout=args.hard_timeout' in (ROOT / 'refresh_desk_supervisor.py').read_text(encoding='utf-8')}
checks['v7_schema'] = {'pass': 'V7_NONBLOCKING_REFRESH_2026_07_18' in (ROOT / 'desk_runtime.py').read_text(encoding='utf-8')}

report = {
    'version': 'v7',
    'pass': all(bool(value.get('pass')) for value in checks.values()),
    'passed': sum(bool(value.get('pass')) for value in checks.values()),
    'total': len(checks),
    'checks': checks,
}
(ROOT / 'RELEASE_VALIDATION_v7.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(0 if report['pass'] else 1)
