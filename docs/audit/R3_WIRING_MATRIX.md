# R3 Wiring Matrix — Engine → UI (2026-07-28, HEAD post-R2 24b5fca)

Canonical contract: every surfaced component is registered in
`warroom/component_registry.py` with fields: component_id, market, instrument,
as_of, source, data_state, freshness, value, confidence, horizon, drivers,
disconfirming, invalidation, claim_limit, proof_status, execution_eligible.
Validation: `tests/test_r3_wiring.py` (schema, uniqueness, stale-not-executable).

Data states come from `warroom/data.py` (CURRENT / STALE_LAST_KNOWN / NO_DATA / ERROR).
STALE renders but execution_eligible=False everywhere (no capital permission in R3).

| # | Tab | Section (UI) | Engine / source | Input dataset | Output | Freshness | Exec-eligible | Status |
|---|-----|--------------|-----------------|---------------|--------|-----------|---------------|--------|
| 1 | Mission Control | world-state strip (structural/tactical/next/alternate quad, transition, carry, shock, posture, crash) | gip_engine, regime_transition_engine, fx_carry_engine, compute | prices + FRED | state labels | cache/live | no | LIVE |
| 1 | Mission Control | tiles + meters (Macro, Crash, Liquidity, Rotation, Conviction, Wealth, Bubble, Credit, Trend, Entry) | brief_export._meters ← meters, gcfis.crash_bottom, compute | prices, FRED, feeds | 0-100 gauges | cache/live | no | LIVE (price-proxy meters = MAPPED/RESEARCH_ONLY) |
| 1 | Mission Control | Today's Attention | warroom.attention | all outputs | ranked 6 items | cache/live | no | LIVE |
| 1 | Mission Control | recommendations (BUY/REDUCE/WAIT) | compute._rank + market_cap_target decision pkg | prices | conviction cards | cache/live | no (shadow) | LIVE, RESEARCH_ONLY |
| 1 | Mission Control | evidence ledger | _confidence_panel | certify registries | proof labels | static | no | LIVE |
| 2 | Morning Brief | briefing text + moves | render.morning_brief | compute outputs | narrative | cache/live | no | LIVE |
| 3 | Briefing | briefing embed | render.briefing_embed | brief_export | html brief | cache/live | no | LIVE |
| 4 | Command Center | quad + transition + rotation + meters | regime, regime_transition, cycle_rotation, meters | prices + FRED | panels | cache/live | no | LIVE |
| 5 | Alpha Center | Tradable Now / conviction vs watchlist / excluded-with-reason | compute._rank, alpha_scanner, market_cap_target | prices | ticker rows + reason | cache/live | no | LIVE — WATCH labelled non-alpha, gated candidates show MODEL_REQUIRED reason |
| 5 | Alpha Center | methodology/batch_a panels | reflexivity, boombust, keith, coatue, narrative, scenarios, transmission, cascade, seasonality, cri, frontrun | prices + FRED | per-engine outputs | cache/live | no | LIVE, RESEARCH_ONLY |
| 6 | Cross-Asset Rotation | rotation + country regime | rotation_engine, cycle_rotation, country_regime | prices | maps | cache/live | no | LIVE |
| 7 | Causal Chains | chain reaction DAGs + hub | causal_chain, theme_graph, data/chain_reactions.json | prices + curated links | chain list | cache/live | no | LIVE |
| 8 | US Stocks | state + leaders + ticker selector + fair value + gex lens | compute, fair_value_cards, greeks_proxy, spotgamma (feeds) | prices, feeds | panels + ticker packet | cache/live | no | LIVE (gex via feeds or NO_DATA) |
| 9 | Crypto | state + onchain (feeds) | compute, feeds.onchain | prices, feeds | panels | cache/live | no | LIVE |
| 10 | Commodities | state + COT (feeds) | compute, feeds.cot | prices, feeds | panels | cache/live | no | LIVE |
| 11 | FX | carry + pairs | fx_carry_engine / feeds.fx_carry | FRED, prices | carry stage/pairs | cache/live | no | LIVE |
| 12 | IHSG | state + typef lens (feeds) | compute, feeds.typef | prices, feeds | panels | cache/live | no | LIVE |
| 13 | Flow | flow + positioning | flow.py, gcfis flows | prices | panels | cache/live | no | LIVE |
| 14 | Bottleneck | bottleneck map + node template | bottleneck.py, data/company_intelligence.json | curated data | map + nodes | static curated | no | LIVE |
| 15 | Market State | macro/regime dashboard + coherence | _macro_dashboard, drivers | prices + FRED | panels | cache/live | no | LIVE |
| 16 | Track Record | open/closed shadow trades | warroom.tracker | shadow log | P&L | runtime log | no | LIVE (shadow only) |
| 16 | Track Record | Validation section (R3) | validation_tab ← _confidence_panel | certify registries | proof matrix | static | no | LIVE |
| 17 | Risk & Health | Crash Meter detail (12 subcomponents, drivers, disconfirming, invalidation, action) | warroom.crash_meter (R3) | compute outputs | 0-100 severity + components | cache/live | no | LIVE, RESEARCH_ONLY |
| 17 | Risk & Health | portfolio risk + limits | warroom.risk | conviction + prices | exposure/VaR/breaches | cache/live | no | LIVE |
| 17 | Risk & Health | system health + feeds + engine errors | diagnostics, feeds_status | runtime | status | runtime | no | LIVE |
| 17 | Risk & Health | Early Warning detail (R3) | early_warning_tab ← fear_greed, panic, crash_lead, valuation_room | prices, FRED | gauges | cache/live | no | LIVE |

