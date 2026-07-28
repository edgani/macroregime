"""tools/build_alpha_center_r7.py — assemble R7 Alpha Center board + sample packets."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines import alpha_us, alpha_ihsg, alpha_crypto, alpha_commodities, alpha_fx
from warroom.research.ledger import TrialLedger


def main():
    boards = {m: mod.board() for m, mod in [
        ("us", alpha_us), ("ihsg", alpha_ihsg),
        ("crypto", alpha_crypto), ("commodities", alpha_commodities)]}

    ledger = TrialLedger(ROOT / "data" / "research" / "trial_ledger.jsonl")
    trials = [e["trial"] for e in ledger.all()]
    boards["fx"] = {
        "schema": "warroom.alpha_family_board.v1", "market": "fx",
        "families_tested": len({t["family"] for t in trials}),
        "trials_logged": len(trials),
        "results": [{"family": t["family"], "params": t["parameters"],
                     "results": t["results"],
                     "verdict": "PRELIMINARY_IN_SAMPLE_ONLY", "promoted": False}
                    for t in trials],
        "note": "Sharpe 0.31 / n=22 / excess~0 vs equal-weight baseline: no edge demonstrated; family weight 0 pending OOS + lockbox (R10)",
        "candidates": alpha_fx.candidate_board(trials),
    }

    out = {"schema": "warroom.alpha_center_r7.v1",
           "rule": "WATCH is not alpha; DATA_GATED weight 0; no universal score; preliminary tournament is not a signal",
           "markets": boards}
    (ROOT / "data" / "alpha").mkdir(exist_ok=True)
    (ROOT / "data" / "alpha" / "alpha_center_r7.json").write_text(json.dumps(out, indent=1), encoding="utf-8")

    packets = {
        "us": alpha_us.sample_packet("SNDK"),
        "ihsg": alpha_ihsg.sample_packet("BBCA.JK"),
        "crypto": alpha_crypto.sample_packet("BTC-USD"),
        "commodities": alpha_commodities.sample_packet("CL=F"),
        "fx": dict(boards["fx"]["candidates"][0], sample_pair="USDJPY"),
    }
    (ROOT / "data" / "alpha" / "sample_packets_r7.json").write_text(
        json.dumps(packets, indent=1), encoding="utf-8")
    print("alpha center board + sample packets written")
    print("gated families:", {m: b["summary"]["data_gated"]
                              for m, b in boards.items() if "summary" in b})


if __name__ == "__main__":
    main()
