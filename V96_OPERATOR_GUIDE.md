# V9.6 Operator Guide

## Required sequence

1. **Mapping:** freeze decision purpose, causal role, source/liquidity, stock-flow-surprise-state, transmission, target/horizon, lineage, interactions, invalidation, and claim limits.
2. **Candidate registration:** register every candidate and parameter neighbourhood before testing. Chart-derived technical predictors are rejected.
3. **Test start:** bind protocol, code, admitted data contract and trial family.
4. **Adjudication:** use `PROVEN`, `RETEST_ALTERNATE`, or `REMOVE`. Failed trials remain in the immutable ledger.
5. **Final metric:** freeze only the preselected validation winner before lockbox.
6. **Historical gate:** run `anti_overfit_gate_v96.py` using real point-in-time candidate returns.
7. **Prospective gate:** record forecasts before maturity and import genuine account closed trades/equity. Paper fills remain separate.
8. **Promotion:** install a V9.6 proof run only through `install_proof_run_v96.py`. Human approval is still required for limited production.

## What must never be done

- Choose a formula after seeing lockbox outcomes.
- Delete losing trials or reset the family count.
- Treat current revised data as historical point-in-time data.
- Backfill a forecast, fake an order ID, or convert public prices into fills.
- Promote a model because one regime, ticker, month, or parameter spike produced most P&L.
- Interpret a validator PASS as strategy profitability.
