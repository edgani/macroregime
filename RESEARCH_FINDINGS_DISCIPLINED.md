# DISCIPLINED RESEARCH FINDINGS
### `research_harness.py` — anti-memorization factor scan. Re-run: `python research_harness.py`

Built against the "LLMs that remember too much" critique. Three defenses baked in: **anonymization**
(cross-sectional ranks only, ticker identity never enters the signal), **multiple-testing correction**
(Benjamini-Hochberg FDR + White's Reality Check), **out-of-sample** (held-out tail). 14 factors, each
with a stated economic mechanism — not a random combination sweep.

## What survived (genuine OOS edge, FDR-corrected)
| factor | OOS IC | t | mechanism |
|---|---|---|---|
| skew_60 | **+0.034** | 6.8 | idiosyncratic-skewness preference — high positive-skew names overpriced |
| rev_5 | **+0.032** | 4.9 | 1-week overreaction / liquidity provision |
| rev_21 | **+0.026** | 3.6 | 1-month mean reversion |
| illiq | **+0.019** | 3.8 | Amihud illiquidity premium |

**White's Reality Check: best |IC| 0.055, bootstrap p = 0.0005** → the edge beats the multiple-testing null. There is real cross-sectional predictability here — but it lives in **short-horizon microstructure**, not the glamorous factors.

## What got REJECTED — and why this matters more than the survivors
- **Momentum died OOS.** mom_126 IC −0.0008 (pure noise). And critically: my earlier "factor_momentum VALIDATED" (+0.021) was **split-dependent** — flip the train/test split and it's noise. Fragile-to-methodology = not a real edge. This is the lookahead/overfitting trap in action.
- **Low-volatility / BAB REVERSED.** IC −0.05, strongly significant but *wrong sign*. 2016-18 was risk-on; high-beta led. A naive backtest would have shipped the factor **backwards** and blown up in the next regime.
- maxret (lottery), range-location, drawdown-recovery, accel: significant raw, **die on FDR correction** → multiple-testing artifacts.

## The honest ceiling (the part no harness can fix)
This data (S&P 2013-18) is **inside my training window**. Even a clean pass here cannot rule out that
I've absorbed 2013-18 outcomes. Per the memorization proofs, skill and memory are *observationally
equivalent* on seen data. **The only memorization-proof test is post-Jan-2026 (post-cutoff) forward
data.** Every survivor above is therefore flagged PENDING forward confirmation. This is the rigorous
reason your "forward test" instinct was right all along.

## What this means for the product
- Ship the survivors (skew, reversal, illiquidity) as **candidate** short-horizon signals, flagged "pending forward."
- Do NOT ship momentum or low-vol as validated — they're fragile / regime-dependent here.
- The real durable edge remains the **structural** one you already have: IHSG bandar/foreign-flow (mechanism-based, validated IC 0.173), not a price-derived factor.
- There is no secret hidden metric in price/volume that the discipline didn't already surface. The edge is structure + execution + risk, not a magic combination.
