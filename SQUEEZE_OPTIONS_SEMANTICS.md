# Squeeze and Options Semantics

## US options context

For each configured underlying, the engine calculates:

- call/put OI and volume;
- put/call OI and volume ratios;
- call wall and put wall;
- positive/negative signed-gamma reference strikes;
- max-pain reference;
- nearest-expiry ATM-straddle expected-move band;
- approximate 25-delta skew and ATM IV term structure;
- signed-OI gamma proxy;
- Black–Scholes vanna and charm proxies;
- observed options-flow balance when a trade-level feed is present.

The directional output is named `directional_context`, not a price forecast. True dealer gamma requires position-side/dealer inventory information. A chain snapshot alone cannot prove it.

## US squeeze context

The descriptive pressure index can use:

- short interest as a percentage of free float;
- cost to borrow;
- days to cover;
- option-flow pressure;
- signed-gamma amplification context;
- current price/setup confirmation.

Missing short-interest/borrow data reduces evidence completeness. It is never filled with zero.

## Crypto derivatives context

The engine normalizes available observations from Binance, Bybit and OKX and keeps raw venue rows. It calculates:

- median mark price;
- reported USD OI where the venue supplies comparable USD value;
- mean funding rate;
- median account long/short ratio;
- median taker buy/sell ratio;
- price/OI quadrant versus a prior stored snapshot;
- short- and long-squeeze pressure indices.

Because venue contract units and OI definitions differ, the system does not claim a canonical global OI total. Raw venue values remain available in the detail drawer.

## Time and target context

- Funding is intraday context.
- OI needs persistence across snapshots.
- Options horizons are tied to the loaded expiry.
- Expected move is tied to the nearest loaded expiry and available quotes.
- Wall/max-pain zones can move as OI changes.
- Liquidation targets require a dedicated liquidation heatmap feed.
- War Room never promises an exact direction, target, or duration from derivatives alone.
