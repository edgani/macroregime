"""Compatibility entrypoint. v2.4 checks are superseded by the v2.7 full stability suite."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
raise SystemExit(subprocess.run([sys.executable, str(HERE / "validate_v27_full.py")], cwd=HERE).returncode)
