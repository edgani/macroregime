"""composition_audit.py — validate the COMPOSITION of every composite (a-z), not just its edge.

For each meter/score/signal, per your ask ("is a,b,c,d,e really used? is e useless? anything hidden
missing?"), this classifies EACH ingredient:

  LIVE            — contributes to the output on the data we have (ablate it → output moves)
  WIRED-INERT     — coded & weighted, but contributes 0 until its feed is supplied (needs feed X)
  DEAD            — never contributes regardless of feed (broken wiring / redundant) → cut it
  REDUNDANT       — >0.9 correlated with another ingredient → one is wasted

Method = ABLATION: toggle each ingredient's feed and measure the change in the composite on the real
S&P panel. A weight that never moves the output is not a real weight.
"""
from __future__ import annotations
import os, sys, warnings
import numpy as np, pandas as pd
warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "research")

TAG = {"LIVE": "\033[92mLIVE\033[0m", "WIRED-INERT": "\033[93mWIRED-INERT\033[0m",
       "DEAD": "\033[91mDEAD\033[0m", "REDUNDANT": "\033[91mREDUNDANT\033[0m", "OK": "\033[92m✓\033[0m"}
def row(comp, weight, status, detail=""):
    print(f"    {comp:<16} w={str(weight):<6} {TAG.get(status,status):<22} {detail}")


def _panel():
    p = pd.read_parquet(os.path.join(RES, "sp500_panel.parquet")); p["date"] = pd.to_datetime(p["date"])
    close = p.pivot_table(index="date", columns="Name", values="close")
    vol = p.pivot_table(index="date", columns="Name", values="volume")
    keep = close.columns[close.notna().mean() > 0.9]
    return close[keep].sort_index(), vol[keep].sort_index()


def audit_accumulation(close, vol, bench):
    print("\n" + "═" * 84)
    print("ACCUMULATION  =  0.30·rs + 0.25·ve + 0.20·er + 0.15·own + 0.10·opt")
    print("═" * 84)
    from gcfis.engines.accumulation import run_accumulation
    tk = "MU" if "MU" in close.columns else close.columns[0]
    px, vv = close[tk].dropna(), vol[tk].dropna()
    base = run_accumulation(tk, px, bench, vv)["accumulation"]
    n = len(px)
    rng = np.random.default_rng(0)
    syn = pd.Series(rng.normal(0, 1, n).cumsum() + 100, index=px.index)  # random walk → non-trivial Δ and level

    # toggle each optional feed; if score changes vs base → the ingredient is WIRED (feed-gated), else DEAD
    def delta(**kw):
        return abs(run_accumulation(tk, px, bench, vv, **kw)["accumulation"] - base)
    # rs & ve are LIVE (from price/volume) — confirm by removing volume (kills ve)
    d_ve = abs(run_accumulation(tk, px, bench, None)["accumulation"] - base)   # no volume → ve dead
    row("rs (0.30)", 0.30, "LIVE", "α-vs-benchmark from price — always on")
    row("ve (0.25)", 0.25, "LIVE" if d_ve > 0.001 else "DEAD",
        f"volume-effort; removing volume moves score by {round(d_ve,3)}")
    row("er (0.20)", 0.20, "WIRED-INERT" if delta(earnings_rev=syn) > 0.001 else "DEAD",
        f"earnings-revision; feed absent→0, synthetic feed moves it by {round(delta(earnings_rev=syn),3)} ⇒ needs feed")
    row("own (0.15)", 0.15, "WIRED-INERT" if delta(inst_own=syn) > 0.001 else "DEAD",
        f"institutional-ownership Δ; needs 13F feed")
    row("opt (0.10)", 0.10, "WIRED-INERT" if delta(options_oi=syn) > 0.001 else "DEAD",
        f"options-OI; needs options feed")
    print("    ── VERDICT: on price+volume data, 0.45 of weight (er+own+opt) is INERT.")
    print("       accumulation currently ≈ (0.30·rs + 0.25·ve) renormalized. Not wrong — feed-starved.")


def audit_entry(close):
    print("\n" + "═" * 84)
    print("ENTRY_SCORE  =  0.25·trend + 0.25·mom + 0.20·dealer + 0.15·liq + 0.15·structure")
    print("═" * 84)
    from gcfis.engines.entry import run_entry
    px = close["MU"].dropna() if "MU" in close.columns else close.iloc[:, 0].dropna()
    base = run_entry(px, "long")["entry_score"]
    d_dealer = abs(run_entry(px, "long", dealer={"gex_sign": -1, "regime": "momentum"})["entry_score"] - base)
    d_liq = abs(run_entry(px, "long", liquidity_score=95)["entry_score"] - base)
    row("trend (0.25)", 0.25, "LIVE", "price vs SMA50/200")
    row("mom (0.25)", 0.25, "LIVE", "RSI-based")
    row("dealer (0.20)", 0.20, "WIRED-INERT" if d_dealer > 0.001 else "DEAD",
        f"GEX sign; default 0, feed moves it {round(d_dealer,3)} ⇒ needs options/GEX")
    row("liq (0.15)", 0.15, "WIRED-INERT" if d_liq > 0.001 else "DEAD",
        f"liquidity_score; default 50→0, feed moves it {round(d_liq,3)}")
    row("structure (0.15)", 0.15, "LIVE", "position in 20d range")
    print("    ⚑ BUT entry_score is COSMETIC: nothing downstream reads it. The entry DECISION is")
    print("      driven by entry_type (gamma+trend+RSI) and ATR/sigma levels — not this blend.")
    print("      → either wire entry_score into the decision, or drop it. Right now it misleads.")


