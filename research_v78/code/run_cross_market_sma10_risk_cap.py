from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / 'research_v78/protocols/V78_CROSS_MARKET_SMA10_RISK_CAP_PROTOCOL_FROZEN.json'
RESULTS_PATH = ROOT / 'research_v78/results/V78_CROSS_MARKET_SMA10_RISK_CAP_RESULTS.json'
SUMMARY_PATH = ROOT / 'research_v78/results/V78_CROSS_MARKET_SMA10_RISK_CAP_SUMMARY.csv'
LEDGER_PATH = ROOT / 'research_v78/ledgers/V78_CROSS_MARKET_SMA10_RISK_CAP_LEDGER.csv'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_frame(path: Path) -> pd.DataFrame:
    import sys
    sys.path.insert(0, str(ROOT))
    from parquet_compat import read_parquet_compat
    df = read_parquet_compat(path)
    if not isinstance(df.index, pd.DatetimeIndex):
        df.index = pd.to_datetime(df.index)
    return df.sort_index()


def max_drawdown(r: pd.Series) -> float:
    wealth = (1.0 + r.fillna(0.0)).cumprod()
    peak = wealth.cummax()
    return float((wealth / peak - 1.0).min())


def es5(r: pd.Series) -> float:
    x = r.dropna().sort_values()
    if x.empty:
        return float('nan')
    k = max(1, int(math.ceil(len(x) * 0.05)))
    return float(x.iloc[:k].mean())


def annual_arith(r: pd.Series) -> float:
    return float(r.dropna().mean() * 12.0)


def capture(strategy: pd.Series, base: pd.Series, positive: bool) -> float | None:
    mask = base > 0 if positive else base < 0
    if mask.sum() == 0:
        return None
    den = float(base[mask].mean())
    if den == 0:
        return None
    return float(strategy[mask].mean() / den)


def risk_metrics(base: pd.Series, strat: pd.Series) -> dict:
    return {
        'n_months': int(len(base)),
        'base_annual_arithmetic_return': annual_arith(base),
        'strategy_annual_arithmetic_return': annual_arith(strat),
        'annual_return_difference': annual_arith(strat) - annual_arith(base),
        'base_maximum_drawdown': max_drawdown(base),
        'strategy_maximum_drawdown': max_drawdown(strat),
        'drawdown_improvement': max_drawdown(strat) - max_drawdown(base),
        'base_worst_5pct_expected_shortfall_monthly': es5(base),
        'strategy_worst_5pct_expected_shortfall_monthly': es5(strat),
        'expected_shortfall_improvement': es5(strat) - es5(base),
        'downside_capture': capture(strat, base, False),
        'upside_capture': capture(strat, base, True),
    }


def rolling_improvement(base: pd.Series, strat: pd.Series, window: int = 120) -> tuple[float | None, float | None, int]:
    dd = []
    es = []
    for i in range(window, len(base) + 1):
        b = base.iloc[i-window:i]
        s = strat.iloc[i-window:i]
        dd.append(max_drawdown(s) > max_drawdown(b))
        es.append(es5(s) > es5(b))
    if not dd:
        return None, None, 0
    return float(np.mean(dd)), float(np.mean(es)), len(dd)


def _np_max_drawdown(x: np.ndarray) -> float:
    wealth = np.cumprod(1.0 + x)
    peak = np.maximum.accumulate(wealth)
    return float(np.min(wealth / peak - 1.0))

def _np_es5(x: np.ndarray) -> float:
    k = max(1, int(math.ceil(len(x) * 0.05)))
    return float(np.partition(x, k-1)[:k].mean())

