# Original Warroom preservation / quarantine

The user's original Warroom source is preserved under `legacy_warroom_original/`, including the original `app.py`, `run.py`, `data_layer.py`, `warroom/`, `gcfis/`, research data, and dashboard assets.

It is intentionally **not imported by the active EROS application**. The old code contains price-derived/technical directional paths (including fallback price signals) that conflict with the current EROS production doctrine. It remains available for UI/data/reference migration and independent research only.

The active runnable entry points are at repository root:

- `app.py` — Streamlit Warroom UI
- `run.py` — CLI engine + dashboard build
- `run_eros.bat` — Windows one-click launcher
- `run_eros.sh` — Linux/macOS launcher
