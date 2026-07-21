"""warroom/decision_center.py — LEVEL 8 DECISION CENTER (spec dari dokumen IIDOS Edward).

Mengganti approach lama (stop = px*0.97 / target = px*1.06 hardcoded, entry zone yang
bawahnya = stop, P(win) linear-map dari score). Approach baru per spec:

  ENTRY  : Conservative / Base / Aggressive zone + DCA ladder + pyramiding level —
           SEMUA diturunkan dari Hedgeye TRADE/TREND band. TANPA risk range → TANPA level
           (di-withhold + flag, TIDAK PERNAH difabrikasi ±3%).
  STOP   : 5 jenis — Technical (band-derived), Macro (kondisi quad-flip), Thesis (kill-switch
           kausal dari chain), Time (bar tanpa follow-through), Fundamental (hanya jika feed ada;
           kalau tidak: 'absent, not faked').
  TARGET : T1 = TRADE opposite band · T2 = TREND · T3 = TAIL (jika tersedia) + expected holding
           dari konvensi durasi Hedgeye (TRADE≈15d, TREND≈63d, TAIL≈756d) — konvensi, bukan prediksi.
  P(win)/EV: HANYA dari kalibrasi track-record (tracker DB) kalau n_closed ≥ MIN_N di bucket
           yang sama. Di bawah itu → None + alasan ("uncalibrated") dan EV TIDAK ditampilkan.
  INVALIDATION: daftar kondisi kausal yang bisa diuji (bukan cuma level harga).
  REKOMENDASI: BUY / WATCH / AVOID / SELL / HOLD (vocab spec).

Semua parameter struktur (0.5·half stop, rung DCA, 10-bar time stop) = PRIOR TAK-TERVALIDASI,
dilabel begitu, dan masuk daftar uji di validation/ (stability + decision replay).
"""
from __future__ import annotations
import os
import sqlite3
import math

MIN_N_CALIB = 30          # minimum closed trades sebelum P(win) boleh tampil
STOP_HALF_FRAC = 0.5      # technical stop = 0.5 · half-width di luar TRADE band (prior MQA v25)
TIME_STOP_BARS = 10       # prior — diuji di validation/stability
TIME_STOP_R = 0.5         # follow-through minimal +0.5R dalam TIME_STOP_BARS


# ────────────────────────────────────────── level builder ──────────────────────────────────────────
def levels(direction, rr, px):
    """Bangun paket level dari risk range asli. rr None/invalid → None (withheld, bukan fabricated)."""
    try:
        tl, th = float(rr["trade"]["lrr"]), float(rr["trade"]["trr"])
        if not (math.isfinite(tl) and math.isfinite(th)) or th <= tl or px is None:
            return None
    except Exception:
        return None
    nl = _f((rr.get("trend") or {}).get("lrr")); nh = _f((rr.get("trend") or {}).get("trr"))
    xl = _f((rr.get("tail") or {}).get("lrr")); xh = _f((rr.get("tail") or {}).get("trr"))
    W = th - tl
    half = W / 2.0
    r2 = lambda v: (round(float(v), 2) if v is not None and math.isfinite(float(v)) else None)

    if direction == "Long":
        entry = {
            "conservative": (r2(tl), r2(tl + 0.25 * W)),
            "base":         (r2(tl + 0.15 * W), r2(tl + 0.50 * W)),
            "aggressive":   (r2(min(px, tl + 0.70 * W)), r2(px)),
            "dca_ladder":   [{"px": r2(tl + f * W), "wt": w} for f, w in ((0.40, 0.40), (0.25, 0.30), (0.10, 0.30))],
            "pyramid":      {"trigger": f"close > {r2(th)} lalu retest {r2(th)}", "level": r2(th)},
        }
        stop_tech = r2(tl - STOP_HALF_FRAC * half)
        t1, t2, t3 = r2(th), r2(nh), r2(xh)
        in_zone = tl <= px <= tl + 0.70 * W
    elif direction == "Short":
        entry = {
            "conservative": (r2(th - 0.25 * W), r2(th)),
            "base":         (r2(th - 0.50 * W), r2(th - 0.15 * W)),
            "aggressive":   (r2(px), r2(max(px, th - 0.70 * W))),
            "dca_ladder":   [{"px": r2(th - f * W), "wt": w} for f, w in ((0.40, 0.40), (0.25, 0.30), (0.10, 0.30))],
            "pyramid":      {"trigger": f"close < {r2(tl)} lalu retest {r2(tl)}", "level": r2(tl)},
        }
        stop_tech = r2(th + STOP_HALF_FRAC * half)
        t1, t2, t3 = r2(tl), r2(nl), r2(xl)
        in_zone = th - 0.70 * W <= px <= th
    else:
        return {"entry": None, "stops": None, "targets": None, "watch_band": (r2(tl), r2(th)), "in_zone": False}

    # Sanitize target ladder: TREND/TAIL bands are computed independently of TRADE, so in some
    # vol states they can fall inside T1. A valid ladder must be strictly monotonic AWAY from price.
    # Drop (not crash) any rung that isn't genuinely further out than the previous one.
    if direction == "Long":
        if t2 is not None and t2 <= t1: t2 = None
        if t3 is not None and t3 <= (t2 or t1): t3 = None
        # core direction invariant (this one must hold; if not, levels are unusable → withhold)
        if not (stop_tech < tl <= t1):
            return None
    else:
        if t2 is not None and t2 >= t1: t2 = None
        if t3 is not None and t3 >= (t2 or t1): t3 = None
        if not (stop_tech > th >= t1):
            return None

    hold = {"T1": "~15 hari bursa (durasi TRADE)", "T2": "~63 hari (TREND)", "T3": "~3 thn (TAIL)"}
    return {"entry": entry, "stops": {"technical": stop_tech}, "targets": {"t1": t1, "t2": t2, "t3": t3},
            "expected_holding": hold, "in_zone": in_zone, "band": (r2(tl), r2(th)), "width": r2(W)}


