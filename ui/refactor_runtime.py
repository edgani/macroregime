
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from config.display_names import DISPLAY_NAME_MAP


def display_name(sym: str) -> str:
    return DISPLAY_NAME_MAP.get(sym, sym.replace('.JK', ''))


def _flatten_bucket(bucket_map: dict[str, list[str]], names: list[str], tail: bool = False, limit: int = 6) -> list[str]:
    out: list[str] = []
    lowered = {str(n).strip().lower(): str(n).strip() for n in names or []}
    # exact / fuzzy matching to bucket keys
    keys = list(bucket_map.keys())
    matched: list[str] = []
    for raw in names or []:
        s = str(raw).strip().lower()
        for k in keys:
            kl = k.lower()
            if s == kl or s in kl or kl in s:
                matched.append(k)
                break
    if not matched:
        matched = keys[:3]
    for k in matched:
        vals = list(bucket_map.get(k, []))
        vals = list(reversed(vals)) if tail else vals
        for sym in vals:
            if sym not in out:
                out.append(sym)
            if len(out) >= limit:
                return out
    return out


def _normalize_ihsg_symbol(sym: str) -> str:
    sym = str(sym).strip()
    if not sym:
        return sym
    if sym.endswith('.JK'):
        return sym
    candidate = sym + '.JK'
    all_ihsg = {x for vals in IHSG_BUCKETS.values() for x in vals}
    return candidate if candidate in all_ihsg else sym


