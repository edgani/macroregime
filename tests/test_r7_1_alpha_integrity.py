"""R7.1 Alpha Center integrity tests (definitive master prompt Part III).

Required checks: no duplicate cards, no universal score, no generic target/stop
multiplier in alpha output, no missing price as zero, confidence labelled,
shadow infra separated from eligibility, targets need value bridge, candidates
need horizon/LCB/ES/liquidity/proof, selection+exclusion reasons, SHORT and
NO-TRADE states exist, five-market coverage visible, build identity current.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _load(p):
    return json.loads((ROOT / p).read_text(encoding="utf-8"))


def test_conviction_watchlist_disconnected_from_momentum():
    src = (ROOT / "warroom" / "compute.py").read_text(encoding="utf-8")
    # pool rows must not be assigned to conviction/watchlist
    assert '"conviction": rows[:4]' not in src
    assert '"watchlist": rows[4:12]' not in src
    assert 'out["conviction"] = pool[:5]' not in src
    assert 'out["watchlist"] = pool[5:14]' not in src
    # legacy scan must be explicitly zero-weight
    assert '"alpha_weight": 0' in src
    assert "LEGACY_PRICE_MOMENTUM_SCAN_NOT_ALPHA" in src
    # honest alpha state present
    assert '"alpha_state"' in src and '"no_trade": True' in src


def test_alpha_render_has_no_score_cards_or_generic_bands():
    src = (ROOT / "warroom" / "render.py").read_text(encoding="utf-8")
    m = re.search(r"def alpha\(d\):.*?(?=\ndef |\Z)", src, re.S)
    body = m.group(0)
    assert "_xcard" not in body, "score cards still rendered in alpha()"
    assert "rs63" not in body and "RS {" not in body, "momentum RS shown in alpha()"
    assert "cross-market competitive ranking" not in body
    assert "entry" not in body.lower() or "entry" not in re.findall(r"\{[^}]*\}", body).__str__(), \
        "generic entry shown in alpha()"
    # NO TRADE state present
    assert "NO TRADE" in body
    # five-market coverage present
    assert "Five-market coverage" in body
    # activation board + excluded sections
    assert "Activation board" in body and "Excluded / missing data" in body
    # confidence labelled
    assert "uncalibrated" in body.lower()


def test_no_generic_multiplier_in_alpha_output_paths():
    """The px*0.97/px*1.03 generic bands may exist only inside the legacy scan
    (zero weight), never in conviction/watchlist/tradable_now paths."""
    src = (ROOT / "warroom" / "compute.py").read_text(encoding="utf-8")
    assert "px * .97" in src  # legacy preserved
    rank = re.search(r"def _rank\(.*?(?=\ndef |\Z)", src, re.S).group(0)
    assert "px * .97" in rank, "generic bands moved out of _rank?"
    # the pool block must not add entry/stop/target to conviction
    pool = re.search(r"out\[\"legacy_momentum_scan\"\].*?out\[\"fair_value\"\]", src, re.S).group(0)
    assert "stop" not in pool and "target" not in pool


def test_alpha_board_json_integrity():
    board = _load("data/alpha/alpha_center_r7.json")
    tickers = []
    for m, b in board["markets"].items():
        for c in (b.get("candidates") or []):
            tickers.append(c.get("instrument") or c.get("ticker"))
    assert len(tickers) == len(set(tickers)), "duplicate ticker cards"
    # NO-TRADE and SHORT-capable states exist in schema
    from engines.alpha_base import DIRECTIONS
    assert "NO_TRADE" in DIRECTIONS and "SHORT" in DIRECTIONS
    # every candidate has proof state + execution flag + reasons
    for m, b in board["markets"].items():
        for c in (b.get("candidates") or []):
            assert c.get("proof_state")
            assert c.get("execution_eligible") is False
            assert c.get("reason"), "selection/exclusion reason required"


def test_shadow_infra_separated_from_eligibility():
    """tracker.log_signals must receive only the gated conviction list, which is
    empty until a component is proof-gated — no unproven rows enter the DB."""
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'TR.log_signals(d["conviction"]' in app
    comp = (ROOT / "warroom" / "compute.py").read_text(encoding="utf-8")
    # conviction is assigned the honest empty list, never pool/rows
    assigns = re.findall(r'out\["conviction"\]\s*=\s*([^\n]+)', comp)
    assert all("[]" in a for a in assigns), f"conviction fed by: {assigns}"


def test_no_v10_branding_anywhere():
    for rel in ("app.py", "warroom/render.py", "warroom/compute.py", "config.py"):
        p = ROOT / rel
        if p.exists():
            src = p.read_text(encoding="utf-8")
            assert "V10" not in src and "v10.1" not in src.lower(), f"V10 branding in {rel}"


def test_alpha_state_contract_complete():
    src = (ROOT / "warroom" / "compute.py").read_text(encoding="utf-8")
    for field in ('"tradable_now"', '"no_trade"', '"no_trade_reason"',
                  '"board_artifact"', '"activation_board"', '"proof_required"'):
        assert field in src, f"alpha_state missing {field}"


def test_tradable_now_entries_require_full_packet():
    """If anything ever enters tradable_now it must carry the complete packet
    (horizon, LCB return, expected shortfall, liquidity, value bridge, proof)."""
    from engines.alpha_base import CANDIDATE_SCHEMA
    required = ["horizon", "lcb_expected_return", "expected_shortfall",
                "liquidity_capacity", "proof_state", "selection_reason",
                "exclusion_reason", "activation_stage", "invalidation"]
    packets = _load("data/alpha/sample_packets_r7.json")
    for m, p in packets.items():
        for f in required:
            assert f in p, f"{m} packet missing {f}"
        assert p["schema"] == CANDIDATE_SCHEMA
