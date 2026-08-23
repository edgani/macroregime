# Macro Trading Framework — Causal Research & Decision OS Upgrade

You are upgrading the existing **Macro Trading Framework / EROS-style decision system**.

This is NOT a technical-analysis dashboard.

Do not introduce:

- RSI;
- MACD;
- SMA/EMA directional logic;
- Bollinger Bands;
- candlestick patterns;
- chart-pattern alpha;
- Fibonacci;
- classical support/resistance;
- technical breakout signals;
- price-derived momentum indicators;
- price-derived regime classifiers.

Price may only be used where legitimately required for:

- outcome labels;
- valuation;
- execution/risk;
- market-implied expectations;
- event-study response;
- portfolio accounting.

The system's purpose is:

> transform macroeconomic, fundamental, market-implied, positioning, policy, liquidity and cross-asset evidence into falsifiable causal scenarios, calibrated probabilities, cross-market opportunity rankings and explicit invalidation conditions.

---

# 1. PRIMARY UPGRADE

Move the framework from:

> “Here are macro metrics and a scenario.”

toward:

> “Here are the competing causal mechanisms, what the market currently prices, which mechanism is gaining/losing evidence, the probability distribution of outcomes, which markets benefit or lose, how much runway remains, and exactly what would invalidate the thesis.”

---

# 2. MATFIN PRINCIPLE: EVERY CLAIM IS AN EXPERIMENT

Treat every macro rule as a hypothesis.

Examples:

> “Re-steepening after inversion predicts recession stress.”

> “Credit-spread acceleration precedes equity drawdown.”

> “VIX backwardation implies worsening risk.”

> “Liquidity expansion supports crypto.”

None may become a production rule merely because the narrative sounds economically plausible.

For every candidate:

1. write causal hypothesis;
2. define mechanism;
3. define observable variables;
4. define timing;
5. define outcome;
6. define competing explanation;
7. define null hypothesis;
8. test point-in-time data;
9. use negative/matched controls;
10. perform temporal OOS;
11. perform cross-era/country testing where applicable;
12. perform ablation;
13. document failure domain.

Maintain an **Experiment Registry**.

Record failed ideas as carefully as successful ideas.

---

# 3. SEPARATE MECHANISM FROM CORRELATION

For each metric, require:

### Actor

Who is acting?

### Constraint

What balance-sheet, policy, funding, regulatory, liquidity, collateral, income, or behavioral constraint exists?

### Transmission

How does the mechanism reach the relevant asset?

### Horizon

How quickly should the effect appear?

### Observable confirmation

What should happen if the thesis is correct?

### Contradiction

What evidence should not occur?

### Pricing

How much appears already discounted?

Metrics without defensible causal transmission should be downgraded even if historical correlation looks attractive.

---

# 4. BUILD A THESIS LIFECYCLE ENGINE

Borrow the useful concept of continuously updating the thesis, but formalize it quantitatively.

For every active macro scenario track:

[
P\_t(Thesis)
]

as new data arrives.

Do not use arbitrary confidence scores.

Update only from evidence whose historical conditional information has been evaluated.

Every thesis must include:

- INITIAL PRIOR;
- SUPPORTING EVIDENCE;
- CONTRADICTING EVIDENCE;
- CATALYST WINDOW;
- PRICING/CROWDING;
- THESIS DECAY;
- INVALIDATION;
- NEXT DISCRIMINATING OBSERVATION.

Explicitly distinguish:

**Thesis still true but fully priced**

from

**Thesis becoming false.**

They are not the same problem.

---

# 5. COMPETING SCENARIOS + NULL

Never produce only one narrative.

At minimum:

### Base scenario

### Competing scenario

### Tail/adverse scenario

### Null / no meaningful macro edge

Probabilities must sum coherently.

Each scenario must specify:

- causal chain;
- actors;
- triggers;
- timing window;
- likely duration;
- expected peak;
- decay process;
- confirmation;
- contradiction;
- beneficiaries;
- losers;
- what is already priced;
- invalidation.

Avoid storytelling without discriminating evidence.

---

# 6. VOLATILITY STATE AS A CONDITIONING VARIABLE

Use useful concepts from volatility research, but do NOT turn volatility into a directional oracle.

Candidate information:

- VIX level;
- VIX percentile;
- VIX futures term structure;
- term-structure slope/curvature;
- VVIX;
- implied vs realized volatility;
- skew;
- vol-of-vol;
- option-implied event premium;
- expiry/event concentration where reliable data exists.

Avoid crude rules such as:

