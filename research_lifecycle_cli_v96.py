"""Operator CLI for the immutable V9.6 causal research lifecycle."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from causal_research_lifecycle_v96 import append_event, replay


def load_json(path: str) -> dict:
    raw=json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw,dict): raise ValueError("payload JSON must be an object")
    return raw


def main():
    ap=argparse.ArgumentParser(description="Append or inspect V9.6 research lifecycle events")
    ap.add_argument("command",choices=["append","status"])
    ap.add_argument("--ledger",required=True)
    ap.add_argument("--event")
    args=ap.parse_args(); ledger=Path(args.ledger)
    if args.command=="append":
        if not args.event: raise SystemExit("--event JSON is required")
        append_event(ledger,load_json(args.event))
    print(json.dumps(replay(ledger),indent=2,allow_nan=False))
if __name__=="__main__": main()
