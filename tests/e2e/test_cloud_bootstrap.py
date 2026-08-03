"""Regression test for Streamlit Cloud's direct app.py execution model."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_app_bootstraps_src_layout_without_installed_project(tmp_path: Path) -> None:
    """The entry point must find eros when only third-party modules are importable."""
    fake_modules = tmp_path / "fake_modules"
    fake_modules.mkdir()
    (fake_modules / "streamlit.py").write_text(
        "def cache_data(*args, **kwargs):\n"
        "    def decorator(function):\n"
        "        function.clear = lambda: None\n"
        "        return function\n"
        "    return decorator\n",
        encoding="utf-8",
    )
    (fake_modules / "pydantic.py").write_text(
        "class BaseModel:\n    pass\n\n"
        "FiniteFloat = float\n\n"
        "def ConfigDict(**kwargs):\n    return kwargs\n\n"
        "def Field(*args, **kwargs):\n    return None\n\n"
        "def field_validator(*args, **kwargs):\n"
        "    def decorator(function):\n        return function\n"
        "    return decorator\n\n"
        "def model_validator(*args, **kwargs):\n"
        "    def decorator(function):\n        return function\n"
        "    return decorator\n",
        encoding="utf-8",
    )
    (fake_modules / "yaml.py").write_text(
        "def safe_load(value):\n    return {}\n",
        encoding="utf-8",
    )

    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(fake_modules)
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            "import runpy; runpy.run_path('app.py', run_name='cloud_probe')",
        ],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
