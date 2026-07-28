# V54 Options/Gamma Video Source Map

## Video inspected

Uploaded video: `6c7b822099336970b8c7ffec44da3244.mp4`, 39.03 seconds.
Visible source page: London Strategic Edge, **Gamma Scalping | Interactive Guide With Real Options Data**.
Visible creator overlay: TikTok `@falaktb`.

## Exact claims visible in the video

1. Gamma scalping holds a long-gamma option position and dynamically delta-hedges it with the underlying.
2. Delta changes as spot moves, so the hedge becomes unbalanced.
3. A long-gamma hedge tends to sell after rises and buy after falls.
4. If rebalancing gains exceed theta decay, the position may profit without requiring a directional forecast.
5. The page presents the delta-hedged P&L as a gamma-weighted realized-versus-implied variance trade.
6. The video says market makers sell options to clients, hedge the resulting delta exposure, and capture spread as compensation for liquidity.

## Audit verdict

### Correct and importable as theory

- Gamma is the change in delta as the underlying moves.
- Dynamic delta hedging is required because delta is not constant.
- A long-gamma position is locally contrarian in its hedge flow; a short-gamma position is locally pro-cyclical.
- A delta-hedged long option is economically related to buying realized variance at an implied-variance price.
- Hedge profitability is path-dependent and must exceed theta, spreads, fees, slippage, hedge latency, and model error.

### Oversimplified and must not be imported literally

- Gamma scalping is not an option-pricing model.
- “Realized volatility above implied volatility” is not by itself a guaranteed profit rule. The relevant exposure is gamma-weighted realized variance along the path, with discrete hedging, surface changes, jumps, dividends/rates, and costs.
- “Profit regardless of direction” means first-order delta neutrality, not risk-free P&L.
- Market makers do not always sell options to clients. Their inventory can be long or short gamma, and positions can be offset across strikes, expiries, products, and venues.
- Gross option volume or gross open interest does not reveal dealer net gamma.
- Call wall, put wall, gamma wall, and gamma flip are estimated mechanical zones, not deterministic support/resistance or directional targets.

## War Room mapping

### Decision purpose

Use options to answer four separate questions:

1. **Expected movement magnitude:** how wide is the distribution/range priced by the surface?
2. **Volatility mispricing:** is future realized variance likely to exceed or undershoot the tradable implied surface after costs?
3. **Mechanical flow regime:** are likely dealer hedge flows damping or amplifying spot moves?
4. **Execution/timing:** where and when can strike/expiry concentration alter first-passage, pinning, acceleration, or liquidity?

Do not use the module as a standalone LONG/SHORT engine.

### Causal role

- Implied volatility is a market price of optionality/risk under the option surface, not a pure physical forecast.
- Net dealer gamma changes the sign of hedge feedback.
- Delta, gamma, vanna, and charm change hedge demand as spot, volatility, and time move.
- Market impact depends on hedge notional relative to underlying liquidity/depth, not raw option notional.

### Market-specific scope

- **US indices/equities:** eligible when exact listed-option chain, quotes, trades, open interest, contract multiplier, and underlying hedge instrument are available.
- **Futures/commodities/FX:** eligible only through exact listed futures-option contracts and their actual underlying futures.
- **Crypto:** eligible only per venue and underlying where option order book, IV, Greeks, OI, expiry, and contract rules are available.
- **IHSG:** no direct gamma module unless IDX lists liquid options with sufficient data. Futures/broker-flow remain separate proxies and must not be relabeled as GEX.

### Data lineage requirements

Minimum row-level fields:

- venue and product;
- underlying and hedge instrument;
- option type, strike, expiry, multiplier, exercise/settlement style;
- bid, ask, sizes, timestamp, underlying bid/ask;
- trade price/size and signed-side confidence;
- open interest timestamp and whether it is previous-day or intraday;
- IV and Greeks source/model;
- rates, dividends/forward/funding inputs;
- quote quality, staleness, crossed-market and liquidity flags.

### Candidate metric families

No metric is production-approved at mapping stage.

1. Tradable IV surface and term structure.
2. Gamma-weighted implied variance versus forecasted realized variance.
3. Cost-adjusted gamma-scalping breakeven.
4. Signed net dealer delta/gamma/vanna/charm by strike and expiry.
5. Hedge-flow notional normalized by underlying ADV, spread, and depth.
6. Gamma concentration, flip uncertainty, and expiry concentration.
7. First-passage probability/time to strike clusters.
8. Pinning versus continuation probability conditional on gamma sign, trend, event state, and liquidity.
9. Volatility-event premium and post-event crush/expansion.
10. Confidence score for dealer-side inference.

### Required challengers and baselines

- realized-vol-only baseline;
- implied-vol-only baseline;
- ATR/range baseline;
- distance-to-strike and open-interest-only baseline;
- trend/momentum and liquidity baseline;
- unsigned GEX baseline;
- signed-flow model;
- signed-flow plus liquidity normalization;
- full surface/Greek model.

### Frozen claim limits

Allowed claims before proof:

- “options price a range/distribution”;
- “estimated hedge feedback is damping/amplifying”;
- “this strike/expiry is a mechanical concentration zone”;
- “this is a volatility or timing hypothesis.”

Forbidden claims before proof:

- “dealer gamma predicts direction”;
- “call wall is guaranteed resistance”;
- “put wall is guaranteed support”;
- “gamma flip guarantees acceleration”;
- “realized volatility above IV guarantees gamma-scalping profit”;
- “gross OI identifies dealer inventory.”

### Promotion tests

- purged walk-forward and untouched lockbox;
- event-time aggregation to avoid overlapping observations;
- separate 0DTE, weekly, monthly, and longer expiry cohorts;
- separate index, ETF, single-stock, futures, FX, and crypto tests;
- calibration of pin/break/first-passage probabilities;
- comparison with simple baselines;
- transaction costs, spread, slippage, hedge frequency, and no-trade bands;
- uncertainty sensitivity for trade-side and dealer-side classification;
- liquidity-normalized impact tests;
- multiple-testing correction and frozen global trial ledger;
- prospective signed predictions before any live weight.

## Immediate integration decision

- Import the video as a **research source and causal mapping input**.
- Add a distinct **Options Volatility & Mechanical Flow** research module.
- Keep its live direction and capital weights at zero.
- Do not merge it into the existing direction engine until signed-flow, liquidity-normalized, OOS and prospective evidence passes.
