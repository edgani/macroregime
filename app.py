"""EROS v3.0 Streamlit entry point."""

import sys
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent / "src"
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

from eros.app.shell import render_app  # noqa: E402, I001


if __name__ == "__main__":
    render_app()
