from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_PATH = ROOT / 'research_v78/protocols/V78_US_EQUITY_VOL12_RISK_CAP_PROTOCOL_FROZEN.json'
RESULTS_PATH = ROOT / 'research_v78/results/V78_US_EQUITY_VOL12_RISK_CAP_RESULTS.json'
SUMMARY_PATH = ROOT / 'research_v78/results/V78_US_EQUITY_VOL12_RISK_CAP_SUMMARY.csv'
LEDGER_PATH = ROOT / 'research_v78/ledgers/V78_US_EQUITY_VOL12_RISK_CAP_LEDGER.csv'


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def max_drawdown(r: pd.Series) -> float:
    w = (1.0 + r.fillna(0.0)).cumprod()
    return float((w / w.cummax() - 1.0).min())


def es5(r: pd.Series) -> float:
    x = r.dropna().to_numpy(float)
    k = max(1, int(math.ceil(len(x) * 0.05)))
    return float(np.partition(x, k - 1)[:k].mean())


def annual_arith(r: pd.Series) -> float:
    return float(r.dropna().mean() * 12.0)


def capture(strategy: pd.Series, base: pd.Series, positive: bool) -> float | None:
    mask = base > 0 if positive else base < 0
    if not bool(mask.any()):
        return None
    den = float(base.loc[mask].mean())
    return None if den == 0 else float(strategy.loc[mask].mean() / den)


def metrics(base: pd.Series, strategy: pd.Series, exposure: pd.Series) -> dict:
    return {
        'n_months': int(len(base)),
        'base_annual_arithmetic_return': annual_arith(base),
        'strategy_annual_arithmetic_return': annual_arith(strategy),
        'annual_return_difference': annual_arith(strategy) - annual_arith(base),
        'base_maximum_drawdown': max_drawdown(base),
        'strategy_maximum_drawdown': max_drawdown(strategy),
        'maximum_drawdown_improvement': max_drawdown(strategy) - max_drawdown(base),
        'base_worst_5pct_expected_shortfall_monthly': es5(base),
        'strategy_worst_5pct_expected_shortfall_monthly': es5(strategy),
        'expected_shortfall_5pct_improvement': es5(strategy) - es5(base),
        'downside_capture': capture(strategy, base, False),
        'upside_capture': capture(strategy, base, True),
        'mean_exposure': float(exposure.mean()),
        'median_exposure': float(exposure.median()),
        'minimum_exposure': float(exposure.min()),
        'turnover_total': float(exposure.diff().abs().fillna(0.0).sum()),
    }


def rolling_risk_shares(base: pd.Series, strategy: pd.Series, window: int = 240) -> tuple[float | None, float | None, int]:
    dd: list[bool] = []
    es: list[bool] = []
    for end in range(window, len(base) + 1, 12):
        b = base.iloc[end-window:end]
        s = strategy.iloc[end-window:end]
        dd.append(max_drawdown(s) > max_drawdown(b))
        es.append(es5(s) > es5(b))
    if not dd:
        return None, None, 0
    return float(np.mean(dd)), float(np.mean(es)), len(dd)


def _np_max_drawdown(x: np.ndarray) -> float:
    w = np.cumprod(1.0 + x)
    return float(np.min(w / np.maximum.accumulate(w) - 1.0))


def _np_es5(x: np.ndarray) -> float:
    k = max(1, int(math.ceil(len(x) * 0.05)))
    return float(np.partition(x, k - 1)[:k].mean())


def block_boot_probability(base: pd.Series, strategy: pd.Series, *, seed: int, reps: int = 10000, block: int = 12) -> float:
    b = base.to_numpy(float)
    s = strategy.to_numpy(float)
    n = len(b)
    starts = np.arange(n)
    offsets = np.arange(block)
    nblocks = int(math.ceil(n / block))
    rng = np.random.default_rng(seed)
    passed = 0
    for _ in range(reps):
        sampled_starts = rng.choice(starts, nblocks, replace=True)
        idx = ((sampled_starts[:, None] + offsets[None, :]) % n).reshape(-1)[:n]
        bb = b[idx]
        ss = s[idx]
        if _np_max_drawdown(ss) > _np_max_drawdown(bb) and _np_es5(ss) > _np_es5(bb):
            passed += 1
    return passed / reps


