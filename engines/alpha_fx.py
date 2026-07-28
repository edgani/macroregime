"""engines/alpha_fx.py — FX alpha engine (R7): carry/policy-differential tournament.

The ONLY family with admitted data today (see data/research/prereg_r7.json).
Data: FRED short rates via fredgraph CSV (public, release-lagged 1 formation month)
+ spot from cache (yfinance PIT daily bars, resampled monthly).

Conventions:
  USDJPY (JPY per USD): long pair earns (us_rate - jpy_rate)
  EURUSD/GBPUSD/AUDUSD (USD per FCY): long pair earns (fcy_rate - us_rate)

Every trial is logged to the immutable ledger, pass or fail. Lockbox sealed.
"""
from __future__ import annotations

import io
import json
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

RATE_SERIES = {  # FRED immediate short rates (<24h), monthly
    "US": "IRSTCI01USM156N", "JP": "IRSTCI01JPM156N", "EZ": "IRSTCI01EZM156N",
    "GB": "IRSTCI01GBM156N", "AU": "IRSTCI01AUM156N",
}
PAIRS = {  # pair -> (base_ccy, quote_ccy, long_pair_carry = base_rate - quote_rate)
    "USDJPY": ("US", "JP"), "EURUSD": ("EZ", "US"),
    "GBPUSD": ("GB", "US"), "AUDUSD": ("AU", "US"),
}
COST_BPS_PER_LEG = 1.0


def fetch_rate(ccy: str, cache_dir: Path) -> pd.Series:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = cache_dir / f"{RATE_SERIES[ccy]}.csv"
    if fp.exists():
        df = pd.read_csv(fp)
    else:
        url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={RATE_SERIES[ccy]}"
        req = urllib.request.Request(url, headers={"User-Agent": "warroom-r7/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            text = r.read().decode()
        fp.write_text(text)
        df = pd.read_csv(io.StringIO(text))
    df.columns = ["date", "rate"]
    df["date"] = pd.to_datetime(df["date"])
    df["rate"] = pd.to_numeric(df["rate"], errors="coerce")
    return df.set_index("date")["rate"].dropna()


def load_spot(cache_path: Path) -> pd.DataFrame:
    df = pd.read_parquet(cache_path)
    closes = df.xs("Close", level=-1, axis=1) if isinstance(df.columns, pd.MultiIndex) else df
    out = {}
    for pair in PAIRS:
        col = f"{pair}=X"
        if col in closes.columns:
            out[pair] = closes[col].dropna()
    return pd.DataFrame(out)


def run_carry_tournament(ledger, prereg_fam: dict, work_dir: Path,
                         formation_months: int = 1) -> dict:
    """One trial of the carry family. Monthly rebalance, formation-lagged rates."""
    rates = {c: fetch_rate(c, work_dir / "fred_rates") for c in RATE_SERIES}
    spot = load_spot(ROOT / "cache" / "prices.parquet")
    spot_m = spot.resample("ME").last()

    carry = pd.DataFrame(index=spot_m.index)
    for pair, (b, q) in PAIRS.items():
        if pair not in spot_m.columns:
            continue
        carry[pair] = (rates[b].reindex(spot_m.index, method="ffill")
                       - rates[q].reindex(spot_m.index, method="ffill"))
    # formation lag: only use rates published formation_months ago
    carry_signal = carry.shift(formation_months)
    rets = spot_m.pct_change().shift(-1)  # next-month return, realized after signal

    # equal-weight long top-2 carry, short bottom-1 (USD-neutral basket)
    port_ret, bench_ret = [], []
    dates = carry_signal.dropna(how="all").index
    for d in dates:
        sig = carry_signal.loc[d].dropna()
        if len(sig) < 3 or d not in rets.index:
            continue
        r = rets.loc[d, sig.index]
        if r.isna().all():
            continue
        longs = sig.nlargest(2).index
        shorts = sig.nsmallest(1).index
        gross = r[longs].mean() - r[shorts].mean()
        legs = len(longs) + len(shorts)
        cost = legs * COST_BPS_PER_LEG / 10000.0
        port_ret.append(gross - cost)
        bench_ret.append(r.mean())  # naive equal-weight all pairs
    pr = pd.Series(port_ret, dtype=float)
    br = pd.Series(bench_ret, dtype=float)
    n = len(pr)
    ann = pr.mean() * 12 if n else np.nan
    vol = pr.std() * np.sqrt(12) if n > 1 else np.nan
    sharpe = ann / vol if vol and vol > 0 else np.nan
    cum = (1 + pr).cumprod()
    maxdd = float((cum / cum.cummax() - 1).min()) if n else np.nan
    bench_ann = br.mean() * 12 if len(br) else np.nan

    trial = {
        "market": "fx", "family": "carry_policy_differential",
        "parameters": {"formation_months": formation_months, "rebalance": "monthly",
                       "legs": "long2_short1", "cost_bps_per_leg": COST_BPS_PER_LEG},
        "sample": {"periods": n,
                   "span": [str(dates[0].date()), str(dates[-1].date())] if n else None},
        "results": {"ann_return": _r(ann), "ann_vol": _r(vol), "sharpe": _r(sharpe),
                    "max_drawdown": _r(maxdd), "hit_rate": _r(float((pr > 0).mean()) if n else np.nan),
                    "bench_equal_weight_ann": _r(bench_ann),
                    "excess_vs_bench": _r(ann - bench_ann) if n else np.nan},
        "lockbox_touched": False,
        "honest_limits": ["2y spot history only (cache)", "rates release-lagged monthly",
                          "4 pairs only (IDR gated)", "no volatility scaling (frozen)",
                          "preliminary: full walk-forward splits + lockbox in R10"],
    }
    ledger.record({"type": "trial", **trial})
    return trial


def _r(x, nd=4):
    try:
        return None if x is None or not np.isfinite(x) else round(float(x), nd)
    except TypeError:
        return None


def candidate_board(trials: list) -> list:
    """Canonical candidate records. FX emits NO_TRADE until a family passes OOS —
    preliminary in-sample tournament results are NOT tradable signals."""
    from engines.alpha_base import CANDIDATE_SCHEMA
    return [{
        "schema": CANDIDATE_SCHEMA,
        "market": "fx", "instrument": p, "direction": "NO_TRADE",
        "stage": "RESEARCH_ONLY",
        "causal_thesis": "carry/policy differential (preliminary tournament only)",
        "bottleneck": "NO_DATA",
        "expectation_gap": "NO_DATA",
        "activation_stage": "RED_NOT_READY",
        "current_quote": "NO_DATA",
        "projection_low_base_high": None,
        "probability_weighted_target": None,
        "lcb_expected_return": None,
        "horizon": "1-4 quarters (contract)",
        "return_velocity": None,
        "entry": None, "stop": None, "invalidation": "policy path reversal; carry compression",
        "expected_shortfall": None,
        "liquidity_capacity": "major pairs deep; NO_DATA for current depth",
        "selection_reason": "none — carry family has no demonstrated edge (excess ~0 vs baseline)",
        "exclusion_reason": "preliminary in-sample only; OOS + lockbox required (R10)",
        "missing_feeds": ["ois_policy_path", "cftc_tff", "fx_options", "bop_reserves_pit"],
        "reason": "carry family in preliminary tournament; no OOS/lockbox pass yet",
        "proof_state": "MAPPED",
        "execution_eligible": False,
    } for p in PAIRS]
