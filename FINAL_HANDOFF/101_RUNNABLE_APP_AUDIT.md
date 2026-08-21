# EROS Runnable App Packaging Audit

## Correction
The prior `EROS_FINAL_PRODUCTION_20260822` package was not a proper successor to the user's original Warroom application because it omitted the root Streamlit `app.py` and the original Warroom application structure. Its static `dashboard.html` generator also emitted invalid JavaScript due to an unescaped newline in a single-quoted JS string.

## Fixed in this build
- Root `app.py` restored as the active Streamlit Warroom entry point.
- Root `run.py` restored as a CLI entry point.
- Windows one-click `run_eros.bat` + `setup_windows.bat` added.
- Linux/macOS `run_eros.sh` added.
- `dashboard.html` generator rewritten and Node syntax-checked.
- Five active UI tabs: Command Center, Global Explorer, Opportunity Engine, Portfolio, Research Lab.
- Original Warroom code preserved under `legacy_warroom_original/` including original `app.py`, `run.py`, `data_layer.py`, `warroom/`, `gcfis/`, dashboard assets and research data.
- Legacy Warroom is quarantined from active production because old price-signal/technical directional paths conflict with current EROS doctrine.
- Legacy parquet research data copied under `data/legacy_research/` for explicit research/revalidation only.

## Execution checks performed in the build environment
- Python compileall: PASS.
- Active CLI `python run.py`: PASS.
- App model/artifact load: PASS.
- Attachment scenario acceptance: PASS.
- Generalized scenario discovery: PASS.
- Event-router tests: PASS.
- Ticker fail-closed test: PASS.
- Strict software acceptance: PASS (scientific full scope remains limited by documented data debt).
- Generated dashboard JavaScript checked with Node `--check`: PASS.
- Runnable app packaging acceptance: PASS.

## Environment limitation of this audit
The audit container does not have outbound package-install access, so the Streamlit server itself could not be launched here after attempting to install Streamlit. The Windows/Linux launchers create a virtual environment and install `requirements.txt` on a normal internet-connected machine. All application source and non-Streamlit model paths were executed/tested locally.
