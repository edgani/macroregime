# Validation Results — v2.6 IHSG Transaction Intelligence

Fresh working-tree validation:

- `python -m py_compile app.py macro_embedded.py decision_core.py data_adapters.py ihsg_transaction.py` — PASS
- All 13 constituent test files in `tests/run_all.py` were executed individually — **13 PASS / 0 NONPASS**
- `tests/test_ihsg_transaction.py` — PASS

Covered suites:
1. self test
2. final contract
3. static contract
4. decision core
5. data adapters
6. IHSG transaction intelligence
7. macro logic
8. macro snapshot
9. replay timestamps
10. negative controls
11. fuzz/property tests
12. walk-forward machinery
13. visual/expression visibility contract

IHSG transaction tests specifically verify:
- missing API keys fail closed and cannot add a bullish evidence vote;
- broker-level concentration and persistence are computed without fabricating a total-market broker net buy;
- negotiated-market/crossing contamination can neutralize a transaction state;
- order-book imbalance and aggressive-flow/price absorption logic are bounded;
- transaction intelligence contributes at most one independent evidence-family vote;
- the transaction score is explicitly a research score, not a calibrated probability.

Important distinction: the walk-forward suite validates chronology/purge/embargo mechanics. It does not convert missing full-universe PIT datasets into proven market alpha. Live provider responses still require configured API keys in the deployment environment.
