"""warroom/market_cap_target.py — Market-Cap-Anchored Target + Convexity Engine.

Jawaban buat pertanyaan Edward: target/stop JANGAN cuma teknikal (TREND high). Target = EXPECTED
MARKET CAP (bull/base/bear TAM capture) → konversi ke price. Company = kendaraan, bukan endpoint:

    Company → Expected Market Cap → Price Target → Convexity → Portfolio Weight → Capital Allocation

Cara kerja (semua di market-cap space, lalu konversi):
  price_target = price × (mcap_target / mcap_now) × (1 − dilution)
  (rasio market-cap = rasio harga kalau shares konstan; dilution haircut buat unlock/raise)

Scenario multiples (bull/base/bear × mcap sekarang) datang dari thesis-TAM view. SEMUANYA PRIOR YANG
BISA DIKALIBRASI — bukan presisi karangan. Kill-conditions & TAM-note dari dokumen Edward.

Output per nama:
  • Price target bull/base/bear (dari expected market cap)
  • Convexity: upside/downside, EV (probability-weighted), max permanent loss, tail ratio
  • Alpha tier: TACTICAL (5-20%) / STRATEGIC (20-80%) / GENERATIONAL (10x+) — DIPISAH, sesuai permintaan
  • Kill-thesis: "what would change my mind" (kondisi yang mematikan thesis)
  • Suggested portfolio weight (dari EV × conviction, di-cap)

HONEST: multiples & probabilitas = prior. Validasi lewat outcome (tracker) + backtest. Ga ada DCF penuh;
ga ada data TAM real-time. Ini kerangka keputusan yang eksplisit & bisa diaudit, bukan ramalan.
"""
from __future__ import annotations
import math

# ─────────────────────── thesis-TAM scenario priors (KALIBRASI di sini) ───────────────────────
# mcap_mult = target market cap sebagai kelipatan market cap SEKARANG (bull/base/bear).
# p_* = probabilitas skenario (jumlah = 1). dilution = haircut buat share issuance/unlock.
# horizon_m = bulan ke target. kill = kondisi yang mematikan thesis. Semua PRIOR — ubah sesuai view lu.
_THESIS = {
    "ai_power": {
        "label": "AI Power / Electrification",
        "bull": 3.2, "base": 1.7, "bear": 0.65, "p_bull": 0.30, "p_base": 0.45, "p_bear": 0.25,
        "dilution": 0.03, "horizon_m": 18,
        "tam": "Datacenter power demand 2024→2030: ~3-4x. Grid + backup + on-site gen bottleneck.",
        "kill": ["Hyperscaler capex guide cut >15% QoQ", "Transformer lead-time normalizes <40wk",
                 "Utility capex growth turns negative", "Power price (PJM/ERCOT fwd) −25%"]},
    "ai_compute": {
        "label": "AI Compute / Accelerators",
        "bull": 2.6, "base": 1.5, "bear": 0.60, "p_bull": 0.28, "p_base": 0.47, "p_bear": 0.25,
        "dilution": 0.02, "horizon_m": 15,
        "tam": "Accelerator TAM $400B+ by 2027 (consensus). Leader-heavy; watch ASIC share shift.",
        "kill": ["Cloud capex deceleration 2 quarters", "Inference moves off-GPU at scale",
                 "China export relief floods supply", "Gross-margin compression from ASIC competition"]},
    "photonics": {
        "label": "Photonics / CPO / Optics",
        "bull": 4.0, "base": 1.9, "bear": 0.55, "p_bull": 0.32, "p_base": 0.40, "p_bear": 0.28,
        "dilution": 0.04, "horizon_m": 24,
        "tam": "1.6T transceiver + CPO ramp. InP/EML supply constrained through 2027+. Small floats.",
        "kill": ["CPO adoption slips (pluggables persist)", "NVDA optics roadmap de-commits",
                 "New EML capacity online (supply unconstrained)", "Transceiver ASP collapse"]},
    "uranium": {
        "label": "Uranium / Nuclear Fuel",
        "bull": 3.5, "base": 1.6, "bear": 0.55, "p_bull": 0.30, "p_base": 0.42, "p_bear": 0.28,
        "dilution": 0.05, "horizon_m": 30,
        "tam": "Structural supply deficit; SMR optionality. Spot vs term divergence = the setup.",
        "kill": ["Spot uranium −25% sustained", "SMR timelines slip >2yr", "Kazatomprom supply surge",
                 "Reactor restart/newbuild policy reversal"]},
    "crypto_beta": {
        "label": "Crypto Beta Chain",
        "bull": 5.0, "base": 1.8, "bear": 0.35, "p_bull": 0.25, "p_base": 0.35, "p_bear": 0.40,
        "dilution": 0.10, "horizon_m": 9,
        "tam": "Cycle beta: BTC→ETH→SOL→alt→meme, rising beta + rising fragility down the chain.",
        "kill": ["BTC loses cycle trend (200d)", "Funding flips deeply negative", "Major token unlock cliff",
                 "Exchange reserve rising (distribution)"]},
    "generic": {
        "label": "Generic (uncalibrated thesis)",
        "bull": 1.8, "base": 1.2, "bear": 0.75, "p_bull": 0.30, "p_base": 0.45, "p_bear": 0.25,
        "dilution": 0.02, "horizon_m": 12,
        "tam": "No thesis-specific TAM wired — using conservative generic multiples. Calibrate per name.",
        "kill": ["RS vs benchmark turns negative", "Formation breaks", "Regime flips defensive"]},
}

