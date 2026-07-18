# War Room OS v6 — Deep Re-Audit and Regression Closure

## Why v5 lost content

The missing Alpha and incomplete Mission Control were integration regressions, not normal feed behavior.

1. `run.py` explicitly set the current Alpha output to an empty list until the separate SEC Foundry ran.
2. The original 14-tab visual shell was retained only superficially; many rich tab bodies were replaced by registry/proof-state pages.
3. The GCFIS orchestrator calculated internals, crash/bottom state, lead-lag, per-ticker evidence, ranking summaries and final-desk objects, but those objects were discarded before dashboard injection.
4. Supply Chain, Company Intel and Knowledge Graph had reference/runtime sources but displayed only component registries.
5. The last-known-good desk cache did not reject an older/incomplete desk schema.
6. The Alpha Foundry package embedded in the patched app was missing its historical S&P membership reference files, so its own pipeline test could not fully pass.
7. The release contained stale synthetic standalone outputs and Python/pytest cache artifacts that could confuse review.

## v6 fixes

- Restored the original visual shell and all 14 navigation tabs.
- Removed legacy hard-coded current `ALPHA`, `TABS` and `MARKET` JavaScript payloads.
- Removed dead mock regional-state fallback and initial MOCK/SYNTHETIC header labels.
- Mission Control again displays:
  - systemic state;
  - feed health/freshness;
  - multi-timeframe regime;
  - regional regime;
  - cross-market opportunity watch;
  - early-warning state;
  - flow/rotation observations;
  - Alpha proof state;
  - permission/integrity.
- Alpha now has two separate layers:
  - current tactical discovery watch generated from surviving runtime setups;
  - frozen US Alpha Foundry output generated only by its own research pipeline.
- Tactical Alpha rows are explicitly `UNPROVEN_RESEARCH_WATCH` and are removed if their underlying setup is quarantined.
- Macro, Early Warning, Flow, Supply Chain, Company Intel, Knowledge Graph and Validation receive rich runtime payloads rather than registry-only content.
- Reference chains/bottlenecks are labelled `REFERENCE_ONLY_NOT_CURRENT_SIGNAL`.
- Added desk schema version `V6_RICH_DYNAMIC_2026_07_18`; older last-known-good desks are rejected.
- Migrated feed cache namespace to `market_v6` to prevent stale v5 cache collisions.
- Restored required Alpha Foundry historical reference files:
  - `sp500_ticker_start_end.csv`;
  - `current_us_universe_2026-07-17.csv`;
  - source receipts.
- Removed packaged `desk_data.json`, `dashboard_live.html`, `.cache`, `__pycache__`, `.pytest_cache` and `.pyc` files.
- Updated launcher so it does not reinstall dependencies on every start; temporary PyPI outages no longer prevent startup when dependencies already exist.

## What Alpha means now

The tactical discovery watch prevents an empty Alpha UI when valid runtime setups exist. It is not the
same thing as a proven cross-sectional selector. The frozen US Alpha Foundry remains a separate layer and
requires its historical pipeline, one-shot lockbox and prospective evidence.

## Honest data behavior

The app uses real provider data or a persistent last-known-good cache. It never creates synthetic current
prices. A first launch with both no network and no cache cannot display current market observations, but
all tabs still render their complete panels and explicit empty/data-health states.

## Final audit surface

- rich-data synthetic contract: all 14 tabs render;
- no-data first-run contract: all 14 tabs still render without JavaScript errors;
- cross-tab ticker identity: tactical Alpha is a subset of surviving setup surfaces;
- ETF/index filtering: US ETFs and `^JKSE` do not surface as stock candidates;
- current dashboard values: runtime-bound only;
- PAPER/LIVE: blocked.