> VIX > 20 = bearish.

Instead build states such as:

- CALM;
- NORMAL;
- STRESSED;
- EVENT;
- VOL EXPANSION;
- VOL CRUSH;
- DISLOCATED.

Then test whether macro relationships behave differently conditional on those states.

Use rolling/relative distributions where more robust than permanent fixed thresholds.

---

# 7. MARKET-IMPLIED FORWARD DISTRIBUTIONS

Where reliable option/futures data exists, build forward-looking distributions rather than deterministic targets.

Examples:

[
P(Return\_h < x)
]

[
P(Drawdown\_h > x)
]

[
P(Range\_h > x)
]

[
P(Asset\ reaches\ scenario\ zone)
]

Use:

- options-implied distributions;
- volatility surface;
- skew;
- futures curve;
- forwards;
- credit spreads;
- rate curves;
- FX forwards

where defensible.

Every probability interval must be empirically calibrated.

A claimed 80% interval should approximately achieve 80% coverage OOS under its exact definition.

Do not call an option-implied quantile “support” or “resistance.”

---

# 8. OPTIONS STRUCTURE IS OPTIONAL AND INSTRUMENT-SPECIFIC

Do NOT force GEX / CW / PW / Zero Flip / centroid concepts into the entire macro framework.

Only consider options-structure features when:

- options market is deep and relevant;
- historical point-in-time data exists;
- dealer-sign assumptions are documented;
- feature construction is reproducible;
- incremental information survives OOS.

Possible use:

> execution/context layer for highly liquid US indices.

Not:

> universal macro causal variable.

Test against matched controls before granting structural significance.

If the feature does not add information after volatility/pricing variables are included, reject it.

---

# 9. CRASH ENGINE: MECHANISM-FIRST

Preserve explicit separation:

### FRAGILITY

System vulnerable but no immediate crash implied.

### EARLY WARNING

Conditions deteriorating.

### ACUTE TRIGGER

Mechanism capable of forcing rapid repricing/deleveraging.

### SEVERITY

How large the damage could become.

### RECOVERY / REENTRY

Conditions under which systemic pressure is clearing.

Do not combine all variables into one arbitrary risk score without proving incremental value.

Test candidate signals at multiple horizons:

- 6m;
- 12m;
- 18m;
- 24m;

and shorter horizons where economically justified.

Distinguish:

**ordinary correction**

from

**liquidity/funding/credit/systemic event.**

ATH is not automatically bullish or bearish.

Test ATH/state-transition scenarios as separate hypotheses.

---

# 10. CROSS-MARKET CAUSAL TRANSMISSION

The system covers:

- US equities;
- Indonesia / IHSG;
- commodities;
- FX;
- crypto;
- other supported global markets.

Do NOT use mappings such as:

> USD down = gold up.

Instead model transmission.

Example:

[
Policy
\rightarrow
Real\ Yields
\rightarrow
Dollar
\rightarrow
Financial\ Conditions
\rightarrow
Asset\ Cashflows/Valuation/Flows
]

But allow the data to falsify the presumed chain.

For each market calculate whether the causal mechanism is:

- direct;
- indirect;
- weak;
- already priced;
- contradicted.

---

# 11. OBJECTIVE-SPECIFIC OPPORTUNITY ENGINE

Do not search for one universal “best trade.”

The optimal trade depends on objective.

Examples:

- maximize asymmetric upside;
- preserve capital;
- hedge crash risk;
- exploit short catalyst window;
- express long-duration macro view;
- relative-value opportunity.

Separate:

### Forecast edge

from

### Position-sizing edge

from

### Instrument-structure edge.

A better equity curve caused by volatility targeting does not mean the underlying forecast became more accurate.

---

# 12. TRADE EXPRESSION COMES AFTER THESIS

For every qualified opportunity determine:

### View

What exactly must happen?

### Horizon

When?

### Risk factor

What exposure are we actually trying to own?

### Instrument

Which instrument isolates it most cleanly?

### Pricing

Is the expected outcome already embedded?

### Cost

Spread, slippage, borrow, funding, tax, FX, capacity.

### Kill switch

What invalidates it?

Do not automatically translate:

> bullish thesis

into:

> buy stock.

Consider the cleanest available expression.

The final allowed actions remain:

- LONG;
- SHORT;
- NO TRADE.

NO TRADE must be a first-class result.

---

# 13. BOTTLENECK / WINNER-LOSER ENGINE

Do not return huge lists of mediocre candidates.

Find a small number of high-quality bottleneck opportunities.

For every candidate provide:

