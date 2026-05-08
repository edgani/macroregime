"""engines/options_engine.py — Options Intelligence Layer

Integrates with Risk Range™ (LRR/TRR) to produce:
- Black-Scholes Greeks (Delta, Gamma, Theta, Vega)
- Max Pain (strike where all options holders lose most)
- Gamma Wall (net gamma exposure by strike)
- OI Heatmap (call/put open interest by strike)
- Implied Move (expected ±% from ATM straddle)
- Entry / TP1 / TP2 / Stop recommendations
- Holding duration estimate
- IV Percentile (current IV vs 52w range)

No scipy dependency — Black-Scholes implemented from math stdlib.
Caches results per ticker. IHSG = skip (no liquid options market).

Usage:
    eng = OptionsEngine()
    result = eng.analyze("XLE", spot=92.0, lrr=88.0, trr=97.0)
"""
from __future__ import annotations

import math
import time
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Risk-free rate (US 3M T-bill proxy, update periodically)
RISK_FREE_RATE: float = 0.052  # 5.2%

# Cache: {ticker: (result_dict, timestamp)}
_CACHE: Dict[str, Tuple[dict, float]] = {}
_CACHE_TTL: float = 3600.0  # 1 hour


# ── Pure Black-Scholes (no scipy) ─────────────────────────────────────────────

def _erf(x: float) -> float:
    """Approximation of error function (Abramowitz & Stegun 7.1.26)."""
    t = 1.0 / (1.0 + 0.3275911 * abs(x))
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 +
           t * (-1.453152027 + t * 1.061405429))))
    result = 1.0 - poly * math.exp(-x * x)
    return result if x >= 0 else -result

def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + _erf(x / math.sqrt(2)))

def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)

def bs_price(S: float, K: float, T: float, r: float, sigma: float,
             opt: str = "call") -> float:
    """Black-Scholes option price."""
    if T <= 1e-8 or sigma <= 1e-8: return max(0.0, (S-K) if opt=="call" else (K-S))
    sq = sigma * math.sqrt(T)
    d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / sq
    d2 = d1 - sq
    if opt == "call":
        return S * _norm_cdf(d1) - K * math.exp(-r * T) * _norm_cdf(d2)
    else:
        return K * math.exp(-r * T) * _norm_cdf(-d2) - S * _norm_cdf(-d1)

def bs_greeks(S: float, K: float, T: float, r: float, sigma: float,
              opt: str = "call") -> Optional[Dict[str, float]]:
    """Compute Black-Scholes Greeks."""
    if T <= 1e-8 or sigma <= 1e-8 or S <= 0 or K <= 0: return None
    try:
        sq = sigma * math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / sq
        d2 = d1 - sq
        nd1  = _norm_pdf(d1)
        nd1c = _norm_cdf(d1)
        nd2c = _norm_cdf(d2)
        price = bs_price(S, K, T, r, sigma, opt)
        if opt == "call":
            delta = nd1c
            theta = (-S * nd1 * sigma / (2 * math.sqrt(T))
                     - r * K * math.exp(-r * T) * nd2c) / 365.0
        else:
            delta = nd1c - 1.0
            theta = (-S * nd1 * sigma / (2 * math.sqrt(T))
                     + r * K * math.exp(-r * T) * _norm_cdf(-d2)) / 365.0
        gamma = nd1 / (S * sq)
        vega  = S * nd1 * math.sqrt(T) / 100.0
        return {
            "price": round(price, 4),
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 4),  # per day
            "vega":  round(vega, 4),
            "d1": round(d1, 4),
            "d2": round(d2, 4),
        }
    except Exception:
        return None


# ── Utility helpers ────────────────────────────────────────────────────────────

def _get_nearest_expiry(expirations: tuple, days_min: int = 7, days_target: int = 35) -> str:
    """Pick expiry closest to target days out, but at least days_min from today."""
    from datetime import datetime, date
    today = date.today()
    best = None; best_diff = 9999
    for exp in expirations:
        try:
            exp_date = datetime.strptime(exp, "%Y-%m-%d").date()
            diff = (exp_date - today).days
            if diff < days_min: continue
            dist = abs(diff - days_target)
            if dist < best_diff: best_diff = dist; best = exp
        except Exception: continue
    return best or (expirations[0] if expirations else "")

