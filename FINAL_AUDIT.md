# Final Audit — v2.6 IHSG Transaction Intelligence

## PASS
- Python compile / AST contract
- Decision / entry / expression core tests
- Macro fail-closed logic and macro snapshot integration
- Replay publication-time guards
- Negative controls and fuzz/property tests
- Synthetic purged/embargo walk-forward machinery
- Plain-language daily board functions present
- IHSG remains cash-only
- IHSG transaction layer integrated into the existing evidence engine
- Index Alpha adapter: daily broker attribution, RG/NG, foreign flow
- Invezgo adapter: intraday summary and order-book depth
- Missing transaction APIs fail closed
- Broker-code identity is not treated as beneficial ownership
- Total broker net is not used as a directional signal because market-wide broker net is an accounting zero
- Transaction feature family is capped at one support/deterioration vote
- Negotiated-market contamination is discounted rather than interpreted as directional accumulation
- HAKA/HAKI-style absorption is only computed if those fields actually exist in provider payloads
- Queue endpoint is wired at adapter level but excluded from broad scoring until its response contract is explicitly validated
- Streamlit secrets/environment configuration documented
- Full table, readiness gates and evidence chart remain collapsed under Advanced
- Deep thesis/valuation/causal-chain prose remains collapsed

## INTENTIONAL GATES
- `transaction_score` is a research-state score, not a calibrated probability.
- Live Index Alpha/Invezgo calls require the user's API keys and provider subscription/quotas.
- Full PIT/OOS transaction-alpha validation remains required before production-alpha claims.
- The broad scanner does not infer hidden beneficial owner identity from broker codes.
