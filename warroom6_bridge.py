"""warroom6_bridge.py — attach War Room 6 intelligence (macro quad, crash meter)
to the V10.1 desk snapshot.

The V10.1 desk never included the War Room 6 components (macro_quad via
warroom/macro_regime.py, crash_meter via warroom/crash_meter.py), so the
operator saw them as "gone". This bridge runs the warroom/compute.py pipeline
in cache-only (offline) mode and attaches the surviving outputs to the desk.

Honesty contract:
- Every output keeps the War Room 6 labels: quad is a regime classification,
  crash meter is a SEVERITY GAUGE, NOT a calibrated probability
  (proof_status RESEARCH_ONLY, execution_eligible False).
- On ANY failure the section is attached as UNAVAILABLE with the error —
  the worker must never break because of this bridge.
- No synthetic data: if the compute stack has no data, subcomponents stay
  NO_DATA exactly as warroom/crash_meter.py reports them.
"""
from __future__ import annotations

import datetime as dt
import os
from typing import Any


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def build_market_intelligence() -> dict[str, Any]:
    """Run the War Room 6 compute stack (cache-only) and extract the components
    the operator expects on the desk: macro quad + crash meter (+ regime)."""
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

        mr = d.get("macro_regime") or {}
        cm = d.get("crash_meter") or {}
        return {
            "state": "CURRENT",
            "computed_at": _utc_now(),
            "source": "warroom6_compute_stack (cache-only)",
            "proof_status": "RESEARCH_ONLY",
            "execution_eligible": False,
            "claim_limit": "Regime classification + severity gauge. Neither is a "
                           "calibrated probability; neither is an alpha input.",
            "macro_quad": mr.get("macro_quad"),
            "risk_regime": mr.get("risk_regime"),
            "inflation_play": mr.get("inflation_play"),
            "crash_meter": cm,
            "engine_errors": list(getattr(C, "_DIAG", []))[:10],
        }
    except Exception as exc:  # honest failure, never break the worker
        return {
            "state": "UNAVAILABLE",
            "computed_at": _utc_now(),
            "source": "warroom6_compute_stack (cache-only)",
            "error": f"{type(exc).__name__}: {exc}",
            "macro_quad": None,
            "crash_meter": None,
        }