# ticker → thesis key (curated; extend freely). Names not here → 'generic'.
_TICKER_THESIS = {
    # AI power / electrification
    "VRT": "ai_power", "ETN": "ai_power", "PWR": "ai_power", "GEV": "ai_power", "CEG": "ai_power",
    "VST": "ai_power", "NRG": "ai_power", "TLN": "ai_power", "HUBB": "ai_power", "POWL": "ai_power",
    "NEE": "ai_power", "BE": "ai_power", "BLDP": "ai_power", "OKLO": "uranium", "SMR": "uranium",
    # compute
    "NVDA": "ai_compute", "AMD": "ai_compute", "AVGO": "ai_compute", "MRVL": "ai_compute",
    "SMH": "ai_compute", "SOXX": "ai_compute", "MU": "ai_compute", "TSM": "ai_compute", "ALAB": "ai_compute",
    "CRDO": "ai_compute", "AMAT": "ai_compute", "LRCX": "ai_compute", "KLAC": "ai_compute",
    # photonics
    "COHR": "photonics", "LITE": "photonics", "FN": "photonics", "GLW": "photonics", "AMKR": "photonics",
    # uranium
    "CCJ": "uranium", "UEC": "uranium", "URA": "uranium", "DNN": "uranium", "NXE": "uranium",
    # crypto
    "BTC-USD": "crypto_beta", "ETH-USD": "crypto_beta", "SOL-USD": "crypto_beta", "BNB-USD": "crypto_beta",
    "MSTR": "crypto_beta", "COIN": "crypto_beta", "IBIT": "crypto_beta", "MARA": "crypto_beta",
    "RIOT": "crypto_beta", "CLSK": "crypto_beta",
    # materials for aero/decoupling
    "MP": "generic", "ATI": "generic", "MTRN": "generic", "KTOS": "generic",
}


def thesis_for(ticker):
    return _TICKER_THESIS.get((ticker or "").upper(), "generic")


def _f(v):
    try:
        v = float(v)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def _mcap_scale(market_cap):
    """Nama kecil punya room lebih besar (bisa 10x lebih gampang dari mega-cap). Skala bull/bear
    multiple by posisi market-cap (log). $1-3B → amplify; >$100B → dampen. Ini inti beta-chain:
    thesis yang sama, tapi convexity beda per ukuran. Anchor di ~$20B = netral (scale 1.0)."""
    mc = _f(market_cap)
    if mc is None or mc <= 0:
        return 1.0, 1.0  # no mcap → no scaling
    anchor = 20e9
    # log-distance from anchor; smaller = positive boost to upside, larger = damped
    z = math.log10(anchor / mc)          # >0 if smaller than anchor, <0 if larger
    z = max(-1.2, min(1.5, z))           # clamp: cap the boost/damp
    bull_scale = 1.0 + 0.45 * z          # small-cap: bigger bull; mega-cap: smaller bull
    bear_scale = 1.0 + 0.15 * max(z, 0)  # small-cap slightly deeper bear (fragility), mega-cap unchanged
    return round(bull_scale, 3), round(bear_scale, 3)


