# R5 Data Coverage & Licensing Matrix (2026-07-28)

Universe masters: data/universe/*.json (schema warroom.universe_master.v1)
Gap registry: data/coverage/gap_registry.json | Coverage report: data/coverage/coverage_report.json

## Universe coverage

| Market | Instruments | Tier A | Tier B | Tier C | Source |
|---|---|---|---|---|---|
| US | 13,021 | 197 | 4,998 | 7,826 | Nasdaq listed/otherlisted snapshot 2026-07-17 + S&P 500 membership history (delisted, research grade) |
| IHSG | 15 | 15 | 0 | 0 | warroom price-fed sleeve |
| Crypto | 103 | 7 | 96 | 0 | price-fed + CoinGecko top-100 live |
| Commodities | 11 | 8 | 3 | 0 | price-fed ETF proxies + exact CL/GC/HG contract specs |
| FX | 6 | 6 | 0 | 0 | pair master with conventions |

## License gaps (9 registered, recall impact quantified)

| Domain | Status | Provider required | Recall impact |
|---|---|---|---|
| us.delisted_history_full_market | LICENSE_REQUIRED | CRSP/Sharadar/Compustat | HIGH outside S&P 500 (extreme-winner cohorts) |
| us.pit_fundamentals | LICENSE_REQUIRED | SEC EDGAR + PIT vendor | HIGH (backlog/ASP activation inputs) |
| ihsg.full_universe_master | LICENSE_REQUIRED | IDX feed | HIGH (~900 issuers vs 15; small-cap multibaggers missed) |
| ihsg.broker_summary_done_detail | LICENSE_REQUIRED | IDX broker summary | MEDIUM-HIGH (IDX flow activation) |
| crypto.venue_exact_derivatives | LICENSE_REQUIRED | Binance/Deribit APIs | MEDIUM (positioning timing) |
| crypto.onchain_fees_usage | LICENSE_REQUIRED | DeFiLlama/Artemis | MEDIUM-HIGH (value-capture theses) |
| commodities.exact_futures_history | LICENSE_REQUIRED | CME Datamine/CHRIS | MEDIUM (curve/roll) |
| commodities.physical_inventories | LICENSE_REQUIRED (EIA key free) | EIA/USDA/LME | HIGH (physical-shock + crash meter) |
| fx.forwards_options_tff | LICENSE_REQUIRED | CFTC TFF + vendor | MEDIUM (carry crowding) |

## Refresh plane

tools/refresh.py: phase 1 fast quote snapshot (5 markets interleaved, per-market publish,
~5s total, NO_DATA keeps null price — verified live 2026-07-28: US 200 current/7 no_data
(delisted, honest), IHSG 15/0, Crypto 7/0, Commodities 8/0, FX 6/0);
phase 2 slow cache + feeds (build_cache.py, build_feeds.py) never blocks fast publish.
Progress + exact provider errors: runtime/refresh_status.json.

## PIT admission

warroom/pit.py: source/market/venue/instrument/retrieval_ts/release_ts/available_at/
vintage/revision/sha256/schema/license/state. release_ts > available_at rejected.
Unknown release stays null, never zero/fabricated. is_pit_eligible(decision_ts) enforces
no-look-ahead. States: CURRENT/STALE_LAST_KNOWN/HISTORICAL_REFERENCE/PARTIAL/NO_DATA/
ERROR/LICENSE_REQUIRED.

## Bottleneck evidence store

data/bottleneck/archetypes.json: 26 archetypes (P2 library) with causal role, state
variables, transmission, monetization, lag, supply response, substitutes, invalidation,
claim limits, required data, market applicability. NAND vs DRAM/HBM pools explicitly
separated (memory_storage_capacity archetype claim_limit).
data/bottleneck/evidence.jsonl: 5 sourced records (SNDK Q2/Q3 FY26 earnings, ASP>cost
spread, TrendForce eSSD +80%, NAND +70-75% forecast) — all marked SECONDARY_REQUIRES_VERIFICATION
against EDGAR/TrendForce primary sources, PIT-admitted, HISTORICAL_REFERENCE state.
data/bottleneck/case_studies/sndk_pit_case.json: blind-replay harness, 3 frozen decision
dates, outputs PENDING (filled by R7 replay, never by hand), no score boost.

## Hardcode removal (R5 finding)

engines/coatue_methodology.py + engines/leopold_methodology.py contained hand-picked
per-ticker "score" values (incl. SNDK) flowing into displayed output. Renamed to
"curator_prior" + score_provenance=CURATOR_PRIOR_UNVALIDATED (zero capital weight).
Test test_sndk_no_score_boost_in_code guards repo-wide.
