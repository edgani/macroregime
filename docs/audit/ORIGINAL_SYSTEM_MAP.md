# Original System Map & Recovery Plan — War Room OS rebuild (2026-07-28)

## Diagnosis (verified from git history, not assumed)

The user's judgment is correct: V10.1/V10.2 oversimplified War Room into
"refresh data → WATCH list → proof gated". The original system was gutted by the
user's own commit **943bdee (2026-07-11, message "1")**, which deleted 81 of 104
engine files and replaced the 17-tab app. The audit cleanup (a60f413) deleted only
bytecode/caches/generated junk — zero source files.

### Recovery source

Commit `d3bee91` (parent of 943bdee) = last complete War Room:
- `app.py`: 17 tabs — Mission Control, Morning Brief, Briefing, Command Center,
  Alpha Center, Cross-Asset Rotation, Causal Chains, US Stocks, Crypto, Commodities,
  FX, IHSG, Flow, Bottleneck, Market State, Track Record, Risk & Health
- `engines/`: 104 files (GIP quad, regime transition, quad explainer, chain reaction,
  market health, cascade, transmission, reflexivity, hedgeye sizing, alpha
  scanner/gatekeeper/curator, walkforward, gex/greeks, frontrun, seasonality, …)
- `warroom/`: compute.py (orchestrator), render.py (Streamlit UI), data.py (5 market
  universes: US, IDX, crypto, FX, commodities), early_warning, meters, macro_regime,
  crash_lead, tracker (forward-test log), statelog (what-changed), brief_export
- `build_cache.py` / `build_feeds.py`: data pipeline (yfinance + FRED + feeds)

### What survived at HEAD (before restoration)

- `warroom/` — 52 modules (superset of d3bee91's 41; compute.py references the full
  engine set via fail-soft `_try()` wrappers)
- `gcfis/` — complete (own test suite: ALL TESTS PASSED)
- `engines/` — only 23 of 104 files
- V10.1 infrastructure worth keeping: proof gates, signed receipts, shadow ledger,
  data lineage flags, carry engine v101, v3 kernel (src/warroom_v3)

## Restoration executed (this commit)

- 81 engine files restored from d3bee91 into `engines/` (HEAD versions of the 23
  survivors untouched).
- `build_cache.py`, `build_feeds.py`, `run_validation.py`, `briefing_template.html`
  restored to root.
- Import health: 33/33 engine modules referenced by warroom/compute.py import cleanly.
- Regression: pytest 134/134 PASS, gcfis ALL TESTS PASSED.

## Gap analysis vs master-prompt target (11 tabs)

| Target tab | Original source | Status after restoration |
|---|---|---|
| 1 Mission Control | R.mission_control (17-tab app) | engine+render exist; needs re-wire into new app |
| 2 Macro, Liquidity & Regime | GIP + quad_explainer + regime_transition + treasury_liquidity | engines restored; needs wiring |
| 3 Early Warning & Crash | warroom/early_warning + crash_lead + gcfis shock/fragility/crash_bottom | exists; needs Crash Meter panel assembly |
| 4 Alpha Center | R.alpha + alpha_scanner/gatekeeper/curator + warroom ranking | exists; needs funnel restructure per contract |
| 5-9 Market tabs (US/IHSG/Crypto/Commodities/FX) | R.us_stocks/ihsg/crypto/commodities/fx | render exists; needs market-specific data wiring |
| 10 Portfolio & Execution | engines/portfolio_sizing + conviction_sizing + shadow ledger v95/v101 | partial; needs unified execution tab |
| 11 Data Integrity & Research Lab | docs/audit + proof registry + validation_engine | mostly exists; needs UI assembly |

### Known conflicts to resolve during rebuild

1. `warroom/data.py::_synth` synthetic price fallback — VIOLATES master prompt §9
   ("never replace failed live data with synthetic"). Must be removed; failed loads
   must surface NO_DATA/STALE states instead.
2. Original 17-tab structure vs 11-tab target — merge mapping required
   (Morning Brief/Briefing/Command Center → Mission Control; Flow/Bottleneck →
   ticker-bound drawers; Market State → Macro tab; Track Record → Portfolio;
   Risk & Health → Early Warning).
3. gcfis Hedgeye-style risk_range vs "no static Quad doctrine" — keep as base-rate
   context only, never as asset mapping.
4. V10.1 carry engine (current-context) vs engines/fx_carry_engine — reconcile to
   one canonical carry engine per §7 output contract.
5. Crash Meter: prior cusp-fragility predictive variant is REJECTED (V73-V75). The
   Crash Meter must be rebuilt as a severity gauge from the §3 subcomponents
   (liquidity/credit/funding/leverage/crowding/vol/cross-asset/macro/policy/
   physical/carry-unwind/market-response), labeled decision-severity, not probability,
   until calibrated.

## Rebuild phases

- R1 (this commit): restoration + map. DONE.
- R2: data pipeline — offline-capable cache build, no synthetic fallback, data states
  (CURRENT/STALE_LAST_KNOWN/HISTORICAL_REFERENCE/PARTIAL/NO_DATA/ERROR).
- R3: new 11-tab app.py wiring warroom/render + engines + gcfis + v101 proof layer.
- R4: component assembly — Crash Meter, Quad state/transition, carry map, chain
  reaction, alpha funnel, unified ticker packet.
- R5: validation/promotion integration (existing proof gates + shadow ledger +
  walkforward engines), promotion states per §12.
- R6: acceptance per §16 + tests + delivery.
