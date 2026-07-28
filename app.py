"""
War Room — entry point.  Run:  streamlit run app.py

Architecture:
  • Design + ranking  = mine (warroom/render.py, warroom/compute.py) — verdict-first mockup.
  • Formula engines   = your zip (engines/, gcfis/) called as providers: Hedgeye GIP (structural+
    monthly), Hedgeye Risk Range, GEX/greeks, methodology (Citrini/Yves/Soros/Coatue/Druck via
    thought_process), lead-lag (Granger+TE) + supply-chain-graph for propagation, value-based LPM.
  • NO old UI, NO old ticker-filter/elimination pipeline.
Data: parquet cache (build_cache.py) → yfinance live → honest NO_DATA/STALE states.
No synthetic production output (R2 data contract; test fixtures behind WARROOM_DATA_TEST_FIXTURE=1).
Set WARROOM_OFFLINE=1 to disable live fetching (cache-only mode). FRED via fredgraph (no key).
"""
import streamlit as st
from warroom import data as D, compute as C, render as R, fred as F, feeds as FEEDS, tracker as TR, statelog as SL
from warroom import brief_export as BE


def main():
    st.set_page_config(page_title="War Room", layout="wide", initial_sidebar_state="collapsed")
    with st.spinner("Loading prices + running engines…"):
        us, source = D.load(D.US_UNIVERSE)
        idx, _ = D.load(D.IDX_UNIVERSE)
        cp, _ = D.load(D.CRYPTO_UNIVERSE)
        fxp, _ = D.load(D.FX_UNIVERSE)
        commo, _ = D.load(D.COMMO_UNIVERSE)
        feeds = FEEDS.load_feeds()                     # live-feed snapshot (build_feeds.py); empty = proxy
        fred = feeds.get("fred") or F.fetch()
        d = C.run(us, idx, cp, fxp, commo, fred, feeds)
        # forward-test logger: log today's conviction point-in-time, then resolve open signals on later bars
        # R7.1: conviction now contains ONLY proof-gated candidates (currently none); legacy
        # momentum-scan rows can no longer enter the prospective signal DB.
        allpx = {**commo, **fxp, **cp, **idx, **us}
        try:
            TR.log_signals(d["conviction"], d["regime"])
            TR.update_outcomes(allpx)
        except Exception:
            pass
        try:
            d["whatchanged"], d["whatchanged_prev_ts"] = SL.record_and_diff(d)
        except Exception:
            d["whatchanged"], d["whatchanged_prev_ts"] = [], None
        try:
            BE.export(d)   # regenerate the interactive briefing deck (briefing.html) with today's data
        except Exception:
            pass
    # R4 final design: 17 original tabs consolidated to 11 — every original render
    # function is still invoked exactly once (parity by construction; see
    # docs/audit/PRESERVATION_MATRIX.md and tests/test_r4_consolidation.py).
    # No formulas changed; sections are composed, not rewritten.
    tabs = st.tabs(["Mission Control", "Macro & Regime", "Alpha Center", "US Stocks",
                    "Crypto", "Commodities", "FX", "IHSG", "Flow & Bottleneck",
                    "Rotation & Chains", "Portfolio & Proof"])
    with tabs[0]:  # was: Mission Control + Morning Brief + Briefing + Command Center
        R.mission_control(d)
        st.divider()
        R.morning_brief(d)
        st.divider()
        R.command_center(d, source)
        st.divider()
        R.briefing_embed()
    with tabs[1]: R.market_state(d)          # was: Market State
    with tabs[2]: R.alpha(d)                 # unchanged
    with tabs[3]:                            # unchanged
        R.us_stocks(d)
        R.fair_value_cards(d)
    with tabs[4]: R.crypto(d)
    with tabs[5]: R.commodities(d)
    with tabs[6]: R.fx(d)
    with tabs[7]: R.ihsg(d)
    with tabs[8]:                            # was: Flow + Bottleneck
        R.flow(d)
        st.divider()
        R.bottleneck(d)
        R.node_template(d)
    with tabs[9]:                            # was: Cross-Asset Rotation + Causal Chains
        R.cycle_rotation(d)
        st.divider()
        R.causal_chains(d)
    with tabs[10]:                           # was: Track Record + Risk & Health
        R.track_record(TR.performance(), TR.open_positions(), TR.closed_trades())
        st.divider()
        R.validation_tab(d)
        st.divider()
        R.risk_health(d)
        st.divider()
        R.early_warning_tab(d)


if __name__ == "__main__":
    main()
