
from __future__ import annotations

import json
import pandas as pd
import streamlit as st

from utils.streamlit_utils import metric_card, info_card, render_pills
from ui.refactor_runtime import display_name


def _fmt_score(x):
    try:
        return f"{float(x):.1f}"
    except Exception:
        return '—'


def _df(rows, cols):
    if not rows:
        return pd.DataFrame(columns=cols)
    return pd.DataFrame([{c: r.get(c) for c in cols} for r in rows])


def _section_title(title: str):
    st.markdown(f"### {title}")


def _render_kpis(payload: dict):
    c1, c2, c3, c4 = st.columns(4, gap='small')
    with c1:
        metric_card('Rally / Scenario State', payload.get('rally_state', '—'), 'current board tone')
    with c2:
        metric_card('Action', payload.get('action', '—'), 'execution bias')
    with c3:
        metric_card('Exec Mode', payload.get('exec_mode', '—'), 'sizing posture')
    with c4:
        metric_card('Board', payload.get('board', '—'), 'headline summary')


def _render_scenario_card(title: str, s: dict):
    if not s:
        info_card(title, ['—'])
        return
    lines = [
        f"{s.get('name','-')}",
        f"Status: {s.get('status','-')} | Score { _fmt_score(s.get('score')) } | Weight {int(round(100*float(s.get('weight',0))))}%",
        f"Responders: {', '.join((s.get('first_responders') or [])[:3]) or '-'}",
        f"Invalidator: {', '.join((s.get('invalidators') or [])[:2]) or '-'}",
    ]
    info_card(title, lines, accent='#365b46' if float(s.get('direction',0)) >= 0 else '#6a3340')


def _render_scenario_board(cards: dict):
    c1, c2, c3, c4 = st.columns(4, gap='small')
    with c1:
        _render_scenario_card('Primary Scenario', cards.get('primary'))
    with c2:
        _render_scenario_card('Secondary Scenario', cards.get('secondary'))
    with c3:
        _render_scenario_card('Residual Drag', cards.get('residual_drag'))
    with c4:
        _render_scenario_card('Tail Risk', cards.get('tail_risk'))


def _render_why(payload: dict):
    _section_title('Why This Is Moving')
    drivers = payload.get('top_drivers', [])
    pills = []
    for item in drivers[:6]:
        label = item.get('label', '-') if isinstance(item, dict) else str(item)
        pills.append((label, 'blue'))
    if pills:
        render_pills(pills)
    route = payload.get('route', {})
    c1, c2, c3 = st.columns(3, gap='small')
    with c1:
        metric_card('Current Path', route.get('active_path', '—'), 'live route')
    with c2:
        metric_card('Next Path', route.get('next_path', '—'), 'watch route')
    with c3:
        metric_card('Invalidator', route.get('invalidator_path', '—'), 'what breaks current branch')


