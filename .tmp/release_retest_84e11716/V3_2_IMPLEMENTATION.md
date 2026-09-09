# v3.2 Implementation Map

## Objective
Find emerging, economically explainable opportunities early; freeze what was known then; keep watching; label future outcomes; learn calibration without allowing the model to self-modify production logic.

## Data flow

```text
CURRENT / PIT DATA
      ↓
EXISTING CHANGE + MACRO + FUNDAMENTAL ENGINES
      ↓
AUTOMATIC OPPORTUNITY DISCOVERY
      ↓
CAUSAL THEME / BOTTLENECK / BENEFICIARY MAP
      ↓
COMPONENT SCORES + EXPECTATION GAP
      ↓
IMMUTABLE OPPORTUNITY_EVENT
      ↓
PERSISTENT LIFECYCLE WATCH
      ↓
FORWARD OUTCOME MATURATION
      ↓
RELATIVE ALPHA + PATH RISK
      ↓
REGIME / MARKET / THEME CALIBRATION
      ↓
CHRONOLOGICAL WALK-FORWARD + BASELINE COMPARISON
```

## Files
- `opportunity_longitudinal.py` — SQLite schemas, immutable event memory, lifecycle, alerts, failures, missed-runner records.
- `opportunity_discovery.py` — archetypes, causal chain, economic-capture / bottleneck / expectation component scoring, event sync.
- `opportunity_outcomes.py` — forward path outcome math and horizon maturation.
- `opportunity_learning.py` — historical expectancy, shrinkage-oriented sample confidence, chronological walk-forward, baseline status, daily/weekly reports.
- `opportunity_ui.py` — dense dashboard UI.
- `app.py` — additive integration; original core remains.

## Important non-claims
- Full exchange enumeration is not yet bundled; automatic scanning covers the configured universe plus the existing adaptive scenario/news discovery path.
- Historical analyst/sector/ownership PIT datasets are still required before claiming production-grade long-history recall across every market.
- Fresh v3.2 installs have no mature longitudinal outcomes by definition. The system must accumulate them prospectively or ingest properly reconstructed PIT events.
