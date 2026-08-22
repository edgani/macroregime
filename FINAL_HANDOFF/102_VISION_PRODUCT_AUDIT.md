# EROS Warroom Vision Product Audit — 2026-08-22

## Product correction

The prior runnable package was rejected because it behaved like a research console instead of a daily Warroom.

This rebuild changes the product flow to:

**AUTO FETCH → CURRENT STATE → WHAT MATTERS → VERIFIED SCENARIOS → SCENARIO RADAR → ASSET EXPRESSIONS → AUTO TICKER CANDIDATES → QUALIFICATION / WAIT**

Research artifacts are moved behind the daily interface into Research Lab.

## Acceptance results

`product_acceptance.py`: **19 / 19 PASS**.

Verified behaviors include:

- root `app.py`
- one-click Windows launcher
- exactly five main product tabs
- no mandatory company JSON uploader
- no synthetic production fallback
- no classic technical directional alpha in new EROS production package
- automatic factual/public-data fetching
- conservative event router
- general causal graph
- generalized news-scenario discovery
- automatic scenario-to-asset routing
- automatic scenario-to-ticker candidate generation
- no fabricated BUY/SHORT qualification
- complete old Warroom preserved as reference
- end-to-end mocked factual pipeline passes
- no-data path fails closed

## Scenario vision

The system now has a general event router plus causal graph, so its scenario layer is not restricted to the four supplied screenshot examples.

Screenshot themes remain valid acceptance archetypes:

- weak labor/housing versus sticky inflation and policy reaction
- mega IPO / capital formation / index mechanics
- AI data-center financing / securitization / credit fragility
- dealer gamma as execution/volatility context only

But arbitrary leads are also routed into event types and traversed through the causal graph to produce verification hypotheses.

## Important remaining scientific limitation

This package fixes the **product vision and runnable architecture**. It does not claim that unresolved PIT cross-market/company/scenario-calibration data debt has magically disappeared.

Ticker candidates therefore appear as `WATCH/RESEARCH`, `VERIFY`, or `NO_RANK` unless the required scientific qualification layer exists.

This is the intended distinction between a useful daily Warroom and fabricated certainty.
