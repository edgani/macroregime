"""Price-context setup generator.

Generates symmetric long and short research setups for two-sided markets.  The caller still owns
market-direction alignment and long-only rules (IHSG).  Scores are descriptive ranking context,
not calibrated probabilities.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def price_signal_setups(ohlcv, top=12):
    """Return bounded long/short setup candidates from observed OHLCV.

    Each ticker can contribute one long and one short context.  Market tabs later filter these
    through the market posture; a neutral posture labels them WATCH LONG/WATCH SHORT, not trades.
    """
    from engines import bandarmetrics_engine as BM
    from gcfis.engines.entry import run_entry
    from engines.inventory_transfer_engine import classify_phase

    rows = []
    for tk, frame in (ohlcv or {}).items():
        try:
            df = frame.dropna()
        except Exception:
            continue
        if len(df) < 200 or "Close" not in df:
            continue
        c = pd.to_numeric(df["Close"], errors="coerce").dropna()
        if len(c) < 200:
            continue
        rs = float(c.iloc[-1] / c.iloc[-252] - 1) if len(c) > 252 else float(c.iloc[-1] / c.iloc[0] - 1)
        try:
            bm = BM.compute(df)
            mr = bm.get("markup_readiness") or {}
            readiness = mr.get("readiness") if isinstance(mr, dict) else mr
            if readiness is None and isinstance(mr, dict):
                readiness = mr.get("score")
            acc = 1.0 if (bm.get("stealth_accumulation") or {}).get("is_stealth") else 0.0
            phase = str(bm.get("phase") or "NEUTRAL").upper()
            divergence = str(bm.get("divergence") or "FLAT").upper()
            bm_score = float(bm.get("score") if bm.get("score") is not None else 50.0)
        except Exception:
            readiness, acc, phase, divergence, bm_score = None, 0.0, "NEUTRAL", "FLAT", 50.0
        if readiness is None:
            continue
        distribution = 1.0 if phase in {"DISTRIBUTION", "MARKDOWN"} or divergence in {"BEARISH_DIV", "ALIGNED_DOWN"} else 0.0
        rows.append({
            "tk": tk, "rs": rs, "mr": float(readiness), "acc": acc,
            "distribution": distribution, "bm_score": bm_score, "c": c, "df": df,
            "phase": phase,
        })
    if not rows:
        return []

    ranked = pd.DataFrame(rows)
    ranked["long_score"] = (
        0.40 * ranked["mr"].rank(pct=True)
        + 0.35 * ranked["rs"].rank(pct=True)
        + 0.15 * ranked["acc"]
        + 0.10 * ranked["bm_score"].rank(pct=True)
    )
    ranked["short_score"] = (
        0.40 * (-ranked["rs"]).rank(pct=True)
        + 0.25 * (-ranked["bm_score"]).rank(pct=True)
        + 0.20 * ranked["distribution"]
        + 0.15 * (-ranked["mr"]).rank(pct=True)
    )

    each_side = max(1, int(np.ceil(max(2, top) / 2)))
    selected = []
    for direction, score_col in (("long", "long_score"), ("short", "short_score")):
        for _, row in ranked.sort_values(score_col, ascending=False).head(each_side).iterrows():
            selected.append((direction, score_col, row))

    out = []
    for direction, score_col, row in selected:
        e = run_entry(row["c"], direction)
        try:
            phase_info = classify_phase(row["df"])
        except Exception:
            phase_info = {"ok": False}
        valid = bool(e.get("valid", False))
        act = ("BUILD_LONG" if valid else "WATCH_LONG") if direction == "long" else ("BUILD_SHORT" if valid else "WATCH_SHORT")
        rationale = (
            f"markup-readiness {round(row['mr'])} · RS {round(row['rs'] * 100)}%"
            if direction == "long"
            else f"distribution context {row['phase']} · RS {round(row['rs'] * 100)}%"
        )
        if phase_info.get("ok"):
            rationale += f" · {phase_info.get('phase')} {phase_info.get('confidence')}%"
        out.append({
            "tk": row["tk"], "act": act, "dir": direction,
            "conv": round(float(row[score_col]) * 100),
            "e": round(e.get("entry_px"), 2) if e.get("entry_px") else None,
            "s": round(e.get("stop"), 2) if e.get("stop") else None,
            "t": round(e.get("target"), 2) if e.get("target") else None,
            "rr": round(e.get("rr"), 2) if e.get("rr") else None,
            "ty": "PRICE-CONTEXT", "gm": e.get("gamma_regime", ""), "valid": valid,
            "warn": e.get("warning", ""), "phase": phase_info.get("phase") if phase_info.get("ok") else row["phase"],
            "phase_conf": phase_info.get("confidence") if phase_info.get("ok") else None,
            "why": rationale,
        })

    # Keep the strongest unique ticker+direction rows.  A ticker may legitimately appear on both
    # sides while posture is neutral; the market gate determines whether either becomes actionable.
    out.sort(key=lambda x: float(x.get("conv") or 0), reverse=True)
    return out[: max(2, top)]
