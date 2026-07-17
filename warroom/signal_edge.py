"""warroom/signal_edge.py — bisa sistem nangkep PEMENANG sebelum lari? (event study, jujur).

Jawaban buat pertanyaan Edward: "SNDK/PLTR naik for a reason — bisa ga kita dapet SEBELUM surging,
di harga berapa masuk, kapan keluar?" Modul ini nguji itu secara rigorous dan JUJUR soal edge.

Temuan dari data real (S&P 500, 2013-2018 — lihat research/RESEARCH_FINDINGS.md):
  • Sinyal absolut (breakout, volume-spike, base-breakout) → lift 0.56-1.01x = TIDAK ada edge.
  • CROSS-SECTIONAL RS top-decile → lift 2.08x = ada tail edge. Nangkep AMD $2.52→$12 (+380%),
    MU $14→$27, AVGO, SWKS dengan entry/exit konkret.
  • TAPI excess return top-decile p=0.12 (TIDAK signifikan di 5thn) → sebagian besar beta, alpha
    belum kebukti. "Always be the winner" itu mustahil; yang realistis = edge kecil yang teruji.

Metodologi (yang bikin ini bukan asal bunyi):
  1. LIFT = P(surge | sinyal nyala) / P(surge | hari random). >1.3 = edge; ~1.0 = coin flip.
  2. Entry/exit discipline: kapan nama MASUK rekomendasi (cross ke top-decile), kapan KELUAR (drop out),
     di harga berapa. Return per trade + win rate + hold.
  3. Alpha vs beta: excess return vs equal-weight benchmark + t-stat. Beta-adjusted alpha.

Semua terima data LU. Tanpa data → None. Ga ngarang. Ini alat uji, bukan ramalan.
"""
from __future__ import annotations
import numpy as np
import pandas as pd

try:
    from scipy import stats as _stats
    _HAVE_SCIPY = True
except Exception:
    _HAVE_SCIPY = False


def _ew_benchmark(close):
    dret = close.pct_change().fillna(0)
    return (1 + dret.mean(axis=1)).cumprod()


def surge_precision(close, signal_matrix, surge_thresh=0.30, horizon=63):
    """LIFT test: saat sinyal nyala (fresh), seberapa sering surge (+surge_thresh dalam `horizon` hari)?
    Bandingkan vs base rate. signal_matrix: bool DataFrame [dates × tickers]. Return dict + verdict."""
    fwd = close.shift(-horizon) / close - 1
    base = (fwd >= surge_thresh).sum().sum() / max(1, fwd.notna().sum().sum())
    turns = signal_matrix & ~signal_matrix.shift(1).fillna(False)
    hits = tot = 0
    for t in close.columns:
        for dt in turns[t][turns[t]].index:
            loc = close.index.get_loc(dt)
            if loc < len(close) - horizon:
                c0 = close[t].iloc[loc]
                if pd.notna(c0):
                    fr = close[t].iloc[loc + horizon] / c0 - 1
                    tot += 1
                    hits += int(fr >= surge_thresh)
    if tot < 20:
        return {"error": "too few signal fires", "fires": tot}
    p = hits / tot
    lift = p / base if base > 0 else None
    return {"fires": tot, "surge_hit_rate": round(p, 4), "base_rate": round(base, 4),
            "lift": round(lift, 2) if lift else None,
            "verdict": ("EDGE — beats random" if lift and lift > 1.3 else
                        "weak" if lift and lift > 1.05 else "NO edge — ≈ random/worse")}


def rs_rank_signal(close, lookback=126, decile=0.90):
    """Cross-sectional relative-strength top-decile membership (the ONE signal with edge in testing)."""
    ew = _ew_benchmark(close)
    rs = (close / close.shift(lookback) - 1).sub((ew / ew.shift(lookback) - 1), axis=0)
    rank = rs.rank(axis=1, pct=True)
    return rank > decile


