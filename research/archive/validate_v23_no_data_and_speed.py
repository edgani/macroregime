"""Compatibility entrypoint. v2.3 checks are superseded by v2.7 staged-startup validation."""
from __future__ import annotations
import subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
raise SystemExit(subprocess.run([sys.executable, str(HERE / "validate_v27_startup.py")], cwd=HERE).returncode)