def _seed_symbols(market: str, section: dict) -> dict[str, list[str]]:
    sw = section.get('strong_weak', {}) or {}
    rb = section.get('route_branch', {}) or {}
    cat = section.get('catalyst_overlay', {}) or {}

    if market == 'US':
        long_labels = (rb.get('winners') or []) + (sw.get('strong_sectors') or [])
        short_labels = (rb.get('losers') or []) + (sw.get('weak_sectors') or [])
        longs = [x for x in cat.get('beneficiaries', []) if x in {s for vals in US_BUCKETS.values() for s in vals}]
        longs += _flatten_bucket(US_BUCKETS, long_labels, tail=False, limit=8)
        shorts = _flatten_bucket(US_BUCKETS, short_labels, tail=True, limit=8)
        fr_long = [x for x in cat.get('watch', []) if x in {s for vals in US_BUCKETS.values() for s in vals}] + _flatten_bucket(US_BUCKETS, long_labels[1:] + long_labels[:1], tail=False, limit=8)
        fr_short = _flatten_bucket(US_BUCKETS, short_labels[1:] + short_labels[:1], tail=True, limit=8)
        return {'now_long': longs, 'now_short': shorts, 'front_run_long': fr_long, 'front_run_short': fr_short}

    if market == 'IHSG':
        long_labels = (rb.get('winners') or []) + (sw.get('strong_sectors') or [])
        buys = [_normalize_ihsg_symbol(x) for x in (cat.get('beneficiaries', []) or [])]
        buys += _flatten_bucket(IHSG_BUCKETS, long_labels, tail=False, limit=8)
        fr = [_normalize_ihsg_symbol(x) for x in (cat.get('watch', []) or [])]
        fr += _flatten_bucket(IHSG_BUCKETS, long_labels[1:] + long_labels[:1], tail=False, limit=8)
        avoid = _flatten_bucket(IHSG_BUCKETS, (rb.get('losers') or []) + (sw.get('weak_sectors') or []), tail=True, limit=8)
        defensive = list(dict.fromkeys(IHSG_BUCKETS.get('Consumer Def', [])[:3] + IHSG_BUCKETS.get('Banks', [])[:2]))
        return {'buy_now': buys, 'front_run_buy': fr, 'avoid_reduce': avoid, 'defensive_shelter': defensive}

    if market == 'FX':
        long_labels = (rb.get('winners') or []) + (sw.get('strong_currencies') or [])
        short_labels = (rb.get('losers') or []) + (sw.get('weak_currencies') or [])
        longs = _flatten_bucket(FX_BUCKETS, long_labels, tail=False, limit=8)
        shorts = _flatten_bucket(FX_BUCKETS, short_labels, tail=True, limit=8)
        fr_long = [x for x in cat.get('watch', []) if x in {s for vals in FX_BUCKETS.values() for s in vals}] + _flatten_bucket(FX_BUCKETS, long_labels[1:] + long_labels[:1], tail=False, limit=8)
        fr_short = _flatten_bucket(FX_BUCKETS, short_labels[1:] + short_labels[:1], tail=True, limit=8)
        return {'now_long': longs, 'now_short': shorts, 'front_run_long': fr_long, 'front_run_short': fr_short}

    if market == 'COMMODITIES':
        long_labels = (rb.get('winners') or []) + (sw.get('strong_families') or [])
        short_labels = (rb.get('losers') or []) + (sw.get('weak_families') or [])
        longs = _flatten_bucket(COMMODITY_BUCKETS, long_labels, tail=False, limit=8)
        shorts = _flatten_bucket(COMMODITY_BUCKETS, short_labels, tail=True, limit=8)
        fr_long = [x for x in cat.get('watch', []) if x in {s for vals in COMMODITY_BUCKETS.values() for s in vals}] + _flatten_bucket(COMMODITY_BUCKETS, long_labels[1:] + long_labels[:1], tail=False, limit=8)
        fr_short = _flatten_bucket(COMMODITY_BUCKETS, short_labels[1:] + short_labels[:1], tail=True, limit=8)
        return {'now_long': longs, 'now_short': shorts, 'front_run_long': fr_long, 'front_run_short': fr_short}

    long_labels = (rb.get('winners') or []) + (sw.get('strong_sectors') or [])
    short_labels = (rb.get('losers') or []) + (sw.get('weak_sectors') or [])
    longs = _flatten_bucket(CRYPTO_BUCKETS, long_labels, tail=False, limit=8)
    shorts = _flatten_bucket(CRYPTO_BUCKETS, short_labels, tail=True, limit=8)
    fr_long = [x for x in cat.get('watch', []) if x in {s for vals in CRYPTO_BUCKETS.values() for s in vals}] + _flatten_bucket(CRYPTO_BUCKETS, long_labels[1:] + long_labels[:1], tail=False, limit=8)
    fr_short = _flatten_bucket(CRYPTO_BUCKETS, short_labels[1:] + short_labels[:1], tail=True, limit=8)
    return {'now_long': longs, 'now_short': shorts, 'front_run_long': fr_long, 'front_run_short': fr_short}


def _score_base(section: dict) -> float:
    try:
        return max(5.0, min(9.0, 5.0 + 8.0 * float((section.get('macro_vs_market', {}) or {}).get('score', 0.25))))
    except Exception:
        return 6.5


def _bias_title(raw: str) -> str:
    raw = str(raw or '').strip()
    return raw or '—'


def _mk_row(sym: str, bias: str, bucket: str, idx: int, section: dict, front_run: bool = False) -> dict:
    macro = section.get('macro_vs_market', {}) or {}
    route = section.get('route_branch', {}) or {}
    base = _score_base(section) - idx * 0.25
    if front_run:
        base -= 0.35
    return {
        'ticker': display_name(sym),
        'raw_ticker': sym,
        'bias': bias,
        'bucket': bucket,
        'entry_zone': 'pullback / reclaim' if not front_run else None,
        'invalidation': macro.get('invalidator') or (route.get('market_invalidators') or ['route invalidates'])[0],
        'target': macro.get('best_expression') or (route.get('summary') or 'route extension'),
        'score': round(max(4.8, min(9.4, base)), 1),
        'why_now': f"{(macro.get('trigger') or 'route confirmation')} · {route.get('route_interpretation', '-')}",
        'trigger': macro.get('trigger') or 'confirmation trigger',
        'why_not_yet': macro.get('forward_branch') or 'needs confirmation',
        'trigger_distance': round(max(0.4, 1.4 - idx * 0.1), 1),
        'problem': (route.get('market_invalidators') or ['route conflict'])[0],
        'why_avoid': (macro.get('invalidator') or 'risk/reward not clean enough'),
        'better_alternative': None,
    }


