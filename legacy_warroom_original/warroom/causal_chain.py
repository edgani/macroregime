"""warroom/causal_chain.py — Causal-Chain + Kill-Switch engine (the Ant Markets way of thinking).

Two ideas the screenshot nails, operationalized:
  1. CAUSAL CHAIN — don't view an asset alone; view the network. Gold-bear = Energy↑ → inflation↑ →
     Fed higher-for-longer → DXY↑ → Gold↓, plus a second-order loop (equity stress → fund margin call →
     forced gold selling → Gold↓). Each link maps to an OBSERVABLE asset, and we check whether each link
     is currently CONFIRMING or NOT from live price momentum. A chain with most links confirming = thesis
     is playing out; links breaking = thesis weakening.
  2. KILL-SWITCH / REFUTATION — "I'm willing to switch sides when DXY peaks or XAU prints a bottom."
     Every chain carries explicit FLIP triggers (disconfirming evidence). We actively watch for them and
     flag when one fires — so the system hunts for what would BREAK the thesis, not just confirm it.

HONEST: the chains are a CURATED library (priors), and 'confirming/flip' come from simple price momentum,
not proven causality. It's a disciplined checklist for network-effect + invalidation thinking, not proof.
"""
from __future__ import annotations
import numpy as np, pandas as pd

# each link -> an observable asset + the direction the thesis NEEDS; flips -> disconfirming triggers
CHAINS = [
    {"id": "gold_bear", "name": "Gold bear — DXY / real-yield regime",
     "thesis": "Energy↑ → inflation↑ → Fed higher-for-longer → DXY↑ → Gold↓; + equities↓ → fund margin call → forced gold selling → Gold↓",
     "links": [{"label": "Energy ↑ (inflation impulse)", "a": "USO", "want": "up"},
               {"label": "DXY ↑ (dollar strong)", "a": "DX-Y.NYB", "want": "up"},
               {"label": "Equity stress (liquidation risk)", "a": "SPY", "want": "down"},
               {"label": "Gold ↓ (the payoff)", "a": "GLD", "want": "down"}],
     "flips": [{"label": "DXY peaks — momentum rolls over", "a": "DX-Y.NYB", "sig": "roll_down"},
               {"label": "XAU prints a bottom — gold momentum turns up", "a": "GLD", "sig": "turn_up"}]},
    {"id": "gold_bull", "name": "Gold bull — debasement / easing regime",
     "thesis": "DXY↓ + real yields↓ (Fed easing / fiscal debasement) → Gold↑; central-bank bid underpins",
     "links": [{"label": "DXY ↓ (dollar soft)", "a": "DX-Y.NYB", "want": "down"},
               {"label": "Real-yield proxy ↓ (TLT ↑)", "a": "TLT", "want": "up"},
               {"label": "Gold ↑ (the payoff)", "a": "GLD", "want": "up"}],
     "flips": [{"label": "DXY breaks higher again", "a": "DX-Y.NYB", "sig": "turn_up"},
               {"label": "Gold momentum rolls over", "a": "GLD", "sig": "roll_down"}]},
    {"id": "risk_off", "name": "Risk-off cascade — credit → equity → flight to safety",
     "thesis": "Credit stress (HYG↓) → equities↓ → capital flees to USD & Treasuries; high-beta & EM hit hardest",
     "links": [{"label": "Credit weak (HYG ↓)", "a": "HYG", "want": "down"},
               {"label": "Equities ↓", "a": "SPY", "want": "down"},
               {"label": "Treasuries bid (TLT ↑)", "a": "TLT", "want": "up"},
               {"label": "EM underperforms (EEM ↓)", "a": "EEM", "want": "down"}],
     "flips": [{"label": "Credit repairs — HYG turns up", "a": "HYG", "sig": "turn_up"},
               {"label": "Equities print a bottom", "a": "SPY", "sig": "turn_up"}]},
    {"id": "reflation", "name": "Reflation (Q3→Q2) — growth impulse rotates to cyclicals",
     "thesis": "Growth re-accelerates → copper & energy lead gold → cyclicals/EM outperform defensives → reflation trade",
     "links": [{"label": "Copper ↑ (growth demand)", "a": "CPER", "want": "up"},
               {"label": "Energy ↑", "a": "XLE", "want": "up"},
               {"label": "EM outperforms (EEM ↑)", "a": "EEM", "want": "up"},
               {"label": "Defensives lag (XLU ↓ vs mkt)", "a": "XLU", "want": "down"}],
     "flips": [{"label": "Copper rolls over — growth fades", "a": "CPER", "sig": "roll_down"},
               {"label": "Defensives (XLU) bid — risk-off returns", "a": "XLU", "sig": "turn_up"}]},
    {"id": "ai_power", "name": "AI power bottleneck — compute → grid → copper",
     "thesis": "AI capex↑ → datacenter power demand↑ → grid/transformer bottleneck → utilities & copper re-rate",
     "links": [{"label": "AI leader intact (NVDA ↑)", "a": "NVDA", "want": "up"},
               {"label": "Power/utilities bid (XLU ↑)", "a": "XLU", "want": "up"},
               {"label": "Copper ↑ (electrification)", "a": "CPER", "want": "up"}],
     "flips": [{"label": "AI leader rolls over (NVDA ↓)", "a": "NVDA", "sig": "roll_down"},
               {"label": "Copper fails to confirm", "a": "CPER", "sig": "roll_down"}]},
]


