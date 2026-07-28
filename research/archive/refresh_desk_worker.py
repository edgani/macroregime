"""Build one War Room desk in a child process and atomically save it."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from alpha_foundry_adapter import attach_alpha_foundry
from consistency_guard import enforce_desk
from data.resilient_market_data import attach_quotes_to_desk
from desk_runtime import DESK_SCHEMA_VERSION, save_desk, utc_now_iso


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markets", required=True)
    parser.add_argument("--scope", choices=["fast", "full"], default="fast")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    markets = [value for value in args.markets.split(",") if value]
    os.environ["WARROOM_FAST_START"] = "1" if args.scope == "fast" else "0"

    import data_layer
    from run import build_desk

    data = data_layer.load_all(markets=markets, allow_live=True, force_refresh=args.force)
    desk = build_desk(data, top_per_market=20)
    desk = attach_alpha_foundry(desk)
    desk = attach_quotes_to_desk(desk, force_refresh=args.force)
    desk = enforce_desk(desk)
    desk.setdefault("meta", {})
    desk["meta"].update({
        "desk_schema_version": DESK_SCHEMA_VERSION,
        "refresh_scope": args.scope.upper(),
        "refresh_completed_at_utc": utc_now_iso(),
        "trading_permission": "RESEARCH_ONLY_PAPER_AND_LIVE_BLOCKED",
    })
    loaded = sum(int(((market.get("funnel") or {}).get("loaded") or 0)) for market in (desk.get("markets") or {}).values())
    if loaded <= 0:
        raise RuntimeError("Refresh completed without any real or cached market rows")
    save_desk(desk)
    print(json.dumps({"ok": True, "loaded": loaded, "scope": args.scope}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
