from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config.metric_registry_v4 import METRIC_FAMILIES
from data_layer_v4 import build_data_bundle, strict_prices
from providers.options_public import snapshot as option_snapshot
from engines.state_engine import current_state
from engines.scenario_engine import live_evidence
from engines.crash_engine import crash_matrix, crash_conclusion
from engines.projection_engine import analog_distribution, walkforward_calibration, opportunity_radar, normalized_projection_path
from engines.cross_market_engine import bottleneck_matrix, empirical_sensitivities
from engines.bottleneck_engine import investigate
from engines.opportunity_engine import OBJECTIVES
from engines.experiment_registry import (
    load_experiments, load_failures, load_search_ledger,
    load_governance_overrides, proof_summary,
)
from engines.visual_engine import (
    headline_states, percentile_strip, standardized_shocks,
    macro_correlation, macro_asset_relationships, relationship_scatter,
    bundled_longrun_correlation,
)
from engines.decision_engine import (
    operational_posture, heatmap_guidance, shock_guidance,
    scenario_guidance, projection_guidance, company_gate_guidance,
)

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title='Macro Decision OS v5.2', page_icon='◈', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem; max-width: 1540px;}
[data-testid="stMetric"] {border:1px solid rgba(128,128,128,.22); border-radius:12px; padding:9px 12px;}
div[data-testid="stTabs"] button {font-size:.96rem;}
.decision-title {font-size:.78rem; opacity:.65; margin-bottom:.1rem;}
.decision-text {font-size:.98rem; line-height:1.45;}
</style>
''', unsafe_allow_html=True)


def finite(x):
    try:return np.isfinite(float(x))
    except Exception:return False


def fmt_num(x,digits=2,pct=False):
    if not finite(x):return 'N/A'
    return f'{float(x):.{digits}%}' if pct else f'{float(x):.{digits}f}'


def flatten_prices(bundle):
    out={}
    for d in bundle.get('prices',{}).values():out.update(d or {})
    return out


def guidance(read, do, nxt, title='How to use this'):
    st.markdown(f'**{title}**')
    a,b,c=st.columns(3)
    with a:
        st.markdown('**READ**')
        st.caption(read)
    with b:
        st.markdown('**DO**')
        st.caption(do)
    with c:
        st.markdown('**NEXT**')
        st.caption(nxt)


def relationship_heatmap(df,title,zmin=-1,zmax=1,height=430):
    if df is None or df.empty:
        st.info('Not enough overlapping data for this matrix.');return False
    fig=px.imshow(df,text_auto='.2f',aspect='auto',zmin=zmin,zmax=zmax,title=title)
    fig.update_layout(height=max(height,31*len(df.index)+160),margin=dict(l=10,r=10,t=55,b=10))
    st.plotly_chart(fig,use_container_width=True);return True


def projection_fan(stats,title='Forward projection — normalized current value = 100'):
    path=normalized_projection_path(stats)
    if path.empty:
        st.info('Projection fan unavailable.');return
    fig=go.Figure()
    fig.add_trace(go.Scatter(x=path.month,y=path.p90,mode='lines',line=dict(width=0),showlegend=False,hovertemplate='P90 %{y:.1f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=path.month,y=path.p10,mode='lines',line=dict(width=0),fill='tonexty',name='P10–P90 range',hovertemplate='P10 %{y:.1f}<extra></extra>'))
    fig.add_trace(go.Scatter(x=path.month,y=path['median'],mode='lines+markers',name='Median',hovertemplate='Median %{y:.1f}<extra></extra>'))
    fig.add_hline(y=100,line_width=1,line_dash='dot')
    fig.update_xaxes(tickvals=[0,1,3,6,12],ticktext=['Now','1M','3M','6M','12M'],title=None)
    fig.update_layout(height=390,margin=dict(l=10,r=10,t=55,b=10),title=title,yaxis_title='Normalized outcome')
    st.plotly_chart(fig,use_container_width=True)


def compact_projection_metrics(stats,horizon='3M'):
    g=projection_guidance(stats,horizon)
    r=g.get('row')
    if r is None:return g
    cols=st.columns(4)
    cols[0].metric(f'{horizon} median',fmt_num(r.get('median'),1,True))
    cols[1].metric('P(positive)',fmt_num(r.get('p_positive'),0,True))
    cols[2].metric('P(loss >10%)',fmt_num(r.get('p_loss10'),0,True))
    cols[3].metric('P90 outcome',fmt_num(r.get('p90'),1,True))
    return g


# Sidebar — only controls that change a decision view.
st.sidebar.markdown('### Decision setup')
objective=st.sidebar.selectbox('Objective',OBJECTIVES)
markets=st.sidebar.multiselect('Markets',['us','idx','crypto','commodity','fx'],default=['us','idx','crypto','commodity','fx'])
with st.sidebar.expander('Advanced data controls',expanded=False):
    cap=st.slider('Live symbols / market',5,35,20,5)
    special=st.toggle('Specialized public feeds',True)
    st.caption('FRED_API_KEY in Streamlit Secrets is recommended for reliable macro data.')
if st.sidebar.button('Refresh data',use_container_width=True):
    st.cache_data.clear();st.rerun()

@st.cache_data(ttl=1800,show_spinner=False)
def load_bundle(m,c,s):return build_data_bundle(m,c,s)

with st.spinner('Loading live / public data…'):
    bundle=load_bundle(markets,cap,special)
state=current_state(bundle);fred=bundle.get('fred',{});flat=flatten_prices(bundle);lineage=bundle.get('lineage',pd.DataFrame())
head=headline_states(state);scenarios=live_evidence(state);crash=crash_conclusion(state);posture=operational_posture(state,scenarios,crash)
fred_loaded=len(fred);price_loaded=len(flat)

# Header
st.title('Macro Decision OS v5.2')
st.caption('Decision-first view: state → what to do → next projection → opportunity → invalidation. Research proof stays behind the interface.')
if fred_loaded==0:
    st.error('Macro feed unavailable. Add FRED_API_KEY in Streamlit Secrets. No synthetic macro values are substituted.')
elif fred_loaded<10:
    st.warning(f'Partial macro feed: {fred_loaded} series loaded. Projection and scenario panels may be incomplete.')

h1,h2,h3,h4=st.columns(4)
h1.metric('Operational posture',posture['posture'])
h2.metric('Macro coverage',f'{fred_loaded} series')
h3.metric('Market coverage',f'{price_loaded} symbols')
h4.metric('Trade action',posture['trade_action'])

guidance(posture['read'],posture['do'],posture['next'],'What the system says now')

T=st.tabs(['Dashboard','Scenarios & Relationships','Opportunities','Research & Data'])

# ══════════════════════════════════════════════════════════════════════════
# DASHBOARD
# ══════════════════════════════════════════════════════════════════════════
with T[0]:
    st.subheader('1 · Current State')
    cols=st.columns(6)
    for col,label in zip(cols,['Growth','Inflation','Rates','Credit','Funding','Volatility']):
        lab,raw=head[label]
        raw_txt=fmt_num(raw,1,True) if label=='Inflation' else (f'{fmt_num(raw,2)} pp' if label=='Funding' else fmt_num(raw,2))
        col.metric(label,lab,raw_txt)

    left,right=st.columns(2)
    with left:
        st.markdown('#### A. Relative-state heatmap')
        h=percentile_strip(state).dropna(subset=['percentile'])
        if len(h):
            z=h.set_index('driver')[['percentile']].T
            fig=px.imshow(z,text_auto='.0%',aspect='auto',zmin=0,zmax=1)
            fig.update_layout(height=205,margin=dict(l=8,r=8,t=8,b=8),xaxis_title=None,yaxis_title=None)
            st.plotly_chart(fig,use_container_width=True)
        else:st.info('Needs macro data.')
        g=heatmap_guidance(h)
        guidance(g['read'],g['do'],g['next'])

    with right:
        st.markdown('#### B. What changed most recently?')
        sh=standardized_shocks(fred).dropna(subset=['z_13w'])
        if len(sh):
            sh=sh.sort_values('z_13w')
            fig=px.bar(sh,x='z_13w',y='driver',orientation='h',hover_data=['series','raw_change'])
            fig.add_vline(x=0,line_width=1)
            fig.update_layout(height=315,margin=dict(l=8,r=8,t=8,b=8),xaxis_title='13w move vs own history (z-score)',yaxis_title=None)
            st.plotly_chart(fig,use_container_width=True)
        else:st.info('Needs macro history.')
        g=shock_guidance(sh)
        guidance(g['read'],g['do'],g['next'])

    st.divider()
    st.subheader('2 · Competing Scenario')
    if len(scenarios):
        bal=[]
        for _,r in scenarios.iterrows():
            sup=str(r.get('supporting_evidence',''));con=str(r.get('contradicting_evidence',''))
            ns=0 if sup.startswith('None') else len([x for x in sup.split(';') if x.strip()]);nc=0 if con.startswith('None') else len([x for x in con.split(';') if x.strip()])
            bal.append({'type':r['type'],'scenario':r['scenario'],'support':ns,'contradiction':-nc})
        d=pd.DataFrame(bal).melt(id_vars=['type','scenario'],value_vars=['support','contradiction'],var_name='evidence',value_name='count')
        fig=px.bar(d,x='count',y='scenario',color='evidence',orientation='h',barmode='relative')
        fig.add_vline(x=0,line_width=1);fig.update_layout(height=310,margin=dict(l=8,r=8,t=8,b=8),xaxis_title='Evidence balance — not probability',yaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)
    g=scenario_guidance(scenarios)
    guidance(g['read'],g['do'],g['next'])

    st.divider()
    st.subheader('3 · Next Projection')
    projection_assets=[x for x in ['IWM','SPY','QQQ','TLT','GLD','USO','UUP','^JKSE','BTC-USD','ETH-USD'] if x in flat]
    if projection_assets and fred_loaded:
        p1,p2=st.columns([1,3])
        proj_asset=p1.selectbox('Projection instrument',projection_assets,index=0,key='dash_proj_asset')
        proj_h=p1.selectbox('Decision horizon',['1M','3M','6M','12M'],index=1,key='dash_proj_h')
        with st.spinner('Finding historically similar macro states…'):
            stats,analogs,meta=analog_distribution(fred,flat[proj_asset],20)
        with p2:
            projection_fan(stats,f'{proj_asset} — historical macro-analog fan')
        g=compact_projection_metrics(stats,proj_h)
        guidance(g['read'],g['do'],g['next'])
        st.caption('Projection is a historical conditional distribution from revised public history. It is research context until PIT/vintage calibration is available.')
    else:
        st.info('Projection needs both macro history and asset price history.')

    st.divider()
    st.subheader('4 · Crash / Risk Gate')
    cm=crash_matrix(state)
    phase_map={'DATA_GATED':0,'NO ACTIVE EVIDENCE IN LOADED SUBSET':1,'WATCH':2,'ACTIVE / INVESTIGATE':3}
    if len(cm):
        cmv=cm[['phase','status']].copy();cmv['level']=cmv.status.map(phase_map).fillna(0)
        fig=px.bar(cmv,x='phase',y='level',text='status')
        fig.update_yaxes(tickvals=[0,1,2,3],ticktext=['GATED','CLEAR','WATCH','ACTIVE'],range=[0,3.4])
        fig.update_layout(height=300,margin=dict(l=8,r=8,t=8,b=8),yaxis_title=None,xaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)
    if crash.get('active_phases'):
        guidance('Acute crash evidence is active.','Risk/hedge review takes priority over new directional exposure.','Look for credit/funding/liquidation normalization before re-entry research.')
    elif crash.get('watch_phases'):
        guidance('Some crash phases are on WATCH but no calibrated crash probability exists.','Keep position sizing selective; do not confuse fragility with an imminent crash.','Escalate only if funding/credit acute-trigger evidence appears.')
    else:
        guidance('No active acute trigger is visible in the loaded subset.','Do not short simply because fragility metrics exist. Continue scenario/opportunity selection.','Watch for credit velocity, funding dislocation and forced-deleveraging evidence.')

# ══════════════════════════════════════════════════════════════════════════
# SCENARIOS & RELATIONSHIPS
# ══════════════════════════════════════════════════════════════════════════
with T[1]:
    st.subheader('Scenario & Relationship Map')
    st.caption('Use relationships to identify sensitivity, then return to causal scenario and opportunity gates. Correlation alone never becomes LONG/SHORT.')

    c1,c2=st.columns([1,1])
    years=c1.selectbox('History window',[5,10,15],index=1)
    horizon=c2.selectbox('Forward outcome horizon',[1,3,6],index=1,format_func=lambda x:f'{x}M')

    rel=macro_asset_relationships(fred,flat,years,horizon) if fred_loaded else pd.DataFrame()
    preferred=['SPY','IWM','QQQ','TLT','GLD','USO','UUP','^JKSE','BTC-USD','ETH-USD']
    if len(rel):
        avail=[x for x in preferred if x in rel.instrument.unique()] or list(rel.instrument.unique())[:10]
        p=rel[rel.instrument.isin(avail)].pivot(index='factor',columns='instrument',values='correlation')
        ok=relationship_heatmap(p,f'Macro driver change ↔ {horizon}M forward asset outcome')
        if ok:
            flat_rel=rel[rel.instrument.isin(avail)].dropna(subset=['correlation']).copy();flat_rel['abs_corr']=flat_rel.correlation.abs()
            top=flat_rel.sort_values('abs_corr',ascending=False).head(5)
            read='Strongest raw associations: '+', '.join(f"{r.factor}→{r.instrument} {r.correlation:+.2f}" for _,r in top.iterrows())+'.'
            guidance(read,'Use the strongest cells only as sensitivity hypotheses. Open one pair below and inspect stability/sample before acting.','If the sign flips across windows or causal confirmation is absent, discard the relationship.')
    else:st.info('Macro ↔ asset matrix needs overlapping history.')

    st.markdown('#### Drill into one relationship')
    factors=list(macro_correlation(fred,years).columns) if fred_loaded else []
    assets=[x for x in preferred if x in flat]
    if factors and assets:
        a,b=st.columns(2);factor=a.selectbox('Driver',factors);asset=b.selectbox('Asset',assets)
        d=relationship_scatter(fred,flat[asset],factor,years,horizon)
        if len(d)>=24:
            plot_d=d[['factor_value','forward_return']].copy();plot_d.index=pd.to_datetime(plot_d.index,errors='coerce');plot_d=plot_d.loc[plot_d.index.notna()];plot_d.index.name='date';plot_d=plot_d.reset_index().replace([np.inf,-np.inf],np.nan).dropna()
            fig=px.scatter(plot_d,x='factor_value',y='forward_return',hover_data=['date'])
            corr=plot_d.factor_value.corr(plot_d.forward_return)
            x=plot_d.factor_value.to_numpy(float);y=plot_d.forward_return.to_numpy(float);good=np.isfinite(x)&np.isfinite(y)
            if good.sum()>=3 and np.nanstd(x[good])>0:
                m,q=np.polyfit(x[good],y[good],1);xx=np.linspace(np.nanmin(x[good]),np.nanmax(x[good]),100);fig.add_trace(go.Scatter(x=xx,y=m*xx+q,mode='lines',name='Linear association'))
            fig.update_layout(height=420,title=f'{factor} vs {asset} {horizon}M outcome · corr={corr:.2f}',xaxis_title=factor,yaxis_title='Forward return')
            st.plotly_chart(fig,use_container_width=True)

            sens=empirical_sensitivities(fred,{asset:flat[asset]})
            stable=sens[sens.sign_stable_across_windows] if len(sens) else pd.DataFrame()
            if len(stable):
                st.dataframe(stable[['macro_factor','beta_5y','beta_10y','beta_full','sign_stable_across_windows']],use_container_width=True,hide_index=True)
                stability='The selected asset has at least some factor sensitivities with stable sign across 5Y/10Y/full windows.'
            else:stability='No stable-sign sensitivity was confirmed by the simple multi-window check.'
            guidance(f'Pair correlation is {corr:+.2f} over this window. {stability}','Do not trade the scatter. Use it to identify which macro variable should confirm or contradict an asset thesis.','Re-check after the next driver shock; reject the relationship if sign/sample stability deteriorates.')
        else:st.info('Not enough clean observations for this pair.')

    with st.expander('Macro ↔ macro and long-run research matrices'):
        relationship_heatmap(macro_correlation(fred,years),f'Macro ↔ macro — {years}Y')
        relationship_heatmap(bundled_longrun_correlation(),'Bundled long-run research matrix')

# ══════════════════════════════════════════════════════════════════════════
# OPPORTUNITIES
# ══════════════════════════════════════════════════════════════════════════
with T[2]:
    st.subheader('Opportunity Decision Board')
    st.caption('The board first asks: where is historical payoff asymmetry attractive? Then: is there a causal mechanism? Then: what is still missing before execution?')

    st.markdown('### A. Cross-market payoff vs downside')
    horizon=st.selectbox('Opportunity horizon',['1M','3M','6M','12M'],index=1,key='opp_horizon')
    radar_assets=[x for x in ['SPY','IWM','QQQ','TLT','GLD','USO','UUP','^JKSE','BTC-USD','ETH-USD'] if x in flat]
    radar=opportunity_radar(fred,flat,radar_assets,horizon,20) if fred_loaded else pd.DataFrame()
    if len(radar):
        fig=px.scatter(radar,x='p_loss10',y='median',size='p_positive',text='instrument',color='pareto_candidate',
                       hover_data=['p10','p90','p_gt25','n','research_priority'])
        fig.update_xaxes(tickformat='.0%',title='P(loss >10%)  ← lower is better')
        fig.update_yaxes(tickformat='.1%',title=f'{horizon} median outcome  ↑ higher is better')
        fig.update_layout(height=500,title='Upper-left = better historical analog asymmetry · highlighted points are Pareto-efficient')
        st.plotly_chart(fig,use_container_width=True)

        pareto=radar[radar.pareto_candidate]
        worst=radar.sort_values(['p_loss10','median'],ascending=[False,True]).head(2)
        a,b,c=st.columns(3)
        a.metric('Inspect first',', '.join(pareto.instrument.tolist()) or 'None')
        b.metric('Highest downside watch',', '.join(worst.instrument.tolist()))
        c.metric('Universe',f'{len(radar)} instruments')
        guidance('Upper-left instruments have higher historical median outcome with lower >10% loss frequency in states similar to today.','Inspect Pareto-frontier assets first. This is a research queue, not an automatic trade ranking.','Before execution, require causal fit + pricing/catalyst evidence. The frontier can change after the next macro release.')

        sel=st.selectbox('Inspect market opportunity',radar.instrument.tolist(),key='radar_pick')
        rr=radar[radar.instrument==sel].iloc[0]
        stats,analogs,meta=analog_distribution(fred,flat[sel],20)
        l,r=st.columns([1.4,1])
        with l:projection_fan(stats,f'{sel} — next outcome distribution')
        with r:
            g=compact_projection_metrics(stats,horizon)
            st.markdown('**Decision interpretation**')
            st.write(g['do'])
            st.markdown('**What changes the view**')
            st.write(g['next'])
            st.markdown('**Trade action**')
            st.error('NO TRADE until causal/pricing/catalyst gates pass')

        sens=empirical_sensitivities(fred,{sel:flat[sel]})
        if len(sens):
            sens=sens.copy();sens['abs_beta']=sens.beta_full.abs();stable=sens[sens.sign_stable_across_windows].sort_values('abs_beta',ascending=False).head(4)
            if len(stable):
                st.markdown('**Macro drivers to watch for this asset**')
                st.dataframe(stable[['macro_factor','beta_5y','beta_10y','beta_full']],use_container_width=True,hide_index=True)
                st.caption('Stable-sign association across windows; still not proof of causality.')
    else:
        st.info('Cross-market opportunity radar needs live macro history and price histories.')

    st.divider()
    st.markdown('### B. Company bottleneck / monster-winner search')
    st.caption('This section answers whether a company actually captures a binding constraint. It does not reward hype, backlog headlines, or prior price performance.')
    txt=st.text_input('US candidates','SNDK, PLTR, GNRC, MOD, POWL')
    if st.button('Analyze company evidence',type='primary'):
        tickers=[x.strip().upper() for x in txt.split(',') if x.strip()][:10]
        with st.spinner('Reading SEC filings + filed-date Company Facts…'):
            df,det=investigate(tickers)
        st.session_state['v52_bdf']=df;st.session_state['v52_bdet']=det

    df=st.session_state.get('v52_bdf');det=st.session_state.get('v52_bdet',{})
    if isinstance(df,pd.DataFrame) and len(df):
        chart=df.copy();chart['SEC_revenue_yoy']=pd.to_numeric(chart.SEC_revenue_yoy,errors='coerce');chart['SEC_operating_income_yoy']=pd.to_numeric(chart.SEC_operating_income_yoy,errors='coerce')
        chart['drawdown_abs']=pd.to_numeric(chart.drawdown_5y_peak,errors='coerce').abs().fillna(.05).clip(lower=.03)
        if chart[['SEC_revenue_yoy','SEC_operating_income_yoy']].notna().any().any():
            fig=px.scatter(chart,x='SEC_revenue_yoy',y='SEC_operating_income_yoy',size='drawdown_abs',text='ticker',color='evidence_status',hover_data=['drawdown_vol_units','price','filing_date'])
            fig.add_hline(y=0,line_width=1);fig.add_vline(x=0,line_width=1)
            fig.update_layout(height=455,xaxis_tickformat='.0%',yaxis_tickformat='.0%',xaxis_title='Revenue capture (SEC YoY)',yaxis_title='Operating-income capture (SEC YoY)',title='Upper-right + verified mechanism = bottleneck monetization worth deeper work')
            st.plotly_chart(fig,use_container_width=True)
        guidance('Upper-right means revenue and operating capture are both improving; color shows whether filing evidence supports the underlying bottleneck mechanism.','Prioritize companies with confirmed mechanism + monetization. Do not use drawdown alone as a reload signal.','Next unlock is PIT pricing/revisions + catalyst timing; failure of revenue/operating capture kills the thesis.')

        pick=st.selectbox('Inspect company',df.ticker.tolist(),key='company_pick');d=det.get(pick,{})
        if d:
            pxs=flat.get(pick)
            if pxs is None:
                pp,_=strict_prices([pick]);pxs=pp.get(pick)
            stats=pd.DataFrame();analogs=pd.DataFrame();meta={}
            if pxs is not None and fred_loaded:stats,analogs,meta=analog_distribution(fred,pxs,20)
            gate=company_gate_guidance(d,projection_available=not stats.empty)

            st.markdown(f'#### {pick} · {gate["research_state"]}')
            stage_cols=st.columns(5)
            for col,(stage,status) in zip(stage_cols,gate['stages']):
                col.metric(stage,status)
            guidance(gate['read'],gate['do'],'Re-check only when the first missing gate gets new evidence; do not skip directly from mechanism to trade.')

            cur=d.get('current',{});facts=d.get('sec_facts',{})
            m1,m2,m3,m4=st.columns(4)
            m1.metric('Price',fmt_num(cur.get('price'),2))
            m2.metric('Drawdown from 5Y peak',fmt_num(cur.get('drawdown_5y_peak'),1,True))
            m3.metric('Drawdown / expected 3M vol',fmt_num(cur.get('drawdown_vol_units'),1))
            m4.metric('SEC revenue YoY',fmt_num(facts.get('revenue_yoy'),1,True))

            if not stats.empty:
                projection_fan(stats,f'{pick} — macro-analog forward context')
                g=compact_projection_metrics(stats,horizon)
                guidance(g['read'],g['do'],'For a prior winner/reload, require this payoff context PLUS intact mechanism, pricing reset and positive PIT revisions.')

            with st.expander('Why / competing thesis / kill switches'):
                st.write('**Why it is interesting:**',d.get('reason','N/A'))
                st.write('**Competing thesis:**',d.get('competing_thesis','N/A'))
                st.write('**Why trade action is not unlocked:**',d.get('action_reason','N/A'))
                for x in d.get('kill_switches',[]):st.write('•',x)
                for x in d.get('filing',{}).get('snippets',[])[:6]:st.write(f"**{x['group']} / {x['term']}** — {x['snippet']}")

            if st.button(f'Load {pick} options execution context'):
                with st.spinner('Loading current option chain…'):st.session_state['v52_opt']=(pick,option_snapshot(pick))
            if st.session_state.get('v52_opt',(None,None))[0]==pick:
                with st.expander('Options execution context',expanded=True):
                    st.json(st.session_state['v52_opt'][1]);st.caption('Execution/risk context only; not a universal GEX directional signal.')
    else:
        st.info('Analyze a small candidate list to populate the company decision funnel.')

# ══════════════════════════════════════════════════════════════════════════
# RESEARCH & DATA
# ══════════════════════════════════════════════════════════════════════════
with T[3]:
    st.subheader('Research & Data Health')
    a,b,c,d=st.columns(4);a.metric('Metric families',len(METRIC_FAMILIES));b.metric('Experiments',len(load_experiments()));c.metric('FRED failures',len(bundle.get('fred_errors',{})));d.metric('Synthetic fallback','NONE')

    if bundle.get('fred_errors'):
        with st.expander('Macro feed errors / setup',expanded=(fred_loaded==0)):
            st.json(bundle['fred_errors']);st.markdown('Best cloud fix: add `FRED_API_KEY` in Streamlit Secrets. If all real-data routes fail, macro state stays blank.')
    with st.expander('Proof summary',expanded=True):st.dataframe(proof_summary(),use_container_width=True,hide_index=True)
    with st.expander('Experiment registry'):st.dataframe(load_experiments(),use_container_width=True,hide_index=True,height=430)
    with st.expander('Failure library / governance'):
        st.dataframe(load_failures(),use_container_width=True,hide_index=True);st.dataframe(load_governance_overrides(),use_container_width=True,hide_index=True);st.dataframe(load_search_ledger(),use_container_width=True,hide_index=True)
    with st.expander('Data lineage'):
        st.dataframe(lineage,use_container_width=True,hide_index=True,height=500);st.warning('Latest/revised macro history is not PIT-safe. Monitoring/research only until vintage data are available.')
    with st.expander('Critical data gaps'):
        for x in bundle.get('data_gaps',[]):st.write('•',x)
    cp=HERE/'research'/'spec_compliance_v4.csv'
    if cp.exists():
        with st.expander('Framework compliance'):st.dataframe(pd.read_csv(cp),use_container_width=True,hide_index=True)

st.divider()
st.caption('v5.2: every major visual has READ → DO → NEXT. Opportunity selection uses payoff/downside Pareto logic first, then causal/pricing/catalyst gates; no arbitrary composite alpha score.')
