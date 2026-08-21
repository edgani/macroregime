"""
lineage_audit.py — proves DATA LINEAGE empirically, not by file existence.

Edward's #1 point: "keberadaan file tidak membuktikan data mengalir." Correct. A dashboard can render
a full crash meter while the feed behind it is dead and the number is a default. This script tests the
actual wiring by PERTURBING each feed and checking whether the downstream metric MOVES.

  RESPONDS  = feed A vs feed B produces different metric  → the link is genuinely wired.
  CONSTANT  = metric identical regardless of feed         → placeholder / default / broken lineage.

Then two robustness tests Edward flagged:
  FEED-DROP     — remove a feed entirely; does the system degrade gracefully or break?
  DECISION-STABILITY — perturb an input ±10%; does the posture flip? (flip on tiny change = fragile)

Run offline (constructs feed dicts, no live fetch needed): python lineage_audit.py
"""
from __future__ import annotations
import os, sys, warnings, numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from run import build_desk

RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research")


def _macro():
    mp = pd.read_parquet(os.path.join(RES, "macro_panel.parquet"))
    return mp


def _series(base=100.0, n=400, drift=0.0, vol=0.01, seed=0):
    rng = np.random.default_rng(seed)
    idx = pd.date_range("1993-01-01", periods=n, freq="MS")
    r = rng.normal(drift, vol, n)
    return pd.Series(base * np.exp(np.cumsum(r)), index=idx)


def _base_data(mp, fred):
    prices = {"SPY": mp["spx"].dropna(), "GLD": mp["gold"].dropna(),
              "USO": mp["oil"].dropna(), "UUP": mp["dxy"].dropna()}
    return {"prices": {"us": prices}, "bench": mp["spx"].dropna(), "markets": ["us"],
            "fred": fred, "proxies": {}, "treasury_liquidity": {"ok": False},
            "sources": {"us": "x"}, "bench_source": "x", "fred_source": "real" if fred else "none",
            "overall_source": "LIVE", "vix": None}


def _get(desk, path):
    cur = desk
    for k in path.split("."):
        cur = (cur or {}).get(k) if isinstance(cur, dict) else None
    return cur


def probe_lineage(mp):
    """Establish a FULL feed baseline, then swap ONE feed high vs low (others held) to isolate each link."""
    idx = _series().index
    baseline = {
        "DGS10": pd.Series(np.linspace(2.5, 3.5, 400), index=idx),
        "DGS2": pd.Series(np.linspace(2.0, 3.0, 400), index=idx),
        "BAMLH0A0HYM2": pd.Series(np.linspace(4.0, 5.0, 400), index=idx),
        "WALCL": _series(base=8e6, vol=0.005, seed=7),
        "T10YIE": pd.Series(np.linspace(0.02, 0.025, 400), index=idx),
        "M2SL": _series(base=2e7, vol=0.004, seed=8),
        "RRPONTSYD": _series(base=1e6, vol=0.02, seed=9),
    }
    rising = pd.Series(np.linspace(1.5, 6.5, 400), index=idx)
    falling = pd.Series(np.linspace(6.5, 1.5, 400), index=idx)
    wide = pd.Series(np.linspace(3.0, 13.0, 400), index=idx)
    tight = pd.Series(np.linspace(13.0, 3.0, 400), index=idx)
    grow = _series(base=4e6, drift=0.01, vol=0.005, seed=10)
    shrink = _series(base=9e6, drift=-0.01, vol=0.005, seed=11)

    probes = [
        ("DGS10", {"DGS10": falling}, {"DGS10": rising}),
        ("BAMLH0A0HYM2", {"BAMLH0A0HYM2": tight}, {"BAMLH0A0HYM2": wide}),
        ("WALCL", {"WALCL": shrink}, {"WALCL": grow}),
        ("T10YIE", {"T10YIE": pd.Series(np.full(400, 0.015), index=idx)}, {"T10YIE": pd.Series(np.linspace(0.02, 0.05, 400), index=idx)}),
    ]
    metrics = ["systemic.fragility", "systemic.shock_prob", "systemic.liquidity", "systemic.quad", "regime_tf.posture"]
    print("═══ LINEAGE PROBE — full feed baseline, perturb ONE feed (others held) ═══")
    print(f"{'feed':14s} {'metric':24s} {'low→high':>28s}  verdict")
    results = {}
    for fk, low_override, high_override in probes:
        dl = build_desk(_base_data(mp, {**baseline, **low_override}))
        dh = build_desk(_base_data(mp, {**baseline, **high_override}))
        for m in metrics:
            vlo, vhi = _get(dl, m), _get(dh, m)
            responds = str(vlo) != str(vhi)
            results[(fk, m)] = responds
            tag = "✅ WIRED" if responds else "· constant"
            print(f"{fk:14s} {m:24s} {str(vlo)[:13]:>13s} → {str(vhi)[:13]:<13s}  {tag}")
        print()
    wired = sum(results.values()); total = len(results)
    print(f"LINEAGE: {wired}/{total} feed→metric links respond (with a full baseline present).")
    print("Reading: shock_prob & fragility & liquidity are feed-driven; quad & posture are PRICE-driven")
    print("(the GIP engine derives growth/inflation from price momentum, not the macro feeds — by design,")
    print("but it means the 'macro quad' is mostly a price signal, not a macro-feed signal). Know this.")
    return results


