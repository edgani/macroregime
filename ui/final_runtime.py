from __future__ import annotations

from typing import Any, Dict, List

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from config.display_names import DISPLAY_NAME_MAP


def display_name(sym: str) -> str:
    return DISPLAY_NAME_MAP.get(sym, sym.replace('.JK', '').replace('=X','').replace('-USD',''))


def _flatten_bucket(bucket_map: dict[str, list[str]], labels: list[str], tail: bool = False, limit: int = 6) -> list[str]:
    out: list[str] = []
    keys = list(bucket_map.keys())
    matched: list[str] = []
    for raw in labels or []:
        s = str(raw).strip().lower()
        for k in keys:
            kl = k.lower()
            if s == kl or s in kl or kl in s:
                matched.append(k)
                break
    if not matched:
        matched = keys[:2]
    for k in matched:
        vals = list(bucket_map.get(k, []))
        if tail:
            vals = list(reversed(vals))
        for sym in vals:
            if sym not in out:
                out.append(sym)
            if len(out) >= limit:
                return out
    return out


def _normalize_ihsg(sym: str) -> str:
    sym = str(sym).strip()
    if not sym:
        return sym
    if sym.endswith('.JK'):
        return sym
    all_ihsg = {x for vals in IHSG_BUCKETS.values() for x in vals}
    cand = sym + '.JK'
    return cand if cand in all_ihsg else sym


def _mk_action_row(sym: str, bias: str, bucket: str, section: dict, idx: int, front_run: bool = False) -> dict:
    macro = section.get('macro_vs_market', {}) or {}
    route = section.get('route_branch', {}) or {}
    score_base = 8.4 - idx * 0.3
    if front_run:
        score_base -= 0.5
    return {
        'ticker': display_name(sym),
        'raw_ticker': sym,
        'bias': bias,
        'bucket': bucket,
        'entry_zone': 'pullback / reclaim zone',
        'trigger': macro.get('trigger') or 'confirmation trigger',
        'why_not_yet': macro.get('forward_branch') or 'needs confirmation',
        'trigger_distance': round(max(0.4, 1.2 - idx * 0.1), 1),
        'invalidation': macro.get('invalidator') or ((route.get('market_invalidators') or ['route invalidates'])[0]),
        'target': macro.get('best_expression') or (route.get('summary') or 'continuation target'),
        'score': round(max(5.0, min(9.5, score_base)), 1),
        'why_now': ' · '.join([str(macro.get('now') or route.get('route_interpretation') or 'market aligns with route')[:90], str((macro.get('drivers') or [''])[0])[:50]]).strip(' ·'),
    }