# ─────────────────────── scenario → price targets from expected market cap ───────────────────────
def scenarios(ticker, price, market_cap=None, thesis_key=None, direction="Long"):
    """Bangun target harga bull/base/bear dari expected market cap. market_cap opsional — kalau ada,
    kita tampilkan expected mcap absolut + SCALE multiple by ukuran (small-cap = convexity lebih besar)."""
    price = _f(price)
    if price is None or price <= 0:
        return None
    tk = thesis_key or thesis_for(ticker)
    T = _THESIS.get(tk, _THESIS["generic"])
    dil = T["dilution"]
    mc = _f(market_cap)
    bull_s, bear_s = _mcap_scale(mc)
    # scaled multiples: bull amplified for small-cap; bear deepened slightly; base interpolated
    bull_m = round(1.0 + (T["bull"] - 1.0) * bull_s, 3)
    bear_m = round(max(0.15, 1.0 - (1.0 - T["bear"]) * bear_s), 3)
    base_m = round((bull_m + bear_m) / 2 * 0.55 + T["base"] * 0.45, 3)  # blend scaled midpoint + thesis base

    def tgt(mult):
        p = price * mult * (1 - dil)          # rasio market-cap = rasio harga, minus dilution
        return round(p, 2)

    out = {
        "thesis": tk, "thesis_label": T["label"], "horizon_m": T["horizon_m"], "tam": T["tam"],
        "price": price, "market_cap": mc, "dilution_haircut": dil,
        "mcap_scale": {"bull": bull_s, "bear": bear_s, "note": "small-cap amplified, mega-cap damped" if mc else "no mcap"},
        "bull": {"px": tgt(bull_m), "mcap_mult": bull_m, "p": T["p_bull"],
                 "mcap": round(mc * bull_m, 0) if mc else None},
        "base": {"px": tgt(base_m), "mcap_mult": base_m, "p": T["p_base"],
                 "mcap": round(mc * base_m, 0) if mc else None},
        "bear": {"px": tgt(bear_m), "mcap_mult": bear_m, "p": T["p_bear"],
                 "mcap": round(mc * bear_m, 0) if mc else None},
        "kill": T["kill"],
    }
    return out


def convexity(sc, direction="Long"):
    """Convexity dari scenario tree: upside/downside %, EV (probability-weighted), max permanent loss,
    tail ratio (upside/|downside|). Semua relatif ke harga sekarang."""
    if not sc:
        return None
    px = sc["price"]
    b, m, r = sc["bull"], sc["base"], sc["bear"]
    if direction == "Short":
        # untuk short, 'upside' = harga turun ke bear; balik tanda
        up_pct = (px - r["px"]) / px * 100
        base_pct = (px - m["px"]) / px * 100
        dn_pct = (px - b["px"]) / px * 100          # bull = skenario terburuk buat short
        ev = r["p"] * up_pct + m["p"] * base_pct + b["p"] * dn_pct
        max_loss = dn_pct
    else:
        up_pct = (b["px"] - px) / px * 100
        base_pct = (m["px"] - px) / px * 100
        dn_pct = (r["px"] - px) / px * 100          # bear = downside
        ev = b["p"] * up_pct + m["p"] * base_pct + r["p"] * dn_pct
        max_loss = dn_pct
    tail = (up_pct / abs(dn_pct)) if dn_pct != 0 else None
    return {"upside_pct": round(up_pct, 1), "base_pct": round(base_pct, 1), "downside_pct": round(dn_pct, 1),
            "ev_pct": round(ev, 1), "max_perm_loss_pct": round(max_loss, 1),
            "tail_ratio": round(tail, 2) if tail else None,
            "asymmetric": bool(tail and tail >= 2.5)}


