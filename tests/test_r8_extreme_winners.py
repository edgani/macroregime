"""R8 tests: frozen protocol, case-ticker isolation, baseline honesty, ledger,
DATA_GATED labelling, early-detection rule, universe report."""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def test_prereg_frozen_and_hashed():
    prereg = _load("data/research/prereg_r8.json")
    stored = prereg.pop("frozen_hash")
    assert hashlib.sha256(json.dumps(prereg, sort_keys=True).encode()).hexdigest() == stored
    assert prereg["frozen_before_any_evaluation"] is True
    assert prereg["evaluation_cases"]["rule"].startswith("evaluation only")
    assert prereg["winner_definitions_pct"] == [100, 200, 300, 500]
    assert prereg["loser_definitions_pct"] == [-50, -70]


def test_case_tickers_excluded_from_ranker():
    src = (ROOT / "tools/run_r8_tournament.py").read_text(encoding="utf-8")
    assert 'CASE_TICKERS = {"SNDK", "PLTR", "SPXC"}' in src
    assert "drop(columns=[c for c in CASE_TICKERS" in src
    res = _load("data/research/r8_tournament_results.json")
    assert res["universe"]["case_tickers_excluded"] == ["PLTR", "SNDK", "SPXC"]


def test_baseline_is_measurement_only():
    prereg = _load("data/research/prereg_r8.json")
    fams = {f["family_id"]: f for f in prereg["candidate_families"]}
    assert fams["baseline_momentum_topk"]["status"] == "BASELINE_MEASUREMENT_NOT_ALPHA"
    assert fams["baseline_momentum_topk"]["weight"] == 0
    assert fams["extreme_winner_discovery_causal"]["status"] == "DATA_GATED"
    assert fams["downside_short_detector_causal"]["status"] == "DATA_GATED"
    assert all(f["status"] == "DATA_GATED" and f["trial_budget"] == 0
               for f in prereg["candidate_families"] if "causal" in f["family_id"])


def test_tournament_metrics_complete_and_honest():
    res = _load("data/research/r8_tournament_results.json")
    assert len(res["baseline_results"]) == 2  # K=10, K=20 within budget
    for r in res["baseline_results"]:
        agg = r["aggregate"]
        for m in ("precision_at_k", "recall_at_k", "lift_vs_random", "mae_pct", "mfe_pct",
                  "lead_time_days", "remaining_return_pct", "false_discovery_rate",
                  "regime_precision", "n_decision_dates"):
            assert m in agg, f"missing {m}"
        assert 0 <= agg["precision_at_k"] <= 1 and 0 <= agg["false_discovery_rate"] <= 1
    assert "no Top-K causal ranking exists" in res["honesty_note"]


def test_trials_logged_with_chain():
    from warroom.research.ledger import TrialLedger
    ledger = TrialLedger(ROOT / "data/research/trial_ledger.jsonl")
    assert ledger.verify_chain()
    r8 = [t["trial"] for t in ledger.all() if t.get("trial", {}).get("family") == "us.baseline_momentum_topk"]
    assert len(r8) == 2
    assert all("BASELINE_MEASURED" in t["verdict"] for t in r8)


def test_case_reports_no_detection_claims():
    reps = _load("data/research/r8_case_reports.json")
    assert {r["instrument"] for r in reps["reports"]} == {"SNDK", "PLTR", "SPXC"}
    for rep in reps["reports"]:
        assert "NOT_CAPTURED" in rep["verdict"]
        for d in rep["decision_dates"]:
            if "detection_claim" in d:
                assert d["detection_claim"].startswith("NONE")
            # metrics present where forward data exists
            if d.get("crossed_100pct") is not None:
                assert "mae_pct" in d and "mfe_pct" in d and "lead_time_days" in d


def test_early_detection_rule_frozen():
    prereg = _load("data/research/prereg_r8.json")
    assert "precedes the +100% crossing" in prereg["early_detection_rule"]


def test_universe_report_declares_survivor_bias():
    txt = (ROOT / "docs/audit/R8_UNIVERSE_REPORT.md").read_text(encoding="utf-8")
    assert "NOT survivor-safe" in txt
    assert "BIASED UPWARD" in txt
    assert "CRSP" in txt
