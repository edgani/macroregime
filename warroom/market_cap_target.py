"""Fail-closed market-cap research interface.

Legacy releases generated bull/base/bear targets and EV from hand-authored theme
multiples, market-cap scaling and conviction.  Those values looked precise but were
not calibrated probabilities or company-level value-capture models.  v3.2 keeps the
API import-compatible while withholding targets, EV, alpha tiers and sizing until a
point-in-time, calibrated model is explicitly supplied and validated.
"""
from __future__ import annotations

_TICKER_THESIS = {
    "VRT": "ai_power", "ETN": "ai_power", "PWR": "ai_power", "GEV": "ai_power",
    "NVDA": "ai_compute", "AMD": "ai_compute", "AVGO": "ai_compute", "MU": "memory",
    "COHR": "photonics", "LITE": "photonics", "CCJ": "uranium", "UEC": "uranium",
    "BTC-USD": "crypto_beta", "ETH-USD": "crypto_beta", "SOL-USD": "crypto_beta",
}


def thesis_for(ticker):
    """Structural research bucket only; never a valuation or trade signal."""
    return _TICKER_THESIS.get((ticker or "").upper(), "generic_unassessed")


def _blocked(ticker=None, direction="Long", reason=None):
    return {
        "ticker": (ticker or "").upper() or None,
        "status": "MODEL_REQUIRED",
        "permission": "CAPITAL_BLOCKED",
        "direction": direction,
        "thesis": thesis_for(ticker),
        "scenarios": None,
        "convexity": None,
        "alpha_tier": "UNASSESSED",
        "alpha_color": "gry",
        "suggested_weight": None,
        "kill_thesis": None,
        "reason": reason or (
            "No calibrated company-level value-capture model with point-in-time inputs, "
            "probabilities, dilution, costs, capacity and horizon. Hand-authored theme "
            "multiples and conviction are not accepted as EV."
        ),
        "required_evidence": [
            "company-specific value-capture model",
            "point-in-time fundamental and share-count data",
            "pre-registered scenario definitions",
            "calibrated probabilities",
            "cost/slippage/capacity model",
            "walk-forward and prospective evidence",
        ],
    }


def scenarios(ticker, price, market_cap=None, thesis_key=None, direction="Long", calibrated_model=None):
    """Withhold scenarios unless an external validated model explicitly supplies them.

    A future calibrated model may pass ``calibrated_model`` containing a ``status`` of
    ``PRODUCTION`` plus a ``scenarios`` mapping.  This module does not manufacture one.
    """
    del price, market_cap, thesis_key
    if not isinstance(calibrated_model, dict) or calibrated_model.get("status") != "PRODUCTION":
        return None
    return calibrated_model.get("scenarios")


def convexity(sc, direction="Long"):
    """No EV calculation from uncalibrated scenario priors."""
    del sc, direction
    return None


def alpha_tier(upside_pct):
    del upside_pct
    return "UNASSESSED", "gry"


def suggested_weight(ev_pct, conviction_0_100, max_weight=0.08):
    del ev_pct, conviction_0_100, max_weight
    return None


def build(ticker, price, market_cap=None, conviction=50, direction="Long", thesis_key=None,
          calibrated_model=None):
    del price, market_cap, conviction, thesis_key
    if isinstance(calibrated_model, dict) and calibrated_model.get("status") == "PRODUCTION":
        # Only pass through evidence produced by a separately validated model.
        return {
            **_blocked(ticker, direction),
            **calibrated_model,
            "ticker": (ticker or "").upper(),
            "direction": direction,
        }
    return _blocked(ticker, direction)


def decision_market(candidates, calibrated_models=None):
    """Research inventory only; no max-EV frontier without calibrated models."""
    calibrated_models = calibrated_models or {}
    rows = []
    for c in candidates or []:
        tk = c.get("ticker")
        pkg = build(
            tk,
            c.get("price"),
            c.get("market_cap"),
            c.get("conviction", 50),
            c.get("direction", "Long"),
            c.get("thesis_key"),
            calibrated_models.get(tk),
        )
        rows.append({
            "ticker": tk,
            "thesis": thesis_for(tk),
            "status": pkg.get("status"),
            "permission": pkg.get("permission"),
            "ev_pct": None,
            "upside_pct": None,
            "downside_pct": None,
            "tail_ratio": None,
            "weight": None,
            "targets": None,
            "reason": pkg.get("reason"),
        })
    return {
        "candidates": rows,
        "frontier": {},
        "status": "MODEL_REQUIRED",
        "permission": "CAPITAL_BLOCKED",
        "note": "No candidate is ranked by EV until calibrated evidence exists.",
    }
