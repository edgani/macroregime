"""EROS / Warroom Streamlit application.

Run:
    streamlit run app.py

This is the active UI. The original Warroom source is preserved under
legacy_warroom_original/ but is NOT imported into production because legacy
price-derived directional paths are quarantined.
"""
from __future__ import annotations
from pathlib import Path
import json
import pandas as pd

try:
    import streamlit as st
except ImportError as exc:
    raise SystemExit("Streamlit belum ter-install. Jalankan run_eros.bat atau: py -m pip install -r requirements.txt") from exc

from final_core.app_model import load_app_state
from final_core.event_router import route
from final_core.production_entry import run as run_production
from final_core.build_dashboard import build_dashboard

ROOT = Path(__file__).resolve().parent
CURRENT = ROOT / "data" / "current"
CURRENT.mkdir(parents=True, exist_ok=True)

st.set_page_config(page_title="EROS Warroom", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp{background:#090d13;color:#e8edf5}.block-container{max-width:1600px;padding-top:1.2rem}
[data-testid="stSidebar"]{background:#0d131d}.eros-card{background:#111823;border:1px solid #273348;border-radius:12px;padding:14px;margin:8px 0}
.small-muted{color:#8f9bae;font-size:.86rem}.stTabs [data-baseweb="tab-list"]{gap:8px}.stTabs [data-baseweb="tab"]{background:#111823;border-radius:8px;padding:8px 14px}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def get_state(_nonce: int = 0):
    return load_app_state(run_engine=False)

if "nonce" not in st.session_state:
    st.session_state.nonce = 0

with st.sidebar:
    st.title("EROS · WARROOM")
    st.caption("Evidence → Scenario → Asset → Ticker → EV. Fail-closed by design.")
    if st.button("▶ Run / Refresh EROS", use_container_width=True):
        with st.spinner("Running EROS..."):
            run_production()
            build_dashboard()
        st.session_state.nonce += 1
        st.rerun()
    if st.button("↻ Reload artifacts", use_container_width=True):
        st.session_state.nonce += 1
        st.rerun()
    st.divider()
    st.caption("Ticker output is intentionally blocked unless company mechanism, PIT fundamentals, calibration, priced-in and EV gates are present.")

state = get_state(st.session_state.nonce)
r = state["run"]
summ = state["validation_summary"]
strict = state["strict"]

st.title("EROS Warroom")
st.caption("Runnable successor to the original Warroom app.py. Legacy code is preserved but quarantined from the active production path.")

c1,c2,c3,c4,c5 = st.columns(5)
c1.metric("System", r.get("system_status","UNKNOWN"))
c2.metric("Action", r.get("current_action","UNKNOWN"))
c3.metric("Scenarios", r.get("scenario_count",0))
c4.metric("Scientific engines", summ.get("engine_count",0))
c5.metric("Production-proven", summ.get("production_proven_count",0))

cmd,glob,opp,port,lab = st.tabs(["Command Center","Global Explorer","Opportunity Engine","Portfolio","Research Lab"])

with cmd:
    st.subheader("Current scenario map")
    scenarios = r.get("scenarios", [])
    if not scenarios:
        st.info("No verified scenario available.")
    for sc in scenarios:
        with st.expander(f"{sc.get('scenario_id','SCENARIO')} · {sc.get('title','')}", expanded=False):
            st.write(" → ".join(sc.get("causal_chain",[])))
            a,b,c = st.columns(3)
            a.write(f"**Probability:** {sc.get('probability_status','UNKNOWN')}")
            b.write(f"**Timing:** {sc.get('timing','UNKNOWN')}")
            c.write(f"**Duration:** {sc.get('duration','UNKNOWN')}")
            st.write("**Confirm:**", ", ".join(sc.get("confirming_evidence",[])) or "—")
            st.write("**Contradict:**", ", ".join(sc.get("contradicting_evidence",[])) or "—")
            st.write("**Next data:**", ", ".join(sc.get("next_discriminating_data",[])) or "—")
            st.caption(sc.get("caveat", ""))
    st.subheader("Claim / headline triage")
    claim = st.text_area("Paste headline / observation", placeholder="Example: data-center debt issuance rises while spreads widen...")
    if claim:
        st.json(route(claim))
        st.warning("Router only creates verification candidates. It does NOT turn an unverified headline directly into a trade.")

with glob:
    st.subheader("Verified evidence")
    st.dataframe(pd.DataFrame(state["evidence"]), use_container_width=True, hide_index=True)
    st.subheader("Scenario registry")
    st.dataframe(pd.DataFrame(r.get("scenarios",[])), use_container_width=True, hide_index=True)
    st.subheader("Metric master registry")
    st.dataframe(state["metric_registry"], use_container_width=True, hide_index=True)
    st.subheader("Factual-data coverage")
    st.dataframe(state["data_coverage"], use_container_width=True, hide_index=True)

with opp:
    st.subheader("Asset transmission candidates")
    assets = pd.DataFrame(r.get("asset_candidates",[]))
    if assets.empty: st.info("No asset candidate passed scenario routing.")
    else: st.dataframe(assets, use_container_width=True, hide_index=True)
    st.subheader("Ticker qualification")
    td = pd.DataFrame(r.get("ticker_decisions",[]))
    if td.empty: st.info("No ticker has factual calibrated company inputs yet. This is fail-closed, not an app error.")
    else: st.dataframe(td, use_container_width=True, hide_index=True)
    st.subheader("Qualified opportunities")
    qo = pd.DataFrame(r.get("qualified_opportunities",[]))
    if qo.empty: st.warning("NO QUALIFIED OPPORTUNITY")
    else: st.dataframe(qo, use_container_width=True, hide_index=True)
    st.divider()
    st.markdown("**Optional company-input loader**")
    uploaded = st.file_uploader("Upload factual/calibrated company_inputs.json", type=["json"], key="company")
    if uploaded is not None:
        try:
            rows = json.load(uploaded)
            if not isinstance(rows, list): raise ValueError("Root JSON must be a list of company rows")
            st.dataframe(pd.DataFrame(rows), use_container_width=True)
            if st.button("Save company inputs & rerun", type="primary"):
                (CURRENT / "company_inputs.json").write_text(json.dumps(rows,indent=2), encoding="utf-8")
                run_production(company_input_path=CURRENT / "company_inputs.json")
                build_dashboard(); st.session_state.nonce += 1; st.rerun()
        except Exception as e:
            st.error(f"Invalid company_inputs.json: {e}")

with port:
    st.subheader("Portfolio")
    qo = r.get("qualified_opportunities",[])
    if not qo:
        st.warning("Portfolio remains WAIT / CASH-ELIGIBLE because no opportunity passes the full ticker + EV gates.")
    else:
        st.dataframe(pd.DataFrame(qo), use_container_width=True, hide_index=True)
    st.caption("No portfolio sizing is fabricated when calibrated correlations, costs, capacity and risk inputs are missing.")

with lab:
    st.subheader("Strict acceptance")
    st.json(strict)
    st.subheader("Validation summary")
    st.json(summ)
    st.subheader("GMIS")
    st.dataframe(state["gmis"], use_container_width=True, hide_index=True)
    st.subheader("Experiment ledger")
    st.dataframe(state["experiment_ledger"], use_container_width=True, hide_index=True)
    st.subheader("Engine registry")
    st.dataframe(state["engine_registry"], use_container_width=True, hide_index=True)
    st.subheader("Rejected opportunities")
    st.dataframe(state["rejected"], use_container_width=True, hide_index=True)
    st.download_button("Download current production JSON", data=json.dumps(r,indent=2), file_name="EROS_current_production_run.json", mime="application/json")
