
from __future__ import annotations
from pathlib import Path
import numpy as np,pandas as pd,streamlit as st
from config.metric_registry_v4 import METRIC_FAMILIES
from data_layer_v4 import build_data_bundle,load_universes,strict_prices
from providers.options_public import snapshot as option_snapshot
from engines.state_engine import current_state
from engines.scenario_engine import live_evidence,catalog as scenario_catalog,research_evidence
from engines.thesis_engine import lifecycle,coherent_probability_check
from engines.crash_engine import crash_matrix,crash_conclusion
from engines.projection_engine import analog_distribution,walkforward_calibration
from engines.cross_market_engine import mechanism_table,empirical_sensitivities,bottleneck_matrix
from engines.bottleneck_engine import investigate
from engines.opportunity_engine import OBJECTIVES
from engines.runway_engine import remaining_runway
from engines.experiment_registry import load_experiments,load_failures,load_search_ledger,load_governance_overrides,proof_summary
HERE=Path(__file__).resolve().parent
st.set_page_config(page_title='Macro Decision OS v4',page_icon='◈',layout='wide')
st.title('Macro Trading Framework — Causal Decision OS v4')
st.caption('Mechanism-first · no technical-analysis alpha · fail-closed data · competing scenarios · NO TRADE is first-class')
objective=st.sidebar.selectbox('Objective',OBJECTIVES);markets=st.sidebar.multiselect('Markets',['us','idx','crypto','commodity','fx'],default=['us','idx','crypto','commodity','fx']);cap=st.sidebar.slider('Live symbols per market',5,35,20,5);special=st.sidebar.toggle('Fetch specialized public feeds',True)
if st.sidebar.button('Refresh'):st.cache_data.clear();st.rerun()
st.sidebar.caption('Price is limited to outcome labels, valuation/execution/risk, market-implied context and accounting. ATH remains research-only.')
@st.cache_data(ttl=1800,show_spinner=False)
def load(m,c,s):return build_data_bundle(m,c,s)
with st.spinner('Loading strict public/live data…'):bundle=load(markets,cap,special)
state=current_state(bundle);fred=bundle['fred'];lineage=bundle['lineage'];flat={}
for d in bundle['prices'].values():flat.update(d)
C=st.columns(6);C[0].metric('Metric families',len(METRIC_FAMILIES));C[1].metric('FRED loaded',len(fred));C[2].metric('Objective',objective);C[3].metric('Treasury feed',bundle['treasury'].get('status'));C[4].metric('Crypto-native',bundle['crypto_native'].get('status'));C[5].metric('Synthetic fallback','NONE')
T=st.tabs(['Current State','Thesis Lifecycle','Crash Engine','Scenario Lab','Cross-Market / Bottlenecks','Forward Distribution','Bottleneck / Winners','Options Context','Proof / Experiments','Data Lineage','System Check'])

def f(x,pct=False):
    try:return ('{:.1%}' if pct else '{:.4f}').format(float(x)) if np.isfinite(float(x)) else 'N/A'
    except:return 'N/A'
with T[0]:
    st.subheader('CURRENT STATE — observable evidence, not a trade map')
    for eng,vals in state.items():
        st.markdown('#### '+eng);st.dataframe(pd.DataFrame([{'metric':k,'value':v} for k,v in vals.items()]),hide_index=True,use_container_width=True)
    st.info('No regime→asset mapping. State variables only condition falsifiable mechanisms and scenario evidence.')
with T[1]:
    st.subheader('THESIS LIFECYCLE — Base / Competing / Tail / Null')
    d=lifecycle(state);ok,msg=coherent_probability_check(d);st.dataframe(d,use_container_width=True,hide_index=True);st.warning(msg)
    st.markdown('A thesis can remain **true but fully priced**; that is different from the thesis becoming false. Numerical probability stays unavailable until a current-compatible calibrated model exists.')
with T[2]:
    st.subheader('CRASH — FRAGILITY → EARLY WARNING → ACUTE TRIGGER → SEVERITY → RECOVERY')
    st.dataframe(crash_matrix(state),use_container_width=True,hide_index=True);st.json(crash_conclusion(state));st.caption('No composite crash score. Ordinary correction and systemic event remain separate mechanisms.')
with T[3]:
    st.subheader('SCENARIO LAB')
    st.markdown('#### Live competing evidence');st.dataframe(live_evidence(state),use_container_width=True,hide_index=True)
    st.markdown('#### Candidate scenario library');st.dataframe(scenario_catalog(),use_container_width=True,hide_index=True,height=450)
    re=research_evidence()
    if len(re):st.markdown('#### Existing research evidence');st.dataframe(re,use_container_width=True,hide_index=True,height=300)
with T[4]:
    st.subheader('CROSS-MARKET TRANSMISSION + CANDIDATE BOTTLENECKS');st.dataframe(mechanism_table(),use_container_width=True,hide_index=True);st.dataframe(bottleneck_matrix(state),use_container_width=True,hide_index=True)
    if st.toggle('Show empirical macro-response associations (research only)',False):
        z=empirical_sensitivities(fred,flat);st.dataframe(z,use_container_width=True,hide_index=True);st.warning('Associations use price as a forward outcome. Sign stability does not establish causality or a trade.')