def alpha_tier(upside_pct):
    """Pisahkan alpha (permintaan eksplisit Edward): tactical / strategic / generational."""
    if upside_pct is None:
        return "—", "gry"
    if upside_pct >= 300:
        return "GENERATIONAL 10x-class", "grn"
    if upside_pct >= 80:
        return "STRATEGIC", "grn"
    if upside_pct >= 20:
        return "TACTICAL+", "amb"
    if upside_pct >= 5:
        return "TACTICAL", "amb"
    return "marginal", "gry"


def suggested_weight(ev_pct, conviction_0_100, max_weight=0.08):
    """Expected market cap → portfolio weight. EV × conviction, di-cap. Company = kendaraan.
    Bukan Kelly penuh (itu butuh P(win) terkalibrasi) — ini heuristik sizing yang eksplisit."""
    if ev_pct is None or ev_pct <= 0:
        return 0.0
    conv = max(0.0, min(1.0, (conviction_0_100 or 0) / 100.0))
    raw = (ev_pct / 100.0) * conv * 0.5            # 0.5 = skala konservatif (prior)
    return round(min(max_weight, max(0.0, raw)), 4)


def build(ticker, price, market_cap=None, conviction=50, direction="Long", thesis_key=None):
    """Paket market-cap target lengkap untuk satu nama."""
    sc = scenarios(ticker, price, market_cap, thesis_key, direction)
    if not sc:
        return None
    cx = convexity(sc, direction)
    tier, tcol = alpha_tier(cx["upside_pct"] if cx else None)
    wt = suggested_weight(cx["ev_pct"] if cx else None, conviction)
    return {"scenarios": sc, "convexity": cx, "alpha_tier": tier, "alpha_color": tcol,
            "suggested_weight": wt, "kill_thesis": sc["kill"], "direction": direction}


# ─────────────────────── DECISION MARKET — efficient frontier antar kandidat ───────────────────────
def decision_market(candidates):
    """Bukan 'Buy Bloom'. Kasih SEMUA kandidat dalam satu thesis + trade-off (Decision Market spec).
    candidates: list of {ticker, price, market_cap, conviction, direction, thesis_key?}
    Return: ranked by EV + label pilihan (max-EV / min-risk / max-convexity)."""
    rows = []
    for c in candidates:
        pkg = build(c["ticker"], c.get("price"), c.get("market_cap"),
                    c.get("conviction", 50), c.get("direction", "Long"), c.get("thesis_key"))
        if not pkg or not pkg["convexity"]:
            continue
        cx = pkg["convexity"]
        rows.append({"ticker": c["ticker"], "thesis": pkg["scenarios"]["thesis_label"],
                     "ev_pct": cx["ev_pct"], "upside_pct": cx["upside_pct"], "downside_pct": cx["downside_pct"],
                     "tail_ratio": cx["tail_ratio"], "max_loss_pct": cx["max_perm_loss_pct"],
                     "alpha_tier": pkg["alpha_tier"], "weight": pkg["suggested_weight"],
                     "targets": {"bull": pkg["scenarios"]["bull"]["px"], "base": pkg["scenarios"]["base"]["px"],
                                 "bear": pkg["scenarios"]["bear"]["px"], "price": pkg["scenarios"]["price"]}})
    if not rows:
        return {"candidates": [], "frontier": {}}
    rows.sort(key=lambda x: -x["ev_pct"])
    # efficient frontier labels
    max_ev = max(rows, key=lambda x: x["ev_pct"])
    min_risk = min(rows, key=lambda x: abs(x["downside_pct"]))
    max_cvx = max(rows, key=lambda x: (x["tail_ratio"] or 0))
    frontier = {
        "max_ev": {"ticker": max_ev["ticker"], "ev_pct": max_ev["ev_pct"],
                   "note": "upside terbesar (execution risk lebih tinggi)"},
        "min_risk": {"ticker": min_risk["ticker"], "downside_pct": min_risk["downside_pct"],
                     "note": "downside paling terbatas (kualitas tinggi, upside lebih kecil)"},
        "max_convexity": {"ticker": max_cvx["ticker"], "tail_ratio": max_cvx["tail_ratio"],
                          "note": "payoff paling asimetris (upside/downside terbaik)"},
    }
    return {"candidates": rows, "frontier": frontier}
