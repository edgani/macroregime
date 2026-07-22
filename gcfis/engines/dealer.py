"""Options Greek exposure research engine.

Public option-chain OI does not reveal whether dealers are long or short each contract.  Signed
GEX/Vanna/Charm and a dealer hedging regime are emitted only when an explicit, auditable
``dealer_sign`` column is supplied (+1 dealer long, -1 dealer short).  Otherwise the engine
returns unsigned magnitude and withholds the regime.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm


def _bs_gamma(S, K, T, sigma, r=0.04):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    return float(norm.pdf(d1) / (S * sigma * np.sqrt(T)))


def _bs_vanna(S, K, T, sigma, r=0.04):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return float(-norm.pdf(d1) * d2 / sigma)


def _bs_charm(S, K, T, sigma, r=0.04):
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return 0.0
    d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    return float(-norm.pdf(d1) * (2 * r * T - d2 * sigma * np.sqrt(T)) / (2 * T * sigma * np.sqrt(T)))


def _bucket(T_years: float) -> str:
    days = max(0.0, float(T_years) * 365.0)
    if days < 1.0:
        return "0DTE"
    if days <= 7:
        return "1_7DTE"
    if days <= 30:
        return "8_30DTE"
    return "31P_DTE"


def run_dealer(chain: pd.DataFrame | None, spot: float, r: float = 0.04) -> dict:
    """Compute Greek exposure from an option chain.

    Required columns: ``strike``, ``oi``, ``iv``, ``type``, ``T``.  Signed inventory additionally
    requires ``dealer_sign`` for every usable row. Missing sign never falls back to the popular
    but unverifiable assumption that calls are dealer-long and puts are dealer-short.
    """
    if chain is None or len(chain) == 0 or not spot:
        return {"ok": False, "regime": "unknown", "reason": "no options chain (Greeks not fabricated)"}
    required = {"strike", "oi", "iv", "type", "T"}
    if not required.issubset(chain.columns):
        return {"ok": False, "regime": "unknown", "reason": f"missing required columns: {sorted(required-set(chain.columns))}"}

    signed_available = "dealer_sign" in chain.columns and chain["dealer_sign"].notna().all()
    signed_gex = signed_vanna = signed_charm = 0.0
    unsigned_gamma = unsigned_vanna = unsigned_charm = 0.0
    net_by_strike: dict[float, float] = {}
    calls: dict[float, float] = {}
    puts: dict[float, float] = {}
    dte = {k: {"gamma": 0.0, "vanna": 0.0, "charm": 0.0, "oi": 0.0} for k in ("0DTE", "1_7DTE", "8_30DTE", "31P_DTE")}

    for _, row in chain.iterrows():
        try:
            K, oi, iv, typ, T = float(row["strike"]), float(row["oi"]), float(row["iv"]), str(row["type"]).upper()[0], float(row["T"])
        except Exception:
            continue
        g = _bs_gamma(spot, K, T, iv, r)
        va = _bs_vanna(spot, K, T, iv, r)
        ch = _bs_charm(spot, K, T, iv, r)
        dg = abs(oi * g * 100 * spot**2 * 0.01)
        dv = abs(oi * va * 100)
        dc = abs(oi * ch * 100)
        unsigned_gamma += dg
        unsigned_vanna += dv
        unsigned_charm += dc
        b = _bucket(T)
        dte[b]["gamma"] += dg
        dte[b]["vanna"] += dv
        dte[b]["charm"] += dc
        dte[b]["oi"] += oi
        (calls if typ == "C" else puts)[K] = (calls if typ == "C" else puts).get(K, 0.0) + oi
        if signed_available:
            sign = float(row["dealer_sign"])
            if sign not in {-1.0, 1.0}:
                signed_available = False
                continue
            signed_gex += sign * dg
            signed_vanna += sign * oi * va * 100
            signed_charm += sign * oi * ch * 100
            net_by_strike[K] = net_by_strike.get(K, 0.0) + sign * dg

    result = {
        "ok": True,
        "dealer_sign_state": "EXPLICIT" if signed_available else "UNKNOWN",
        "ownership_state": "VERIFIED_INPUT" if signed_available else "UNVERIFIED",
        "unsigned_gamma_magnitude": round(unsigned_gamma, 1),
        "unsigned_vanna_magnitude": round(unsigned_vanna, 1),
        "unsigned_charm_magnitude": round(unsigned_charm, 1),
        "dte_buckets": {k: {m: round(v, 2) for m, v in vals.items()} for k, vals in dte.items()},
        "call_wall": max(calls, key=calls.get) if calls else None,
        "put_wall": max(puts, key=puts.get) if puts else None,
        "semantics": "Unsigned magnitude is descriptive. Signed regime requires explicit dealer_sign for every contract.",
    }
    if not signed_available:
        result.update({"regime": "unknown", "gex": None, "gex_sign": None, "gamma_flip": None, "vanna": None, "charm": None})
        return result

    ks = sorted(net_by_strike)
    cum = np.cumsum([net_by_strike[k] for k in ks]) if ks else []
    flip = next((ks[i] for i in range(len(ks)) if cum[i] >= 0), None) if ks else None
    result.update({
        "gex": round(signed_gex, 1),
        "gex_sign": int(np.sign(signed_gex)),
        "regime": "mean_reversion_context" if signed_gex > 0 else "amplification_context" if signed_gex < 0 else "neutral_context",
        "gamma_flip": round(float(flip), 2) if flip is not None else None,
        "vanna": round(signed_vanna, 1),
        "charm": round(signed_charm, 1),
    })
    return result
