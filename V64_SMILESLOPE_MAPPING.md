# V6.4 SmileSlope Mapping

## Exact candidate

- **Acronym:** `SmileSlope`
- **Original source:** Shu Yan, *Jump Risk, Stock Returns, and Slope of Implied Volatility Smile* (JFE, 2011).
- **OpenAP definition:** last standardized volatility-surface observation each month; 30 days to expiration; put delta −0.50 and call delta +0.50; signal is put implied volatility minus call implied volatility.
- **Original economic sign:** larger put-minus-call slope predicts lower subsequent stock return. The factor therefore ranks low slope on the long side and high slope on the short side.
- **Original portfolio:** equal-weighted quintiles, one-month holding period.

## Causal role

`OPTIONS-IMPLIED JUMP-RISK / TAIL-DEMAND STATE`

This is not total open interest, dealer gamma, call/put volume, or realized liquidation. It measures asymmetry in near-ATM option-implied volatility and is interpreted as a jump-risk/tail-demand state.

## Frozen modern screen

Candidate universe: **208** non-control OpenAP factors.

Validation 2006–2014:
- alpha: **0.885%/month**
- HAC t-stat: **5.88**
- familywise lower bound: **0.332%/month**
- observations: **108**

Lockbox 2015–available end:
- alpha: **0.742%/month**
- HAC t-stat: **4.24**
- familywise lower bound: **0.100%/month**
- observations: **97**

It is the **only** one of 208 candidates to pass the gross primary gate in both periods. It does **not** pass the familywise 10 bps/month hurdle in both periods; the lockbox lower bound misses by a very small amount.

## Why this is not yet the SNDK detector

- Aggregate portfolio return, not stock-level point-in-time reconstruction.
- Official OpenAP release states option-implied signals currently end in December 2022; the bundled return file has its last SmileSlope label in January 2023.
- No non-micro/value-weighted/liquidity-screen result was available in the runtime.
- No actual turnover, spread, market-impact, data-license or short-borrow calculation.
- The archive was used by earlier research, so no independent external lockbox.
- The factor predicts relative one-month returns; it does not specifically predict +50% moves or catalyst timing.

## Exact next proof battery

1. Acquire PIT OptionMetrics or equivalent full volatility surfaces through 2026.
2. Reconstruct 30D ±50-delta matched call/put IV using quote-time, NBBO and stale-quote filters.
3. Freeze non-micro, price, liquidity and option-volume/OI eligibility rules.
4. Reconstruct equal-weighted, value-weighted and capacity-weighted portfolios.
5. Measure turnover, spread, impact, data cost and borrow separately.
6. Hold out 2023–2026 as an independent external/prospective lockbox.
7. Test `SmileSlope` alone, then only pre-registered interactions with point-in-time AnalystRevision, earnings/guidance origin and borrow scarcity.
8. Measure Precision@K, Recall@K, remaining return, MFE/MAE and lead time for extreme winners.

## Cross-market transport rule

- **US stocks:** exact candidate, subject to listed-option and data-quality eligibility.
- **Commodities/futures:** re-derive from contract option surfaces; no automatic transfer.
- **FX:** 25-delta risk reversal is related but not the same signal; separate proof required.
- **Crypto:** venue-specific option skew may be tested separately; fragmented liquidity and collateral matter.
- **IHSG:** no direct listed-equity-options implementation; do not synthesize a fake SmileSlope proxy.

## Permission

- Historical/modern archive research claim: scoped support.
- Live decision weight: **0.0**.
- Stock-level selector: **not proven**.
- Capital permission: **BLOCKED**.
