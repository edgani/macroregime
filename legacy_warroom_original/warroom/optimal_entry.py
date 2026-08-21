"""warroom/optimal_entry.py — consolidated OPTIMAL-ENTRY view (the original design centerpiece).

The selection/macro/theme layers answer WHAT to trade and WHY. This answers WHERE to enter the
names worth entering — it pulls every tagged setup across all asset classes (each already carries
Hedgeye TRADE/TREND/TAIL risk-range levels + entry/stop/target + anti-FOMO timing), scores ENTRY
QUALITY (is this a good entry NOW, not just a good name), and ranks. Four sources, all surfaced:

  1. From selection — names that are beta-play QUALIFIES or theme-graph bridges (the funnel output).
  2. Top entry-quality cross-asset — best entries regardless of theme (US/crypto/commo/fx/IDX).
  3. Combined — selection-funnelled, then ranked by entry quality.
  4. Manual watchlist — your own tickers, analyzed live (render layer).

Entry quality = WHERE price sits in its TRADE range relative to the trade direction (a Long near the
lower band has room; a Long stretched to the upper band is FOMO) blended with the anti-FOMO timing
verdict. Everything here is the same risk-range + timing engines you already run — just consolidated,
cross-referenced, and ranked. Validate the weights (0.6 location / 0.4 timing) like every other prior.
"""
from __future__ import annotations
import numpy as np, pandas as pd


def _rr(df, t):
    try:
        from gcfis.engines.risk_range_hedgeye import compute_risk_range
        return compute_risk_range(df, t)
    except Exception:
        px = float(df["Close"].iloc[-1])
        return {"trade": {"lrr": round(px * .97, 2), "trr": round(px * 1.03, 2)},
                "trend": {"lrr": round(px * .94, 2), "trr": round(px * 1.06, 2)}, "vol_state": ""}


def _timing_factor(timing):
    et = ((timing or {}).get("entry_timing") or "").upper()
    if "EARLY" in et:
        return 1.0, "EARLY"
    if "LATE" in et or "FOMO" in et:
        return 0.30, "LATE"
    if "ON" in et:  # ON-TIME / ON TIME
        return 0.65, "ON-TIME"
    return 0.55, "—"


def quality(direction, lrr, trr, close, timing):
    """0–100 entry quality + one-line rationale. Location vs direction blended with timing."""
    if not (lrr and trr and close) or trr <= lrr:
        return None, ""
    pos = max(0.0, min(1.0, (close - lrr) / (trr - lrr)))   # 0 = at LRR, 1 = at TRR
    if direction == "Long":
        loc_q, loc_txt = 1.0 - pos, f"near LRR (loc {pos:.2f})" if pos < 0.4 else (f"stretched to TRR (loc {pos:.2f}) — FOMO" if pos > 0.7 else f"mid-range (loc {pos:.2f})")
    elif direction == "Short":
        loc_q, loc_txt = pos, f"near TRR (loc {pos:.2f})" if pos > 0.6 else (f"stretched to LRR (loc {pos:.2f}) — late" if pos < 0.3 else f"mid-range (loc {pos:.2f})")
    else:
        loc_q, loc_txt = 1.0 - abs(pos - 0.5) * 2, f"watch (loc {pos:.2f})"
    tf, tf_txt = _timing_factor(timing)
    q = int(round(100 * (0.6 * loc_q + 0.4 * tf)))
    return q, f"{loc_txt} · timing {tf_txt}"


def _rr_ratio(direction, px, stop, target):
    try:
        if direction == "Long" and stop and target and px > stop:
            return round((target - px) / (px - stop), 2)
        if direction == "Short" and stop and target and stop > px:
            return round((px - target) / (stop - px), 2)
    except Exception:
        pass
    return None


