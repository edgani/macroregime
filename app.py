
from __future__ import annotations
from pathlib import Path
import numpy as np,pandas as pd,streamlit as st
from config.metric_registry_v3 import METRIC_FAMILIES
from data_layer_v3 import build_data_bundle,load_universes,strict_prices
from engines.state_engine import current_state
from engines.thesis_engine import lifecycle,coherent_probability_check
from engines.crash_engine import crash_matrix,crash_conclusion
from engines.projection_engine import analog_distribution,interval_calibration_stub
from engines.cross_market_engine import mechanism_table,empirical_sensitivities
from engines.bottleneck_engine import investigate
from engines.opportunity_engine import OBJECTIVES
from engines.runway_engine import remaining_runway
from engines.experiment_registry import load_experiments,load_failures,load_search_ledger,proof_summary
HERE=Path(__file__).resolve().parent
st.set_page_config(page_title='Macro Decision OS v3',page_icon='◈',layout='wide')
st.title('Macro Trading Framework — Causal Decision OS v3')
st.caption('No technical-analysis alpha · mechanism-first · competing scenarios · fail-closed data · NO TRADE is first-class')
objective=st.sidebar.selectbox('Objective',OBJECTIVES)
markets=st.sidebar.multiselect('Markets',['us','idx','crypto','commodity','fx'],default=['us','idx','crypto','commodity','fx'])
cap=st.sidebar.slider('Live symbols per market',5,35,20,5)
if st.sidebar.button('Refresh'):st.cache_data.clear();st.rerun()
st.sidebar.caption('Price is not used as a macro regime classifier. ATH/price-state research lives only in Experiment Registry.')
@st.cache_data(ttl=1800,show_spinner=False)
def load(m,c):return build_data_bundle(m,c)
with st.spinner('Loading strict real/public data…'):bundle=load(markets,cap)
fred=bundle['fred'];state=current_state(fred)
lineage=bundle['lineage']
cols=st.columns(5);cols[0].metric('Metric families',len(METRIC_FAMILIES));cols[1].metric('FRED loaded',len(fred));cols[2].metric('Objective',objective);cols[3].metric('Synthetic fallback','NONE');cols[4].metric('Trade default','NO TRADE')
T=st.tabs(['Current State','Thesis Lifecycle','Crash Engine','Cross-Market','Forward Distribution','Bottleneck / Winners','Experiment Registry','Proof / Multiple Testing','Data Lineage'])

def f(x,pct=False):
    try:return ('{:.1%}' if pct else '{:.3f}').format(float(x)) if np.isfinite(float(x)) else 'N/A'
    except:return 'N/A'
with T[0]:
    st.subheader('CURRENT STATE — economic / market-implied evidence, not TA')
    for engine,vals in state.items():
        if engine=='percentiles':continue
        st.markdown('#### '+engine)
        if isinstance(vals,dict):st.dataframe(pd.DataFrame([{'metric':k,'value':v} for k,v in vals.items()]),hide_index=True,use_container_width=True)
    st.info('No regime→asset mapping is applied. Current state only feeds falsifiable mechanisms and scenario evidence.')
with T[1]:
    st.subheader('COMPETING SCENARIOS + NULL')
    life=lifecycle(state);ok,msg=coherent_probability_check(life)
    st.dataframe(life,use_container_width=True,hide_index=True)
    st.warning(msg if not ok else msg)
    st.markdown('**Rule:** probability stays DATA_GATED rather than receiving an arbitrary confidence number. A thesis can remain true yet become untradeable when pricing/crowding consumes the payoff.')
with T[2]:
    st.subheader('CRASH: FRAGILITY → EARLY WARNING → ACUTE TRIGGER → SEVERITY → RECOVERY')
    st.dataframe(crash_matrix(state),use_container_width=True,hide_index=True)
    st.json(crash_conclusion(state))
    st.caption('ATH is not a crash input in production. ATH experiments remain research-only and require episode/OOS validation.')
with T[3]:
    st.subheader('CROSS-MARKET CAUSAL TRANSMISSION')
    st.dataframe(mechanism_table(),use_container_width=True,hide_index=True)
    flat={}
    for d in bundle['prices'].values():flat.update(d)
    if st.toggle('Show empirical response associations (research only)',False):
        s=empirical_sensitivities(fred,flat);st.dataframe(s,use_container_width=True,hide_index=True)
        st.warning('These betas/correlations use price only as a forward outcome. They are empirical corroboration, not causal proof or a trade mapping.')