def _render_attack_matrix(matrix: dict):
    _section_title('Ticker Attack Matrix')
    rows = []
    order = [('US','US'),('IHSG','IHSG'),('FX','FX'),('COMMODITIES','Commodities'),('CRYPTO','Crypto')]
    for key,label in order:
        block = matrix.get(key, {})
        if key == 'IHSG':
            rows.append({
                'Market': label,
                'Now Long/Buy': ', '.join(block.get('best_buys_now', [])[:3]),
                'Now Short': '—',
                'Front-Run Long/Buy': ', '.join(block.get('front_run_buys', [])[:3]),
                'Front-Run Short': '—',
            })
        else:
            rows.append({
                'Market': label,
                'Now Long/Buy': ', '.join(block.get('best_longs_now', [])[:3]),
                'Now Short': ', '.join(block.get('best_shorts_now', [])[:3]),
                'Front-Run Long/Buy': ', '.join(block.get('front_run_longs', [])[:3]),
                'Front-Run Short': ', '.join(block.get('front_run_shorts', [])[:3]),
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_best_markets(best_now: list, best_next: list, risk_state: dict):
    c1, c2, c3 = st.columns(3, gap='small')
    with c1:
        info_card('Best Market Now', best_now[:4] or ['-'], accent='#365b46')
    with c2:
        info_card('Best Market Next', best_next[:4] or ['-'], accent='#5d4b3b')
    with c3:
        info_card('Risk State', [
            f"Conflict: {risk_state.get('conflict_label','-')}",
            f"Size cap: {risk_state.get('size_cap','-')}",
            f"Kill switch: {risk_state.get('kill_switch','-')}",
        ], accent='#6a3340')


def render_dashboard_page(payload: dict):
    st.title('Dashboard')
    _render_kpis(payload.get('executive_strip', {}))
    st.divider()
    _render_scenario_board(payload.get('scenario_cards', {}))
    st.divider()
    _render_why(payload.get('why_this_is_moving', {}))
    st.divider()
    _render_attack_matrix(payload.get('market_attack_matrix', {}))
    st.divider()
    _render_best_markets(payload.get('best_market_now', []), payload.get('best_market_next', []), payload.get('risk_state', {}))

    t1, t2 = st.tabs(['Scenarios & What-If', 'Cross-Asset'])
    with t1:
        scen = payload.get('scenario_lab', {}) or {}
        fam = scen.get('scenario_family', []) or []
        if fam:
            info_card('Scenario Families', fam[:8], accent='#365b46')
        whatif = scen.get('what_if_matrix', {}) or {}
        rows = []
        for k, v in list(whatif.items())[:10]:
            if isinstance(v, dict):
                rows.append({'Scenario': k, 'Impact': v.get('impact', v.get('summary', '-')), 'Why': v.get('why', '-')})
            else:
                rows.append({'Scenario': k, 'Impact': str(v), 'Why': '-'})
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        playbooks = scen.get('playbooks', []) or []
        if playbooks:
            st.markdown('**Playbooks**')
            for p in playbooks[:5]:
                info_card(str(p.get('name', 'Playbook')), [
                    p.get('description', '-'),
                    f"Evidence { _fmt_score(p.get('evidence_score')) } | Hypothesis { _fmt_score(p.get('hypothesis_score')) }",
                    f"Invalidators: {', '.join((p.get('invalidators') or [])[:2]) or '-'}",
                ], accent='#5d4b3b')
    with t2:
        cross = payload.get('cross_asset', {}) or {}
        info_card('Global Chain Map', [json.dumps(cross.get('global_chain_map', {}), ensure_ascii=False)[:500]], accent='#365b46')
        info_card('Conflict Map', [json.dumps(cross.get('conflict_map', {}), ensure_ascii=False)[:400]], accent='#6a3340')
        info_card('Confirmation Map', [json.dumps(cross.get('confirmation_map', {}), ensure_ascii=False)[:400]], accent='#28425f')


def _render_header(header: dict):
    metric_cols = st.columns(4, gap='small')
    with metric_cols[0]:
        metric_card('Net Bias', header.get('stance', '—'), 'market stance')
    with metric_cols[1]:
        metric_card('Conflict', header.get('conflict_label', '—'), 'board cleanliness')
    with metric_cols[2]:
        metric_card('Primary Driver', header.get('primary_driver', '—'), 'what helps here')
    with metric_cols[3]:
        metric_card('Main Drag', header.get('main_drag', '—'), 'what hurts here')
    st.caption(header.get('one_line', '—'))


def _render_table(rows: list[dict], cols: list[str], title: str):
    _section_title(title)
    df = _df(rows[:5], cols)
    rename = {
        'ticker':'Ticker','bias':'Bias','bucket':'Bucket','entry_zone':'Entry Zone','invalidation':'Invalidation','target':'Target',
        'score':'Score','why_now':'Why Now','trigger':'Trigger','why_not_yet':'Why Not Yet','trigger_distance':'Trigger Distance',
        'problem':'Problem','why_avoid':'Why Avoid','better_alternative':'Better Alternative','type':'Type','why_defensive':'Why Defensive','trigger_to_use':'Trigger to Use'
    }
    if not df.empty:
        df = df.rename(columns={k:v for k,v in rename.items() if k in df.columns})
        if 'Score' in df.columns:
            df['Score'] = df['Score'].map(_fmt_score)
        if 'Trigger Distance' in df.columns:
            df['Trigger Distance'] = df['Trigger Distance'].map(_fmt_score)
    st.dataframe(df, use_container_width=True, hide_index=True)


def _render_state_change(state_change: dict):
    _section_title('State Change')
    c1, c2, c3, c4 = st.columns(4, gap='small')
    c1.write('**Added**'); c1.write(', '.join(state_change.get('added', [])[:5]) or '—')
    c2.write('**Remaining**'); c2.write(', '.join(state_change.get('remaining', [])[:5]) or '—')
    c3.write('**Removed**'); c3.write(', '.join(state_change.get('removed', [])[:5]) or '—')
    c4.write('**Ripening**'); c4.write(', '.join(state_change.get('ripening', [])[:5]) or '—')


def _render_market_state(market_state: dict):
    _section_title('Market State')
    c1, c2, c3 = st.columns(3, gap='small')
    c1.write(f"Checklist Score: {market_state.get('checklist_score','—')}")
    c1.write(f"Macro Fit: {market_state.get('macro_fit','—')}")
    c2.write(f"Breadth: {market_state.get('breadth','—')}")
    c2.write(f"Leadership: {market_state.get('leadership','—')}")
    strong = market_state.get('strong_vs_weak', {}).get('strong', [])
    weak = market_state.get('strong_vs_weak', {}).get('weak', [])
    c3.write('Strong: ' + (', '.join(strong[:4]) or '—'))
    c3.write('Weak: ' + (', '.join(weak[:4]) or '—'))
    st.caption(market_state.get('one_line', ''))


def _render_why_moving(payload: dict):
    _section_title('Why This Is Moving')
    labels = []
    for x in payload.get('top_drivers', [])[:5]:
        labels.append(x.get('label', '-') if isinstance(x, dict) else str(x))
    if labels:
        render_pills([(x, 'blue') for x in labels])
    route = payload.get('route', {}) or {}
    st.caption(f"Current: {route.get('active_path','-')} | Next: {route.get('next_path','-')} | Invalidator: {route.get('invalidator_path','-')}")


def render_market_page(bundle: dict, ihsg: bool = False, title: str | None = None):
    st.title(title or ('IHSG' if ihsg else bundle.get('market', 'Market').title()))
    _render_header(bundle.get('header', {}))
    st.divider()
    if ihsg:
        _render_table(bundle.get('buy_now', {}).get('rows', []), ['ticker','bucket','entry_zone','invalidation','target','score','why_now'], 'Buy Now')
        st.divider()
        _render_table(bundle.get('front_run_buy', {}).get('rows', []), ['ticker','bucket','trigger','why_not_yet','trigger_distance','invalidation','score'], 'Front-Run Buy')
    else:
        groups = bundle.get('action_groups', {}) or {}
        _render_table(groups.get('now_long', []), ['ticker','bias','bucket','entry_zone','invalidation','target','score','why_now'], 'Best Longs Now')
        st.divider()
        _render_table(groups.get('now_short', []), ['ticker','bias','bucket','entry_zone','invalidation','target','score','why_now'], 'Best Shorts Now')
        st.divider()
        _render_table(groups.get('front_run_long', []), ['ticker','bias','bucket','trigger','why_not_yet','trigger_distance','invalidation','score'], 'Front-Run Longs')
        st.divider()
        _render_table(groups.get('front_run_short', []), ['ticker','bias','bucket','trigger','why_not_yet','trigger_distance','invalidation','score'], 'Front-Run Shorts')
    st.divider()
    _render_state_change(bundle.get('state_change', {}))
    st.divider()
    _render_market_state(bundle.get('market_state', {}))
    st.divider()
    _render_why_moving(bundle.get('why_this_is_moving', {}))
    st.divider()
    _render_table(bundle.get('avoid_reduce', {}).get('rows', []), ['ticker','bias','bucket','problem','why_avoid','better_alternative'], 'Avoid / Reduce')
    if ihsg:
        st.divider()
        _render_table(bundle.get('defensive_shelter', {}).get('rows', []), ['ticker','type','why_defensive','trigger_to_use'], 'Defensive Shelter / Cash')

    with st.expander('Open supporting detail blocks', expanded=False):
        details = bundle.get('details', {}) or {}
        a, b = st.columns(2, gap='small')
        with a:
            info_card('Checklist', [f"{x.get('label')}: {x.get('state')} ({_fmt_score(x.get('score'))})" for x in details.get('asset_checklist', [])[:6]], accent='#365b46')
            info_card('Execution', [json.dumps(details.get('execution', {}), ensure_ascii=False)[:600]], accent='#5d4b3b')
        with b:
            info_card('Catalyst Overlay', [json.dumps(details.get('catalyst_overlay', {}), ensure_ascii=False)[:600]], accent='#28425f')
            info_card('Route Branch', [json.dumps(details.get('route_branch', {}), ensure_ascii=False)[:600]], accent='#633535')


def render_risk_page(snapshot: dict):
    st.title('Risk')
    sh = snapshot.get('shared_core', {}) or {}
    risk = sh.get('risk_summary', {}) or {}
    weather = sh.get('weather', {}) or {}
    rotation = sh.get('rotation', {}) or {}
    c1, c2, c3, c4 = st.columns(4, gap='small')
    with c1:
        metric_card('Risk-Off State', risk.get('risk_off_state', '—'), 'broad defensive tone')
    with c2:
        metric_card('Crash State', risk.get('crash_state', '—'), 'tail risk state')
    with c3:
        metric_card('Weather', weather.get('weather_bias', '—'), 'trade/trend/tail blend')
    with c4:
        metric_card('Safe Harbor', rotation.get('safe_harbor', '—'), 'current escape route')
    a, b, c = st.columns(3, gap='small')
    with a:
        info_card('Top Risks', risk.get('top_reasons', [])[:4] or ['-'], accent='#6a3340')
    with b:
        info_card('Safe Harbors', [f"{x.get('route')}: {x.get('why')}" for x in (rotation.get('safe_harbors') or [])[:3]] or ['-'], accent='#365b46')
    with c:
        info_card('Best Beneficiaries', [f"{x.get('route')}: {x.get('why')}" for x in (rotation.get('beneficiaries') or [])[:3]] or ['-'], accent='#5d4b3b')


def render_diagnostics_page(snapshot: dict):
    st.title('Diagnostics')
    diag = snapshot.get('diagnostics', {}) or {}
    meta = snapshot.get('meta', {}) or {}
    c1, c2, c3 = st.columns(3, gap='small')
    with c1:
        info_card('Snapshot Meta', [f"schema: {meta.get('schema','-')}", f"runtime_mode: {meta.get('runtime_mode','-')}", f"as_of: {meta.get('as_of','-')}"] , accent='#365b46')
    with c2:
        info_card('Coverage Reports', [f"{k}: ranking {v.get('ranking_universe_size',0)} / bucket {v.get('bucket_universe_size',0)}" for k,v in (diag.get('coverage_reports', {}) or {}).items()], accent='#28425f')
    with c3:
        info_card('Validation', [json.dumps(diag.get('validation', {}), ensure_ascii=False)[:400]], accent='#5d4b3b')
    with st.expander('Open raw diagnostics', expanded=False):
        st.json(diag)
