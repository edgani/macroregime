# Robustness Audit

Executed safeguards: chronological OOS, non-overlap sampling, block permutation, multi-era sign check, FDR correction, fixed equal-weight mechanism composites, and negative controls. The two negative controls produced **0 false-positive survivors** under the dependence-corrected rule.

Important limitation: the same long-run US market is still the outcome universe. This cannot establish cross-market generalization. Correlated inflation transforms/composites are not counted as independent votes; `10_GMIS_FINAL.csv` is intentionally a small research-only representative set.

No parameter optimizer was used for composite weights; equal weights were fixed to reduce overfitting.
