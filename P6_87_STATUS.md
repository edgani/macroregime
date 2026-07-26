# P6.87 — Historical Entity and Universe Resolver

Implemented:

- historical S&P 500 start/end membership intervals;
- delisted symbols retained where prices exist;
- SEC filing-time instance ticker extraction;
- active-membership validation at filing date;
- current SEC CIK mapping only as a constrained fallback;
- no fuzzy name joins;
- ambiguous/unmatched filings quarantined.

This directly addresses the most dangerous free-data blocker: silent wrong-company joins.
