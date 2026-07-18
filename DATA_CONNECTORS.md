# War Room OS — Data Connectors

## Production contract

Production mode never fills missing market data with synthetic series. A failed or unconfigured source must remain `NO_DATA`, `NOT_CONFIGURED`, `STALE`, or `ERROR`. Structural reference maps are labeled `STRUCTURAL`; inferred relationships are dashed in the UI; observed events remain `OBSERVED`.

## Refresh architecture

The Streamlit app separates two cadences:

- Core prices, macro and engines: cached for 60 seconds.
- Institutional event layer: polled every 10–60 seconds, selectable in the sidebar; provider-specific file caches prevent duplicate paid requests.

This is near-real-time REST polling. It is not presented as tick-perfect exchange colocation. The UI preserves the last workspace in local storage when it refreshes.

## Connectors

| Connector | Environment variable | Dataset | UI semantics |
|---|---|---|---|
| SEC EDGAR | `WARROOM_SEC_USER_AGENT` | Form 4, 8-K, 13D/G, 13F-HR, 10-Q/K, S-1, 424B5 | Disclosure only; reporting lag varies by form |
| Unusual Whales | `UNUSUAL_WHALES_API_KEY` | Options flow alerts and off-exchange prints | Trade-side evidence; hedge/open-close intent remains unconfirmed |
| Massive | `MASSIVE_API_KEY` | US trades filtered to `exchange=4` with `trf_id` | Raw TRF prints; never automatic accumulation/distribution |
| Nansen | `NANSEN_API_KEY` | Provider-classified Fund/Smart Trader holdings | Smart-Money classification is evidence, not a forward-return guarantee |
| Arkham | `ARKHAM_API_KEY` | Large labeled on-chain transfers | Transfer event only; exchange/custody/internal movement must be classified |
| yfinance | none | Prices and option-chain OI/IV | OI-implied gamma proxy, not observed dealer inventory or live options flow |
| FRED | existing loader / optional key | Macro and liquidity series | Official macro series when available |
| FINRA short volume | none / snapshot builder | Aggregate short-sale volume | Descriptive only; not dark-pool prints, short interest, or institutional intent |

## Setup

Copy `.env.example` into the environment used to start Streamlit. Do not commit real keys.

Linux/macOS example:

```bash
export WARROOM_SEC_USER_AGENT="War Room OS your-email@example.com"
export UNUSUAL_WHALES_API_KEY="..."
export MASSIVE_API_KEY="..."
export NANSEN_API_KEY="..."
export ARKHAM_API_KEY="..."
streamlit run app.py
```

Windows PowerShell example:

```powershell
$env:WARROOM_SEC_USER_AGENT="War Room OS your-email@example.com"
$env:UNUSUAL_WHALES_API_KEY="..."
$env:MASSIVE_API_KEY="..."
$env:NANSEN_API_KEY="..."
$env:ARKHAM_API_KEY="..."
streamlit run app.py
```

## Institutional evidence rules

A large event is not a position by itself. War Room keeps `position_inference=UNCONFIRMED` until independent evidence agrees. Examples of confirmation include repeated prints, next-day open-interest reconciliation, price absorption, a filing, ownership change, or a labeled entity sequence that is inconsistent with custody/internal transfer.

Options-chain OI structure and live options flow are separate datasets. Protocol TVL and whale holdings are separate datasets. FINRA aggregate short volume and individual TRF prints are separate datasets.

## Live-data failure behavior

- One failed provider does not crash the dashboard.
- Existing valid sources continue rendering.
- The source registry shows provider, dataset, state, fetched time, stale threshold, record count and note.
- No placeholder trade, fake print or synthetic ticker is emitted.
