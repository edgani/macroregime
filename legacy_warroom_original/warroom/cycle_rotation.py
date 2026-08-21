"""warroom/cycle_rotation.py — UNIFIED cross-asset rotation engine.

Rotation is NOT a crypto-only thing. It is one mechanic — leadership moving along a risk/cycle
spectrum as the liquidity + business cycle turns — and it shows up in EVERY asset class. This engine
runs the same relative-strength race across seven axes and then fuses them into a single risk compass:

  1. Crypto risk-curve   stablecoin -> BTC -> ETH -> large alts -> small alts   (+ AHR999 cycle gauge)
  2. US sector clock      early(XLY/XLF/XLI/XLB) -> mid(XLK/XLC) -> late(XLE/XLP) -> recession(XLU/XLV)
  3. US factors           small/value/junk (risk-on) <-> large/quality/low-vol (risk-off)
  4. FX risk-on/off       commodity/EM FX (AUD) <-> havens (JPY/USD);  AUDJPY = the risk barometer
  5. Commodity complex    copper/oil (reflation) <-> gold/silver (fear);  copper-gold + gold-silver ratios
  6. DM -> EM             EM (EEM/country ETFs) <-> DM (SPY/EFA), driven by USD;  the global risk-curve
  7. IHSG intra-market    high-beta (coal/metals/small) <-> defensive (banks);  stock-to-stock rotation

The UNIFYING signal: when risk rotates DOWN the curve in all of them at once (alts heating, EM>DM,
high-beta FX>havens, copper>gold, small>large, IHSG cyclicals>banks) that is a coherent risk-ON
regime — the generational-wealth window. When it rotates UP (flight to BTC/USD/gold/quality/large/
banks) that is risk-OFF. The edge is in the CONFLUENCE: how many axes agree on the direction.

All thresholds/weights are unvalidated priors. AHR999 here is computed from price (200d geometric-mean
cost x log-regression growth); on full-history BTC it approximates the published index. MVRV / BTC.D /
NUPL need an on-chain feed (hooks below) and stay dormant until feeds.onchain is populated.
"""
from __future__ import annotations
import numpy as np, pandas as pd


# ───────────────────────────── relative-strength race (RRG core) ─────────────────────────────
def _state(a, b, n=50, mom_lb=10):
    d = pd.concat([a.rename("a"), b.rename("b")], axis=1).dropna()
    if len(d) < n + mom_lb + 2:
        return None
    rs = d["a"] / d["b"]
    base = rs.rolling(n).mean()
    if base.iloc[-1] == 0 or np.isnan(base.iloc[-1]):
        return None
    ratio = float(rs.iloc[-1] / base.iloc[-1] - 1)
    mom = float(rs.iloc[-1] / rs.iloc[-mom_lb - 1] - 1)
    q = "leading" if (ratio >= 0 and mom >= 0) else "weakening" if (ratio >= 0 and mom < 0) else "lagging" if (ratio < 0 and mom < 0) else "improving"
    return {"rs": round(ratio * 100, 2), "mom": round(mom * 100, 2), "quadrant": q}


def _race(allpx, members, bench, n=50, mom_lb=10):
    b = allpx.get(bench)
    if b is None:
        return []
    bc = b["Close"]
    out = []
    for tkr, name in members.items():
        df = allpx.get(tkr)
        if df is None or tkr == bench:
            continue
        st = _state(df["Close"], bc, n, mom_lb)
        if st:
            out.append({"ticker": tkr, "name": name, **st})
    return out


def _basket(allpx, tickers):
    """Equal-weight normalized basket close series from available members."""
    series = []
    for t in tickers:
        df = allpx.get(t)
        if df is not None and len(df) > 60:
            c = df["Close"].dropna()
            series.append(c / c.iloc[0])
    if not series:
        return None
    d = pd.concat(series, axis=1).dropna()
    return d.mean(axis=1) if len(d) else None


def _ratio_trend(allpx, num, den, n=50, mom_lb=10):
    a, b = allpx.get(num), allpx.get(den)
    if a is None or b is None:
        return None
    return _state(a["Close"], b["Close"], n, mom_lb)


def _synth_pair(allpx, t1, t2):
    """Synthetic cross series t1*t2 (e.g. AUDUSD*USDJPY = AUDJPY)."""
    a, b = allpx.get(t1), allpx.get(t2)
    if a is None or b is None:
        return None
    d = pd.concat([a["Close"].rename("a"), b["Close"].rename("b")], axis=1).dropna()
    return (d["a"] * d["b"]) if len(d) > 60 else None


