# Known limitations — v2.3

These are deliberate gates, not hidden assumptions.

1. **Real full-universe PIT/OOS alpha is not claimed.** The bundled walk-forward test is a mechanical leakage/purge/embargo test on synthetic data.
2. **Default mapped universe is 64 seed assets.** SEC and IDX discovery/PIT adapters are included, but a survivorship-safe normalized full-history universe is not bundled.
3. **FX leverage remains gated** until historical/current relative macro, REER, balance-of-payments, positioning and policy/intervention inputs are complete.
4. **Commodity leverage remains gated** until physical inventory, production/consumption, curve/carry and spare-capacity inputs are complete.
5. **Crypto leverage is conditional** on usage, holder capture, dilution/unlocks and leverage-market data; these are not universal for every token.
6. **Crypto options are intentionally limited to BTC/ETH adapter eligibility.** No fake option surface is created for illiquid tokens.
7. **Historical option OOS is not bundled.** Live option adapters can check IV/spread/OI, but a complete historical IV/skew/term-structure database is not included.
8. **Macro numerical crash/scenario probabilities remain gated.** Macro states and scenario evidence are descriptive/conditional until full vintage calibration is complete.
9. **Earliest execution helper handles weekends but not exchange holidays.** A formal PIT backtest should use an exchange calendar.
10. **Live Streamlit/network runtime depends on public providers.** The code fails closed when critical feeds are unavailable.

## v2.4 presentation note
FX, commodity and crypto rows are deliberately visible even when their capital gate is closed. `WAIT/GATED` is a visibility state, not a recommendation. This fixes v2.3's confusing disappearing-market behavior without weakening the fail-closed model.
