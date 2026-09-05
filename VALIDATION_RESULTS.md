# Validation Results — v3.0 Market Opportunity OS

Fresh working-tree validation:

- `python -m py_compile app.py macro_embedded.py decision_core.py data_adapters.py ihsg_transaction.py opportunity_kernel.py market_memory.py defillama_adapter.py verticals.py` — **PASS**
- `python tests/run_all.py` — **15 PASS / 0 NONPASS**

Covered suites:

1. self test
2. final contract
3. static contract
4. decision core
5. data adapters
6. IHSG transaction intelligence
7. universal opportunity kernel + Market Memory
8. DeFiLlama adapter contract
9. macro logic
10. macro snapshot
11. replay timestamps
12. negative controls
13. fuzz/property tests
14. walk-forward machinery
15. visual/expression visibility contract

New v3 checks verify:

- robust change logic uses only prior observations as baseline;
- state sequences preserve order;
- Market Memory is timestamped and append-only for observations;
- vertical readiness fails closed when required causal families are absent;
- DeFiLlama chain snapshot keeps TVL/stablecoins/activity/economics as separate evidence;
- missing external data does not silently create bullish evidence.

Important distinction: chronology/purge/embargo and memory mechanics are validated, but a broad historical PIT dataset is still required before predictive-alpha claims can be made.
