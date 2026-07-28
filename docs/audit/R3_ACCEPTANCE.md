# R3 Acceptance Results — Engine-UI Wiring (2026-07-28)

Checkpoint tag: PRE_R3_ENGINE_UI_WIRING. No tab merges/removals/renames performed.
Canonical contract: warroom/component_registry.py + warroom/crash_meter.py (new).
Registry: 30 components, one component_id per engine output, schema-validated.

| # | Acceptance test | Result | Evidence |
|---|---|---|---|
| 1 | All Python compiles | PASS | test_all_restored_python_compiles (incl. new warroom modules) |
| 2 | All existing tests pass | PASS | pytest 150 passed, 1 skipped (slow boot runs separately, PASS) |
| 3 | App boots | PASS | AppTest offline + real cache, no exception |
| 4 | All 17 tabs render | PASS | AppTest: 17 tabs; screenshots tab_01..17 post-R3 |
| 5 | Every tab has schema-tested live or honest-unavailable section | PASS | component registry covers all surfaced engines; NO_DATA sections honest (leverage/physical/gex feeds) |
| 6 | Crash Meter appears | PASS | Risk & Health detail panel + MC world-strip + tile; 12 subcomponents, drivers, disconfirming, invalidation, RESEARCH_ONLY |
| 7 | Structural and tactical Quad appear | PASS | MC world strip + Command Center; registry gip_structural_quad/gip_tactical_quad |
| 8 | Current/next/alternate Quad appear | PASS | world strip: structural(current)/next/alternate/transition stage |
| 9 | Carry output appears | PASS | FX tab carry + world strip carry stage; fx_carry_engine source of truth |
| 10 | Alpha Center distinguishes alpha/watch/excluded | PASS | conviction vs watchlist (WATCH=not alpha in registry claim_limit) vs decision_market gated candidates with MODEL_REQUIRED reason; test_alpha_watch_excluded_distinction |
| 11 | No missing price displayed as 0 | PASS | R2 contract tests + funnel check (close > 0) |
| 12 | No synthetic production output | PASS | R2 contract tests unchanged; crash meter NO_DATA for missing feeds |
| 13 | Stale visible but non-executable | PASS | test_registry_stale_not_executable: stale_days=30 -> all STALE_LAST_KNOWN, all execution_eligible=False |
| 14 | Every engine output has source/as_of/freshness/proof | PASS | registry canonical fields; test_registry_canonical_schema_valid |
| 15 | No duplicate engine source of truth | PASS | test_registry_no_duplicate_source_of_truth; duplicates documented in R3_WIRING_MATRIX |
| 16 | UI screenshot comparison all 17 tabs | PASS | docs/audit/screenshots/tab_01..17 regenerated post-R3 (comparison vs R2 set: same tabs, added sections visible) |
| 17 | Original feature preservation matrix complete | PASS | docs/audit/PRESERVATION_MATRIX.md unchanged, all rows still LIVE |
| 18 | Clean working tree | PASS | post-commit git status clean |
| 19 | Package manifest and hashes pass | PASS | artifacts/release_manifest_ready.json regenerated post-R3 |

Tests: 150 passed + 1 slow-boot (PASS when RUN_SLOW=1, 100s).
New tests: 7 R3 wiring tests (crash meter schema/severity/empty-desk, registry schema/
stale/uniqueness/quads-carry, alpha funnel honesty, integration boot markers).

Known gaps (honest, not hidden):
- crash_meter composite is an uncalibrated aggregation labelled RESEARCH_ONLY;
  per-horizon splits are placeholders pending R5 calibration.
- leverage + physical subcomponents NO_DATA (feeds not wired).
- gex/finra/typef/onchain/cot feeds need build_feeds.py live run; panels honest-unavailable.
- No tab merge yet (parity gate). No formula optimization yet (R5).
