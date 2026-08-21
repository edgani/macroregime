# Walk-Forward / OOS Evidence

## Executed in this self-run
- Factual Shiller monthly history and factual VIX CSV from the supplied bundle.
- Future SPX maximum drawdown severity at 6/12/24 month horizons and >=20% crash label.
- Chronological 60/40 split.
- Non-overlapping horizon samples.
- Block permutation to correct dependence.
- Era splits (pre-1946, 1946-1989, 1990-2023) for sign stability.
- Logistic OOS Brier/AUC/PR where outcome classes were present.
- Benjamini-Hochberg FDR on non-overlap tests.
- Two negative controls.

## Result
81 factual US-only specifications were executed (60 univariate + 21 mechanism-bounded equal-weight combinations). 19 survive as `HISTORICALLY_SUPPORTED_US_ONLY` or `CONDITIONAL_US_ONLY`; **0 receive production-proven status**.

## Why not PROVEN_SCOPE_LIMITED
The project requires cross-market/cross-regime replication including US stocks, IHSG, commodities/futures, crypto and FX. Those datasets are not all directly readable/ingested in this runtime. The surviving results are therefore research evidence, not production proof.
