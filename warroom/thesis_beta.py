"""warroom/thesis_beta.py — Thesis-Beta / Propagation engine (from Edward's Beta-Propagation doc).

Top investors don't buy the theme — they buy the asset with the best beta/convexity TO the theme.
This measures, from REAL price returns, how much each supply-chain tier moves relative to the theme
LEADER: beta (leverage to the thesis), up- vs down-beta (convexity = asymmetry), and annualized vol
(fragility). High beta + positive convexity + contained vol = the asymmetric play; high beta + high
vol + negative convexity = the trap. No new data needed — uses the beta-play tiers already built.

HONEST: this is statistical beta on ~120d returns, NOT thesis-elasticity from fundamentals (that needs
EPS-sensitivity / revenue-exposure data we don't have). It answers "which name has most leverage to the
leader," not a DCF. Betas are unstable across regimes — recompute often, don't size on a single read.
"""
from __future__ import annotations
import numpy as np, pandas as pd


def _beta(t_ret, l_ret, win=120):
    j = pd.concat([t_ret.rename("t"), l_ret.rename("l")], axis=1).dropna().tail(win)
    if len(j) < 40 or j["l"].var() == 0:
        return None
    beta = float(j["t"].cov(j["l"]) / j["l"].var())
    up, dn = j[j["l"] > 0], j[j["l"] < 0]
    ub = float(up["t"].cov(up["l"]) / up["l"].var()) if len(up) > 10 and up["l"].var() > 0 else beta
    db = float(dn["t"].cov(dn["l"]) / dn["l"].var()) if len(dn) > 10 and dn["l"].var() > 0 else beta
    return {"beta": round(beta, 2), "up_beta": round(ub, 2), "down_beta": round(db, 2),
            "convexity": round(ub - db, 2)}


def compute(allpx, beta_plays):
    out = {}
    for theme, info in (beta_plays or {}).items():
        leader = info.get("leader")
        ldf = allpx.get(leader)
        if ldf is None:
            continue
        lret = ldf["Close"].pct_change().dropna()
        seen, members = set(), []
        for _tier, rows in (info.get("tiers") or {}).items():
            for r in rows:
                t = r.get("ticker")
                if not t or t == leader or t in seen:
                    continue
                seen.add(t)
                tdf = allpx.get(t)
                if tdf is None:
                    continue
                b = _beta(tdf["Close"].pct_change().dropna(), lret)
                if not b:
                    continue
                vol = float(tdf["Close"].pct_change().dropna().tail(120).std() * (252 ** 0.5))
                # asymmetry score: leverage to thesis, rewarded for convexity, penalized for fragility
                asym = round((b["beta"] * (1 + max(b["convexity"], -0.5))) / max(vol, 0.15), 2)
                members.append({"ticker": t, "role": r.get("role", ""), **b,
                                "ann_vol": round(vol, 2), "asym": asym, "verdict": r.get("verdict", "")})
        if members:
            members.sort(key=lambda x: -x["asym"])
            out[theme.split("(")[0].strip()] = {"leader": leader, "members": members[:8]}
    return out
