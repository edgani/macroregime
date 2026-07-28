"""V10.1 unified packet adapter."""
from __future__ import annotations
from typing import Any, Mapping

from decision_packet_v99 import MARKET_LABELS, build_packets as build_base_packets
from action_engine_v101 import enrich_packets, load_policy


def build_packets(*, markets: Mapping[str, Any], quotes: Mapping[str, Any], universe: Mapping[str, Any], proof_registry: Mapping[str, Any], current_context: Mapping[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, Any], dict[str, Any]]:
    base, _ = build_base_packets(markets=markets, quotes=quotes, universe=universe, proof_registry=proof_registry)
    packets, state = enrich_packets(base, current_context, load_policy())
    return packets, state["alpha_center"], state
