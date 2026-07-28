"""R5 data-plane acceptance tests: universe masters, coverage gaps, PIT admission,
fast refresh, bottleneck evidence store, SNDK no-hardcode rule."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from warroom import pit

MARKETS = ["us", "ihsg", "crypto", "commodities", "fx"]
TIERS = {"TIER_A_FULL_DECISION", "TIER_B_RESEARCH_DISCOVERY", "TIER_C_REFERENCE_ONLY",
         "UNSUPPORTED_LICENSE_REQUIRED", "UNAVAILABLE"}


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


# ---- universe masters ----

def test_universe_masters_exist_all_markets():
    for m in MARKETS:
        doc = _load(f"data/universe/{m}.json")
        assert doc["meta"]["schema"] == "warroom.universe_master.v1"
        assert doc["meta"]["instrument_count"] > 0
        for inst in doc["instruments"]:
            assert inst["tier"] in TIERS, f"{m}:{inst['instrument']} bad tier"
            assert inst["market"] == m
            assert inst.get("source"), f"{m}:{inst['instrument']} missing source"


def test_us_master_full_listed_universe_with_delisted_history():
    doc = _load("data/universe/us.json")
    assert doc["meta"]["instrument_count"] > 10000, "US master must cover full listed universe"
    tiers = doc["meta"]["tiers"]
    assert tiers["TIER_A_FULL_DECISION"] > 100
    assert tiers["TIER_B_RESEARCH_DISCOVERY"] > 1000, "discovery tier must not be a hand-picked list"
    # ETFs must be explicitly labelled wherever they appear (execution/hedge instruments)
    etfs = [i for i in doc["instruments"] if i.get("etf")]
    assert etfs, "ETF labels missing from US master"
    tier_a_etfs = [e for e in etfs if e["tier"] == "TIER_A_FULL_DECISION"]
    assert all(e["etf"] for e in tier_a_etfs), "Tier A ETFs must be explicitly labelled"


def test_commodities_exact_contracts_registered():
    doc = _load("data/universe/commodities.json")
    futures = [i for i in doc["instruments"] if i.get("instrument_kind") == "future"]
    names = {f["instrument"] for f in futures}
    assert {"CL", "GC", "HG"} <= names, "WTI/Gold/Copper exact scopes required"
    for f in futures:
        assert f.get("multiplier") and f.get("delivery")
    # proxies labelled
    proxies = [i for i in doc["instruments"] if i.get("instrument_kind") == "etf_proxy"]
    assert proxies and all("proxy" in (p.get("note") or "") for p in proxies)


# ---- coverage gap registry ----

def test_gap_registry_complete_reasons():
    reg = _load("data/coverage/gap_registry.json")
    assert reg["schema"] == "warroom.coverage_gap_registry.v1"
    assert len(reg["gaps"]) >= 8
    for g in reg["gaps"]:
        assert g.get("reason"), f"gap {g.get('domain')} missing exact reason"
        assert g.get("provider_required"), f"gap {g.get('domain')} missing provider"
        assert g.get("recall_impact"), f"gap {g.get('domain')} missing recall impact"
        assert g["status"] in {"UNSUPPORTED_LICENSE_REQUIRED", "UNAVAILABLE"}


def test_coverage_report_quantifies_recall_risk():
    rep = _load("data/coverage/coverage_report.json")
    for m in MARKETS:
        assert m in rep["markets"], f"coverage report missing {m}"
        assert rep["recall_risk"].get(m), f"recall risk not quantified for {m}"


# ---- PIT admission ----

def test_pit_admission_schema_and_rules():
    rec = pit.admit("FRED", "us", "fred", "DGS10", {"value": 4.25},
                    release_ts="2026-07-25T13:30:00+00:00",
                    available_at="2026-07-25T14:00:00+00:00", vintage="2026-07-25")
    assert pit.validate(rec) == []
    assert pit.is_pit_eligible(rec, "2026-07-26") is True
    assert pit.is_pit_eligible(rec, "2026-07-24") is False
    bad = dict(rec, release_ts="2026-07-27T00:00:00+00:00")  # release AFTER available
    assert pit.validate(bad), "release after available must be rejected"
    bad2 = dict(rec, state="FRESH")
    assert pit.validate(bad2), "invalid state must be rejected"


def test_pit_missing_release_stays_null_not_zero():
    rec = pit.admit("yfinance", "us", "yahoo", "NVDA", {"close": 100.0})
    assert rec["release_ts"] is None  # unknown stays null, never fabricated


# ---- fast refresh snapshot ----

def test_fast_snapshot_published_all_markets():
    snap = _load("runtime/fast_snapshot.json")
    assert snap["schema"] == "warroom.fast_snapshot.v1"
    for m in MARKETS:
        mk = snap["markets"].get(m)
        assert mk, f"fast snapshot missing market {m}"
        assert mk.get("published_at"), f"{m} has no publish timestamp"
        assert mk["current"] > 0, f"{m} has no current quotes"
        for t, q in mk["quotes"].items():
            if q["state"] == "NO_DATA":
                assert q["price"] is None, f"{m}:{t} NO_DATA must have null price, not 0"
            else:
                assert q["price"] and q["price"] > 0, f"{m}:{t} bad price"


def test_refresh_status_shows_progress_and_errors():
    st = _load("runtime/refresh_status.json")
    assert st["schema"] == "warroom.refresh_status.v1"
    for m in MARKETS:
        assert st["markets"].get(m, {}).get("fast_state") in {"PUBLISHED", "ERROR"}


# ---- bottleneck store ----

def test_archetype_library_complete():
    lib = _load("data/bottleneck/archetypes.json")
    archs = lib["archetypes"]
    assert len(archs) >= 25
    required = ["id", "causal_role", "state_variables", "transmission", "monetization",
                "expected_lag", "supply_response", "substitutes", "invalidation",
                "claim_limit", "required_data", "markets"]
    for a in archs:
        for f in required:
            assert a.get(f) is not None, f"archetype {a.get('id')} missing {f}"
    ids = [a["id"] for a in archs]
    assert len(ids) == len(set(ids)), "duplicate archetype ids"
    assert "memory_storage_capacity" in ids, "SNDK-relevant archetype missing"


def test_evidence_store_sourced_and_pit_valid():
    lines = (ROOT / "data/bottleneck/evidence.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 5, "evidence store must be populated with real sourced records"
    for line in lines:
        rec = json.loads(line)
        assert rec.get("source") and rec.get("source_quality")
        assert rec.get("observation")
        assert pit.validate(rec["pit"]) == [], f"PIT invalid: {rec.get('evidence_id')}"
        assert rec["pit"]["state"] in pit.STATES


# ---- SNDK no-hardcode rule ----

def test_sndk_no_score_boost_in_code():
    """SNDK may appear in docs/data harnesses but NEVER as a score/rank boost in code."""
    for path in list((ROOT / "warroom").glob("*.py")) + list((ROOT / "engines").glob("*.py")):
        src = path.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r"SNDK", src):
            line_start = src.rfind("\n", 0, m.start()) + 1
            line = src[line_start:src.find("\n", m.end())]
            assert re.search(r"score|boost|rank|weight|conviction", line, re.I) is None, \
                f"SNDK hardcode in {path.name}: {line.strip()[:100]}"


def test_sndk_case_study_pit_structure():
    case = _load("data/bottleneck/case_studies/sndk_pit_case.json")
    assert case["rules"]["no_hardcode"]
    assert len(case["decision_dates"]) >= 3
    for dd in case["decision_dates"]:
        assert "PENDING" in dd["system_output_at_date"], \
            "case-study outputs must come from R7 blind replay, never hand-filled"
    assert "NAND" in case["scope_note"] and "DRAM" in case["scope_note"], \
        "NAND vs DRAM distinction must be explicit"
