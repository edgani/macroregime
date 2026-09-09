# Story / Expectation Optionality Module — v3.1

## Objective
Capture a specific hypothesis without encoding the dangerous shortcut `loss-making = bullish`.

The module asks:
1. Is the company actually loss-making?
2. What kind of loss is it?
3. Are revenue, gross margin, net margin and/or FCF beginning to improve?
4. Is the investment intensity (R&D/capex) consistent with a plausible future-economics story?
5. Can the balance sheet survive long enough for the story to play out?
6. Has share count already expanded materially?
7. For US stocks, are analyst expectations actually revising upward?
8. Is valuation still supportable under a same-sector framework?

## IHSG
Outputs:
- `loss_type`
- `story_optionality_score`
- `story_credibility_score`
- `story_state`
- `cash_runway_years`
- `debt_to_cash`
- `financing_risk`

A high-quality loss story may add **at most one evidence family**. Broker/transaction evidence remains separate, also bounded, so neither story nor broker activity can overwhelm fundamentals.

## US stocks
Adds current analyst expectation data:
- next-year EPS current estimate
- next-year EPS estimate 30 days ago
- 30-day up/down EPS revision breadth
- analyst count
- next-year revenue estimate growth

Outputs:
- `expectation_revision_score`
- `expectation_revision_state`
- `expectation_optionality_score`
- `expectation_optionality_state`

US story optionality only becomes confirming evidence when improving economics and upward analyst revisions agree.

## Loss classification
- `PROFITABLE / NOT A LOSS STORY`
- `TURNAROUND LOSS`
- `INVESTMENT-LED LOSS`
- `EARLY INFLECTION / UNCLEAR LOSS`
- `STRUCTURAL / BAD LOSS`
- `UNCLASSIFIED LOSS`

## Valuation
Positive-EPS companies continue to use same-sector P/E.

Loss-making companies fall back to **same-sector Price/Sales**, using projected revenue. The fallback is blocked when fewer than four valid same-sector peers are available. It never falls back to a broad-market multiple.

## Important limitations
- Current Yahoo analyst data is not historical PIT before the first local snapshot. Market Memory creates PIT history only from the moment this build starts recording it.
- Corporate-action/news catalysts are not automatically treated as verified facts in this module.
- IHSG transaction APIs remain optional and require their configured keys.
- This is a research signal system, not proof of market-maker intent or manipulation.
