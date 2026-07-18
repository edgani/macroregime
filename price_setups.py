"""Price-signal fallback using REAL OHLCV and fail-closed level geometry."""
from __future__ import annotations
import math
import numpy as np
import pandas as pd


def _numeric(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def price_signal_setups(ohlcv, top=12):
    """Return ranked real-data setup rows. Malformed levels never receive valid=True."""
    from engines import bandarmetrics_engine as BM
    from gcfis.engines.entry import run_entry
    from engines.inventory_transfer_engine import classify_phase

    rows = []
    for ticker, frame in (ohlcv or {}).items():
        try:
            frame = pd.DataFrame(frame).dropna().copy()
            frame.columns = [str(column).title() for column in frame.columns]
            if len(frame) < 200 or "Close" not in frame.columns:
                continue
            close = pd.to_numeric(frame["Close"], errors="coerce").dropna()
            if len(close) < 200:
                continue
            rs = float(close.iloc[-1] / close.iloc[-252] - 1) if len(close) > 252 else float(close.iloc[-1] / close.iloc[0] - 1)
            bm = BM.compute(frame)
            readiness = bm.get("markup_readiness")
            readiness = readiness.get("readiness") if isinstance(readiness, dict) else readiness
            accumulation = 1.0 if bm.get("stealth_accumulation", {}).get("is_stealth") else 0.0
            readiness = _numeric(readiness)
            if readiness is None:
                continue
            rows.append({"tk": ticker, "rs": rs, "mr": readiness, "acc": accumulation, "c": close, "df": frame})
        except Exception:
            continue
    if not rows:
        return []

    ranked = pd.DataFrame(rows)
    ranked["score"] = 0.45 * ranked["mr"].rank(pct=True) + 0.35 * ranked["rs"].rank(pct=True) + 0.20 * ranked["acc"]
    ranked = ranked.sort_values("score", ascending=False).head(top)

    output = []
    for _, row in ranked.iterrows():
        entry = run_entry(row["c"], "long", ohlcv=row["df"], ticker=row["tk"])
        try:
            phase = classify_phase(row["df"])
        except Exception:
            phase = {"ok": False}
        entry_px, stop, target = map(_numeric, (entry.get("entry_px"), entry.get("stop"), entry.get("target")))
        geometry_ok = all(value is not None for value in (entry_px, stop, target)) and stop < entry_px < target
        valid = bool(entry.get("valid")) and geometry_ok
        warning = str(entry.get("warning") or "")
        if not geometry_ok:
            warning = (warning + "; " if warning else "") + "malformed levels quarantined"
        raw_source = str(entry.get("rr_source", "UNAVAILABLE"))
        safe_source = "MQA_RISK_RANGE_PROXY" if "hedgeye" in raw_source.lower() else raw_source
        try:
            as_of = str(pd.Timestamp(row["df"].index[-1]).date())
        except Exception:
            as_of = None
        output.append({
            "tk": row["tk"],
            "act": "WATCH_LONG" if valid else "WATCH",
            "dir": "long",
            "conv": round(float(row["score"]) * 100),
            "score_label": "SETUP_SCORE",
            "e": entry_px,
            "s": stop,
            "t": target,
            "rr": _numeric(entry.get("rr")),
            "ty": "PRICE-SIGNAL",
            "gm": entry.get("gamma_regime", ""),
            "valid": valid,
            "warn": warning,
            "phase": phase.get("phase") if phase.get("ok") else None,
            "phase_conf": phase.get("confidence") if phase.get("ok") else None,
            "why": f"markup-readiness {round(row['mr'])} · RS {round(row['rs'] * 100)}%" + (f" · {phase['phase']} {phase['confidence']}%" if phase.get("ok") else ""),
            "level_source": safe_source,
            "stop_basis": "RISK_RANGE_INVALIDATION" if "risk_range" in raw_source.lower() else "VOLATILITY_FALLBACK",
            "target_basis": "TACTICAL_RESPONSE_ZONE" if "risk_range" in raw_source.lower() else "VOLATILITY_FALLBACK",
            "structural_target": None,
            "data_quality": "DAILY_OHLC_SNAPSHOT",
            "evidence_family": "PRICE_RS",
            "as_of": as_of,
            "price_decimals": entry.get("price_decimals"),
        })
    return output