def load_total_returns(path: Path) -> pd.Series:
    df = pd.read_csv(path)
    df['Date'] = pd.to_datetime(df['Date'])
    for c in ['SP500', 'Dividend']:
        df[c] = pd.to_numeric(df[c], errors='coerce')
    df = df.sort_values('Date').set_index('Date')
    usable = df[(df['SP500'] > 0) & (df['Dividend'] > 0)].copy()
    ret = (usable['SP500'] + usable['Dividend'] / 12.0) / usable['SP500'].shift(1) - 1.0
    ret.name = 'total_return'
    return ret.dropna()


def build_strategy(ret: pd.Series, *, target: float, cost_bps: float, reverse: bool = False) -> pd.DataFrame:
    realized_vol = ret.rolling(12, min_periods=12).std(ddof=1) * math.sqrt(12.0)
    if reverse:
        raw_exposure = (realized_vol / target).clip(lower=0.0, upper=1.0)
    else:
        raw_exposure = (target / realized_vol.replace(0.0, np.nan)).clip(lower=0.0, upper=1.0)
    exposure = raw_exposure.shift(1).fillna(0.0)
    turnover = exposure.diff().abs().fillna(exposure.abs())
    strategy = exposure * ret - turnover * (cost_bps / 10000.0)
    return pd.concat({'base': ret, 'strategy': strategy, 'exposure': exposure, 'realized_vol': realized_vol.shift(1)}, axis=1).dropna()


def evaluate_period(full: pd.DataFrame, start: str, end: str, *, seed: int) -> dict:
    x = full.loc[(full.index >= pd.Timestamp(start)) & (full.index <= pd.Timestamp(end))].copy()
    out = metrics(x['base'], x['strategy'], x['exposure'])
    dd_share, es_share, nwin = rolling_risk_shares(x['base'], x['strategy'])
    out.update({
        'period_start': str(x.index.min().date()),
        'period_end': str(x.index.max().date()),
        'rolling_20y_drawdown_improvement_share': dd_share,
        'rolling_20y_expected_shortfall_improvement_share': es_share,
        'rolling_20y_windows': nwin,
        'moving_block_boot_probability_both_risk_metrics_improve': block_boot_probability(x['base'], x['strategy'], seed=seed),
    })
    return out


def period_pass(m: dict, gate: dict, *, require_rolling: bool = True) -> bool:
    rolling_ok = True
    if require_rolling:
        rolling_ok = bool(
            m['rolling_20y_drawdown_improvement_share'] is not None and
            m['rolling_20y_drawdown_improvement_share'] >= gate['rolling_20y_drawdown_improvement_share_min'] and
            m['rolling_20y_expected_shortfall_improvement_share'] is not None and
            m['rolling_20y_expected_shortfall_improvement_share'] >= gate['rolling_20y_expected_shortfall_improvement_share_min']
        )
    return bool(
        m['maximum_drawdown_improvement'] >= gate['maximum_drawdown_improvement_min'] and
        m['expected_shortfall_5pct_improvement'] > gate['expected_shortfall_5pct_improvement_gt'] and
        m['annual_return_difference'] >= gate['annualized_return_shortfall_min'] and
        m['downside_capture'] is not None and m['downside_capture'] <= gate['downside_capture_max'] and
        m['upside_capture'] is not None and m['upside_capture'] >= gate['upside_capture_min'] and
        m['moving_block_boot_probability_both_risk_metrics_improve'] >= gate['moving_block_boot_probability_both_risk_metrics_improve_min'] and
        rolling_ok
    )