def _f(v):
    try:
        v = float(v)
        return v if math.isfinite(v) else None
    except Exception:
        return None


# ────────────────────────────────────── stop non-teknikal ──────────────────────────────────────
def stops_full(direction, lv, regime, chains, ticker, fundamentals=None):
    """5 jenis stop per spec. Non-price stop = KONDISI yang bisa diuji, bukan angka fabrikasi."""
    s = dict((lv or {}).get("stops") or {})
    if direction not in ("Long", "Short"):
        return s
    struct = (regime or {}).get("structural", "?")
    hazard = (regime or {}).get("flip_hazard")
    if direction == "Long":
        s["macro"] = (f"Structural quad flip → Quad 3/4 ATAU posture jadi Defensive "
                      f"(sekarang {struct}, flip hazard {hazard if hazard is not None else '—'})")
    else:
        s["macro"] = (f"Structural quad flip → Quad 1/2 + posture Risk-on "
                      f"(sekarang {struct}, flip hazard {hazard if hazard is not None else '—'})")
    s["thesis"] = _thesis_kill(direction, chains, ticker)
    s["time"] = (f"{TIME_STOP_BARS} bar tanpa close ≥ entry+{TIME_STOP_R}R (Long) / ≤ entry−{TIME_STOP_R}R (Short) "
                 f"→ exit [prior, uji di validation/stability]")
    if fundamentals and isinstance(fundamentals, dict) and fundamentals.get("eps_rev_dir"):
        s["fundamental"] = f"Forward EPS revision berbalik {'negatif' if direction=='Long' else 'positif'} (feed: {fundamentals['eps_rev_dir']})"
    else:
        s["fundamental"] = "feed fundamental tidak aktif — absent, not faked"
    return s


def _thesis_kill(direction, chains, ticker):
    """Ambil kill-switch kausal dari chain yang memuat ticker; fallback = kondisi RS/formation."""
    try:
        for ch in (chains or []):
            names = set()
            for k in ("beneficiaries", "tickers", "nodes"):
                v = ch.get(k)
                if isinstance(v, (list, tuple)):
                    names |= {str(x).upper() for x in v}
                elif isinstance(v, dict):
                    names |= {str(x).upper() for x in v.keys()}
            if ticker and ticker.upper() in names:
                kill = ch.get("kill_condition") or ch.get("kill") or ch.get("invalidation")
                if kill:
                    return f"[chain: {ch.get('name', ch.get('id', '?'))}] {kill}"
    except Exception:
        pass
    return ("RS63 vs SPY berbalik negatif + formation kehilangan BULLISH" if direction == "Long"
            else "RS63 vs SPY berbalik positif + formation kehilangan BEARISH")


def invalidation_list(direction, lv, regime, chains, ticker):
    """Daftar kondisi kausal yang mematikan thesis (spec: 'apa yang membuat thesis mati?')."""
    out = []
    if direction not in ("Long", "Short"):
        return out
    st = stops_full(direction, lv, regime, chains, ticker)
    tech = ((lv or {}).get("stops") or {}).get("technical")
    if tech is not None:
        band = (lv or {}).get("band")
        out.append(f"Harga close di {'bawah' if direction=='Long' else 'atas'} {tech} "
                   f"(0.5·half di luar TRADE band {band[0]}–{band[1]}) [prior]")
    out.append(st.get("thesis", ""))
    out.append(st.get("macro", ""))
    out.append(st.get("time", ""))
    return [x for x in out if x]


