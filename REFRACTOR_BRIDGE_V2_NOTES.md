# Refactor Bridge V2 Notes

This build advances the bridge with actual UI/action changes:
- Dashboard ticker attack matrix now derives from market action payloads, not only master opportunity rows.
- Added `ui/components/market_action_tables.py`
- Market pages now render ticker-first action sections:
  - US / FX / Commodities / Crypto:
    - Best Longs Now
    - Best Shorts Now
    - Front-Run Longs
    - Front-Run Shorts
    - Avoid / Reduce
  - IHSG:
    - Buy Now
    - Front-Run Buy
    - Avoid / Reduce
    - Defensive Shelter / Cash
- Market page wrappers now pass full snapshot so action payloads can fallback to master opportunities.
- Uses bucket-based ticker fallbacks when top rows are empty, so pages stay tickerized.

This is still a bridge build:
- it keeps legacy engines and snapshot build
- it does not yet implement a formal new Scenario Stack + Market Mixer engine
- it reshapes the surface/action layer around current repo output