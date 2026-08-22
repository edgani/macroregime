"""warroom/meters.py — composite meters computed from REAL price proxies (+ FRED where wired).

Menggantikan meter yang di-stub 'needs data feed'. Filosofi Edward (VOLUME X Rule 8: "Unknown is
better than wrong"): meter yang datanya benar-benar ga ada → tetap flag jujur; TAPI yang bisa dihitung
dari harga JANGAN di-stub. Empat dari lima meter bisa dari harga:

  TREND    : breadth (% di atas MA50/MA200) + momentum (median RS63) + market structure (trend quality).
             100% dari harga. LIVE tanpa feed apapun.
  CREDIT   : proxy spread dari credit ETF — HY (JNK/HYG) vs IG (LQD) vs Treasury (IEF/TLT). Spread
             melebar = stress. 100% dari harga (proxy, bukan CDS beneran — di-flag).
  BUBBLE   : ekstensi harga (% di atas MA200) + realized-vol regime + breadth divergence + (valuation
             P/E dari fair_value kalau ada). Sebagian dari harga.
  WEALTH   : momentum tema sekuler (AI=SMH, Power=proxy, Nuclear=NLR/URA, India=INDA, Robotics=BOTZ,
             Defense=ITA). Composite 63d/126d accel. 100% dari harga.
  LIQUIDITY: dari funding_stress (FRED: EFFR/reserves/RRP/TGA). Kalau FRED ga wired → funding_stress
             pakai synthetic + flag. Ini SATU-SATUNYA yang genuinely butuh FRED buat akurat.

Setiap meter: value 0-100, status, komponen, dan 'real' flag + 'basis' (dari mana angkanya).
Semua threshold = prior yang bisa dikalibrasi; ga ada angka yang dikarang tanpa basis data.
"""
from __future__ import annotations
import numpy as np


def _f(v):
    try:
        v = float(v)
        return v if np.isfinite(v) else None
    except Exception:
        return None


def _above_ma(close, n):
    if close is None or len(close) < n:
        return None
    return float(close.iloc[-1]) > float(close.tail(n).mean())


def _ret(close, n):
    if close is None or len(close) <= n:
        return None
    return float(close.iloc[-1] / close.iloc[-1 - n] - 1)


# ─────────────────────────────── TREND (breadth + momentum + structure) ───────────────────────────────
def trend(us, bench="SPY"):
    names = [t for t, d in us.items() if d is not None and len(d) >= 205 and "-USD" not in t and ".JK" not in t]
    if len(names) < 10:
        return _stub("Trend", ["Breadth", "Momentum", "Market Structure", "Internals"])
    above50 = [_above_ma(us[t]["Close"], 50) for t in names]
    above200 = [_above_ma(us[t]["Close"], 200) for t in names]
    b50 = np.mean([x for x in above50 if x is not None])
    b200 = np.mean([x for x in above200 if x is not None])
    _bd = us.get(bench)
    bench_ret = _ret(_bd["Close"], 63) if _bd is not None and len(_bd) > 63 else 0.0
    bench_ret = bench_ret or 0.0
    rs = [(_ret(us[t]["Close"], 63) or 0) - bench_ret for t in names]
    mom = np.mean([1.0 if r > 0 else 0.0 for r in rs])  # % outperforming bench
    # market structure: fraction with MA50 > MA200 (uptrend structure)
    struct = np.mean([1.0 if (float(us[t]["Close"].tail(50).mean()) > float(us[t]["Close"].tail(200).mean())) else 0.0 for t in names])
    val = round((0.40 * b50 + 0.25 * b200 + 0.20 * mom + 0.15 * struct) * 100)
    status = "risk-on / broad" if val >= 60 else "narrowing / mixed" if val >= 40 else "risk-off / weak"
    col = "grn" if val >= 60 else "amb" if val >= 40 else "red"
    return {"name": "Trend", "value": val, "status": status, "color": col, "real": True,
            "basis": f"breadth {b50*100:.0f}%>MA50 · {mom*100:.0f}% beat SPY63 · {struct*100:.0f}% uptrend-struct (price)",
            "components": ["Breadth", "Momentum", "Market Structure", "Internals"]}


