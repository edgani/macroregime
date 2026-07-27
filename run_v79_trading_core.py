"""Operator CLI for the V7.9 exact-scope final trading core.

The CLI never places a broker order. It emits one deterministic manual instruction and an
atomic JSON receipt. Only ``--live`` with dual-source consensus can be executable. CSV mode
is audit-only and always returns NO ORDER.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile

import pandas as pd
from dotenv import load_dotenv

from final_trading_core_v79 import CoreConfig, build_trade_instruction
from release_contract_v79 import release_contract
from us_broad_equity_live_feed_v79 import fetch_completed_monthly_closes

ROOT = Path(__file__).resolve().parent


def _truthy(raw: str | None, default: bool = False) -> bool:
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _float_or_none(raw: str | None) -> float | None:
    if raw in (None, ""):
        return None
    return float(raw)


def _csv_rows(path: str) -> list[dict]:
    d = pd.read_csv(path)
    date_col = "Date" if "Date" in d else "observed_month"
    close_col = "Close" if "Close" in d else ("SP500" if "SP500" in d else "close")
    return [{"observed_month": str(row[date_col]), "close": float(row[close_col])} for _, row in d.iterrows()]


def _atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False) as handle:
        handle.write(raw)
        tmp = Path(handle.name)
    os.replace(tmp, path)


def main() -> None:
    load_dotenv(ROOT / ".env", override=False)
    env_authorized = _truthy(os.getenv("WARROOM_V79_BASELINE_AUTHORIZED"), False)
    env_instrument = (os.getenv("WARROOM_V79_EQUITY_INSTRUMENT") or "SPY").strip().upper()
    env_sleeve = float(os.getenv("WARROOM_V79_SLEEVE_FRACTION", "1.0"))
    env_current = _float_or_none(os.getenv("WARROOM_V79_CURRENT_EQUITY_WEIGHT"))
    env_cost = _float_or_none(os.getenv("WARROOM_V79_ESTIMATED_ONE_WAY_COST_BPS"))

    ap = argparse.ArgumentParser()
    source = ap.add_mutually_exclusive_group(required=True)
    source.add_argument("--live", action="store_true", help="Production mode: requires FRED + Yahoo consensus.")
    source.add_argument("--csv", help="Audit/replay only; never creates an executable instruction.")
    ap.add_argument("--as-of")
    ap.add_argument("--instrument", default=env_instrument, choices=["SPY", "VOO", "IVV"])
    ap.add_argument("--sleeve-fraction", type=float, default=env_sleeve)
    auth = ap.add_mutually_exclusive_group()
    auth.add_argument("--authorize-baseline", dest="authorize_baseline", action="store_true")
    auth.add_argument("--no-authorize-baseline", dest="authorize_baseline", action="store_false")
    ap.set_defaults(authorize_baseline=env_authorized)
    ap.add_argument("--current-equity-weight", type=float, default=env_current)
    ap.add_argument("--estimated-cost-bps", type=float, default=env_cost)
    ap.add_argument("--output", default=str(ROOT / "runtime" / "v79_last_instruction.json"))
    args = ap.parse_args()

    if args.live:
        feed = fetch_completed_monthly_closes(as_of=args.as_of)
        rows = feed.observations
    else:
        feed = None
        rows = _csv_rows(args.csv)

    config = CoreConfig(
        equity_instrument=args.instrument,
        sleeve_fraction_of_account=args.sleeve_fraction,
        baseline_authorized=args.authorize_baseline,
    )
    live_verified = bool(feed and feed.status == "LIVE_DUAL_SOURCE_CONFIRMED" and feed.consensus_status == "PASS")
    instruction = build_trade_instruction(
        rows,
        config=config,
        as_of=args.as_of,
        current_equity_weight_in_sleeve=args.current_equity_weight,
        estimated_one_way_cost_bps=args.estimated_cost_bps,
        verified_live_feed=live_verified,
    )
    payload = {
        "schema": "warroom.v79.operator_receipt.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "mode": "LIVE_PRODUCTION" if args.live else "CSV_AUDIT_ONLY",
        "release_contract": release_contract(),
        "feed": feed.to_dict() if feed else {"status": "USER_CSV_AUDIT_ONLY", "path": str(Path(args.csv).resolve())},
        "configuration": {
            "instrument": args.instrument,
            "sleeve_fraction": args.sleeve_fraction,
            "baseline_authorized": args.authorize_baseline,
            "current_equity_weight": args.current_equity_weight,
            "estimated_one_way_cost_bps": args.estimated_cost_bps,
        },
        "instruction": instruction.to_dict(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["receipt_sha256"] = hashlib.sha256(canonical).hexdigest()
    _atomic_json(Path(args.output), payload)
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
