# Known limitations — v2.5

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

## v2.5 presentation note
FX, commodity and crypto rows remain visible even when their capital gate is closed. `WAIT/GATED` is a visibility state, not a recommendation. v2.5 additionally removes the abstract scatter/heatmap from the default daily screen; advanced model visuals remain available only when the user opens the advanced section.


## v2.6 IHSG transaction layer

- Broker code is **not** treated as a beneficial owner. One broker can represent many clients and desks.
- Negotiated-market activity is discounted as transfer/crossing contamination; it is not assumed to be directional accumulation.
- Order-book depth is visible liquidity and can be cancelled, so it receives low model weight.
- Intraday absorption requires aggressive-flow fields plus price response. If HAKA/HAKI-like fields are absent, the engine reports `GATED` rather than inferring absorption from a static order-book wall.
- Queue tracking is available at the adapter level but is not used by the broad scanner until a stable queue response contract is validated.
- Index Alpha history begins 2025-01-01 on standard coverage, so long-cycle walk-forward validation requires additional licensed/historical data.
- The transaction score is not a win probability and has not yet passed full point-in-time out-of-sample calibration.