def _trend(series, n=50, mom_lb=10):
    if series is None or len(series) < n + mom_lb + 2:
        return None
    base = series.rolling(n).mean()
    ratio = float(series.iloc[-1] / base.iloc[-1] - 1)
    mom = float(series.iloc[-1] / series.iloc[-mom_lb - 1] - 1)
    return {"rs": round(ratio * 100, 2), "mom": round(mom * 100, 2),
            "dir": "up" if mom > 0 else "down"}


# ───────────────────────────── AHR999 (price-derivable crypto cycle gauge) ─────────────────────────────
def ahr999(btc_close):
    c = btc_close.dropna()
    if len(c) < 220:
        return None
    cost200 = float(np.exp(np.log(c.tail(200)).mean()))         # 200d DCA cost = geometric mean
    y = np.log(c.values); lx = np.log(np.arange(len(c)) + 1.0)  # log-regression growth path (proxy: age=index)
    b, a = np.polyfit(lx, y, 1)
    growth = float(np.exp(a + b * lx[-1]))
    price = float(c.iloc[-1])
    val = (price / cost200) * (price / growth)
    zone = "deep-value (<0.45) — aggressive accumulation" if val < 0.45 else \
           "DCA band (0.45–1.2)" if val < 1.2 else "caution (>1.2) — reduce buying"
    return {"value": round(val, 3), "zone": zone, "cost200": round(cost200, 0),
            "growth_est": round(growth, 0), "price": round(price, 0)}


# ───────────────────────────── the seven axes ─────────────────────────────
EARLY_MID = {"XLY", "XLF", "XLI", "XLB", "XLK", "XLC"}
DEFENSIVE = {"XLU", "XLP", "XLV"}
SECTORS = {"XLK": "Tech", "XLE": "Energy", "XLF": "Financials", "XLV": "Health", "XLI": "Industrials",
           "XLY": "Discretionary", "XLP": "Staples", "XLU": "Utilities", "XLB": "Materials",
           "XLRE": "Real estate", "XLC": "Communications"}


def _vote(score):
    return 1 if score > 0.15 else -1 if score < -0.15 else 0


def axis_crypto(allpx):
    cr = {"ETH-USD": "Ethereum", "SOL-USD": "Solana", "BNB-USD": "BNB"}
    members = _race(allpx, cr, "BTC-USD", n=40, mom_lb=7)
    # altseason breadth on our crypto universe: % of alts outperforming BTC over 90d
    btc = allpx.get("BTC-USD")
    breadth = None
    if btc is not None:
        bret = float(btc["Close"].iloc[-1] / btc["Close"].iloc[-90] - 1) if len(btc) > 90 else None
        alts = [t for t in ("ETH-USD", "SOL-USD", "BNB-USD") if allpx.get(t) is not None and len(allpx[t]) > 90]
        if bret is not None and alts:
            beat = sum(1 for t in alts if float(allpx[t]["Close"].iloc[-1] / allpx[t]["Close"].iloc[-90] - 1) > bret)
            breadth = round(100 * beat / len(alts), 0)
    ethbtc = _ratio_trend(allpx, "ETH-USD", "BTC-USD", n=40, mom_lb=7)
    ahr = ahr999(btc["Close"]) if btc is not None else None
    score = 0.0
    if breadth is not None:
        score += (breadth - 50) / 50.0
    if ethbtc:
        score += np.clip(ethbtc["mom"] / 10.0, -1, 1) * 0.5
    v = _vote(score)
    verdict = ("risk DOWN the curve — alts outperforming BTC (alt-season behaviour)" if v > 0
               else "flight UP to BTC — alts lagging, risk-off within crypto" if v < 0
               else "mixed — no clear crypto rotation")
    return {"name": "Crypto risk-curve", "verdict": verdict, "vote": v, "members": members,
            "breadth_pct": breadth, "eth_btc": ethbtc, "ahr999": ahr,
            "down_curve": "alts / ETH / small-caps", "up_curve": "BTC / stablecoins"}


