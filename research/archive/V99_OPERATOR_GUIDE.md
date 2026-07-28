# V9.9 Operator Guide

## Normal daily use

1. Start with `RUN_V99_APP.bat`.
2. Confirm the top status shows `DATA AVAILABLE`.
3. Check `Current quote markets`. A zero value means current execution references have not refreshed; it does not invalidate bundled historical research.
4. Open a market and select a ticker. The same packet contains research context, causal chain, flow status, projection state, risk/execution and proof.
5. Treat every `RESEARCH_ONLY` packet as a research candidate, not a buy/sell instruction.

## When current quotes remain zero

Run `REFRESH_V99_QUOTES.bat`. Check the terminal output and `runtime/worker_status.json`. Common causes are missing network access, provider blocking, missing `yfinance`, or an invalid provider response. The collector retains valid last-known context as stale/non-executable rather than deleting it.

## When Parquet shows reader unavailable

Run `SETUP_V99.bat` again. The data file is still present and hash-validated; `pyarrow` is the reader dependency.

## Capital gate

A packet can be exported only after all of these are true:

- exact market proof is hash-bound and signature-valid;
- ticker-specific value bridge is valid;
- current execution quote is fresh;
- entry, stop, target, invalidation and causal chain are complete;
- portfolio and account risk limits pass;
- human HMAC approval is current.

Auto-submit is disabled. Orders remain broker-neutral manual exports.

## Data claims

- Historical files are research/outcome context unless their `available_at` lineage is reconstructed.
- Current public snapshots do not become historical proof automatically.
- A causal-chain or bottleneck reference is not a numeric target.
- A historical entry reference is not a current recommendation.
- Data presence never promotes a strategy by itself.