def build_market_actions(section: dict, market_label: str) -> dict:
    market_key = market_label.upper()
    seeds = _seed_symbols(market_key if market_key != 'COMMODITIES' else 'COMMODITIES', section)
    rb = section.get('route_branch', {}) or {}
    winner_bucket = ', '.join((rb.get('winners') or [])[:2]) or 'Route winners'
    loser_bucket = ', '.join((rb.get('losers') or [])[:2]) or 'Route losers'
    actions: dict[str, list[dict]] = {}

    if market_key == 'IHSG':
        actions['buy_now'] = [_mk_row(sym, 'Buy', winner_bucket, i, section, front_run=False) for i, sym in enumerate(list(dict.fromkeys(seeds['buy_now']))[:5])]
        actions['front_run_buy'] = [_mk_row(sym, 'Buy', 'Front-Run Buy', i, section, front_run=True) for i, sym in enumerate(list(dict.fromkeys(seeds['front_run_buy']))[:5])]
        actions['avoid_reduce'] = []
        for i, sym in enumerate(list(dict.fromkeys(seeds['avoid_reduce']))[:5]):
            row = _mk_row(sym, 'Avoid', loser_bucket, i, section, front_run=False)
            row['better_alternative'] = display_name(actions['buy_now'][i % len(actions['buy_now'])]['raw_ticker']) if actions['buy_now'] else None
            actions['avoid_reduce'].append(row)
        actions['defensive_shelter'] = []
        for i, sym in enumerate(list(dict.fromkeys(seeds['defensive_shelter']))[:5]):
            actions['defensive_shelter'].append({
                'ticker': display_name(sym),
                'raw_ticker': sym,
                'type': 'Defensive' if sym != 'Cash' else 'Cash',
                'why_defensive': 'lebih tahan saat conflict naik atau USD/flow memburuk',
                'trigger_to_use': (section.get('catalyst_overlay', {}) or {}).get('invalidator', 'use if board turns fragile'),
            })
        return actions

    actions['now_long'] = [_mk_row(sym, 'Long', winner_bucket, i, section, front_run=False) for i, sym in enumerate(list(dict.fromkeys(seeds['now_long']))[:5])]
    actions['now_short'] = [_mk_row(sym, 'Short', loser_bucket, i, section, front_run=False) for i, sym in enumerate(list(dict.fromkeys(seeds['now_short']))[:5])]
    actions['front_run_long'] = [_mk_row(sym, 'Long', 'Front-Run Long', i, section, front_run=True) for i, sym in enumerate(list(dict.fromkeys(seeds['front_run_long']))[:5])]
    actions['front_run_short'] = [_mk_row(sym, 'Short', 'Front-Run Short', i, section, front_run=True) for i, sym in enumerate(list(dict.fromkeys(seeds['front_run_short']))[:5])]
    actions['avoid_reduce'] = []
    avoid_syms = list(dict.fromkeys(seeds.get('front_run_short', [])[:3] + seeds.get('now_short', [])[:2]))[:5]
    for i, sym in enumerate(avoid_syms):
        row = _mk_row(sym, 'Avoid', 'Avoid / Reduce', i, section, front_run=False)
        alts = actions['now_long'] or actions['front_run_long']
        row['better_alternative'] = display_name(alts[i % len(alts)]['raw_ticker']) if alts else None
        actions['avoid_reduce'].append(row)
    return actions


def _scenario_obj(name: str, bucket: str, score: float, direction: float, first: list[str], invalidators: list[str], impacts: dict[str, float]) -> dict:
    if score < 0.18:
        status = 'dormant'
    elif score < 0.35:
        status = 'arming'
    elif score < 0.55:
        status = 'pre_confirmed'
    elif score < 0.72:
        status = 'ignition'
    else:
        status = 'live'
    return {
        'name': name,
        'bucket': bucket,
        'score': round(score, 2),
        'weight': 0.0,
        'status': status,
        'direction': direction,
        'first_responders': first,
        'invalidators': invalidators,
        'market_impacts': impacts,
    }


