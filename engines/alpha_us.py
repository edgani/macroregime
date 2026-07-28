"""engines/alpha_us — us alpha engine (R7).

All candidate families are DATA_GATED: no admitted PIT fundamental feed exists
yet (see data/coverage/gap_registry.json). The engine emits the family board and
honest NO_TRADE packets. Weight 0, execution_eligible False, missing feeds named.
Nothing here is a signal.
"""
from __future__ import annotations

from engines.alpha_base import family_board, gated_candidate_packet

MARKET = "us"
MISSING_FEEDS = ['sec_edgar_pit', 'consensus_estimates_pit', 'trendforce_contract_prices', 'options_borrow']


def board() -> dict:
    return family_board(MARKET)


def sample_packet(instrument: str) -> dict:
    return gated_candidate_packet(MARKET, instrument, MISSING_FEEDS)
