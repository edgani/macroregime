# Video-to-War-Room Implementation Matrix

| Video concept | War Room treatment | Executable state | Claim ceiling |
|---|---|---:|---|
| Delta changes as spot moves | Exact-contract Greeks and delta-hedging simulator | Implemented | Mechanics only |
| Gamma requires repeated re-hedging | Path-dependent hedge simulator with explicit rebalance policy | Implemented | No guaranteed profit |
| Realized volatility versus implied volatility | IV/RV variance-gap diagnostic | Implemented | Hypothesis; costs and path required |
| Long gamma can buy low/sell high through hedging | Net delta-hedged P&L research claim V71_C3 | Frozen prospective test | Not proven |
| Market-maker hedging can damp or amplify | Verified signed-inventory mechanical-flow regime | Implemented fail-closed | Sign unknown without provenance |
| Dealer long/short gamma | Requires audited participant/open-close or signed inventory source | Implemented gate | Public OI forbidden as sign |
| Gamma/call/put walls | OI/Greek concentration reference zones | Implemented | Not targets/support/resistance |
| Gamma flip | Provider-model claim only unless exact method and inventory evidence are admissible | Quarantined | No direction or permission |
| Market makers earn bid/ask spread | Included only in cost/inventory framing | Research context | Not a complete P&L model |
| Option pricing equals gamma scalping | Rejected | Not implemented | Pricing and hedging are separate |
| Apply options signal to every market | Rejected | Market-specific contracts | IHSG direct options disabled |

## Frozen prospective claims

1. Verified long/short gamma inventory versus post-shock reversion/amplification.
2. Liquidity-normalized verified hedge impact versus pin/break and first-passage calibration.
3. Net cost-aware delta-hedged option P&L versus no-trade and buy-and-hold baselines.

All three remain at zero live weight until signed forward outcomes mature and pass frozen chronological, multiplicity, calibration and cost gates.
