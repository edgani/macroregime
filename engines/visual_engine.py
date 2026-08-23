from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[1]


def _s(x):
    try:
        z = pd.Series(x).dropna().sort_index()
        z.index = pd.to_datetime(z.index).tz_localize(None)
        return z
    except Exception:
        return pd.Series(dtype=float)


def _last(d, key):
    try:
        x = d.get(key, np.nan)
        return float(x) if np.isfinite(float(x)) else np.nan
    except Exception:
        return np.nan


def headline_states(state):
    """Descriptive labels only. They are not trade rules or probabilities."""
    g = state.get('Growth', {})
    i = state.get('Inflation', {})
    r = state.get('Policy/Rates', {})
    c = state.get('Credit/Funding', {})
    v = state.get('Volatility', {})

    cf = _last(g, 'CFNAI')
    claims = _last(g, 'Claims_13w_pct')
    if np.isfinite(cf) and np.isfinite(claims):
        growth = 'RESILIENT' if cf >= 0 and claims <= .10 else ('WEAKENING' if cf < -.7 or claims > .15 else 'MIXED')
    elif np.isfinite(cf):
        growth = 'RESILIENT' if cf >= 0 else ('WEAKENING' if cf < -.7 else 'MIXED')
    else:
        growth = 'NO DATA'

    core = _last(i, 'Core_3m_ann')
    inflation = 'NO DATA'
    if np.isfinite(core):
        inflation = 'COOLING' if core < .025 else ('STICKY' if core < .035 else 'HOT')

    rp = _last(r, 'Real10Y_percentile')
    rates = 'NO DATA'
    if np.isfinite(rp):
        rates = 'HIGH HURDLE' if rp >= .75 else ('EASIER' if rp <= .25 else 'MID-RANGE')

    hyp = _last(c, 'HYOAS_percentile')
    hyd = _last(c, 'HYOAS_13w_delta')
    credit = 'NO DATA'
    if np.isfinite(hyp) or np.isfinite(hyd):
        if (np.isfinite(hyp) and hyp >= .75) or (np.isfinite(hyd) and hyd >= .75):
            credit = 'STRESS RISING'
        elif (not np.isfinite(hyp) or hyp < .5) and (not np.isfinite(hyd) or hyd < .25):
            credit = 'BENIGN'
        else:
            credit = 'WATCH'

    fund = _last(c, 'SOFR_minus_IORB')
    funding = 'NO DATA'
    if np.isfinite(fund):
        funding = 'DISLOCATED' if fund > .25 else ('WATCH' if fund > .10 else 'NORMAL')

    vp = _last(v, 'VIX_5y_percentile')
    vol = 'NO DATA'
    if np.isfinite(vp):
        vol = 'STRESSED' if vp >= .90 else ('CALM' if vp <= .25 else 'NORMAL')

    return {
        'Growth': (growth, cf),
        'Inflation': (inflation, core),
        'Rates': (rates, _last(r, 'Real10Y')),
        'Credit': (credit, _last(c, 'HYOAS')),
        'Funding': (funding, fund),
        'Volatility': (vol, _last(v, 'VIX')),
    }


def percentile_strip(state):
    rows = []
    specs = [
        ('Growth activity', state.get('Growth', {}).get('CFNAI_percentile'), 'CFNAI own-history percentile'),
        ('Inflation expectations', state.get('Inflation', {}).get('Breakeven_percentile'), '5Y breakeven own-history percentile'),
        ('Real yield', state.get('Policy/Rates', {}).get('Real10Y_percentile'), '10Y real-yield own-history percentile'),
        ('Credit stress', state.get('Credit/Funding', {}).get('HYOAS_percentile'), 'HY OAS own-history percentile'),
        ('Volatility', state.get('Volatility', {}).get('VIX_5y_percentile'), 'VIX 5Y percentile'),
        ('USD', state.get('FX', {}).get('USD_percentile'), 'Trade-weighted USD own-history percentile'),
    ]
    for name, val, note in specs:
        try:
            v = float(val)
        except Exception:
            v = np.nan
        rows.append({'driver': name, 'percentile': v, 'note': note})
    return pd.DataFrame(rows)


def _hist_change(s, days=91, pct=False):
    z = _s(s)
    if len(z) < 30:
        return pd.Series(dtype=float)
    old = z.reindex(z.index - pd.Timedelta(days=days), method='ffill')
    old.index = z.index
    if pct:
        out = z / old - 1
    else:
        out = z - old
    return out.replace([np.inf, -np.inf], np.nan).dropna()