## Engine status lists

### Working and wired (verified at boot, real cache, 2026-07-28)
gip_engine (structural+tactical quad), regime_transition_engine, quad_explainer,
crash_bottom (gcfis), crash_lead, early_warning (fear-greed/panic), market health
(breadth/posture/HMM), meters (trend/credit/bubble/wealth/liquidity), funding_stress,
policy, fx_carry_engine, causal_chains, transmission, cascade, seasonality, front_run,
reflexivity, boombust, rotation, cycle_rotation, country_regime, alpha ranking,
watchlist, decision_market, walkforward gate, portfolio risk, attention,
crash_meter (R3), component_registry (R3), optimal_entry, valuation_room, macro_regime,
beta_plays, thesis_beta, theme_graph, market_character, drivers/coherence, mechanical
(month-end/vol-target), crowd_market, change_detect (gcfis).

### RESEARCH_ONLY / unproven (visible, zero capital weight)
crash_meter composite (uncalibrated until R5), price-proxy meters (trend/credit/bubble/
wealth/liquidity thresholds = priors), carry stage mapping, alpha ranking, conviction
scores, all batch_a methodology engines, greed leg of fear-greed (flagged weak).

### Broken / unavailable / degraded
- leverage subcomponent (crash meter): NO_DATA — margin-debt feed not wired
- physical subcomponent (crash meter): NO_DATA — inventory/supply feed not wired
- crash-meter per-horizon splits: placeholder pending calibrated history (R5 gate)
- greeks_proxy: proxy only without options-chain feed; gex/finra/typef/onchain/cot
  need build_feeds.py live run (not executed in R3; panels show honest unavailable)
- options/GEX/Greeks: rendered only where data exists, per scope rule

### Duplicated (one source of truth declared; donor not rewired)
- fx carry: engines/fx_carry_engine is source of truth; v101 carry module remains donor (R4 unification to §7 contract)
- crash pressure: gcfis.crash_bottom (tile) + warroom.crash_meter (detail) — different
  objects (bottom-pressure vs severity gauge); both registered, no conflict
- decision_market schema: producer (market_cap_target, honest None-schema) vs consumer
  fixed in R2; registry documents canonical fields

### Disconnected (restored in R1, not yet surfaced)
- hedgeye_position_sizing (partially via _hedgeye sizing in conviction rows)
- greeks per-ticker drawer exists in US tab; options chain feed absent
- research bundles (v53-v101) readable via bundled reader; not all panels rewired

Software/test PASS is not alpha proof. No PAPER/LIVE permission opened in R3.
