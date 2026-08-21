# Knowledge Migration — old files classified (Keep / Refactor / Merge / Archive / Reject)

Per your point that old files are KNOWLEDGE not data. What was carried and how (not exhaustive; the
full ~200-file table is large — this is the decision summary for the load-bearing ones):

## KEEP (logic valid, used as-is)
gcfis brain (57 files: orchestrator, liquidity/fragility/shock/forward_macro, backtest gold-standard
tests, entry, bottleneck), warroom signal/UI engines (53), data.loader + data.fred_loader (v40's live
loaders), bandarmetrics_engine, reflexivity, flow_regime, cftc_cot_scraper, onchain_engine.

## REFACTOR (idea good, reimplemented)
- accumulation logic → generalized into `inventory_transfer_engine.py` (this turn)
- markup-readiness → validated + wired as the price-signal path
- fear_greed/crash/funding → kept but need cross-section inputs wired (composition_audit findings)

## MERGE (folded to avoid duplication)
- position-building indicators → merged into ITE's evidence layers
- risk_range_v20 / risk_range_engine (duplicate ports) → one kept
- entry_score (cosmetic) → flagged for merge-or-delete

## ARCHIVE (reference; needs feeds/track-record, not built to avoid faking)
narrative/theme/rotation-detection, narrative-attribution, variant-perception, expectation/surprise,
information-advantage, alpha-decay, prediction-audit, scorecard, meta-learning, market-microstructure.
Reason: each needs alt-data feeds (earnings transcripts, job postings, patents, options L2, 13F) or a
live track record accumulated over calendar time. Per your no-fabrication rule, not stubbed.

## REJECT (bloat / superseded)
cem_karsan_universal, odte_monitor, vanna_proxy, spotgamma_gex, methodology_pack (text), warroom_engines
(old bridge), yfinance_options (needs paid options).

## What's genuinely still MISSING vs your docs (honest gap list, all feed-gated)
Theme-Discovery, Universal Rotation-Detection (10-layer), Knowledge-Graph expansion, Supply-Chain scanner,
Event engine, Narrative-Attribution ("why did X rerate"), the 15-layer Position-Building (full),
Inventory-Transfer multi-evidence (options/insider/13F/earnings-language). Buildable once feeds are live.