def axis_sectors(allpx):
    members = _race(allpx, SECTORS, "SPY")
    em = [m for m in members if m["ticker"] in EARLY_MID and m["quadrant"] in ("leading", "improving")]
    df = [m for m in members if m["ticker"] in DEFENSIVE and m["quadrant"] in ("leading", "improving")]
    score = (len(em) - len(df)) / 3.0
    v = _vote(score)
    # crude cycle-phase read from which sectors lead
    lead = {m["ticker"] for m in members if m["quadrant"] == "leading"}
    if {"XLY", "XLF"} & lead:
        phase = "EARLY-CYCLE (discretionary/financials leading)"
    elif {"XLK", "XLC"} & lead:
        phase = "MID-CYCLE (tech/comms leading)"
    elif {"XLE", "XLP"} & lead:
        phase = "LATE-CYCLE (energy/staples leading)"
    elif {"XLU", "XLV"} & lead:
        phase = "RECESSION/DEFENSIVE (utilities/health leading)"
    else:
        phase = "transition (no clear sector leadership)"
    verdict = f"{phase} · cyclicals {'leading' if v > 0 else 'lagging' if v < 0 else 'mixed'} vs defensives"
    return {"name": "US sector clock", "verdict": verdict, "vote": v, "members": members, "phase": phase,
            "down_curve": "discretionary / financials / tech / materials", "up_curve": "utilities / staples / health"}


def axis_factors(allpx):
    small = _ratio_trend(allpx, "IWM", "SPY")          # small vs broad = breadth/risk appetite
    value = _ratio_trend(allpx, "IWD", "IWF")          # value vs growth
    momo = _ratio_trend(allpx, "MTUM", "SPY")
    score = 0.0
    if small:
        score += np.clip(small["mom"] / 8.0, -1, 1)
    rows = [{"pair": "IWM/SPY (small/broad)", **(small or {})}, {"pair": "IWD/IWF (value/growth)", **(value or {})},
            {"pair": "MTUM/SPY (momentum)", **(momo or {})}]
    v = _vote(score)
    verdict = ("broad risk-on — small-caps participating (risk down the curve)" if v > 0
               else "narrow/defensive — mega-cap & quality leading (risk up the curve)" if v < 0
               else "mixed factor leadership")
    return {"name": "US factors", "verdict": verdict, "vote": v, "rows": rows,
            "down_curve": "small-cap / value / junk", "up_curve": "large-cap / quality / low-vol"}


def axis_fx(allpx):
    audjpy = _trend(_synth_pair(allpx, "AUDUSD=X", "USDJPY=X"))   # AUD/JPY = classic risk barometer
    dxy = _trend(allpx.get("DX-Y.NYB", {}).get("Close") if allpx.get("DX-Y.NYB") is not None else None)
    score = 0.0
    if audjpy:
        score += np.clip(audjpy["mom"] / 5.0, -1, 1)
    if dxy:
        score -= np.clip(dxy["mom"] / 5.0, -1, 1) * 0.5            # strong USD = risk-off tilt
    v = _vote(score)
    verdict = ("risk-on FX — AUD/JPY rising, USD soft (capital out the risk curve)" if v > 0
               else "risk-off FX — havens (JPY/USD) bid" if v < 0 else "mixed FX risk signal")
    return {"name": "FX risk-on/off", "verdict": verdict, "vote": v, "aud_jpy": audjpy, "dxy": dxy,
            "down_curve": "AUD / NZD / commodity & EM FX", "up_curve": "USD / JPY / CHF (havens)"}


def axis_commodity(allpx):
    copper_gold = _ratio_trend(allpx, "CPER", "GLD")   # growth vs fear
    gold_silver = _ratio_trend(allpx, "GLD", "SLV")    # gold leading silver = fear within metals
    score = 0.0
    if copper_gold:
        score += np.clip(copper_gold["mom"] / 8.0, -1, 1)
    if gold_silver:
        score -= np.clip(gold_silver["mom"] / 8.0, -1, 1) * 0.6   # gold>silver = risk-off
    v = _vote(score)
    verdict = ("reflation/early-cycle — copper & cyclicals over gold (risk-on)" if v > 0
               else "fear/late-cycle — gold leading, copper & silver lagging (risk-off)" if v < 0
               else "mixed commodity complex")
    return {"name": "Commodity complex", "verdict": verdict, "vote": v,
            "copper_gold": copper_gold, "gold_silver": gold_silver,
            "down_curve": "copper / oil / silver (growth)", "up_curve": "gold (store of value)"}


