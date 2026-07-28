"""War Room OS V10.1 Streamlit shell for operational research and shadow trading."""
from __future__ import annotations
import json, os, sys, threading
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE))
import streamlit as st
import streamlit.components.v1 as components
from run import build_desk
from runtime_store import read_snapshot,write_snapshot,write_status
from warroom.no_technical_policy import assert_registry_has_no_active_technical_components,enforce_payload
DASHBOARD=HERE/'dashboard.html'
st.set_page_config(page_title='War Room OS V10.1 Operational Trading System',layout='wide',initial_sidebar_state='collapsed')
st.markdown("""<style>.stApp{background:#050811}header[data-testid="stHeader"]{display:none}.block-container{padding:0!important;max-width:100%!important}#MainMenu,footer,[data-testid="stToolbar"]{display:none!important}</style>""",unsafe_allow_html=True)

def _empty_data()->dict:
    markets=['us','idx','crypto','commodity','fx']
    return {'markets':markets,'fred':{},'fred_source':'NO_DATA','feeds':{'_status':{}},'quotes':{'markets':{m:{} for m in markets}},'public_sources':{'markets':{m:{'state':'ROUTE_ONLY','items':[],'valid_items':0} for m in markets},'markets_with_real_snapshot':0},'universe_summary':{},'sources':{},'overall_source':'INITIALIZING'}

def _seed_snapshot()->dict:
    registry=json.loads((HERE/'component_registry_v99.json').read_text(encoding='utf-8'));assert_registry_has_no_active_technical_components(registry)
    import data_layer_v101 as DL
    snapshot=build_desk(DL.load_all(markets=['us','idx','crypto','commodity','fx'],allow_live=False,allow_synthetic=False));enforce_payload(snapshot);return snapshot

def _worker()->None:
    try:
        from warroom_data_worker_v101 import loop
        loop()
    except BaseException as exc:write_status(state='WORKER_FATAL',error=f'{type(exc).__name__}: {exc}',capital_permission='PROOF_GATED')
@st.cache_resource(show_spinner=False)
def _start_worker()->threading.Thread|None:
    if os.getenv('WARROOM_DISABLE_AUTOSTART','0').lower() in {'1','true','yes'}:return None
    thread=threading.Thread(target=_worker,name='warroom-v101-data-worker',daemon=True);thread.start();return thread
if read_snapshot() is None:write_snapshot(_seed_snapshot(),force=True)
_start_worker();snapshot=read_snapshot() or _seed_snapshot();enforce_payload(snapshot)
payload=json.dumps(snapshot,default=str,separators=(',',':'),ensure_ascii=False).replace('</','<\\/')
html=DASHBOARD.read_text(encoding='utf-8').replace('/*__INJECT_DATA__*/',f'window.DASHBOARD_DATA={payload};',1)
components.html(html,height=1320,scrolling=True)
