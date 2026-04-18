# MacroRegime Pro – Scenario/Transmission Refactor Patch

## What changed
- Replaced stale/hardcoded event worldview with generic rolling event templates plus dynamic scenario-linked event surrogates.
- Added `SCENARIO_FAMILY_LIBRARY` and `TRANSMISSION_LIBRARY` in `app.py`.
- Added `detect_scenario_families()` to separate front-run scenario pressure from the quad core.
- Rebuilt `build_scenarios()` into a family-based scenario graph with:
  - base / alt context
  - family probabilities
  - child branches
  - triggers / confirms / invalidators
  - evidence snippets
- Rebuilt `build_news_catalyst_overlay()` into an adaptive catalyst mapper:
  - still honest that it is not a literal live news feed
  - now links catalyst pressure to scenario families
  - builds dynamic event surrogates
- Added `build_transmission_graph()` so one shock can propagate into:
  - US
  - IHSG
  - FX
  - Commodities
  - Crypto
- Added dashboard/playbook rendering for:
  - active scenario graph
  - transmission graph

## Main design goal
Keep:
- Quad core = truth layer
Add:
- Signal / scenario / transmission / catalyst layer = forward-looking layer

This is meant to reduce narrative contamination and make:
- war -> oil -> tanker -> dollar -> EM pain
- de-escalation -> oil down -> USD down -> EM / breadth relief
- policy relief
- dollar squeeze
- China/global re-acceleration
more explicit and decision-useful.

## What is improved vs prior build
- Less stale April/May/June 2026 hardcoding
- More generic and adaptive scenario families
- More explicit child-branch logic
- Better cross-asset spillover visibility
- Better separation between quad parity objective and front-run objective

## Remaining limits
- Still not a true live semantic news ingestion engine
- Still not point-in-time vintage-safe vs Hedgeye historical calls
- Structural quad can still be contaminated by fallback proxies when observed macro coverage is weak
- Hedgeye parity is improved conceptually, not fully proven date-by-date in this patch alone

## Verification
- `python -m py_compile app.py` ✅
- `MRP_LIVE_FETCH=0 python scripts/run_smoke_checks.py` ✅
