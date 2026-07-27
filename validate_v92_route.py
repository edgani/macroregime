from pathlib import Path
import json
import tempfile

from provider_onboarding_v92 import run

ROOT = Path(__file__).resolve().parent
checks = []

def check(name, ok, detail=""):
    checks.append({"name": name, "status": "PASS" if ok else "FAIL", "detail": detail})

scope = json.loads((ROOT / "V92_SCOPE_LOCK.json").read_text())
registry = json.loads((ROOT / "V92_PROVIDER_ROUTE_REGISTRY.json").read_text())
check("five_exact_market_scopes", set(scope["markets"]) == {"us", "idx", "commodity", "fx", "crypto"})
check("zero_technical_predictors", scope.get("technical_predictors") == 0)
check("four_promotion_levels", set(scope["promotion_levels"]) == {"DATA_ADMITTED", "HISTORICAL_BLIND_PROVEN", "LIMITED_PRODUCTION_READY", "FULLY_PROVEN"})
check("five_provider_routes", set(registry["routes"]) == {"us", "idx", "commodity", "fx", "crypto"})

with tempfile.TemporaryDirectory() as td:
    env = Path(td) / "empty.env"
    env.write_text("", encoding="utf-8")
    audit = run(ROOT / "V92_PROVIDER_ROUTE_REGISTRY.json", env)
    check("empty_environment_fails_closed", audit["data_route_ready_markets"] == 0 and audit["capital_permission"] == "BLOCKED")
    # Satisfy all declared path IDs with non-empty fixtures; this only tests route executability.
    all_ids = set()
    for spec in registry["routes"].values():
        all_ids.update(spec.get("required", []))
        for bundles in (spec.get("required_any_of") or {}).values():
            for bundle in bundles[:1]:
                all_ids.update(bundle.get("files", []))
    lines = []
    for name in sorted(all_ids):
        p = Path(td) / f"{name}.csv"
        p.write_text("record_id,available_at,value\n1,2020-01-01T00:00:00Z,1\n", encoding="utf-8")
        lines.append(f"{name}={p}")
    full_env = Path(td) / "full.env"
    full_env.write_text("\n".join(lines), encoding="utf-8")
    audit = run(ROOT / "V92_PROVIDER_ROUTE_REGISTRY.json", full_env)
    check("route_can_reach_five_of_five_provider_ready", audit["data_route_ready_markets"] == 5)
    check("provider_ready_never_equals_trading_ready", audit["fully_proven_markets"] == 0 and audit["capital_permission"] == "BLOCKED")

status = "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL"
report = {"schema": "warroom.v92.route_validation.v1", "status": status, "checks": checks, "passed": sum(x["status"] == "PASS" for x in checks), "total": len(checks)}
(ROOT / "V92_FINAL_VALIDATION.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps(report, indent=2))
raise SystemExit(0 if status == "PASS" else 1)
