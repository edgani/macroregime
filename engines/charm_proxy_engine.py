"""engines/charm_proxy_engine.py — Charm Flow Proxy
Charm = D-Delta/D-Time. Proxy from options chain theta + price momentum.
Predicts passive directional bias, especially 1:30-3pm ET.
"""
import math
import numpy as np
import pandas as pd

try:
    import yfinance as yf
    _HAS_YF = True
except Exception:
    _HAS_YF = False


def _black_scholes_theta(S, K, T, r, sigma, option_type="call"):
    """Calculate Black-Scholes theta (per day)."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)
    nd1 = 1 / (math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1 ** 2)

    if option_type == "call":
        theta = -(S * nd1 * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * (0.5 * (1 + math.erf(d2 / math.sqrt(2))))
    else:
        theta = -(S * nd1 * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * (0.5 * (1 + math.erf(-d2 / math.sqrt(2))))
    return theta / 365.0  # per calendar day


def analyze_charm(ticker, prices, vix=20.0, risk_free=0.045):
    """
    Calculate Charm exposure for a ticker.
    Returns directional bias from time-decay hedging flows.
    """
    s = prices.get(ticker)
    if s is None or len(s) < 20:
        return {"ok": False, "error": "No price data"}

    try:
        s_clean = pd.to_numeric(s, errors="coerce").dropna()
        spot = float(s_clean.iloc[-1])
    except Exception:
        return {"ok": False, "error": "Price parse failed"}

    # Try to get options chain
    if _HAS_YF:
        try:
            t = yf.Ticker(ticker)
            exps = t.options
            if exps:
                expiry = exps[0]
                chain = t.option_chain(expiry)
                calls, puts = chain.calls, chain.puts

                from datetime import datetime
                exp_date = datetime.strptime(expiry, "%Y-%m-%d")
                T = max((exp_date - datetime.now()).days / 365.0, 0.0027)
                sigma = vix / 100.0

                net_charm = 0
                for _, opt in calls.iterrows():
                    strike = float(opt.get("strike", 0))
                    oi = float(opt.get("openInterest", 0) or 0)
                    if strike <= 0 or oi <= 0:
                        continue
                    theta = _black_scholes_theta(spot, strike, T, risk_free, sigma, "call")
                    # Charm proxy: theta * delta decay direction
                    charm = -theta * oi * 100  # negative theta = dealer must buy
                    net_charm += charm

                for _, opt in puts.iterrows():
                    strike = float(opt.get("strike", 0))
                    oi = float(opt.get("openInterest", 0) or 0)
                    if strike <= 0 or oi <= 0:
                        continue
                    theta = _black_scholes_theta(spot, strike, T, risk_free, sigma, "put")
                    charm = -theta * oi * 100
                    net_charm -= charm  # puts flip sign

                return _charm_from_net(net_charm, spot, s_clean, vix, "YF_OPTIONS")
        except Exception:
            pass

    # Proxy fallback
    return _charm_proxy(ticker, spot, s_clean, vix)


def _charm_from_net(net_charm, spot, s_clean, vix, source):
    """Interpret net charm exposure."""
    r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0

    if net_charm > 5e5:
        regime = "BUILDING"
        signal = "NEVER_SHORT"
        color = "#3FB950"
        note = f"Charm {net_charm/1e6:.1f}M — dealers must BUY futures to hedge"
    elif net_charm > 1e5:
        regime = "BUILDING"
        signal = "BULLISH_BIAS"
        color = "#3FB950"
        note = f"Charm {net_charm/1e6:.1f}M — positive drift expected"
    elif net_charm < -5e5:
        regime = "FADING"
        signal = "AVOID_LONG"
        color = "#F85149"
        note = f"Charm {net_charm/1e6:.1f}M — dealers must SELL futures to hedge"
    elif net_charm < -1e5:
        regime = "FADING"
        signal = "BEARISH_BIAS"
        color = "#F85149"
        note = f"Charm {net_charm/1e6:.1f}M — negative drift expected"
    else:
        regime = "STABLE"
        signal = "NEUTRAL"
        color = "#8B949E"
        note = "Charm balanced — no time-decay drift"

    # Afternoon sweet spot: 1:30-3pm ET (13:30-15:00)
    from datetime import datetime
    now = datetime.now()
    hour = now.hour + now.minute / 60
    sweet_spot = 13.5 <= hour <= 15.0

    return {
        "ok": True,
        "net_charm": round(net_charm, 0),
        "regime": regime,
        "signal": signal,
        "color": color,
        "note": note,
        "sweet_spot": sweet_spot,
        "sweet_spot_note": "13:30-15:00 ET charm dominates" if sweet_spot else "Wait for afternoon window",
        "r5d": round(r5d, 4),
        "source": source,
    }


def _charm_proxy(ticker, spot, s_clean, vix):
    """Proxy charm from price momentum."""
    r5d = float(s_clean.iloc[-1] / s_clean.iloc[-6] - 1) if len(s_clean) >= 6 else 0
    r10d = float(s_clean.iloc[-1] / s_clean.iloc[-11] - 1) if len(s_clean) >= 11 else 0

    # Proxy charm from acceleration
    accel = r5d - (r10d / 2)
    net_charm_proxy = accel * 1e6

    return _charm_from_net(net_charm_proxy, spot, s_clean, vix, "PROXY")


def analyze_multi(tickers, prices, vix=20.0):
    results = {}
    for t in tickers:
        results[t] = analyze_charm(t, prices, vix)
    return results
