# Cross-tab and hard-code audit — v2

## Confirmed defects in v1

1. Mission Control displayed raw relative-strength rotation across the loaded universe, while Alpha and market tabs used separate gates.
2. UI keys `ihsg`/`commod` did not match backend keys `idx`/`commodity`, allowing legacy mock cards to remain visible.
3. Current Alpha cards came from a curated moonshot prior with feed-neutral defaults, not the frozen selector.
4. `run.py` recomputed entry/stop/target with close-only data instead of preserving the orchestrator's OHLC risk-range output.
5. `extended_universe.json` names were automatically added to the production scan universe.
6. Legacy HTML contained mock/current-looking tickers and numeric levels.

## v2 rules

- Mission Control names only cross-confirmed tickers already surfaced by Alpha, a market setup, or the Foundry shortlist.
- Raw rotation stays in Flow & Rotation and is labelled an RS proxy, not capital flow.
- Alpha emits only the frozen Foundry shortlist. Curated structural maps remain research references, not candidates.
- IHSG and Commodities use canonical UI keys and can no longer fall through to stale mock setups.
- Tactical entry/stop/target retain the orchestrator's true-OHLC risk-range values. ATR fallback is explicitly labelled.
- Structural targets are separate scenario fields and are never substituted for tactical targets.
- Discovered names require explicit opt-in and never auto-enter the live universe.
- Synthetic outputs are blocked from the app.
- Consistency failures remove all decision-bearing outputs.
