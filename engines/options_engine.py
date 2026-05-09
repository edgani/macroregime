"""engines/options_engine.py — Institutional Options Intelligence Layer

Implements full Greeks suite (first + second order):

FIRST ORDER:
  Delta  = ∂V/∂S             — directional exposure
  Gamma  = ∂²V/∂S²           — convexity / curvature of delta
  Theta  = ∂V/∂T             — daily time decay
  Vega   = ∂V/∂σ             — IV sensitivity

SECOND ORDER (missing from most retail tools):
  Vanna  = ∂Δ/∂σ = ∂Vega/∂S — how delta changes with IV (cross-Greek)
           Critical: When dealers are long vanna + IV rises → they SELL stock
           Tier 1 Alpha tracks net vanna to predict directional flows
  Charm  = ∂Δ/∂T             — how delta decays with time ("delta bleed")
           As expiry approaches OTM deltas decay → dealers unwind hedges
  Speed  = ∂Γ/∂S             — "gamma of gamma" / curvature of gamma
           Where gamma accelerates most (near ATM at expiry)
  Vomma  = ∂Vega/∂σ          — how vega changes with IV (second-order IV)
           High vomma options: if IV spikes, vega explodes → long gamma wins
  Color  = ∂Γ/∂T             — daily gamma decay rate
           Gamma decays fastest near expiry for OTM options

MARKET STRUCTURE:
  Max Pain      — strike minimizing total option value at expiry (MM pin thesis)
  Gamma Wall    — net gamma by strike: + = dealers long (suppress vol), - = amplify
  Gamma Level   — total net gamma exposure in $ (Tier 1 Alpha Gamma Throttle proxy)
  OI Heatmap    — call/put OI by strike (key support/resistance levels)
  Implied Move  — ATM straddle / spot = expected ±% move
  IV Percentile — current IV vs 52w range (cheap/expensive)
  Put/Call Ratio— total OI put/call

ENTRY/TP/STOP LOGIC:
  Integrated with Risk Range™ LRR/TRR:
  - Long entry: higher of (LRR, key put OI support near spot)
  - Short entry: lower of (TRR, key call OI resistance near spot)
  - TP1/TP2: call OI clusters (for longs) or put OI clusters (for shorts)
  - Stop: below LRR/put support (longs) or above TRR/call resistance (shorts)
  - Holding: derived from theta decay + RR signal duration

SKIP LIST: IHSG (.JK), Futures (=F), Forex (=X), Crypto (-USD), Index (^)
No scipy dependency. All math from stdlib.
Cache: 1 hour TTL.

Source: Tier 1 Alpha framework + CBOE methodology
"""
from __future__ import annotations

import math
import time
import logging
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Risk-free rate (US 3M T-bill, update periodically)
RISK_FREE_RATE: float = 0.052

# Cache: {cache_key: (result_dict, timestamp)}
_CACHE: Dict[str, Tuple[dict, float]] = {}
_CACHE_TTL: float = 3600.0  # 1 hour


# ══════════════════════════════════════════════════════════════════════════════
# BLACK-SCHOLES MATHEMATICS (no scipy — pure Python math)
# ══════════════════════════════════════════════════════════════════════════════

def _erf(x: float) -> float:
    """Abramowitz & Stegun approximation 7.1.26 (max error 1.5e-7)."""
    t = 1.0 / (1.0 + 0.3275911 * abs(x))
    poly = t * (0.254829592 + t * (-0.284496736 + t * (
           1.421413741 + t * (-1.453152027 + t * 1.061405429))))
    result = 1.0 - poly * math.exp(-x * x)
    return result if x >= 0 else -result

def _N(x: float) -> float:  # standard normal CDF
    return 0.5 * (1.0 + _erf(x / math.sqrt(2)))

def _n(x: float) -> float:  # standard normal PDF
    return math.exp(-0.5 * x * x) / math.sqrt(2 * math.pi)


