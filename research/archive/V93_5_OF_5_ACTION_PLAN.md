# Exact route to 5/5

## Phase A — automated now

Run `public_data_bootstrap_v93.py` to collect and hash SEC, CFTC, Binance and Deribit evidence. Add FRED and EIA keys to the existing official collector for ALFRED and EIA vintages.

## Phase B — import licensed/official exports

- US: Sharadar SF1/SEP/TICKERS or institutional equivalent.
- IDX: Data Reference, historical EOD/log, corporate actions, issuer fundamentals, controller/free-float.
- Commodity: CME WTI, gold and copper histories with exact contract metadata.
- FX: CME EUR, JPY, GBP, AUD and CAD futures histories.
- Crypto: paid L2/on-chain data only for claims that explicitly require it.

## Phase C — import actual account fills

Export fills from every exact execution venue and normalize them with `fill_normalizer_v93.py`. Public prices are never accepted as fills.

## Phase D — blind historical proof

Freeze models, hashes, trial budgets and universes. Keep outcomes under separate custody. Run projection calibration, bottleneck activation uplift, extreme-winner/large-move recall, real costs and stress drawdown.

## Phase E — limited production

Run shadow first, then small capital. Freeze each forecast before execution and reconcile orders/fills without manual backfill.

## Phase F — fully proven

Each market independently needs at least 200 closed prospective trades, 24 months, four regimes, net PF >= 1.50, bootstrap PF lower bound >= 1.20, normal MDD <= 15%, stress MDD <= 20%, and passed projection/bottleneck tests.
