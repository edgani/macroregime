# War Room OS — Capital Intelligence Map / Full Live Intelligence v2

A multi-market decision system with explicit live-data lineage, derivatives/option context, institutional event feeds and fail-closed rendering.

Start with:

- `START_HERE.md`
- `LIVE_DATA_ACTIVATION.md`
- `.env.example`
- `DATA_REQUIREMENTS_MATRIX.json`
- `SQUEEZE_OPTIONS_SEMANTICS.md`

Run:

```bash
python validate_live_stack.py
python validate_redesign.py
python verify_live_connections.py --strict --write-report
streamlit run app.py
```

No production component is permitted to replace missing data with synthetic observations.
