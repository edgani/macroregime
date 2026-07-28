"""Attach V7.8 checkpoint evidence and data-readiness state to dashboard snapshots."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import json

from release_contract_v78 import release_contract

ROOT = Path(__file__).resolve().parent


def _json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def attach_research_evidence_v78(desk: dict) -> dict:
    out = deepcopy(desk) if isinstance(desk, dict) else {}
    out["release_contract_v78"] = release_contract()
    out["research_evidence_v78"] = {
        "schema": "warroom.research_evidence.v78",
        "status": "CHECKPOINT_NOT_FINAL_TRADING_SYSTEM",
        "new_promoted_components": 0,
        "ticker_capital_permission": "BLOCKED",
        "confirmatory_results": {
            "cross_market_tsmom": _json(ROOT / "research_v78" / "results" / "V78_CROSS_MARKET_TSMOM_RESULTS.json"),
            "cross_market_sma10": _json(ROOT / "research_v78" / "results" / "V78_CROSS_MARKET_SMA10_RISK_CAP_RESULTS.json"),
            "us_equity_vol12": _json(ROOT / "research_v78" / "results" / "V78_US_EQUITY_VOL12_RISK_CAP_RESULTS.json"),
        },
        "data_readiness": {
            "pit_contract_fixture": _json(ROOT / "research_v78" / "results" / "V78_PIT_DATA_CONTRACT_FIXTURE_VALIDATION.json"),
            "membership_guard": _json(ROOT / "research_v78" / "results" / "V78_SP500_MEMBERSHIP_GUARD_VALIDATION.json"),
            "licensed_complete_us_pit_panel_loaded": False,
        },
        "prospective": {
            "forecast_ledger_path": "research_v78/prospective/V78_FORECAST_LEDGER.jsonl",
            "outcome_ledger_path": "research_v78/prospective/V78_OUTCOME_LEDGER.jsonl",
            "matured_forecasts": 0,
            "capital_permission": "SHADOW_ONLY_ZERO_CAPITAL",
        },
        "claim_boundary": "Proof infrastructure and negative confirmatory evidence only; no new trading permission.",
    }
    return out
