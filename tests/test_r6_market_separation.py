"""R6 tests: market separation, contracts, bottleneck registry, activation clock,
frozen cohorts, blind replay honesty."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from warroom import market_contracts as MC
from warroom import activation as ACT

MARKETS = ["us", "ihsg", "crypto", "commodities", "fx"]


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


# ---- contracts ----

def test_five_contracts_complete_and_valid():
    assert set(MC.CONTRACTS) == set(MARKETS)
    assert MC.validate() == [], f"contract validation errors: {MC.validate()}"


def test_contracts_are_market_specific():
    inputs = {n: set(c["activation_inputs"]) for n, c in MC.CONTRACTS.items()}
    # no two markets share an identical input set
    names = list(inputs)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            assert inputs[names[i]] != inputs[names[j]]
    # spot-check: ihsg has broker/controller inputs, us does not
    assert "controller_action" in inputs["ihsg"]
    assert "controller_action" not in inputs["us"]
    assert "unlock_emission_schedule" in inputs["crypto"]
    assert "cftc_positioning" in inputs["commodities"]
    assert "cross_currency_basis" in inputs["fx"]


def test_no_forbidden_activation_inputs_anywhere():
    banned = {"rsi", "macd", "sma", "ema", "vwap", "chart_pattern", "momentum", "breakout"}
    for name, c in MC.CONTRACTS.items():
        tokens = {t for inp in c["activation_inputs"] for t in inp.lower().split("_")}
        assert not (tokens & banned), f"{name}: forbidden input tokens {tokens & banned}"


def test_no_universal_score_artifact():
    """Contracts define metrics per market; no shared weight/threshold set may exist."""
    weight_sets = {n: json.dumps(c["metrics"], sort_keys=True) for n, c in MC.CONTRACTS.items()}
    assert len(set(weight_sets.values())) == len(MARKETS), "markets share identical metric definitions"


# ---- bottleneck registry ----

def test_bottleneck_registry_schema():
    lines = (ROOT / "data/bottleneck/registry.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 10
    required = ["bottleneck_id", "market", "affected_instruments", "constrained_resource",
                "why_supply_cannot_respond", "demand_source", "current_stage", "winners",
                "invalidation", "source", "available_at", "evidence_quality", "proof_status"]
    for line in lines:
        rec = json.loads(line)
        for f in required:
            assert f in rec, f"record {rec.get('bottleneck_id')} missing {f}"
        assert rec["proof_status"] == "MAPPED", "curated chains are MAPPED, not proven"


# ---- activation board ----

def test_activation_board_states_valid_and_fail_closed():
    board = _load("data/bottleneck/activation_board.json")
    valid = {"RED_NOT_READY", "YELLOW_ARMING", "GREEN_ACTIVATE",
             "GREEN_ACTIVE_HOLD_ADD", "AMBER_LATE_TRIM", "BLACK_INVALIDATED_EXIT"}
    assert board["board"], "empty activation board"
    for b in board["board"]:
        assert b["state"] in valid
        assert b["state"] not in {"GREEN_ACTIVATE", "GREEN_ACTIVE_HOLD_ADD"}, \
            "GREEN requires admitted fundamental feeds — none admitted yet"
        assert b["missing_inputs"], "gated inputs must be listed explicitly"
    # every board entry references its market contract's claim limit
    for b in board["board"]:
        assert b.get("claim_limit")


def test_activation_evaluator_blocks_non_contract_inputs():
    rec = {"bottleneck_id": "x", "market": "ihsg", "current_stage": "ACTIVE",
           "affected_instruments": ["BBCA.JK"], "invalidation": "i", "proof_status": "MAPPED"}
    out = ACT.evaluate_thesis(rec)
    # ihsg active inputs must come from IHSG contract, not US
    ihsg_inputs = set(MC.IHSG_CONTRACT["activation_inputs"])
    assert set(out["active_inputs"]) <= ihsg_inputs
    assert set(out["missing_inputs"]) <= ihsg_inputs


# ---- frozen cohorts ----

def test_extreme_cohorts_frozen_and_computed():
    doc = _load("data/cohorts/extreme_cohorts.json")
    assert doc["frozen_at"] == "2026-07-28"
    assert doc["winner_thresholds_pct"] == [100, 200, 300, 500]
    assert doc["loser_thresholds_pct"] == [-50, -70]
    assert doc["survivorship_caveat"], "survivorship caveat mandatory"
    counts = {k: v["count"] for k, v in doc["cohorts"]["winners"].items()}
    assert counts["+100%"] >= counts["+200%"] >= counts["+300%"] >= counts["+500%"]
    assert counts["+500%"] > 0, "cohort must contain real extreme winners"
    for side in ("winners", "losers"):
        for k, v in doc["cohorts"][side].items():
            assert len(v["members"]) == v["count"]


# ---- blind replay ----

def test_blind_replay_price_facts_and_data_gates():
    doc = _load("data/bottleneck/case_studies/blind_replay_results.json")
    for case in ("SNDK", "PLTR"):
        rows = doc["cases"][case]["frozen_date_audit"]
        assert len(rows) >= 3
        ok = [r for r in rows if r["state"] == "PRICE_AUDIT_OK"]
        assert ok, f"{case}: no successful price audit"
        for r in ok:
            assert r["price_at_date"] > 0
            assert r["fundamental_activation"].startswith("DATA_GATED"), \
                "fundamental columns must be gated, never fabricated"
            assert r["topk_rank_stage"] == "PENDING_R7_SELECTOR_TOURNAMENT"
        # early-capture bar: at first frozen date, most of the move must remain
        first = ok[0]
        assert first["move_remaining_pct_of_full_history"] > 50, \
            f"{case}: frozen date too late to be a meaningful early-detection test"


def test_sndk_dram_nand_separation():
    case = _load("data/bottleneck/case_studies/sndk_pit_case.json")
    assert "NAND" in case["scope_note"] and "DRAM" in case["scope_note"]
    archs = {a["id"]: a for a in _load("data/bottleneck/archetypes.json")["archetypes"]}
    assert "conflat" in archs["memory_storage_capacity"]["claim_limit"].lower()
