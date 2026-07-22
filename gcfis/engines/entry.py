"""entry.py — L13 Entry Engine. GCFIS: Entry = 0.25*Trend+0.25*Momentum+0.20*Dealer+0.15*Liquidity
+0.15*Structure. Classifies Breakout/Pullback/Continuation/Mean-Reversion, GAMMA-AWARE:
  GEX<0 (momentum regime) -> Breakout/Continuation valid (dealers amplify)
  GEX>0 (mean-reversion regime) -> Pullback/Mean-Reversion valid (dealers fade)
Risk-range (Hedgeye-style) gives stop & target -> R/R. Wrong-regime entries are flagged INVALID."""
from __future__ import annotations
import numpy as np, pandas as pd
from ..core.change_core import robust_z, last



def _round_px(value: float) -> float:
    """Preserve meaningful precision for low-priced crypto/FX instruments."""
    x = float(value)
    a = abs(x)
    digits = 2 if a >= 100 else 4 if a >= 1 else 6 if a >= 0.01 else 8
    return round(x, digits)

def _rsi(px: pd.Series, n: int = 14) -> float:
    d = px.diff(); up = d.clip(lower=0).rolling(n).mean(); dn = (-d.clip(upper=0)).rolling(n).mean()
    return last(100 - 100 / (1 + up / dn.replace(0, np.nan)), 50)

def _atr(px: pd.Series, n: int = 14) -> float:
    return last(px.diff().abs().rolling(n).mean(), px.std() * 0.02)  # close-only ATR proxy (FALLBACK only)

def _true_atr(ohlcv, n: int = 14) -> float | None:
    """Real Wilder ATR from high/low/close — true range, catches gaps. The close-only _atr misses both."""
    try:
        import pandas as _pd
        d = _pd.DataFrame(ohlcv); d.columns = [str(c).lower() for c in d.columns]
        h, l, c = d["high"].astype(float), d["low"].astype(float), d["close"].astype(float)
        pc = c.shift(1)
        tr = _pd.concat([h - l, (h - pc).abs(), (l - pc).abs()], axis=1).max(axis=1)
        v = float(tr.ewm(alpha=1 / n, adjust=False).mean().iloc[-1])
        return v if v > 0 else None
    except Exception:
        return None

def _hedgeye_range(ohlcv, ticker=None) -> dict | None:
    """The REAL Hedgeye risk range (Wilder true-range on high/low, TRADE/TREND durations, no-repaint).
    Returns {trade:{lrr,trr}, trend:{lrr,trr}, ...} or None when OHLC isn't available."""
    if ohlcv is None:
        return None
    try:
        import pandas as _pd
        d = _pd.DataFrame(ohlcv)
        d.columns = [str(c).lower() for c in d.columns]
        if not {"open", "high", "low", "close"}.issubset(d.columns) or len(d) < 60:
            return None
        from .risk_range_hedgeye import compute_risk_range
        rr = compute_risk_range(d, ticker)
        t = (rr or {}).get("trade") or {}
        if t.get("lrr") and t.get("trr") and t["trr"] > t["lrr"]:
            return rr
    except Exception:
        pass
    return None