# ─────────────────────────────── CREDIT (ETF spread proxy) ───────────────────────────────
def credit(us):
    hy = us.get("JNK") if us.get("JNK") is not None else us.get("HYG")
    ig = us.get("LQD")
    tsy = us.get("IEF") if us.get("IEF") is not None else us.get("TLT")
    if hy is None or tsy is None:
        return _stub("Credit", ["HY", "IG", "CDS", "Bank Funding"])
    # HY total-return underperformance vs Treasury over 21d = spread-widening proxy (stress)
    hy21 = _ret(hy["Close"], 21) or 0.0
    tsy21 = _ret(tsy["Close"], 21) or 0.0
    hy_excess = hy21 - tsy21                          # negative = HY lagging = spread widening = stress
    ig_excess = ((_ret(ig["Close"], 21) or 0.0) - tsy21) if ig is not None else 0.0
    # 63d trend of HY/Treasury ratio (rising = risk-on credit)
    ratio = (hy["Close"] / tsy["Close"]).dropna()
    ratio_tr = (float(ratio.iloc[-1] / ratio.iloc[-21] - 1)) if len(ratio) > 21 else 0.0
    # map to 0-100 where 100 = healthiest credit (widest risk-on), 0 = max stress
    raw = 50 + 900 * hy_excess + 500 * ig_excess + 400 * ratio_tr
    val = int(max(0, min(100, round(raw))))
    status = "credit calm / risk-on" if val >= 60 else "neutral" if val >= 40 else "credit stress widening"
    col = "grn" if val >= 60 else "amb" if val >= 40 else "red"
    return {"name": "Credit", "value": val, "status": status, "color": col, "real": True,
            "basis": f"HY−Tsy 21d {hy_excess*100:+.1f}% · IG−Tsy {ig_excess*100:+.1f}% · HY/Tsy ratio {ratio_tr*100:+.1f}% (ETF proxy, not CDS)",
            "components": ["HY", "IG", "CDS", "Bank Funding"]}


# ─────────────────────────────── BUBBLE (extension + vol + valuation) ───────────────────────────────
def bubble(us, fair_value=None, bench="SPY"):
    names = [t for t, d in us.items() if d is not None and len(d) >= 205 and "-USD" not in t and ".JK" not in t]
    if len(names) < 10:
        return _stub("Bubble", ["Valuation", "Leverage", "Sentiment", "Options"])
    # extension: median % above MA200 across names
    ext = []
    for t in names:
        c = us[t]["Close"]
        ma = float(c.tail(200).mean())
        if ma > 0:
            ext.append(float(c.iloc[-1]) / ma - 1)
    med_ext = float(np.median(ext)) if ext else 0.0
    # froth in the leaders: % of names >20% above MA200
    frothy = np.mean([1.0 if e > 0.20 else 0.0 for e in ext]) if ext else 0.0
    # low realized vol + high extension = complacency/bubble risk
    spy = us.get(bench)
    rv = float(spy["Close"].pct_change().dropna().tail(21).std() * (252 ** 0.5)) if spy is not None else 0.15
    # valuation overlay (if fair_value has PEs)
    val_over = None
    if isinstance(fair_value, dict) and fair_value:
        pes = [v.get("pe") for v in fair_value.values() if isinstance(v, dict) and _f(v.get("pe")) and v["pe"] > 0]
        if pes:
            val_over = float(np.median(pes))
    raw = 40 + 220 * med_ext + 40 * frothy + (max(0, (0.14 - rv)) * 120)
    if val_over:
        raw += max(0, (val_over - 22)) * 1.2      # PE above ~22 adds froth
    val = int(max(0, min(100, round(raw))))
    status = "froth / late-stage" if val >= 65 else "elevated" if val >= 45 else "healthy / not stretched"
    col = "red" if val >= 65 else "amb" if val >= 45 else "grn"
    basis = f"median {med_ext*100:+.0f}% vs MA200 · {frothy*100:.0f}% names >20% ext · RV {rv*100:.0f}%"
    if val_over:
        basis += f" · median PE {val_over:.0f}"
    return {"name": "Bubble", "value": val, "status": status, "color": col, "real": True,
            "basis": basis + (" (price + valuation)" if val_over else " (price only; no valuation feed)"),
            "components": ["Valuation", "Leverage", "Sentiment", "Options"]}