def _state(close, lb=20):
    c = close.dropna()
    if len(c) < lb + 5:
        return None
    mom = float(c.iloc[-1] / c.iloc[-lb] - 1)
    prev = float(c.iloc[-lb] / c.iloc[-min(2 * lb, len(c) - 1)] - 1)
    return {"mom": mom, "roll_down": mom < prev and mom < 0.01, "turn_up": mom > prev and mom > -0.01}


def _link_status(allpx, link):
    df = allpx.get(link["a"])
    if df is None:
        return {"label": link["label"], "state": "no data", "ok": None}
    s = _state(df["Close"])
    if not s:
        return {"label": link["label"], "state": "no data", "ok": None}
    up = s["mom"] > 0.005
    dn = s["mom"] < -0.005
    ok = (up if link["want"] == "up" else dn)
    return {"label": link["label"], "state": f"{s['mom']*100:+.1f}% / 20d", "ok": bool(ok)}


def _flip_status(allpx, flip):
    df = allpx.get(flip["a"])
    if df is None:
        return {"label": flip["label"], "fired": None}
    s = _state(df["Close"])
    if not s:
        return {"label": flip["label"], "fired": None}
    fired = s["roll_down"] if flip["sig"] == "roll_down" else s["turn_up"]
    return {"label": flip["label"], "fired": bool(fired)}


def compute(allpx):
    out = []
    for ch in CHAINS:
        links = [_link_status(allpx, l) for l in ch["links"]]
        flips = [_flip_status(allpx, f) for f in ch["flips"]]
        confirmed = [l for l in links if l["ok"] is True]
        graded = [l for l in links if l["ok"] is not None]
        integrity = round(100 * len(confirmed) / len(graded)) if graded else None
        fired = [f for f in flips if f["fired"]]
        if integrity is None:
            verdict, col = "no data", "gry"
        elif fired:
            verdict, col = f"KILL-SWITCH FIRING — {fired[0]['label']}", "red"
        elif integrity >= 75:
            verdict, col = "chain intact — thesis confirming", "grn"
        elif integrity >= 50:
            verdict, col = "chain partial — mixed confirmation", "amb"
        else:
            verdict, col = "chain breaking — thesis weakening", "red"
        out.append({"id": ch["id"], "name": ch["name"], "thesis": ch["thesis"], "links": links,
                    "flips": flips, "integrity": integrity, "verdict": verdict, "color": col,
                    "fired": [f["label"] for f in fired]})
    return out
