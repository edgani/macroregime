from __future__ import annotations

import json
import pandas as pd
import streamlit as st


def _title(text: str):
    st.markdown(f"### {text}")


def _df(rows, columns):
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame([{c: r.get(c) for c in columns} for r in rows])


def _score(x):
    try:
        return f"{float(x):.1f}"
    except Exception:
        return '—'


def _card(label: str, value: str, help_text: str = ''):
    st.markdown(f"**{label}**")
    st.markdown(f"<div style='padding:.55rem .75rem;border:1px solid rgba(255,255,255,.12);border-radius:12px;background:rgba(255,255,255,.02);font-size:1rem;font-weight:700'>{value}</div>", unsafe_allow_html=True)
    if help_text:
        st.caption(help_text)


def render_dashboard(payload: dict):
    st.title('Dashboard')
    c1,c2,c3,c4 = st.columns(4)
    with c1: _card('Rally / Scenario State', payload.get('executive_strip',{}).get('rally_state','—'), 'current board tone')
    with c2: _card('Action', payload.get('executive_strip',{}).get('action','—'), 'execution bias')
    with c3: _card('Exec Mode', payload.get('executive_strip',{}).get('exec_mode','—'), 'sizing posture')
    with c4: _card('Board', payload.get('executive_strip',{}).get('board','—'), 'health summary')

    st.divider()
    _title('Scenario Stack')
    cards = payload.get('scenario_cards', {})
    cols = st.columns(4)
    for col, key, label in zip(cols, ['primary','secondary','residual_drag','tail_risk'], ['Primary','Secondary','Residual Drag','Tail Risk']):
        s = cards.get(key, {})
        with col:
            st.markdown(f"**{label}**")
            st.write(s.get('name','—'))
            st.caption(f"Status: {s.get('status','—')} | Score: {_score(s.get('score'))} | Weight: {int(100*float(s.get('weight',0)))}%")
            st.write('Responders: ' + (', '.join([str(x) for x in s.get('first_responders',[])[:3]]) or '—'))
            st.write('Invalidator: ' + (', '.join([str(x) for x in s.get('invalidators',[])[:2]]) or '—'))

    st.divider()
    _title('Why This Is Moving')
    wt = payload.get('why_this_is_moving', {})
    drivers = [d.get('label','—') if isinstance(d, dict) else str(d) for d in wt.get('top_drivers', [])[:6]]
    if drivers:
        st.write(' | '.join(drivers))
    route = wt.get('route', {})
    c1,c2,c3 = st.columns(3)
    c1.metric('Current Path', route.get('active_path','—'))
    c2.metric('Next Path', route.get('next_path','—'))
    c3.metric('Invalidator', route.get('invalidator_path','—'))

    st.divider()
    _title('Ticker Attack Matrix')
    rows=[]
    for market, block in payload.get('market_attack_matrix', {}).items():
        if market == 'IHSG':
            rows.append({
                'Market': market,
                'Now Long/Buy': ', '.join(block.get('best_buys_now', [])[:3]),
                'Now Short': '—',
                'Front-Run Long/Buy': ', '.join(block.get('front_run_buys', [])[:3]),
                'Front-Run Short': '—',
            })
        else:
            rows.append({
                'Market': market,
                'Now Long/Buy': ', '.join(block.get('best_longs_now', [])[:3]),
                'Now Short': ', '.join(block.get('best_shorts_now', [])[:3]),
                'Front-Run Long/Buy': ', '.join(block.get('front_run_longs', [])[:3]),
                'Front-Run Short': ', '.join(block.get('front_run_shorts', [])[:3]),
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.divider()
    c1,c2,c3 = st.columns(3)
    with c1:
        _title('Best Market Now')
        st.write(', '.join(payload.get('best_market_now', [])) or '—')
    with c2:
        _title('Best Market Next')
        st.write(', '.join(payload.get('best_market_next', [])) or '—')
    with c3:
        _title('Risk State')
        risk = payload.get('risk_state', {})
        st.write(f"Conflict: {risk.get('conflict_label','—')}")
        st.write(f"Size Cap: {risk.get('size_cap','—')}")
        st.write(f"Kill Switch: {risk.get('kill_switch','—')}")

    st.divider()
    t1, t2 = st.tabs(['Scenarios & What-If', 'Cross-Asset'])
    with t1:
        scen = payload.get('scenario_lab', {}) or {}
        st.markdown('**Active Route Summary**')
        st.write(scen.get('active_route_summary','—'))
        if scen.get('what_if_matrix'):
            rows=[]
            for k,v in list((scen.get('what_if_matrix') or {}).items())[:12]:
                if isinstance(v, dict):
                    rows.append({'Scenario': k, 'Impact': v.get('impact', v.get('summary','—')), 'Why': v.get('why','—')})
                else:
                    rows.append({'Scenario': k, 'Impact': str(v), 'Why': '—'})
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        if scen.get('playbooks'):
            for p in scen.get('playbooks', [])[:5]:
                with st.expander(str(p.get('name','Playbook'))):
                    st.write(p.get('description','—'))
                    st.write('Invalidators: ' + ', '.join((p.get('invalidators') or [])[:3]))
    with t2:
        cross = payload.get('cross_asset', {}) or {}
        st.markdown('**Global Chain Map**')
        st.json(cross.get('global_chain_map', {}), expanded=False)
        st.markdown('**Conflict Map**')
        st.json(cross.get('conflict_map', {}), expanded=False)
        st.markdown('**Confirmation Map**')
        st.json(cross.get('confirmation_map', {}), expanded=False)


def _render_header(bundle: dict, title: str):
    st.title(title)
    hdr = bundle.get('header', {})
    c1,c2,c3,c4 = st.columns(4)
    c1.metric('Net Bias', hdr.get('stance','—'))
    c2.metric('Conflict', hdr.get('conflict_label','—'))
    c3.metric('Primary Driver', hdr.get('primary_driver','—'))
    c4.metric('Main Drag', hdr.get('main_drag','—'))
    st.caption(hdr.get('one_line','—'))


def _render_table(rows, cols, title):
    _title(title)
    df=_df(rows[:5], cols)
    rename={
        'ticker':'Ticker','bias':'Bias','bucket':'Bucket','entry_zone':'Entry Zone','trigger':'Trigger','why_not_yet':'Why Not Yet',
        'trigger_distance':'Trigger Distance','invalidation':'Invalidation','target':'Target','score':'Score','why_now':'Why Now',
        'problem':'Problem','why_avoid':'Why Avoid','better_alternative':'Better Alternative','type':'Type','why_defensive':'Why Defensive','trigger_to_use':'Trigger to Use'
    }
    if not df.empty:
        df=df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
        if 'Score' in df.columns: df['Score']=df['Score'].map(_score)
        if 'Trigger Distance' in df.columns: df['Trigger Distance']=df['Trigger Distance'].map(_score)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_state_change(sc: dict):
    _title('State Change')
    c1,c2,c3,c4=st.columns(4)
    c1.write('**Added**'); c1.write(', '.join(sc.get('added',[])[:5]) or '—')
    c2.write('**Remaining**'); c2.write(', '.join(sc.get('remaining',[])[:5]) or '—')
    c3.write('**Removed**'); c3.write(', '.join(sc.get('removed',[])[:5]) or '—')
    c4.write('**Ripening**'); c4.write(', '.join(sc.get('ripening',[])[:5]) or '—')


def _render_market_state(ms: dict):
    _title('Market State')
    c1,c2,c3 = st.columns(3)
    c1.write(f"Checklist Score: {ms.get('checklist_score','—')}")
    c1.write(f"Macro Fit: {ms.get('macro_fit','—')}")
    c2.write(f"Breadth: {ms.get('breadth','—')}")
    c2.write(f"Leadership: {ms.get('leadership','—')}")
    svw = ms.get('strong_vs_weak', {})
    c3.write('Strong: ' + (', '.join(svw.get('strong',[])[:4]) or '—'))
    c3.write('Weak: ' + (', '.join(svw.get('weak',[])[:4]) or '—'))
    if ms.get('one_line'):
        st.caption(ms['one_line'])


def _render_why(bundle: dict):
    _title('Why This Is Moving')
    why = bundle.get('why_this_is_moving', {})
    labels = []
    for x in why.get('top_drivers', [])[:5]:
        if isinstance(x, dict): labels.append(x.get('label','—'))
        else: labels.append(str(x))
    st.write(' | '.join([x for x in labels if x]) or '—')
    route = why.get('route', {})
    st.caption(f"Current: {route.get('active_path','—')} | Next: {route.get('next_path','—')} | Invalidator: {route.get('invalidator_path','—')}")


def render_market_page(bundle: dict, ihsg: bool = False, title: str = ''):
    _render_header(bundle, title or bundle.get('market','Market'))
    st.divider()
    if ihsg:
        _render_table(bundle.get('buy_now', {}).get('rows', []), ['ticker','bucket','entry_zone','invalidation','target','score','why_now'], 'Buy Now')
        st.divider()
        _render_table(bundle.get('front_run_buy', {}).get('rows', []), ['ticker','bucket','trigger','why_not_yet','trigger_distance','invalidation','score'], 'Front-Run Buy')
    else:
        _render_table(bundle.get('opportunity_now_long', {}).get('rows', []), ['ticker','bias','bucket','entry_zone','invalidation','target','score','why_now'], 'Best Longs Now')
        st.divider()
        _render_table(bundle.get('opportunity_now_short', {}).get('rows', []), ['ticker','bias','bucket','entry_zone','invalidation','target','score','why_now'], 'Best Shorts Now')
        st.divider()
        _render_table(bundle.get('front_run_long', {}).get('rows', []), ['ticker','bias','bucket','trigger','why_not_yet','trigger_distance','invalidation','score'], 'Front-Run Longs')
        st.divider()
        _render_table(bundle.get('front_run_short', {}).get('rows', []), ['ticker','bias','bucket','trigger','why_not_yet','trigger_distance','invalidation','score'], 'Front-Run Shorts')
    st.divider()
    _render_state_change(bundle.get('state_change', {}))
    st.divider()
    _render_market_state(bundle.get('market_state', {}))
    st.divider()
    _render_why(bundle)
    st.divider()
    _render_table(bundle.get('avoid_reduce', {}).get('rows', []), ['ticker','bias','bucket','problem','why_avoid','better_alternative'], 'Avoid / Reduce')
    if ihsg:
        st.divider()
        _render_table(bundle.get('defensive_shelter', {}).get('rows', []), ['ticker','type','why_defensive','trigger_to_use'], 'Defensive Shelter / Cash')
    with st.expander('Details'):
        st.json(bundle.get('details', {}), expanded=False)


def render_risk(snapshot: dict):
    st.title('Risk')
    risk = (snapshot.get('shared_core', {}) or {}).get('risk_summary', {}) or {}
    weather = (snapshot.get('shared_core', {}) or {}).get('weather', {}) or {}
    c1,c2,c3 = st.columns(3)
    c1.metric('Risk-Off Score', _score(risk.get('risk_off_score',0)))
    c2.metric('Crash State', weather.get('crash_state','—'))
    c3.metric('Execution Mode', ((snapshot.get('shared_core', {}) or {}).get('execution_mode', {}) or {}).get('label','—'))
    st.json(risk, expanded=False)


def render_diagnostics(snapshot: dict):
    st.title('Diagnostics')
    diag = snapshot.get('diagnostics', {}) or {}
    st.json(diag, expanded=False)