- dominant causal mechanism;
- why this asset specifically captures it;
- competing thesis;
- what is already priced;
- catalyst;
- probability distribution;
- downside distribution;
- upside distribution;
- remaining runway;
- timing;
- kill switch.

A previous winner may re-enter the opportunity set after correction if:

- mechanism remains intact;
- pricing improves;
- expected remaining payoff becomes favorable again.

Do not permanently blacklist prior winners.

---

# 14. REMAINING RUNWAY MODEL

For every opportunity separate:

[
TotalPotential
]

from

[
PotentialAlreadyConsumed
]

and estimate:

[
RemainingRunway
]

as a distribution.

Example output:

- 25th percentile remaining upside;
- median;
- 75th percentile;
- tail;
- probability thesis is already >80% priced.

Do not simply extrapolate previous price move.

Runway should come from:

- valuation gap;
- expected fundamental transmission;
- market-implied distribution;
- historical event analogues;
- positioning/crowding;
- scenario state.

If evidence does not support precision, provide a wide interval or mark uncertain.

---

# 15. PRICING AND CROWDING

A correct macro thesis does not guarantee a profitable trade.

Estimate separately:

[
P(MechanismTrue)
]

[
P(CatalystWithinHorizon)
]

[
P(NotFullyPriced)
]

[
P(TradeProfitableNet)
]

Keep these distinct.

A thesis can have:

> 80% mechanism probability

but:

> poor expected trade value

because positioning/pricing already reflect it.

This distinction is mandatory.

---

# 16. VALIDATION STANDARD

No component is “proven” merely because:

- unit tests pass;
- logic seems sensible;
- Monte Carlo looks good;
- an LLM agrees;
- a historical chart looks convincing.

Require:

- PIT/vintage-safe data;
- data provenance;
- no future revisions leakage;
- temporal OOS;
- walk-forward;
- frozen holdout;
- negative controls;
- matched controls;
- multiple-testing tracking;
- parameter sensitivity;
- regime robustness;
- cross-country/era replication where applicable;
- calibration;
- ablation;
- failure-library documentation.

Bootstrap/Monte Carlo may describe uncertainty.

They do NOT replace OOS validation.

---

# 17. MULTIPLE-TESTING DEFENSE

Because the research system will test many hypotheses, track the total search process.

Do not report the winning model's statistics as if it were the only model attempted.

Implement, where suitable:

- false discovery rate control;
- family-wise experiment tracking;
- deflated performance metrics where applicable;
- holdout untouched by the research loop.

The research machine must not become an automated overfitting machine.

---

# 18. DATA QUALITY / FAIL-CLOSED

No synthetic fallback may silently substitute for unavailable data.

Every production metric needs:

- source;
- timestamp;
- release vintage;
- revision status;
- update frequency;
- staleness threshold;
- transformation lineage.

If critical data is missing:

> lower confidence or fail closed.

Never fabricate neutral values to keep the dashboard populated.

---

# 19. OUTPUT FORMAT

For every major market / opportunity produce:

## CURRENT STATE

Growth
Inflation
Policy
Liquidity
Credit/Funding
FX
Commodity transmission
Positioning
Volatility state
Catalysts

## COMPETING SCENARIOS

Probability + uncertainty interval.

## CAUSAL CHAIN

Not just correlation.

## WHAT IS PRICED

## NEXT DISCRIMINATING OBSERVATIONS

## BENEFICIARIES / LOSERS

## OPPORTUNITY RANKING

LONG / SHORT / NO TRADE.

## REMAINING RUNWAY

Distribution, not one magic target.

## KILL SWITCHES

## DATA / MODEL RISKS

---

# 20. FINAL RESEARCH GATE

Every new metric must answer:

1. What decision does it improve?
2. What causal mechanism does it represent?
3. Does it add information beyond existing metrics?
4. Does it survive OOS?
5. Does it survive different regimes?
6. Is it calibrated?
7. Where does it fail?
8. Is the complexity worth the incremental information?

If the answer is no:

REMOVE IT.

---

# SUCCESS CONDITION

The final framework should not be the system with the most metrics.

It should be the system that can say:

> What is happening?

> Why is it happening?

> Which competing mechanism is most likely?

> What does the market already price?

> Which asset expresses the mispricing most efficiently?

> How much upside/downside remains?

> What changes the probability?

> What kills the thesis?

> When is NO TRADE the correct decision?

Every answer must be traceable to data, causal reasoning, and empirical validation.

Prefer a small set of strong, falsifiable signals over a large collection of plausible stories.