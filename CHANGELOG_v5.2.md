# v5.2 — Decision Interface Upgrade

- Every major chart now has **READ → DO → NEXT** guidance.
- Dashboard adds an explicit operational posture and puts **1M/3M/6M/12M projection** on the main screen.
- Projection is visualized as a normalized **P10–Median–P90 fan chart**.
- Opportunities now start with a **payoff-vs-downside Pareto radar** instead of an arbitrary composite score.
- Pareto frontier = higher historical analog median with lower probability of >10% loss; it is a research queue, not a trade signal.
- Selected opportunities show projection, dominant macro sensitivities, what changes the view, and why trade action is still locked.
- Company bottleneck section becomes a visible five-stage funnel: Mechanism → Monetization → Pricing Gap → Catalyst → Projection.
- Added volatility-normalized correction context (`drawdown / expected 3M vol`) so prior winners are not judged by raw drawdown alone.
- Relationship charts explain how to use them; multi-window sign stability is surfaced where available.
- Trade action remains fail-closed when PIT pricing/revisions/catalyst/runway are unavailable.