def standardized_shocks(fred):
    """Current 13-week move as z-score vs its own history. Comparable across units; not an alpha score."""
    specs = [
        ('Claims', 'ICSA', True),
        ('Bank credit', 'TOTLL', True),
        ('Real yield', 'DFII10', False),
        ('Term premium', 'THREEFYTP10', False),
        ('HY OAS', 'BAMLH0A0HYM2', False),
        ('USD', 'DTWEXBGS', True),
        ('Breakeven', 'T5YIE', False),
    ]
    rows = []
    for label, sid, pct in specs:
        h = _hist_change(fred.get(sid, []), 91, pct)
        if len(h) < 30:
            rows.append({'driver': label, 'z_13w': np.nan, 'raw_change': np.nan, 'series': sid})
            continue
        h = h.tail(min(len(h), 2600))
        cur = float(h.iloc[-1])
        sd = float(h.std(ddof=1))
        z = (cur - float(h.mean())) / sd if sd > 0 else np.nan
        rows.append({'driver': label, 'z_13w': z, 'raw_change': cur, 'series': sid})
    return pd.DataFrame(rows)


def _monthly_macro_features(fred, years=10):
    end = None
    for s in fred.values():
        z = _s(s)
        if len(z):
            end = max(end, z.index[-1]) if end is not None else z.index[-1]
    cutoff = end - pd.DateOffset(years=years) if end is not None else None

    feats = {}
    # Use economically interpretable transformations rather than raw-level correlations where practical.
    for label, sid, transform in [
        ('Growth activity', 'CFNAI', 'level'),
        ('Claims', 'ICSA', 'pct'),
        ('Core inflation', 'CPILFESL', 'yoy'),
        ('Real yield', 'DFII10', 'diff'),
        ('Term premium', 'THREEFYTP10', 'diff'),
        ('HY OAS', 'BAMLH0A0HYM2', 'diff'),
        ('Financial conditions', 'NFCI', 'diff'),
        ('Breakeven', 'T5YIE', 'diff'),
        ('USD', 'DTWEXBGS', 'pct'),
        ('VIX', 'VIXCLS', 'pct'),
    ]:
        s = _s(fred.get(sid, []))
        if not len(s):
            continue
        m = s.resample('ME').last()
        if transform == 'pct':
            x = m.pct_change()
        elif transform == 'diff':
            x = m.diff()
        elif transform == 'yoy':
            x = m.pct_change(12)
        else:
            x = m
        if cutoff is not None:
            x = x.loc[x.index >= cutoff]
        feats[label] = x
    return pd.concat(feats, axis=1).dropna(how='all') if feats else pd.DataFrame()


def macro_correlation(fred, years=10):
    d = _monthly_macro_features(fred, years)
    return d.corr(min_periods=24) if not d.empty else pd.DataFrame()


def macro_asset_relationships(fred, prices, years=10, horizon_months=1):
    F = _monthly_macro_features(fred, years)
    if F.empty:
        return pd.DataFrame()
    rows = []
    for tk, p in prices.items():
        s = _s(p)
        if len(s) < 60:
            continue
        m = s.resample('ME').last()
        fwd = (m.shift(-horizon_months) / m - 1).rename('asset_return')
        d = F.join(fwd).dropna(subset=['asset_return'])
        for factor in F.columns:
            z = d[[factor, 'asset_return']].dropna()
            if len(z) < 36:
                continue
            corr = z[factor].corr(z['asset_return'])
            rows.append({'factor': factor, 'instrument': tk, 'correlation': corr, 'n': len(z), 'horizon_months': horizon_months})
    return pd.DataFrame(rows)


def relationship_scatter(fred, price, factor, years=10, horizon_months=1):
    F = _monthly_macro_features(fred, years)
    if F.empty or factor not in F.columns:
        return pd.DataFrame()
    s = _s(price)
    if len(s) < 60:
        return pd.DataFrame()
    m = s.resample('ME').last()
    fwd = (m.shift(-horizon_months) / m - 1).rename('forward_return')
    d = F[[factor]].join(fwd).dropna().rename(columns={factor: 'factor_value'})
    return d


def bundled_macro_panel():
    p = HERE / 'research' / 'legacy_data' / 'macro_panel.parquet'
    if not p.exists():
        return pd.DataFrame()
    try:
        d = pd.read_parquet(p)
        if not isinstance(d.index, pd.DatetimeIndex):
            for c in ['date', 'Date', 'DATE']:
                if c in d.columns:
                    d[c] = pd.to_datetime(d[c], errors='coerce')
                    d = d.set_index(c)
                    break
        return d.sort_index()
    except Exception:
        return pd.DataFrame()


def bundled_longrun_correlation():
    d = bundled_macro_panel()
    if d.empty:
        return pd.DataFrame()
    cols = [c for c in ['spx', 'cape', 'cpi_yoy', 'rate10', 'gold', 'oil', 'gas', 'dxy'] if c in d.columns]
    z = d[cols].copy()
    # Price-like columns use returns; state-like columns use changes/levels as appropriate.
    for c in ['spx', 'gold', 'oil', 'gas', 'dxy']:
        if c in z.columns:
            z[c] = z[c].pct_change()
    for c in ['rate10']:
        if c in z.columns:
            z[c] = z[c].diff()
    return z.corr(min_periods=24)
