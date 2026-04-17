
from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from config.asset_buckets import US_BUCKETS, IHSG_BUCKETS, FX_BUCKETS, COMMODITY_BUCKETS, CRYPTO_BUCKETS
from ui.components.compact_table_helpers import frame_height


_BUCKETS = {
    'us': US_BUCKETS,
    'ihsg': IHSG_BUCKETS,
    'fx': FX_BUCKETS,
    'commodities': COMMODITY_BUCKETS,
    'crypto': CRYPTO_BUCKETS,
}

_STRONG_KEYS = {
    'us': ('strong_names', 'strong_sectors'),
    'ihsg': ('strong_names', 'strong_sectors'),
    'fx': ('strong_pairs', 'strong_currencies'),
    'commodities': ('strong_names', 'strong_families'),
    'crypto': ('strong_tokens', 'strong_sectors'),
}

_WEAK_KEYS = {
    'us': ('weak_names', 'weak_sectors'),
    'ihsg': ('weak_names', 'weak_sectors'),
    'fx': ('weak_pairs', 'weak_currencies'),
    'commodities': ('weak_names', 'weak_families'),
    'crypto': ('weak_tokens', 'weak_sectors'),
}


def _bias_side(bias: str) -> str:
    b = str(bias or '').lower()
    if 'short' in b:
        return 'short'
    if 'buy' in b or 'long' in b:
        return 'long'
    return ''


def _mkrow(ticker: str, bias: str, bucket: str, score: float | None = None, why: str | None = None) -> dict:
    return {
        'ticker': ticker,
        'bias': bias,
        'bucket': bucket,
        'entry_zone': 'See chart / setup context',
        'trigger': 'See trigger / setup context',
        'invalidation': 'Break of setup logic',
        'target': 'Route-dependent',
        'score': score if score is not None else 0.0,
        'why_now': why or '',
        'why_not_yet': why or '',
    }


def _rows_from_pool(rows: list[dict] | None, actionable: bool | None, side: str | None, market_name: str | None = None) -> list[dict]:
    out: list[dict] = []
    for row in rows or []:
        if market_name and str(row.get('market', '')).strip().lower() != market_name.lower():
            continue
        state = str(row.get('state', '')).lower()
        if actionable is True and state != 'actionable':
            continue
        if actionable is False and state == 'actionable':
            continue
        if side:
            rb = _bias_side(row.get('bias', ''))
            if rb != side:
                continue
        out.append(row)
    return out


def _match_bucket_labels(labels: list[str], bucket_map: dict[str, list[str]]) -> list[tuple[str, list[str]]]:
    matches: list[tuple[str, list[str]]] = []
    low_labels = [str(x).lower() for x in labels if str(x).strip()]
    for bucket, tickers in bucket_map.items():
        b = bucket.lower()
        hit = False
        for lab in low_labels:
            if lab in b or b in lab or any(tok in b for tok in lab.split('/')):
                hit = True
                break
        if hit:
            matches.append((bucket, tickers))
    return matches


def _fallback_rows(section: dict, market_key: str, side: str, actionable: bool) -> list[dict]:
    sw = section.get('strong_weak', {}) or {}
    bucket_map = _BUCKETS.get(market_key, {})
    label_keys = _STRONG_KEYS.get(market_key, ()) if side == 'long' else _WEAK_KEYS.get(market_key, ())
    labels: list[str] = []
    for lk in label_keys:
        vals = sw.get(lk, []) or []
        labels.extend([str(x) for x in vals[:4]])

    matched = _match_bucket_labels(labels, bucket_map)
    if not matched:
        matched = list(bucket_map.items())[:3]

    out: list[dict] = []
    seen = set()
    bias = 'Buy' if market_key == 'ihsg' else ('Long' if side == 'long' else 'Short')
    prefix = 'Actionable fallback' if actionable else 'Front-run fallback'
    for bucket, tickers in matched:
        for t in tickers[:3]:
            if t in seen:
                continue
            seen.add(t)
            out.append(_mkrow(t, bias, bucket, 0.0, f'{prefix} from {bucket} bucket'))
            if len(out) >= 5:
                return out
    return out


