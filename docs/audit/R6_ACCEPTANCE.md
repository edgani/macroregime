# R6 Acceptance — Market-Specific Causal Alpha Foundation (2026-07-28)

Checkpoint tag: PRE_R6_MARKET_SPECIFIC_PROOF. Base: R5 dd0f8f5 (pushed, verified).

## Deliverables (master prompt §2.4)

| # | Deliverable | Status | Evidence |
|---|---|---|---|
| 1 | Five market contracts | DONE | warroom/market_contracts.py — 24 required fields each; validate()=0 errors; metric/activation sets provably different per market |
| 2 | Market-specific bottleneck registry | DONE | data/bottleneck/registry.jsonl — 10 records, full §2.1 schema, proof_status=MAPPED |
| 3 | Thesis library | DONE | registry + data/bottleneck/archetypes.json (26 archetypes) + evidence.jsonl (5 sourced records) |
| 4 | Activation board | DONE | data/bottleneck/activation_board.json — 10 theses, all YELLOW_ARMING (fail-closed: only catalyst_proximity admitted; every gated input listed explicitly; no GREEN without value bridge + fresh quote + risk plan) |
| 5 | SNDK/PLTR blind replay report | PARTIAL BY DESIGN | data/bottleneck/case_studies/blind_replay_results.json — price-side FACTS from PIT bars; fundamental activation DATA_GATED (licensed PIT sources); Top-K/rank PENDING R7 tournament |
| 6 | Extreme-winner cohort definition | DONE | data/cohorts/extreme_cohorts.json — frozen thresholds/horizons BEFORE testing; computed on Close-only panel (207 tickers): +100%:137, +200%:97, +300%:67, +500%:47; -50%:84, -70%:21; survivorship caveat registered |
| 7 | False-lookalike cohort | DEFERRED TO R8 | requires same-date matched controls — part of selector tournament design |
| 8 | Market-specific activation candidates | DONE | per-contract activation_inputs (US 14, IHSG 14, crypto 12, commodities 13, FX 14); RSI/MACD/SMA/EMA/VWAP/chart-pattern/momentum/breakout hard-blocked (token-level) |
| 9 | Exact data gaps | DONE | gap registry (9) + per-board missing_inputs + contract claim_limits |
| 10 | R6 tests | DONE | tests/test_r6_market_separation.py — 10 tests |
| 11 | Commit/push/ZIP | DONE | see git log; milestone ZIPs |

## Blind replay price facts (real bars, yfinance PIT)

SNDK: 2025-06-30 px $45.35 → 99.6% of full move remaining (+5048.8% to peak, MAE -10.3%);
2025-09-30 px $112.20 → 96.7% remaining; 2025-12-31 px $237.38 → 91.2% remaining.
PLTR: 2024-01-31 px $16.09 → 96.7% remaining (+1187.6% to peak, MAE +1.5%);
2024-06-28 px $25.33 → 92.0%; 2024-10-31 px $41.56 → 83.8%.
Interpretation: all frozen dates are valid early-detection tests (most of the move still
ahead). Whether the SYSTEM would have detected at those dates is an R7/R8 selector
question — not asserted here.

## Honest limits

- No formula optimization performed (mapping frozen first, per prompt).
- All curated chain research = MAPPED, zero capital weight.
- GREEN activation is currently impossible by construction (fundamental feeds gated) —
  that is the fail-closed design working, not a bug.
- 176 passed + 2 slow-boot skips (verified separately). R4 parity intact. Zero alpha claims.