def _round_to(val: float, gran: float = 1.0) -> float:
    return round(round(val / gran) * gran, 4)

def _find_key_oi_levels(df: pd.DataFrame, spot: float,
                        side: str, n: int = 3) -> List[float]:
    """Find top n OI strikes above (calls) or below (puts) spot."""
    if df is None or df.empty: return []
    df = df.copy()
    df = df[df["openInterest"] > 0].copy()
    if side == "call":
        df = df[df["strike"] >= spot * 0.95]
    else:
        df = df[df["strike"] <= spot * 1.05]
    df = df.nlargest(n, "openInterest")
    return sorted(df["strike"].tolist())

def _compute_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> Optional[float]:
    """Strike where total intrinsic value of all options is minimized."""
    if calls is None or puts is None: return None
    try:
        strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
        pain: Dict[float, float] = {}
        for s in strikes:
            cp = sum(max(0.0, s - k) * oi
                     for k, oi in zip(calls["strike"], calls["openInterest"]))
            pp = sum(max(0.0, k - s) * oi
                     for k, oi in zip(puts["strike"], puts["openInterest"]))
            pain[s] = cp + pp
        return min(pain, key=pain.get) if pain else None
    except Exception:
        return None

def _compute_gamma_wall(calls: pd.DataFrame, puts: pd.DataFrame,
                        spot: float, r: float, T: float) -> Dict[float, float]:
    """Net gamma by strike — positive = dealers long gamma (vol suppressor)."""
    gw: Dict[float, float] = {}
    if calls is None or puts is None: return gw
    try:
        for _, row in calls.iterrows():
            iv = float(row.get("impliedVolatility", 0))
            if iv <= 0: continue
            g = bs_greeks(spot, float(row["strike"]), T, r, iv, "call")
            if g:
                oi = float(row.get("openInterest", 0))
                gw[row["strike"]] = gw.get(row["strike"], 0) + g["gamma"] * oi * 100.0
        for _, row in puts.iterrows():
            iv = float(row.get("impliedVolatility", 0))
            if iv <= 0: continue
            g = bs_greeks(spot, float(row["strike"]), T, r, iv, "put")
            if g:
                oi = float(row.get("openInterest", 0))
                # Puts: dealers SHORT gamma (they BUY puts) → subtract
                gw[row["strike"]] = gw.get(row["strike"], 0) - g["gamma"] * oi * 100.0
    except Exception as e:
        logger.debug(f"Gamma wall error: {e}")
    return gw

def _implied_move(calls: pd.DataFrame, puts: pd.DataFrame, spot: float) -> Optional[float]:
    """Expected ±% move from ATM straddle (front month)."""
    try:
        atm = _round_to(spot, 5.0)
        c_row = calls[calls["strike"] == atm]
        p_row = puts[puts["strike"] == atm]
        if c_row.empty or p_row.empty:
            # Try nearest strike
            c_row = calls.iloc[(calls["strike"] - atm).abs().argsort().iloc[:1]]
            p_row = puts.iloc[(puts["strike"] - atm).abs().argsort().iloc[:1]]
        c_mid = (float(c_row["bid"].iloc[0]) + float(c_row["ask"].iloc[0])) / 2
        p_mid = (float(p_row["bid"].iloc[0]) + float(p_row["ask"].iloc[0])) / 2
        straddle = c_mid + p_mid
        return round(straddle / spot, 4) if spot > 0 else None
    except Exception:
        return None

def _iv_percentile(hist_iv: Optional[List[float]], current_iv: float) -> Optional[float]:
    """IV percentile vs 52w range (0=cheapest, 1=most expensive)."""
    if not hist_iv or len(hist_iv) < 20: return None
    lo, hi = min(hist_iv), max(hist_iv)
    if hi <= lo: return None
    return round((current_iv - lo) / (hi - lo), 3)


# ── Entry / TP / Stop Logic ────────────────────────────────────────────────────

