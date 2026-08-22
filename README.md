# EROS / WARROOM — Vision Rebuild

This rebuild uses the **original Warroom product idea as the shell** and the newer EROS discipline as the decision brain.

## Run

Windows: double-click `EROS.bat`.

CLI smoke run:

```bash
python run.py
python run.py --refresh
```

## Daily product flow

App opens → factual/public data refresh → economic state map → verified-evidence scenarios → unverified scenario radar → asset expressions → automatic ticker candidates → fail-closed qualification.

There is **no required manual company JSON upload** in the daily workflow.

## Five user-facing tabs

1. Command Center
2. Global Explorer
3. Opportunity Engine
4. Portfolio
5. Research Lab

## Scenario discovery

Two lanes exist:

- **Verified-evidence scenarios:** generated only from factual data already accepted as evidence.
- **Scenario Radar:** public-news leads are routed into event families and causal chains, but remain `UNVERIFIED_LEAD` until primary/factual evidence confirms the mechanism.

This allows the system to investigate things such as mega IPO/index reflexivity, data-center credit/securitization fragility, policy conflict, China gold demand, physical supply shocks, fiscal/funding stress, and new combinations not explicitly pre-programmed as a finished trade thesis.

## Tickers

Ticker candidates are generated automatically from scenarios and current company fundamentals when available.

A candidate is **not** a BUY/SHORT simply because it appears. Production qualification remains blocked until PIT company transmission, historical ticker replay, calibrated scenario probabilities, priced-in evidence and expected-value validation are available.

This is intentional fail-closed behavior.

## Data

Live adapters attempt:

- FRED public CSV / DBnomics mirror for US macro/rates/credit/liquidity
- US Treasury Fiscal Data
- World Bank country context
- Yahoo Finance for market context and current company fundamentals
- GDELT for **news discovery leads only**

No synthetic data are used in the production path.

## Legacy Warroom

The complete prior Warroom is preserved under `legacy_warroom_reference/` for migration/reference. Its classic price-derived directional modules are not automatically used by the new production decision path.

## Scientific status

Product/behavior acceptance can pass while some scientific components remain scope-limited. Do not interpret a runnable app or a candidate ticker as universal proof.
