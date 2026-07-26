from __future__ import annotations
from dataclasses import asdict
from datetime import timezone
from typing import Sequence

from .contracts import ResearchObservationTicket, EvidenceStatus
from .data import OHLCVBar, validate_bars
from .hashing import canonical_hash
from .sensors import compute_mqa_benchmarks, compute_momentum_axes, true_ranges


def build_research_observation(bars: Sequence[OHLCVBar], *, formula_hashes: dict[str,str]) -> ResearchObservationTicket:
    quality=validate_bars(bars)
    if not quality.accepted: raise ValueError("data quality failed: "+",".join(quality.reason_codes))
    high=[b.high for b in bars]; low=[b.low for b in bars]; close=[b.close for b in bars]
    mqa=compute_mqa_benchmarks(high,low,close)[-1]
    momentum=compute_momentum_axes(close,true_ranges(high,low,close))[-1]
    as_of=bars[-1].available_at.astimezone(timezone.utc).isoformat()
    identity={"asset":bars[-1].asset,"timeframe":bars[-1].timeframe,"as_of":as_of,"source":quality.payload_hash,"formulas":formula_hashes}
    oid=canonical_hash(identity)
    return ResearchObservationTicket(
        observation_id=oid, asset=bars[-1].asset, timeframe=bars[-1].timeframe, as_of=as_of,
        source_snapshot_hash=quality.payload_hash or "",
        component_states={"mqa_benchmarks":asdict(mqa),"momentum_axes":asdict(momentum)},
        component_evidence={"mqa_benchmarks":EvidenceStatus.NOT_EVALUATED,"momentum_axes":EvidenceStatus.NOT_EVALUATED},
        reason_codes=("DESCRIPTIVE_ONLY","NO_CALIBRATED_PROBABILITY","NO_EXECUTION_MAP","SCOPE_NOT_EVALUATED"),
    )