def build_scenario_stack(snapshot: dict) -> dict:
    sh = snapshot.get('shared_core', {}) or {}
    news = sh.get('news_state', {}) or {}
    breadth = sh.get('breadth_snapshot', {}) or {}
    pet = sh.get('petrodollar', {}) or {}
    pos = sh.get('positioning', {}) or {}
    risk = sh.get('risk_summary', {}) or {}
    weather = sh.get('weather', {}) or {}

    relief_score = min(1.0, max(float(news.get('deescalation_watch', 0.0) or 0.0), float(news.get('relief_hazard', 0.0) or 0.0)) + 0.15 * (1.0 - float(risk.get('risk_off_score', 0.5) or 0.5)))
    oil_score = min(1.0, 0.55 * float(pet.get('score', 0.0) or 0.0) + 0.25 * float(news.get('oil_shock_fading', 0.0) or 0.0) + 0.20 * float(news.get('war_oil_hazard', 0.0) or 0.0))
    breadth_score = min(1.0, 0.60 * float(breadth.get('breadth_score', 0.0) or 0.0) + 0.20 * (1.0 if sh.get('health', {}).get('eqw_confirm') else 0.0) + 0.20 * (1.0 if sh.get('health', {}).get('smallcap_confirm') else 0.0))
    mh_score = min(1.0, 0.45 * float(pos.get('squeeze_risk', 0.0) or 0.0) + 0.35 * (1.0 - float(risk.get('crash_score', 0.5) or 0.5)) + 0.20 * float(weather.get('score', 0.0) or 0.0))
    tail_score = min(1.0, 0.55 * float(risk.get('crash_score', 0.0) or 0.0) + 0.25 * float(news.get('war_oil_hazard', 0.0) or 0.0) + 0.20 * float(sh.get('shock', {}).get('override_strength', 0.0) or 0.0))

    scenarios = [
        _scenario_obj('Liquidity / Relief', 'liquidity_policy', relief_score, +0.8, ['DXY', 'rates', 'breadth'], ['DXY reclaim', 'breadth narrows'], {'US': 0.6, 'IHSG': 0.35, 'FX': -0.5, 'COMMODITIES': 0.1, 'CRYPTO': 0.55}),
        _scenario_obj('Inflation / Oil Shock', 'inflation_commodity', oil_score, -0.5, ['oil', 'gold', 'USD'], ['oil rollback', 'USD softens'], {'US': -0.2, 'IHSG': -0.05, 'FX': 0.45, 'COMMODITIES': 0.65, 'CRYPTO': -0.25}),
        _scenario_obj('Breadth Healing', 'growth_breadth', breadth_score, +0.5, ['IWM', 'RSP', 'sector breadth'], ['breadth narrows again'], {'US': 0.55, 'IHSG': 0.2, 'FX': -0.15, 'COMMODITIES': 0.25, 'CRYPTO': 0.2}),
        _scenario_obj('Most Hated Rally', 'positioning_mania', mh_score, +0.45, ['BTC', 'small caps', 'short-covering'], ['VIX spike', 'failed squeeze'], {'US': 0.3, 'IHSG': 0.1, 'FX': -0.1, 'COMMODITIES': 0.0, 'CRYPTO': 0.7}),
    ]
    total = sum(max(s['score'], 0.0) for s in scenarios) or 1.0
    for s in scenarios:
        s['weight'] = round(s['score'] / total, 2)
    positives = sorted([s for s in scenarios if s['direction'] > 0], key=lambda x: x['score'], reverse=True)
    negative = [s for s in scenarios if s['direction'] < 0]
    drag = max(negative, key=lambda x: x['score']) if negative else scenarios[-1]
    tail = _scenario_obj('Tail Risk / Re-escalation', 'tail', tail_score, -0.9, ['oil', 'USD', 'vol'], ['de-escalation confirmed', 'risk stays calm'], {'US': -0.45, 'IHSG': -0.3, 'FX': 0.55, 'COMMODITIES': 0.35, 'CRYPTO': -0.5})
    return {
        'primary': positives[0] if positives else scenarios[0],
        'secondary': positives[1] if len(positives) > 1 else scenarios[1],
        'residual_drag': drag,
        'tail_risk': tail,
        'all_selected': scenarios,
    }


