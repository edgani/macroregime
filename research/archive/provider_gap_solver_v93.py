"""Explain the exact path from current files to 5/5 without conflating readiness levels."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PUBLIC_AUTOMATABLE = {
    "us": ["SEC_EVENT_ARCHIVE"],
    "idx": [],
    "commodity": ["OFFICIAL_PHYSICAL_VINTAGES", "CFTC_COT_HISTORY"],
    "fx": ["ALFRED_MACRO_VINTAGES", "BIS_AND_CENTRAL_BANK_HISTORY", "CFTC_TFF_HISTORY"],
    "crypto": ["BINANCE_PUBLIC_HISTORY", "DERIBIT_HISTORY", "CRYPTO_PROTOCOL_FUNDAMENTALS"],
}
LICENSED_OR_OFFICIAL_EXPORT = {
    "us": ["survivor_free_equity_bundle", "IBES_PIT", "CBOE_OPTIONS", "BORROW_HISTORY"],
    "idx": ["IDX_REFERENCE", "IDX_HISTORICAL_EOD_OR_LOG", "IDX_CORPORATE_ACTIONS", "IDX_ISSUER_FUNDAMENTALS", "IDX_CONTROLLER_FREE_FLOAT"],
    "commodity": ["CME_COMMODITY_HISTORY", "PHYSICAL_BASIS", "FREIGHT_STORAGE", "CME_COMMODITY_OPTIONS"],
    "fx": ["CME_FX_HISTORY", "FX_OPTIONS", "DEALER_FLOW", "REUTERS_POLL_HISTORY"],
    "crypto": ["CRYPTO_SUPPLY_UNLOCK_HISTORY", "KAIKO_L2", "COIN_METRICS_MARKET_DATA", "ENTITY_LABELLED_ONCHAIN"],
}
USER_ACCOUNT_EXPORT = {
    "us": ["BROKER_FILLS_US"], "idx": ["BROKER_FILLS_IDX"],
    "commodity": ["BROKER_FILLS_COMMODITY"], "fx": ["BROKER_FILLS_FX"],
    "crypto": ["CRYPTO_ACCOUNT_FILLS"],
}


def solve(audit_path: Path) -> dict[str, Any]:
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    markets = []
    for row in audit.get("markets", []):
        market = row["market"]
        missing_required = [name for name, item in row.get("required", {}).items() if not item.get("ready")]
        missing_alt = [g["group"] for g in row.get("required_any_of", []) if not g.get("ready")]
        markets.append({
            "market": market,
            "current_provider_ready": bool(row.get("data_route_ready")),
            "missing_required": missing_required,
            "missing_required_any_of": missing_alt,
            "public_automatable": PUBLIC_AUTOMATABLE[market],
            "licensed_or_official_export": LICENSED_OR_OFFICIAL_EXPORT[market],
            "user_account_export": USER_ACCOUNT_EXPORT[market],
            "cannot_be_created_by_model": ["real future fills", "24 months prospective evidence", "four realized regimes"],
            "next_action": "RUN_PUBLIC_BOOTSTRAP_THEN_IMPORT_LICENSED_DATA_AND_LIVE_FILLS",
        })
    return {
        "schema": "warroom.v93.gap_solver.v1",
        "markets": markets,
        "provider_ready": sum(int(x["current_provider_ready"]) for x in markets),
        "fully_proven": 0,
        "capital_permission": "BLOCKED",
        "truth": "The software can automate public collection and validate imports, but it cannot manufacture licensed history, user account fills, or elapsed prospective time."
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", default="V92_CURRENT_5_OF_5_AUDIT.json")
    parser.add_argument("--out", default="V93_CURRENT_GAP_MAP.json")
    args = parser.parse_args()
    result = solve(Path(args.audit))
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
