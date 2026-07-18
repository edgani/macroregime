"""entry.py — L13 Entry Engine. GCFIS: Entry = 0.25*Trend+0.25*Momentum+0.20*Dealer+0.15*Liquidity
+0.15*Structure. Classifies Breakout/Pullback/Continuation/Mean-Reversion, GAMMA-AWARE:
  GEX<0 (momentum regime) -> Breakout/Continuation valid (dealers amplify)
  GEX>0 (mean-reversion regime) -> Pullback/Mean-Reversion valid (dealers fade)
Risk-range (Hedgeye-style) gives stop & target -> R/R. Wrong-regime entries are flagged INVALID."""
from __future__ import annotations
import numpy as np, pandas as pd
from ..core.change_core import robust_z, last

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
    """Internal MQA risk-range proxy using OHLC true range and frozen TRADE/TREND durations.
    It is not claimed to be the proprietary Hedgeye calculation.
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
    dsign = (dealer or {}).get("gex_sign", 0); gregime = (dealer or {}).get("regime", "unknown")
    # dealer contribution is direction-aware: momentum regime helps trend entries, mean-rev helps fades
    dealer_contrib = float(dsign) * (1 if direction == "long" else -1) * -1  # GEX<0 (momentum) aids trend
    liq = (liquidity_score - 50) / 50.0
    structure = float((pos - 0.5) * 2) if direction == "long" else float((0.5 - pos) * 2)
    entry_score = 0.25 * trend + 0.25 * mom + 0.20 * dealer_contrib + 0.15 * liq + 0.15 * structure

    near_hi, near_lo = pos > 0.8, pos < 0.2
    breaking = p >= hi20 * 0.999
    if direction == "long":
        if gregime == "momentum" and breaking: etype = "BREAKOUT"
        elif gregime == "momentum" and trend > 0: etype = "CONTINUATION"
        elif gregime == "mean_reversion" and near_lo and rsi < 38: etype = "MEAN_REVERSION"
        elif gregime == "mean_reversion" and near_lo: etype = "PULLBACK"
        elif breaking: etype = "BREAKOUT"
        elif near_lo: etype = "PULLBACK"
        else: etype = "CONTINUATION"
    else:  # short
        if gregime == "momentum" and p <= lo20 * 1.001: etype = "BREAKDOWN"
        elif gregime == "momentum" and trend < 0: etype = "CONTINUATION"
        elif gregime == "mean_reversion" and near_hi and rsi > 62: etype = "MEAN_REVERSION"
        elif gregime == "mean_reversion" and near_hi: etype = "BOUNCE_SHORT"
        elif p <= lo20 * 1.001: etype = "BREAKDOWN"
        elif near_hi: etype = "BOUNCE_SHORT"
        else: etype = "CONTINUATION"

    # gamma-validity: breakout/continuation need momentum regime; pullback/mean-rev need mean-rev regime
    trend_types = {"BREAKOUT", "BREAKDOWN", "CONTINUATION"}
    valid = True; warn = ""
    if gregime == "mean_reversion" and etype in trend_types:
        valid = False; warn = "breakout in positive-gamma (dealers fade) — likely to fail"
    if gregime == "momentum" and etype in {"PULLBACK", "MEAN_REVERSION", "BOUNCE_SHORT"}:
        warn = "fading a negative-gamma (momentum) tape — risky"

    # ── stop/target: RISK-RANGE driven (thesis boundary), ATR only as fallback when no OHLC ──
    hrr = _hedgeye_range(ohlcv, ticker)
    if hrr:
        rr_src = "mqa_risk_range_proxy"
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
            thesis_stop = lrr - 0.10 * band
            noise_floor = entry_px - 1.0 * atr_true
            stop = min(thesis_stop, noise_floor)
            # A continuation/breakout target must remain above the current executable entry,
            # even when price has already moved beyond yesterday's frozen range.
            target = trr if fade else max(entry_px + band, max(trr, ttrr) + band)
        else:
            fade = etype in {"BOUNCE_SHORT", "MEAN_REVERSION"}
            entry_px = max(p, trr - 0.25 * band) if fade else p
            thesis_stop = trr + 0.10 * band
            noise_floor = entry_px + 1.0 * atr_true
            stop = max(thesis_stop, noise_floor)
            target = lrr if fade else min(entry_px - band, min(lrr, tlrr) - band)
        risk_range_out = [round(lrr, 2), round(trr, 2)]
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
        risk_range_out = [round(ref - sigma, 2), round(ref + sigma, 2)]
    # Directional geometry is part of validity. The old code used absolute distances,
    # so a target below a long entry could still report a positive R/R and valid=True.
    finite = all(np.isfinite(float(v)) for v in (entry_px, stop, target))
    if direction == "long":
        direction_ok = finite and float(stop) < float(entry_px) < float(target)
        risk = float(entry_px) - float(stop) if direction_ok else 0.0
        reward = float(target) - float(entry_px) if direction_ok else 0.0
    else:
        direction_ok = finite and float(target) < float(entry_px) < float(stop)
        risk = float(stop) - float(entry_px) if direction_ok else 0.0
        reward = float(entry_px) - float(target) if direction_ok else 0.0
    if not direction_ok:
        valid = False
        warn = (warn + "; " if warn else "") + "directional level invariant failed"
    rr = round(reward / risk, 2) if risk > 0 else 0.0
    if rr < rr_min:
        valid = False
        warn = (warn + "; " if warn else "") + f"R/R {rr} < {rr_min}"

    # Adaptive precision prevents sub-$1 assets from collapsing entry/stop/target to
    # the same two-decimal value. Keep enough decimals to preserve strict ordering.
    def _round_levels(values):
        scale = max(abs(float(v)) for v in values if np.isfinite(float(v)))
        start = 2 if scale >= 10 else (4 if scale >= 1 else 6)
        for decimals in range(start, 9):
            rounded = tuple(round(float(v), decimals) for v in values)
            if len(set(rounded)) == len(rounded):
                return rounded, decimals
        return tuple(round(float(v), 8) for v in values), 8
    (entry_out, stop_out, target_out), price_decimals = _round_levels((entry_px, stop, target))
    return {"ok": True, "entry_type": etype, "entry_score": round(float(np.clip(entry_score, -1, 1)), 2),
            "gamma_regime": gregime, "valid": bool(valid), "warning": warn,
            "entry_px": entry_out, "stop": stop_out, "target": target_out,
            "price_decimals": price_decimals,
            "rr": rr, "rsi": round(rsi, 1), "risk_range": risk_range_out, "rr_source": rr_src}
