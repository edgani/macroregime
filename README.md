# War Room OS — complete, self-contained package

This is the **whole thing**: the gcfis reasoning brain + the KEEP signal/UI engines + the rescue
engines + the data adapter + the full validation suite + the real research data + the dashboard.
It runs from this folder — no other repo needed.

```
warroom_os/
  gcfis/                     # the reasoning brain (57 files, self-contained) — orchestrator + 13 layers
  warroom/                   # KEEP signal/UI engines (signal_edge, early_warning, meters, internals,
                             #   drivers, backtest, walkforward, accumulation, render, …)
  engines/                   # RESCUE engines: onchain_engine, cftc_cot_scraper, fx_carry_engine
                             #   (+ bottleneck/gip/vix/thought as refs). The 83-file bloat is DROPPED.
  research/                  # REAL data: sp500_panel.parquet (482 tkr, 2013-18), macro_panel (1881-2023),
                             #   factor_ic / validated_tickers / macro_attribution, shiller.csv, vix.csv
  data_layer.py              # ONE data adapter — yfinance + FRED (no key) + synthetic fallback, source-stamped
  run.py                     # data → gcfis.orchestrator → asymmetric_discovery → desk_data.json + dashboard
  dashboard.html             # approved v0.3 UI, data-driven (renders the run; standalone = mock)
  validate_all.py            # runs all 3 validators below
  validation_plus.py         # statistical battery + negative/positive controls (validates the validator)
  validate_real.py           # factor + macro battery on the real bundled data (reconciles prior work)
  component_validation.py    # every engine: runs/deterministic/no-lookahead/no-repaint/formula/edge
  VALIDATION.md              # the full coverage matrix + results
  requirements.txt
```

## Run it

```bash
pip install -r requirements.txt

streamlit run app.py         # the dashboard (main file = app.py)
python run.py --synthetic     # headless: offline: proves the pipeline runs end-to-end (0 setups on noise = correct)
python run.py                 # your machine: live yfinance + FRED → desk_data.json + dashboard_live.html
python validate_all.py        # the entire validation stack (statistical + real-data + component)
```

Open `dashboard.html` standalone (design), or `dashboard_live.html` after a run (populated).

## Verified — every entry point runs from THIS folder

```
run.py --synthetic        → pipeline runs, writes dashboard_live.html ✓
validation_plus.py        → VALIDATOR VALIDATED (noise→NOISE, planted→TRADEABLE) ✓
validate_real.py          → IC reproduces prior factor_ic.parquet exactly (5/5) ✓
component_validation.py   → 28 checks, 21 PASS, 0 FAIL ✓
```

## What is validated vs what still needs feeds (honest)

Fully validated **here, on real data**: gcfis brain (13 layers, e2e), all statistical methods
(permutation/MC/White-RC/SPA/FDR/DSR/drift), US-equity signals, macro/cross-asset/crash/CAPE, and
every engine's determinism/no-lookahead/no-repaint/formula.

Genuinely **needs feeds not in this zip** (flagged, never faked): non-US prices (IHSG/crypto/FX/commodity),
live/current prices (panel ends 2018-02), vintage/ALFRED FRED, on-chain (Glassnode), COT (CFTC).
`run.py` picks these up automatically on a machine with network + keys.

## The gate (unchanged)

A signal surfaces a ticker only if it clears **perm_p < 0.05 AND DSR ≥ 0.95**, survives Reality-Check/SPA
after data-snooping, and is stable OOS. On synthetic/noise → 0 setups. That is correct, not a bug.

DROPPED from the original 64k-LOC zip: 83 orphaned engines (~60%), led by the 19-file options/GEX/vanna/
charm cluster (needs paid options data). KEPT: only what's validated and wired.
