# V9.5 proof-firewall repair

The V9.4 package was a useful acquisition bootstrap, but it was not a trading engine. During the V9.5 audit, the following release-critical weaknesses were repaired:

1. The global promotion path still imported the older V8.8 gate and could evaluate raw receipt assertions rather than only a recomputed exact-market V9.5 proof run.
2. A receipt could contain syntactically valid 64-character hashes that were not bound to the runtime files supplied to the proof runner.
3. Signed projection/profit/drawdown numbers were not cross-checked against metrics recomputed from the supplied CSV files.
4. Direct CSV fills were not strongly bound to a recognized broker/exchange source, one account, one strategy and one market.
5. Python truth conversion could misinterpret string booleans such as `"False"`.
6. Future fills, duplicate/colliding order hashes, source mismatch and trade/equity P&L mismatch were not all blocked.
7. The IDX browser importer accepted structurally weak JSON without requiring an official `idx.co.id` source URL.
8. An IDX browser handoff receipt could be counted as if it were a real market-data snapshot.
9. Missing SEC configuration could unnecessarily block unrelated Nasdaq collection.
10. Runtime identity was inconsistent across the Streamlit shell, CLI and dashboard.
11. Legacy validators could overwrite committed validation reports, making package-manifest checks confusing after execution.

V9.5 adds a non-mutating authoritative validator. Historical reports are retained only for audit history.
