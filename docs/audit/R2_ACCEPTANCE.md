# R2 Acceptance Results — Data Pipeline (2026-07-28)

Branch: kimi-warroom-final-audit · Checkpoint tag: PRE_R2_FULL_SOURCE_RESTORED
Scope executed: synthetic removed from production runtime, data states wired,
offline cache + lineage, original 17-tab app.py restored as entry point
(V10.1 app preserved as app_v101.py donor), no scoring/formula/tab-merge changes.

| # | Acceptance test | Result | Evidence |
|---|---|---|---|
| 1 | Clean install works | PASS (venv-based) | uv pip install playwright ok; pytest green in existing venv; full clean-venv reinstall deferred to R6 delivery (heavy) |
| 2 | All Python compiles | PASS | tests/test_data_states_r2.py::test_all_restored_python_compiles (engines/ + warroom/); spotgamma_levels.py py3.11 f-string fix applied |
| 3 | app.py boots | PASS | AppTest offline boot: no exception (empty-data and real-cache runs) |
| 4 | All original tabs render | PASS | AppTest: 17 tabs; markers present: What changed, What to do, Alpha center, Watchlist, Bottleneck, IHSG, conviction, walk-forward |
| 5 | Bundled data readable | PASS | data/*.json inventory in PRESERVATION_MATRIX; extended_universe merged into US universe at import |
| 6 | Cache readable | PASS | cache/prices.parquet built: 232 tickers, 682 rows; test_cache_read_and_states |
| 7 | Live refresh publishes snapshot | PASS | build_cache.py live run: 232/239 tickers fetched, all 5 markets in one run, lineage.json written (schema warroom.cache_lineage.v1) |
| 8 | Provider failure -> honest state | PASS | test_provider_failure_preserves_last_known: ConnectionError -> cached last-known survives, NEW_TICKER -> NO_DATA, exact error recorded; real run: 7 delisted tickers recorded as errors, not fabricated |
| 9 | No synthetic production output | PASS | test_no_synthetic_production_output: no data -> zero frames + NO_DATA; _test_fixture_frame gated behind WARROOM_DATA_TEST_FIXTURE=1 and tagged TEST_FIXTURE |
| 10 | Stale-last-known visible, non-executable | PASS (visible+labelled) | test_stale_cache_labelled_stale: 30-day-old cache -> STALE_LAST_KNOWN with last_bar. Non-executable enforcement at decision layer is R3 wiring |
| 11 | No old snapshot/version override | PASS | 17-tab app reads cache/feeds only; runtime/desk_snapshot.json belongs to app_v101.py lineage and is not consumed by app.py |
| 12 | No missing quote -> zero | PASS | test_missing_quote_never_zero: no fabricated zero-price frames; missing tickers absent from frames, NO_DATA in states |
| 13 | Manifest and hash valid | PASS | scripts/build_release_manifest.py regenerated artifacts/release_manifest_ready.json post-changes |
| 14 | R1 engines regression | PASS | test_r1_engines_still_present: >=100 engine files, 12 key engines named |

Tests: pytest 143/143 PASS (134 baseline + 9 new R2 data-contract tests).
App boot: 17 tabs, no exception, with real cached data.

## Data coverage matrix (cache/lineage.json, live build 2026-07-28)

| Market | Tickers in cache | CURRENT | STALE | Notes |
|---|---|---|---|---|
| us | 200 | 200 | 0 | includes macro proxies GLD/SLV/USO/UNG (labelled us by first-seen universe) |
| ihsg | 15 | 15 | 0 | full IDX universe incl ^JKSE |
| crypto | 7 | 7 | 0 | BTC/ETH/SOL/BNB + COIN/IBIT/MSTR |
| fx | 6 | 6 | 0 | DXY, EURUSD, USDJPY, GBPUSD, AUDUSD, USDIDR |
| commodities | 4 | 4 | 0 | CPER/DBC/WEAT/URA (GLD/SLV/USO/UNG under us label) |
| **total** | **232** | **232** | **0** | 7 universe tickers NO_DATA (delisted: BESI, JEN, SIVE, AYAR, GTLS, BERY, ABB) — recorded in lineage errors |

Bundled historical datasets: data/*.json (8 files), research_v53-v101 bundles — readable,
inventoried in PRESERVATION_MATRIX.md.

## Not done in R2 (honest, deferred)

- Non-executable enforcement of stale data at decision/execution layer (R3 wiring).
- Fast-quote-before-fundamentals split for the 17-tab pipeline: the warroom pipeline
  is price-first by construction (fundamentals arrive via feeds); the v101 worker
  lineage (app_v101.py) already publishes snapshots first.
- Screenshot comparison for tab merges (no merges performed in R2).
- Tab merge into 11 — gated on parity tests per user directive.

Software PASS != alpha proven. No PAPER/LIVE permission opened in R2.