def strategy_with_entries(close, signal_matrix, rebal_days=21):
    """Hold names while signal true; monthly rebalance. Return per-trade entry/exit log + summary.
    Ini jawaban 'di harga berapa masuk, kapan keluar'. signal_matrix bool [dates × tickers]."""
    ew = _ew_benchmark(close)
    reb = close.index[::rebal_days]
    holdings = set(); entry_px = {}; entry_dt = {}
    trades = []; pr = []; br = []
    for i, dt in enumerate(reb[:-1]):
        nxt = reb[i + 1]
        row = signal_matrix.loc[dt] if dt in signal_matrix.index else None
        cur = set(row[row].dropna().index) if row is not None else set()
        for t in cur - holdings:
            entry_px[t] = close[t].asof(dt); entry_dt[t] = dt
        for t in holdings - cur:
            if t in entry_px and pd.notna(entry_px[t]):
                ex = close[t].asof(dt)
                if pd.notna(ex):
                    trades.append({"ticker": t, "entry_dt": str(entry_dt[t].date()), "entry_px": round(float(entry_px[t]), 2),
                                   "exit_dt": str(dt.date()), "exit_px": round(float(ex), 2),
                                   "ret_pct": round(float(ex / entry_px[t] - 1) * 100, 1),
                                   "days": (dt - entry_dt[t]).days})
        holdings = cur
        seg = close.loc[dt:nxt]
        if len(seg) > 1 and cur:
            pr.append(float((seg[list(cur)].iloc[-1] / seg[list(cur)].iloc[0] - 1).mean()))
            b = ew.loc[dt:nxt]; br.append(float(b.iloc[-1] / b.iloc[0] - 1))
        else:
            pr.append(0.0); b = ew.loc[dt:nxt]; br.append(float(b.iloc[-1] / b.iloc[0] - 1) if len(b) > 1 else 0.0)
    pr, br = np.array(pr), np.array(br)
    T = pd.DataFrame(trades)
    ann = 252 / rebal_days; n = len(pr)
    summary = {"n_months": n, "n_trades": len(T),
               "strat_ann_pct": round((np.prod(1 + pr) ** (ann / n) - 1) * 100, 1) if n else None,
               "bench_ann_pct": round((np.prod(1 + br) ** (ann / n) - 1) * 100, 1) if n else None,
               "sharpe": round(pr.mean() / pr.std() * np.sqrt(ann), 2) if pr.std() > 0 else None}
    if len(T):
        summary.update({"win_rate": round((T.ret_pct > 0).mean(), 2), "avg_trade_pct": round(T.ret_pct.mean(), 1),
                        "avg_win_pct": round(T[T.ret_pct > 0].ret_pct.mean(), 1),
                        "avg_loss_pct": round(T[T.ret_pct < 0].ret_pct.mean(), 1) if (T.ret_pct < 0).any() else None,
                        "avg_hold_days": round(T.days.mean(), 0)})
    # alpha vs beta
    if _HAVE_SCIPY and n > 10:
        excess = pr - br
        t, p = _stats.ttest_1samp(excess, 0)
        beta = np.cov(pr, br)[0, 1] / np.var(br) if np.var(br) > 0 else None
        alpha_mo = pr.mean() - (beta * br.mean() if beta else 0)
        summary["alpha_test"] = {"excess_mo_pct": round(excess.mean() * 100, 2), "t_stat": round(float(t), 2),
                                 "p_value": round(float(p), 3), "beta": round(beta, 2) if beta else None,
                                 "alpha_ann_pct": round(alpha_mo * ann * 100, 1),
                                 "verdict": ("REAL ALPHA (p<0.05)" if p < 0.05 and excess.mean() > 0
                                             else "mostly BETA — alpha not proven")}
    return {"summary": summary, "trades": T, "top_winners": T.sort_values("ret_pct", ascending=False).head(10) if len(T) else T}


def valuation_room(cape_series, price_series, current_cape=None):
    """Jawaban 'bubble/valuasi ekstrem → berapa room & berapa lama'. cape_series+price_series monthly.
    Return forward-return-by-valuation + median months to next -20% from high valuation."""
    df = pd.DataFrame({"cape": cape_series, "px": price_series}).dropna()
    if len(df) < 120:
        return {"error": "insufficient history"}
    df["fwd12"] = df["px"].shift(-12) / df["px"] - 1
    df["fwd36"] = df["px"].shift(-36) / df["px"] - 1
    cur = current_cape if current_cape is not None else df["cape"].iloc[-1]
    pct = (df["cape"] < cur).mean()
    hi = df[df["cape"] >= cur * 0.9].dropna(subset=["fwd12"])
    dd = df["px"] / df["px"].cummax() - 1
    gaps = []
    for dt in df[df["cape"] > 30].index:
        fut = dd.loc[dt:]; crash = fut[fut < -0.20]
        if len(crash):
            gaps.append((crash.index[0] - dt).days / 30)
    return {"current_cape": round(float(cur), 1), "percentile": round(float(pct) * 100, 0),
            "when_this_high": {"fwd_1yr_pct": round(float(hi["fwd12"].mean()) * 100, 0),
                               "fwd_3yr_pct": round(float(hi["fwd36"].mean()) * 100, 0),
                               "pct_1yr_positive": round(float((hi["fwd12"] > 0).mean()) * 100, 0)},
            "months_to_next_20pct_drawdown": {"median": round(float(np.median(gaps)), 0) if gaps else None,
                                              "min": round(float(np.min(gaps)), 0) if gaps else None,
                                              "max": round(float(np.max(gaps)), 0) if gaps else None},
            "interpretation": ("High valuation lowers forward return & raises tail risk, but does NOT time "
                               "the top — historically years of room can remain.")}
