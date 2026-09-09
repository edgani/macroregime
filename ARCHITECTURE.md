# Architecture

Macroregime is a research-only Streamlit application. `app.py` owns the single product shell and composes the macro engine, market adapters, discovery, causal scoring, longitudinal memory, forward outcomes, prospective baselines, and learning/replay modules.

The data flow is:

`observations -> availability-aware change detection -> theme and bottleneck mapping -> beneficiary/value-capture gates -> expectation and expression gates -> ranked candidates -> immutable episodes -> matured outcomes -> chronological calibration`

SQLite-backed state is runtime-only and excluded from source control. Production weights are fixed; learning reports expectancy and confidence without self-modifying ranking logic.

Five stable routes are exposed through `?route=CONTROL_ROOM`, `OPPORTUNITIES`, `VERTICALS`, `MACRO_EVENTS`, and `LEARNING_REPLAY`.
