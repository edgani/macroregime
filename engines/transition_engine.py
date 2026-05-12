"""engines/transition_engine.py — minimal TransitionEngine stub.
Computes basic quad-transition signal from GIP output. Replace with full
implementation when transition_engine logic is fleshed out.
"""
from __future__ import annotations
from types import SimpleNamespace


class TransitionEngine:
    def run(self, gip, prices, asset_ranges):
        sq = getattr(gip, "structural_quad", "Q3")
        mq = getattr(gip, "monthly_quad", "Q2")
        flip_hazard = float(getattr(gip, "flip_hazard", 0.25) or 0.25)
        scenario = "stable" if sq == mq else "transition"
        if flip_hazard > 0.6:
            window = "active"
        elif flip_hazard > 0.35:
            window = "building"
        else:
            window = "not yet"
        return SimpleNamespace(
            from_quad=sq,
            to_quad=mq,
            scenario=scenario,
            front_run_window=window,
            flip_hazard=flip_hazard,
        )