def block_boot_prob(base: pd.Series, strat: pd.Series, seed: int, reps: int = 3000, block: int = 12) -> float:
    b = base.to_numpy(float)
    s = strat.to_numpy(float)
    n = len(b)
    rng = np.random.default_rng(seed)
    starts = np.arange(n)
    offsets = np.arange(block)
    nblocks = int(math.ceil(n / block))
    passed = 0
    for _ in range(reps):
        ss = rng.choice(starts, nblocks, replace=True)
        idx = ((ss[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
        bb = b[idx]
        st = s[idx]
        if _np_max_drawdown(st) > _np_max_drawdown(bb) and _np_es5(st) > _np_es5(bb):
            passed += 1
    return passed / reps


def build_returns(level: pd.Series, cost: float, reverse: bool = False) -> tuple[pd.Series, pd.Series, pd.Series]:
    level = level.dropna().astype(float)
    ret = level.pct_change()
    sma = level.rolling(10, min_periods=10).mean()
    raw = (level >= sma).astype(float)
    if reverse:
        raw = 1.0 - raw
    position = raw.shift(1)
    switches = position.diff().abs().fillna(0.0)
    strat = position * ret - switches * cost
    aligned = pd.concat({'base': ret, 'strategy': strat, 'position': position}, axis=1).dropna()
    return aligned['base'], aligned['strategy'], aligned['position']


def period_eval(level: pd.Series, start: str, end: str, cost: float, seed: int, reverse: bool = False) -> dict:
    # Preserve pre-start observations for the 10-month signal, then slice realized returns.
    base, strat, position = build_returns(level.loc[:pd.Timestamp(end)], cost=cost, reverse=reverse)
    mask = (base.index >= pd.Timestamp(start)) & (base.index <= pd.Timestamp(end))
    base = base.loc[mask]
    strat = strat.loc[mask]
    position = position.loc[mask]
    m = risk_metrics(base, strat)
    dd_share, es_share, windows = rolling_improvement(base, strat, 120)
    m.update({
        'rolling_10y_drawdown_improvement_share': dd_share,
        'rolling_10y_expected_shortfall_improvement_share': es_share,
        'rolling_10y_windows': windows,
        'moving_block_boot_probability_both_risk_metrics_improve': block_boot_prob(base, strat, seed=seed),
        'exposure_share': float(position.mean()),
        'switch_count': int(position.diff().abs().fillna(0).sum()),
    })
    return m


def main() -> None:
    p = json.loads(PROTOCOL_PATH.read_text())
    if p['status'] != 'FROZEN_BEFORE_RESULT_COMPUTATION':
        raise RuntimeError('protocol not frozen')
    source = ROOT / p['input']['path']
    if sha(source) != p['input']['sha256']:
        raise RuntimeError('source hash mismatch')
    df = load_frame(source)
    cost = 0.0025
    gate = p['promotion_gate']
    results = {
        'schema': 'warroom.v78.cross_market_sma10_risk_cap_results.v1',
        'protocol_sha256': sha(PROTOCOL_PATH),
        'input_sha256': sha(source),
        'assets': {},
        'claim_boundary': p['claim_boundary'],
        'capital_permission': 'BLOCKED_UNTIL_EXACT_LIVE_INSTRUMENT_MAPPING',
        'live_decision_weight': 0.0,
    }
    summary = []
    ledger = []
    promoted = []
    for i, (asset, splits) in enumerate(p['assets'].items()):
        if asset not in df.columns:
            raise RuntimeError(f'missing asset {asset}')
        asset_out = {}
        normal = {}
        reverse = {}
        for j, period in enumerate(['validation', 'lockbox']):
            start, end = splits[period]
            normal[period] = period_eval(df[asset], start, end, cost, seed=78020 + i*10 + j, reverse=False)
            reverse[period] = period_eval(df[asset], start, end, cost, seed=78120 + i*10 + j, reverse=True)
            ledger.append({'asset': asset, 'rule': 'normal', 'period': period, **normal[period]})
            ledger.append({'asset': asset, 'rule': 'reverse', 'period': period, **reverse[period]})
        v, l = normal['validation'], normal['lockbox']
        rv, rl = reverse['validation'], reverse['lockbox']
        def gates(x: dict, lockbox: bool) -> bool:
            return bool(
                x['drawdown_improvement'] > 0 and
                x['expected_shortfall_improvement'] > 0 and
                x['annual_return_difference'] >= -gate['lockbox_annual_return_shortfall_max' if lockbox else 'validation_annual_return_shortfall_max'] and
                (not lockbox or (
                    x['rolling_10y_drawdown_improvement_share'] is not None and x['rolling_10y_drawdown_improvement_share'] >= gate['lockbox_rolling10y_drawdown_improvement_share_min'] and
                    x['rolling_10y_expected_shortfall_improvement_share'] is not None and x['rolling_10y_expected_shortfall_improvement_share'] >= gate['lockbox_rolling10y_es_improvement_share_min']
                )) and
                x['moving_block_boot_probability_both_risk_metrics_improve'] >= gate['moving_block_boot_probability_both_risk_metrics_improve_min']
            )
        reverse_pass = gates(rv, False) and gates(rl, True)
        passed = gates(v, False) and gates(l, True) and not reverse_pass
        status = 'HISTORICAL_SPOT_LEVEL_RISK_CAP_SUPPORTED' if passed else 'NOT_PROMOTED'
        if passed:
            promoted.append(asset)
        asset_out['normal_rule'] = normal
        asset_out['reverse_control'] = reverse
        asset_out['reverse_control_passed_same_gate'] = reverse_pass
        asset_out['status'] = status
        results['assets'][asset] = asset_out
        summary.append({
            'asset': asset,
            'status': status,
            'validation_return_difference': v['annual_return_difference'],
            'validation_drawdown_improvement': v['drawdown_improvement'],
            'validation_es_improvement': v['expected_shortfall_improvement'],
            'validation_boot_probability': v['moving_block_boot_probability_both_risk_metrics_improve'],
            'lockbox_return_difference': l['annual_return_difference'],
            'lockbox_drawdown_improvement': l['drawdown_improvement'],
            'lockbox_es_improvement': l['expected_shortfall_improvement'],
            'lockbox_rolling10y_drawdown_improvement_share': l['rolling_10y_drawdown_improvement_share'],
            'lockbox_rolling10y_es_improvement_share': l['rolling_10y_expected_shortfall_improvement_share'],
            'lockbox_boot_probability': l['moving_block_boot_probability_both_risk_metrics_improve'],
            'reverse_control_passed': reverse_pass,
            'capital_permission': 'BLOCKED_UNTIL_EXACT_LIVE_INSTRUMENT_MAPPING',
            'live_decision_weight': 0.0,
        })
    results['promotion'] = {
        'supported_assets': promoted,
        'supported_count': len(promoted),
        'decision_active_count': 0,
        'reason_decision_inactive': 'Bundled series are spot/index histories, not exact investable total-return futures/ETF implementations with roll and carry.'
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2, sort_keys=True))
    pd.DataFrame(summary).to_csv(SUMMARY_PATH, index=False)
    pd.DataFrame(ledger).to_csv(LEDGER_PATH, index=False)
    print(json.dumps(results['promotion'], indent=2))


if __name__ == '__main__':
    main()
