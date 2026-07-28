# Preservation Matrix — Original 17-Tab War Room

R4 update (2026-07-28): consolidated to the final 11-tab design. Every original
render function is still invoked exactly once — parity enforced by
tests/test_r4_consolidation.py (source-level exact-call check + boot markers +
screenshots before/after). Final locations in the rightmost column.

| # | Original tab | Render fn | Final tab (R4) | Parity status |
|---|--------------|-----------|----------------|---------------|
| 1 | Mission Control | mission_control | Mission Control (section 1) | PRESERVED |
| 2 | Morning Brief | morning_brief | Mission Control (section 2) | PRESERVED |
| 3 | Briefing | briefing_embed | Mission Control (section 4) | PRESERVED |
| 4 | Command Center | command_center | Mission Control (section 3) | PRESERVED |
| 5 | Alpha Center | alpha | Alpha Center | PRESERVED (unchanged) |
| 6 | Cross-Asset Rotation | cycle_rotation | Rotation & Chains (section 1) | PRESERVED |
| 7 | Causal Chains | causal_chains | Rotation & Chains (section 2) | PRESERVED |
| 8 | US Stocks | us_stocks + fair_value_cards | US Stocks | PRESERVED (unchanged) |
| 9 | Crypto | crypto | Crypto | PRESERVED (unchanged) |
| 10 | Commodities | commodities | Commodities | PRESERVED (unchanged) |
| 11 | FX | fx | FX | PRESERVED (unchanged) |
| 12 | IHSG | ihsg | IHSG | PRESERVED (unchanged) |
| 13 | Flow | flow | Flow & Bottleneck (section 1) | PRESERVED |
| 14 | Bottleneck | bottleneck + node_template | Flow & Bottleneck (section 2) | PRESERVED |
| 15 | Market State | market_state | Macro & Regime | PRESERVED |
| 16 | Track Record | track_record + validation_tab | Portfolio & Proof (sections 1-2) | PRESERVED |
| 17 | Risk & Health | risk_health + early_warning_tab | Portfolio & Proof (sections 3-4) | PRESERVED |

No render function deleted, renamed, or rewritten. No formula touched in R4.
Screenshots: pre-merge set at docs/audit/screenshots_r2_17tab/, post-merge set at
docs/audit/screenshots/ (11 tabs).

Source of truth: commit d3bee91 (last complete original), warroom/render.py at HEAD
(superset — includes additional views), ZIP warroom_os_COMPLETE (6).zip as secondary
reference (14-tab HTML lineage).

Rule (user directive): no tab is merged or removed until a functional-parity test and
screenshot comparison prove every function and output survives at its target location.

