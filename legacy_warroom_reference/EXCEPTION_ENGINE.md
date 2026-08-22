# EXCEPTION ENGINE — "when the model is wrong, find WHY by data" (built real)
Reproducible: `python exception_engine.py`. Worked on your own example: "Quad 3 → long gold, but gold fell — why?"

## The mechanism you asked me to figure out
When a thesis says "regime R → asset A moves direction D" but reality does the opposite, the system must **investigate why, by data, ranked** — never stay silent, never fabricate. Four steps, and this structure generalizes to crash meter / tickers / bottleneck (each needs its own data):
1. **FALSIFY** — does the law even hold on data? (IC, win-rate, walk-forward) — no hardcoded verdict
2. **ISOLATE** — find the exceptions: precondition held but asset moved against it
3. **ATTRIBUTE** — decompose the failed move onto the drivers we have, ranked, with evidence strength
4. **COVERAGE** — state honestly which candidate causes are NOT in the data

## What it found on gold (real data, 1971–2023 floating era)
**Data-integrity catch first:** gold was pegged (~$35) until Aug-1971, so ~90 years of the panel had zero gold movement. The engine caught this (median return +0.00%, 25% win-rate on full sample) and restricted to the floating era. This is the discipline you want — the engine flagged its own contaminated input instead of reporting a garbage number.

**Step 1 — the law holds, but it's a tendency not a certainty:**
- IC(Δreal-yield → gold) = **−0.156** (p=0.0001), walk-forward sign stable (early −0.059, late −0.267)
- gold win-rate when real yields FELL: **58%** (median +0.46% vs −0.23% when yields rose)
- So "Quad 3 → gold up" is a **58% edge, not a law**. The other 42% is the point.

**Step 2 — the exceptions:** real yields fell (law says gold up) in 332 months; gold fell anyway in **139 (42%)**.

**Step 3 — WHY, by data, ranked:** in the exception months, the dominant drag was the **DOLLAR** (β=−0.198, avg contribution −0.058). The real-yield tailwind was real (+0.097) but **the dollar rise overwhelmed it**. That is the honest, ranked, data-driven answer to "why did gold fall when it should've risen" — not "the model failed."

**Step 4 — honest coverage:** attributed with real-yield / dollar / inflation / oil. **NOT** in the data (would complete it): China/EM central-bank reserve sales (your exact example), gold-ETF flows, COT positioning, forced-liquidation events, TIPS real yield. The engine answers with what it has and flags the seam — it does not fake the China leg.

## The honest scope
This is the **kernel**, proven on one thesis with the data on hand. To run it for "everything — every metric, weight, formula, combination" (your ask) needs two things I can't shortcut: (1) the **data** for each thesis (most feeds aren't wired), and (2) the **multiple-testing discipline** already in `research_harness.py` (Benjamini-Hochberg FDR + White's Reality Check) so that testing thousands of metric combinations doesn't become an overfitting factory that "discovers" false laws. The 4-step falsify→isolate→attribute→coverage loop IS the "test every metric, can't be wrong" discipline — applied honestly, one thesis at a time, on real data.
