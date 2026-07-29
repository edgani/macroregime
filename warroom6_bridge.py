"""warroom6_bridge.py — attach the FULL War Room 6 intelligence stack to the
V10.1 desk snapshot.

War Room 6 (warroom/compute.py, app.py dashboard) computes the operator's
market-direction guidance: structural/monthly/forward quads, regime state,
risk-on/off (HMM), shock state, crash meter + crash pressure + crash lead,
fear/greed early warnings, market health + character, computed meters
(trend/credit/...), cycle compass, sector rotation, cross-asset regime,
funding stress, crowding, country regimes, asset drivers, mechanical flows
and the macro focus board. The V10.1 desk never carried these, so they
looked "gone". This bridge runs the compute pipeline in cache-only mode and
attaches the complete bundle.

Honesty contract:
- Everything here is RESEARCH_ONLY, execution_eligible False. Regime/quad are
  classifications; crash meter/lead are severity gauges, not calibrated
  probabilities. Bases reported by the engines themselves are passed through.
- On ANY failure the section degrades to UNAVAILABLE with the error — the
  worker must never break because of this bridge.
- No synthetic data: NO_DATA/empty sections are attached exactly as computed.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from typing import Any


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _san(o: Any, depth: int = 0) -> Any:
    """JSON-safe sanitize: tuple keys -> str, numpy/pandas scalars -> python,
    unknown objects -> str. Depth-capped to keep the snapshot lean."""
    if depth > 8:
        return str(o)[:200]
    if isinstance(o, dict):
        return {str(k): _san(v, depth + 1) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_san(x, depth + 1) for x in o]
    try:
        json.dumps(o)
        return o
    except (TypeError, ValueError):
        pass
    # numpy / pandas scalars
    for attr in ("item",):
        fn = getattr(o, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                break
    return str(o)


# Sections carried from the War Room 6 compute output into the desk bundle.
# Key = desk section name, value = compute-output key.
SECTION_MAP = {
    "regime_state": "regime",                 # you-are-here: structural + monthly quad, divergence, probs
    "macro_regime": "macro_regime",           # risk regime score + quad
    "forward_quad": "forward",                # current/next quad (MIFG/MII/GROC/IROC)
    "cycle_compass": "cycle_rotation",        # RISK-ON/OFF compass
    "sector_rotation": "rotation",            # sector quadrants (RS x momentum)
    "cross_asset": "xasset",                  # cross-asset regime + divergences
    "market_health": "market",                # bull/bear/breadth
    "market_character": "market_character",   # direction, effort/result, emotion
    "meters": "meters_computed",              # trend/credit/... computed meters
    "crash_pressure": "crash",                # crash pressure components
    "crash_meter": "crash_meter",             # 0-100 severity gauge
    "crash_lead": "crash_lead",               # 12/24/36mo lead probabilities (engine-labelled)
    "early_warning": "early_warning",         # fear/greed, panic
    "funding": "funding",                     # funding stress + treasury liquidity
    "crowding": "crowd_market",               # positioning heat
    "macro_focus": "attention",               # attention board
    "country_regimes": "country_regime",      # per-country quad cells
    "asset_drivers": "drivers",               # factor-model driver notes
    "mechanical_flows": "mechanical",         # month-end rebalance, vol target
    "alpha_state": "alpha_state",             # honest no-trade state + reason
    "data_asof": "data_asof",                 # data freshness
    "feeds_status": "feeds_status",           # feed health
}


def build_market_intelligence() -> dict[str, Any]:
    """Run the War Room 6 compute stack (cache-only) and attach the full
    market-direction intelligence bundle to the desk."""
    try:
        os.environ.setdefault("WARROOM_OFFLINE", "1")  # cache-only: no live fetch storms
        from warroom import compute as C
        from warroom import data as D
        from warroom import feeds as FEEDS
        from warroom import fred as F

        us, _ = D.load(D.US_UNIVERSE)
        idx, _ = D.load(D.IDX_UNIVERSE)
        cp, _ = D.load(D.CRYPTO_UNIVERSE)
        fxp, _ = D.load(D.FX_UNIVERSE)
        try:
            commo = D.load(D.COMMO_UNIVERSE)[0] if hasattr(D, "COMMO_UNIVERSE") else {}
        except Exception:
            commo = {}
        fred = F.load() if hasattr(F, "load") else {}
        feeds = FEEDS.load() if hasattr(FEEDS, "load") else {}
        d = C.run(us, idx, cp, fxp, commo, fred, feeds)

        bundle: dict[str, Any] = {
            "state": "CURRENT",
            "computed_at": _utc_now(),
            "source": "warroom6_compute_stack (cache-only)",
            "proof_status": "RESEARCH_ONLY",
            "execution_eligible": False,
            "claim_limit": "Market-direction guidance from the War Room 6 stack: regime/quad "
                           "classifications and severity gauges, not calibrated probabilities "
                           "and not alpha inputs. Engine-reported bases passed through unchanged.",
            # scalars kept top-level for fast dashboard reads
            "hmm_state": _san(d.get("hmm")),
            "shock_state": _san(d.get("shock_prob")),
            "vix": _san(d.get("vix")),
        }
        for desk_key, src_key in SECTION_MAP.items():
            bundle[desk_key] = _san(d.get(src_key))
        # convenience copies (existing consumers expect these names)
        mr = bundle.get("macro_regime") or {}
        bundle["macro_quad"] = mr.get("macro_quad")
        bundle["risk_regime"] = mr.get("risk_regime")
        bundle["inflation_play"] = mr.get("inflation_play")
        bundle["engine_errors"] = list(getattr(C, "_DIAG", []))[:10]
        return bundle
    except Exception as exc:  # honest failure, never break the worker
        return {
            "state": "UNAVAILABLE",
            "computed_at": _utc_now(),
            "source": "warroom6_compute_stack (cache-only)",
            "error": f"{type(exc).__name__}: {exc}",
            "macro_quad": None,
            "crash_meter": None,
        }
