from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> None:
    print('>', ' '.join(cmd))
    subprocess.run(cmd, cwd=ROOT, check=True)


def main() -> None:
    env = os.environ.copy()
    env['MRP_LIVE_FETCH'] = '0'
    print('Running compileall...')
    subprocess.run([sys.executable, '-m', 'compileall', '.'], cwd=ROOT, check=True, env=env)
    print('Running unittest discovery...')
    subprocess.run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], cwd=ROOT, check=True, env=env)
    print('Smoke checks passed.')


if __name__ == '__main__':
    main()