def _derive_long_levels(spot: float, lrr: float, trr: float,
                        key_puts: List[float], key_calls: List[float],
                        implied_move: Optional[float]) -> Dict:
    """
    Long trade levels combining Risk Range + options OI.

    Entry: Near LRR OR near key put OI support (bullish = buy near put support)
    TP1  : First call OI cluster above entry
    TP2  : TRR or next call OI cluster
    Stop : Below LRR OR below key put support (max -1 implied move from entry)
    Hold : TRADE if near LRR, TREND if confirmed breakout
    """
    # Entry: higher of LRR or highest put support below spot
    put_support = max((k for k in key_puts if k <= spot * 1.01), default=None)
    entry = max(lrr, put_support * 0.99) if put_support else lrr
    entry = round(entry, 2)

    # TP1: first call OI above entry
    call_above = [k for k in key_calls if k > entry]
    tp1 = round(call_above[0], 2) if call_above else round(trr, 2)

    # TP2: TRR or second call OI
    tp2_candidates = [k for k in key_calls if k > tp1]
    tp2 = round(tp2_candidates[0], 2) if tp2_candidates else round(trr * 1.02, 2)
    tp2 = max(tp2, round(trr, 2))

    # Stop: below LRR, with options-derived buffer
    im_pct = implied_move or 0.05
    stop = round(min(lrr * 0.99, entry * (1 - im_pct * 0.8)), 2)

    # R/R
    reward = tp1 - entry
    risk   = entry - stop
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0

    # Holding duration
    if rr_ratio >= 2.0:
        hold = "TREND (≥3mo)"
    elif rr_ratio >= 1.2:
        hold = "TRADE (1-3wk)"
    else:
        hold = "SKIP (poor R/R)"

    # EV score from options perspective
    ev_ok = rr_ratio >= 1.5 and entry <= spot * 1.02

    return {
        "side": "LONG",
        "entry": entry,
        "tp1": tp1,
        "tp2": tp2,
        "stop": stop,
        "rr": rr_ratio,
        "holding": hold,
        "ev_ok": ev_ok,
        "put_support": put_support,
        "call_resistance": call_above[0] if call_above else None,
    }

def _derive_short_levels(spot: float, lrr: float, trr: float,
                         key_puts: List[float], key_calls: List[float],
                         implied_move: Optional[float]) -> Dict:
    """
    Short trade levels. Sell near TRR or call OI resistance.
    Entry: Near TRR OR key call OI cluster above spot
    TP1  : First put OI cluster below entry
    TP2  : LRR or next put OI cluster
    Stop : Above TRR or above call resistance (max +1 implied move)
    """
    call_resist = min((k for k in key_calls if k >= spot * 0.99), default=None)
    entry = min(trr, call_resist * 1.01) if call_resist else trr
    entry = round(entry, 2)

    put_below = [k for k in sorted(key_puts, reverse=True) if k < entry]
    tp1 = round(put_below[0], 2) if put_below else round(lrr, 2)
    tp2_candidates = [k for k in sorted(key_puts, reverse=True) if k < tp1]
    tp2 = round(tp2_candidates[0], 2) if tp2_candidates else round(lrr * 0.98, 2)
    tp2 = min(tp2, round(lrr, 2))

    im_pct = implied_move or 0.05
    stop = round(max(trr * 1.01, entry * (1 + im_pct * 0.8)), 2)

    reward = entry - tp1
    risk   = stop - entry
    rr_ratio = round(reward / risk, 2) if risk > 0 else 0
    hold = "TRADE (1-3wk)" if rr_ratio >= 1.5 else "SKIP (poor R/R)"
    ev_ok = rr_ratio >= 1.5 and entry >= spot * 0.98

    return {
        "side": "SHORT",
        "entry": entry,
        "tp1": tp1,
        "tp2": tp2,
        "stop": stop,
        "rr": rr_ratio,
        "holding": hold,
        "ev_ok": ev_ok,
        "call_resistance": call_resist,
        "put_support": put_below[0] if put_below else None,
    }


# ── Main Engine ────────────────────────────────────────────────────────────────

