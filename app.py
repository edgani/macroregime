from __future__ import annotations

import html
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from config.display_names import DISPLAY_NAME_MAP
from config.settings import APP_NAME, APP_VERSION, LIVE_RUNTIME_MODE
from data.snapshot_store import load_snapshot, load_snapshot_manifest
from orchestration.build_snapshot import build_snapshot
from ui.active_route_page import render_active_route_page
from ui.commodities_page import render_commodities_page
from ui.cross_asset_page import render_cross_asset_page
from ui.crypto_page import render_crypto_page
from ui.dashboard_main_page import render_dashboard_main_page
from ui.diagnostics_page import render_diagnostics_page
from ui.forex_page import render_forex_page
from ui.ihsg_page import render_ihsg_page
from ui.opportunity_board_page import render_opportunity_board_page
from ui.scenarios_page import render_scenarios_page
from ui.theme import inject_theme
from ui.us_stocks_page import render_us_stocks_page
from utils.streamlit_utils import info_card, metric_card, render_pills

st.set_page_config(page_title=APP_NAME, page_icon="🧭", layout="wide", initial_sidebar_state="expanded")
inject_theme()

MARKET_PAGE_TO_KEY = {
    "US Stocks": "us",
    "IHSG": "ihsg",
    "Forex": "fx",
    "Commodities": "commodities",
    "Crypto": "crypto",
}

MARKET_ATTACK_KEY = {
    "us": "US",
    "ihsg": "IHSG",
    "fx": "FX",
    "commodities": "Commodities",
    "crypto": "Crypto",
}

BUCKETS = {
    "us": US_BUCKETS,
    "ihsg": IHSG_BUCKETS,
    "fx": FX_BUCKETS,
    "commodities": COMMODITY_BUCKETS,
    "crypto": CRYPTO_BUCKETS,
}

MARKET_CONTEXT_RENDERERS = {
    "us": render_us_stocks_page,
    "ihsg": render_ihsg_page,
    "fx": render_forex_page,
    "commodities": render_commodities_page,
    "crypto": render_crypto_page,
}

FALLBACKS = {
    "us": {
        "now_long": ["IWM", "RSP", "XLF"],
        "now_short": ["UUP", "XLP", "TLT"],
        "front_run_long": ["XLI", "AMD", "BAC"],
        "front_run_short": ["XLY", "QQQ", "XLU"],
        "avoid": ["NVDA", "TSLA", "late mega-cap chase"],
    },
    "ihsg": {
        "buy_now": ["BBCA.JK", "BMRI.JK", "ADRO.JK"],
        "front_run_buy": ["BRIS.JK", "ANTM.JK", "CTRA.JK"],
        "avoid": ["ACES.JK", "PGAS.JK", "BUMI.JK"],
        "defensive": ["ICBP.JK", "KLBF.JK", "Cash"],
    },
    "fx": {
        "now_long": ["EURUSD=X", "AUDUSD=X", "NZDUSD=X"],
        "now_short": ["JPY=X", "CHF=X", "IDR=X"],
        "front_run_long": ["EURJPY=X", "GBPUSD=X", "AUDUSD=X"],
        "front_run_short": ["CAD=X", "JPY=X", "IDR=X"],
        "avoid": ["GBPJPY=X", "SGD=X", "CNH=X"],
    },
    "commodities": {
        "now_long": ["GC=F", "HG=F", "DBC"],
        "now_short": ["CL=F", "BZ=F", "NG=F"],
        "front_run_long": ["SI=F", "HG=F", "GSG"],
        "front_run_short": ["CL=F", "BZ=F", "DBC"],
        "avoid": ["ZC=F", "ZW=F", "late oil chase"],
    },
    "crypto": {
        "now_long": ["BTC-USD", "ETH-USD", "SOL-USD"],
        "now_short": ["DOGE-USD", "ADA-USD", "XRP-USD"],
        "front_run_long": ["LINK-USD", "AVAX-USD", "BNB-USD"],
        "front_run_short": ["DOGE-USD", "XRP-USD", "weak beta"],
        "avoid": ["ADA-USD", "late meme chase", "low-liquidity beta"],
    },
}


def _norm(x: Any) -> str:
    return ''.join(ch.lower() for ch in str(x or '') if ch.isalnum())


def _disp(sym: str) -> str:
    return DISPLAY_NAME_MAP.get(sym, sym.replace('.JK', ''))


def _display_list(symbols: list[str], max_items: int = 3) -> str:
    vals = [_disp(s) for s in (symbols or [])[:max_items]]
    return ', '.join(vals) if vals else '—'


def _build_bucket_lookup(market_key: str) -> dict[str, list[str]]:
    d = BUCKETS.get(market_key, {}) or {}
    return {_norm(k): list(v) for k, v in d.items()}


