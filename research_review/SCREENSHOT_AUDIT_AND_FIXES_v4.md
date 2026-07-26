# Screenshot Audit and Fixes — v4

The v3 screenshots were not final-clean. The following defects were confirmed and fixed:

1. `LIVE` mixed data freshness with trading permission. The header now says daily/partial data and `RESEARCH ONLY · PAPER/LIVE BLOCKED`.
2. Yahoo/IDX daily bars were presented as live execution data. Each market now carries its own daily as-of timestamp and source state.
3. Mission Control called RS plus a price/RS setup “cross-confirmation.” This was same-family evidence. Mission now requires an independent selector/fundamental family; same-family overlap is withheld and shown in Flow.
4. The Early Warning tab used the wrong registry key (`early` instead of `ew`) and could render empty while Mission showed stress scores.
5. `shock_prob` is not a calibrated probability. UI now calls it a shock-stress score.
6. The funnel was mathematically inconsistent because invalid fallback rows counted as entry-valid. New funnel: Loaded → History-eligible → Signal-valid → Displayed.
7. The US Stocks tab could surface ETFs/proxies (EWT, XLK, etc.). These are excluded from stock setup output.
8. The IHSG tab could surface `^JKSE` as if it were a stock. Index proxies are excluded.
9. The mixed commodity tab incorrectly used the gold driver model for oil and copper contracts. Drivers are now subtype-aware; unsupported copper/natural-gas models stay NO_DATA.
10. Driver colors used raw z direction rather than causal sign. Rising real yields/DXY can now display as a headwind even when raw z is positive.
11. The UI said “gamma-aware” even when gamma was unknown. That label was removed.
12. Price/RS fallback rows said BUILD_LONG and displayed percentile scores as conviction. They now say WATCH_LONG/WATCH_SHORT and `SETUP_SCORE`.
13. Macro counter-regime conditions are disclosed per setup; low-coverage macro does not silently hard-block.
14. Internal MQA risk-range output was labeled as Hedgeye. It is now explicitly `MQA_RISK_RANGE_PROXY`; no proprietary-exactness claim is made.
15. Dead legacy hard-coded current-value panels were removed from the JavaScript tab specification.
16. Macro and Early Warning now expose the current data-bound snapshot plus the proof registry, instead of Mission showing numbers that cannot be reviewed upstream.

The build remains research/shadow only. Alpha Foundry has not produced a real shortlist yet, and system proven component/selector/alpha counts remain zero.