# ────────────────────────────────── P(win)/EV: calibrated-or-silent ──────────────────────────────────
def pwin_calibrated(direction, market=None, db_path=os.path.join("data", "track_record.db"), min_n=MIN_N_CALIB):
    """P(win) HANYA dari trade CLOSED di tracker (point-in-time log). n<min_n → (None, n, alasan)."""
    try:
        c = sqlite3.connect(db_path)
        q = "SELECT COUNT(*), SUM(CASE WHEN ret_pct > 0 THEN 1 ELSE 0 END) FROM signals WHERE status='CLOSED' AND direction=?"
        args = [direction]
        if market:
            q += " AND market=?"; args.append(market)
        n, w = c.execute(q, args).fetchone(); c.close()
        n, w = int(n or 0), int(w or 0)
        if n < min_n:
            if market:  # coba bucket lebih lebar (tanpa market) sebelum nyerah
                return pwin_calibrated(direction, None, db_path, min_n)
            return None, n, f"uncalibrated — baru {n} closed (< {min_n})"
        p = w / n
        se = math.sqrt(p * (1 - p) / n)
        return round(p, 3), n, f"±{1.96*se:.2f} (95% CI, n={n})"
    except Exception as e:
        return None, 0, f"tracker unavailable ({type(e).__name__})"


def ev_r(pwin, lv, direction, px):
    """EV dalam R-multiple ke T1 (risk = jarak ke technical stop). None kalau P(win) uncalibrated."""
    if pwin is None or not lv or not lv.get("targets") or px is None:
        return None
    t1 = lv["targets"].get("t1"); stop = (lv.get("stops") or {}).get("technical")
    if t1 is None or stop is None:
        return None
    risk = abs(px - stop)
    if risk <= 0:
        return None
    reward = (t1 - px) if direction == "Long" else (px - t1)
    if reward <= 0:
        return None
    rr = reward / risk
    return round(pwin * rr - (1 - pwin) * 1.0, 2)


# ────────────────────────────────────── rekomendasi (vocab spec) ──────────────────────────────────────
def recommend(s, regime, open_tickers=None):
    """Research/action vocabulary. Capital permission is handled outside this descriptive layer."""
    d = s.get("_dir"); t = s.get("ticker")
    market = str(s.get("market") or "").lower()
    if open_tickers and t in open_tickers:
        return "MANAGE OPEN POSITION", "existing position; use explicit risk and thesis invalidation"
    lv = s.get("decision_levels")
    timing = ((s.get("timing") or {}).get("entry_timing") or "").upper()
    late = ("LATE" in timing) or ("FOMO" in timing)
    if d == "Long":
        if regime.get("defensive") and not s.get("_override_defensive"):
            return "REDUCE / AVOID", "defensive regime; new long requires stronger evidence"
        if lv and lv.get("in_zone") and not late:
            return "TRIGGERED WATCH LONG", "entry-state conditions observed; capital remains governed by validation gate"
        return "WATCH LONG", ("late/stretched; wait for a valid zone" if late or (lv and not lv.get("in_zone"))
                              else "risk range withheld" if not lv else "wait for trigger")
    if d == "Short":
        if market in {"idx", "ihsg", "indonesia"}:
            return "REDUCE / AVOID", "IHSG adapter is long-only; short execution is prohibited"
        if lv and lv.get("in_zone") and not late:
            return "TRIGGERED WATCH SHORT", "short-state conditions observed; capital remains governed by validation gate"
        return "WATCH SHORT", "wait for bounce/zone and explicit trigger"
    return "NO TRADE", "no aligned formation and relative-strength state"


# ────────────────────────────────────────── paket lengkap ──────────────────────────────────────────
def build(s, regime, chains=None, open_tickers=None, fundamentals=None, db_path=None, market_cap=None, conviction=None):
    """Satu paket keputusan utuh untuk satu setup (dipanggil compute)."""
    d = s.get("_dir"); px = s.get("close") or s.get("px")
    rr = s.get("_rr_full")  # dict risk range asli kalau compute simpen; fallback rakit dari lrr/trr
    if rr is None and s.get("lrr") and s.get("trr"):
        rr = {"trade": {"lrr": s["lrr"], "trr": s["trr"]}}
        tb = s.get("trend_band") or (None, None)
        if tb and tb[0] and tb[1]:
            rr["trend"] = {"lrr": tb[0], "trr": tb[1]}
    lv = levels(d, rr, _f(px)) if rr else None
    s["decision_levels"] = lv
    pw, n, note = pwin_calibrated(d, s.get("market"), db_path or os.path.join("data", "track_record.db"))
    # MARKET-CAP TARGET + CONVEXITY (thesis-level target, beda dari technical target di atas)
    mct = None
    try:
        from warroom import market_cap_target as MC
        conv = conviction if conviction is not None else int(s.get("score", 50))
        mct = MC.build(s.get("ticker"), _f(px), market_cap, conv, d if d in ("Long", "Short") else "Long")
    except Exception:
        mct = None
    pkg = {
        "levels": lv,
        "stops": stops_full(d, lv, regime, chains, s.get("ticker"), fundamentals),
        "invalidation": invalidation_list(d, lv, regime, chains, s.get("ticker")),
        "pwin": pw, "pwin_n": n, "pwin_note": note,
        "ev_r": ev_r(pw, lv, d, _f(px)),
        "mcap_target": mct,
        "levels_withheld": bool(d in ("Long", "Short") and lv is None),
    }
    pkg["recommendation"], pkg["reason"] = recommend(s, regime, open_tickers)
    return pkg
