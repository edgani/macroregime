# Validation Results — v2.5 Simple Decision Board

Fresh working-tree run:

- `python -m py_compile app.py` — PASS
- `python tests/run_all.py` — **12 PASS / 0 NONPASS / 12 TOTAL**

Covered suites:
1. self test
2. final contract
3. static contract
4. decision core
5. data adapters
6. macro logic
7. macro snapshot
8. replay timestamps
9. negative controls
10. fuzz/property tests
11. walk-forward machinery
12. visual/expression visibility contract

The visual contract now checks the simple daily hierarchy: At a glance → Top opportunities now → How it can be traded → advanced detail collapsed.

Important distinction: the walk-forward suite validates chronology/purge/embargo mechanics. It does not convert missing full-universe PIT datasets into proven market alpha.
