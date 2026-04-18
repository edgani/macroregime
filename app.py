
from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable

import pandas as pd
import streamlit as st

from orchestration.build_snapshot import build_snapshot
from ui.theme import inject_theme
from ui.active_route_page import render_active_route_page
from ui.cross_asset_page import render_cross_asset_page
from ui.scenario_lab_page import render_scenario_lab_page
from ui.opportunity_board_page import render_opportunity_board_page
from ui.diagnostics_page import render_diagnostics_page
from ui.components.market_page_layout import render_market_page
from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from config.display_names import DISPLAY_NAME_MAP

st.set_page_config(page_title='MacroRegime Pro', layout='wide')
inject_theme()

MARKET_META = {
    'US Stocks': {'key': 'us', 'title': 'US Stocks', 'bucket_map': US_BUCKETS, 'buy_only': False, 'hub_title': 'Market Hubs US', 'checklist_title': 'US Checklist'},
    'IHSG': {'key': 'ihsg', 'title': 'IHSG', 'bucket_map': IHSG_BUCKETS, 'buy_only': True, 'hub_title': 'Market Hubs IHSG', 'checklist_title': 'IHSG Checklist'},
    'Forex': {'key': 'fx', 'title': 'Forex', 'bucket_map': FX_BUCKETS, 'buy_only': False, 'hub_title': 'Currency / Pair Hubs', 'checklist_title': 'Forex Checklist'},
    'Commodities': {'key': 'commodities', 'title': 'Commodities', 'bucket_map': COMMODITY_BUCKETS, 'buy_only': False, 'hub_title': 'Commodity Family Hubs', 'checklist_title': 'Commodities Checklist'},
    'Crypto': {'key': 'crypto', 'title': 'Crypto', 'bucket_map': CRYPTO_BUCKETS, 'buy_only': False, 'hub_title': 'Market Hubs Crypto', 'checklist_title': 'Crypto Checklist'},
}

BUCKET_ALIASES = {
    'us': {
        'growth': 'Growth', 'quality': 'Quality', 'defensives': 'Defensives', 'defensive': 'Defensives',
        'semis': 'Semis', 'software/cyber': 'Software/Cyber', 'energy': 'Energy', 'industrials': 'Industrials',
        'brokers/alt': 'Brokers/Alt', 'banks': 'Brokers/Alt', 'financials': 'Brokers/Alt',
    },
    'ihsg': {
        'banks': 'Banks', 'coal/energy': 'Coal/Energy', 'energy': 'Coal/Energy', 'metals': 'Metals',
        'telco/infra': 'Telco/Infra', 'consumer def': 'Consumer Def', 'consumer cyc': 'Consumer Cyc',
        'property/health': 'Property/Health',
    },
    'fx': {
        'majors': 'Majors', 'jpy crosses': 'JPY Crosses', 'core crosses': 'Core Crosses', 'asia overlay': 'Asia Overlay',
    },
    'commodities': {
        'precious': 'Precious', 'energy': 'Energy', 'industrial': 'Industrial', 'industrial metals': 'Industrial', 'agri/softs': 'Agri/Softs',
    },
    'crypto': {
        'majors': 'Majors', 'l1/l2': 'L1/L2', 'defi': 'DeFi', 'ai/data': 'AI/Data', 'rwa': 'RWA', 'infra': 'Infra', 'high beta': 'High Beta',
    },
}


