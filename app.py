from __future__ import annotations
from pathlib import Path
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from config.metric_registry_v4 import METRIC_FAMILIES
from data_layer_v4 import build_data_bundle, load_universes, strict_prices
from providers.options_public import snapshot as option_snapshot
from engines.state_engine import current_state
from engines.scenario_engine import live_evidence
from engines.thesis_engine import lifecycle
from engines.crash_engine import crash_matrix, crash_conclusion
from engines.projection_engine import analog_distribution, walkforward_calibration
from engines.cross_market_engine import bottleneck_matrix
from engines.bottleneck_engine import investigate
from engines.opportunity_engine import OBJECTIVES
from engines.runway_engine import remaining_runway
from engines.experiment_registry import (
    load_experiments, load_failures, load_search_ledger,
    load_governance_overrides, proof_summary,
)
from engines.visual_engine import (
    headline_states, percentile_strip, standardized_shocks,
    macro_correlation, macro_asset_relationships, relationship_scatter,
    bundled_longrun_correlation,
)

HERE = Path(__file__).resolve().parent
st.set_page_config(page_title='Macro Decision OS v5', page_icon='◈', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 2rem; max-width: 1550px;}
[data-testid="stMetric"] {border: 1px solid rgba(128,128,128,.22); border-radius: 12px; padding: 9px 12px;}
.small {font-size: .83rem; opacity: .75;}
div[data-testid="stTabs"] button {font-size: .95rem;}
</style>
''', unsafe_allow_html=True)


def finite(x):
    try:
        return np.isfinite(float(x))
    except Exception:
        return False


def fmt_num(x, digits=2, pct=False):
    if not finite(x):
        return 'N/A'
    return f'{float(x):.{digits}%}' if pct else f'{float(x):.{digits}f}'


def flatten_prices(bundle):
    out = {}
    for d in bundle.get('prices', {}).values():
        out.update(d or {})
    return out


def scenario_counts(row):
    sup = str(row.get('supporting_evidence', ''))
    con = str(row.get('contradicting_evidence', ''))
    ns = 0 if not sup or sup.startswith('None') else len([x for x in sup.split(';') if x.strip()])
    nc = 0 if not con or con.startswith('None') else len([x for x in con.split(';') if x.strip()])
    return ns, nc


def relationship_heatmap(df, title, zmin=-1, zmax=1):
    if df is None or df.empty:
        st.info('Not enough overlapping data for this matrix.')
        return
    fig = px.imshow(df, text_auto='.2f', aspect='auto', zmin=zmin, zmax=zmax, title=title)
    fig.update_layout(height=max(420, 32 * len(df.index) + 180), margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig, use_container_width=True)


# ── Sidebar: only decisions; advanced controls hidden ──────────────────────
st.sidebar.markdown('### Decision setup')
objective = st.sidebar.selectbox('Objective', OBJECTIVES)
markets = st.sidebar.multiselect('Markets', ['us', 'idx', 'crypto', 'commodity', 'fx'], default=['us', 'idx', 'crypto', 'commodity', 'fx'])
with st.sidebar.expander('Data controls', expanded=False):
    cap = st.slider('Live symbols / market', 5, 35, 20, 5)
    special = st.toggle('Specialized public feeds', True)
    st.caption('Optional: add FRED_API_KEY in Streamlit Secrets for the most reliable macro feed.')
if st.sidebar.button('Refresh data', use_container_width=True):
    st.cache_data.clear()
    st.rerun()


@st.cache_data(ttl=1800, show_spinner=False)
def load_bundle(m, c, s):
    return build_data_bundle(m, c, s)


with st.spinner('Loading live / public data…'):
    bundle = load_bundle(markets, cap, special)
state = current_state(bundle)
fred = bundle.get('fred', {})
flat = flatten_prices(bundle)
lineage = bundle.get('lineage', pd.DataFrame())
head = headline_states(state)
crash = crash_conclusion(state)


# ── Header ─────────────────────────────────────────────────────────────────
st.title('Macro Decision OS v5')
st.caption('One-screen decision board first; proof and data lineage stay available behind it. No classic TA alpha. Missing critical data fails closed.')

fred_loaded = len(fred)
price_loaded = len(flat)
if fred_loaded == 0:
    st.error('Macro feed is unavailable: FRED loaded 0 series. V5 already tries FRED API → fredgraph → DBnomics; add `FRED_API_KEY` in Streamlit Secrets for the most reliable cloud path. No synthetic macro values are substituted.')
elif fred_loaded < 10:
    st.warning(f'Partial macro feed: only {fred_loaded} FRED series loaded. Interpret scenario/correlation panels cautiously.')

# Compact system status row
s1, s2, s3, s4 = st.columns(4)
s1.metric('Macro data', f'{fred_loaded}/{len(getattr(__import__("data_layer_v4"), "FRED", {})) or 29} series')
s2.metric('Market prices', f'{price_loaded} symbols')
s3.metric('Crash trigger', 'ACTIVE' if crash.get('active_phases') else ('WATCH' if crash.get('watch_phases') else 'NO ACTIVE TRIGGER'))
s4.metric('Decision default', 'NO TRADE' if not crash.get('active_phases') else 'RISK REVIEW')

T = st.tabs(['Dashboard', 'Scenarios & Relationships', 'Opportunities', 'Research & Data'])


# ═══════════════════════════════════════════════════════════════════════════
# 1. DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
with T[0]:
    st.subheader('Live Macro Board')
    st.caption('Labels are descriptive state summaries, not trade signals or probabilities.')

    cols = st.columns(6)
    labels = ['Growth', 'Inflation', 'Rates', 'Credit', 'Funding', 'Volatility']
    for col, label in zip(cols, labels):
        state_label, raw = head[label]
        if label == 'Inflation':
            raw_txt = fmt_num(raw, 1, pct=True)
        elif label in ('Funding',):
            raw_txt = f'{fmt_num(raw, 2)} pp'
        elif label == 'Volatility':
            raw_txt = fmt_num(raw, 1)
        else:
            raw_txt = fmt_num(raw, 2)
        col.metric(label, state_label, raw_txt)

    left, right = st.columns([1.15, 1])
    with left:
        st.markdown('#### Relative-state heatmap')
        h = percentile_strip(state).dropna(subset=['percentile'])
        if len(h):
            z = h.set_index('driver')[['percentile']].T
            fig = px.imshow(z, text_auto='.0%', aspect='auto', zmin=0, zmax=1)
            fig.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=10), xaxis_title=None, yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
            st.caption('Own-history percentile. High percentile means high relative level, not automatically bullish/bearish.')
        else:
            st.info('Relative-state heatmap requires macro data.')

    with right:
        st.markdown('#### 13-week macro shocks')
        sh = standardized_shocks(fred).dropna(subset=['z_13w'])
        if len(sh):
            sh = sh.sort_values('z_13w')
            fig = px.bar(sh, x='z_13w', y='driver', orientation='h', hover_data=['series', 'raw_change'])
            fig.add_vline(x=0, line_width=1)
            fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), xaxis_title='Current 13w change, z-score vs own history', yaxis_title=None)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('Shock chart requires macro history.')

    st.markdown('#### Competing thesis — evidence, not storytelling')
    le = live_evidence(state)
    if len(le):
        card_cols = st.columns(4)
        for col, (_, row) in zip(card_cols, le.iterrows()):
            ns, nc = scenario_counts(row)
            with col:
                st.markdown(f"**{row['type']}**")
                st.write(row['scenario'])
                st.metric('Support / contradiction', f'{ns} / {nc}')
                with st.expander('Evidence'):
                    st.write('**Supports:**', row['supporting_evidence'])
                    st.write('**Contradicts:**', row['contradicting_evidence'])
        st.info('Numerical scenario probabilities remain unavailable until a live-compatible calibrated model exists. Evidence counts are not probabilities.')

    st.markdown('#### Crash mechanism')
    cm = crash_matrix(state)
    phase_map = {'DATA_GATED': 0, 'NO ACTIVE EVIDENCE IN LOADED SUBSET': 1, 'WATCH': 2, 'ACTIVE / INVESTIGATE': 3}
    cmv = cm[['phase', 'status']].copy()
    cmv['level'] = cmv['status'].map(phase_map).fillna(0)
    fig = px.bar(cmv, x='phase', y='level', text='status')
    fig.update_yaxes(tickvals=[0,1,2,3], ticktext=['GATED','CLEAR','WATCH','ACTIVE'], range=[0,3.4])
    fig.update_layout(height=330, margin=dict(l=10, r=10, t=10, b=10), yaxis_title=None, xaxis_title=None)
    st.plotly_chart(fig, use_container_width=True)
    with st.expander('Crash evidence details'):
        st.dataframe(cm, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════════════════════════════════════
# 2. SCENARIOS & RELATIONSHIPS
# ═══════════════════════════════════════════════════════════════════════════
with T[1]:
    st.subheader('Scenarios & Relationships')
    st.caption('Correlation/association panels are research context. They do not replace causal transmission or PIT validation.')

    # Scenario balance visual
    le = lifecycle(state)
    sb = []
    for _, row in le.iterrows():
        ns, nc = scenario_counts(row)
        sb.append({'scenario': row['scenario'], 'type': row['type'], 'support': ns, 'contradiction': -nc})
    sb = pd.DataFrame(sb)
    if len(sb):
        sb_long = sb.melt(id_vars=['scenario','type'], value_vars=['support','contradiction'], var_name='evidence', value_name='count')
        fig = px.bar(sb_long, x='count', y='scenario', color='evidence', orientation='h', barmode='relative', title='Live scenario evidence balance')
        fig.add_vline(x=0, line_width=1)
        fig.update_layout(height=360, margin=dict(l=10, r=10, t=50, b=10), xaxis_title='Evidence count (not probability)', yaxis_title=None)
        st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns([1,1,1])
    years = c1.selectbox('Relationship window', [5, 10, 15], index=1)
    horizon = c2.selectbox('Forward asset horizon', [1, 3, 6], index=0, format_func=lambda x: f'{x} month' if x == 1 else f'{x} months')
    source_mode = c3.selectbox('Matrix', ['Macro ↔ Assets', 'Macro ↔ Macro', 'Long-run bundled research'])

    if source_mode == 'Macro ↔ Macro':
        relationship_heatmap(macro_correlation(fred, years), f'Macro driver correlation — last {years}y')
    elif source_mode == 'Long-run bundled research':
        relationship_heatmap(bundled_longrun_correlation(), 'Bundled long-run macro / asset relationship matrix')
        st.caption('Bundled War Room research panel is historical research context, not live PIT evidence.')
    else:
        rel = macro_asset_relationships(fred, flat, years, horizon)
        if len(rel):
            # Keep a concise set of liquid representative instruments first.
            preferred = ['SPY','IWM','QQQ','TLT','GLD','USO','UUP','^JKSE','BTC-USD','ETH-USD']
            avail = [x for x in preferred if x in rel.instrument.unique()]
            if not avail:
                avail = list(rel.instrument.unique())[:10]
            p = rel[rel.instrument.isin(avail)].pivot(index='factor', columns='instrument', values='correlation')
            relationship_heatmap(p, f'Macro change ↔ {horizon}M forward asset return correlation, last {years}y')
            st.caption('Forward outcome correlation only. A stable sign still does not prove a causal trade mapping.')
        else:
            st.info('Macro ↔ asset matrix needs overlapping macro and price history.')

    st.markdown('#### Relationship explorer')
    if fred_loaded:
        factors = list(macro_correlation(fred, years).columns)
    else:
        factors = []
    asset_choices = [x for x in ['SPY','IWM','QQQ','TLT','GLD','USO','UUP','^JKSE','BTC-USD','ETH-USD'] if x in flat]
    if factors and asset_choices:
        a, b = st.columns(2)
        factor = a.selectbox('Macro driver', factors)
        asset = b.selectbox('Asset', asset_choices)
        d = relationship_scatter(fred, flat[asset], factor, years, horizon)
        if len(d) >= 24:
            fig = px.scatter(d.reset_index(), x='factor_value', y='forward_return', hover_data=['index'])
            x = d['factor_value'].values; y = d['forward_return'].values
            ok = np.isfinite(x) & np.isfinite(y)
            if ok.sum() >= 3 and np.nanstd(x[ok]) > 0:
                m, q = np.polyfit(x[ok], y[ok], 1)
                xx = np.linspace(np.nanmin(x[ok]), np.nanmax(x[ok]), 100)
                fig.add_trace(go.Scatter(x=xx, y=m*xx+q, mode='lines', name='Linear association'))
            corr = d['factor_value'].corr(d['forward_return'])
            fig.update_layout(height=440, title=f'{factor} vs {asset} forward {horizon}M return · corr={corr:.2f}', xaxis_title=factor, yaxis_title='Forward return')
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info('Not enough observations for this pair.')
    else:
        st.info('Relationship explorer will activate once macro and asset histories overlap.')


# ═══════════════════════════════════════════════════════════════════════════
# 3. OPPORTUNITIES
# ═══════════════════════════════════════════════════════════════════════════
with T[2]:
    st.subheader('Opportunity Board')
    st.caption('Mechanism first. A candidate can be interesting and still finish as NO TRADE when pricing, catalyst or runway is not defensible.')

    bm = bottleneck_matrix(state)
    if len(bm):
        cards = st.columns(min(5, len(bm)))
        for col, (_, row) in zip(cards, bm.iterrows()):
            with col:
                st.markdown(f"**{row['market']}**")
                st.write(row['candidate_binding_channel'])
                st.metric('Status', row['status'])
                st.caption(row['evidence'])
                with st.expander('Next check'):
                    st.write(row['next_discriminating_observation'])

    st.divider()
    st.markdown('### Company bottleneck / winner-loser')
    txt = st.text_input('US candidates', 'SNDK, PLTR, GNRC, MOD, POWL')
    if st.button('Analyze company evidence', type='primary'):
        tickers = [x.strip().upper() for x in txt.split(',') if x.strip()][:10]
        with st.spinner('Reading SEC filings + filed-date Company Facts…'):
            df, det = investigate(tickers)
        st.session_state['v5_bdf'] = df
        st.session_state['v5_bdet'] = det

    df = st.session_state.get('v5_bdf')
    det = st.session_state.get('v5_bdet', {})
    if isinstance(df, pd.DataFrame) and len(df):
        chart = df.copy()
        chart['SEC_revenue_yoy'] = pd.to_numeric(chart['SEC_revenue_yoy'], errors='coerce')
        chart['SEC_operating_income_yoy'] = pd.to_numeric(chart['SEC_operating_income_yoy'], errors='coerce')
        chart['drawdown_abs'] = pd.to_numeric(chart['drawdown_5y_peak'], errors='coerce').abs().fillna(0.05).clip(lower=.03)
        if chart[['SEC_revenue_yoy','SEC_operating_income_yoy']].notna().any().any():
            fig = px.scatter(chart, x='SEC_revenue_yoy', y='SEC_operating_income_yoy', size='drawdown_abs', text='ticker', hover_data=['evidence_status','action','price'])
            fig.add_hline(y=0, line_width=1); fig.add_vline(x=0, line_width=1)
            fig.update_layout(height=450, xaxis_tickformat='.0%', yaxis_tickformat='.0%', xaxis_title='SEC revenue YoY', yaxis_title='SEC operating income YoY')
            st.plotly_chart(fig, use_container_width=True)

        short_cols = [c for c in ['ticker','evidence_status','action','price','drawdown_5y_peak','SEC_revenue_yoy','SEC_operating_income_yoy','filing_date'] if c in df.columns]
        view = df[short_cols].copy()
        for c in ['drawdown_5y_peak','SEC_revenue_yoy','SEC_operating_income_yoy']:
            if c in view.columns:
                view[c] = pd.to_numeric(view[c], errors='coerce').map(lambda x: f'{x:.1%}' if finite(x) else 'N/A')
        st.dataframe(view, use_container_width=True, hide_index=True)

        pick = st.selectbox('Inspect one candidate', df.ticker.tolist())
        d = det.get(pick, {})
        if d:
            a,b,c = st.columns(3)
            a.metric('Evidence', d.get('reason','N/A'))
            b.metric('Action', d.get('action','NO TRADE'))
            cur = d.get('current',{})
            btm = d.get('sec_facts',{})
            c.metric('Revenue YoY', fmt_num(btm.get('revenue_yoy'), 1, pct=True))

            chain = d.get('chain', {})
            chain_df = pd.DataFrame([{'stage': k.replace('_',' '), 'observed': bool(v)} for k,v in chain.items()])
            fig = px.bar(chain_df, x='stage', y=chain_df['observed'].astype(int), text=chain_df['observed'].map({True:'YES',False:'NO'}))
            fig.update_yaxes(tickvals=[0,1], ticktext=['NO','YES'], range=[0,1.25])
            fig.update_layout(height=310, xaxis_title=None, yaxis_title='Evidence chain')
            st.plotly_chart(fig, use_container_width=True)

            st.write('**Competing thesis:**', d.get('competing_thesis','N/A'))
            st.write('**Why action is still NO TRADE:**', d.get('action_reason','N/A'))
            with st.expander('Kill switches & SEC snippets'):
                for x in d.get('kill_switches',[]):
                    st.write('•', x)
                for x in d.get('filing',{}).get('snippets',[])[:8]:
                    st.write(f"**{x['group']} / {x['term']}** — {x['snippet']}")

            # Forward analog for selected candidate in same screen.
            st.markdown('#### Forward outcome context')
            pxs = flat.get(pick)
            if pxs is None:
                pp, _ = strict_prices([pick])
                pxs = pp.get(pick)
            if pxs is not None and fred_loaded:
                stats, analogs, meta = analog_distribution(fred, pxs, 20)
                if len(stats):
                    graph = stats.copy()
                    keep = [c for c in ['horizon','p_positive','p_gt25','p_gt50','p_gt100','p_loss10'] if c in graph.columns]
                    long = graph[keep].melt(id_vars=['horizon'], var_name='outcome', value_name='probability')
                    fig = px.bar(long, x='horizon', y='probability', color='outcome', barmode='group')
                    fig.update_yaxes(tickformat='.0%')
                    fig.update_layout(height=370, yaxis_title='Historical analog frequency', xaxis_title=None)
                    st.plotly_chart(fig, use_container_width=True)
                    st.caption(meta.get('warning','Historical analog context only; not calibrated remaining runway.'))
                else:
                    st.info('No usable macro analog distribution for this ticker.')
            else:
                st.info('Forward analog needs both macro history and ticker history.')

            # Options integrated here instead of separate tab.
            if st.button(f'Load {pick} options context'):
                with st.spinner('Loading current option chain…'):
                    st.session_state['v5_opt'] = (pick, option_snapshot(pick))
            if st.session_state.get('v5_opt', (None,None))[0] == pick:
                with st.expander('Options execution context', expanded=True):
                    st.json(st.session_state['v5_opt'][1])
                    st.caption('Instrument-specific execution/risk context only; no universal GEX direction claim.')
    else:
        st.info('Analyze a short candidate list to populate the visual company board.')


# ═══════════════════════════════════════════════════════════════════════════
# 4. RESEARCH & DATA
# ═══════════════════════════════════════════════════════════════════════════
with T[3]:
    st.subheader('Research & Data Health')
    st.caption('Everything needed for auditability remains here, without dominating the decision screen.')

    h1,h2,h3,h4 = st.columns(4)
    h1.metric('Metric families', len(METRIC_FAMILIES))
    h2.metric('Experiments', len(load_experiments()))
    h3.metric('FRED failures', len(bundle.get('fred_errors',{})))
    h4.metric('Synthetic fallback', 'NONE')

    if bundle.get('fred_errors'):
        with st.expander('Macro feed errors / setup', expanded=(fred_loaded==0)):
            st.json(bundle['fred_errors'])
            st.markdown('**Best Streamlit Cloud fix:** add a `FRED_API_KEY` secret. V5 also tries anonymous fredgraph and DBnomics as real-data fallbacks. If all fail, the system stays blank rather than generating macro data.')

    with st.expander('Proof summary', expanded=True):
        st.dataframe(proof_summary(), use_container_width=True, hide_index=True)

    with st.expander('Experiment registry'):
        st.dataframe(load_experiments(), use_container_width=True, hide_index=True, height=450)

    with st.expander('Failure library / governance overrides'):
        st.markdown('**Failed / rejected ideas**')
        st.dataframe(load_failures(), use_container_width=True, hide_index=True)
        st.markdown('**Governance overrides**')
        st.dataframe(load_governance_overrides(), use_container_width=True, hide_index=True)
        st.markdown('**Search ledger**')
        st.dataframe(load_search_ledger(), use_container_width=True, hide_index=True)

    with st.expander('Data lineage'):
        st.dataframe(lineage, use_container_width=True, hide_index=True, height=520)
        st.warning('Latest/revised macro history is explicitly not PIT-safe. It can support monitoring/research, not final historical proof.')

    with st.expander('Critical data gaps'):
        for x in bundle.get('data_gaps',[]):
            st.write('•', x)

    cp = HERE / 'research' / 'spec_compliance_v4.csv'
    if cp.exists():
        with st.expander('Framework compliance'):
            st.dataframe(pd.read_csv(cp), use_container_width=True, hide_index=True)

st.divider()
st.caption('v5 visual layer: current state → competing mechanisms → relationships → opportunities. Research proof remains accessible but no longer overwhelms the decision screen.')
