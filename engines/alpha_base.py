"""engines/alpha_base.py — shared canonical candidate-record machinery (R7).

Every market engine emits the same canonical schema; metrics/formulas/thresholds
stay market-specific (market_contracts.py). A family without admitted PIT data is
DATA_GATED: weight 0, execution_eligible False, exact missing feed named.
WATCH is never alpha. No universal score exists anywhere.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CANDIDATE_SCHEMA = "warroom.alpha_candidate.v1"
DIRECTIONS = ["LONG", "SHORT", "FRONT_RUN", "NEXT_BENEFICIARY", "WATCH",
              "LATE", "INVALIDATED", "NO_TRADE"]


def load_prereg() -> dict:
    return json.loads((ROOT / "data" / "research" / "prereg_r7.json").read_text(encoding="utf-8"))


def gated_family_records(market: str, prereg: dict) -> list:
    """One record per candidate family. DATA_GATED families get weight 0."""
    out = []
    for fam in prereg["markets"][market]["candidate_families"]:
        status = fam["status"]
        out.append({
            "schema": CANDIDATE_SCHEMA,
            "market": market,
            "family_id": fam["family_id"],
            "status": status,
            "weight": 0 if status != "PROVEN_FOR_EXACT_CLAIM" else None,
            "reason": fam.get("reason", "registered"),
            "execution_eligible": False,
            "proof_state": "UNAVAILABLE" if status == "DATA_GATED" else "MAPPED",
        })
    return out


def gated_candidate_packet(market: str, instrument: str, missing_feeds: list) -> dict:
    """Canonical per-instrument packet when fundamentals are gated.

    All decision fields are NO_DATA (never zero, never fabricated).
    """
    return {
        "schema": CANDIDATE_SCHEMA,
        "market": market,
        "instrument": instrument,
        "direction": "NO_TRADE",
        "stage": "RESEARCH_ONLY",
        "causal_thesis": "NO_DATA (fundamental feeds gated)",
        "bottleneck": "NO_DATA",
        "expectation_gap": "NO_DATA",
        "activation_stage": "RED_NOT_READY",
        "current_quote": "NO_DATA",
        "projection_low_base_high": None,
        "probability_weighted_target": None,
        "lcb_expected_return": None,
        "horizon": None,
        "return_velocity": None,
        "entry": None, "stop": None, "invalidation": None,
        "expected_shortfall": None,
        "liquidity_capacity": "NO_DATA",
        "selection_reason": "none — no admitted fundamental feed",
        "exclusion_reason": f"missing feeds: {', '.join(missing_feeds)}",
        "missing_feeds": missing_feeds,
        "proof_state": "UNAVAILABLE",
        "execution_eligible": False,
    }


def family_board(market: str) -> dict:
    prereg = load_prereg()
    fams = gated_family_records(market, prereg)
    n_gated = sum(1 for f in fams if f["status"] == "DATA_GATED")
    return {
        "schema": "warroom.alpha_family_board.v1",
        "market": market,
        "exact_claim": prereg["markets"][market]["exact_claim"],
        "baseline": prereg["markets"][market]["baseline"],
        "trial_budget_total": prereg["markets"][market]["trial_budget_total"],
        "families": fams,
        "summary": {"families": len(fams), "data_gated": n_gated,
                    "testable": len(fams) - n_gated},
        "note": "WATCH is not alpha; gated families have weight 0 and cannot affect capital",
    }
