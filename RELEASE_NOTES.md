# v3.2.1 — Interactive UI / Navigation Hotfix

This hotfix fixes the UI defect in the first v3.2 handoff: the workspace navigation looked like top tabs but was implemented as a `st.radio` after the expensive scanner path. On rerun, a stale scan could execute before the page change visibly completed, making the navigation appear dead.

## Fixed
- Replaced the top workspace `st.radio` pseudo-navigation with six native Streamlit buttons and persistent `session_state` routing.
- Renders navigation before expensive scanning.
- Page-switch callback skips one stale auto-refresh so navigation remains responsive; the scheduled refresh resumes afterward.
- Active workspace is visually distinct and state persists across reruns.
- Rebuilt CONTROL ROOM into a dense dark-cyan three-column operator dashboard: vertical readiness, selected opportunity + causal transmission, macro/risk + recent alerts, and a full-width cross-market radar.
- Removed decorative non-interactive Opportunity Tracker pseudo-tabs so nothing that looks like a tab is intentionally fake.
- Added `test_v321_ui_navigation.py` covering native routing, ordering before scan, scan-skip-on-navigation, all six routes and the dense control-room contract.

## Validation
- **19 PASS / 0 NONPASS / 19 TOTAL** automated package tests.
- Existing **20/20 v3.2 structural acceptance checks** remain green.
- A real Streamlit browser-smoke test is still environment-dependent and is not falsely claimed in the build environment where Streamlit is unavailable.

---

# Market Opportunity OS v3.2 — Longitudinal Discovery + Outcome Learning

Base: **v3.1 Story / Expectation Optionality**. This is an additive upgrade; the existing Macro Decision Engine, IHSG transaction intelligence, story/expectation optionality, causal graph, valuation logic and fail-closed decision gates remain intact.

## Added
- Immutable `OPPORTUNITY_EVENT` memory in `state/opportunity_memory.sqlite`.
- Automatic discovery from the existing cross-market scan; no ticker-by-ticker input required for the loaded universe.
- Explicit causal event fields: driver → first order → second order → bottleneck → beneficiary → revenue/margin capture → catalyst → invalidation.
- Multi-archetype classification and component scores instead of one opaque score.
- First-seen / first-unusual / first-high-conviction timestamps and prices.
- Persistent lifecycle states: DISCOVERED → EMERGING → PROVING → HIGH_CONVICTION → PRICING_IN → MATURE → CROWDED / INVALIDATED / RESOLVED.
- Forward outcome schema for 1D, 3D, 1W, 2W, 1M, 3M, 6M and 12M.
- Absolute return, benchmark alpha, sector alpha, MFE, MAE, time-to-MFE, time-to-MAE, peak return and max drawdown.
- Bounded cached outcome maturation using yfinance where a real symbol + benchmark are available.
- Explicit false-positive taxonomy and missed-runner audit store.
- Regime/market/sector/theme historical expectancy with sample-size confidence.
- Expanding chronological walk-forward calibration; no random shuffle.
- Baseline comparison surface that stays DATA GATED when PIT baseline features do not exist.
- Automatic daily / weekly learning reports under `state/learning_reports/`.
- HK / China / Europe / Taiwan equity architecture support when symbols/data are supplied.
- New dense dark-cyan Opportunity Tracker UI inspired by the supplied dashboard reference.
- Original v3.1 decision desk preserved as `DECISION DESK`.

## Guardrails
- No autotrading, broker credentials, private keys, leverage execution or automatic orders.
- No RSI / MACD / stochastic / generic MA-cross primary opportunity logic.
- Production weights do not self-modify from recent outcomes.
- First-detection snapshots are immutable; future data only enters outcome/lifecycle tables.
- No fake historical performance. Fresh installs correctly show insufficient-sample / no-mature-outcome states.
- Narrative exposure alone cannot create a longitudinal opportunity event.

## Validation
Run:

```bash
python tests/run_all.py
```

Current package result: **18 PASS / 0 NONPASS** plus **20/20 v3.2 structural acceptance checks**.
