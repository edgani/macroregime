"""wr/internals.py — Market Internals (ported from V40, kept only the OHLCV-computable parts).

Advisor lu (doc 22-23) bilang Breadth/Internals + Market Mode + Change Detection jangan dibuang. Ketiganya
BISA dihitung dari close panel (ga butuh data berbayar) — jadi gw tarik dari V40 ke lean. Bagian yang
butuh options/dealer-gamma (di V40) di-default netral & ditandai, ga dikarang.

JUJUR: ini internals/correlation (deskriptif), BUKAN sinyal kausal teruji. Breadth-thrust & vol-break
punya literatur edge, tapi status di sini RESEARCH sampai divalidasi di data lu (certify bisa nambah).
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def _panel(us_prices, min_len=60):
    """Self-contained close-panel builder (robust to MultiIndex/scalar/empty)."""
    series = {}
    for t, d in (us_prices or {}).items():
        if d is None or len(d) <= min_len or "Close" not in getattr(d, "columns", []):
            continue
        c = d["Close"]
        if getattr(c, "ndim", 1) > 1:
            c = c.iloc[:, 0]
        c = pd.to_numeric(c, errors="coerce").dropna()
        if len(c) > min_len:
            series[t] = c
    return pd.DataFrame(series) if series else pd.DataFrame()


def breadth(close_panel):
    """Advance-decline, % above 50/200MA, new highs/lows, top-5 concentration. From the US universe."""
    if not isinstance(close_panel, pd.DataFrame) or close_panel.shape[1] < 5 or len(close_panel) < 200:
        return None
    last = close_panel.iloc[-1]
    ma50 = close_panel.rolling(50).mean().iloc[-1]
    ma200 = close_panel.rolling(200).mean().iloc[-1]
    above50 = float((last > ma50).mean()) * 100
    above200 = float((last > ma200).mean()) * 100
    # advance-decline over last 5 days
    chg5 = close_panel.iloc[-1] / close_panel.iloc[-6] - 1
    adv = int((chg5 > 0).sum()); dec = int((chg5 < 0).sum())
    # new 52wk highs/lows
    hi52 = close_panel.rolling(252).max().iloc[-1]; lo52 = close_panel.rolling(252).min().iloc[-1]
    new_hi = int((last >= hi52 * 0.99).sum()); new_lo = int((last <= lo52 * 1.01).sum())
    # concentration: top-5 momentum share (are gains narrow or broad?)
    mom = (close_panel.iloc[-1] / close_panel.iloc[-63] - 1).dropna()
    pos = mom[mom > 0]
    top5_share = float(pos.nlargest(5).sum() / pos.sum() * 100) if len(pos) and pos.sum() > 0 else None
    # verdict
    if above50 > 65 and adv > dec * 1.5:
        state, col = "broad strength", "grn"
    elif above50 < 35 and dec > adv * 1.5:
        state, col = "broad weakness", "red"
    elif top5_share and top5_share > 60:
        state, col = "narrow (concentration risk)", "amb"
    else:
        state, col = "mixed", "gry"
    return {"above_50ma_pct": round(above50, 0), "above_200ma_pct": round(above200, 0),
            "advancers": adv, "decliners": dec, "new_highs": new_hi, "new_lows": new_lo,
            "top5_momentum_share": round(top5_share, 0) if top5_share else None,
            "state": state, "color": col,
            "note": "breadth from your universe — narrow leadership (high top-5 share) is a late-cycle tell; broad participation confirms trend"}


def market_mode(close_panel):
    """PINNING/EXPANSION/SQUEEZE/DISTRIBUTION from price+breadth (options/gamma parts neutral — no paid data)."""
    if not isinstance(close_panel, pd.DataFrame) or len(close_panel) < 70:
        return None
    spx = close_panel.mean(axis=1)
    r = np.log(spx).diff()
    s10, s30 = float(r.tail(10).std() or 0), float(r.tail(30).std() or 1e-9)
    vol_rising = s10 > 1.2 * s30
    rng10 = float(spx.tail(10).max() - spx.tail(10).min()); rng60 = float(spx.tail(60).max() - spx.tail(60).min() or 1e-9)
    compressed = (rng10 / rng60) < 0.30
    ret20z = float(r.tail(20).sum() / (np.sqrt(20) * s30 + 1e-9)); trending = abs(ret20z) > 1.0
    b = breadth(close_panel) or {}
    narrow = (b.get("top5_momentum_share") or 0) > 60
    if narrow and ret20z > 0 and not vol_rising:
        mode, style, col = "DISTRIBUTION", "reduce / avoid — narrow, upside reactions weak", "amb"
    elif vol_rising and trending:
        mode, style, col = "EXPANSION", "momentum — continuation valid, add on acceptance", "grn"
    elif compressed and not trending:
        mode, style, col = "PINNING", "range — fade extremes, don't chase breakouts", "gry"
    elif (b.get("above_50ma_pct") or 50) < 25 and ret20z > 0.8:
        mode, style, col = "SQUEEZE", "oversold bounce — position before the chase", "inf"
    else:
        mode, style, col = "MIXED", "no dominant mode — lower aggression", "gry"
    return {"mode": mode, "style": style, "color": col, "trend_z": round(ret20z, 2),
            "vol_rising": bool(vol_rising), "compressed": bool(compressed),
            "note": "market mode from price + breadth. Dealer-gamma refinement needs options data (your feed) — omitted, not faked."}


def change_detection(close_panel):
    """Correlation-regime shift + volatility break — early warning that market STRUCTURE is changing."""
    if not isinstance(close_panel, pd.DataFrame) or close_panel.shape[1] < 8 or len(close_panel) < 130:
        return None
    rets = close_panel.pct_change().dropna()
    if len(rets) < 130:
        return None
    # avg pairwise correlation: recent vs baseline (rising corr = risk-off / crowding)
    recent = rets.tail(21).corr().values; base = rets.tail(126).corr().values
    def _avg_offdiag(m):
        n = m.shape[0]; s = (np.nansum(m) - n) / (n * n - n) if n > 1 else 0
        return float(s)
    corr_recent, corr_base = _avg_offdiag(recent), _avg_offdiag(base)
    corr_shift = corr_recent - corr_base
    # vol break: recent realized vol vs 6mo
    spx = close_panel.mean(axis=1); rv = spx.pct_change()
    vol_recent = float(rv.tail(21).std() * np.sqrt(252)); vol_base = float(rv.tail(126).std() * np.sqrt(252))
    vol_break = vol_recent / vol_base - 1 if vol_base else 0
    flags = []
    if corr_shift > 0.15:
        flags.append("correlations spiking (crowding / risk-off — diversification failing)")
    if vol_break > 0.4:
        flags.append("volatility regime breaking higher (stress building)")
    if corr_shift < -0.15:
        flags.append("correlations falling (stock-picking regime returning)")
    return {"avg_correlation": round(corr_recent, 2), "correlation_shift": round(corr_shift, 2),
            "vol_recent_annualized": round(vol_recent * 100, 0), "vol_change_pct": round(vol_break * 100, 0),
            "flags": flags or ["no structural break detected"],
            "state": "STRUCTURE SHIFTING" if flags and "no structural" not in flags[0] else "stable",
            "color": "red" if (corr_shift > 0.15 or vol_break > 0.4) else "grn",
            "note": "rising correlation + vol break = market structure changing before price fully reflects it (regime early-warning)"}


def run_internals(us_prices):
    cp = _panel(us_prices, 60)
    if cp is None or cp.empty:
        return {"breadth": None, "market_mode": None, "change_detection": None}
    return {"breadth": breadth(cp), "market_mode": market_mode(cp), "change_detection": change_detection(cp)}
