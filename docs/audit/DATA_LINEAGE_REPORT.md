# Data Lineage Report — Phase 4 (branch `kimi-warroom-final-audit`)

Scope: production runtime surface only (`app.py`, `run.py`, `warroom_data_worker_v101.py`,
`data_layer_v101.py`, `current_context_v101.py`, `bundled_research_reader_v99.py`,
`public_snapshot_reader_v98.py`). Method: direct code reads + offline desk build smoke.
Network-dependent collectors were NOT exercised live in this audit.

## 1. Source-by-source lineage

| # | Source | Consumer | Vintage semantics | PIT-safe? | Code evidence |
|---|--------|----------|-------------------|-----------|---------------|
| 1 | FRED fredgraph.csv (14 series: INDPRO, PAYEMS, CPIAUCSL, PCEPI, WALCL, RRPONTSYD, WTREGEN, DFII10, T10YIE, BAMLH0A0HYM2, DFF, DGS2, DGS10, DTWEXBGS) | `data_layer._fetch_fred_series`, `current_context_v101._fred_series` | CURRENT VINTAGE. fredgraph.csv returns the latest revision; historical release timestamps are NOT reconstructed | NO — explicitly flagged `point_in_time_eligible=False` with `availability_semantics` note in `run.py:45-46` and `current_context_v101.py:312` |
| 2 | Yahoo quote API | `current_context_v101` quotes collector | live quote | Execution reference only (data_layer.py docstring); not evidence |
| 3 | Binance / CoinGecko | `current_context_v101` quotes collector | live quote | Execution reference only |
| 4 | yfinance equity fundamentals | `current_context_v101` fundamentals collector | current snapshot, no release-lag reconstruction | NO (context only) |
| 5 | CFTC TFF positioning (publicreporting.cftc.gov) | `current_context_v101._cftc_dataset` | release-lagged; lag disclosed in payload: `release_lag_semantics` + claim_limit "never a standalone signal" (`current_context_v101.py:499,504`) | Lagged — usable as context, not real-time |
| 6 | Central-bank policy-rate HTML scrape | `current_context_v101:521` | current page; no decision-date archive | NO — flagged `point_in_time_eligible=False` |
| 7 | Bundled research (`research/*.csv/parquet`, `data/`, `evidence/`) | `bundled_research_reader_v99` | frozen bundles, sha256 inventoried (`_sha256`, line 63) | Lineage per bundle recorded; note: "Presence and hash do not prove live alpha or point-in-time eligibility" (line 64) |
| 8 | Public-source snapshots (`runtime/v94_public_snapshots/`, nasdaq listed files) | `public_snapshot_reader_v98` | collected snapshots | Universe/reference only |
| 9 | `runtime/v99_decisions`, `runtime/v98_decisions` projection requests | `decision_packet_v99` | operator-supplied | n/a (operator input, not market data) |

## 2. Synthetic-data policy

`data_layer_v101.load_all(allow_synthetic=False)` hard-refuses synthetic data
(`data_layer_v101.py:25` raises when allow_synthetic is requested on this path — verified by
the offline smoke: `allow_live=False, allow_synthetic=False` builds with zero synthetic
admission). Live refresh is opt-in via `WARROOM_REFRESH_ON_LOAD=1` (line 28); default load is
offline from persisted collectors.

## 3. Missing-data handling

- FRED series that fail to fetch are simply absent from the `fred` map; `run.py:152` reports
  `NO_CURRENT_DATA` state instead of fabricating values.
- CFTC collector records per-dataset `failures` alongside datasets (line 504).
- v3 kernel: scopes with <100 finalized bars report `INSUFFICIENT_WARMUP` and the UI renders
  UNAVAILABLE instead of interpolating.

## 4. Known lineage gaps (honest register)

| Gap | Impact | Status |
|-----|--------|--------|
| FRED current vintage only | No historical macro backtest can be PIT-certified from this adapter | DISCLOSED in code; capital_eligible=False everywhere |
| yfinance fundamentals: no release-lag | Equity fundamental context not PIT | DISCLOSED (context only) |
| Central-bank scrape: no archive | Policy-rate history not reconstructable | DISCLOSED |
| CFTC TFF: release lag | Positioning usable only as lagged context | DISCLOSED |
| Live collectors unverified this audit | Yahoo/Binance/CoinGecko/yfinance/CFTC/CB scrape not exercised (network-dependent) | BLOCKED_EXTERNAL (no live probe run); offline path fully verified |

## 5. Conclusion

The production data plane is fail-closed about its own lineage: every non-PIT source carries an
explicit `point_in_time_eligible=False` (or lag disclosure) and `capital_eligible=False`.
No silent fallbacks or fabricated fills were found in the offline path. The main residual risk
is upstream: any future historical study built on `data_layer_v101` FRED pulls would embed
revised-data leakage unless a release-vintage source (e.g., ALFRED) is substituted first.
