# Macro Decision OS v5 — Visual Decision Board

V5 keeps the v4 mechanism-first / fail-closed research architecture but replaces the 11-tab UI with four screens:

1. **Dashboard** — live states, percentile heatmap, standardized shocks, competing thesis cards, crash mechanism.
2. **Scenarios & Relationships** — scenario evidence balance, macro↔macro and macro↔asset correlation matrices, relationship explorer.
3. **Opportunities** — cross-market bottleneck board, SEC company evidence, forward outcome context, options execution context.
4. **Research & Data** — proof registry, failures, lineage, data gaps and compliance.

## Important FRED cloud fix
V4 used anonymous `fredgraph.csv`, which can return zero series on Streamlit Cloud. V5 tries real sources in this order:

1. FRED API when `FRED_API_KEY` is available in Streamlit Secrets/environment.
2. FRED fredgraph CSV.
3. DBnomics FRED mirror.

There is **no synthetic macro fallback**.

For Streamlit Cloud, add this secret for the most reliable route:

```toml
FRED_API_KEY="your_fred_api_key"
```

## Deploy
Upload the entire project, install `requirements.txt`, and keep main file path as `app.py`.

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Research warning
Correlation matrices are explicitly association/research panels. They do not create fixed macro→asset sign rules. Latest/revised macro history is not final PIT proof.


## v5.2 UX
Every decision chart exposes READ → DO → NEXT. Opportunities use a payoff/downside Pareto frontier and a company gate funnel instead of an opaque score.
