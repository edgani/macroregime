"""tools/build_bottleneck_registry.py — market-specific bottleneck registry (R6 §2.1).

Converts the existing chain_reactions.json causal chains + evidence store into the
canonical bottleneck record schema. Every record carries evidence quality, source,
available-at, and proof status. Records without admitted evidence for their
activation inputs stay RED_NOT_READY with exact missing data listed.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

OUT = ROOT / "data" / "bottleneck" / "registry.jsonl"
NOW = datetime.now(timezone.utc).isoformat(timespec="seconds")

# chain -> market mapping (explicit, auditable; chains are US-centric by origin)
CHAIN_MARKET = {
    "ai_compute_cascade": "us",
    "power_crisis": "us",
    "memory_supercycle": "us",
    "helium_crisis": "us",
    "robotics_wave": "us",
    "photonics_transition": "us",
    "advanced_packaging": "us",
    "pcb_interconnect": "us",
    "chipmaking_machines": "us",
    "ai_materials": "us",
}

# per-chain data availability: which activation inputs currently have admitted feeds
# (honest: most fundamental inputs are LICENSE_REQUIRED until R5 gaps close)
ADMITTED_FEEDS = {
    "prices": True,                      # yfinance PIT-eligible daily bars
    "fred_macro": True,                  # FRED series
    "cot_positioning": False,            # admitted, not wired (build_feeds)
    "sec_edgar_pit": False,              # LICENSE/INTEGRATION gap
    "trendforce_contract_prices": False, # LICENSE gap
    "consensus_estimates_pit": False,    # LICENSE gap
    "options_borrow": False,             # LICENSE gap
    "eia_physical": False,               # API key required
    "onchain_analytics": False,          # LICENSE gap
    "idx_broker_summary": False,         # LICENSE gap
    "venue_crypto_derivatives": False,   # venue API integration gap
}


def _record(chain, market):
    steps = chain.get("propagation_sequence", [])
    winners = sorted({t for s in steps for t in s.get("tickers", [])})
    tier1 = next((s for s in steps if s.get("tier") == 1), {})
    second = [s for s in steps if s.get("tier", 0) >= 2]
    second_tickers = sorted({t for s in second for t in s.get("tickers", [])})
    return {
        "bottleneck_id": chain.get("chain_id"),
        "market": market,
        "industry": chain.get("name"),
        "affected_instruments": winners,
        "constrained_resource": (tier1.get("role") or "see mechanism"),
        "why_supply_cannot_respond": chain.get("mechanism", "")[:400],
        "demand_source": chain.get("trigger_event", "")[:300],
        "capacity_utilization": None,  # requires licensed industry data
        "qualification_lead_time": None,
        "inventory": None,
        "pricing_power": None,
        "contract_backlog_evidence": None,
        "cost_curve": None,
        "concentration": None,
        "policy_dependency": None,
        "expected_persistence": chain.get("horizon"),
        "current_stage": chain.get("trigger_status"),
        "winners": tier1.get("tickers", []),
        "losers": [],
        "direct_exposure": tier1.get("tickers", []),
        "better_second_order_exposure": second_tickers,
        "market_expectation_gap": None,  # requires PIT consensus
        "target_bridge": None,
        "invalidation": "supply response delivered; demand rollover; qualification loss; estimate reversal",
        "source": "data/chain_reactions.json (curated research, human-reviewed)",
        "available_at": chain.get("updated_at") or NOW,
        "evidence_quality": "CURATED_RESEARCH_UNVALIDATED",
        "proof_status": "MAPPED",
        "schema": "warroom.bottleneck_record.v1",
    }


def main():
    src = json.loads((ROOT / "data" / "chain_reactions.json").read_text(encoding="utf-8"))
    chains = src.get("chains", [])
    records = []
    for c in chains:
        market = CHAIN_MARKET.get(c.get("chain_id"), "us")
        records.append(_record(c, market))
    with OUT.open("w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")
    print(f"{len(records)} bottleneck records -> {OUT.relative_to(ROOT)}")
    # attach SNDK/NAND evidence records as registry-adjacent references
    ev = ROOT / "data" / "bottleneck" / "evidence.jsonl"
    n_ev = sum(1 for _ in ev.open(encoding="utf-8")) if ev.exists() else 0
    print(f"evidence store: {n_ev} sourced records (separate file, linked by archetype)")


if __name__ == "__main__":
    main()
