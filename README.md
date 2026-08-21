# EROS Warroom — Runnable Build

This package restores the runnable application structure that existed in the original Warroom while keeping the newer EROS fail-closed research/scenario/ticker architecture active.

## Windows — easiest

1. Extract the ZIP.
2. Double-click `run_eros.bat`.
3. First launch creates `.venv` and installs dependencies.
4. Browser opens/visit `http://localhost:8501`.

Manual Windows:

```bat
setup_windows.bat
.venv\Scripts\activate
python -m streamlit run app.py
```

CLI test:

```bat
run_cli.bat
```

## Linux/macOS

```bash
chmod +x run_eros.sh
./run_eros.sh
```

## Active application files

- `app.py` — actual Streamlit app / Warroom UI
- `run.py` — CLI run + dashboard generator
- `final_core/` — active EROS production/research logic
- `tests/` — scenario/router/ticker fail-closed tests
- `FINAL_HANDOFF/` — scientific/audit artifacts
- `data/` — current, factual, research, reference data
- `dashboard.html` — generated offline snapshot

## Original Warroom

The complete original Warroom source is preserved in `legacy_warroom_original/` so the old architecture/assets are not lost. It is quarantined from active production because some legacy paths used technical/price-derived directional alpha that is forbidden by the current EROS doctrine.

## Important scientific behavior

The app is runnable, but it remains fail-closed: if calibrated PIT company data / scenario probability / priced-in / EV inputs are absent, the correct ticker output is `NO QUALIFIED OPPORTUNITY` rather than a fabricated ticker.