def axis_dm_em(allpx):
    em_members = _race(allpx, {"EEM": "EM broad", "EWZ": "Brazil", "INDA": "India", "FXI": "China",
                               "EWY": "Korea", "EWT": "Taiwan", "EWW": "Mexico"}, "SPY")
    em_basket = _basket(allpx, ["EEM", "EWZ", "INDA", "FXI", "EWY", "EWT"])
    spy = allpx.get("SPY")
    em_vs_dm = _state(em_basket, spy["Close"]) if (em_basket is not None and spy is not None) else None
    dxy = _trend(allpx.get("DX-Y.NYB", {}).get("Close") if allpx.get("DX-Y.NYB") is not None else None)
    score = 0.0
    if em_vs_dm:
        score += np.clip(em_vs_dm["mom"] / 8.0, -1, 1)
    if dxy:
        score -= np.clip(dxy["mom"] / 6.0, -1, 1) * 0.5
    v = _vote(score)
    verdict = ("capital rotating DM → EM — EM outperforming US, USD soft (global risk-on)" if v > 0
               else "capital fleeing EM → DM — US/USD bid (global risk-off)" if v < 0 else "mixed DM/EM signal")
    return {"name": "DM → EM", "verdict": verdict, "vote": v, "members": em_members,
            "em_vs_dm": em_vs_dm, "dxy": dxy,
            "down_curve": "EM equities / EM FX (incl. IHSG)", "up_curve": "US / DM / USD"}


def axis_ihsg(allpx):
    bench = allpx.get("^JKSE")
    bench_series = bench["Close"] if bench is not None else _basket(allpx, [t for t in (
        "BBCA.JK", "BMRI.JK", "BBRI.JK", "ASII.JK", "TLKM.JK", "ADRO.JK", "ANTM.JK") if allpx.get(t) is not None])
    groups = {"Banks (defensive core)": ["BBCA.JK", "BMRI.JK", "BBRI.JK", "BBNI.JK"],
              "Coal/energy (high-beta)": ["ADRO.JK", "BUMI.JK", "HUMI.JK", "BREN.JK"],
              "Metals (high-beta)": ["ANTM.JK", "MDKA.JK", "AMMN.JK"]}
    rows = []
    grp_state = {}
    for g, tks in groups.items():
        bk = _basket(allpx, tks)
        st = _state(bk, bench_series) if (bk is not None and bench_series is not None) else None
        if st:
            rows.append({"group": g, **st})
            grp_state[g] = st
    hb = [grp_state[g]["mom"] for g in grp_state if "high-beta" in g]
    bank = grp_state.get("Banks (defensive core)", {}).get("mom", 0.0)
    score = 0.0
    if hb:
        score += np.clip((np.mean(hb) - bank) / 8.0, -1, 1)
    v = _vote(score)
    verdict = ("IHSG risk-on — coal/metals leading banks (cyclical rotation)" if v > 0
               else "IHSG risk-off — banks/defensives leading cyclicals" if v < 0 else "mixed IHSG rotation")
    return {"name": "IHSG intra-market", "verdict": verdict, "vote": v, "rows": rows,
            "down_curve": "coal / metals / small-caps", "up_curve": "big-cap banks"}


# ───────────────────────────── synthesis: the risk compass ─────────────────────────────
def compute(allpx):
    axes = [axis_crypto(allpx), axis_sectors(allpx), axis_factors(allpx), axis_fx(allpx),
            axis_commodity(allpx), axis_dm_em(allpx), axis_ihsg(allpx)]
    votes = [a["vote"] for a in axes]
    total = sum(votes)
    up = sum(1 for v in votes if v > 0)
    down = sum(1 for v in votes if v < 0)
    n = len(axes)
    if total >= 3 and up >= down:
        compass = "RISK-ON · DOWN the curve"
        meaning = "Capital is rotating into high-beta across asset classes — the generational-wealth window is forming. Lean into EM, alts, cyclicals, small-caps; this is where the catch-up moves live."
        col = "grn"
    elif total <= -3:
        compass = "RISK-OFF · UP the curve"
        meaning = "Flight to safety across the board — USD, gold, BTC, quality, large-cap, banks. Capital is leaving the risk curve. Defend, don't chase; wait for the rotation to turn back down."
        col = "red"
    else:
        compass = "MIXED / TRANSITIONING"
        meaning = "The axes disagree — rotation is not aligned. This is a transition zone: conviction is low because the asset classes are not confirming each other. Wait for confluence before sizing up."
        col = "amb"
    agree = [a["name"] for a in axes if a["vote"] == (1 if total >= 0 else -1) and a["vote"] != 0]
    disagree = [a["name"] for a in axes if a["vote"] == (-1 if total >= 0 else 1) and a["vote"] != 0]
    onchain_note = ("MVRV Z-Score / BTC.D / NUPL not shown — they need an on-chain feed (feeds.onchain). "
                    "AHR999 above is computed from price (proxy for the published log-regression index).")
    return {"compass": compass, "meaning": meaning, "color": col, "score": total,
            "up_axes": up, "down_axes": down, "n_axes": n, "axes": axes,
            "agree": agree, "disagree": disagree, "onchain_note": onchain_note}
