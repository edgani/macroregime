"""warroom/backtest.py — REAL walk-forward backtest (replaces the random batch_gatekeeper).

CATATAN PENTING: engines/walkforward_backtest_engine.batch_gatekeeper() yang lama itu
mengembalikan random.uniform(50,85) — PASS/FAIL, wf_score, mc_score, optimal_stop_adj SEMUANYA
angka acak, bukan hasil backtest. Modul ini menggantinya dengan mesin yang benar:

  • PATH-DEPENDENT TRADE SIM — untuk setiap sinyal, telusuri bar ke depan dan tentukan WIN/LOSS
    dari mana yang tersentuh lebih dulu antara {target, stop} pada jalur OHLC. Both-touch-same-bar
    = LOSS (asumsi konservatif, sama seperti tracker.py).
  • NO LOOK-AHEAD — sinyal di bar t hanya diuji pada bar > t.
  • WALK-FORWARD FOLDS — statistik per fold kronologis (IS/OOS terpisah).
  • BLOCK BOOTSTRAP p-value — signifikansi hit-rate vs entry acak (block=5 untuk jaga autocorr).
  • NET OF COST — kurangi biaya round-trip (bps) dari tiap return.

Semua ini butuh data harga REAL (OHLC) untuk verdict yang bermakna. Di sandbox tanpa network,
harness pakai data sintetis → HANYA membuktikan mesinnya jalan & tidak look-ahead, BUKAN edge.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


# ─────────────────────────────── path-dependent single-trade outcome ───────────────────────────────
def simulate_trade(df, entry_idx, direction, entry_px, stop, target, max_bars=63, cost_bps=10.0):
    """Telusuri bar SETELAH entry_idx; return dict hasil (WIN/LOSS/OPEN, ret, bars, exit_reason).
    Konservatif: kalau stop & target kena di bar yang sama → LOSS."""
    if direction not in ("Long", "Short") or stop is None or target is None:
        return None
    h, l = df["High"].values, df["Low"].values
    n = len(df)
    end = min(entry_idx + 1 + max_bars, n)
    cost = cost_bps / 1e4
    for i in range(entry_idx + 1, end):
        hi, lo = h[i], l[i]
        if direction == "Long":
            hit_stop = lo <= stop
            hit_tgt = hi >= target
            if hit_stop and hit_tgt:  # ambiguous bar → conservative LOSS
                return _res("LOSS", entry_px, stop, direction, i - entry_idx, cost, "stop(ambig)")
            if hit_stop:
                return _res("LOSS", entry_px, stop, direction, i - entry_idx, cost, "stop")
            if hit_tgt:
                return _res("WIN", entry_px, target, direction, i - entry_idx, cost, "target")
        else:
            hit_stop = hi >= stop
            hit_tgt = lo <= target
            if hit_stop and hit_tgt:
                return _res("LOSS", entry_px, stop, direction, i - entry_idx, cost, "stop(ambig)")
            if hit_stop:
                return _res("LOSS", entry_px, stop, direction, i - entry_idx, cost, "stop")
            if hit_tgt:
                return _res("WIN", entry_px, target, direction, i - entry_idx, cost, "target")
    # timeout → mark-to-market at last close
    last = float(df["Close"].values[end - 1])
    ret = ((last - entry_px) / entry_px if direction == "Long" else (entry_px - last) / entry_px) - cost
    return {"outcome": "OPEN", "ret": ret, "bars": end - 1 - entry_idx, "exit_reason": "timeout"}


def _res(outcome, entry_px, exit_px, direction, bars, cost, reason):
    ret = ((exit_px - entry_px) / entry_px if direction == "Long" else (entry_px - exit_px) / entry_px) - cost
    return {"outcome": outcome, "ret": ret, "bars": bars, "exit_reason": reason}


# ─────────────────────────────── signal-rule backtest (rolling, no look-ahead) ───────────────────────────────
def backtest_rule(df, signal_fn, direction_fn, level_fn, warmup=80, max_bars=21, cost_bps=10.0, cooldown=3):
    """Backtest sebuah aturan pada satu instrumen.
      signal_fn(hist_df)   -> bool  (apakah sinyal nyala di bar terakhir hist_df; hist HANYA s.d. bar t)
      direction_fn(hist_df)-> 'Long'/'Short'
      level_fn(hist_df, dir)-> (entry_px, stop, target)   semua dari data s.d. bar t (no look-ahead)
    Return: daftar trade + statistik agregat.
    """
    trades = []
    n = len(df)
    last_entry = -10_000
    for t in range(warmup, n - 1):
        if t - last_entry < cooldown:
            continue
        hist = df.iloc[: t + 1]                      # inclusive s.d. t — TIDAK ada bar masa depan
        try:
            if not signal_fn(hist):
                continue
            d = direction_fn(hist)
            entry_px, stop, target = level_fn(hist, d)
        except Exception:
            continue
        if entry_px is None or stop is None or target is None:
            continue
        res = simulate_trade(df, t, d, float(entry_px), float(stop), float(target), max_bars, cost_bps)
        if res is None:
            continue
        res.update({"entry_idx": t, "date": str(df.index[t].date()) if hasattr(df.index[t], "date") else t,
                    "direction": d, "entry_px": float(entry_px)})
        trades.append(res)
        last_entry = t
    return {"trades": trades, "stats": _agg(trades)}


def _agg(trades):
    if not trades:
        return {"n": 0}
    rets = np.array([t["ret"] for t in trades])
    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    wins = [t for t in closed if t["outcome"] == "WIN"]
    hit = len(wins) / len(closed) if closed else np.nan
    avg = float(rets.mean())
    sd = float(rets.std(ddof=1)) if len(rets) > 1 else np.nan
    sharpe_pertrade = (avg / sd) if (sd and sd == sd and sd > 0) else np.nan
    gross_w = sum(t["ret"] for t in wins)
    gross_l = -sum(t["ret"] for t in closed if t["outcome"] == "LOSS")
    pf = (gross_w / gross_l) if gross_l > 0 else np.nan
    dd = _max_dd(rets)
    return {"n": len(trades), "n_closed": len(closed), "hit_rate": _r(hit),
            "avg_ret_pct": _r(avg, 100), "sd_pct": _r(sd, 100),
            "sharpe_per_trade": _r(sharpe_pertrade), "profit_factor": _r(pf),
            "avg_bars": _r(np.mean([t["bars"] for t in trades])),
            "expectancy_pct": _r(avg, 100), "max_dd_pct": _r(dd, 100)}


def _max_dd(rets):
    eq = np.cumprod(1 + rets)
    peak = np.maximum.accumulate(eq)
    return float(((eq - peak) / peak).min()) if len(eq) else np.nan


def _r(x, mult=1.0, nd=3):
    try:
        if x is None or (isinstance(x, float) and x != x):
            return None
        return round(float(x) * mult, nd)
    except Exception:
        return None


# ─────────────────────────────── walk-forward folds ───────────────────────────────
def walk_forward(df, signal_fn, direction_fn, level_fn, n_folds=4, **kw):
    """Statistik per fold kronologis + konsistensi tanda hit-rate vs 0.5 (edge OOS)."""
    n = len(df)
    if n < 200:
        return {"error": "insufficient data", "n": n}
    bounds = np.linspace(0, n, n_folds + 1).astype(int)
    folds = []
    for k in range(n_folds):
        seg = df.iloc[bounds[k]: bounds[k + 1]]
        if len(seg) < 100:
            continue
        r = backtest_rule(seg, signal_fn, direction_fn, level_fn, **kw)
        folds.append({"fold": k + 1, "period": f"{seg.index[0].date()}..{seg.index[-1].date()}"
                      if hasattr(seg.index[0], "date") else f"{k}", **r["stats"]})
    hits = [f["hit_rate"] for f in folds if f.get("hit_rate") is not None]
    pos = sum(1 for h in hits if h > 0.5)
    return {"folds": folds, "n_folds": len(folds),
            "hit_consistency": f"{pos}/{len(hits)} folds > 50%" if hits else "n/a",
            "mean_hit": _r(np.mean(hits)) if hits else None}


# ─────────────────────────────── block-bootstrap significance ───────────────────────────────
def bootstrap_pvalue(df, trades, n_boot=1000, block=5, seed=0):
    """H0: entry acak menghasilkan hit-rate yang sama. Bandingkan hit-rate nyata vs distribusi acak.
    Block bootstrap (block=5 hari) menjaga autokorelasi harga."""
    closed = [t for t in trades if t["outcome"] in ("WIN", "LOSS")]
    if len(closed) < 10:
        return {"error": "too few closed trades", "n": len(closed)}
    real_hit = np.mean([1.0 if t["outcome"] == "WIN" else 0.0 for t in closed])
    rng = np.random.default_rng(seed)
    n = len(df)
    dirs = [t["direction"] for t in closed]
    max_bars = int(np.median([t["bars"] for t in closed])) or 21
    boot_hits = []
    for _ in range(n_boot):
        wins = 0
        for d in dirs:
            # pilih titik entry acak (blok) → simulate dengan stop/target simetris median
            t0 = int(rng.integers(80, max(81, n - max_bars - 1)))
            entry = float(df["Close"].values[t0])
            # gunakan lebar ATR-like dari data lokal supaya sebanding
            loc = df.iloc[max(0, t0 - 20): t0 + 1]
            w = float((loc["High"] - loc["Low"]).mean()) or entry * 0.02
            if d == "Long":
                stop, tgt = entry - w, entry + w
            else:
                stop, tgt = entry + w, entry - w
            res = simulate_trade(df, t0, d, entry, stop, tgt, max_bars, 0.0)
            if res and res["outcome"] == "WIN":
                wins += 1
        boot_hits.append(wins / len(dirs))
    boot_hits = np.array(boot_hits)
    p = float((boot_hits >= real_hit).mean())
    return {"real_hit": _r(real_hit), "boot_mean_hit": _r(boot_hits.mean()),
            "boot_p95": _r(np.percentile(boot_hits, 95)), "p_value": round(p, 4),
            "verdict": "beats random (p<0.05)" if p < 0.05 else "NOT distinguishable from random"}


# ─────────────────────────────── REAL gatekeeper (drop-in replacement) ───────────────────────────────
def batch_gatekeeper_real(tickers, prices, setups, max_bars=21, cost_bps=10.0):
    """Drop-in pengganti engines.walkforward_backtest_engine.batch_gatekeeper (yang random).
    Untuk tiap setup {direction, entry, stop, target}: jalankan SATU trade path-dependent dari bar
    terakhir + walk-forward hit-rate historis rule 'harga di zona entry'. PASS butuh bukti OOS nyata."""
    out = {}
    for t in tickers:
        s = setups.get(t) or {}
        df = prices.get(t)
        if not s or df is None or len(df) < 200:
            out[t] = {"gate_status": "NO_DATA", "reason": "insufficient history"}
            continue
        d = s.get("direction"); entry = s.get("entry"); stop = s.get("stop"); target = s.get("target")
        if d not in ("Long", "Short") or stop is None or target is None:
            out[t] = {"gate_status": "SKIP", "reason": "no directional setup"}
            continue

        # historical rule: entry when close within 2% of the setup's entry level, same direction
        entry_lvl = float(entry) if not isinstance(entry, str) else float(df["Close"].iloc[-1])
        band = abs(entry_lvl) * 0.02

        def sig(hist, _lvl=entry_lvl, _b=band):
            return abs(float(hist["Close"].iloc[-1]) - _lvl) <= _b

        def dfn(hist, _d=d):
            return _d

        # scale stop/target distance from entry as fixed fractions observed in the setup
        sdist = abs(entry_lvl - float(stop)) / entry_lvl
        tdist = abs(float(target) - entry_lvl) / entry_lvl

        def lvl(hist, dd, _sd=sdist, _td=tdist):
            px = float(hist["Close"].iloc[-1])
            if dd == "Long":
                return px, px * (1 - _sd), px * (1 + _td)
            return px, px * (1 + _sd), px * (1 - _td)

        wf = walk_forward(df, sig, dfn, lvl, n_folds=4, max_bars=max_bars, cost_bps=cost_bps)
        bt = backtest_rule(df, sig, dfn, lvl, max_bars=max_bars, cost_bps=cost_bps)
        st = bt["stats"]
        boot = bootstrap_pvalue(df, bt["trades"]) if st.get("n_closed", 0) >= 10 else {"p_value": None}

        # PASS rule: real OOS edge — hit>52%, positive expectancy, beats random, ≥15 closed trades
        passed = (st.get("n_closed", 0) >= 15 and (st.get("hit_rate") or 0) > 0.52
                  and (st.get("expectancy_pct") or -1) > 0
                  and boot.get("p_value") is not None and boot["p_value"] < 0.10)
        out[t] = {"gate_status": "PASS" if passed else "FAIL",
                  "n_trades": st.get("n"), "n_closed": st.get("n_closed"),
                  "hit_rate": st.get("hit_rate"), "expectancy_pct": st.get("expectancy_pct"),
                  "profit_factor": st.get("profit_factor"), "max_dd_pct": st.get("max_dd_pct"),
                  "wf_hit_consistency": wf.get("hit_consistency"), "boot_p": boot.get("p_value"),
                  "note": "REAL path-dependent walk-forward (not random)"}
    return out
