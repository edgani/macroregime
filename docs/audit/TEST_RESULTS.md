# Test Results — War Room Final Audit

Environment (baseline reproduction):
- OS: Windows 10, shell: git-bash
- Python: 3.11.15 (uv-managed venv at `.venv/`, created with `uv venv .venv --python 3.11`)
- Installed: requirements.txt + requirements-dev.txt + fastapi, uvicorn[standard], plotly, scikit-learn, PyYAML
  (last five were missing from declared requirements — see ENVIRONMENT_REQUIREMENTS.md)

## Baseline run (branch point, main @ 5c72d58)

### pytest tests/ (v3 kernel suite)

- Command: `.venv/Scripts/python.exe -m pytest tests/ -q`
- Result: **119 passed, 5 failed** (duration ~7s)
- Failures (all in `tests/test_streamlit_release.py`):
  - `test_streamlit_app_and_config_exist` — `streamlit_app.py` does not exist
  - `test_streamlit_is_release_dependency` — `plotly` absent from requirements.txt
  - `test_app_compiles_without_importing_streamlit_runtime` — same missing file
  - `test_streamlit_app_boots_in_empty_state` — same missing file
  - `test_streamlit_market_and_planner_with_finalized_bars` — same missing file
- Collection errors fixed by installing undeclared deps (fastapi, scikit-learn) —
  recorded as dependency-audit findings, not test weakening.

### pytest hardening_tests/

- Command: `.venv/Scripts/python.exe -m pytest hardening_tests/ -q`
- Result: **INTERNALERROR, no tests ran** — `test_options_gamma_v70.py` executes
  `raise SystemExit(0)` at module import, killing the pytest worker.
  These are script-style checks, not pytest tests.

### hardening_tests as scripts (each `python <file>`, timeout 90s)

| Script | Exit | Note |
|---|---|---|
| test_attachment_continuation_v53 | 0 | 11/11 PASS |
| test_cusp_fragility_v73 | 0 | JSON report emitted |
| test_cusp_research_v57 | 0 | 15/15 PASS |
| test_hardening_v52 | 0 | **FALSE-GREEN: prints `TypeError: component_status() missing 1 required positional argument: 'row'`** |
| test_options_gamma_v70 | 0 | capital_permission=BLOCKED (expected) |
| test_options_prospective_v71 | 0 | capital_permission=BLOCKED (expected) |
| test_parquet_compat_v55 | 0 | source_mutations=0 |
| test_position_lifecycle_v59 | 0 | PASS |
| test_signed_dealer_v72 | 0 | tbt_rows=4 |
| test_v72_manifest_generators | 0 | PASS |
| test_v72_outcome_evaluator | 0 | PASS |
| test_v72_release_runners | 0 | PASS |

### Offline desk build smoke (production path)

- Command: `python -c "import data_layer_v101 as DL; from run import build_desk; desk=build_desk(DL.load_all(allow_live=False, allow_synthetic=False))"`
- Result: PASS in ~1s. `research_permission=ACTIVE`, `shadow_permission=WATCH_ONLY`,
  `packets=0` (no current quotes offline), no synthetic data admitted.

## Post-change runs

Appended below as phases complete. Every run records command, environment, duration,
pass/fail, skips and reasons.

### After Phase 2 cleanup

(pending)

### After Phase 6 application repair

(pending)

### Final end-to-end (Phase 8)

(pending)