def inject_app_css() -> None:
    st.markdown(
        """
        <style>
        .hero-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:6px 0 14px 0;}
        .hero-card {background:linear-gradient(180deg,rgba(15,33,64,.95),rgba(10,22,40,.98));border:1px solid rgba(99,135,190,.35);border-radius:16px;padding:14px 16px;box-shadow:0 10px 28px rgba(0,0,0,.18);min-height:110px;}
        .hero-kicker {font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;color:#8fb1e3;font-weight:800;margin-bottom:8px;}
        .hero-value {font-size:1.25rem;font-weight:800;color:#eef5ff;line-height:1.15;font-family:Syne, Inter, sans-serif;}
        .hero-sub {font-size:.78rem;color:#b8cbe6;margin-top:8px;line-height:1.3;}

        .flow-wrap {display:grid;grid-template-columns:1.1fr 56px 1.1fr 56px 1.1fr 56px 1.2fr;gap:0;align-items:center;margin:8px 0 16px 0;}
        .flow-box {background:linear-gradient(180deg,rgba(12,28,52,.96),rgba(9,18,34,.99));border:1px solid rgba(110,150,212,.38);border-radius:16px;padding:14px 14px 12px 14px;min-height:142px;box-shadow:0 10px 28px rgba(0,0,0,.16);}
        .flow-box.warn {border-color:rgba(232,177,76,.45);}
        .flow-box.bad {border-color:rgba(206,91,115,.45);}
        .flow-title {font-size:.68rem;letter-spacing:.08em;text-transform:uppercase;color:#8fb1e3;font-weight:800;margin-bottom:8px;}
        .flow-head {font-size:1.0rem;font-weight:800;color:#eef5ff;line-height:1.2;font-family:Syne, Inter, sans-serif;margin-bottom:8px;}
        .flow-text {font-size:.78rem;color:#b8cbe6;line-height:1.35;}
        .flow-arrow {display:flex;align-items:center;justify-content:center;color:#8fb1e3;font-size:1.8rem;font-weight:900;opacity:.9;}

        .pill-row {display:flex;flex-wrap:wrap;gap:8px;margin:4px 0 16px 0;}
        .pill {display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;border:1px solid rgba(106,141,194,.45);background:rgba(20,41,73,.72);font-size:.76rem;font-weight:700;color:#dce9ff;}
        .pill.warn {border-color:rgba(232,177,76,.50);background:rgba(95,72,24,.28);color:#f4ddb2;}
        .pill.bad {border-color:rgba(206,91,115,.50);background:rgba(90,28,41,.28);color:#ffd8df;}
        .pill.good {border-color:rgba(57,217,138,.42);background:rgba(20,74,53,.28);color:#dcffef;}

        .market-grid {display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin:4px 0 10px 0;}
        .market-card {background:linear-gradient(180deg,rgba(15,33,64,.95),rgba(10,22,40,.98));border:1px solid rgba(99,135,190,.35);border-radius:18px;padding:14px;min-height:290px;box-shadow:0 10px 28px rgba(0,0,0,.16);}
        .market-name {font-size:1rem;font-weight:800;color:#eef5ff;font-family:Syne, Inter, sans-serif;margin-bottom:4px;}
        .market-sub {font-size:.78rem;color:#b8cbe6;line-height:1.3;margin-bottom:10px;}
        .section-tag {font-size:.64rem;letter-spacing:.08em;text-transform:uppercase;color:#8fb1e3;font-weight:800;margin-top:10px;margin-bottom:6px;}
        .ticker-chip {display:inline-block;margin:0 6px 6px 0;padding:4px 10px;border-radius:999px;border:1px solid rgba(96,132,185,.48);background:rgba(20,41,73,.75);color:#eef5ff;font-size:.72rem;font-weight:800;}
        .ticker-chip.warn {border-color:rgba(232,177,76,.52);background:rgba(95,72,24,.30);color:#f4ddb2;}
        .ticker-chip.bad {border-color:rgba(206,91,115,.52);background:rgba(90,28,41,.30);color:#ffd8df;}
        .ticker-chip.good {border-color:rgba(57,217,138,.45);background:rgba(20,74,53,.30);color:#dcffef;}
        .market-line {height:1px;background:linear-gradient(90deg,rgba(125,179,255,.0),rgba(125,179,255,.45),rgba(125,179,255,.0));margin:10px 0;}

        .market-summary-grid {display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin:6px 0 14px 0;}
        .summary-box {background:linear-gradient(180deg,rgba(15,33,64,.95),rgba(10,22,40,.98));border:1px solid rgba(99,135,190,.35);border-radius:14px;padding:12px 14px;min-height:92px;}
        .summary-label {font-size:.66rem;letter-spacing:.08em;text-transform:uppercase;color:#8fb1e3;font-weight:800;margin-bottom:6px;}
        .summary-value {font-size:1rem;font-weight:800;color:#eef5ff;line-height:1.2;}
        .summary-note {font-size:.76rem;color:#b8cbe6;line-height:1.25;margin-top:6px;}

        .mini-flow {display:grid;grid-template-columns:1.1fr 44px 1.1fr 44px 1.1fr;align-items:center;margin:8px 0 16px 0;}
        .mini-arrow {display:flex;align-items:center;justify-content:center;color:#8fb1e3;font-size:1.5rem;font-weight:900;}
        .mini-box {background:linear-gradient(180deg,rgba(14,28,49,.96),rgba(8,18,32,.99));border:1px solid rgba(96,132,185,.38);border-radius:14px;padding:10px 12px;min-height:100px;}

        @media (max-width: 1100px) {
          .hero-grid, .market-summary-grid, .market-grid, .flow-wrap, .mini-flow {display:block;}
          .flow-arrow, .mini-arrow {display:none;}
          .hero-card, .market-card, .flow-box, .summary-box, .mini-box {margin-bottom:10px;}
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _display_name(value: str) -> str:
    if not value:
        return '—'
    return DISPLAY_NAME_MAP.get(value, value).replace('=X', '').replace('-USD', '')


def _unique(seq: Iterable[str], n: int | None = None) -> list[str]:
    out: list[str] = []
    for item in seq:
        s = str(item).strip()
        if s and s not in out:
            out.append(s)
        if n and len(out) >= n:
            break
    return out


def _extract_tickers(rows: list[dict] | None, side: str | None = None, limit: int = 5) -> list[str]:
    out: list[str] = []
    for row in rows or []:
        bias = str(row.get('bias', '')).lower()
        if side == 'long' and 'long' not in bias:
            continue
        if side == 'short' and 'short' not in bias:
            continue
        ticker = str(row.get('ticker') or row.get('display_name') or '').strip()
        if ticker and ticker not in out:
            out.append(ticker)
        if len(out) >= limit:
            break
    return out


def _resolve_bucket_tickers(market_key: str, names: list[str], limit: int = 5) -> list[str]:
    meta = next(v for v in MARKET_META.values() if v['key'] == market_key)
    bucket_map = meta['bucket_map']
    aliases = BUCKET_ALIASES.get(market_key, {})
    out: list[str] = []
    for raw in names:
        key = aliases.get(str(raw).strip().lower())
        if key and key in bucket_map:
            out.extend(bucket_map[key])
        elif str(raw).strip() in bucket_map:
            out.extend(bucket_map[str(raw).strip()])
    return _unique(out, limit)


def _fallback_action_lists(section: dict, market_key: str) -> dict[str, list[str]]:
    route = section.get('route_branch', {}) or {}
    strong_weak = section.get('strong_weak', {}) or {}
    branch = section.get('route_branch', {}) or {}
    winners = list(route.get('winners', []) or [])
    losers = list(route.get('losers', []) or [])

    names_long = []
    names_short = []

    for key in ['strong_names', 'strong_tokens', 'strong_pairs']:
        names_long.extend(strong_weak.get(key, []) or [])
    for key in ['weak_names', 'weak_tokens', 'weak_pairs']:
        names_short.extend(strong_weak.get(key, []) or [])

    if not names_long:
        for key in ['strong_sectors', 'strong_families', 'strong_currencies']:
            names_long.extend(strong_weak.get(key, []) or [])
    if not names_short:
        for key in ['weak_sectors', 'weak_families', 'weak_currencies']:
            names_short.extend(strong_weak.get(key, []) or [])

    long_now = _resolve_bucket_tickers(market_key, names_long or winners, 5)
    short_now = _resolve_bucket_tickers(market_key, names_short or losers, 5)

    next_names = list((section.get('next_path', {}) or {}).get('market_routes', {}).get(market_key, []) or [])
    if isinstance(next_names, str):
        next_names = [next_names]
    front_long = _resolve_bucket_tickers(market_key, next_names or winners, 5)
    front_short = _resolve_bucket_tickers(market_key, losers or names_short, 5)

    if market_key == 'ihsg':
        defensive = _resolve_bucket_tickers(market_key, ['Consumer Def', 'Banks'], 5)
        avoid = short_now or _resolve_bucket_tickers(market_key, ['Consumer Cyc', 'Property/Health'], 5)
        return {
            'buy_now': long_now,
            'front_run_buy': front_long,
            'avoid_reduce': avoid,
            'defensive': defensive,
        }

    avoid = short_now or front_short
    return {
        'long_now': long_now,
        'short_now': short_now,
        'front_run_long': front_long,
        'front_run_short': front_short,
        'avoid_reduce': avoid,
    }


def _market_actions(snapshot: dict, market_key: str) -> dict[str, list[str]]:
    section = snapshot.get(market_key, {}) or {}
    now_rows = section.get('top_opportunities_now', []) or []
    next_rows = section.get('top_opportunities_next', []) or []
    fallback = _fallback_action_lists(section, market_key)

    if market_key == 'ihsg':
        buy_now = _extract_tickers(now_rows, 'long', 5) or fallback['buy_now']
        fr_buy = _extract_tickers(next_rows, 'long', 5) or fallback['front_run_buy']
        avoid = _extract_tickers(now_rows, 'short', 5) or fallback['avoid_reduce']
        return {
            'buy_now': buy_now,
            'front_run_buy': fr_buy,
            'avoid_reduce': avoid,
            'defensive': fallback['defensive'],
        }

    return {
        'long_now': _extract_tickers(now_rows, 'long', 5) or fallback['long_now'],
        'short_now': _extract_tickers(now_rows, 'short', 5) or fallback['short_now'],
        'front_run_long': _extract_tickers(next_rows, 'long', 5) or fallback['front_run_long'],
        'front_run_short': _extract_tickers(next_rows, 'short', 5) or fallback['front_run_short'],
        'avoid_reduce': fallback['avoid_reduce'],
    }


def _risk_label(snapshot: dict) -> str:
    state = (snapshot.get('shared_core', {}) or {}).get('risk_summary', {}) or {}
    ro = str(state.get('risk_off_state', '-') or '-')
    crash = str(state.get('crash_state', '-') or '-')
    return f"Risk-off {ro} / crash {crash}"


def _scenario_cards(snapshot: dict) -> list[dict]:
    shared = snapshot.get('shared_core', {}) or {}
    family = list(shared.get('scenario_family', []) or [])
    lab = snapshot.get('scenario_lab', {}) or {}
    dominant = str(snapshot.get('master_routes', {}).get('dominant_family', family[0] if family else '-')).replace('_', ' ')
    primary = {'title': 'Primary', 'name': dominant.title(), 'note': str(shared.get('resolved_regime', {}).get('resolved_language', '-'))}
    secondary = {'title': 'Secondary', 'name': (family[1] if len(family) > 1 else lab.get('next_resolved_regime', '-')), 'note': str(lab.get('continuation_path', '-'))}
    residual = {'title': 'Residual Drag', 'name': (shared.get('top_risks', ['-'])[0] if shared.get('top_risks') else '-'), 'note': ', '.join((shared.get('top_risks') or [])[:2]) or '-'}
    tail = {'title': 'Tail Risk', 'name': (family[2] if len(family) > 2 else 'Shock branch'), 'note': ', '.join((lab.get('invalidators') or [])[:2]) or '-'}
    return [primary, secondary, residual, tail]


def _render_chip_list(items: list[str], tone: str = 'neutral') -> str:
    cls = ''
    if tone == 'warn':
        cls = ' warn'
    elif tone == 'bad':
        cls = ' bad'
    elif tone == 'good':
        cls = ' good'
    return ''.join(f"<span class='ticker-chip{cls}'>{html.escape(_display_name(x))}</span>" for x in items[:4]) or "<span class='ticker-chip'>—</span>"


def _render_dashboard(snapshot: dict) -> None:
    shared = snapshot.get('shared_core', {}) or {}
    dashboard = snapshot.get('dashboard', {}) or {}
    routes = snapshot.get('master_routes', {}) or {}
    status = dashboard.get('status_ribbon', {}) or shared.get('status_ribbon', {}) or {}
    exec_mode = shared.get('execution_mode', {}) or {}
    strongest = dashboard.get('strongest_markets', []) or snapshot.get('home_summary', {}).get('strongest_markets', []) or []
    best_now = ', '.join(str(x.get('market')) for x in strongest[:2]) or '-'
    best_next = str((shared.get('next_path', {}) or {}).get('next_resolved_regime', '-'))
    top_driver = str((shared.get('top_drivers') or ['-'])[0])

    hero = [
        ('Board State', status.get('resolved_language', '-'), f"Structural {status.get('structural_quad','-')} · Monthly {status.get('monthly_quad','-')}"),
        ('Action Now', exec_mode.get('execute_mode', '-'), f"Size {float(exec_mode.get('size_multiplier', 0.0) or 0.0):.2f}x"),
        ('Main Driver', top_driver, 'what is moving the tape now'),
        ('Risk Alert', _risk_label(snapshot), ', '.join((shared.get('top_risks') or [])[:2]) or '-'),
    ]
    html_cards = "".join(
        f"<div class='hero-card'><div class='hero-kicker'>{html.escape(k)}</div><div class='hero-value'>{html.escape(v)}</div><div class='hero-sub'>{html.escape(s)}</div></div>"
        for k,v,s in hero
    )
    st.markdown(f"<div class='hero-grid'>{html_cards}</div>", unsafe_allow_html=True)

    scenarios = _scenario_cards(snapshot)
    flow_html = []
    flow_boxes = [
        ('Macro / Regime', status.get('resolved_language', '-'), f"Confidence {status.get('confidence_band','-')} · Health {status.get('health','-')}", ''),
        ('Scenario Stack', scenarios[0]['name'], f"Secondary: {scenarios[1]['name']} · Drag: {scenarios[2]['name']}", 'warn'),
        ('Market Effect', best_now, 'Which markets are cleanest now', ''),
        ('Ticker Action', 'Now + Front-Run', 'Move from context to actual names', 'good'),
    ]
    for idx, (title, head, text, tone) in enumerate(flow_boxes):
        flow_html.append(f"<div class='flow-box {tone}'><div class='flow-title'>{html.escape(title)}</div><div class='flow-head'>{html.escape(str(head))}</div><div class='flow-text'>{html.escape(str(text))}</div></div>")
        if idx < len(flow_boxes)-1:
            flow_html.append("<div class='flow-arrow'>→</div>")
    st.markdown(f"<div class='flow-wrap'>{''.join(flow_html)}</div>", unsafe_allow_html=True)

    st.markdown("**Why This Is Moving**")
    pills = []
    for i, item in enumerate((shared.get('top_drivers') or dashboard.get('top_drivers') or [])[:6]):
        tone = 'good' if i < 2 else ('warn' if i < 4 else 'bad')
        pills.append(f"<span class='pill {tone}'>{html.escape(str(item))}</span>")
    st.markdown(f"<div class='pill-row'>{''.join(pills) or '<span class=\'pill\'>No active drivers</span>'}</div>", unsafe_allow_html=True)

    # Market attack matrix
    cards = []
    for page_name in ['US Stocks', 'IHSG', 'Forex', 'Commodities', 'Crypto']:
        meta = MARKET_META[page_name]
        actions = _market_actions(snapshot, meta['key'])
        section = snapshot.get(meta['key'], {}) or {}
        header = section.get('market_hub', {}) or section.get('macro_vs_market', {}) or {}
        sub = str(header.get('operating_regime', section.get('route_branch', {}).get('summary', '-')))
        body = [
            f"<div class='section-tag'>{'Buy Now' if meta['buy_only'] else 'Long Now'}</div>{_render_chip_list(actions.get('buy_now', actions.get('long_now', [])), 'good')}",
            f"<div class='section-tag'>{'Front-Run Buy' if meta['buy_only'] else 'Front-Run'}</div>{_render_chip_list(actions.get('front_run_buy', actions.get('front_run_long', [])), 'warn')}",
        ]
        if meta['buy_only']:
            body.append(f"<div class='section-tag'>Avoid / Defensive</div>{_render_chip_list(actions.get('avoid_reduce', []) + actions.get('defensive', []), 'bad')}")
        else:
            body.append(f"<div class='section-tag'>Short Now</div>{_render_chip_list(actions.get('short_now', []), 'bad')}")
            body.append(f"<div class='section-tag'>Front-Run Short</div>{_render_chip_list(actions.get('front_run_short', []), 'warn')}")
        cards.append(f"<div class='market-card'><div class='market-name'>{html.escape(page_name)}</div><div class='market-sub'>{html.escape(sub)}</div><div class='market-line'></div>{''.join(body)}</div>")
    st.markdown(f"<div class='market-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)

    st.markdown('---')
    tab_overview, tab_route, tab_scen, tab_cross, tab_board = st.tabs(['Control Tower', 'Active Route', 'Scenarios & What-If', 'Cross-Asset', 'Opportunity Board'])
    with tab_overview:
        c1, c2 = st.columns(2, gap='small')
        with c1:
            st.subheader('Current Path')
            st.caption(str(routes.get('dominant_summary', '-')))
            st.write(f"**Safe harbor:** {_display_name(str(status.get('safe_harbor','-')))}")
            st.write(f"**Best beneficiary:** {_display_name(str(status.get('best_beneficiary','-')))}")
            st.write(f"**Main invalidator:** {snapshot.get('home_summary', {}).get('main_risk', '-')}")
        with c2:
            st.subheader('What to watch next')
            nxt = shared.get('next_path', {}) or {}
            st.write(f"**Next path:** {nxt.get('next_resolved_regime', '-')}")
            st.write(f"**Triggers:** {', '.join((nxt.get('triggers') or [])[:2]) or '-'}")
            st.write(f"**Invalidators:** {', '.join((nxt.get('invalidators') or [])[:2]) or '-'}")
    with tab_route:
        render_active_route_page(snapshot)
    with tab_scen:
        render_scenario_lab_page(snapshot)
    with tab_cross:
        render_cross_asset_page(snapshot)
    with tab_board:
        render_opportunity_board_page(snapshot)


def _render_action_table(title: str, tickers: list[str], bias: str, why: str, invalidator: str, buy_only: bool = False) -> None:
    st.subheader(title)
    rows = []
    label_bias = 'Buy' if buy_only and bias == 'Long' else bias
    for t in tickers[:5]:
        rows.append({
            'Ticker': _display_name(t),
            'Bias': label_bias,
            'Entry / Trigger': 'use nearby pullback / confirmation zone',
            'Invalidation': invalidator,
            'Why': why,
        })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info('Belum ada ticker yang cukup bersih di section ini.')


def _render_market_shell(snapshot: dict, page_name: str) -> None:
    meta = MARKET_META[page_name]
    section = snapshot.get(meta['key'], {}) or {}
    actions = _market_actions(snapshot, meta['key'])
    branch = section.get('route_branch', {}) or {}
    hub = section.get('market_hub', {}) or {}
    execn = section.get('execution', {}) or {}

    st.title(page_name)
    header_html = []
    summary_boxes = [
        ('Bias', execn.get('bias', '-'), execn.get('mode', '-')),
        ('Conflict / Conviction', hub.get('confidence_band', '-'), branch.get('summary', '-')),
        ('Primary Driver', ', '.join((branch.get('winners') or [])[:2]) or '-', branch.get('route_interpretation', '-')),
        ('Main Drag', ', '.join((branch.get('losers') or [])[:2]) or '-', ', '.join((branch.get('market_invalidators') or [])[:1]) or '-'),
    ]
    for label, value, note in summary_boxes:
        header_html.append(f"<div class='summary-box'><div class='summary-label'>{html.escape(label)}</div><div class='summary-value'>{html.escape(str(value))}</div><div class='summary-note'>{html.escape(str(note))}</div></div>")
    st.markdown(f"<div class='market-summary-grid'>{''.join(header_html)}</div>", unsafe_allow_html=True)

    flow_nodes = [
        ('Scenario Effect', branch.get('summary', '-')),
        ('Sector / Style Effect', ', '.join((branch.get('winners') or [])[:3]) or '-'),
        ('Ticker Action', 'See boxes below'),
    ]
    flow_html = []
    for idx, (title, value) in enumerate(flow_nodes):
        flow_html.append(f"<div class='mini-box'><div class='flow-title'>{html.escape(title)}</div><div class='flow-head'>{html.escape(str(value))}</div></div>")
        if idx < len(flow_nodes)-1:
            flow_html.append("<div class='mini-arrow'>→</div>")
    st.markdown(f"<div class='mini-flow'>{''.join(flow_html)}</div>", unsafe_allow_html=True)

    if meta['buy_only']:
        c1, c2, c3 = st.columns(3, gap='small')
        with c1:
            _render_action_table('Buy Now', actions['buy_now'], 'Long', execn.get('mode', '-'), (branch.get('market_invalidators') or ['-'])[0], buy_only=True)
        with c2:
            _render_action_table('Front-Run Buy', actions['front_run_buy'], 'Long', 'Needs cleaner trigger / confirmation', (branch.get('market_invalidators') or ['-'])[0], buy_only=True)
        with c3:
            st.subheader('Avoid / Defensive')
            avoid = actions.get('avoid_reduce', [])[:3]
            defensive = actions.get('defensive', [])[:3]
            st.markdown("**Avoid / Reduce**")
            st.markdown(_render_chip_list(avoid, 'bad'), unsafe_allow_html=True)
            st.markdown("**Defensive Shelter / Cash**")
            st.markdown(_render_chip_list(defensive, 'warn'), unsafe_allow_html=True)
    else:
        c1, c2, c3 = st.columns(3, gap='small')
        with c1:
            _render_action_table('Long Now', actions['long_now'], 'Long', execn.get('mode', '-'), (branch.get('market_invalidators') or ['-'])[0])
        with c2:
            _render_action_table('Short Now', actions['short_now'], 'Short', 'Best used on weak bounces / failures', (branch.get('market_invalidators') or ['-'])[0])
        with c3:
            _render_action_table('Front-Run', actions['front_run_long'], 'Long', 'Secondary branch can become primary', (branch.get('market_invalidators') or ['-'])[0])
            if actions.get('front_run_short'):
                st.markdown('**Front-Run Shorts**')
                st.markdown(_render_chip_list(actions['front_run_short'], 'warn'), unsafe_allow_html=True)

    with st.expander('Detailed context / full market page', expanded=False):
        render_market_page(
            title=meta['title'],
            section=section,
            checklist_title=meta['checklist_title'],
            hub_title=meta['hub_title'],
            master_graph=snapshot.get('master_graph', {}),
            market_key=meta['key'],
        )


def _render_risk_page(snapshot: dict) -> None:
    st.title('Risk')
    shared = snapshot.get('shared_core', {}) or {}
    risk = shared.get('risk_summary', {}) or {}
    exec_mode = shared.get('execution_mode', {}) or {}
    status = shared.get('status_ribbon', {}) or {}

    cards = [
        ('Execution Mode', exec_mode.get('execute_mode', '-'), f"Size {float(exec_mode.get('size_multiplier', 0.0) or 0.0):.2f}x"),
        ('Risk-Off State', risk.get('risk_off_state', '-'), ', '.join((risk.get('risk_off_reasons') or [])[:2]) or '-'),
        ('Crash State', risk.get('crash_state', '-'), ', '.join((risk.get('crash_reasons') or [])[:2]) or '-'),
        ('Safe Harbor', status.get('safe_harbor', '-'), f"Best beneficiary {status.get('best_beneficiary', '-')}")
    ]
    html_cards = ''.join(f"<div class='hero-card'><div class='hero-kicker'>{html.escape(k)}</div><div class='hero-value'>{html.escape(str(v))}</div><div class='hero-sub'>{html.escape(str(s))}</div></div>" for k,v,s in cards)
    st.markdown(f"<div class='hero-grid'>{html_cards}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2, gap='small')
    with c1:
        st.subheader('What can break the board')
        st.write(', '.join((shared.get('top_risks') or [])[:5]) or '-')
        nxt = shared.get('next_path', {}) or {}
        st.write(f"**Invalidators:** {', '.join((nxt.get('invalidators') or [])[:5]) or '-'}")
    with c2:
        st.subheader('Execution notes')
        for line in (exec_mode.get('notes') or [])[:5]:
            st.write(f"- {line}")


def _render_diagnostics(snapshot: dict) -> None:
    render_diagnostics_page(snapshot)


@st.cache_data(show_spinner=False)
def _load_snapshot_cached(open_mode: str, compact_mode: bool) -> dict:
    return build_snapshot(open_mode=open_mode, compact_mode=compact_mode, prefer_saved=(open_mode == 'snapshot_only'))


def _load_snapshot(force_refresh: bool, use_saved: bool) -> dict:
    if force_refresh:
        st.cache_data.clear()
        return build_snapshot(open_mode='force_rebuild', compact_mode=False, force_refresh=True, prefer_saved=False)
    mode = 'snapshot_only' if use_saved else 'smart_fresh'
    return _load_snapshot_cached(mode, False)


def main() -> None:
    inject_app_css()
    with st.sidebar:
        st.markdown("### 🧭 MacroRegime Pro")
        refresh = st.button('🔄 Refresh snapshot', use_container_width=True)
        use_saved = st.toggle('Use saved snapshot when available', value=True)
        st.markdown('---')
        page = st.radio('Page', ['Dashboard', 'US Stocks', 'IHSG', 'Forex', 'Commodities', 'Crypto', 'Risk', 'Diagnostics'])
        st.caption('Urutan baca: Dashboard → pilih market → Risk → Diagnostics')

    snapshot = _load_snapshot(refresh, use_saved)

    if page == 'Dashboard':
        _render_dashboard(snapshot)
    elif page in MARKET_META:
        _render_market_shell(snapshot, page)
    elif page == 'Risk':
        _render_risk_page(snapshot)
    elif page == 'Diagnostics':
        _render_diagnostics(snapshot)


if __name__ == '__main__':
    main()
