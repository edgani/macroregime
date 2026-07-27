"""Non-mutating release and adversarial validation for War Room OS V9.5."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import py_compile
import tempfile
from pathlib import Path
from typing import Any, Callable

import pandas as pd

import autonomous_public_data_plane_v95 as collector
import proof_registry
from global_market_promotion_gate_v95 import evaluate_all
from realized_performance_gate_v95 import TRADE_REQUIRED, EQUITY_REQUIRED, validate_trade_ledger, validate_equity_ledger
from shadow_execution_ledger_v95 import append_forecast, append_order_intent, append_shadow_fill, verify as verify_shadow
from blind_proof_runner_v95 import run as run_blind_proof
from live_trade_normalizer_v95 import normalize as normalize_trades
from equity_ledger_normalizer_v95 import normalize as normalize_equity

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def trade_row(**overrides: Any) -> dict[str, Any]:
    h = "1" * 64
    row: dict[str, Any] = {
        "trade_id": "T1", "forecast_id": "F95_TEST0001", "strategy_id": "S1", "market": "us",
        "security_id": "TEST", "direction": "LONG", "entry_fill_at": "2020-01-02T00:00:00Z",
        "exit_fill_at": "2022-01-03T00:00:00Z", "quantity": 1, "entry_price": 100,
        "exit_price": 110, "commission": 0, "fees": 0, "spread_cost": 0, "slippage_cost": 0,
        "impact_cost": 0, "borrow_cost": 0, "financing_cost": 0, "taxes": 0, "regime": "R1",
        "regime_definition_hash": h, "adv_notional": 100000, "borrow_available": "False",
        "source_snapshot_hash": h, "execution_source": "BROKER_EXPORT", "is_live": "True",
        "paper": "False", "synthetic": "False", "account_id_hash": h,
        "entry_order_id_hash": "2" * 64, "exit_order_id_hash": "3" * 64,
    }
    row.update(overrides)
    return row


def equity_rows(account: str = "1" * 64) -> pd.DataFrame:
    h = "4" * 64
    return pd.DataFrame([
        {"timestamp": "2020-01-01T00:00:00Z", "net_liquidation_value": 100000,
         "stress_net_liquidation_value": 100000, "external_cash_flow": 0,
         "account_id_hash": account, "source_snapshot_hash": h, "execution_source": "BROKER_EXPORT",
         "is_live": "True", "paper": "False", "synthetic": "False", "stress_model_hash": "5" * 64},
        {"timestamp": "2022-01-04T00:00:00Z", "net_liquidation_value": 100010,
         "stress_net_liquidation_value": 100008, "external_cash_flow": 0,
         "account_id_hash": account, "source_snapshot_hash": h, "execution_source": "BROKER_EXPORT",
         "is_live": "True", "paper": "False", "synthetic": "False", "stress_model_hash": "5" * 64},
    ], columns=EQUITY_REQUIRED)


def run_validation() -> dict[str, Any]:
    tests: list[dict[str, Any]] = []

    def check(name: str, fn: Callable[[], Any]) -> None:
        try:
            detail = fn()
            passed = bool(detail if isinstance(detail, bool) else detail.get("pass", False))
            tests.append({"name": name, "pass": passed, "detail": detail if isinstance(detail, (str, int, float, bool, type(None), list, dict)) else str(detail)})
        except Exception as exc:
            tests.append({"name": name, "pass": False, "detail": f"{type(exc).__name__}: {exc}"})

    def compile_all() -> dict[str, Any]:
        files = sorted(p for p in HERE.rglob("*.py") if "__pycache__" not in p.parts)
        failures = []
        with tempfile.TemporaryDirectory() as temp:
            for index, path in enumerate(files):
                try:
                    py_compile.compile(str(path), cfile=str(Path(temp) / f"{index}.pyc"), doraise=True)
                except Exception as exc:
                    failures.append(f"{path.relative_to(HERE)}: {exc}")
        return {"pass": not failures, "files": len(files), "failures": failures}

    check("all_python_compiles", compile_all)

    def identity() -> dict[str, Any]:
        targets = ["app.py", "run.py", "dashboard.html", "research_kernel.py", "proof_registry.py", "README.md", "START_HERE.md"]
        stale = []
        for name in targets:
            text = (HERE / name).read_text(encoding="utf-8")
            if "V9.1" in text or "v9.1" in text or "V9.0" in text or "v9.0" in text:
                stale.append(name)
        return {"pass": not stale, "stale_files": stale}
    check("release_identity_consistent", identity)

    def registry_default_blocked() -> dict[str, Any]:
        raw = proof_registry.load_registry(); rows = raw.get("components", {})
        active = [name for name, row in rows.items() if row.get("decision_active") or row.get("capital_permission") != "BLOCKED" or float(row.get("live_weight", 0)) != 0]
        desk = proof_registry.attach_proof_registry({})
        return {"pass": len(rows) == 5 and not active and desk["proof_status"]["capital_permission"] == "BLOCKED", "components": len(rows), "active": active}
    check("five_market_registry_fail_closed", registry_default_blocked)

    def legacy_gate_attack() -> dict[str, Any]:
        fake = {m: {"market": m, "trading_ready": True, "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE", "errors": []} for m in ("us", "idx", "commodity", "fx", "crypto")}
        result = evaluate_all(fake)
        return {"pass": result["global_trading_ready"] is False and result["capital_permission"] == "BLOCKED", "reasons": result["reasons"]}
    check("legacy_boolean_promotion_rejected", legacy_gate_attack)

    def strict_bool_false() -> dict[str, Any]:
        result = validate_trade_ledger(pd.DataFrame([trade_row()], columns=TRADE_REQUIRED), now=dt.datetime(2026, 1, 1, tzinfo=UTC))
        return {"pass": result.get("valid") is True and not any("paper fills rejected" in x for x in result.get("errors", [])), "result": result}
    check("string_false_is_not_truthy", strict_bool_false)

    def paper_attack() -> dict[str, Any]:
        result = validate_trade_ledger(pd.DataFrame([trade_row(paper="True")], columns=TRADE_REQUIRED), now=dt.datetime(2026, 1, 1, tzinfo=UTC))
        return {"pass": result.get("valid") is False and "paper fills rejected" in result.get("errors", []), "errors": result.get("errors")}
    check("paper_fill_rejected", paper_attack)

    def unknown_source_attack() -> dict[str, Any]:
        result = validate_trade_ledger(pd.DataFrame([trade_row(execution_source="CSV")], columns=TRADE_REQUIRED), now=dt.datetime(2026, 1, 1, tzinfo=UTC))
        return {"pass": result.get("valid") is False and any("recognized live" in x for x in result.get("errors", [])), "errors": result.get("errors")}
    check("unrecognized_fill_source_rejected", unknown_source_attack)

    def future_fill_attack() -> dict[str, Any]:
        result = validate_trade_ledger(pd.DataFrame([trade_row(exit_fill_at="2030-01-01T00:00:00Z")], columns=TRADE_REQUIRED), now=dt.datetime(2026, 1, 1, tzinfo=UTC))
        return {"pass": result.get("valid") is False and "future exit fills rejected" in result.get("errors", []), "errors": result.get("errors")}
    check("future_fill_rejected", future_fill_attack)

    def account_mismatch() -> dict[str, Any]:
        result = validate_equity_ledger(equity_rows(account="9" * 64), expected_account_id_hash="1" * 64, expected_execution_source="BROKER_EXPORT", max_exit_at=pd.Timestamp("2022-01-03T00:00:00Z"), now=dt.datetime(2026, 1, 1, tzinfo=UTC))
        return {"pass": result.get("valid") is False and "equity account does not match trade account" in result.get("errors", []), "errors": result.get("errors")}
    check("equity_account_mismatch_rejected", account_mismatch)

    def shadow_chain() -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ledger.jsonl"; now = dt.datetime.now(UTC).replace(microsecond=0)
            forecast = {
                "forecast_id": "F95_VALIDTEST01", "trial_id": "TRIAL_1", "market": "us", "security_id": "TEST",
                "generated_at": (now - dt.timedelta(seconds=1)).isoformat().replace("+00:00", "Z"),
                "decision_at": now.isoformat().replace("+00:00", "Z"),
                "outcome_start": (now + dt.timedelta(days=1)).isoformat().replace("+00:00", "Z"),
                "outcome_end": (now + dt.timedelta(days=31)).isoformat().replace("+00:00", "Z"),
                "horizon": "30D", "direction": "LONG", "probability": 0.60, "expected_return": 0.10,
                "expected_shortfall": -0.08, "invalidation": "fundamental bridge fails", "regime": "R1",
                "model_hash": "1" * 64, "data_snapshot_hash": "2" * 64, "code_snapshot_hash": "3" * 64,
                "global_trial_ledger_hash": "4" * 64, "projection_file_hash": "5" * 64,
            }
            append_forecast(path, forecast, now=now)
            order = {"forecast_id": forecast["forecast_id"], "shadow_order_id": "SO_1", "created_at": now.isoformat().replace("+00:00", "Z"), "instrument_id": "TEST", "side": "BUY", "quantity": 1, "order_type": "MARKET", "reference_price": 100, "max_slippage_bps": 25}
            append_order_intent(path, order, now=now)
            fill = {"forecast_id": forecast["forecast_id"], "shadow_order_id": "SO_1", "filled_at": now.isoformat().replace("+00:00", "Z"), "quantity": 1, "price": 100.1, "commission": 0, "fees": 0, "spread_cost": 0.05, "slippage_cost": 0.05, "source_snapshot_hash": "6" * 64}
            append_shadow_fill(path, fill, now=now)
            good = verify_shadow(path)
            lines = path.read_text(encoding="utf-8").splitlines(); row = json.loads(lines[0]); row["probability"] = 0.99; lines[0] = json.dumps(row, sort_keys=True)
            tampered = Path(temp) / "tampered.jsonl"; tampered.write_text("\n".join(lines) + "\n", encoding="utf-8")
            bad = verify_shadow(tampered)
            return {"pass": good.get("valid") is True and bad.get("valid") is False and good.get("shadow_fills") == 1, "good": good, "tampered": bad}
    check("shadow_ledger_hash_chain_and_tamper_detection", shadow_chain)

    def backfill_attack() -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ledger.jsonl"; now = dt.datetime.now(UTC).replace(microsecond=0)
            forecast = {
                "forecast_id": "F95_BACKFILL001", "trial_id": "TRIAL_1", "market": "us", "security_id": "TEST",
                "generated_at": (now - dt.timedelta(days=1)).isoformat().replace("+00:00", "Z"), "decision_at": now.isoformat().replace("+00:00", "Z"),
                "outcome_start": (now + dt.timedelta(days=1)).isoformat().replace("+00:00", "Z"), "outcome_end": (now + dt.timedelta(days=31)).isoformat().replace("+00:00", "Z"),
                "horizon": "30D", "direction": "LONG", "probability": 0.6, "expected_return": 0.1, "expected_shortfall": -0.1,
                "invalidation": "x", "regime": "R1", "model_hash": "1"*64, "data_snapshot_hash": "2"*64,
                "code_snapshot_hash": "3"*64, "global_trial_ledger_hash": "4"*64, "projection_file_hash": "5"*64,
            }
            try:
                append_forecast(path, forecast, now=now); accepted = True
            except ValueError as exc:
                accepted = False; message = str(exc)
            return {"pass": not accepted and "backfilled" in message.lower(), "message": message}
    check("backfilled_forecast_rejected", backfill_attack)

    def collector_contract() -> dict[str, Any]:
        handoff_only = collector._status([{"id": "IDX_BROWSER_HANDOFF", "sha256": "1"*64, "is_evidence": False}])
        us_sources = collector.SOURCE_REGISTRY["us"]["sources"]
        independent_nasdaq = any(s["id"] == "NASDAQ_TRADED" and not s.get("requires_sec_ua") for s in us_sources)
        return {"pass": len(collector.SOURCE_REGISTRY) == 5 and handoff_only == "BLOCKED" and independent_nasdaq, "routes": list(collector.SOURCE_REGISTRY), "handoff_only_status": handoff_only}
    check("collector_five_routes_and_no_fake_idx_success", collector_contract)

    def idx_source_lock() -> dict[str, Any]:
        import IDX_BROWSER_EXPORT_IMPORT_V95 as idx
        return {"pass": idx.OFFICIAL_HOST.search("www.idx.co.id") is not None and idx.OFFICIAL_HOST.search("idx.co.id.evil.com") is None}
    check("idx_browser_import_official_host_lock", idx_source_lock)

    def missing_artifacts_fail_closed() -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            missing = root / "missing"
            result = run_blind_proof(
                predictor_manifest=missing, outcome_manifest=missing, projections=missing,
                trades=missing, equity=missing, signed_receipt=missing, forecast_seal=missing,
            )
            return {"pass": result.get("trading_ready") is False and result.get("capital_permission") == "BLOCKED" and result.get("errors"), "result": result}
    check("missing_proof_artifacts_fail_closed", missing_artifacts_fail_closed)

    def live_normalizers_smoke() -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); trade_in = root / "trade.csv"; trade_map = root / "trade_map.json"; trade_out = root / "normalized_trade.csv"
            pd.DataFrame([{
                "TradeID":"T1","ForecastID":"F95_TEST0001","StrategyID":"S1","Symbol":"TEST","Direction":"LONG",
                "EntryTime":"2020-01-02T00:00:00Z","ExitTime":"2022-01-03T00:00:00Z","Quantity":1,"EntryPrice":100,"ExitPrice":110,
                "Commission":0,"Fees":0,"SpreadCost":0,"SlippageCost":0,"ImpactCost":0,"BorrowCost":0,"FinancingCost":0,"Taxes":0,
                "FrozenRegime":"R1","RegimeDefinitionHash":"1"*64,"ADVNotional":100000,"BorrowAvailable":"False","IsLive":"True","Paper":"False","Synthetic":"False",
                "AccountID":"ACCOUNT","EntryOrderID":"ENTRY1","ExitOrderID":"EXIT1"
            }]).to_csv(trade_in,index=False)
            trade_mapping={"schema":"warroom.v95.closed_trade_mapping.v1","columns":{
                "trade_id":"TradeID","forecast_id":"ForecastID","strategy_id":"StrategyID","security_id":"Symbol","direction":"Direction",
                "entry_fill_at":"EntryTime","exit_fill_at":"ExitTime","quantity":"Quantity","entry_price":"EntryPrice","exit_price":"ExitPrice",
                "commission":"Commission","fees":"Fees","spread_cost":"SpreadCost","slippage_cost":"SlippageCost","impact_cost":"ImpactCost","borrow_cost":"BorrowCost","financing_cost":"FinancingCost","taxes":"Taxes",
                "regime":"FrozenRegime","regime_definition_hash":"RegimeDefinitionHash","adv_notional":"ADVNotional","borrow_available":"BorrowAvailable","is_live":"IsLive","paper":"Paper","synthetic":"Synthetic",
                "account_id":"AccountID","entry_order_id":"EntryOrderID","exit_order_id":"ExitOrderID"},"constants":{"market":"us","execution_source":"BROKER_EXPORT"}}
            trade_map.write_text(json.dumps(trade_mapping),encoding="utf-8")
            trade_receipt=normalize_trades(trade_in,trade_map,trade_out,salt="0123456789abcdef")

            equity_in=root/"equity.csv";equity_map=root/"equity_map.json";equity_out=root/"normalized_equity.csv"
            pd.DataFrame([
                {"Timestamp":"2020-01-01T00:00:00Z","NLV":100000,"StressNLV":100000,"CashFlow":0,"AccountID":"ACCOUNT","IsLive":"True","Paper":"False","Synthetic":"False"},
                {"Timestamp":"2022-01-04T00:00:00Z","NLV":100010,"StressNLV":100008,"CashFlow":0,"AccountID":"ACCOUNT","IsLive":"True","Paper":"False","Synthetic":"False"}
            ]).to_csv(equity_in,index=False)
            equity_mapping={"schema":"warroom.v95.equity_mapping.v1","columns":{"timestamp":"Timestamp","net_liquidation_value":"NLV","stress_net_liquidation_value":"StressNLV","external_cash_flow":"CashFlow","account_id":"AccountID","is_live":"IsLive","paper":"Paper","synthetic":"Synthetic"},"constants":{"execution_source":"BROKER_EXPORT","stress_model_hash":"5"*64}}
            equity_map.write_text(json.dumps(equity_mapping),encoding="utf-8")
            equity_receipt=normalize_equity(equity_in,equity_map,equity_out,salt="0123456789abcdef")
            same_account = json.loads(trade_out.with_suffix('.csv.receipt.json').read_text())["account_id_hash"] == json.loads(equity_out.with_suffix('.csv.receipt.json').read_text())["account_id_hashes"][0]
            return {"pass": trade_receipt["ledger_structurally_valid"] is True and equity_receipt["rows"] == 2 and same_account, "trade": trade_receipt, "equity": equity_receipt}
    check("live_trade_and_equity_normalizers_smoke", live_normalizers_smoke)

    def technical_policy() -> dict[str, Any]:
        registry = json.loads((HERE / "component_registry_v95.json").read_text(encoding="utf-8"))
        active = [name for name, row in registry["components"].items() if row.get("decision_active")]
        forbidden = ("rsi", "macd", "moving_average", "sma", "ema", "vwap", "breakout", "momentum")
        names = [name.lower() for name in registry["components"]]
        violations = [name for name in names if any(token in name for token in forbidden)]
        return {"pass": not active and not violations, "active": active, "violations": violations}
    check("zero_active_technical_predictors", technical_policy)

    passed = sum(int(t["pass"]) for t in tests)
    payload = {
        "schema": "warroom.v95.final_validation.v1",
        "generated_at": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "release": "War Room OS V9.5 Proof Firewall & Shadow Trading Runtime",
        "passed": passed,
        "total": len(tests),
        "all_pass": passed == len(tests),
        "tests": tests,
        "operational_permission": "SHADOW_TRADING_READY" if passed == len(tests) else "BLOCKED",
        "capital_permission": "BLOCKED",
        "trading_ready_markets": 0,
        "claim_limit": "Validation proves software controls and shadow-operational readiness, not live predictive profitability.",
    }
    payload["validation_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--out")
    args = parser.parse_args(); result = run_validation()
    if args.out:
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["all_pass"] else 2)


if __name__ == "__main__":
    main()