def main() -> None:
    protocol = json.loads(PROTOCOL_PATH.read_text())
    if protocol['status'] != 'FROZEN_BEFORE_RESULT_COMPUTATION':
        raise RuntimeError('protocol is not frozen')
    source = ROOT / protocol['input']['path']
    if sha(source) != protocol['input']['sha256']:
        raise RuntimeError('input hash mismatch')
    ret = load_total_returns(source)
    target = float(protocol['signal']['annual_volatility_target'])
    primary_bps = float(protocol['cost']['primary_one_way_bps_per_100pct_turnover'])
    stress_bps = float(protocol['cost']['stress_one_way_bps_per_100pct_turnover'])
    normal = build_strategy(ret, target=target, cost_bps=primary_bps, reverse=False)
    stress = build_strategy(ret, target=target, cost_bps=stress_bps, reverse=False)
    reverse = build_strategy(ret, target=target, cost_bps=primary_bps, reverse=True)
    periods = protocol['periods']
    usable_end = str(normal.index.max().date())
    resolved = {
        k: [v[0], usable_end if v[1] == 'LATEST_USABLE_MONTH' else v[1]]
        for k, v in periods.items()
    }
    result_periods: dict[str, dict] = {}
    rows: list[dict] = []
    for i, name in enumerate(['historical_replication', 'validation', 'lockbox']):
        start, end = resolved[name]
        n = evaluate_period(normal, start, end, seed=78200 + i)
        s = evaluate_period(stress, start, end, seed=78300 + i)
        r = evaluate_period(reverse, start, end, seed=78400 + i)
        result_periods[name] = {'normal_10bps': n, 'stress_25bps': s, 'reverse_control_10bps': r}
        for label, metrics_row in result_periods[name].items():
            rows.append({'period': name, 'rule': label, **metrics_row})
    gate = protocol['promotion_gate']
    v = result_periods['validation']['normal_10bps']
    l = result_periods['lockbox']['normal_10bps']
    l_stress = result_periods['lockbox']['stress_25bps']
    reverse_pass = period_pass(result_periods['validation']['reverse_control_10bps'], gate) and period_pass(result_periods['lockbox']['reverse_control_10bps'], gate)
    passed = bool(
        period_pass(v, gate) and
        period_pass(l, gate) and
        l_stress['expected_shortfall_5pct_improvement'] > gate['stress_25bps_expected_shortfall_improvement_gt'] and
        not reverse_pass
    )
    status = 'HISTORICAL_US_EQUITY_VOLATILITY_RISK_CAP_SUPPORTED' if passed else 'NOT_PROMOTED'
    results = {
        'schema': 'warroom.v78.us_equity_vol12_risk_cap_results.v1',
        'protocol_sha256': sha(PROTOCOL_PATH),
        'input_sha256': sha(source),
        'candidate_id': protocol['candidate_id'],
        'status': status,
        'promoted': passed,
        'periods': result_periods,
        'gate_evaluation': {
            'validation_pass': period_pass(v, gate),
            'lockbox_pass': period_pass(l, gate),
            'stress_25bps_expected_shortfall_pass': l_stress['expected_shortfall_5pct_improvement'] > gate['stress_25bps_expected_shortfall_improvement_gt'],
            'reverse_control_passed_same_gate': reverse_pass,
        },
        'claim_boundary': protocol['claim_boundary'],
        'capital_permission': 'BLOCKED_PENDING_EXACT_LIVE_TOTAL_RETURN_INPUT_AND_RUNTIME_VALIDATION' if passed else 'BLOCKED',
        'live_decision_weight': 0.0,
        'no_post_outcome_retuning': True,
    }
    RESULTS_PATH.write_text(json.dumps(results, indent=2, sort_keys=True))
    pd.DataFrame(rows).to_csv(LEDGER_PATH, index=False)
    pd.DataFrame([{
        'candidate_id': protocol['candidate_id'],
        'status': status,
        'validation_pass': results['gate_evaluation']['validation_pass'],
        'lockbox_pass': results['gate_evaluation']['lockbox_pass'],
        'reverse_control_passed_same_gate': reverse_pass,
        'validation_return_difference': v['annual_return_difference'],
        'validation_drawdown_improvement': v['maximum_drawdown_improvement'],
        'validation_es_improvement': v['expected_shortfall_5pct_improvement'],
        'validation_boot_probability': v['moving_block_boot_probability_both_risk_metrics_improve'],
        'lockbox_return_difference': l['annual_return_difference'],
        'lockbox_drawdown_improvement': l['maximum_drawdown_improvement'],
        'lockbox_es_improvement': l['expected_shortfall_5pct_improvement'],
        'lockbox_boot_probability': l['moving_block_boot_probability_both_risk_metrics_improve'],
        'lockbox_mean_exposure': l['mean_exposure'],
        'capital_permission': results['capital_permission'],
        'live_decision_weight': 0.0,
    }]).to_csv(SUMMARY_PATH, index=False)
    print(json.dumps({'status': status, **results['gate_evaluation']}, indent=2))


if __name__ == '__main__':
    main()
