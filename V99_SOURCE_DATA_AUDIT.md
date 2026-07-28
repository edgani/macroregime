# War Room OS COMPLETE — Data Audit

Audited archive: `warroom_os_COMPLETE (6)(3).zip`
SHA-256: `92c670a92b3a594fb5775c45ce00c4fcaed4f9dcff14ac06e8c7acaf04886a9a`

## Archive inventory

- ZIP members: 232
- Uncompressed size: 16,465,288 bytes
- Python files: 168
- JSON files: 9
- Parquet files: 6
- CSV files: 2

## Real historical research data present

- `research/sp500_panel.parquet` — 13,054,119 bytes; columns: date, open, high, low, close, volume, Name. Package documentation identifies it as a 482-name S&P 500 panel covering 2013–2018 and flags fixed-constituent survivorship bias.
- `research/macro_panel.parquet` — columns: spx, cape, cpi_yoy, rate10, gold, oil, gas, dxy, Date. Package documentation identifies coverage as 1881–2023.
- `research/macro_attribution.parquet` — Shiller fields plus ret, cape, cpi_yoy, rate, rate_chg, vol12, fwd_dd12.
- `research/shiller.csv` — 1,866 monthly rows, 1871-01-01 through 2026-06-01.
- `research/vix.csv` — 9,219 daily rows, 1990-01-02 through 2026-07-01.
- `research/factor_ic.parquet` — factor IC validation results.
- `research/validated_tickers.parquet` — per-ticker validation fields.
- `research/bt_nobootstrap.parquet` — historical backtest summary fields.
- `research_results.json` and `metric_grades.json` — saved research verdicts/grades.

## Structured reference data present

- `data/extended_universe.json` — 66 discovered + 12 user-requested symbols.
- `data/chain_reactions.json` — 10 causal-chain definitions.
- `data/ihsg_conglomerates.json` — 21 Indonesian conglomerate maps plus alliance/macro notes.
- `data/bottleneck_reference.json` — 68 ticker heatmap entries, 12 photonics layers, catalyst timeline and risk/reference records.

These are structured research/reference inputs, not point-in-time market histories or validated live feeds.

## Runtime/current state bundled in the ZIP

`desk_data.json` is not live:

- generated: 2026-07-06T02:11:48Z
- source: SYNTHETIC
- FRED source: OFFLINE
- US/IDX/crypto/commodity/FX sources: synthetic offline fallback
- setups: 0 for all five markets

No bundled runtime cache was found for:

- `.price_cache.pkl`
- `.cache/fred_v3/*.parquet`
- `data/feeds_snapshot.pkl`
- execution/current quote file
- SQLite/DuckDB database

`data/snapshot.json` contains only a saved timestamp, not the snapshot payload.

## Root cause of empty dashboard

`app.py` calls `data_layer.load_all(allow_live=True)`, which tries to fetch current Yahoo/FRED data at runtime. It does not use the bundled research Parquet files as current market feeds. When outbound fetch fails, the system falls back to synthetic data. Therefore the dashboard can show NO_DATA even though historical research files exist in the archive.

## Correct verdict

The archive does contain substantial real historical US-equity and macro data, plus structured narrative/universe/reference data. It does not contain a complete current point-in-time data plane for all five markets. The dashboard problem is primarily data wiring, persistence, and coverage separation—not total data absence.
