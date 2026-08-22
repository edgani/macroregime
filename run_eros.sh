#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv 2>/dev/null || true
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py --server.port 8501 --server.address 127.0.0.1