def bs_all_greeks(
    S: float,   # spot price
    K: float,   # strike
    T: float,   # time to expiry (years)
    r: float,   # risk-free rate (annualized)
    sigma: float,  # implied volatility (annualized)
    opt: str = "call",  # "call" or "put"
) -> Optional[Dict[str, float]]:
    """
    Compute full Black-Scholes Greeks suite:
    First order:  price, delta, gamma, theta, vega
    Second order: vanna, charm, speed, vomma, color

    All values in practical units:
    - theta: $ per day (annualized / 365)
    - vega:  $ per 1% IV move (multiplied by 0.01)
    - vanna: Δ per 1% IV move
    - charm: Δ per day
    - speed: Γ per $1 spot move
    - vomma: vega change per 1% IV move
    - color: Γ per day
    """
    if T <= 1e-8 or sigma <= 1e-8 or S <= 0 or K <= 0:
        return None
    try:
        sq = sigma * math.sqrt(T)
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / sq
        d2 = d1 - sq

        Nd1 = _N(d1); Nd2 = _N(d2)
        Nnd1 = _N(-d1); Nnd2 = _N(-d2)
        nd1 = _n(d1)

        disc = math.exp(-r * T)

        # ── Price ──────────────────────────────────────────────────────────
        if opt == "call":
            price = S * Nd1 - K * disc * Nd2
        else:
            price = K * disc * Nnd2 - S * Nnd1
        price = max(price, 0.0)

        # ── First Order ────────────────────────────────────────────────────
        delta = Nd1 if opt == "call" else Nd1 - 1.0
        gamma = nd1 / (S * sq)  # same for calls and puts

        if opt == "call":
            theta = (-S * nd1 * sigma / (2 * math.sqrt(T))
                     - r * K * disc * Nd2) / 365.0
        else:
            theta = (-S * nd1 * sigma / (2 * math.sqrt(T))
                     + r * K * disc * Nnd2) / 365.0

        vega = S * nd1 * math.sqrt(T) / 100.0  # per 1% IV move

        # ── Second Order Greeks ────────────────────────────────────────────

        # Vanna: ∂Δ/∂σ = ∂Vega/∂S — how delta changes when IV moves
        # = -nd1 * d2 / sigma
        # Units: Δ per 1 unit of IV; we convert to per 1% IV: divide by 100
        vanna = -nd1 * d2 / sigma / 100.0

        # Charm: ∂Δ/∂T — daily delta decay ("delta bleed")
        # For call: -nd1 * [2rT - d2*sigma*sqrt(T)] / [2T*sigma*sqrt(T)]
        if opt == "call":
            charm = -nd1 * (2 * r * T - d2 * sq) / (2 * T * sq) / 365.0
        else:
            charm = nd1 * (2 * r * T - d2 * sq) / (2 * T * sq) / 365.0

        # Speed: ∂Γ/∂S = "Gamma of Gamma" / curvature of gamma curve
        # = -Gamma/S * (d1/sq + 1)
        speed = -gamma / S * (d1 / sq + 1.0)

        # Vomma (Volga): ∂Vega/∂σ — how vega changes with IV
        # = Vega * d1 * d2 / sigma
        # Units: vega change per 1 unit of sigma; convert to per 1% IV
        vomma = vega * d1 * d2 / sigma  # per 1% since vega is already /100

        # Color: ∂Γ/∂T — daily gamma decay
        # = -nd1 / (2 * S * T * sq) * (2rT + 1 - d1*d2*(sq/T))
        # Simplified: color = nd1 / (2*S*T*sq) * (2rT + 1 - d1*d2*sq)
        # Actually correct formula:
        # color = nd1 / (2*S*T*sq) * [2rT + 1 - d1*(d1-sq)/(sigma*sqrt(T))]
        try:
            color = (nd1 / (2.0 * S * T * sq) *
                     (2.0 * r * T + 1.0 - d1 * d2)) / 365.0
        except ZeroDivisionError:
            color = 0.0

        return {
            # Identification
            "type": opt,
            "S": round(S, 4), "K": round(K, 4),
            "T_years": round(T, 4), "sigma": round(sigma, 4),
            "d1": round(d1, 4), "d2": round(d2, 4),

            # Price
            "price": round(max(price, 0), 4),

            # First-order Greeks
            "delta": round(delta, 4),
            "gamma": round(gamma, 6),
            "theta": round(theta, 4),   # $ per day
            "vega":  round(vega, 4),    # $ per 1% IV

            # Second-order Greeks
            "vanna": round(vanna, 6),   # Δ per 1% IV move
            "charm": round(charm, 6),   # Δ per day (delta bleed)
            "speed": round(speed, 8),   # Γ per $1 spot move
            "vomma": round(vomma, 6),   # Vega per 1% IV move
            "color": round(color, 8),   # Γ per day
        }
    except Exception as e:
        logger.debug(f"bs_all_greeks error (S={S},K={K},T={T},σ={sigma}): {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# MARKET STRUCTURE COMPUTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def _get_nearest_expiry(expirations: tuple, days_min: int = 7, days_target: int = 35) -> str:
    from datetime import datetime, date
    today = date.today()
    best = None; best_diff = 9999
    for exp in expirations:
        try:
            diff = (datetime.strptime(exp, "%Y-%m-%d").date() - today).days
            if diff < days_min: continue
            dist = abs(diff - days_target)
            if dist < best_diff: best_diff = dist; best = exp
        except Exception: continue
    return best or (expirations[0] if expirations else "")

def _find_key_oi_levels(df: pd.DataFrame, spot: float, side: str, n: int = 3) -> List[float]:
    if df is None or df.empty: return []
    df = df[df["openInterest"] > 0].copy()
    df = df[df["strike"] >= spot * 0.90] if side == "call" else df[df["strike"] <= spot * 1.10]
    if side == "call": df = df[df["strike"] >= spot * 0.95]
    else:              df = df[df["strike"] <= spot * 1.05]
    top = df.nlargest(n, "openInterest")
    return sorted(top["strike"].tolist())

def _compute_max_pain(calls: pd.DataFrame, puts: pd.DataFrame) -> Optional[float]:
    """Strike where total intrinsic value of all options is minimized at expiry."""
    if calls is None or puts is None: return None
    try:
        strikes = sorted(set(calls["strike"].tolist() + puts["strike"].tolist()))
        pain: Dict[float, float] = {}
        for s in strikes:
            cp = sum(max(0.0, s - k) * oi for k, oi in zip(calls["strike"], calls["openInterest"]))
            pp = sum(max(0.0, k - s) * oi for k, oi in zip(puts["strike"],  puts["openInterest"]))
            pain[s] = cp + pp
        return min(pain, key=pain.get) if pain else None
    except Exception: return None

def _compute_gamma_structures(
    calls: pd.DataFrame, puts: pd.DataFrame,
    spot: float, r: float, T: float,
) -> Tuple[Dict[float, float], Dict[float, float], Dict[float, float], float]:
    """
    Returns:
      gamma_wall  — net gamma by strike (+ = dealer long gamma / vol suppressor)
      vanna_wall  — net vanna by strike
      charm_wall  — net charm by strike (delta decay)
      net_gamma_usd — total net gamma in $ (Gamma Level — Tier 1 Alpha concept)
    """
    gamma_wall: Dict[float, float] = {}
    vanna_wall:  Dict[float, float] = {}
    charm_wall:  Dict[float, float] = {}
    net_gamma_usd = 0.0

    if calls is None or puts is None:
        return gamma_wall, vanna_wall, charm_wall, net_gamma_usd

    try:
        for _, row in calls.iterrows():
            iv = float(row.get("impliedVolatility", 0))
            if iv <= 0: continue
            oi = float(row.get("openInterest", 0)) * 100  # contracts × 100 shares
            g = bs_all_greeks(spot, float(row["strike"]), T, r, iv, "call")
            if g:
                # Dealers are typically short calls → long delta, long gamma
                gamma_wall[row["strike"]] = gamma_wall.get(row["strike"], 0) + g["gamma"] * oi
                vanna_wall[row["strike"]]  = vanna_wall.get(row["strike"], 0)  + g["vanna"]  * oi
                charm_wall[row["strike"]]  = charm_wall.get(row["strike"], 0)  + g["charm"]  * oi
                net_gamma_usd += g["gamma"] * oi * spot * spot * 0.01  # Gamma $ exposure

        for _, row in puts.iterrows():
            iv = float(row.get("impliedVolatility", 0))
            if iv <= 0: continue
            oi = float(row.get("openInterest", 0)) * 100
            g = bs_all_greeks(spot, float(row["strike"]), T, r, iv, "put")
            if g:
                # Dealers are typically short puts → short delta, short gamma
                gamma_wall[row["strike"]] = gamma_wall.get(row["strike"], 0) - g["gamma"] * oi
                vanna_wall[row["strike"]]  = vanna_wall.get(row["strike"], 0)  - g["vanna"]  * oi
                charm_wall[row["strike"]]  = charm_wall.get(row["strike"], 0)  - g["charm"]  * oi
                net_gamma_usd -= g["gamma"] * oi * spot * spot * 0.01

    except Exception as e:
        logger.debug(f"Gamma structure error: {e}")

    return gamma_wall, vanna_wall, charm_wall, round(net_gamma_usd, 2)

def _implied_move(calls: pd.DataFrame, puts: pd.DataFrame, spot: float) -> Optional[float]:
    """Expected ±% from ATM straddle price."""
    try:
        atm = min(calls["strike"].tolist(), key=lambda k: abs(k - spot))
        c_row = calls[calls["strike"] == atm]
        p_row = puts[puts["strike"]  == atm]
        if c_row.empty: c_row = calls.iloc[(calls["strike"] - atm).abs().argsort()[:1]]
        if p_row.empty: p_row = puts.iloc[(puts["strike"]   - atm).abs().argsort()[:1]]
        c_mid = (float(c_row["bid"].iloc[0]) + float(c_row["ask"].iloc[0])) / 2
        p_mid = (float(p_row["bid"].iloc[0]) + float(p_row["ask"].iloc[0])) / 2
        straddle = c_mid + p_mid
        return round(straddle / spot, 4) if spot > 0 else None
    except Exception: return None


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY / TP / STOP LOGIC (Risk Range™ + Options integrated)
# ══════════════════════════════════════════════════════════════════════════════

def _derive_long_levels(
    spot: float, lrr: float, trr: float,
    key_puts: List[float], key_calls: List[float],
    implied_move: Optional[float],
    max_pain: Optional[float],
) -> Dict:
    """
    Long setup levels. Rule: only recommend if price is NEAR LRR (not extended).
    Do NOT recommend long if price is already near TRR.
    """
    # Reject if price is near or above TRR (extended)
    if trr > lrr > 0 and (spot - lrr) / (trr - lrr) > 0.65:
        return {"side":"LONG","ev_ok":False,"reason":"Extended — wait for pullback to LRR"}

    # Entry: Higher of LRR or nearest put OI support below spot
    put_support = max((k for k in key_puts if k <= spot * 1.01), default=None)
    entry = max(lrr, put_support * 0.99) if put_support else lrr
    entry = round(entry, 2)

    # TP1: first call OI cluster above entry
    call_above = sorted(k for k in key_calls if k > entry)
    tp1 = round(call_above[0], 2) if call_above else round(trr, 2)

    # TP2: TRR or next call OI level
    tp2_candidates = sorted(k for k in key_calls if k > tp1)
    tp2 = round(max(tp2_candidates[0] if tp2_candidates else 0, trr), 2)

    # Max Pain gravity: if max_pain is between entry and TP1, note it
    mp_note = f"Max Pain ${max_pain:.1f} (gravity level)" if max_pain and entry < max_pain < tp2 else ""

    # Stop: below LRR with options-derived cushion
    im = implied_move or 0.05
    stop = round(min(lrr * 0.985, entry * (1 - im * 0.75)), 2)

    reward = tp1 - entry; risk = entry - stop
    rr_ratio = round(reward / risk, 2) if risk > 0.001 else 0.0
    ev_ok    = rr_ratio >= 1.5 and entry <= spot * 1.01

    # Holding duration from R/R + theta consideration
    if rr_ratio >= 2.5:   hold = "TREND (≥3 months)"
    elif rr_ratio >= 1.5: hold = "TRADE (1-3 weeks)"
    else:                 hold = "SKIP — poor R/R"

    return {
        "side": "LONG", "entry": entry, "tp1": tp1, "tp2": tp2,
        "stop": stop, "rr": rr_ratio, "holding": hold,
        "ev_ok": ev_ok, "put_support": put_support,
        "call_resistance": call_above[0] if call_above else None,
        "max_pain_note": mp_note, "reason": "",
    }

def _derive_short_levels(
    spot: float, lrr: float, trr: float,
    key_puts: List[float], key_calls: List[float],
    implied_move: Optional[float],
    max_pain: Optional[float],
) -> Dict:
    """
    Short setup levels. Only recommend if price is near TRR (extended).
    Do NOT recommend short if price is near LRR.
    """
    # Reject if price is near LRR (oversold — not a short entry)
    if trr > lrr > 0 and (spot - lrr) / (trr - lrr) < 0.40:
        return {"side":"SHORT","ev_ok":False,"reason":"Near LRR — not a short entry"}

    # Entry: Lower of TRR or nearest call OI resistance above spot
    call_resist = min((k for k in key_calls if k >= spot * 0.99), default=None)
    entry = min(trr, call_resist * 1.01) if call_resist else trr
    entry = round(entry, 2)

    # TP1: first put OI cluster below entry
    put_below = sorted((k for k in key_puts if k < entry), reverse=True)
    tp1 = round(put_below[0], 2) if put_below else round(lrr, 2)

    # TP2: LRR or next put OI level
    tp2_candidates = sorted((k for k in key_puts if k < tp1), reverse=True)
    tp2 = round(min(tp2_candidates[0] if tp2_candidates else float("inf"), lrr), 2)
    mp_note = f"Max Pain ${max_pain:.1f} (gravity level)" if max_pain and tp1 < max_pain < entry else ""

    im = implied_move or 0.05
    stop = round(max(trr * 1.015, entry * (1 + im * 0.75)), 2)

    reward = entry - tp1; risk = stop - entry
    rr_ratio = round(reward / risk, 2) if risk > 0.001 else 0.0
    ev_ok    = rr_ratio >= 1.5 and entry >= spot * 0.99
    hold = "TRADE (1-3 weeks)" if rr_ratio >= 1.5 else "SKIP — poor R/R"

    return {
        "side": "SHORT", "entry": entry, "tp1": tp1, "tp2": tp2,
        "stop": stop, "rr": rr_ratio, "holding": hold,
        "ev_ok": ev_ok, "call_resistance": call_resist,
        "put_support": put_below[0] if put_below else None,
        "max_pain_note": mp_note, "reason": "",
    }


# ══════════════════════════════════════════════════════════════════════════════
# MAIN OPTIONS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class OptionsEngine:
    """
    Institutional-grade options analysis.
    Covers: BS full Greeks + second-order (Vanna/Charm/Speed/Vomma/Color)
    + Gamma Wall + Vanna Wall + Charm Wall + Max Pain + OI Heatmap
    + Entry/TP/Stop integrated with Risk Range LRR/TRR.

    Skip: IHSG (.JK), Futures (=F), Forex (=X), Crypto (-USD), Index (^)
    """
    SKIP_PATTERNS = (".JK", "=F", "=X", "-USD", "-USDT")

    def __init__(self, cache_ttl: float = _CACHE_TTL, r: float = RISK_FREE_RATE):
        self.cache_ttl = cache_ttl
        self.r = r

    def _should_skip(self, ticker: str) -> bool:
        if ticker.startswith("^"): return True
        return any(ticker.endswith(p) for p in self.SKIP_PATTERNS)

    def analyze(
        self,
        ticker: str,
        spot: float,
        lrr: Optional[float] = None,
        trr: Optional[float] = None,
        trend_signal: str = "neutral",
        days_to_exp: int = 35,
    ) -> Dict:
        """
        Full options analysis. Returns dict with all signals.
        """
        if self._should_skip(ticker):
            return {"ok": False, "ticker": ticker, "reason": "skip_no_options"}
        if spot <= 0:
            return {"ok": False, "ticker": ticker, "reason": "invalid_spot"}

        cache_key = f"{ticker}_{days_to_exp}"
        if cache_key in _CACHE:
            data, ts = _CACHE[cache_key]
            if time.time() - ts < self.cache_ttl:
                return data

        try:
            import yfinance as yf
            yt = yf.Ticker(ticker)
            expirations = yt.options
            if not expirations:
                return {"ok": False, "ticker": ticker, "reason": "no_options"}

            exp = _get_nearest_expiry(expirations, days_min=7, days_target=days_to_exp)
            if not exp:
                return {"ok": False, "ticker": ticker, "reason": "no_valid_expiry"}

            from datetime import datetime, date
            T = max(1, (datetime.strptime(exp, "%Y-%m-%d").date() - date.today()).days) / 365.0

            chain = yt.option_chain(exp)
            calls = chain.calls.copy() if chain.calls is not None else pd.DataFrame()
            puts  = chain.puts.copy()  if chain.puts  is not None else pd.DataFrame()
            if calls.empty or puts.empty:
                return {"ok": False, "ticker": ticker, "reason": "empty_chain"}

            # Clean numeric columns
            for df in [calls, puts]:
                for col in ["openInterest","volume","bid","ask","impliedVolatility","strike"]:
                    if col in df.columns:
                        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

            # ── ATM IV and greeks ──────────────────────────────────────────
            atm_strike = float(calls.iloc[(calls["strike"] - spot).abs().argsort().iloc[0]]["strike"])
            atm_iv_row = calls[calls["strike"] == atm_strike]
            atm_iv = float(atm_iv_row["impliedVolatility"].iloc[0]) if not atm_iv_row.empty else 0.25
            if atm_iv < 0.01: atm_iv = 0.25  # fallback

            atm_call = bs_all_greeks(spot, atm_strike, T, self.r, atm_iv, "call")
            atm_put  = bs_all_greeks(spot, atm_strike, T, self.r, atm_iv, "put")

            # IV percentile (vs chain range as proxy for 52w)
            all_ivs = [v for v in calls["impliedVolatility"].tolist() + puts["impliedVolatility"].tolist() if v > 0.01]
            if all_ivs and len(all_ivs) >= 5:
                lo, hi = min(all_ivs), max(all_ivs)
                iv_pct = round((atm_iv - lo) / max(hi - lo, 0.01), 3)
            else:
                iv_pct = None

            # ── Market structure ───────────────────────────────────────────
            max_pain = _compute_max_pain(calls, puts)
            gamma_wall, vanna_wall, charm_wall, net_gamma_usd = _compute_gamma_structures(calls, puts, spot, self.r, T)
            key_puts  = _find_key_oi_levels(puts,  spot, "put",  4)
            key_calls = _find_key_oi_levels(calls, spot, "call", 4)
            impl_move = _implied_move(calls, puts, spot)

            # Top gamma/vanna strikes
            top_gamma_strikes = sorted(gamma_wall.items(), key=lambda x: -abs(x[1]))[:8]
            top_vanna_strikes  = sorted(vanna_wall.items(),  key=lambda x: -abs(x[1]))[:8]

            # Gamma wall: where dealers SWITCH from net long to net short gamma
            gamma_flip = None
            prev_sign  = None
            for strike in sorted(gamma_wall.keys()):
                cur_sign = 1 if gamma_wall[strike] >= 0 else -1
                if prev_sign is not None and cur_sign != prev_sign:
                    gamma_flip = strike
                    break
                prev_sign = cur_sign

            # Vanna flow signal
            # If dealers are net long vanna AND IV is rising → they sell stock (bearish pressure)
            # If dealers are net short vanna AND IV is rising → they buy stock (bullish pressure)
            total_vanna = sum(vanna_wall.values())
            vanna_signal = "bearish" if total_vanna > 0 else "bullish" if total_vanna < 0 else "neutral"

            # Charm: delta decay flow near expiry
            total_charm = sum(charm_wall.values())
            charm_signal = "covering" if total_charm < 0 else "unwinding" if total_charm > 0 else "neutral"

            # OI Heatmap
            calls_oi = calls.set_index("strike")["openInterest"].to_dict()
            puts_oi  = puts.set_index("strike")["openInterest"].to_dict()
            all_s    = sorted(set(list(calls_oi.keys()) + list(puts_oi.keys())))
            oi_heatmap = sorted(
                [{"strike": s,
                  "call_oi": int(calls_oi.get(s, 0)),
                  "put_oi":  int(puts_oi.get(s, 0)),
                  "total_oi": int(calls_oi.get(s,0) + puts_oi.get(s,0)),
                  "net_oi":  int(calls_oi.get(s,0) - puts_oi.get(s,0)),
                  "net_gamma": round(gamma_wall.get(s, 0), 3)}
                 for s in all_s if (calls_oi.get(s,0) + puts_oi.get(s,0)) > 0],
                key=lambda x: -x["total_oi"]
            )[:25]

            # Put/Call ratio
            total_call_oi = int(calls["openInterest"].sum())
            total_put_oi  = int(puts["openInterest"].sum())
            pc_ratio = round(total_put_oi / max(total_call_oi, 1), 3)

            # ── Entry / TP / Stop ──────────────────────────────────────────
            long_levels  = None
            short_levels = None
            if lrr is not None and trr is not None and lrr < trr:
                long_levels  = _derive_long_levels(spot, lrr, trr, key_puts, key_calls, impl_move, max_pain)
                short_levels = _derive_short_levels(spot, lrr, trr, key_puts, key_calls, impl_move, max_pain)

            # ── Combined options signal ────────────────────────────────────
            options_signal = "NEUTRAL"
            if long_levels and long_levels.get("ev_ok") and trend_signal == "bullish":
                options_signal = "LONG CONFIRMED"
            elif long_levels and long_levels.get("ev_ok"):
                options_signal = "LONG SETUP"
            elif short_levels and short_levels.get("ev_ok") and trend_signal == "bearish":
                options_signal = "SHORT CONFIRMED"
            elif short_levels and short_levels.get("ev_ok"):
                options_signal = "SHORT SETUP"
            elif long_levels and not long_levels.get("ev_ok"):
                options_signal = long_levels.get("reason", "EXTENDED — WAIT")

            result = {
                "ok": True,
                "ticker": ticker,
                "spot": spot,
                "expiry": exp,
                "days_to_exp": int(T * 365),

                # Volatility
                "atm_iv": round(atm_iv, 4),
                "iv_percentile": iv_pct,
                "implied_move_pct": impl_move,

                # Flow
                "pc_ratio": pc_ratio,
                "vanna_signal": vanna_signal,
                "charm_signal": charm_signal,
                "net_gamma_usd": round(net_gamma_usd, 0),

                # Structure
                "max_pain": max_pain,
                "gamma_flip": gamma_flip,
                "key_puts": key_puts,
                "key_calls": key_calls,

                # Greeks (ATM)
                "atm_greeks_call": atm_call,
                "atm_greeks_put":  atm_put,

                # Second-order highlights
                "atm_vanna_call": round(atm_call.get("vanna", 0), 6) if atm_call else None,
                "atm_charm_call": round(atm_call.get("charm", 0), 6) if atm_call else None,
                "atm_vomma_call": round(atm_call.get("vomma", 0), 6) if atm_call else None,

                # Walls (top strikes by exposure)
                "gamma_wall_top": {str(k): round(v, 2) for k, v in top_gamma_strikes},
                "vanna_wall_top": {str(k): round(v, 4) for k, v in top_vanna_strikes},

                # Heatmap
                "oi_heatmap": oi_heatmap,

                # Trade levels
                "long_levels":  long_levels,
                "short_levels": short_levels,
                "options_signal": options_signal,
            }
            _CACHE[cache_key] = (result, time.time())
            return result

        except Exception as e:
            logger.warning(f"OptionsEngine.analyze({ticker}): {e}")
            return {"ok": False, "ticker": ticker, "reason": str(e)}

    def batch_analyze(self, tickers: List[str], asset_ranges: Dict[str, dict],
                      max_tickers: int = 15) -> Dict[str, dict]:
        """Analyze multiple tickers. Pull spot/LRR/TRR from asset_ranges."""
        results = {}
        count = 0
        for ticker in tickers:
            if count >= max_tickers: break
            if self._should_skip(ticker): continue
            v = asset_ranges.get(ticker, {})
            trade = v.get("trade", {})
            spot  = float(v.get("px") or 0)
            lrr   = float(trade.get("lrr") or 0) or None
            trr   = float(trade.get("trr") or 0) or None
            trend = str(v.get("composite", "neutral"))
            if spot <= 0: continue
            try:
                results[ticker] = self.analyze(ticker, spot, lrr, trr, trend)
                count += 1
            except Exception as e:
                logger.debug(f"Batch error {ticker}: {e}")
                results[ticker] = {"ok": False, "ticker": ticker, "reason": str(e)}
        return results
