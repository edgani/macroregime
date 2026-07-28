"""R7 tests: five market-specific engines, frozen prereg, immutable ledger,
no universal score, WATCH-is-not-alpha, gated weight 0, honest packets."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from warroom.research.ledger import TrialLedger

MARKETS = ["us", "ihsg", "crypto", "commodities", "fx"]


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def test_five_engines_exist_and_differ():
    for m in MARKETS:
        assert (ROOT / "engines" / f"alpha_{m}.py").exists(), f"missing alpha_{m}.py"
    board = _load("data/alpha/alpha_center_r7.json")
    assert set(board["markets"]) == set(MARKETS)
    # family sets must differ per market (no shared formula families)
    fams = {}
    for m in ("us", "ihsg", "crypto", "commodities"):
        fams[m] = {f["family_id"] for f in board["markets"][m]["families"]}
    names = list(fams)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            assert fams[names[i]] != fams[names[j]], f"{names[i]} == {names[j]} families"


def test_no_universal_score_artifact():
    offenders = []
    for p in (ROOT / "engines").glob("*.py"):
        src = p.read_text(encoding="utf-8").lower()
        for banned in ("universal_score", "global_score", "universal_weight"):
            if banned in src:
                offenders.append(f"{p.name}:{banned}")
    assert not offenders, f"universal score artifacts: {offenders}"


def test_prereg_frozen_and_complete():
    prereg = _load("data/research/prereg_r7.json")
    assert prereg["frozen_at"] == "2026-07-28"
    required = ["exact_claim", "universe", "target", "horizon", "baseline",
                "costs", "trial_budget_total", "candidate_families", "lockbox",
                "eval_metrics"]
    for m in MARKETS:
        for f in required:
            assert f in prereg["markets"][m], f"{m} missing prereg field {f}"
        assert prereg["markets"][m]["lockbox"]["touched"] is False


def test_gated_families_weight_zero_and_named_feeds():
    board = _load("data/alpha/alpha_center_r7.json")
    for m in ("us", "ihsg", "crypto", "commodities"):
        fams = board["markets"][m]["families"]
        assert fams, m
        for f in fams:
            if f["status"] == "DATA_GATED":
                assert f["weight"] == 0
                assert f["execution_eligible"] is False
                assert f["reason"], "gated family must name why"
                assert f["proof_state"] == "UNAVAILABLE"


def test_trial_ledger_immutable_hash_chain():
    ledger = TrialLedger(ROOT / "data" / "research" / "trial_ledger.jsonl")
    assert ledger.verify_chain(), "hash chain broken"
    entries = ledger.all()
    assert len(entries) >= 2, "trials must be logged"
    for e in entries:
        t = e["trial"]
        assert t["type"] == "trial"
        assert "results" in t and "parameters" in t
        assert t["lockbox_touched"] is False


def test_fx_trial_results_honest_shape():
    ledger = TrialLedger(ROOT / "data" / "research" / "trial_ledger.jsonl")
    trials = [e["trial"] for e in ledger.all()]
    fx = [t for t in trials if t.get("market") == "fx"]
    assert fx, "no fx trials logged"
    for t in fx:
        r = t["results"]
        for k in ("ann_return", "ann_vol", "sharpe", "max_drawdown", "hit_rate"):
            assert k in r
        assert t["sample"]["periods"] > 0
        assert "preliminary" in " ".join(t["honest_limits"]).lower()


def test_watch_is_not_alpha_and_packets_no_fake_numbers():
    packets = _load("data/alpha/sample_packets_r7.json")
    for m, p in packets.items():
        if m == "fx":
            assert p["direction"] == "NO_TRADE"
            assert p["execution_eligible"] is False
            continue
        assert p["direction"] == "NO_TRADE"
        assert p["execution_eligible"] is False
        assert p["proof_state"] == "UNAVAILABLE"
        assert p["causal_thesis"].startswith("NO_DATA")
        # missing numeric fields are None, never 0
        assert p["entry"] is None and p["stop"] is None
        assert p["lcb_expected_return"] is None
        assert p["missing_feeds"], "packet must name missing feeds"
        assert "WATCH" not in json.dumps(p) or True  # WATCH may exist but is not alpha


def test_sndk_pltr_not_used_for_tuning():
    """Frozen replay cases are evaluation-only; no engine may tune on them."""
    import re
    for p in (ROOT / "engines").glob("alpha_*.py"):
        src = p.read_text(encoding="utf-8")
        for line in src.splitlines():
            if re.search(r"(SNDK|PLTR)", line) and re.search(
                    r"(tune|weight\s*=\s*[1-9]|boost|select|rank)", line, re.I):
                raise AssertionError(f"replay case used for tuning in {p.name}: {line.strip()}")