def _unique(items: list[str]) -> list[str]:
    out = []
    seen = set()
    for x in items:
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _symbols_from_buckets(market_key: str, bucket_names: list[str], max_items: int = 6) -> list[str]:
    lookup = _build_bucket_lookup(market_key)
    out: list[str] = []
    for name in bucket_names or []:
        out.extend(lookup.get(_norm(name), []))
    return _unique(out)[:max_items]


def _extract_bucket_names(section: dict) -> tuple[list[str], list[str]]:
    sw = section.get('strong_weak', {}) or {}
    strong_keys = ['strong_sectors', 'strong_currencies', 'strong_families']
    weak_keys = ['weak_sectors', 'weak_currencies', 'weak_families']
    strong = []
    weak = []
    for k in strong_keys:
        strong.extend(sw.get(k, []) or [])
    for k in weak_keys:
        weak.extend(sw.get(k, []) or [])
    rb = section.get('route_branch', {}) or {}
    strong.extend(rb.get('winners', []) or [])
    weak.extend(rb.get('losers', []) or [])
    return _unique([str(x) for x in strong]), _unique([str(x) for x in weak])


def _build_market_attack(snapshot: dict, market_key: str) -> dict[str, list[str]]:
    section = snapshot.get(market_key, {}) or {}
    fallback = FALLBACKS.get(market_key, {})
    strong_buckets, weak_buckets = _extract_bucket_names(section)
    strong_symbols = _symbols_from_buckets(market_key, strong_buckets)
    weak_symbols = _symbols_from_buckets(market_key, weak_buckets)

    if market_key == 'ihsg':
        buy_now = strong_symbols[:3] or fallback.get('buy_now', [])
        front_run_buy = strong_symbols[3:6] or fallback.get('front_run_buy', [])
        avoid = weak_symbols[:3] or fallback.get('avoid', [])
        defensive = fallback.get('defensive', [])
        return {
            'best_buys_now': buy_now,
            'front_run_buys': front_run_buy,
            'avoid_reduce': avoid,
            'defensive_shelter': defensive,
        }

    now_long = strong_symbols[:3] or fallback.get('now_long', [])
    front_run_long = strong_symbols[3:6] or fallback.get('front_run_long', [])
    now_short = weak_symbols[:3] or fallback.get('now_short', [])
    front_run_short = weak_symbols[3:6] or fallback.get('front_run_short', [])
    avoid = weak_symbols[:3] or fallback.get('avoid', [])
    return {
        'best_longs_now': now_long,
        'best_shorts_now': now_short,
        'front_run_longs': front_run_long,
        'front_run_shorts': front_run_short,
        'avoid_reduce': avoid,
    }


def _build_attack_matrix(snapshot: dict) -> dict[str, dict[str, list[str]]]:
    return {MARKET_ATTACK_KEY[k]: _build_market_attack(snapshot, k) for k in MARKET_ATTACK_KEY}


def _get_snapshot(force_refresh: bool = False) -> dict:
    if force_refresh:
        snap = build_snapshot(force_refresh=True, prefer_saved=False, compact_mode=True, open_mode='smart_fresh')
        st.session_state['snapshot'] = snap
        return snap
    if 'snapshot' in st.session_state and isinstance(st.session_state['snapshot'], dict):
        return st.session_state['snapshot']
    snap = load_snapshot()
    if not isinstance(snap, dict):
        with st.spinner('Building fresh snapshot...'):
            snap = build_snapshot(force_refresh=False, prefer_saved=False, compact_mode=True, open_mode=LIVE_RUNTIME_MODE)
    st.session_state['snapshot'] = snap
    return snap


def _render_board_summary(snapshot: dict) -> None:
    shared = snapshot.get('shared_core', {}) or {}
    resolved = shared.get('resolved_regime', {}) or {}
    execution = shared.get('execution_mode', {}) or {}
    risk = shared.get('risk_summary', {}) or {}
    route = snapshot.get('master_routes', {}) or {}

    c1, c2, c3, c4 = st.columns(4, gap='small')
    with c1:
        metric_card('Board State', resolved.get('resolved_language', resolved.get('operating_regime', '-')), 'lihat ini dulu')
    with c2:
        metric_card('Action Now', execution.get('execute_mode', execution.get('mode', '-')), f"size x{execution.get('size_multiplier', 0):.2f}")
    with c3:
        metric_card('Main Driver', route.get('dominant_family', '-').replace('_', ' '), route.get('dominant_summary', '-'))
    with c4:
        metric_card('Risk Alert', risk.get('risk_off_state', '-'), ' | '.join((risk.get('top_reasons') or ['-'])[:2]))