with T[4]:
    st.subheader('FORWARD DISTRIBUTION — outcome-label research')
    sym=st.text_input('Instrument','IWM').upper().strip();k=st.slider('Macro analogs',8,40,20)
    flat={}
    for d in bundle['prices'].values():flat.update(d)
    px=flat.get(sym)
    if px is None and st.button('Fetch instrument'):
        p,_=strict_prices([sym]);px=p.get(sym);st.session_state['px']=(sym,px)
    if st.session_state.get('px',(None,None))[0]==sym:px=st.session_state['px'][1]
    if px is not None:
        stats,a,meta=analog_distribution(fred,px,k);st.json(meta)
        if len(stats):
            show=stats.copy()
            for c in ['p_positive','p_gt25','p_gt50','p_gt100','p_loss10','p10','median','p90']:show[c]=show[c].map(lambda z:f'{z:.1%}')
            st.dataframe(show,use_container_width=True,hide_index=True)
            st.warning('P(+25/+50/+100) here is historical-analog context, NOT calibrated RemainingRunway.')
    else:st.info('Price series unavailable. No synthetic substitute is used.')
    st.json(interval_calibration_stub())
with T[5]:
    st.subheader('BOTTLENECK / WINNER-LOSER ENGINE')
    st.write('A bottleneck is not a buy reason by itself. Required chain: constraint → specific capture → monetization → pricing gap → catalyst → trade expression.')
    default='SNDK, PLTR, GNRC, MOD, POWL';txt=st.text_input('US candidates to investigate',default)
    if st.button('Investigate filing evidence',type='primary'):
        t=[x.strip().upper() for x in txt.split(',') if x.strip()][:10]
        with st.spinner('Reading SEC evidence and current fundamentals…'):df,det=investigate(t)
        st.session_state['bdf']=df;st.session_state['bdet']=det
    df=st.session_state.get('bdf');det=st.session_state.get('bdet',{})
    if isinstance(df,pd.DataFrame) and len(df):
        st.dataframe(df,use_container_width=True,hide_index=True)
        pick=st.selectbox('Inspect',df.ticker.tolist());d=det[pick]
        st.markdown('**Dominant causal evidence**');st.json(d['chain']);st.write('**Competing thesis:** '+d['competing_thesis']);st.write('**Action:** '+d['action']+' — '+d['action_reason'])
        st.markdown('**Kill switches**');[st.write('- '+x) for x in d['kill_switches']]
        st.json(remaining_runway())
        with st.expander('SEC evidence snippets'):
            for x in d['filing'].get('snippets',[]):st.write(f"**{x['group']} / {x['term']}** — {x['snippet']}")
    st.caption('Previous winners are not blacklisted. A reload can qualify only after pricing/runway is recalibrated; drawdown alone is not a reload signal.')
with T[6]:
    st.subheader('EXPERIMENT REGISTRY — every claim is an experiment')
    st.dataframe(load_experiments(),use_container_width=True,hide_index=True,height=520)
    st.markdown('### Failure library');st.dataframe(load_failures(),use_container_width=True,hide_index=True)
with T[7]:
    st.subheader('PROOF + MULTIPLE-TESTING DEFENSE')
    st.dataframe(proof_summary(),use_container_width=True,hide_index=True)
    st.dataframe(load_search_ledger(),use_container_width=True,hide_index=True)
    for fn,label in [('scenario_validation_results_v2.csv','Macro scenario tests'),('price_state_validation_results_v2.csv','Price-state experiments — research only'),('metric_validation_results_v2.csv','Metric placement tests')]:
        p=HERE/'research'/fn
        if p.exists():st.markdown('#### '+label);st.dataframe(pd.read_csv(p),use_container_width=True,hide_index=True,height=260)
    st.error('Unit tests, Monte Carlo, a nice chart, or LLM agreement never set status=PROVEN. Final proof requires PIT/vintage-safe data, OOS, untouched holdout, controls, calibration and search-process accounting.')
with T[8]:
    st.subheader('DATA LINEAGE / FAIL-CLOSED')
    st.dataframe(lineage,use_container_width=True,hide_index=True,height=500)
    st.markdown('### Critical gaps');[st.write('- '+x) for x in bundle['data_gaps']]
    st.warning('Latest/revised FRED history is explicitly marked NOT_PRESERVED vintage. It is acceptable for live monitoring/exploration, not final historical proof.')
st.divider();st.caption('v3: mechanism before correlation; thesis before instrument; pricing before action; missing evidence => lower confidence or NO TRADE, never fabricated neutrality.')
