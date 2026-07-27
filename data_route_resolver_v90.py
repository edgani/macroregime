"""Resolve the exact data route for a V9.0 market/model without weakening proof rules."""
from __future__ import annotations
from pathlib import Path
import json

REGISTRY_PATH = Path(__file__).with_name("V90_SOURCE_ROUTE_REGISTRY.json")

def resolve(market: str, available: dict) -> dict:
    reg=json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    market=market.lower().strip()
    if market not in reg["markets"]:
        raise ValueError(f"unsupported market: {market}")
    spec=reg["markets"][market]
    core=spec["core_roles"]
    optional=spec["optional_addons"]
    present=set(available.get("roles", []))
    missing_core=[r for r in core if r not in present]
    present_optional=[r for r in optional if r in present]
    return {
        "schema":"warroom.v90.route_resolution.v1",
        "market":market,
        "model_id":available.get("model_id"),
        "core_roles":core,
        "missing_core":missing_core,
        "optional_addons_present":present_optional,
        "data_admission_possible":not missing_core,
        "proof_ceiling":"DATA_ADMITTED" if not missing_core else "BLOCKED_DATA",
        "routes":spec["routes"],
        "claim_limit":"Optional add-ons cannot be silently imputed or transferred from another market."
    }

if __name__ == "__main__":
    import argparse
    p=argparse.ArgumentParser(); p.add_argument("market"); p.add_argument("--available-json",required=True); p.add_argument("--out")
    a=p.parse_args(); result=resolve(a.market,json.loads(Path(a.available_json).read_text()))
    text=json.dumps(result,indent=2); print(text)
    if a.out: Path(a.out).write_text(text,encoding="utf-8")