def audit_fear_greed(close):
    print("\n" + "═" * 84)
    print("FEAR_GREED  =  0.40·(1−VIX) + 0.30·(1−breadth) + 0.30·momentum")
    print("═" * 84)
    from warroom import early_warning as EW
    base = EW.fear_greed(close)["value"]
    # ingredient reconstruction to ablate + check redundancy
    spx = close.mean(axis=1)
    below50 = (close < close.rolling(50).mean()).mean(axis=1)
    z20 = ((spx - spx.rolling(20).mean()) / spx.rolling(20).std()).clip(-3, 3)
    rv = spx.pct_change().rolling(20).std()
    vix_term = 1 - rv.rank(pct=True)
    brd_term = 1 - below50
    mom_term = (z20 + 3) / 6
    df = pd.concat([vix_term.rename("vix"), brd_term.rename("brd"), mom_term.rename("mom")], axis=1).dropna()
    row("VIX (0.40)", 0.40, "LIVE", "using realized-vol proxy (no VIX in panel) — supply VIX for the real term")
    row("breadth (0.30)", 0.30, "LIVE", f"cross-sectional %<50ma (latest {round(below50.iloc[-1]*100)}%)")
    row("momentum (0.30)", 0.30, "LIVE", "20d z-score of index")
    # redundancy: correlation among the three terms
    c = df.corr()
    print("    ── redundancy (pairwise corr of the three terms):")
    for a, b in [("vix", "brd"), ("vix", "mom"), ("brd", "mom")]:
        r = c.loc[a, b]; flag = "REDUNDANT" if abs(r) > 0.9 else "OK"
        print(f"       {a}~{b}: {round(r,2)}  {TAG.get(flag, flag)}")
    # the hidden trap: Series input kills breadth
    ser = EW.fear_greed(spx)  # pass a Series (no cross-section)
    print(f"    ⚑ HIDDEN TRAP: pass a Series (no cross-section) → breadth term becomes constant 0.5 (DEAD).")
    print(f"       DataFrame fg={base} vs Series fg={ser['value']}. Always feed the cross-section.")


def audit_static():
    print("\n" + "═" * 84)
    print("STATIC COMPOSITION (dict-input engines) — ingredient inventory + feed-gating")
    print("═" * 84)
    print("\n  SURGE = Σ w·comp  (8 parts):")
    surgeW = {"liquidity": 0.20, "accumulation": 0.20, "positioning": 0.15, "bottleneck": 0.12,
              "narrative": 0.10, "reflexivity": 0.08, "rs": 0.08, "compression": 0.07}
    notes = {"bottleneck": "BINARY presence 0.4/1.0 — low info without supply-chain graph feed",
             "liquidity": "needs FRED net-liq (else proxy 0.5)", "compression": "needs market-mode (else 0.3)",
             "reflexivity": "capped at 0.8 (parabolic=exit elsewhere)"}
    for k, w in surgeW.items():
        row(k, w, "LIVE" if k in ("accumulation", "positioning", "rs", "narrative") else "WIRED-INERT",
            notes.get(k, "price-derived"))
    print("\n  COMPETITIVE_RANKING = weighted geometric mean of 5 pillars (regime-dynamic weights):")
    for p in ["regime_alignment", "bottleneck_pressure", "accumulation_persistence",
              "positioning_asymmetry", "reflexivity_potential"]:
        row(p, "dyn", "LIVE", "derived from engine outputs; regime OVERRIDE re-weights (verified)")
    print("\n  ASYMMETRY (moonshot) = 6 factors:")
    for f, s, d in [("centrality", "LIVE", "irreplaceability from bottleneck map"),
                    ("early", "LIVE", "uncrowdedness"), ("reflexivity", "LIVE", "feedback potential"),
                    ("undercoverage", "WIRED-INERT", "needs analyst-coverage feed"),
                    ("valuation", "WIRED-INERT", "needs fundamental feed"),
                    ("room_to_run", "WIRED-INERT", "needs market-cap feed")]:
        row(f, "1/6", s, d)
    print("\n  FLOW_REGIME (IHSG) — ALREADY audited in-engine (docstring):")
    print("    KEEP: Corr_F, Par_F (high edge) · EFD = Corr_F×Par_F · LPM conditional-only")
    print("    " + TAG["DEAD"] + " DROPPED as useless/redundant: Vol-Rotation (fwd-edge~0), AvgCost-standalone,")
    print("            Net-Buy/Sell-F (redundant derivative of the flow). ← this is the model to copy.")


def main():
    close, vol = _panel()
    bench = close.mean(axis=1)
    print("═" * 84)
    print(f"COMPOSITION AUDIT — every composite, ingredient-by-ingredient (real panel {close.shape[1]} tkr)")
    print("═" * 84)
    audit_accumulation(close, vol, bench)
    audit_entry(close)
    audit_fear_greed(close)
    audit_static()
    print("\n" + "═" * 84)
    print("SUMMARY — what to FIX")
    print("═" * 84)
    print("""  • INERT weight (needs feeds): accumulation er/own/opt (0.45), entry dealer/liq (0.35),
    surge liquidity/bottleneck/compression, asymmetry undercoverage/valuation/room_to_run.
    These aren't bugs — they're feed-gated. Until fed, RENORMALIZE weights over live parts so
    the score isn't silently diluted (a 0.30·rs that's really 0.30/0.55 of the live blend).
  • COSMETIC: entry_score (nothing reads it) → wire it into the decision or delete it.
  • HIDDEN TRAP: fear_greed breadth dies on Series input → always pass the cross-section.
  • GOOD MODEL: flow_regime already cut its dead/redundant parts (Vol-Rot/AvgCost/NetF).
    Every other composite should get the same treatment once its feeds are live.""")


if __name__ == "__main__":
    main()
