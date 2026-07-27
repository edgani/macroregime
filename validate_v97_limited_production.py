"""Adversarial validation for V9.7 limited-production trading controls."""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Any, Callable

import execution_reconciliation_v97 as XR
import trading_control_plane_v97 as TC
from trading_readiness_v97 import audit as readiness_audit

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def sha(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now_iso(now: dt.datetime) -> str:
    return now.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def quote_payload(now: dt.datetime, *, price: float = 500.0) -> dict[str, Any]:
    record = {
        "instrument": "SPY",
        "provider_symbol": "SPY",
        "asset_type": "US_UNLEVERED_ETF",
        "price": price,
        "currency": "USD",
        "provider_timestamp": now_iso(now),
        "provider": "YAHOO",
        "source": {"http_status": 200, "raw_sha256": "a" * 64, "final_url": "fixture://quote"},
        "received_at": now_iso(now),
        "age_seconds_at_collection": 0.0,
        "validation": "VALID_EXECUTION_REFERENCE",
        "predictor_eligible": False,
        "capital_eligible": False,
    }
    record["record_hash"] = sha(record)
    payload = {
        "schema": "warroom.v97.execution_quotes.v1",
        "generated_at": now_iso(now),
        "markets": {"us": {"SPY": record}, "idx": {}, "commodity": {}, "fx": {}, "crypto": {}},
        "failures": [], "markets_with_quote": 1, "quote_count": 1,
        "proof_status": "EXECUTION_REFERENCE_ONLY", "predictor_eligible": False,
        "capital_permission": "BLOCKED_PENDING_DECISION_AND_RISK_GATE",
    }
    payload["manifest_hash"] = sha(payload)
    return payload


def account_payload(now: dt.datetime) -> dict[str, Any]:
    return {
        "schema": "warroom.v97.account_state.v1",
        "account_id_hash": "b" * 64,
        "as_of": now_iso(now),
        "currency": "USD",
        "equity": 100000.0,
        "peak_equity": 100000.0,
        "daily_realized_pnl": 0.0,
        "weekly_realized_pnl": 0.0,
        "orders_today": 0,
        "open_positions": [],
    }


def decision_payload(now: dt.datetime, proof_path: str, proof_hash: str) -> dict[str, Any]:
    return {
        "schema": "warroom.v97.trade_decision.v1",
        "decision_id": "fixture-us-001",
        "created_at": now_iso(now),
        "market": "us",
        "instrument": "SPY",
        "asset_type": "US_UNLEVERED_ETF",
        "venue": "MANUAL_BROKER_EXPORT",
        "direction": "LONG",
        "order_type": "LIMIT",
        "time_in_force": "DAY",
        "entry_limit": 500.0,
        "stop_price": 490.0,
        "target_price": 520.0,
        "horizon_days": 20,
        "expected_net_return_pct": 4.0,
        "confidence_lower_bound_return_pct": 1.0,
        "invalidation": "Issuer and macro transmission evidence reverses before the target horizon.",
        "causal_thesis": {
            "trigger": "Confirmed improvement in real demand and funding conditions",
            "direct_effect": "Revenue and cash-generation expectation improves",
            "transmission": ["real demand", "company cash generation", "valuation bridge"],
            "value_recipient": "Approved instrument in the exact proof scope",
            "timing": "Within the frozen 20-day horizon",
            "interaction_conditions": ["credit stress does not worsen", "evidence remains available point-in-time"],
            "claim_limit": "Limited-production decision only; no claim outside the exact proof scope"
        },
        "feature_names": ["released_demand_surprise", "funding_condition_state", "cash_generation_revision"],
        "causal_map_hash": "c" * 64,
        "proof_binding": {"proof_run_path": proof_path, "proof_run_sha256": proof_hash, "required_state": "LIMITED_PRODUCTION_ELIGIBLE"},
        "instrument_spec": {"currency": "USD", "contract_multiplier": 1.0, "quantity_step": 1.0, "minimum_quantity": 1.0, "maximum_quantity": 10.0, "board_lot": 1.0, "expiry": None, "tick_size": 0.01},
    }


def check(name: str, fn: Callable[[], bool], results: list[dict[str, Any]]) -> None:
    try:
        passed = bool(fn()); error = None if passed else "condition returned false"
    except Exception as exc:
        passed = False; error = f"{type(exc).__name__}: {exc}"
    results.append({"name": name, "passed": passed, "error": error})


def contains_error(result: dict[str, Any], text: str) -> bool:
    return any(text.lower() in str(x).lower() for x in result.get("errors") or [])


def main() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    fixture_root = HERE / "runtime" / "v97_validation_fixture"
    shutil.rmtree(fixture_root, ignore_errors=True); fixture_root.mkdir(parents=True)
    original_registry = TC.REGISTRY_PATH.read_bytes()
    original_tc_paths = (TC.RUNTIME, TC.LEDGER_PATH, TC.KILL_SWITCH_PATH)
    original_xr_paths = (XR.RUNTIME, XR.LEDGER, XR.FILLED_DIR, XR.PENDING_DIR)
    try:
        runtime = fixture_root / "trading"
        TC.RUNTIME = runtime; TC.LEDGER_PATH = runtime / "order_ledger.jsonl"; TC.KILL_SWITCH_PATH = runtime / "KILL_SWITCH.json"
        XR.RUNTIME = runtime; XR.LEDGER = runtime / "order_ledger.jsonl"; XR.FILLED_DIR = runtime / "orders" / "filled"; XR.PENDING_DIR = runtime / "orders" / "pending"
        now = dt.datetime.now(UTC).replace(microsecond=0)
        proof = {
            "schema": "warroom.v97.blind_proof_run.v1", "market": "us", "trading_ready": True,
            "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE", "signed_receipt_verification": {"valid": True},
            "errors": [], "validation_kind": "ADVERSARIAL_FIXTURE_ONLY_NOT_INSTALLABLE",
        }
        proof_path_abs = fixture_root / "proof_us.json"; proof_path_abs.write_text(json.dumps(proof, indent=2), encoding="utf-8")
        proof_bytes = proof_path_abs.read_bytes(); proof_rel = proof_path_abs.relative_to(HERE).as_posix(); proof_hash = file_sha(proof_path_abs)
        registry = json.loads(original_registry)
        row = next(iter(registry["components"].values()))
        for item in registry["components"].values():
            item["proof_run_path"] = None; item["proof_run_sha256"] = None
        row["proof_run_path"] = proof_rel; row["proof_run_sha256"] = proof_hash
        TC.REGISTRY_PATH.write_text(json.dumps(registry, indent=2), encoding="utf-8")
        decision = decision_payload(now, proof_rel, proof_hash); account = account_payload(now); quotes = quote_payload(now)
        policy = TC._policy()

        check("policy schema and auto-submit disabled", lambda: policy["schema"] == "warroom.v97.limited_production_policy.v1" and policy["execution_rules"]["auto_submit_enabled"] is False, results)
        check("five market execution routes defined", lambda: set(policy["market_routes"]) == TC.MARKETS, results)
        check("flat decision produces no trade", lambda: TC.evaluate({**decision, "direction": "FLAT"}, account, quotes, now=now)["state"] == "NO_TRADE", results)
        base = TC.evaluate(decision, account, quotes, now=now)
        check("valid exact-scope fixture reaches human approval only", lambda: base["pretrade_pass"] is True and base["state"] == "AWAITING_HUMAN_APPROVAL" and base["exportable"] is False, results)
        check("sizing respects one percent notional cap", lambda: base["sizing"]["notional_pct_equity"] <= 1.0 + 1e-9, results)
        check("stale decision rejected", lambda: contains_error(TC.evaluate({**decision, "created_at": now_iso(now-dt.timedelta(hours=1))}, account, quotes, now=now), "decision is stale"), results)
        check("future decision rejected", lambda: contains_error(TC.evaluate({**decision, "created_at": now_iso(now+dt.timedelta(hours=1))}, account, quotes, now=now), "future"), results)
        stale_q = copy.deepcopy(quotes); stale_q["markets"]["us"]["SPY"]["provider_timestamp"] = now_iso(now-dt.timedelta(minutes=10)); stale_q["markets"]["us"]["SPY"]["record_hash"] = sha({k:v for k,v in stale_q["markets"]["us"]["SPY"].items() if k!="record_hash"})
        check("stale quote rejected", lambda: contains_error(TC.evaluate(decision, account, stale_q, now=now), "quote is stale"), results)
        future_q = copy.deepcopy(quotes); future_q["markets"]["us"]["SPY"]["provider_timestamp"] = now_iso(now+dt.timedelta(minutes=10)); future_q["markets"]["us"]["SPY"]["record_hash"] = sha({k:v for k,v in future_q["markets"]["us"]["SPY"].items() if k!="record_hash"})
        check("future quote rejected", lambda: contains_error(TC.evaluate(decision, account, future_q, now=now), "future"), results)
        tampered_q = copy.deepcopy(quotes); tampered_q["markets"]["us"]["SPY"]["price"] = 501.0
        check("quote hash tamper rejected", lambda: contains_error(TC.evaluate(decision, account, tampered_q, now=now), "quote record hash mismatch"), results)
        check("missing quote rejected", lambda: contains_error(TC.evaluate(decision, account, {**quotes, "markets": {}}, now=now), "quote is missing"), results)
        check("proof hash mismatch rejected", lambda: contains_error(TC.evaluate({**decision, "proof_binding": {**decision["proof_binding"], "proof_run_sha256": "d"*64}}, account, quotes, now=now), "hash"), results)
        unbound_registry = copy.deepcopy(registry); next(iter(unbound_registry["components"].values()))["proof_run_path"] = None; next(iter(unbound_registry["components"].values()))["proof_run_sha256"] = None; TC.REGISTRY_PATH.write_text(json.dumps(unbound_registry), encoding="utf-8")
        check("unbound proof rejected", lambda: contains_error(TC.evaluate(decision, account, quotes, now=now), "not uniquely bound"), results)
        TC.REGISTRY_PATH.write_text(json.dumps(registry), encoding="utf-8")
        invalid_proof = copy.deepcopy(proof); invalid_proof["signed_receipt_verification"]={"valid":False}; proof_path_abs.write_text(json.dumps(invalid_proof), encoding="utf-8"); bad_hash=file_sha(proof_path_abs); bad_dec=copy.deepcopy(decision); bad_dec["proof_binding"]["proof_run_sha256"]=bad_hash; registry_bad=copy.deepcopy(registry); next(iter(registry_bad["components"].values()))["proof_run_sha256"]=bad_hash; TC.REGISTRY_PATH.write_text(json.dumps(registry_bad), encoding="utf-8")
        check("invalid signed receipt rejected", lambda: contains_error(TC.evaluate(bad_dec, account, quotes, now=now), "signed receipt"), results)
        proof_path_abs.write_bytes(proof_bytes); TC.REGISTRY_PATH.write_text(json.dumps(registry), encoding="utf-8")
        tech = copy.deepcopy(decision); tech["feature_names"]=["RSI_signal"]
        check("technical predictor rejected", lambda: contains_error(TC.evaluate(tech, account, quotes, now=now), "forbidden technical"), results)
        missing_causal = copy.deepcopy(decision); missing_causal["causal_thesis"]["trigger"]=""
        check("missing causal field rejected", lambda: contains_error(TC.evaluate(missing_causal, account, quotes, now=now), "missing trigger"), results)
        wrong_geom = {**decision, "stop_price": 510.0}
        check("invalid long geometry rejected", lambda: contains_error(TC.evaluate(wrong_geom, account, quotes, now=now), "stop < entry < target"), results)
        low_rr = {**decision, "target_price": 508.0}
        check("low reward-risk rejected", lambda: contains_error(TC.evaluate(low_rr, account, quotes, now=now), "reward-to-risk"), results)
        low_expected = {**decision, "expected_net_return_pct": 0.1}
        check("low expected return rejected", lambda: contains_error(TC.evaluate(low_expected, account, quotes, now=now), "expected net return"), results)
        bad_lower = {**decision, "confidence_lower_bound_return_pct": -0.1}
        check("negative lower bound rejected", lambda: contains_error(TC.evaluate(bad_lower, account, quotes, now=now), "lower-bound"), results)
        far_entry = {**decision, "entry_limit": 510.0, "stop_price": 500.0, "target_price": 530.0}
        check("entry too far from quote rejected", lambda: contains_error(TC.evaluate(far_entry, account, quotes, now=now), "too far"), results)
        stale_account = {**account, "as_of": now_iso(now-dt.timedelta(minutes=10))}
        check("stale account state rejected", lambda: contains_error(TC.evaluate(decision, stale_account, quotes, now=now), "account state is stale"), results)
        daily_loss = {**account, "daily_realized_pnl": -600.0}
        check("daily loss kill threshold enforced", lambda: contains_error(TC.evaluate(decision, daily_loss, quotes, now=now), "daily loss"), results)
        weekly_loss = {**account, "weekly_realized_pnl": -1100.0}
        check("weekly loss kill threshold enforced", lambda: contains_error(TC.evaluate(decision, weekly_loss, quotes, now=now), "weekly loss"), results)
        drawdown = {**account, "equity": 97000.0, "peak_equity": 100000.0}
        check("drawdown kill threshold enforced", lambda: contains_error(TC.evaluate(decision, drawdown, quotes, now=now), "drawdown"), results)
        many_orders = {**account, "orders_today": 5}
        check("daily order count enforced", lambda: contains_error(TC.evaluate(decision, many_orders, quotes, now=now), "order-count"), results)
        many_positions = {**account, "open_positions": [{"market":"idx","direction":"LONG","notional":100,"open_risk":1} for _ in range(5)]}
        check("maximum open positions enforced", lambda: contains_error(TC.evaluate(decision, many_positions, quotes, now=now), "maximum open positions"), results)
        market_cap = {**account, "open_positions": [{"market":"us","direction":"LONG","notional":1450,"open_risk":1}]}
        check("market notional cap enforced", lambda: contains_error(TC.evaluate(decision, market_cap, quotes, now=now), "market notional"), results)
        gross_cap = {**account, "open_positions": [{"market":"idx","direction":"LONG","notional":4950,"open_risk":1}]}
        check("portfolio gross cap enforced", lambda: contains_error(TC.evaluate(decision, gross_cap, quotes, now=now), "gross-notional"), results)
        risk_cap = {**account, "open_positions": [{"market":"idx","direction":"LONG","notional":100,"open_risk":295}]}
        check("total open risk cap enforced", lambda: contains_error(TC.evaluate(decision, risk_cap, quotes, now=now), "open-risk"), results)
        TC.engage_kill_switch("fixture test", actor="validator")
        check("manual kill switch blocks order", lambda: contains_error(TC.evaluate(decision, account, quotes, now=now), "kill switch"), results)
        TC.release_kill_switch(actor="validator", explicit_text="RELEASE V97 KILL SWITCH")
        base = TC.evaluate(decision, account, quotes, now=now)
        secret="fixture-secret-which-is-long-enough"
        approval=TC.create_approval(base,account,approved_by="validator",secret=secret,now=now)
        check("valid HMAC approval verifies", lambda: TC.verify_approval(approval,base,account,secret=secret)==[], results)
        tampered_approval=copy.deepcopy(approval); tampered_approval["approved_by"]="attacker"
        check("approval tamper rejected", lambda: any("HMAC" in x for x in TC.verify_approval(tampered_approval,base,account,secret=secret)), results)
        exported=TC.export_order(decision,account,base,approval,secret=secret,output_dir=runtime/"orders"/"pending")
        check("order export is manual-only", lambda: exported["order"]["status"]=="READY_FOR_MANUAL_SUBMISSION" and exported["order"]["auto_submit"] is False, results)
        check("duplicate order export rejected", lambda: _raises(lambda: TC.export_order(decision,account,base,approval,secret=secret,output_dir=runtime/"orders"/"pending")), results)
        order=exported["order"]
        paper_fill={"schema":"warroom.v97.fill_receipt.v1","order_id":order["order_id"],"broker_order_id_hash":"e"*64,"account_id_hash":account["account_id_hash"],"market":"us","instrument":"SPY","venue":"MANUAL_BROKER_EXPORT","side":"BUY","filled_quantity":order["quantity"],"fill_price":500.0,"fees":1.0,"filled_at":now_iso(now+dt.timedelta(seconds=1)),"source":"BROKER_EXPORT","live":False}
        check("paper fill rejected", lambda: XR.reconcile(order,paper_fill)["status"]=="REJECTED", results)
        mismatch={**paper_fill,"live":True,"instrument":"QQQ"}
        check("fill instrument mismatch rejected", lambda: XR.reconcile(order,mismatch)["status"]=="REJECTED", results)
        live_fill={**paper_fill,"live":True}
        reconciled=XR.reconcile(order,live_fill)
        check("live account fill reconciles", lambda: reconciled["status"]=="RECONCILED", results)
        check("execution ledger hash chain valid", lambda: XR.verify_ledger()["valid"] is True and XR.verify_ledger()["events"]>=3, results)
        readiness=readiness_audit()
        check("readiness keeps alpha separate from software", lambda: readiness["operational_control_plane_ready_markets"]==5 and readiness["fully_proven_markets"]==0 and readiness["capital_permission"].startswith("BLOCKED"), results)
    finally:
        TC.REGISTRY_PATH.write_bytes(original_registry)
        TC.RUNTIME, TC.LEDGER_PATH, TC.KILL_SWITCH_PATH = original_tc_paths
        XR.RUNTIME, XR.LEDGER, XR.FILLED_DIR, XR.PENDING_DIR = original_xr_paths
        shutil.rmtree(fixture_root, ignore_errors=True)
    payload = {
        "schema": "warroom.v97.final_validation.v1",
        "release": "War Room OS V9.7 Limited-Production Trading Control Plane",
        "generated_at": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tests": results,
        "passed": sum(bool(x["passed"]) for x in results),
        "total": len(results),
        "all_passed": all(bool(x["passed"]) for x in results),
        "capital_claim": "NO_ALPHA_CLAIM; CONTROL_PLANE_ONLY",
    }
    payload["validation_hash"] = sha({k:v for k,v in payload.items() if k!="validation_hash"})
    (HERE / "V97_FINAL_VALIDATION.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return payload


def _raises(fn: Callable[[], Any]) -> bool:
    try: fn(); return False
    except Exception: return True


if __name__ == "__main__":
    main()