def feed_drop(mp):
    """Drop all FRED; does it still run and what falls back to default?"""
    print("\n═══ FEED-DROP — remove ALL FRED, does it break or degrade gracefully? ═══")
    full = {"DGS10": _series(vol=0.03, seed=3), "BAMLH0A0HYM2": pd.Series(np.linspace(4, 8, 400), index=_series().index),
            "WALCL": _series(base=8e6, seed=4)}
    try:
        d_full = build_desk(_base_data(mp, full))
        d_none = build_desk(_base_data(mp, {}))
        print("  with feeds : quad=%s fragility=%s liquidity=%s" % (
            _get(d_full, "systemic.quad"), _get(d_full, "systemic.fragility"), _get(d_full, "systemic.liquidity")))
        print("  no feeds   : quad=%s fragility=%s liquidity=%s" % (
            _get(d_none, "systemic.quad"), _get(d_none, "systemic.fragility"), _get(d_none, "systemic.liquidity")))
        print("  → system runs without feeds (graceful). Note which fields fall to a reason-string / default above.")
    except Exception as e:
        print("  ✗ BREAKS without feeds:", repr(e))


def decision_stability(mp):
    """Perturb an input ±10%; does the posture/quad flip? (flip on tiny change = fragile)"""
    print("\n═══ DECISION-STABILITY — perturb 10Y ±10%, does the decision flip? ═══")
    base_rate = _series(base=3.0, vol=0.02, seed=5)
    outs = []
    for mult, lbl in [(0.9, "-10%"), (1.0, "base"), (1.1, "+10%")]:
        d = build_desk(_base_data(mp, {"DGS10": base_rate * mult}))
        outs.append((lbl, _get(d, "systemic.quad"), _get(d, "regime_tf.posture")))
    for lbl, q, p in outs:
        print(f"  {lbl:5s}: quad={q}  posture={str(p)[:34]}")
    quads = {q for _, q, _ in outs}; posts = {str(p) for _, _, p in outs}
    print(f"  → quad {'STABLE' if len(quads)==1 else 'FLIPS'} · posture {'STABLE' if len(posts)==1 else 'FLIPS'} under ±10%.")
    print("    (Flipping on a 10% wiggle = fragile; stable = robust. Real revisions are usually <10%.)")


if __name__ == "__main__":
    mp = _macro()
    probe_lineage(mp)
    feed_drop(mp)
    decision_stability(mp)
    print("\nThis is the EMPIRICAL lineage/robustness proof — reproducible: python lineage_audit.py")
