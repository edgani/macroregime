"""engines/alpha_crypto — crypto alpha engine (R7).

All candidate families are DATA_GATED: no admitted PIT fundamental feed exists
yet (see data/coverage/gap_registry.json). The engine emits the family board and
honest NO_TRADE packets. Weight 0, execution_eligible False, missing feeds named.
Nothing here is a signal.
"""
from __future__ import annotations

from engines.alpha_base import family_board, gated_candidate_packet

MARKET = "crypto"
MISSING_FEEDS = ['onchain_analytics', 'venue_derivatives', 'stablecoin_flows']


def board() -> dict:
    return family_board(MARKET)


def sample_packet(instrument: str) -> dict:
    return gated_candidate_packet(MARKET, instrument, MISSING_FEEDS)
