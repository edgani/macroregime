"""warroom/decision_journal.py — Decision Journal (#399, WAJIB) + Decision Quality (Volume XXIV).

Edward: "semua keputusan harus disimpan, 6 bulan lagi dashboard review apakah benar." Plus prinsip
Volume XXIV: DECISION QUALITY ≠ OUTCOME QUALITY. Keputusan bisa benar walau hasil jangka pendek jelek,
kalau dibuat berdasarkan evidence terbaik + EV positif saat itu.

Tiap entry nyimpen: tanggal, ticker, action, REASON (mekanisme), CONFIDENCE, ALTERNATIVE (+ conf-nya),
INVALIDATION (kondisi yang mematikan thesis), entry price, target, review-date. Saat review:
  • Outcome: apa yang terjadi ke harga sejak keputusan.
  • Decision quality: apakah prosesnya benar (evidence + EV positif + invalidation jelas), TERLEPAS dari
    outcome. Ini yang dipakai poker/quant fund — nilai proses, bukan cuma hasil.

Store: SQLite (data/decision_journal.db). Ga ada yang dikarang — cuma nyimpen & review keputusan nyata.
"""
from __future__ import annotations
import os, sqlite3, json, datetime

DB = os.path.join(os.path.dirname(__file__), "..", "data", "decision_journal.db")


def _conn():
    os.makedirs(os.path.dirname(DB), exist_ok=True)
    c = sqlite3.connect(DB)
    c.execute("""CREATE TABLE IF NOT EXISTS decisions (
        id INTEGER PRIMARY KEY AUTOINCREMENT, date TEXT, ticker TEXT, action TEXT,
        reason TEXT, confidence REAL, alternative TEXT, alt_confidence REAL,
        invalidation TEXT, entry_px REAL, target_px REAL, review_date TEXT,
        reviewed INTEGER DEFAULT 0, outcome_px REAL, decision_quality TEXT, outcome_note TEXT)""")
    return c


def log_decision(ticker, action, reason, confidence, entry_px=None, target_px=None,
                 alternative=None, alt_confidence=None, invalidation=None, review_months=6):
    """Record a decision. review_date = today + review_months."""
    c = _conn()
    today = datetime.date.today()
    review = today + datetime.timedelta(days=int(review_months * 30))
    c.execute("""INSERT INTO decisions (date,ticker,action,reason,confidence,alternative,alt_confidence,
                 invalidation,entry_px,target_px,review_date) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
              (today.isoformat(), ticker, action, reason, confidence, alternative, alt_confidence,
               invalidation, entry_px, target_px, review.isoformat()))
    c.commit(); rid = c.execute("SELECT last_insert_rowid()").fetchone()[0]; c.close()
    return {"id": rid, "logged": ticker, "review_date": review.isoformat()}


def pending_reviews(current_prices=None):
    """Decisions past their review date → compute outcome + decision quality. current_prices: {ticker: px}."""
    c = _conn()
    today = datetime.date.today().isoformat()
    cur = c.execute("SELECT * FROM decisions WHERE reviewed=0 AND review_date<=?", (today,))
    cols = [d[0] for d in cur.description]; rows = cur.fetchall()
    out = []
    for row in rows:
        r = dict(zip(cols, row))
        px_now = (current_prices or {}).get(r["ticker"])
        outcome_ret = None
        if px_now and r["entry_px"]:
            outcome_ret = px_now / r["entry_px"] - 1
        # Decision quality = process, independent of outcome
        # (had reason + invalidation + reasonable confidence = sound process)
        dq = "SOUND" if (r["reason"] and r["invalidation"] and (r["confidence"] or 0) >= 50) else "WEAK PROCESS"
        out.append({**r, "outcome_ret": round(outcome_ret * 100, 1) if outcome_ret is not None else None,
                    "decision_quality": dq})
    c.close()
    return out


def mark_reviewed(decision_id, outcome_px, decision_quality, note=""):
    c = _conn()
    c.execute("UPDATE decisions SET reviewed=1, outcome_px=?, decision_quality=?, outcome_note=? WHERE id=?",
              (outcome_px, decision_quality, note, decision_id))
    c.commit(); c.close()


def all_decisions(limit=50):
    c = _conn()
    cur = c.execute("SELECT * FROM decisions ORDER BY date DESC LIMIT ?", (limit,))
    cols = [d[0] for d in cur.description]; rows = cur.fetchall(); c.close()
    return [dict(zip(cols, r)) for r in rows]


def stats():
    """Decision-quality KPIs (blueprint Research KPI): how many sound decisions, hit rate, DQ vs outcome."""
    c = _conn()
    all_d = c.execute("SELECT confidence,reason,invalidation,reviewed,outcome_px,entry_px FROM decisions").fetchall()
    c.close()
    n = len(all_d)
    if n == 0:
        return {"n": 0, "note": "no decisions logged yet"}
    sound = sum(1 for d in all_d if d[1] and d[2] and (d[0] or 0) >= 50)
    reviewed = [d for d in all_d if d[3]]
    wins = sum(1 for d in reviewed if d[4] and d[5] and d[4] > d[5])
    return {"n": n, "sound_process_pct": round(sound / n * 100), "reviewed": len(reviewed),
            "outcome_win_rate": round(wins / len(reviewed) * 100) if reviewed else None,
            "note": "Decision quality (sound process) is tracked separately from outcome — a sound decision "
                    "with a bad short-term outcome is still a good decision (Volume XXIV)."}
