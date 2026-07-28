# Baseline Inventory — Phase 0 (branch `kimi-warroom-final-audit`)

Baseline point: `main` @ `5c72d58e4ea91b6725bc59143869e864c1028408` (working tree was clean at branch time).

## Repository shape (tracked)

| Metric | Value |
|---|---|
| Tracked files | 1775 |
| Tracked size | ~271.7 MB |
| Python source files | 624 |
| Versioned report artifacts (V*.json/md/txt) | 513 |
| Shell launchers (.bat/.ps1) | 85 |
| Data/config (json/csv/parquet) | 150 |
| Documentation (.md) | 86 |
| Images (tracked PNG) | 14 |
| .gitignore | **MISSING at baseline** |

Machine-readable details: `manifest.json`, full tree with sizes: `file_tree.txt`,
dependency snapshots: `dependencies.json`, key-file SHA-256: `manifest.json.key_file_hashes`.

Regenerate with: `python tools/audit/build_baseline.py`

## Startup commands (as found at baseline)

- Primary app: `streamlit run app.py` (Streamlit shell rendering `dashboard.html` + injected snapshot).
- Background data worker: `python warroom_data_worker_v101.py [--once|--full]`.
- Packaged v3 CLI (pyproject): `warroom = warroom_v3.cli:main` (package under `src/`).
- Docker: `Dockerfile` + `docker-compose.yml` present (not exercised in Phase 0).
- 85 `.bat` launchers, mostly per-version `CHECK_VNN.bat` wrappers.

## Test inventory (as found at baseline)

- `tests/` — 18 pytest modules (contracts, gates, pipeline, registry_release, streamlit_release, trading_workstation, ...) targeting `src/warroom_v3` via `pythonpath = ["src"]`.
- `hardening_tests/` — 12 pytest modules tied to historical versions (v52–v73).
- Root-level `validate_*.py` / `verify_*.py` / `audit_*.py` — ~80 ad-hoc per-version validation scripts, not pytest-integrated.

## UI / tab inventory (as found at baseline)

- Single-page dashboard: `dashboard.html` (25 KB template) rendered inside Streamlit via `components.html`, data injected as `window.DASHBOARD_DATA`.
- `dashboard_live.html` (7.2 MB) — generated artifact tracked in git (bloat candidate).
- Tab/panel structure lives inside `dashboard.html` JS; enumerated in Phase 1 mapping.

## Module inventory (as found at baseline)

- `warroom/` — 50+ decision modules (liquidity, crash_lead, rotation, decision_engine, walkforward, ...).
- `engines/` — 24 engines (bottleneck, fx_carry, regime_transition, markov_regime_v3, scrapers, ...).
- `src/warroom_v3/` — packaged v3 kernel (api, cli, pipeline, gates, registry, validation, ...).
- Root — 400+ flat versioned scripts (`*_vNN.py`), many duplicates of each other.

## Data-source inventory (as found at baseline)

- `data_layer.py` (legacy bundled) + `current_context_v101.py` (persistent collectors).
- `official_source_connectors.py`, `full_live_data_hub.py`, `engines/*_scraper.py` (AAII, Barchart, CFTC COT, CME, DefiLlama, Laevitas).
- FRED series via `data_layer.FRED_SERIES`; quotes via yfinance (`requirements.txt`).
- Detailed lineage audit: Phase 4 (`docs/audit/DATA_LINEAGE_REPORT.md`).

## Current failures (Phase 0)

- Not yet reproduced; Phase 3 records exact startup/test results in `docs/audit/TEST_RESULTS.md`.
- Known at sight: no `.gitignore`; 7.2 MB generated HTML + PNG previews + `*.bak` tracked;
  `decision_packet_v98.py.bak` backup file tracked; `__pycache__`/`.pytest_cache` present in worktree.
