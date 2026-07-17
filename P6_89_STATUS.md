# P6.89 — Monthly Research Panel

Implemented:

- two-day conservative filing availability lag;
- month-end decision timestamps;
- maximum 200-day filing staleness;
- historical membership filtering;
- price, liquidity and fundamental eligibility;
- 20D/63D/126D/252D future labels;
- sector-neutral labels using filing-time SIC groups;
- market baselines and frozen simple-quality baseline.

Missing features remain missing and are imputed inside training folds only for the Ridge model.