with T[5]:
    st.subheader('FORWARD DISTRIBUTION — historical analog outcome research');sym=st.text_input('Instrument','IWM',key='proj').upper().strip();k=st.slider('Macro analogs',8,40,20,key='k')
    px=flat.get(sym)
    if px is None and st.button('Fetch instrument',key='fetchproj'):
        p,_=strict_prices([sym]);px=p.get(sym);st.session_state['extra_px']=(sym,px)
    if st.session_state.get('extra_px',(None,None))[0]==sym:px=st.session_state['extra_px'][1]
    if px is not None:
        stats,a,meta=analog_distribution(fred,px,k);st.json(meta)
        if len(stats):
            s=stats.copy()
            for c in ['p_positive','p_gt25','p_gt50','p_gt100','p_loss10','p10','median','p90']:s[c]=s[c].map(lambda z:f'{z:.1%}')
            st.dataframe(s,use_container_width=True,hide_index=True)
        if st.button('Run temporal walk-forward reliability check'):
            cal,cm=walkforward_calibration(fred,px,k);st.session_state['cal']=(cal,cm)
        if 'cal' in st.session_state:
            cal,cm=st.session_state['cal'];st.json(cm);st.dataframe(cal,use_container_width=True,hide_index=True)
    else:st.info('Price unavailable; no synthetic substitute.')
    st.warning('Even a good walk-forward result here remains revision-unsafe until macro vintages are point-in-time safe.')
with T[6]:
    st.subheader('BOTTLENECK / WINNER-LOSER ENGINE');st.write('Required chain: binding constraint → company-specific capture → monetization → pricing gap → catalyst → clean instrument expression.')
    txt=st.text_input('US candidates','SNDK, PLTR, GNRC, MOD, POWL')
    if st.button('Investigate SEC evidence',type='primary'):
        t=[x.strip().upper() for x in txt.split(',') if x.strip()][:10]
        with st.spinner('Reading SEC filings + filed-date Company Facts…'):df,det=investigate(t)
        st.session_state['bdf']=df;st.session_state['bdet']=det
    df=st.session_state.get('bdf');det=st.session_state.get('bdet',{})
    if isinstance(df,pd.DataFrame) and len(df):
        st.dataframe(df,use_container_width=True,hide_index=True);pick=st.selectbox('Inspect candidate',df.ticker.tolist());d=det[pick];st.write('**Evidence interpretation:** '+d['reason']);st.json(d['chain']);st.write('**Competing thesis:** '+d['competing_thesis']);st.write('**Action:** '+d['action']+' — '+d['action_reason']);st.markdown('**Kill switches**');[st.write('- '+x) for x in d['kill_switches']];st.json(remaining_runway())
        with st.expander('SEC evidence snippets'):
            for x in d['filing'].get('snippets',[]):st.write(f"**{x['group']} / {x['term']}** — {x['snippet']}")
    st.caption('Previous winners may re-enter after a correction only if mechanism + pricing + remaining payoff reopen. Drawdown alone never qualifies a reload.')
with T[7]:
    st.subheader('OPTIONS CONTEXT — instrument-specific, not universal macro alpha');osym=st.text_input('Optionable instrument','SPY').upper().strip()
    if st.button('Fetch options snapshot'):
        with st.spinner('Loading current option chain…'):st.session_state['opt']=option_snapshot(osym)
    if 'opt' in st.session_state:st.json(st.session_state['opt'])
    st.caption('No GEX directional claim. Current IV/skew/OI can condition execution/risk; historical PIT calibration remains data-gated.')
with T[8]:
    st.subheader('PROOF / EXPERIMENT REGISTRY');st.dataframe(proof_summary(),use_container_width=True,hide_index=True);st.markdown('### Experiments');st.dataframe(load_experiments(),use_container_width=True,hide_index=True,height=430);st.markdown('### Failure library');st.dataframe(load_failures(),use_container_width=True,hide_index=True);st.markdown('### Governance overrides');st.dataframe(load_governance_overrides(),use_container_width=True,hide_index=True);st.markdown('### Search ledger');st.dataframe(load_search_ledger(),use_container_width=True,hide_index=True)
    st.error('A unit test, attractive chart or LLM agreement never sets PROVEN. Final proof needs PIT/vintage-safe data, temporal OOS, frozen holdout, matched/negative controls, multiple-testing accounting, calibration and ablation.')
with T[9]:
    st.subheader('DATA LINEAGE / FAIL-CLOSED');st.dataframe(lineage,use_container_width=True,hide_index=True,height=520);st.markdown('### FRED failures');st.json(bundle['fred_errors']);st.markdown('### Critical gaps');[st.write('- '+x) for x in bundle['data_gaps']];st.warning('Latest/revised macro history is explicitly not point-in-time. It is monitoring/research data, not final historical proof.')
with T[10]:
    st.subheader('SYSTEM CHECK');st.write('Metric registry:',len(METRIC_FAMILIES),'families');st.write('Synthetic fallback: **NONE**');st.write('Scenario probabilities: **fail-closed unless calibrated**');st.write('Classic TA production features: **NONE**');st.write('Opportunity default when pricing/catalyst/runway unavailable: **NO TRADE**');st.write('Specialized public feed status:',{'Treasury':bundle['treasury'].get('status'),'CryptoNative':bundle['crypto_native'].get('status')});cp=HERE/'research'/'spec_compliance_v4.csv';st.markdown('### Spec compliance');st.dataframe(pd.read_csv(cp),use_container_width=True,hide_index=True) if cp.exists() else None
st.divider();st.caption('v4 — metric → mechanism → competing scenario → pricing/crowding → opportunity → instrument. Missing critical evidence lowers confidence or returns NO TRADE; it never becomes a fabricated neutral value.')