| # | Original tab | Function | Render fn (warroom/render.py) | Engines (warroom/compute.py + engines/) | Datasets | Outputs | Target location (11-tab plan, NOT yet executed) | Parity test (planned) |
|---|---|---|---|---|---|---|---|---|
| 1 | Mission Control | "You are here" state, what changed, regime drivers, quad, country grid, rotation, theme graph, narratives, causal chain, coherence, policy, crowd | mission_control, _whatchanged, _macro_dashboard, country_grid, _rotation_panel, _theme_graph_panel, _policy_panel, _coherence_panel | GIP engine, regime_transition_engine, quad_explainer, meters, macro_regime, country_regime, cycle_rotation, themes, policy, funding_stress | prices (5 universes), FRED, feeds | regime/quad state, meters, rotation, narratives, chain, what-changed diff | Tab 1 Mission Control (extended with crash/carry/countdown) | boot + panel-presence + screenshot diff |
| 2 | Morning Brief | Daily plain-language brief of state and actions | morning_brief | synthesis, decision_center | computed desk | brief text | merge into Tab 1 (mission control section) | text-section presence |
| 3 | Briefing | Embedded interactive briefing deck | briefing_embed | brief_export (briefing.html) | briefing_template.html | briefing deck iframe | Data/Research drawer or Mission Control export | artifact-exists test |
| 4 | Command Center | Full desk command view (data source, feeds status, conviction cards) | command_center | all compute outputs + feeds | prices, feeds, FRED | desk overview, cards | Tab 1 Mission Control | boot + screenshot |
| 5 | Alpha Center | Cross-market conviction ranking, funnel (scanned/ranked/conviction/watchlist), walk-forward gate | alpha, _xcard, decision_market_panel | alpha ranking (_rank), _setups, walkforward validation, decision_engine | prices, regime | conviction cards, watchlist, WF gate | Tab 4 Alpha Center (funnel restructure R4) | funnel-presence + card schema |
| 6 | Cross-Asset Rotation | Cycle/rotation axes and cross-asset signals | cycle_rotation | cycle_rotation, macro_regime, _xasset | prices cross-asset | rotation axes, cross-asset snapshot | Tab 2 Macro & Regime (or Tab 1 panel) | panel-presence |
| 7 | Causal Chains | Causal chain view (trigger→transmission→beneficiary) | causal_chains, _causal5 | causal_chain, chain_reaction_engine (data/chain_reactions.json) | chain_reactions.json, prices | chain cards per theme | Ticker packet drawer + cross-market panel | chain-card schema |
| 8 | US Stocks | US lens rows (themes, beta plays, fair value) | us_stocks, fair_value_cards, _lens_rows | fair_value, beta_play, methodology engines | prices US, fair value data | lens tables, FV cards | Tab 5 US Stocks | lens-row count > 0 or honest empty |
| 9 | Crypto | Crypto lens | crypto | onchain_engine, market modules | prices crypto | crypto lens rows | Tab 7 Crypto | lens presence |
| 10 | Commodities | Commodities lens | commodities | commodity drivers, fx_commodity_driver_engine | prices commo | commo lens rows | Tab 8 Commodities | lens presence |
| 11 | FX | FX lens | fx | fx_carry_engine, fx drivers | prices FX | FX lens rows | Tab 9 FX | lens presence |
| 12 | IHSG | IDX lens (conglomerate awareness) | ihsg | ihsg_specialist_v38, bandarmetrics_engine | prices IDX, ihsg_conglomerates.json | IDX lens rows | Tab 6 IHSG | lens presence |
| 13 | Flow | Flow lens (flows/positioning) | flow | real_flow_engine, mechanical_flow_driver | feeds, prices | flow rows | Ticker packet drawer + market tabs | row presence |
| 14 | Bottleneck | Bottleneck map + node template | bottleneck, node_template, _load_bottleneck | bottleneck_engine, bottleneck_discovery_v3, supply_chain_graph_real | bottleneck_reference.json | bottleneck cards, node detail | Ticker packet + Macro bottleneck map | card schema |
| 15 | Market State | Market structure state panel | market_state | structure_quality, regime engines | prices | structure/state panel | Tab 2 Macro & Regime | panel presence |
| 16 | Track Record | Forward-test performance, open/closed signals | track_record | tracker (log_signals/update_outcomes) | tracker log | performance table, open/closed | Tab 10 Portfolio & Execution | artifact + table presence |
| 17 | Risk & Health | Risk meters and health view | risk_health | meters, crash_bottom (gcfis), funding_stress | prices, FRED | risk meters, health panel | Tab 3 Early Warning & Crash | meter presence |

## Extra views present at HEAD warroom/render.py (not in the 17-tab app — candidates for wiring in R3+)

early_warning_tab, validation_tab, knowledge_graph_view, decision_journal_tab,
theme_library, catalyst_timeline, decision_board, investment_memo_view,
thesis_playbook_view, internals_view, cross_asset_macro, optimal_entry,
confidence_panel (_confidence_panel), knowledge_cards.

These map to master-prompt tabs: Early Warning (3), Validation (11), Knowledge
Graph (evidence provider), Portfolio/Execution (10). Wiring decision deferred to R3
with parity evidence.

## ZIP (14-tab HTML lineage) cross-check

ZIP tabs: Mission Control, Macro & Regime, Early Warning, Alpha, US Stocks, IHSG,
Crypto, Commodities, FX, Flow & Rotation, Supply Chain, Company Intel, Knowledge
Graph, Validation. All 14 are covered by the 17-tab set + HEAD extra views above
(Supply Chain ≈ Bottleneck/Supply-chain graph; Company Intel ≈ knowledge/company
lenses; Knowledge Graph ≈ knowledge_graph_view; Validation ≈ validation_tab).
No ZIP-only feature is orphaned: dashboard.html lineage preserved as
app_v101.py + static/dashboard_live.html donor.

## Datasets inventory (bundled, tracked)

data/extended_universe.json, data/ihsg_conglomerates.json, data/bottleneck_reference.json,
data/chain_reactions.json, data/current_developments.json, data/source_watchlist.json,
data/snapshot.json, data/state_history.json; research_v53-v101 bundles; FRED loader;
cache/prices.parquet + cache/lineage.json (built by build_cache.py).

## Parity-test plan (gate for any future tab merge)

1. Boot test: 17 tabs render with no exception (DONE offline — AppTest, 17 tabs).
2. Panel-presence test per tab: key HTML markers from each render fn present in output.
3. Screenshot comparison per tab (baseline vs post-merge) — requires live browser
   (playwright); deferred until R3 wiring is stable.
4. Engine-output schema test: compute() keys required by each tab present.