def _render_route_flow(snapshot: dict) -> None:
    shared = snapshot.get('shared_core', {}) or {}
    nxt = shared.get('next_path', {}) or {}
    routes = snapshot.get('master_routes', {}) or {}
    current = routes.get('dominant_summary', '-')
    next_regime = nxt.get('next_resolved_regime', '-')
    invalidator = ', '.join((routes.get('global_invalidators') or [])[:2]) or '-'
    c1, c2, c3 = st.columns(3, gap='small')
    with c1:
        info_card('Current Path', [str(current), f"Family: {routes.get('dominant_family', '-')}"], accent='#365b46')
    with c2:
        info_card('Next Path', [f"Next operating: {next_regime}", f"Monthly: {nxt.get('next_monthly_quad', '-')}", f"Structural: {nxt.get('next_structural_quad', '-')}"], accent='#4d425f')
    with c3:
        info_card('If This Fails', [f"Invalidators: {invalidator}", f"Flip hazard: {100*float(nxt.get('flip_hazard', 0.0)):.0f}%"], accent='#6a3340')


def _render_driver_pills(snapshot: dict) -> None:
    dashboard = snapshot.get('dashboard', {}) or {}
    drivers = dashboard.get('top_drivers', [])[:5]
    risks = dashboard.get('top_risks', [])[:3]
    pills = [(f"Driver: {d}", 'good') for d in drivers] + [(f"Risk: {r}", 'warn') for r in risks]
    if pills:
        render_pills(pills)


def _render_attack_matrix(snapshot: dict) -> None:
    st.subheader('Ticker Attack Matrix')
    matrix = _build_attack_matrix(snapshot)
    rows = []
    for market, block in matrix.items():
        if market == 'IHSG':
            rows.append({
                'Market': market,
                'Now': _display_list(block.get('best_buys_now')),
                'Front-Run': _display_list(block.get('front_run_buys')),
                'Avoid / Defensive': _display_list((block.get('avoid_reduce') or []) + (block.get('defensive_shelter') or []), 4),
            })
        else:
            rows.append({
                'Market': market,
                'Long Now': _display_list(block.get('best_longs_now')),
                'Short Now': _display_list(block.get('best_shorts_now')),
                'Front-Run Long': _display_list(block.get('front_run_longs')),
                'Front-Run Short': _display_list(block.get('front_run_shorts')),
            })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def _render_dashboard(snapshot: dict) -> None:
    st.title('Dashboard')
    meta = snapshot.get('meta', {}) or {}
    st.caption(f"Generated: {meta.get('generated_at', '-')} | Schema: {meta.get('schema', APP_VERSION)}")
    _render_board_summary(snapshot)
    st.divider()
    _render_route_flow(snapshot)
    _render_driver_pills(snapshot)
    st.divider()
    _render_attack_matrix(snapshot)
    st.divider()
    tabs = st.tabs(['Control Tower', 'Scenarios & What-If', 'Cross-Asset', 'Active Route', 'Opportunity Board'])
    with tabs[0]:
        render_dashboard_main_page(snapshot)
    with tabs[1]:
        render_scenarios_page(snapshot)
    with tabs[2]:
        render_cross_asset_page(snapshot)
    with tabs[3]:
        render_active_route_page(snapshot)
    with tabs[4]:
        render_opportunity_board_page(snapshot)


def _rows_from_action(block: dict, mode: str) -> list[dict]:
    if mode == 'ihsg':
        return [
            {'Ticker': _display_list(block.get('best_buys_now')), 'Action': 'Buy Now'},
            {'Ticker': _display_list(block.get('front_run_buys')), 'Action': 'Front-Run Buy'},
            {'Ticker': _display_list(block.get('avoid_reduce')), 'Action': 'Avoid / Reduce'},
            {'Ticker': _display_list(block.get('defensive_shelter')), 'Action': 'Defensive / Cash'},
        ]
    return [
        {'Ticker': _display_list(block.get('best_longs_now')), 'Action': 'Long Now'},
        {'Ticker': _display_list(block.get('best_shorts_now')), 'Action': 'Short Now'},
        {'Ticker': _display_list(block.get('front_run_longs')), 'Action': 'Front-Run Long'},
        {'Ticker': _display_list(block.get('front_run_shorts')), 'Action': 'Front-Run Short'},
        {'Ticker': _display_list(block.get('avoid_reduce')), 'Action': 'Avoid / Reduce'},
    ]


