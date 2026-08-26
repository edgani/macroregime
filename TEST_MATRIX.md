# Test matrix — v2.3

| Area | Test | Release status |
|---|---|---|
| Syntax/package | Python compile / AST | PASS |
| Data files | required schemas / market classes / duplicates | PASS |
| Causal graph | required columns / minimum edge coverage | PASS |
| No-classic-TA contract | RSI/MACD/MA signal paths absent | PASS |
| Valuation | same-sector only / insufficient peers gated | PASS |
| Percentiles | tie-neutral midrank | PASS |
| Detection/entry | detection != entry | PASS |
| Entry | STARTER / CORE / ADD / NO CHASE / macro sizing | PASS |
| Revision logic | fair-value revision vs price revision | PASS |
| Expression | IHSG cash-only | PASS |
| Expression | US leverage when earned | PASS contract |
| Expression | FX/commodity fail-closed until dedicated model ready | PASS |
| Expression | BTC/ETH option eligibility / other crypto excluded | PASS |
| Timestamp | after-close earliest regular-session execution | PASS |
| Replay fixtures | SNDK Aug date correction + earliest execution fields | PASS |
| SEC PIT | filing-date cutoff parser | PASS |
| IDX | universe/report parsers | PASS |
| ALFRED/FRED | vintage CSV parser | PASS |
| Macro components | growth/inflation/labor/FC/fiscal/energy/crash/action | PASS |
| Macro fuzz | fiscal/energy bounds | PASS |
| Macro integration | supportive vs crisis synthetic snapshots | PASS |
| Macro failure | missing critical families -> MACRO GATED | PASS |
| Negative controls | weak hype / crypto revenue without capture | PASS |
| Fuzz | 5,000 randomized entry/expression cases | PASS |
| Walk-forward machinery | rolling purge + embargo + no-overlap | PASS |
| Synthetic OOS | injected causal relation sanity check | PASS mechanical only |
| State isolation | checkpoint previous/current behavior | PASS |
| Fresh-extract aggregate runner | all bundled suites | PASS at release freeze |
| Real full-universe PIT/OOS | survivorship-safe empirical market test | DATA NOT BUNDLED / GATED |
| Historical options OOS | IV/skew/OI/term structure | DATA NOT BUNDLED / GATED |
| Full global macro vintage OOS | non-US country modules | DATA NOT BUNDLED / GATED |
