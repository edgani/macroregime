# Logic Audit

The maintained regression suite covers episode immutability and renewal, point-in-time bar availability, weekend/holiday horizon selection, benchmark/sector unknown handling, chronological label-mature walk-forward folds, sample shrinkage, continuous path outcomes, capture/valuation/readiness gates, independent expression gating, prospective baselines and runner cohorts, evidence deduplication, and market-specific readiness.

Last dependency-complete result: `tests/run_all.py` passed 28/28 under Python 3.12. The cleanup-environment rerun reached 8/28, with the remaining 20 suites unable to import the declared `numpy`/`pandas` dependencies; the static, visual, navigation, deep-link, baseline/evidence, cockpit, and release-packaging contracts passed. This establishes implementation-level logic verification, not production alpha, complete point-in-time vendor coverage, survivorship-safe history, or out-of-sample superiority.

Browser automation is intentionally separate in `tests/browser_smoke.py`; it must run against a live Streamlit server in an environment allowed to launch Chromium.
