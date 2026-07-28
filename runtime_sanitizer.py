"""Fail-closed sanitation for the active V9.8 runtime payload.

Risk fields such as entry, stop and target are retained because V9.8 binds them to a causal ticker
packet and proof/risk gate. Only explicitly technical-analysis fields are removed.
"""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any
DROP_TOP_LEVEL={"market_breadth","rotation_snapshot","regime_tf","regional","cycle_rotation","technical","technical_analysis","price_action"}
DROP_KEYS={"setup_rank","technical_stop","technical_target","sma","ema","rsi","macd","stochastic","vwap","momentum","relative_strength","breakout","candlestick","support","resistance","price_breadth","above_50d_pct","advance_pct"}

def sanitize_runtime_payload(payload:Any,*,_path:tuple[str,...]=())->Any:
    if isinstance(payload,Mapping):
        out={}
        for key,value in payload.items():
            text=str(key).strip().lower()
            if not _path and text in DROP_TOP_LEVEL:continue
            if text in DROP_KEYS:continue
            out[key]=deepcopy(value) if _path and _path[0]=='no_technical_analysis_policy' else sanitize_runtime_payload(value,_path=_path+(text,))
        return out
    if isinstance(payload,Sequence) and not isinstance(payload,(str,bytes,bytearray)):
        return [sanitize_runtime_payload(item,_path=_path) for item in payload]
    return deepcopy(payload)
