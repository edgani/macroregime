# Final audit — Opportunity Intelligence Engine v2.3

## Release decision

**READY AS A FAIL-CLOSED RESEARCH/DECISION DASHBOARD.**

This means the software contract, entry separation, macro safety gates, expression restrictions, static integrity, negative controls, fuzz/property tests and mechanical walk-forward machinery pass the bundled validation suite.

It does **not** mean production-proven investment alpha. Components without sufficient historical point-in-time data remain gated.

## Major fixes frozen in this release

- Macro Control Room simplified to beginner-first action/projection/crash/scenario flow.
- Critical macro missing-data coverage now fails closed to `HOLD / MACRO GATED`.
- Early detection separated from entry.
- Entry lifecycle: DISCOVER → STARTER → CORE → ADD/HOLD → NO CHASE → TRIM/EXIT.
- Fair-value revision vs price revision added to add/no-chase logic.
- Options/leverage treated as expression after entry, never discovery.
- IHSG cannot leak into leverage/options.
- FX/commodities cannot be promoted to leverage from stock-style evidence.
- Crypto revenue alone cannot earn high-conviction entry; holder capture/usage/dilution readiness matters.
- BTC/ETH option adapter eligibility is explicit; illiquid token options are never invented.
- Whole-market valuation fallback removed; sparse same-sector peers gate fair value.
- Tie-percentile inflation fixed with neutral midrank.
- Publication timing guard added; known SNDK/PLTR after-close fixtures use next-session execution.
- SNDK FY2025 Q4 replay fixture corrected from 2025-08-07 to 2025-08-14.
- SEC PIT, IDX discovery/report, and ALFRED/FRED vintage parsers included.
- Checkpoint state can be isolated with `OIE_STATE_DIR`; the aggregate runner isolates state per test.

## Release test result

See `VALIDATION_RESULTS.md`. The package is built, extracted to a clean directory, and the bundled aggregate suite is rerun from that extraction before the final ZIP is retained.
