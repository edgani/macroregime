# v5.1 hotfix

- Fixed Relationship Explorer crash when macro series DatetimeIndex is named `DATE`, `observation_date`, or another non-`index` name.
- Normalizes scatter index to a `date` column before Plotly Express.
- Coerces factor/forward-return values to numeric and drops non-finite observations.
- Adds chart-level fail-soft guard so a visualization error does not crash the whole Streamlit page.
- No changes to causal/model governance or signal logic.