def run_entry(price: pd.Series, direction: str, dealer: dict | None = None,
              liquidity_score: float = 50.0, k_atr: float = 2.0, rr_min: float = 1.5, long_only: bool = False,
              ohlcv=None, ticker: str | None = None) -> dict:
    px = pd.to_numeric(pd.Series(price), errors="coerce").dropna()
    if len(px) < 60:
        return {"ok": False, "reason": "insufficient history"}
    if long_only and direction == "short":          # buy-only market: a bearish read is WAIT/reduce, never a short
        return {"ok": True, "entry_type": "AVOID", "valid": False,
                "gamma_regime": (dealer or {}).get("regime", "unknown"),
                "warning": "long-only market — bearish/distribution, no short (WAIT or reduce if holding)",
                "entry_px": 0.0, "stop": 0.0, "target": 0.0, "rr": 0.0, "entry_score": 0.0}
    p = float(px.iloc[-1]); sma50 = px.rolling(50).mean().iloc[-1]; sma200 = px.rolling(200).mean().iloc[-1] if len(px) >= 200 else sma50
    hi20, lo20 = px.tail(20).max(), px.tail(20).min()
    pos = (p - lo20) / (hi20 - lo20) if hi20 > lo20 else 0.5
    ref = px.tail(20).mean(); sigma = px.pct_change().tail(20).std() * ref or (px.std() * 0.02)
    atr = _atr(px); rsi = _rsi(px)

    trend = float(np.tanh((p / sma50 - 1) * 10) + np.sign(sma50 - sma200) * 0.3)
    mom = float(np.tanh((rsi - 50) / 20))
    raw_dsign = (dealer or {}).get("gex_sign")
    dsign = float(raw_dsign) if raw_dsign in (-1, 1, -1.0, 1.0) else 0.0
    gregime = str((dealer or {}).get("regime", "unknown"))
    # Dealer contribution is zero unless contract-level dealer sign is explicitly supplied.
    dealer_contrib = dsign * (1 if direction == "long" else -1) * -1
    liq = (liquidity_score - 50) / 50.0
    structure = float((pos - 0.5) * 2) if direction == "long" else float((0.5 - pos) * 2)
    entry_score = 0.25 * trend + 0.25 * mom + 0.20 * dealer_contrib + 0.15 * liq + 0.15 * structure

    near_hi, near_lo = pos > 0.8, pos < 0.2
    breaking = p >= hi20 * 0.999
    if direction == "long":
        if gregime in {"momentum", "amplification_context"} and breaking: etype = "BREAKOUT"
        elif gregime in {"momentum", "amplification_context"} and trend > 0: etype = "CONTINUATION"
        elif gregime in {"mean_reversion", "mean_reversion_context"} and near_lo and rsi < 38: etype = "MEAN_REVERSION"
        elif gregime in {"mean_reversion", "mean_reversion_context"} and near_lo: etype = "PULLBACK"
        elif breaking: etype = "BREAKOUT"
        elif near_lo: etype = "PULLBACK"
        else: etype = "CONTINUATION"
    else:  # short
        if gregime in {"momentum", "amplification_context"} and p <= lo20 * 1.001: etype = "BREAKDOWN"
        elif gregime in {"momentum", "amplification_context"} and trend < 0: etype = "CONTINUATION"
        elif gregime in {"mean_reversion", "mean_reversion_context"} and near_hi and rsi > 62: etype = "MEAN_REVERSION"
        elif gregime in {"mean_reversion", "mean_reversion_context"} and near_hi: etype = "BOUNCE_SHORT"
        elif p <= lo20 * 1.001: etype = "BREAKDOWN"
        elif near_hi: etype = "BOUNCE_SHORT"
        else: etype = "CONTINUATION"

    # gamma-validity: breakout/continuation need momentum regime; pullback/mean-rev need mean-rev regime
    trend_types = {"BREAKOUT", "BREAKDOWN", "CONTINUATION"}
    valid = True; warn = ""
    if gregime in {"mean_reversion", "mean_reversion_context"} and etype in trend_types:
        valid = False; warn = "trend entry conflicts with explicit positive-gamma context"
    if gregime in {"momentum", "amplification_context"} and etype in {"PULLBACK", "MEAN_REVERSION", "BOUNCE_SHORT"}:
        warn = "fade conflicts with explicit negative-gamma context"

    # ── stop/target: RISK-RANGE driven (thesis boundary), ATR only as fallback when no OHLC ──
    hrr = _hedgeye_range(ohlcv, ticker)
    if hrr:
        rr_src = "hedgeye_risk_range"
        lrr, trr = float(hrr["trade"]["lrr"]), float(hrr["trade"]["trr"])     # TRADE = tactical entry zone
        tl = (hrr.get("trend") or {})
        tlrr, ttrr = float(tl.get("lrr") or lrr), float(tl.get("trr") or trr)  # TREND = thesis boundary
        band = max(trr - lrr, 1e-9)
        # true ATR (Wilder, uses high/low → real range incl. gaps) as the NOISE FLOOR for the stop:
        # a stop tighter than daily noise gets hit even when the thesis is intact.
        atr_true = _true_atr(ohlcv) or atr
        # Stop AND target must come from the SAME duration or R/R is structurally broken.
        # TRADE = the tactical thesis: the trade is wrong when price leaves the TRADE range.
        # The ATR floor stops the band from producing a noise-tight stop; TREND is kept as context only.
        if direction == "long":
            fade = etype in {"PULLBACK", "MEAN_REVERSION"}
            entry_px = min(p, lrr + 0.25 * band) if fade else p
            thesis_stop = lrr - 0.10 * band                   # price out of the TRADE range = setup invalid
            noise_floor = entry_px - 1.0 * atr_true           # never tighter than one true-ATR of noise
            stop = min(thesis_stop, noise_floor)
            target = trr if fade else max(trr, ttrr) + 1.0 * band   # fade→range top; breakout→extension
        else:
            fade = etype in {"BOUNCE_SHORT", "MEAN_REVERSION"}
            entry_px = max(p, trr - 0.25 * band) if fade else p
            thesis_stop = trr + 0.10 * band
            noise_floor = entry_px + 1.0 * atr_true
            stop = max(thesis_stop, noise_floor)
            target = lrr if fade else min(lrr, tlrr) - 1.0 * band
        risk_range_out = [_round_px(lrr), _round_px(trr)]
    else:
        rr_src = "atr_fallback (no OHLC — close-only proxy, stop is vol-based not thesis-based)"
        if direction == "long":
            if etype in {"PULLBACK", "MEAN_REVERSION"}:
                entry_px = min(p, ref - 0.5 * sigma); stop = entry_px - k_atr * atr; target = ref + 1.0 * sigma
            else:
                entry_px = p; stop = p - k_atr * atr; target = p + 2.0 * sigma
        else:
            if etype in {"BOUNCE_SHORT", "MEAN_REVERSION"}:
                entry_px = max(p, ref + 0.5 * sigma); stop = entry_px + k_atr * atr; target = ref - 1.0 * sigma
            else:
                entry_px = p; stop = p + k_atr * atr; target = p - 2.0 * sigma
        risk_range_out = [_round_px(ref - sigma), _round_px(ref + sigma)]
    risk = abs(entry_px - stop); reward = abs(target - entry_px)
    rr = round(reward / risk, 2) if risk > 0 else 0.0
    if rr < rr_min: valid = False; warn = (warn + "; " if warn else "") + f"R/R {rr} < {rr_min}"
    return {"ok": True, "entry_type": etype, "entry_score": round(float(np.clip(entry_score, -1, 1)), 2),
            "gamma_regime": gregime, "valid": bool(valid), "warning": warn,
            "entry_px": _round_px(entry_px), "stop": _round_px(stop), "target": _round_px(target),
            "rr": rr, "rsi": round(rsi, 1), "risk_range": risk_range_out, "rr_source": rr_src}