def build_market_mix(snapshot: dict, stack: dict) -> dict:
    selected = stack.get('all_selected', []) or []
    out = {}
    for market in ['US', 'IHSG', 'FX', 'COMMODITIES', 'CRYPTO']:
        net = sum(float(s.get('weight', 0.0)) * float((s.get('market_impacts') or {}).get(market, 0.0)) for s in selected)
        conflict = max(0.0, min(1.0, 1.0 - abs(sum(float(s.get('weight',0.0))*float(s.get('direction',0.0)) for s in selected))))
        primary = max(selected, key=lambda s: abs(float((s.get('market_impacts') or {}).get(market, 0.0)) * float(s.get('weight',0.0)))) if selected else {'name':'—'}
        drag = min(selected, key=lambda s: float((s.get('market_impacts') or {}).get(market, 0.0)) * float(s.get('weight',0.0))) if selected else {'name':'—'}
        if net > 0.35:
            stance = 'bullish'
        elif net > 0.10:
            stance = 'selective_bullish'
        elif net < -0.10:
            stance = 'defensive'
        else:
            stance = 'mixed'
        if conflict < 0.25:
            conflict_label = 'Clean'
        elif conflict < 0.45:
            conflict_label = 'Selective'
        elif conflict < 0.70:
            conflict_label = 'Mixed'
        else:
            conflict_label = 'Fragile'
        out[market] = {
            'market': market,
            'net_bias': round(net, 2),
            'stance': stance,
            'conflict_score': round(conflict, 2),
            'conflict_label': conflict_label,
            'primary_driver': primary.get('name', '—'),
            'main_drag': drag.get('name', '—'),
            'confidence': round(max(0.0, min(1.0, 1.0 - conflict)), 2),
        }
    return out


