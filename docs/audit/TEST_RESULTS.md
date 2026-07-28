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

Environment: same venv. Run at commit a60f413 + phase-3 repairs (uncommitted at run time).

- `pytest tests/ -q` immediately after cleanup commit: **118 passed, 6 failed**.
  - Same 5 `test_streamlit_release.py` failures as baseline (missing `streamlit_app.py`, plotly).
  - NEW failure: `test_release_ready.py::test_release_manifest_binds_operational_core` —
    cleanup deleted generated `artifacts/release_manifest_ready.json`; the manifest is
    regenerable via `scripts/build_release_manifest.py` (deferred to Phase 6, which also
    supplies `streamlit_app.py` required by the generator's INCLUDE list).
- Offline desk build smoke: PASS ("desk ok"), unchanged.
- Hardening scripts after cleanup: 4 regressions surfaced and repaired in Phase 3:
  1. `test_attachment_continuation_v53` + `test_cusp_research_v57` — cleanup moved the LIVE
     registry `research_evidence_registry_v53.json` into `research/archive/` while kept code
     `research_evidence_v53.py` reads it from repo root. Fix: registry restored to root
     (misclassification in cleanup plan corrected). 11/11 and 15/15 PASS.
  2. `test_parquet_compat_v55` — `projection_semantics` failed: pyarrow-backed read yields
     `datetime64[us]`, the pure-Python fallback reader yields `datetime64[ns]`, and
     `DataFrame.equals` is dtype-strict. Fix: `parquet_compat.read_parquet_compat` now
     normalizes all datetime64 columns to ns (backend-independent). 36/36 PASS.
  3. `test_hardening_v52` — was FALSE-GREEN at baseline (TypeError in
     `registry_and_valuation_tests`, exit masked). Repairs:
     - `component_status()` called with the forged registry row (current two-arg API);
       forgery assertion now checks fail-closed outputs (capital BLOCKED, decision_active
       False, live_weight 0.0, proof_run_valid False).
     - Receipt fixture updated to current `proof_receipts.REQUIRED_GATES` (16 gates),
       artifact hash roles (4 extra roles), prospective thresholds (obs>=200, regimes>=4,
       drawdown caps) and metric blocks (large_move/narrative_timing/realized/projection).
     - Static scan scope: excluded `.venv`/`node_modules`/`research/archive` (quarantined
       legacy) and allowlisted non-production legacy `data/resilient_market_data.py`
       (.pkl cache strings — recorded here as a finding: local self-written pickle cache,
       0 production references per docs/audit/production_reachable.json).
     - `PROOF_GATED` added to the deny-by-default permission set (run.py default state,
       does not authorize capital).
     - Scoped risk-cap file list updated for `research/archive/` paths.
     Result: **39/39 PASS, genuine exit 0** (previously crashed before static tests ran).
- Full hardening re-run after repairs: **12/12 scripts exit 0, 0 FAIL lines, 0 tracebacks**.

### After Phase 6 application repair

- `streamlit_app.py` created at repo root (was never committed): read-only workstation over
  the v3 kernel. Pages: Market Overview (8 metrics across 4 timeframes, UNAVAILABLE placeholders
  in empty state), Execution Planner (operator-supplied direction; `build_structural_template`
  + `calculate_manual_trade_plan`, claim ceiling OPERATOR_PLANNING_ONLY). Fail-closed: no
  finalized bars -> no template.
- `.streamlit/config.toml` aligned to the release contract: address 127.0.0.1, port 8501,
  enableXsrfProtection=true (matches ops/systemd + docker-compose localhost-only posture).
- `requirements.txt`: added plotly (was declared only in pyproject.toml).
- `scripts/build_release_manifest.py`: INCLUDE paths for the two historical status docs
  updated to their `research/archive/` locations; manifest regenerated to
  `artifacts/release_manifest_ready.json` (committed).
- `pytest tests/ -q`: **124 passed, 0 failed** (was 119 passed / 5 failed at baseline).
- Hardening scripts: 12/12 still exit 0 after Phase 6 (no interaction).

### Final end-to-end (Phase 8)

Run at HEAD of `kimi-warroom-final-audit` (2026-07-28):

- `pytest tests/ -q`: **134 passed, 0 failed** (124 kernel + 10 paper trading), ~6s.
- Hardening scripts: **12/12 exit 0, 0 FAIL lines, 0 tracebacks**.
- Offline desk build smoke: PASS.
- Production app boot smoke: `streamlit.testing.v1.AppTest.from_file('app.py').run()` —
  no exception (one upstream deprecation notice for `st.components.v1.html`; non-blocking).
  Boot regenerated `runtime/desk_snapshot.json` (+ static mirror, worker_status) from an
  offline desk build — committed as the smoke-run state.
- v3 workstation boot: covered by `tests/test_streamlit_release.py` (empty state + finalized bars).
- `git diff --check`: clean.
- Secrets scan (git grep over tracked non-archive files for credential literals and PEM
  blocks): no findings; only env-var name references in examples/config.
- Junk scan: no tracked `.pyc`/`__pycache__`/`.pytest_cache`/`.bak`; worker pid/lock
  gitignored.
- Paper-trading instructions: `docs/audit/PAPER_TRADING.md` verified end-to-end by
  `tests/test_shadow_paper_trading.py`.
- Evidence labels: `docs/audit/CLAIM_EVIDENCE_AUDIT.md`; no module labeled PROVEN.
