# V6.6 Scoped Usable Control — Evidence and Operating Contract

## Why earlier versions were not final

Earlier versions correctly prevented unsupported alpha promotion, but they mixed two different questions:

1. Can a module forecast returns or select a ticker?
2. Can a module reliably reduce a known portfolio risk?

Canonical trend and style sleeves failed as standalone return or crisis-alpha engines in modern periods. The broad-equity SMA10 rule also failed as a next-month crash predictor. It became confirmable only after the claim was frozen to its actual economic function: monthly left-tail and drawdown reduction.

## Frozen rule

At month `t`, broad-US-equity exposure may remain at its separately authorized baseline only when the completed price at month `t-1` is at or above its trailing ten-month simple moving average. Otherwise the maximum permitted broad-US-equity multiplier is zero until a later completed monthly rebalance.

- One-month implementation lag
- Monthly observations only
- No leverage
- No shorting
- No intramonth switching
- Cash return assumed zero in the historical test
- Primary one-way switching cost: 10 bps
- Stress one-way switching cost: 25 bps

## Permission boundary

Allowed:

- Cap an independently authorized broad-US-equity allocation
- Reduce that allocation to cash at a completed monthly rebalance
- Display the current state and evidence

Forbidden:

- Treat `BASELINE_CAP_ALLOWED` as a buy signal
- Create an equity position that did not otherwise have permission
- Select individual stocks
- Predict a crash date
- Short the market
- Apply the rule to IHSG, FX, commodities, crypto, sectors, or individual stocks without a new test
- Change the lookback, rebalance frequency, or threshold after seeing outcomes

## Fail-closed implementation

The runtime denies permission when:

- fewer than ten completed monthly observations exist;
- the final ten-month window has a gap or duplicate month;
- a value is non-positive or non-finite;
- the latest observation is future-dated;
- the latest observation exceeds the permitted staleness;
- evidence or protocol hashes do not match.

A denied state has a maximum multiplier of zero. This prevents stale or malformed data from accidentally creating exposure.

## Why this counts as usable but not universal

The rule has a narrow, historically confirmed risk-control outcome. Its deployment action is deterministic, low-frequency, and directly tied to the tested scope. It still cannot prove future profits or solve ticker selection. Future alpha modules require point-in-time data and prospective outcomes that do not exist until time passes.