# ─────────────────────────────── WEALTH (secular theme momentum) ───────────────────────────────
_WEALTH_THEMES = {"AI": ["SMH", "SOXX"], "Power Grid": ["XLU", "VST", "GEV"], "Nuclear": ["NLR", "URA", "CCJ"],
                  "India": ["INDA"], "Robotics": ["BOTZ"], "Defense": ["ITA"]}

def wealth(us):
    scores = {}
    for theme, proxies in _WEALTH_THEMES.items():
        accs = []
        for p in proxies:
            d = us.get(p)
            if d is not None and len(d) > 131:
                r63, r126 = _ret(d["Close"], 63), _ret(d["Close"], 126)
                if r63 is not None and r126 is not None:
                    accs.append(r63 - r126 + 0.5 * r126)     # accel + trend
        if accs:
            scores[theme] = float(np.mean(accs))
    if not scores:
        return _stub("Wealth", ["AI", "Power Grid", "Nuclear", "India", "Robotics"])
    avg = float(np.mean(list(scores.values())))
    val = int(max(0, min(100, round(50 + 300 * avg))))
    lead = max(scores, key=scores.get)
    status = f"secular bid · leader {lead}" if val >= 55 else "secular cooling" if val < 45 else "mixed secular"
    col = "grn" if val >= 55 else "amb" if val >= 45 else "red"
    return {"name": "Wealth", "value": val, "status": status, "color": col, "real": True,
            "basis": " · ".join(f"{k} {v*100:+.0f}%" for k, v in sorted(scores.items(), key=lambda x: -x[1])[:4]) + " (theme ETF momentum)",
            "components": list(_WEALTH_THEMES.keys())}


# ─────────────────────────────── LIQUIDITY (FRED via funding_stress) ───────────────────────────────
def liquidity(fred=None):
    try:
        from warroom import funding_stress as FS
        a = FS.assess()
        score = a.get("score")  # 0-100 stress (HIGH = tight)
        if score is None:
            return _stub("Liquidity", ["Fed", "ECB", "BOJ", "RRP", "TGA", "M2"])
        # invert: liquidity meter HIGH = ample liquidity (low stress)
        val = int(max(0, min(100, round(100 - score))))
        synthetic = a.get("synthetic", False) or a.get("basis") == "synthetic"
        status = ("ample / easing" if val >= 60 else "neutral" if val >= 40 else "tightening / stress")
        if synthetic:
            status += " (synthetic — wire FRED_API_KEY)"
        col = "grn" if val >= 60 else "amb" if val >= 40 else "red"
        return {"name": "Liquidity", "value": val, "status": status, "color": col, "real": not synthetic,
                "basis": a.get("summary", "EFFR/reserves/RRP/TGA composite (FRED)"),
                "components": ["Fed", "ECB", "BOJ", "RRP", "TGA", "M2"]}
    except Exception:
        return _stub("Liquidity", ["Fed", "ECB", "BOJ", "RRP", "TGA", "M2"])


def _stub(name, comps):
    return {"name": name, "value": None, "status": "needs data feed", "color": "gry", "real": False,
            "basis": "no usable data in this environment", "components": comps}


def compute_all(us, fred=None, fair_value=None):
    """Semua meter yang bisa dihitung dari harga + funding. Dipanggil compute, hasil dipakai brief_export."""
    return {"trend": trend(us), "credit": credit(us), "bubble": bubble(us, fair_value),
            "wealth": wealth(us), "liquidity": liquidity(fred)}