def build_market_bundle(snapshot: dict, market_slug: str, market_mix: dict) -> dict:
    section = snapshot[market_slug]
    market_key = 'COMMODITIES' if market_slug == 'commodities' else market_slug.upper()
    actions = build_market_actions(section, market_key)
    mix = market_mix[market_key]
    macro = section.get('macro_vs_market', {}) or {}
    header = {
        'stance': mix['stance'],
        'conflict_label': mix['conflict_label'],
        'primary_driver': mix['primary_driver'],
        'main_drag': mix['main_drag'],
        'one_line': macro.get('best_expression') or section.get('route_branch', {}).get('summary', '-'),
    }
    why = {
        'top_drivers': [{'label': x} for x in (macro.get('drivers', []) or [])[:5]],
        'route': {
            'active_path': snapshot.get('shared_core', {}).get('resolved_regime', {}).get('operating_regime', '-'),
            'next_path': snapshot.get('shared_core', {}).get('next_path', {}).get('next_resolved_regime', '-'),
            'invalidator_path': macro.get('invalidator', '-'),
        },
    }
    state_change = {
        'added': [display_name(x) for x in [r['raw_ticker'] for r in actions.get('front_run_buy' if market_key=='IHSG' else 'front_run_long', [])[:3]]],
        'remaining': [display_name(x) for x in [r['raw_ticker'] for r in actions.get('buy_now' if market_key=='IHSG' else 'now_long', [])[:3]]],
        'removed': [display_name(x) for x in [r['raw_ticker'] for r in actions.get('avoid_reduce', [])[:3] if r.get('raw_ticker')]],
        'ripening': [display_name(x) for x in [r['raw_ticker'] for r in actions.get('front_run_short', [])[:2]]],
    }
    market_state = {
        'checklist_score': f"{sum(1 for c in (section.get('asset_checklist') or []) if (c.get('tone')=='good'))}/{len(section.get('asset_checklist') or [])}",
        'macro_fit': section.get('execution', {}).get('mode', '-'),
        'breadth': section.get('macro_vs_market', {}).get('breadth_state', section.get('market_hub', {}).get('breadth_state', '-')),
        'leadership': section.get('macro_vs_market', {}).get('resolved_language', section.get('route_branch', {}).get('route_interpretation', '-')),
        'strong_vs_weak': {
            'strong': [display_name(x) for x in [r['raw_ticker'] for r in actions.get('buy_now' if market_key=='IHSG' else 'now_long', [])[:3]]],
            'weak': [display_name(x) for x in [r['raw_ticker'] for r in actions.get('avoid_reduce', [])[:3] if r.get('raw_ticker')]],
        },
        'one_line': macro.get('forward_branch') or section.get('catalyst_overlay', {}).get('why', '-'),
    }
    bundle = {
        'market': market_key,
        'header': header,
        'state_change': state_change,
        'market_state': market_state,
        'why_this_is_moving': why,
        'avoid_reduce': {'title': 'Avoid / Reduce', 'rows': actions.get('avoid_reduce', [])},
        'details': {
            'asset_checklist': section.get('asset_checklist', []),
            'execution': section.get('execution', {}),
            'route_branch': section.get('route_branch', {}),
            'catalyst_overlay': section.get('catalyst_overlay', {}),
            'market_hub': section.get('market_hub', {}),
            'transmission': section.get('transmission', {}),
        },
    }
    if market_key == 'IHSG':
        bundle['buy_now'] = {'title': 'Buy Now', 'rows': actions.get('buy_now', [])}
        bundle['front_run_buy'] = {'title': 'Front-Run Buy', 'rows': actions.get('front_run_buy', [])}
        bundle['defensive_shelter'] = {'title': 'Defensive Shelter / Cash', 'rows': actions.get('defensive_shelter', [])}
    else:
        bundle['opportunity_now'] = {'title': 'Opportunity Now', 'rows': actions.get('now_long', []) + actions.get('now_short', [])}
        bundle['front_run_next'] = {'title': 'Front-Run Next', 'rows': actions.get('front_run_long', []) + actions.get('front_run_short', [])}
        bundle['action_groups'] = actions
    return bundle