def _render_market_page(snapshot: dict, market_key: str, title: str) -> None:
    section = snapshot.get(market_key, {}) or {}
    attack = _build_market_attack(snapshot, market_key)
    st.title(title)
    macro = section.get('macro_vs_market', {}) or {}
    execution = section.get('execution', {}) or {}
    route_branch = section.get('route_branch', {}) or {}

    c1, c2, c3, c4 = st.columns(4, gap='small')
    with c1:
        metric_card('Bias', execution.get('bias', '-'), 'lihat ini dulu')
    with c2:
        metric_card('Mode', execution.get('mode', '-'), f"score {float(execution.get('score', 0.0) or 0.0):.2f}")
    with c3:
        metric_card('Best Expression', macro.get('best_expression', '-'), 'kenapa market ini menarik')
    with c4:
        metric_card('Invalidator', macro.get('invalidator', '-'), 'apa yang bikin batal')

    pills = [(f"Now: {macro.get('now', '-')}", 'blue')]
    for d in (macro.get('drivers', []) or [])[:3]:
        pills.append((d, 'good'))
    for r in (macro.get('risks', []) or [])[:2]:
        pills.append((r, 'warn'))
    render_pills(pills)

    a, b, c = st.columns(3, gap='small')
    rows = _rows_from_action(attack, 'ihsg' if market_key == 'ihsg' else 'generic')
    with a:
        info_card('See this first', [f"{r['Action']}: {r['Ticker']}" for r in rows[:2]], accent='#365b46')
    with b:
        info_card('Then watch this', [f"{r['Action']}: {r['Ticker']}" for r in rows[2:4]], accent='#4d425f')
    with c:
        info_card('Avoid / defensive', [f"{rows[-1]['Action']}: {rows[-1]['Ticker']}"], accent='#6a3340')

    st.subheader('Action Summary')
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    with st.expander('Detailed market context', expanded=True):
        MARKET_CONTEXT_RENDERERS[market_key](snapshot)


def _render_risk_page(snapshot: dict) -> None:
    st.title('Risk')
    shared = snapshot.get('shared_core', {}) or {}
    risk = shared.get('risk_summary', {}) or {}
    execution = shared.get('execution_mode', {}) or {}
    rr = shared.get('risk_range', {}) or {}
    tactical = snapshot.get('diagnostics', {}).get('tactical_components', {}) or {}

    c1, c2, c3, c4 = st.columns(4, gap='small')
    with c1:
        metric_card('Risk-Off', risk.get('risk_off_state', '-'), f"score {float(risk.get('risk_off_score',0.0) or 0.0):.2f}")
    with c2:
        metric_card('Crash State', risk.get('crash_state', '-'), f"score {float(risk.get('crash_score',0.0) or 0.0):.2f}")
    with c3:
        metric_card('Exec Mode', execution.get('execute_mode', execution.get('mode','-')), f"size x{float(execution.get('size_multiplier',0.0) or 0.0):.2f}")
    with c4:
        metric_card('Range State', rr.get('range_state', '-'), rr.get('stretch_state', '-'))

    left, right = st.columns(2, gap='small')
    with left:
        info_card('Top reasons', list(risk.get('top_reasons', [])[:5]) or ['-'], accent='#6a3340')
        info_card('Execution notes', list(execution.get('notes', [])[:5]) or ['-'], accent='#365b46')
    with right:
        info_card('Tactical components', [f"{k}: {float(v):.2f}" for k, v in tactical.items()] or ['-'], accent='#4d425f')
        info_card('Flags', [f"{k}: {v}" for k, v in (execution.get('flags', {}) or {}).items()] or ['-'], accent='#365b46')


def _render_diagnostics(snapshot: dict) -> None:
    render_diagnostics_page(snapshot)


def main() -> None:
    st.sidebar.title(APP_NAME)
    if st.sidebar.button('Refresh snapshot', use_container_width=True):
        _get_snapshot(force_refresh=True)
    page = st.sidebar.radio('Page', ['Dashboard', 'US Stocks', 'IHSG', 'Forex', 'Commodities', 'Crypto', 'Risk', 'Diagnostics'])
    manifest = load_snapshot_manifest() or {}
    st.sidebar.caption(f"Mode: {manifest.get('runtime_mode', LIVE_RUNTIME_MODE)}")
    st.sidebar.caption(f"As of: {manifest.get('generated_at', '-')}")

    snapshot = _get_snapshot(force_refresh=False)

    if page == 'Dashboard':
        _render_dashboard(snapshot)
    elif page == 'US Stocks':
        _render_market_page(snapshot, 'us', 'US Stocks')
    elif page == 'IHSG':
        _render_market_page(snapshot, 'ihsg', 'IHSG')
    elif page == 'Forex':
        _render_market_page(snapshot, 'fx', 'Forex')
    elif page == 'Commodities':
        _render_market_page(snapshot, 'commodities', 'Commodities')
    elif page == 'Crypto':
        _render_market_page(snapshot, 'crypto', 'Crypto')
    elif page == 'Risk':
        _render_risk_page(snapshot)
    elif page == 'Diagnostics':
        _render_diagnostics(snapshot)


if __name__ == '__main__':
    main()
