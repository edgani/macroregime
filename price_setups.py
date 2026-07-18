"""price_signal_setups — surface REAL tickers from validated price engines when feeds are absent."""
import numpy as np, pandas as pd
def price_signal_setups(ohlcv, top=12):
    """ohlcv: {ticker: DataFrame[Open,High,Low,Close,Volume]}. Returns setup dicts (real tickers)."""
    from engines import bandarmetrics_engine as BM
    from gcfis.engines.entry import run_entry
    from engines.inventory_transfer_engine import classify_phase
    rows = []
    for tk, df in ohlcv.items():
        df = df.dropna()
        if len(df) < 200: continue
        c = df["Close"]
        rs = float(c.iloc[-1]/c.iloc[-252]-1) if len(c) > 252 else float(c.iloc[-1]/c.iloc[0]-1)
        try:
            bm = BM.compute(df); mr = bm.get("markup_readiness")
            mr = mr.get("readiness") if isinstance(mr, dict) else mr
            acc = 1.0 if bm.get("stealth_accumulation", {}).get("is_stealth") else 0.0
        except Exception:
            mr, acc = None, 0.0
        if mr is None: continue
        rows.append({"tk": tk, "rs": rs, "mr": float(mr), "acc": acc, "c": c, "df": df})
    if not rows: return []
    df = pd.DataFrame(rows)
    df["score"] = 0.45*df["mr"].rank(pct=True) + 0.35*df["rs"].rank(pct=True) + 0.20*df["acc"]
    df = df.sort_values("score", ascending=False).head(top)
    out = []
    for _, r in df.iterrows():
        e = run_entry(r["c"], "long")
        try:
            _ph = classify_phase(r["df"])
        except Exception:
            _ph = {"ok": False}
        out.append({"tk": r["tk"], "act": "BUILD_LONG" if e.get("valid") else "WATCH",
                    "dir": "long", "conv": round(float(r["score"])*100),
                    "e": round(e.get("entry_px"), 2) if e.get("entry_px") else None,
                    "s": round(e.get("stop"), 2) if e.get("stop") else None,
                    "t": round(e.get("target"), 2) if e.get("target") else None,
                    "rr": round(e.get("rr"), 2) if e.get("rr") else None,
                    "ty": "PRICE-SIGNAL", "gm": e.get("gamma_regime", ""), "valid": e.get("valid", False),
                    "warn": "", "phase": _ph.get("phase") if _ph.get("ok") else None,
                    "phase_conf": _ph.get("confidence") if _ph.get("ok") else None,
                    "why": f"markup-readiness {round(r['mr'])} · RS {round(r['rs']*100)}%" + (f" · {_ph['phase']} {_ph['confidence']}%" if _ph.get("ok") else "")})
    return out