def build_dashboard_payload(snapshot: dict, stack: dict, market_mix: dict, bundles: dict[str, dict]) -> dict:
    sh = snapshot.get('shared_core', {}) or {}
    home = snapshot.get('home_summary', {}) or {}
    scen = snapshot.get('scenarios', {}) or {}
    risk = sh.get('risk_summary', {}) or {}
    dashboard = snapshot.get('dashboard', {}) or {}

    attack = {
        'US': {
            'best_longs_now': [r['ticker'] for r in bundles['us'].get('action_groups', {}).get('now_long', [])[:3]],
            'best_shorts_now': [r['ticker'] for r in bundles['us'].get('action_groups', {}).get('now_short', [])[:3]],
            'front_run_longs': [r['ticker'] for r in bundles['us'].get('action_groups', {}).get('front_run_long', [])[:3]],
            'front_run_shorts': [r['ticker'] for r in bundles['us'].get('action_groups', {}).get('front_run_short', [])[:3]],
        },
        'IHSG': {
            'best_buys_now': [r['ticker'] for r in bundles['ihsg'].get('buy_now', {}).get('rows', [])[:3]],
            'front_run_buys': [r['ticker'] for r in bundles['ihsg'].get('front_run_buy', {}).get('rows', [])[:3]],
            'avoid_reduce': [r['ticker'] for r in bundles['ihsg'].get('avoid_reduce', {}).get('rows', [])[:3]],
            'defensive_shelter': [r['ticker'] for r in bundles['ihsg'].get('defensive_shelter', {}).get('rows', [])[:3]],
        },
        'FX': {
            'best_longs_now': [r['ticker'] for r in bundles['fx'].get('action_groups', {}).get('now_long', [])[:3]],
            'best_shorts_now': [r['ticker'] for r in bundles['fx'].get('action_groups', {}).get('now_short', [])[:3]],
            'front_run_longs': [r['ticker'] for r in bundles['fx'].get('action_groups', {}).get('front_run_long', [])[:3]],
            'front_run_shorts': [r['ticker'] for r in bundles['fx'].get('action_groups', {}).get('front_run_short', [])[:3]],
        },
        'COMMODITIES': {
            'best_longs_now': [r['ticker'] for r in bundles['commodities'].get('action_groups', {}).get('now_long', [])[:3]],
            'best_shorts_now': [r['ticker'] for r in bundles['commodities'].get('action_groups', {}).get('now_short', [])[:3]],
            'front_run_longs': [r['ticker'] for r in bundles['commodities'].get('action_groups', {}).get('front_run_long', [])[:3]],
            'front_run_shorts': [r['ticker'] for r in bundles['commodities'].get('action_groups', {}).get('front_run_short', [])[:3]],
        },
        'CRYPTO': {
            'best_longs_now': [r['ticker'] for r in bundles['crypto'].get('action_groups', {}).get('now_long', [])[:3]],
            'best_shorts_now': [r['ticker'] for r in bundles['crypto'].get('action_groups', {}).get('now_short', [])[:3]],
            'front_run_longs': [r['ticker'] for r in bundles['crypto'].get('action_groups', {}).get('front_run_long', [])[:3]],
            'front_run_shorts': [r['ticker'] for r in bundles['crypto'].get('action_groups', {}).get('front_run_short', [])[:3]],
        },
    }

    # best markets by positive net bias
    mix_sorted = sorted(market_mix.items(), key=lambda kv: kv[1]['net_bias'], reverse=True)
    best_now = [k for k, v in mix_sorted[:3]]
    best_next = [str(snapshot.get('shared_core', {}).get('next_path', {}).get('market_routes', {}).get(k.lower(), k)) for k in ['us','ihsg','fx']]

    return {
        'executive_strip': {
            'rally_state': sh.get('news_state', {}).get('display_state', 'Mixed'),
            'action': sh.get('resolved_regime', {}).get('execution_bias', 'mixed'),
            'exec_mode': 'Selective' if risk.get('risk_off_state') != 'calm' else 'Aggressive',
            'board': dashboard.get('status_ribbon', {}).get('headline', home.get('dominant_route', 'Control tower active')),
        },
        'scenario_cards': {
            'primary': stack['primary'],
            'secondary': stack['secondary'],
            'residual_drag': stack['residual_drag'],
            'tail_risk': stack['tail_risk'],
        },
        'why_this_is_moving': {
            'top_drivers': [{'label': x} for x in (dashboard.get('top_drivers', []) or sh.get('top_drivers', []) or [])[:6]],
            'route': {
                'active_path': sh.get('resolved_regime', {}).get('operating_regime', '-'),
                'next_path': sh.get('next_path', {}).get('next_resolved_regime', '-'),
                'invalidator_path': ', '.join((sh.get('next_path', {}).get('invalidators') or [])[:2]) or '-',
            },
        },
        'market_attack_matrix': attack,
        'best_market_now': best_now,
        'best_market_next': best_next,
        'risk_state': {
            'conflict_label': max((v['conflict_label'] for v in market_mix.values()), key=lambda x: ['Clean','Selective','Mixed','Fragile'].index(x)),
            'size_cap': 0.7 if risk.get('risk_off_state') == 'watch' else 1.0,
            'kill_switch': ', '.join((risk.get('top_reasons') or [])[:2]) or 'Risk-off + breadth failure',
        },
        'scenario_lab': scen,
        'cross_asset': snapshot.get('cross_asset', {}),
    }
