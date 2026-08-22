"""alpha_discovery_test.py — THE Alpha Discovery Test (docs Phase 11 ⭐).

Not "did MU go up 20%". The real test: run the discovery engine AS OF a past date using ONLY
data available then (no look-ahead), rank the whole universe, and check whether the names that
WENT ON to be the biggest winners were ranked TOP — i.e. did we find NVDA-type moves early.

Discovery score = rank-blend of validated signals:
  • RS_252 (relative strength / leadership)   • bandarmetrics markup-readiness (IC 0.17, perm 0.025)
Both computed point-in-time. Winner = top forward-return from the as-of date (defined by the FUTURE,
so being top-ranked at T with data≤T is a genuine early call).
"""
from __future__ import annotations
import os, sys, warnings
import numpy as np, pandas as pd
from scipy import stats
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research")


def _panel():
    p = pd.read_parquet(os.path.join(RES, "sp500_panel.parquet")); p["date"] = pd.to_datetime(p["date"])
    piv = lambda c: p.pivot_table(index="date", columns="Name", values=c)
    close, vol, hi, lo, op = piv("close"), piv("volume"), piv("high"), piv("low"), piv("open")
    keep = close.columns[close.notna().mean() > 0.9]
    return (close[keep].sort_index(), vol[keep].sort_index(), hi[keep].sort_index(),
            lo[keep].sort_index(), op[keep].sort_index())


def discovery_score(close, vol, hi, lo, op, asof, universe):
    """Point-in-time discovery score for every ticker using data up to `asof` only."""
    from engines import bandarmetrics_engine as BM
    c = close.loc[:asof]
    rs = (c.iloc[-1] / c.iloc[-252] - 1) if len(c) > 252 else (c.iloc[-1] / c.iloc[0] - 1)
    markup = {}
    for t in universe:
        sub = pd.DataFrame({"Open": op[t].loc[:asof], "High": hi[t].loc[:asof], "Low": lo[t].loc[:asof],
                            "Close": close[t].loc[:asof], "Volume": vol[t].loc[:asof]}).dropna()
        if len(sub) < 150:
            continue
        try:
            r = BM.compute(sub); mr = r.get("markup_readiness")
            if isinstance(mr, dict):
                mr = mr.get("readiness")
            if mr is not None:
                markup[t] = float(mr)
        except Exception:
            pass
    df = pd.DataFrame({"rs": rs, "markup": pd.Series(markup)}).dropna()
    df["score"] = 0.5 * df["rs"].rank(pct=True) + 0.5 * df["markup"].rank(pct=True)
    return df.sort_values("score", ascending=False)


def run_asof(close, vol, hi, lo, op, asof, fwd_days=504):
    universe = [t for t in close.columns if close[t].loc[:asof].notna().sum() > 252]
    disc = discovery_score(close, vol, hi, lo, op, asof, universe)
    # forward return from asof (the future — defines the winners)
    fut = close.loc[asof:]
    horizon = min(fwd_days, len(fut) - 1)
    fwd = (fut.iloc[horizon] / fut.iloc[0] - 1).reindex(disc.index)
    disc = disc.assign(fwd=fwd).dropna(subset=["fwd"])
    n = len(disc)
    top_decile = disc.head(max(1, n // 10))
    winners = disc.sort_values("fwd", ascending=False).head(max(1, n // 5)).index  # top-quintile future
    # metrics
    hit = top_decile.index.isin(winners).mean()                      # precision: top-decile that became winners
    recall = disc.loc[list(winners)].pipe(lambda d: d.index.isin(top_decile.index)).mean()
    lift = hit / (len(winners) / n)                                  # vs base rate
    td_fwd = top_decile["fwd"].mean(); uni_fwd = disc["fwd"].mean()
    ic, _ = stats.spearmanr(disc["score"], disc["fwd"])
    print(f"\n── AS OF {pd.Timestamp(asof).date()}  (forward {horizon}d, {n} names) ──")
    print(f"   discovery-score vs forward-return: rank-IC = {ic:+.3f}")
    print(f"   top-decile precision (became top-quintile winner): {hit:.0%}  (base 20%, LIFT {lift:.2f}x)")
    print(f"   top-decile forward return: {td_fwd*100:+.1f}%   vs universe {uni_fwd*100:+.1f}%")
    # where did the famous names rank?
    for name in ["NVDA", "AVGO", "MU", "NFLX", "AMD"]:
        if name in disc.index:
            pct = (disc["score"] >= disc.loc[name, "score"]).mean()
            print(f"   {name}: discovery percentile {(1-pct)*100:4.0f}th  → forward {disc.loc[name,'fwd']*100:+.0f}%  "
                  f"{'★ top-decile' if pct <= 0.1 else '(top-'+str(int(np.ceil(pct*100)))+'%)'}")
    return {"asof": str(pd.Timestamp(asof).date()), "ic": ic, "precision": hit, "lift": lift,
            "td_fwd": td_fwd, "uni_fwd": uni_fwd}


def main():
    close, vol, hi, lo, op = _panel()
    print("═" * 80)
    print("ALPHA DISCOVERY TEST — does the engine surface eventual winners EARLY? (no look-ahead)")
    print(f"panel {close.shape[1]} tkr, {close.index.min().date()}→{close.index.max().date()}")
    print("═" * 80)
    res = []
    for asof in ["2014-06-30", "2015-06-30", "2016-06-30"]:
        res.append(run_asof(close, vol, hi, lo, op, pd.Timestamp(asof)))
    print("\n" + "═" * 80)
    print("VERDICT")
    print("═" * 80)
    avg_lift = np.mean([r["lift"] for r in res]); avg_ic = np.mean([r["ic"] for r in res])
    edge = avg_lift > 1.2 and avg_ic > 0.05
    print(f"  avg rank-IC={avg_ic:+.3f} | avg top-decile LIFT={avg_lift:.2f}x vs base rate")
    print(f"  → the discovery engine {'HAS predictive lift toward the eventual winners' if edge else 'does NOT reliably rank winners early'}")
    print("""  HONEST: this is a survivor-biased S&P panel (winners were destined to stay in the index), and
  discovery = RS + markup-readiness only. It shows whether the ranking tilts toward future winners —
  NOT a claim that it prints NVDA every time. Full alpha (bottleneck/TAM/asymmetry) needs fundamental
  + cross-market feeds; this validates the price/volume half on real history.""")


if __name__ == "__main__":
    main()
