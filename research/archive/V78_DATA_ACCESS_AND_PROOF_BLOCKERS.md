# V7.8 Data Access and Proof Blockers

## Available now

- A community-maintained MIT-licensed S&P 500 membership interval file is bundled as a survivorship-bias **guard**. It has 1,259 intervals across 1,206 ticker symbols and passes hash/header/date/overlap checks.
- Existing bundled research panels remain usable for reproducing earlier diagnostics, but they do not cover the independent current stock-level lockbox needed for promotion.
- The V7.8 point-in-time contract and validator are executable now.

## Not available in a proof-sufficient form

- Survivor-bias-free daily prices including delisted and renamed securities.
- Permanent security identifiers and complete corporate actions.
- Point-in-time US option surfaces through the modern lockbox.
- Point-in-time analyst estimates and revision histories.
- Borrow availability, fee and recall history for the short leg.
- Provider-specific spreads, depth, impact and data costs.

## Why the current free-data routes were not silently substituted

- Current Stooq bulk/CSV access requires interactive/API-key handling and cannot be assumed to be a stable unauthenticated research source.
- Yahoo chart requests were rate-limited during acquisition and, more importantly, a current-ticker pull does not restore delisted securities or permanent-ID history.
- Public historical-membership lists do not themselves provide a survivor-bias-free adjusted price panel.

## Required directory contract

Place licensed or otherwise authorized raw/derived files outside the distributable ZIP under:

```text
licensed_data/us_pit/
  source_manifest.json
  security_master.csv
  daily_prices.csv
  index_membership.csv
  corporate_actions.csv
  delistings.csv
```

Run:

```bash
python research_v78/data_acquisition/pit_data_contract_v78.py licensed_data/us_pit --report V78_REAL_PIT_DATA_VALIDATION.json
```

A `PASS` only means the data contract is satisfied. It does not promote any strategy.