def _seed_actions(section: dict, market: str) -> dict[str, list[str]]:
    sw = section.get('strong_weak', {}) or {}
    rb = section.get('route_branch', {}) or {}
    cat = section.get('catalyst_overlay', {}) or {}

    if market == 'US':
        strong = (sw.get('strong_sectors') or []) + (rb.get('winners') or [])
        weak = (sw.get('weak_sectors') or []) + (rb.get('losers') or [])
        return {
            'now_long': _flatten_bucket(US_BUCKETS, strong, False, 6),
            'now_short': _flatten_bucket(US_BUCKETS, weak, True, 6),
            'front_run_long': _flatten_bucket(US_BUCKETS, strong[1:] + strong[:1], False, 6),
            'front_run_short': _flatten_bucket(US_BUCKETS, weak[1:] + weak[:1], True, 6),
        }
    if market == 'IHSG':
        strong = (sw.get('strong_sectors') or []) + (rb.get('winners') or [])
        weak = (sw.get('weak_sectors') or []) + (rb.get('losers') or [])
        ben = [_normalize_ihsg(x) for x in (cat.get('beneficiaries') or [])]
        watch = [_normalize_ihsg(x) for x in (cat.get('watch') or [])]
        return {
            'buy_now': (ben + _flatten_bucket(IHSG_BUCKETS, strong, False, 6))[:6],
            'front_run_buy': (watch + _flatten_bucket(IHSG_BUCKETS, strong[1:] + strong[:1], False, 6))[:6],
            'avoid_reduce': _flatten_bucket(IHSG_BUCKETS, weak, True, 6),
            'defensive_shelter': list(dict.fromkeys(IHSG_BUCKETS.get('Consumer Def', [])[:3] + IHSG_BUCKETS.get('Banks', [])[:2])),
        }
    if market == 'FX':
        strong = (sw.get('strong_currencies') or []) + (rb.get('winners') or [])
        weak = (sw.get('weak_currencies') or []) + (rb.get('losers') or [])
        return {
            'now_long': _flatten_bucket(FX_BUCKETS, strong, False, 6),
            'now_short': _flatten_bucket(FX_BUCKETS, weak, True, 6),
            'front_run_long': _flatten_bucket(FX_BUCKETS, strong[1:] + strong[:1], False, 6),
            'front_run_short': _flatten_bucket(FX_BUCKETS, weak[1:] + weak[:1], True, 6),
        }
    if market == 'Commodities':
        strong = (sw.get('strong_families') or []) + (rb.get('winners') or [])
        weak = (sw.get('weak_families') or []) + (rb.get('losers') or [])
        return {
            'now_long': _flatten_bucket(COMMODITY_BUCKETS, strong, False, 6),
            'now_short': _flatten_bucket(COMMODITY_BUCKETS, weak, True, 6),
            'front_run_long': _flatten_bucket(COMMODITY_BUCKETS, strong[1:] + strong[:1], False, 6),
            'front_run_short': _flatten_bucket(COMMODITY_BUCKETS, weak[1:] + weak[:1], True, 6),
        }
    strong = (sw.get('strong_tokens') or sw.get('strong_sectors') or []) + (rb.get('winners') or [])
    weak = (sw.get('weak_tokens') or sw.get('weak_sectors') or []) + (rb.get('losers') or [])
    return {
        'now_long': _flatten_bucket(CRYPTO_BUCKETS, strong, False, 6),
        'now_short': _flatten_bucket(CRYPTO_BUCKETS, weak, True, 6),
        'front_run_long': _flatten_bucket(CRYPTO_BUCKETS, strong[1:] + strong[:1], False, 6),
        'front_run_short': _flatten_bucket(CRYPTO_BUCKETS, weak[1:] + weak[:1], True, 6),
    }


