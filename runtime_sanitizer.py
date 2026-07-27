"""Fail-closed sanitation for the active V8.1 runtime payload."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

DROP_TOP_LEVEL = {
    "market_breadth", "rotation_snapshot", "regime_tf", "regional", "cycle_rotation",
    "causal_chains", "technical", "technical_analysis", "price_action", "timing",
}
DROP_KEYS = {
    "setups", "setup_rank", "entry", "entry_px", "entry_type", "stop", "stop_price",
    "technical_stop", "technical_target", "sma", "ema", "rsi", "macd",
    "stochastic", "vwap", "momentum", "relative_strength", "breakout", "candlestick",
    "support", "resistance", "price_breadth", "above_50d_pct", "advance_pct",
}


def sanitize_runtime_payload(payload: Any, *, _path: tuple[str, ...] = ()) -> Any:
    if isinstance(payload, Mapping):
        out = {}
        for key, value in payload.items():
            text = str(key).strip().lower()
            if not _path and text in DROP_TOP_LEVEL:
                continue
            if text in DROP_KEYS:
                continue
            # Keep the policy itself, because it is the guardrail rather than a decision feature.
            if _path and _path[0] == "no_technical_analysis_policy":
                out[key] = deepcopy(value)
            else:
                out[key] = sanitize_runtime_payload(value, _path=_path + (text,))
        return out
    if isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        return [sanitize_runtime_payload(item, _path=_path) for item in payload]
    return deepcopy(payload)
