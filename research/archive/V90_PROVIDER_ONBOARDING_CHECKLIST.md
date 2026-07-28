# V9.0 Provider Onboarding Checklist

This is the shortest honest route from `0/5 data admitted` to real historical tests. A provider purchase does not prove alpha; it only removes a data blocker.

## US stocks

Core institutional route: CRSP (security lifecycle, corporate actions, delistings) + point-in-time fundamentals/estimates (LSEG or equivalent) + consolidated quote/trade data or broker fills. Cboe options and securities-finance data are separately registered add-ons; their absence cannot block the fundamental core, but the core cannot claim an options/borrow edge.

## IHSG

Core route: IDX historical/reference/EOD data + KSEI lifecycle/ownership + issuer filings and corporate actions + actual broker fills. Historical broker summary/done-detail is an add-on required only for the broker-accumulation claim.

## Commodities

Proof is archetype-specific. Energy, metals and agriculture cannot share one model. Core route: official as-released physical balances + release-lagged CFTC positioning + exact futures contract master + exchange quote/trade/settlement data. Physical basis/freight is an add-on where the thesis requires it.

## FX

Freeze the execution instrument first. CME futures proof and OTC spot proof are different scopes. Core route: vintage relative macro + balance of payments/reserves + positioning/funding + exact venue quotes/fills.

## Crypto

Each venue and collateral regime is a separate scope. Core route: venue lifecycle and market archive + protocol/token economics + supply/unlocks + stablecoin liquidity + funding/basis/OI/liquidations + own-account fills and counterparty incidents.

## Mandatory onboarding receipts

Every imported dataset must include provider identity, license/use ceiling, raw-file SHA-256, coverage dates, timezone, observation timestamp, market-availability timestamp, revision semantics, entity identifier mapping, missingness report and extraction-code hash.