def _row_from_setup(s, market, sel_set, bridge_set):
    direction = s.get("_dir", "")
    lrr, trr, close = s.get("lrr"), s.get("trr"), s.get("close") or s.get("px")
    q, why = quality(direction, lrr, trr, close, s.get("timing"))
    if q is None:
        return None
    tkr = s["ticker"]
    src = []
    if tkr in sel_set:
        src.append("beta-play")
    if tkr in bridge_set:
        src.append("bridge")
    return {"ticker": tkr, "market": market, "direction": direction, "px": s.get("px"),
            "lrr": lrr, "trr": trr, "entry": s.get("entry"), "stop": s.get("stop"), "target": s.get("target"),
            "rr_ratio": _rr_ratio(direction, close, s.get("stop"), s.get("target")),
            "timing": ((s.get("timing") or {}).get("entry_timing") or ""), "quality": q, "why": why,
            "from_selection": bool(src), "source": "+".join(src) if src else "screen"}


def _selection_sets(d):
    sel = set()
    for theme, info in (d.get("beta_plays") or {}).items():
        for tier, rows in (info.get("tiers") or {}).items():
            for x in rows:
                if x.get("verdict") == "QUALIFIES":
                    sel.add(x["ticker"])
    bridge = {b["ticker"] for b in (d.get("theme_graph") or {}).get("bridges", [])}
    return sel, bridge


def gather(d):
    sel, bridge = _selection_sets(d)
    markets = [("us_lens", "US"), ("crypto", "Crypto"), ("commo", "Commodities"), ("fx", "FX"), ("idx", "IHSG")]
    rows = []
    for key, label in markets:
        for s in (d.get(key, {}).get("setups") or []):
            r = _row_from_setup(s, label, sel, bridge)
            if r:
                rows.append(r)
    rows.sort(key=lambda x: -x["quality"])
    from_sel = [r for r in rows if r["from_selection"]]
    actionable = [r for r in rows if r["direction"] in ("Long", "Short")]
    return {"from_selection": from_sel[:12], "top_quality": actionable[:12],
            "combined": (sorted(from_sel, key=lambda x: -x["quality"])[:12] or actionable[:12]),
            "sel_count": len(sel), "bridge_count": len(bridge), "n_total": len(rows)}


def analyze_watchlist(tickers, loader=None):
    """Live analysis for a manual watchlist — loads tickers, computes risk range + timing + quality."""
    if loader is None:
        from warroom import data as D
        loader = D.load
    try:
        from warroom import timing as TIM
    except Exception:
        TIM = None
    px, _ = loader(list(tickers))
    out = []
    for t in tickers:
        df = px.get(t)
        if df is None or len(df) < 60:
            out.append({"ticker": t, "error": "no data / too short"})
            continue
        rr = _rr(df, t)
        c = df["Close"]
        close = float(c.iloc[-1])
        lrr, trr = rr["trade"]["lrr"], rr["trade"]["trr"]
        tl, th = rr.get("trend", {}).get("lrr"), rr.get("trend", {}).get("trr")
        sma50 = float(c.rolling(50).mean().iloc[-1]) if len(c) >= 50 else close
        direction = "Long" if close >= sma50 else "Short"
        if direction == "Long":
            stop, target = lrr, (th or trr)
        else:
            stop, target = trr, (tl or lrr)
        tm = None
        if TIM is not None:
            try:
                tm = TIM.assess(t, df, direction, close, stop, target, rr, None)
            except Exception:
                tm = None
        q, why = quality(direction, lrr, trr, close, tm if isinstance(tm, dict) else None)
        out.append({"ticker": t, "market": "manual", "direction": direction, "px": round(close, 2),
                    "lrr": lrr, "trr": trr, "entry": f"{round(close,2)}", "stop": round(stop, 2), "target": round(target, 2),
                    "rr_ratio": _rr_ratio(direction, close, stop, target),
                    "timing": (tm or {}).get("entry_timing", "") if isinstance(tm, dict) else "",
                    "quality": q or 0, "why": why, "source": "manual"})
    out.sort(key=lambda x: -(x.get("quality") or 0))
    return out