def build_market_bundle(snapshot: dict, market_key: str) -> dict:
    section = snapshot.get(market_key.lower(), {}) or {}
    macro = section.get('macro_vs_market', {}) or {}
    trans = section.get('transmission', {}) or {}
    execn = section.get('execution', {}) or {}
    sw = section.get('strong_weak', {}) or {}
    seeds = _seed_actions(section, market_key)
    bundle = {
        'market': market_key,
        'header': {
            'stance': execn.get('bias') or macro.get('resolved_language') or 'Mixed',
            'conflict_label': 'Mixed' if trans.get('conflict') else 'Selective',
            'primary_driver': (macro.get('drivers') or ['—'])[0],
            'main_drag': (macro.get('risks') or ['—'])[0],
            'one_line': macro.get('now') or '—',
        },
        'state_change': {
            'added': [display_name(x) for x in ((sw.get('strong_names') or sw.get('strong_pairs') or sw.get('strong_tokens') or [])[:5])],
            'remaining': [display_name(x) for x in ((section.get('catalyst_overlay', {}) or {}).get('beneficiaries', [])[:5]],
            'removed': [display_name(x) for x in ((sw.get('weak_names') or sw.get('weak_pairs') or sw.get('weak_tokens') or [])[:5])],
            'ripening': [display_name(x) for x in ((section.get('catalyst_overlay', {}) or {}).get('watch', [])[:5])],
        },
        'market_state': {
            'checklist_score': f"{sum(1 for c in section.get('asset_checklist', []) if float(c.get('score',0)) >= 0.5)}/{len(section.get('asset_checklist', [])) or 0}",
            'macro_fit': macro.get('resolved_language') or '—',
            'breadth': macro.get('breadth_state', 'mixed / watch'),
            'leadership': ' / '.join((section.get('route_branch', {}) or {}).get('winners', [])[:2]) or 'mixed leaders',
            'strong_vs_weak': {
                'strong': [display_name(x) for x in ((sw.get('strong_names') or sw.get('strong_pairs') or sw.get('strong_tokens') or sw.get('strong_sectors') or sw.get('strong_families') or [])[:4])],
                'weak': [display_name(x) for x in ((sw.get('weak_names') or sw.get('weak_pairs') or sw.get('weak_tokens') or sw.get('weak_sectors') or sw.get('weak_families') or [])[:4])],
            },
            'one_line': macro.get('best_expression') or '—',
        },
        'why_this_is_moving': {
            'top_drivers': [{'label': x} for x in (macro.get('drivers') or [])[:4]] + [{'label': (section.get('catalyst_overlay', {}) or {}).get('title','')}],
            'route': {
                'active_path': (section.get('route_branch', {}) or {}).get('summary', '—'),
                'next_path': macro.get('forward_branch', '—'),
                'invalidator_path': macro.get('invalidator', '—'),
            },
        },
        'details': {
            'transmission': trans,
            'next_path': section.get('next_path', {}),
            'market_hub': section.get('market_hub', {}),
        },
    }
    if market_key == 'IHSG':
        bundle['buy_now'] = {'rows': [_mk_action_row(sym, 'Buy', 'Buy Now', section, i, False) for i, sym in enumerate(seeds['buy_now'][:5])]}
        bundle['front_run_buy'] = {'rows': [_mk_action_row(sym, 'Buy', 'Front-Run Buy', section, i, True) for i, sym in enumerate(seeds['front_run_buy'][:5])]}
        avoid_rows=[]
        alts = bundle['buy_now']['rows'] or bundle['front_run_buy']['rows']
        for i,sym in enumerate(seeds['avoid_reduce'][:5]):
            row = _mk_action_row(sym,'Avoid','Avoid / Reduce',section,i,False)
            row['problem'] = row['invalidation']
            row['why_avoid'] = row['invalidation']
            row['better_alternative'] = alts[i % len(alts)]['ticker'] if alts else '—'
            avoid_rows.append(row)
        bundle['avoid_reduce'] = {'rows': avoid_rows}
        bundle['defensive_shelter'] = {'rows':[{'ticker':display_name(sym),'type':'Defensive' if sym!='Cash' else 'Cash','why_defensive':'lebih tahan saat conflict naik atau USD/flow memburuk','trigger_to_use':(section.get('catalyst_overlay',{}) or {}).get('invalidator','use if board turns fragile')} for sym in seeds['defensive_shelter'][:5]]}
    else:
        bundle['opportunity_now_long'] = {'rows': [_mk_action_row(sym, 'Long', 'Now Long', section, i, False) for i, sym in enumerate(seeds['now_long'][:5])]}
        bundle['opportunity_now_short'] = {'rows': [_mk_action_row(sym, 'Short', 'Now Short', section, i, False) for i, sym in enumerate(seeds['now_short'][:5])]}
        bundle['front_run_long'] = {'rows': [_mk_action_row(sym, 'Long', 'Front-Run Long', section, i, True) for i, sym in enumerate(seeds['front_run_long'][:5])]}
        bundle['front_run_short'] = {'rows': [_mk_action_row(sym, 'Short', 'Front-Run Short', section, i, True) for i, sym in enumerate(seeds['front_run_short'][:5])]}
        avoid_rows=[]
        alts = bundle['opportunity_now_long']['rows'] or bundle['front_run_long']['rows']
        for i,sym in enumerate((seeds['front_run_short'][:3] + seeds['now_short'][:2])[:5]):
            row=_mk_action_row(sym,'Avoid','Avoid / Reduce',section,i,False)
            row['problem']=row['invalidation']
            row['why_avoid']=row['invalidation']
            row['better_alternative']=alts[i % len(alts)]['ticker'] if alts else '—'
            avoid_rows.append(row)
        bundle['avoid_reduce']={'rows':avoid_rows}
    return bundle


def build_dashboard_payload(snapshot: dict) -> dict:
    shared = snapshot.get('shared_core', {}) or {}
    dash = snapshot.get('dashboard', {}) or {}
    scen = snapshot.get('scenarios', {}) or {}
    home = snapshot.get('home_summary', {}) or {}
    status = dash.get('status_ribbon', {}) or {}

    # simple scenarios from existing state
    primary = {
        'name': home.get('dominant_family') or 'Primary Route',
        'status': status.get('confidence_band','low'),
        'score': float(status.get('confidence',0.0) or 0.0),
        'weight': 0.40,
        'first_responders': (dash.get('top_drivers') or [])[:3],
        'invalidators': [home.get('main_risk') or 'breadth fails'],
    }
    secondary = {
        'name': (scen.get('top_catalysts') or ['Breadth healing'])[0],
        'status': 'watch',
        'score': 0.55,
        'weight': 0.25,
        'first_responders': ['breadth', 'equal-weight', 'small caps'],
        'invalidators': ['narrow leadership persists'],
    }
    residual = {
        'name': shared.get('petrodollar', {}).get('state', 'Residual drag'),
        'status': 'residual',
        'score': float(shared.get('petrodollar', {}).get('score', 0.0) or 0.0),
        'weight': 0.20,
        'first_responders': ['oil', 'USD', 'gold'],
        'invalidators': ['oil rollback'],
    }
    tail = {
        'name': (scen.get('what_if_matrix') and list(scen.get('what_if_matrix').keys())[1]) if scen.get('what_if_matrix') else 'Tail risk',
        'status': 'tail',
        'score': 0.22,
        'weight': 0.15,
        'first_responders': ['vol', 'credit', 'USD'],
        'invalidators': ['broad confirmation fails'],
    }

    attack = {}
    for mk, key in [('US','US'),('IHSG','IHSG'),('FX','FX'),('COMMODITIES','Commodities'),('CRYPTO','Crypto')]:
        b = build_market_bundle(snapshot, mk)
        if mk == 'IHSG':
            attack[key] = {
                'best_buys_now': [r['ticker'] for r in b['buy_now']['rows'][:3]],
                'front_run_buys': [r['ticker'] for r in b['front_run_buy']['rows'][:3]],
                'avoid_reduce': [r['ticker'] for r in b['avoid_reduce']['rows'][:3]],
                'defensive_shelter': [r['ticker'] for r in b['defensive_shelter']['rows'][:3]],
            }
        else:
            attack[key] = {
                'best_longs_now': [r['ticker'] for r in b['opportunity_now_long']['rows'][:3]],
                'best_shorts_now': [r['ticker'] for r in b['opportunity_now_short']['rows'][:3]],
                'front_run_longs': [r['ticker'] for r in b['front_run_long']['rows'][:3]],
                'front_run_shorts': [r['ticker'] for r in b['front_run_short']['rows'][:3]],
            }

    best_now = [display_name(x) for x in (home.get('strongest_markets') or [])[:3]]
    best_next = []
    for x in (scen.get('next_path', {}) or {}).get('market_routes', {}).keys():
        best_next.append(str(x).upper())
    best_next = best_next[:3]

    return {
        'executive_strip': {
            'rally_state': status.get('resolved_language') or status.get('operating_regime') or '—',
            'action': shared.get('execution_mode', {}).get('label', 'Selective'),
            'exec_mode': shared.get('execution_mode', {}).get('subtitle', 'scale in'),
            'board': f"{status.get('health','-')} / {status.get('risk_off','-')}",
        },
        'scenario_cards': {
            'primary': primary,
            'secondary': secondary,
            'residual_drag': residual,
            'tail_risk': tail,
        },
        'why_this_is_moving': {
            'top_drivers': [{'label':str(x)} for x in (dash.get('top_drivers') or [])[:6]],
            'route': {
                'active_path': home.get('dominant_route', '—'),
                'next_path': (scen.get('next_path', {}) or {}).get('continuation_path', '—'),
                'invalidator_path': home.get('main_risk', '—'),
            },
        },
        'market_attack_matrix': attack,
        'best_market_now': best_now,
        'best_market_next': best_next,
        'risk_state': {
            'conflict_label': status.get('health','Mixed'),
            'size_cap': shared.get('execution_mode', {}).get('size_multiplier', '0.8x'),
            'kill_switch': home.get('main_risk', 'breadth / USD / rates invalidator'),
        },
        'scenario_lab': snapshot.get('scenario_lab', {}),
        'cross_asset': snapshot.get('cross_asset', {}),
    }