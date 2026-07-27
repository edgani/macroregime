"""Five-market V9.6 research factory orchestrator.

The orchestrator never invents candidate formulas or promotes missing evidence. It initializes the
frozen causal map, inspects each exact market workspace, executes the anti-overfit gate when all
artifacts exist and writes one machine-readable five-market status file.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

from anti_overfit_gate_v96 import evaluate
from causal_research_lifecycle_v96 import append_event, replay

HERE = Path(__file__).resolve().parent
MARKETS = ("us", "idx", "commodity", "fx", "crypto")
DEFAULT_ROOT = HERE / "runtime" / "v96_research"


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("JSON root must be an object")
    return raw


def initialize_market(market: str, *, root: Path = DEFAULT_ROOT, now: dt.datetime | None = None) -> dict[str, Any]:
    market = market.lower().strip()
    if market not in MARKETS:
        raise ValueError("unsupported market")
    now = (now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    maps = _json(HERE / "V96_MARKET_CAUSAL_MAPS.json")
    mapping = dict(maps["markets"][market])
    mapping["data_contract_hash"] = _sha(HERE / "V92_SCOPE_LOCK.json")
    workspace = root / market
    workspace.mkdir(parents=True, exist_ok=True)
    lifecycle = workspace / "research_lifecycle.jsonl"
    state = replay(lifecycle)
    if state.get("events", 0) == 0:
        event = {
            "event_id": f"{market}-map-{now.strftime('%Y%m%dT%H%M%SZ')}",
            "research_id": f"{market}-core-v96",
            "market": market,
            "event_type": "MAP_FREEZE",
            "payload": mapping,
        }
        append_event(lifecycle, event, now=now)
    return {
        "schema": "warroom.v96.market_workspace_init.v1",
        "market": market,
        "workspace": workspace.relative_to(HERE).as_posix() if HERE in workspace.resolve().parents else str(workspace),
        "lifecycle": replay(lifecycle),
        "capital_permission": "BLOCKED",
    }


def _market_paths(root: Path, market: str) -> dict[str, Path]:
    workspace = root / market
    return {
        "workspace": workspace,
        "lifecycle": workspace / "research_lifecycle.jsonl",
        "protocol": workspace / "anti_overfit_protocol.json",
        "seal": workspace / "anti_overfit_seal.json",
        "returns": workspace / "candidate_returns.csv",
        "report": workspace / "anti_overfit_report.json",
    }


def run_market(market: str, *, root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    paths = _market_paths(root, market)
    required = ["lifecycle", "protocol", "seal", "returns"]
    missing = [name for name in required if not paths[name].is_file()]
    if missing:
        return {
            "market": market,
            "workspace_ready": False,
            "missing": missing,
            "historical_statistical_pass": False,
            "historical_blind_proven": False,
            "capital_permission": "BLOCKED",
            "reason": "Required frozen research artifacts are missing.",
        }
    report = evaluate(
        returns_path=paths["returns"], lifecycle_path=paths["lifecycle"],
        protocol_path=paths["protocol"], seal_path=paths["seal"],
    )
    paths["report"].write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    return {
        "market": market,
        "workspace_ready": True,
        "missing": [],
        "historical_statistical_pass": bool(report.get("historical_statistical_pass")),
        "historical_blind_proven": bool(report.get("historical_blind_proven")),
        "selected_candidate_id": report.get("selected_candidate_id"),
        "report_path": paths["report"].relative_to(HERE).as_posix() if HERE in paths["report"].resolve().parents else str(paths["report"]),
        "report_hash": report.get("report_hash"),
        "errors": report.get("errors") or [],
        "failed_gates": sorted(name for name, passed in (report.get("gates") or {}).items() if passed is not True),
        "capital_permission": "BLOCKED_PENDING_ACTUAL_FILL_PROOF",
    }


def run_all(*, root: Path = DEFAULT_ROOT) -> dict[str, Any]:
    results = {market: run_market(market, root=root) for market in MARKETS}
    payload = {
        "schema": "warroom.v96.five_market_research_status.v1",
        "release": "War Room OS V9.6 Causal Anti-Overfit Research Factory",
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
        "markets": results,
        "pipeline_ready_markets": sum(bool(x.get("workspace_ready")) for x in results.values()),
        "historical_statistical_pass_markets": sum(bool(x.get("historical_statistical_pass")) for x in results.values()),
        "historical_blind_proven_markets": sum(bool(x.get("historical_blind_proven")) for x in results.values()),
        "live_capital_ready_markets": 0,
        "capital_permission": "BLOCKED",
        "claim_limit": "Historical anti-overfit proof cannot substitute for the separate prospective actual-fill proof gate.",
    }
    out = root / "V96_RESEARCH_STATUS.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["init", "run", "run-all", "status"])
    parser.add_argument("--market", choices=MARKETS)
    parser.add_argument("--root", default=str(DEFAULT_ROOT))
    args = parser.parse_args()
    root = Path(args.root)
    if args.command == "init":
        if args.market:
            result = initialize_market(args.market, root=root)
        else:
            result = {market: initialize_market(market, root=root) for market in MARKETS}
    elif args.command == "run":
        if not args.market:
            raise SystemExit("--market is required for run")
        result = run_market(args.market, root=root)
    elif args.command == "run-all":
        result = run_all(root=root)
    else:
        status_path = root / "V96_RESEARCH_STATUS.json"
        result = _json(status_path) if status_path.is_file() else run_all(root=root)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
