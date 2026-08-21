# Expected Value Validation

**Current result: NO QUALIFIED OPPORTUNITY.**

No EV number is produced because scenario probabilities and ticker/company PIT transmission are not calibrated. Producing `P_WIN`, expected win/loss or `EV_NET` would be fabricated. The production path therefore fails closed. Once a thesis qualifies, the required formula is:

`EV_NET = P_WIN*E[WIN] + (1-P_WIN)*E[LOSS] - costs - spread - slippage - funding - borrow - tax - FX - liquidity impact`.

A conservative EV must also penalize tail and model uncertainty.
