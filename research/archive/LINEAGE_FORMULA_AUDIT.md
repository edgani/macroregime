# LINEAGE + FORMULA/WEIGHT AUDIT
### Answering "prove data flows, not just that files exist." Reproducible: `python lineage_audit.py`

## 1. DATA LINEAGE — tested empirically (perturb feed → does the metric move?)
Full feed baseline present; each feed swapped low↔high one at a time.

| feed | → metric | responds? |
|---|---|---|
| DGS10 (10Y) | shock_prob | ✅ WIRED (56.7 → 79.3) |
| HY spread (BAMLH0A0HYM2) | fragility | ✅ WIRED (24.4 → 66.0) |
| HY spread | shock_prob | ✅ WIRED (43.3 → 79.3) |
| WALCL (Fed BS) | liquidity | ✅ WIRED (— → expanding) |
| DGS10 / WALCL / T10YIE | **fragility** | · constant (fragility is driven by HY-spread+vol only) |
| **any FRED feed** | **quad** | · **CONSTANT — the quad is PRICE-driven, not macro-fed** |
| **any FRED feed** | **posture** | · **CONSTANT — price-driven** |
| T10YIE (breakeven) | anything probed | · constant — appears **dead** in these paths |

**4/20 links are genuinely wired.** The honest headline: **the "macro regime quad" is mostly a PRICE-momentum signal, not a macro-feed signal** — the GIP engine derives growth/inflation from SPY/GLD/USO/UUP momentum, not from FRED. Calling it a macro quad oversells it. And **T10YIE looks like broken lineage** — it's fed but moves nothing I could probe. These are exactly the placeholder/default seams you predicted.

## 2. ROBUSTNESS
- **Feed-drop (remove ALL FRED):** system runs, degrades gracefully — quad falls Q3→Q2 (price-only), fragility → "no inputs available" (an honest reason-string, not a fake number). Does not crash. ✅
- **Decision-stability (perturb 10Y ±10%):** quad STABLE, posture STABLE — the decision does **not** flip on a 10% wiggle. Robust, not over-sensitive. ✅ (This is the test you flagged as most important.)

## 3. FORMULA + WEIGHT AUDIT — the two wired engines
**Systemic fragility** (`gcfis/engines/fragility.py:8`):
```
fragility = 0.30·credit + 0.20·breadth + 0.20·vol + 0.15·funding + 0.15·leverage
```
**Crash-pressure** (`gcfis/engines/crash_bottom.py:32`):
```
pressure = 0.22·fragility + 0.22·liquidity_contraction + 0.16·breadth_weak
         + 0.12·crowding + 0.10·divergences + 0.10·dealer_gamma + 0.08·distribution
```

**Why 0.30? Why 0.22?** Honest answer: **they are hand-set PRIORS, not optimized or proven.** The crash_bottom source says so verbatim: *"Weights are PRIORS pending walk-forward validation."* The fragility weights have no derivation either. The direction is defensible (credit gets the top weight, and the lineage test confirms credit/HY does drive fragility), but the exact numbers are not evidence-based. Per your standard, these should be shown banded, and a weight-optimization pass (with proper OOS + multiple-testing guards) is required before any weight is called "correct."

## 4. What this audit does NOT yet cover (your framework, honestly)
Still owed, and each needs real work (some needs live/forward data the sandbox can't reach):
- Full **feed table** (your ~60 feeds: GDP/CPI/PCE/payroll/ISM/MOVE/VVIX/gamma/dark-pool/on-chain/COT/…) — most are NOT wired; need a per-feed Source|Update|Engine|Used audit.
- **Weight optimization** (are 0.22/0.30 optimal?) + **SHAP/permutation importance** + **feature ablation** (does dropping the crash meter improve the decision?).
- **Decision-quality vs benchmark** — does Aggressive/Neutral/Defensive actually beat buy-and-hold OOS? (the real test, not signal IC.)
- **Cross-regime** (bull/bear/QE/QT/war/pandemic) + **PSI/concept-drift** + **replay** on named cases (NVDA/PLTR/CCJ/…).
- Per-tab **input→output→decision→visual→explanation→action** completeness.

## Bottom line
The lineage/robustness layer now has reproducible evidence: ~4 feed→metric links are real, the quad is price-not-macro-driven, T10YIE looks dead, decisions are stable and degrade gracefully. The crash/fragility formulas are documented with honest weights (priors, not proven). Everything else in your framework remains owed — this is a research platform under construction, not a finished one, and I won't claim otherwise.
