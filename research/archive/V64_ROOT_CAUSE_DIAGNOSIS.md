# V6.4 Root-Cause Diagnosis — Why “Nothing Is Proven” Kept Happening

Generated: 2026-07-26T03:00:04.818326+00:00

## Root cause 1 — Four different proof questions were collapsed into one

Earlier releases treated these as though they were identical:

1. Does an aggregate historical market claim exist?
2. Does it survive in the modern era and a tradable universe?
3. Can War Room reconstruct it point-in-time at ticker level?
4. Is the live implementation cost/capacity/prospective/capital ready?

That made a real historical result look like zero evidence merely because the live feed was unavailable, while also making an attractive historical backtest easy to overstate as investable. V6.4 separates all four levels.

## Root cause 2 — Historical anomaly strength decayed in modern, non-micro stocks

The three V5.8 survivors remain strong in their original historical validation/lockbox tests, but all three fail the frozen 2006–2014 / 2015–2024 modern all-stock gate. External July 2026 evidence reports that the median published anomaly falls to about 7 bps/month when restricted to post-2005 non-micro stocks, before modest luck/cost allowances.

## Root cause 3 — Maintained portfolio returns are not a ticker selector

`PredictorLSretWide.csv` contains aggregate long-short portfolio returns. It cannot prove that War Room can reconstruct the exact stock membership, availability date, corporate-action handling, liquidity, turnover, borrow, or next ticker before the move.

## Root cause 4 — Flat cost stress was used as a universal proxy

A flat 25 bps/month hurdle is useful as a robustness screen but is not actual implementation cost. Different signals have different turnover, spread, market impact, borrow and data costs. V6.4 reports gross statistical proof separately and refuses to call it investable until exact portfolio construction and turnover are reconstructed.

## Root cause 5 — Massive-move labels combine different causal species

A +50% stock move can originate from earnings revisions, customer qualification, pricing/capacity, takeover, squeeze, spin-off, fraud resolution or commodity beta. Generic OHLCV/OI/liquidation combinations cannot be expected to solve every origin. Earlier negative batteries correctly killed universal shortcuts but could not test missing origin data.

## Root cause 6 — “Untouched lockbox” was sometimes operationally impossible

The maintained OpenAP archive had already been used in earlier War Room research. V6.4 therefore calls the all-208 modern screen a **frozen confirmatory re-analysis**, not an independent external lockbox. A genuinely independent proof now requires post-2022/2023 point-in-time option data or a separate vendor vintage.

## What changed

- Historical aggregate market proof is allowed to be positive without granting capital.
- Modern archive support is separated from independent modern proof.
- Non-micro/capacity proof, ticker-level proof and prospective proof each have separate gates.
- No result receives live weight merely because a statistical claim passes.