def build_market_action_payload(snapshot: dict, section: dict, market_key: str) -> dict[str, list[dict]]:
    market_label = {
        'us': 'us',
        'ihsg': 'ihsg',
        'fx': 'fx',
        'commodities': 'commodities',
        'crypto': 'crypto',
    }.get(market_key, market_key)

    top_now = list(section.get('top_opportunities_now', []) or [])
    top_next = list(section.get('top_opportunities_next', []) or [])

    # fallback to master opportunities if section-specific rows are empty
    if not top_now and not top_next:
        mrows = snapshot.get('master_opportunities', {}).get('rows', []) or []
        pretty_market = {
            'us': 'US',
            'ihsg': 'IHSG',
            'fx': 'FX',
            'commodities': 'Commodities',
            'crypto': 'Crypto',
        }.get(market_key, market_key)
        top_now = _rows_from_pool(mrows, True, None, pretty_market)
        top_next = _rows_from_pool(mrows, False, None, pretty_market)

    if market_key == 'ihsg':
        buy_now = _rows_from_pool(top_now, None, 'long')
        front_run_buy = _rows_from_pool(top_next, None, 'long')
        if not buy_now:
            buy_now = _fallback_rows(section, market_key, 'long', True)
        if not front_run_buy:
            front_run_buy = _fallback_rows(section, market_key, 'long', False)
        avoid = _rows_from_pool(top_now + top_next, None, 'short')[:5]
        if not avoid:
            avoid = _fallback_rows(section, market_key, 'short', False)
        defensive = []
        for bucket, tickers in list(IHSG_BUCKETS.items()):
            if any(x in bucket.lower() for x in ['consumer', 'health']) or bucket.lower().startswith('banks'):
                for t in tickers[:2]:
                    defensive.append({'ticker': t, 'type': bucket, 'why_defensive': f'Defensive / liquid bucket: {bucket}', 'trigger_to_use': 'Use when conflict rises / flow weakens'})
        defensive.append({'ticker': 'Cash', 'type': 'Cash', 'why_defensive': 'Default shelter if IHSG setup quality drops', 'trigger_to_use': 'Use when USD/IDR + flow both deteriorate'})
        return {
            'buy_now': buy_now[:5],
            'front_run_buy': front_run_buy[:5],
            'avoid_reduce': avoid[:5],
            'defensive_shelter': defensive[:5],
        }

    now_long = _rows_from_pool(top_now, None, 'long')
    now_short = _rows_from_pool(top_now, None, 'short')
    fr_long = _rows_from_pool(top_next, None, 'long')
    fr_short = _rows_from_pool(top_next, None, 'short')

    if not now_long:
        now_long = _fallback_rows(section, market_key, 'long', True)
    if not now_short:
        now_short = _fallback_rows(section, market_key, 'short', True)
    if not fr_long:
        fr_long = _fallback_rows(section, market_key, 'long', False)
    if not fr_short:
        fr_short = _fallback_rows(section, market_key, 'short', False)

    avoid = (now_short + fr_short)[:5] if market_key in {'us', 'fx', 'commodities', 'crypto'} else []
    if not avoid:
        avoid = _fallback_rows(section, market_key, 'short', False)

    return {
        'now_long': now_long[:5],
        'now_short': now_short[:5],
        'front_run_long': fr_long[:5],
        'front_run_short': fr_short[:5],
        'avoid_reduce': avoid[:5],
    }


def _frame(rows: list[dict], columns: list[str]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=columns)
    data = []
    for r in rows:
        data.append({c: r.get(c) for c in columns})
    df = pd.DataFrame(data)
    if 'score' in df.columns:
        df['score'] = pd.to_numeric(df['score'], errors='coerce').fillna(0.0).map(lambda x: f'{x:.2f}')
    if 'trigger_distance' in df.columns:
        df['trigger_distance'] = pd.to_numeric(df['trigger_distance'], errors='coerce').map(lambda x: '' if pd.isna(x) else f'{x:.2f}')
    return df


def render_action_table(title: str, rows: list[dict], columns: list[str], rename: dict[str, str] | None = None, empty_msg: str | None = None):
    st.subheader(title)
    if not rows:
        st.info(empty_msg or 'No rows.')
        return
    df = _frame(rows, columns)
    if rename:
        df = df.rename(columns=rename)
    st.dataframe(df, use_container_width=True, hide_index=True, height=frame_height(len(df), base=90, row=36, max_height=360))