class OptionsEngine:
    """
    Fetch and analyze options data for a ticker.
    Integrates Black-Scholes Greeks, OI heatmap, Max Pain, Gamma Wall
    with Risk Range LRR/TRR to produce entry/TP/stop recommendations.

    Skip list: IHSG tickers (no liquid options), futures, FX pairs.
    """
    SKIP_SUFFIXES = (".JK", "=F", "=X", "-USD", "^")
    MAX_CHAINS = 12   # max OI rows to pull per calls/puts DF

    def __init__(self, cache_ttl: float = 3600.0):
        self.cache_ttl = cache_ttl

    def _should_skip(self, ticker: str) -> bool:
        for sfx in self.SKIP_SUFFIXES:
            if ticker.endswith(sfx) or ticker.startswith("^"): return True
        return False

    def analyze(
        self,
        ticker: str,
        spot: float,
        lrr: Optional[float] = None,
        trr: Optional[float] = None,
        trend_signal: str = "neutral",  # "bullish" / "bearish" / "neutral"
        days_to_exp: int = 35,
        r: float = RISK_FREE_RATE,
    ) -> Dict:
        """
        Full options analysis for one ticker.
        Returns dict with all signals, or {"ok": False, ...} on failure.
        """
        if self._should_skip(ticker):
            return {"ok": False, "ticker": ticker, "reason": "skip_no_options"}

        # Cache check
        cache_key = f"{ticker}_{days_to_exp}"
        if cache_key in _CACHE:
            data, ts = _CACHE[cache_key]
            if time.time() - ts < self.cache_ttl:
                return data

        try:
            import yfinance as yf
            yticker = yf.Ticker(ticker)
            expirations = yticker.options
            if not expirations:
                return {"ok": False, "ticker": ticker, "reason": "no_options"}

            # Pick best expiry
            exp = _get_nearest_expiry(expirations, days_min=7, days_target=days_to_exp)
            if not exp:
                return {"ok": False, "ticker": ticker, "reason": "no_valid_expiry"}

            from datetime import datetime, date
            T = max(1, (datetime.strptime(exp, "%Y-%m-%d").date() - date.today()).days) / 365.0

            chain = yticker.option_chain(exp)
            calls = chain.calls.copy() if chain.calls is not None else pd.DataFrame()
            puts  = chain.puts.copy()  if chain.puts  is not None else pd.DataFrame()

            if calls.empty or puts.empty:
                return {"ok": False, "ticker": ticker, "reason": "empty_chain"}

            # Clean data
            for df in [calls, puts]:
                for col in ["openInterest","volume","bid","ask","impliedVolatility"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            # ── Core computations ─────────────────────────────────────────
            max_pain    = _compute_max_pain(calls, puts)
            gamma_wall  = _compute_gamma_wall(calls, puts, spot, r, T)
            key_puts    = _find_key_oi_levels(puts,  spot, "put",  3)
            key_calls   = _find_key_oi_levels(calls, spot, "call", 3)
            impl_move   = _implied_move(calls, puts, spot)
            top_gamma_strike = max(gamma_wall, key=gamma_wall.get) if gamma_wall else None

            # ATM Greeks
            atm_strike = min(calls["strike"].tolist(), key=lambda k: abs(k - spot))
            atm_iv = float(calls[calls["strike"] == atm_strike]["impliedVolatility"].iloc[0]) if not calls[calls["strike"]==atm_strike].empty else 0.25
            atm_greeks_call = bs_greeks(spot, atm_strike, T, r, atm_iv, "call")
            atm_greeks_put  = bs_greeks(spot, atm_strike, T, r, atm_iv, "put")

            # IV Percentile (proxy: use range of IVs in chain)
            all_ivs = calls["impliedVolatility"].tolist() + puts["impliedVolatility"].tolist()
            all_ivs = [v for v in all_ivs if v > 0.01]
            iv_pct = _iv_percentile(all_ivs, atm_iv)

            # OI Heatmap (top 20 strikes by total OI)
            calls_oi = calls.set_index("strike")["openInterest"].to_dict()
            puts_oi  = puts.set_index("strike")["openInterest"].to_dict()
            all_strikes = sorted(set(list(calls_oi.keys()) + list(puts_oi.keys())))
            oi_heatmap = [
                {
                    "strike": s,
                    "call_oi": int(calls_oi.get(s, 0)),
                    "put_oi":  int(puts_oi.get(s, 0)),
                    "total_oi": int(calls_oi.get(s, 0) + puts_oi.get(s, 0)),
                    "net": int(calls_oi.get(s, 0) - puts_oi.get(s, 0)),
                }
                for s in all_strikes
                if (calls_oi.get(s, 0) + puts_oi.get(s, 0)) > 0
            ]
            oi_heatmap.sort(key=lambda x: -x["total_oi"])
            oi_heatmap = oi_heatmap[:20]

            # Put/Call ratio
            total_call_oi = int(calls["openInterest"].sum())
            total_put_oi  = int(puts["openInterest"].sum())
            pc_ratio = round(total_put_oi / max(total_call_oi, 1), 3)

            # ── Trade levels ───────────────────────────────────────────────
            long_levels  = None
            short_levels = None
            if lrr is not None and trr is not None:
                long_levels  = _derive_long_levels(spot, lrr, trr, key_puts, key_calls, impl_move)
                short_levels = _derive_short_levels(spot, lrr, trr, key_puts, key_calls, impl_move)

            # ── Signal summary ─────────────────────────────────────────────
            options_signal = "NEUTRAL"
            if long_levels and long_levels["ev_ok"] and trend_signal == "bullish":
                options_signal = "LONG CONFIRMED"
            elif long_levels and long_levels["ev_ok"] and trend_signal == "neutral":
                options_signal = "LONG SETUP"
            elif short_levels and short_levels["ev_ok"] and trend_signal == "bearish":
                options_signal = "SHORT CONFIRMED"
            elif short_levels and short_levels["ev_ok"]:
                options_signal = "SHORT SETUP"
            elif long_levels and not long_levels["ev_ok"]:
                options_signal = "EXTENDED — WAIT"

            result = {
                "ok": True,
                "ticker": ticker,
                "spot": spot,
                "expiry": exp,
                "days_to_exp": int(T * 365),
                "atm_iv": round(atm_iv, 4),
                "iv_percentile": iv_pct,
                "implied_move_pct": impl_move,
                "pc_ratio": pc_ratio,
                "max_pain": max_pain,
                "top_gamma_strike": top_gamma_strike,
                "key_puts": key_puts,
                "key_calls": key_calls,
                "atm_greeks_call": atm_greeks_call,
                "atm_greeks_put":  atm_greeks_put,
                "oi_heatmap": oi_heatmap,
                "gamma_wall": {str(k): round(v, 2) for k, v in
                               sorted(gamma_wall.items(), key=lambda x: -abs(x[1]))[:15]},
                "long_levels":  long_levels,
                "short_levels": short_levels,
                "options_signal": options_signal,
            }
            _CACHE[cache_key] = (result, time.time())
            return result

        except Exception as e:
            logger.warning(f"OptionsEngine.analyze({ticker}): {e}")
            return {"ok": False, "ticker": ticker, "reason": str(e)}

    def batch_analyze(
        self,
        tickers: List[str],
        asset_ranges: Dict[str, dict],
    ) -> Dict[str, dict]:
        """
        Analyze a list of tickers in batch.
        Pull LRR/TRR from asset_ranges if available.
        """
        results = {}
        for ticker in tickers[:20]:  # cap at 20 to avoid timeout
            if self._should_skip(ticker): continue
            v = asset_ranges.get(ticker, {})
            trade = v.get("trade", {})
            spot  = v.get("px") or 0.0
            lrr   = trade.get("lrr")
            trr   = trade.get("trr")
            trend = v.get("composite", "neutral")
            if spot <= 0: continue
            try:
                results[ticker] = self.analyze(ticker, spot, lrr, trr, trend)
            except Exception as e:
                logger.debug(f"Batch options error {ticker}: {e}")
                results[ticker] = {"ok": False, "ticker": ticker, "reason": str(e)}
        return results
