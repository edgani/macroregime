"""Architecture and fail-closed validation for War Room OS V9.8 Unified Decision Packet."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

import data_layer as DL
import execution_quote_collector_v98 as EQ
from public_snapshot_reader_v98 import load_execution_universe, summarize_public_sources
from run import build_desk, render_dashboard
from runtime_sanitizer import sanitize_runtime_payload
from warroom.no_technical_policy import assert_registry_has_no_active_technical_components

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc
MARKETS = ("us", "idx", "crypto", "commodity", "fx")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def check(name: str, fn: Callable[[], bool], results: list[dict[str, Any]]) -> None:
    try:
        passed = bool(fn()); error = None if passed else "condition returned false"
    except Exception as exc:
        passed = False; error = f"{type(exc).__name__}: {exc}"
    results.append({"name": name, "passed": passed, "error": error})


def quote_fixture(now: dt.datetime) -> dict[str, Any]:
    markets = {m: {} for m in MARKETS}
    rows = [
        ("us", "SPY", 500.0, "USD"), ("idx", "HUMI", 72.0, "IDR"),
        ("crypto", "BTCUSDT", 100000.0, "USDT"), ("commodity", "GOLD_REFERENCE", 2400.0, "USD"),
        ("fx", "EURUSD_REFERENCE", 1.1, "USD"),
    ]
    stamp = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    for market, ticker, price, currency in rows:
        record = {
            "instrument": ticker, "provider_symbol": ticker, "asset_type": "VALIDATION_REFERENCE",
            "price": price, "currency": currency, "provider_timestamp": stamp, "provider": "VALIDATION",
            "source": {"http_status": 200}, "received_at": stamp, "age_seconds_at_collection": 0.0,
            "validation": "VALID_EXECUTION_REFERENCE", "predictor_eligible": False, "capital_eligible": False,
        }
        record["record_hash"] = digest(record); markets[market][ticker] = record
    payload = {
        "schema": "warroom.v98.execution_quotes.v1", "generated_at": stamp, "universe_hash": "0" * 64,
        "markets": markets, "failures": [], "markets_with_quote": 5, "quote_count": 5,
        "proof_status": "EXECUTION_REFERENCE_ONLY", "predictor_eligible": False,
        "capital_permission": "BLOCKED_PENDING_DECISION_AND_RISK_GATE",
    }
    payload["manifest_hash"] = digest(payload)
    return payload


def projection_fixture(now: dt.datetime) -> dict[str, Any]:
    stamp = now.isoformat(timespec="seconds").replace("+00:00", "Z")
    common = {
        "baseline_revenue": 1000.0, "gross_margin": 0.6, "operating_expense": 300.0,
        "tax_rate": 0.2, "non_operating_assets": 100.0, "net_debt": 50.0, "diluted_shares": 10.0,
    }
    def scenario(name: str, probability: float, incremental: float, multiple: float) -> dict[str, Any]:
        return {"name": name, "probability": probability, "evidence_ids": [f"fixture-{name}"], "assumptions": [f"frozen {name} scenario"], "drivers": {**common, "bottleneck_incremental_revenue": incremental, "earnings_multiple": multiple}}
    return {
        "projection_id": "fixture-spy-v98", "narrative_id": "fixture-narrative", "market": "us",
        "instrument_id": "SPY", "ticker": "SPY", "as_of": stamp, "availability_max": stamp,
        "currency": "USD", "quote_convention": "USD per share", "method": "equity_earnings_bridge",
        "horizon_days": 90, "current_price": 500.0,
        "bottleneck_claim": "Validation-only capacity bottleneck", "beneficiary_value_capture": "Validation-only issuer cash generation",
        "projection_reason": "Validation-only transparent earnings bridge", "invalidation_rule": "Validation-only evidence reversal",
        "feature_domains": ["economics", "fundamentals", "expectations", "bottleneck", "causal_transmission", "valuation"],
        "narrative_state": "REPRICING_READY_RESEARCH_CANDIDATE",
        "feature_snapshot_hash": "1" * 64, "evidence_lineage_hash": "2" * 64,
        "universe_snapshot_hash": "3" * 64, "model_hash": "4" * 64,
        "trial_ledger_hash": "5" * 64, "narrative_state_hash": "6" * 64,
        "scenarios": [scenario("low", 0.25, 0.0, 18.0), scenario("base", 0.5, 100.0, 20.0), scenario("high", 0.25, 200.0, 22.0)],
    }


def main() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    dashboard = (HERE / "dashboard.html").read_text(encoding="utf-8")
    tabs_match = re.search(r"const TABS=\[(.*?)\];", dashboard, flags=re.S)
    tabs_text = tabs_match.group(1) if tabs_match else ""
    expected_labels = ["Mission Control", "Macro & Risk", "Alpha Center", "US Stocks", "IHSG", "Crypto", "Commodities", "FX"]

    check("dashboard has exactly eight primary tabs", lambda: all(label in tabs_text for label in expected_labels) and tabs_text.count("['") == 8, results)
    check("price projection is not a primary tab", lambda: "Price Projection" not in tabs_text, results)
    check("flow positioning is not a primary tab", lambda: "Flow & Positioning" not in tabs_text, results)
    check("execution control is not a primary tab", lambda: "Execution Control" not in tabs_text, results)
    check("data integrity and validation are not primary tabs", lambda: "Data Integrity" not in tabs_text and "Validation" not in tabs_text, results)
    check("data and proof is an advanced drawer", lambda: "<details" in dashboard and "Data & Proof" in dashboard, results)
    check("ticker page contains ticker-bound projection", lambda: "PRICE PROJECTION — TICKER-BOUND" in dashboard, results)

    registry = json.loads((HERE / "component_registry_v98.json").read_text(encoding="utf-8"))
    check("registry contains no active technical component", lambda: (assert_registry_has_no_active_technical_components(registry) is None), results)
    check("all active runtime identities are V9.8", lambda: all("V9.7" not in (HERE / name).read_text(encoding="utf-8") for name in ("app.py", "run.py", "research_kernel.py", "dashboard.html", "release_meta.py")), results)

    quote_path = HERE / "runtime" / "v98_trading" / "execution_quotes.json"
    projection_path = HERE / "runtime" / "v98_decisions" / "us" / "SPY.json"
    quote_backup = quote_path.read_bytes() if quote_path.is_file() else None
    projection_backup = projection_path.read_bytes() if projection_path.is_file() else None
    try:
        now = dt.datetime.now(UTC).replace(microsecond=0)
        quote_path.parent.mkdir(parents=True, exist_ok=True); quote_path.write_text(json.dumps(quote_fixture(now), indent=2), encoding="utf-8")
        projection_path.parent.mkdir(parents=True, exist_ok=True); projection_path.write_text(json.dumps(projection_fixture(now), indent=2), encoding="utf-8")
        data = DL.load_all(allow_live=False, allow_synthetic=False)
        desk = build_desk(data)
        universe = load_execution_universe()

        check("runtime release identity is 9.8", lambda: desk["meta"]["version"] == "9.8", results)
        check("five market objects exist", lambda: set(desk["markets"]) == set(MARKETS), results)
        check("ticker packets exist for every execution reference", lambda: all(len(desk["ticker_packets"][m]) == len(universe[m]) for m in MARKETS), results)
        check("HUMI has a unified ticker packet", lambda: "HUMI" in desk["ticker_packets"]["idx"], results)
        required_packet = {"decision", "quote", "causal_chain", "fundamental_value_capture", "flow_positioning", "projection", "risk_execution", "proof_data"}
        check("every packet contains the complete decision chain", lambda: all(required_packet <= set(packet) for market in desk["ticker_packets"].values() for packet in market.values()), results)
        check("no separate top-level price projection object", lambda: "price_projection" not in desk and "projection" not in desk, results)
        check("quote fixture is visible in all five markets", lambda: desk["mission_control"]["quote_markets"] == 5, results)
        check("quote availability does not promote a trade", lambda: all(packet["decision"]["state"] == "NO_TRADE" for market in desk["ticker_packets"].values() for packet in market.values()), results)
        check("SPY research projection calculates inside its ticker packet", lambda: desk["ticker_packets"]["us"]["SPY"]["projection"].get("valid") is True, results)
        check("valid research projection remains blocked without proof", lambda: desk["ticker_packets"]["us"]["SPY"]["decision"]["capital_permission"] == "BLOCKED", results)
        check("projection is scoped to exact ticker", lambda: desk["ticker_packets"]["us"]["SPY"]["projection"].get("ticker") == "SPY", results)
        check("current quote is never predictor eligible", lambda: all(packet["quote"].get("predictor_eligible") is not True for market in desk["ticker_packets"].values() for packet in market.values()), results)
        check("risk entry stop and target survive sanitizer", lambda: {"entry", "stop", "target"} <= set(sanitize_runtime_payload(desk["ticker_packets"]["us"]["SPY"])["risk_execution"]), results)
        check("alpha ranking declares coverage-only basis", lambda: "Coverage" in desk["alpha_center"]["ranking_basis"], results)
        check("bundled US source snapshot remains visible", lambda: desk["public_sources"]["markets"]["us"]["valid_items"] >= 1, results)
        check("Mission Control remains honest no-trade", lambda: desk["mission_control"]["decision"] == "NO_TRADE" and desk["mission_control"]["capital_permission"] == "BLOCKED", results)
        check("auto-submit remains disabled", lambda: desk["trading_readiness"]["auto_submit_enabled"] is False, results)
        check("five execution routes remain operational", lambda: desk["trading_readiness"]["operational_control_plane_ready_markets"] == 5, results)

        rendered = HERE / "runtime" / "v98_validation_dashboard.html"
        check("dashboard renders from unified payload", lambda: render_dashboard(desk, str(HERE / "dashboard.html"), str(rendered)) and rendered.is_file() and rendered.stat().st_size > 10000, results)
        rendered.unlink(missing_ok=True)
    finally:
        if quote_backup is None: quote_path.unlink(missing_ok=True)
        else: quote_path.write_bytes(quote_backup)
        if projection_backup is None: projection_path.unlink(missing_ok=True)
        else: projection_path.write_bytes(projection_backup)
        try: projection_path.parent.rmdir()
        except OSError: pass
        try: projection_path.parent.parent.rmdir()
        except OSError: pass

    source_summary = summarize_public_sources()
    check("public source reader validates at least bundled US evidence", lambda: source_summary["markets"]["us"]["valid_items"] >= 1, results)

    # A failed refresh may preserve a hash-valid last-known record for context,
    # but it must be explicitly stale and never execution-fresh.
    with tempfile.TemporaryDirectory(prefix="v98_quote_resilience_") as temp_dir:
        temp = Path(temp_dir)
        universe_path = temp / "universe.json"
        output_path = temp / "quotes.json"
        universe_path.write_text(json.dumps({
            "us": [{"instrument": "SPY", "provider": "YAHOO", "provider_symbol": "SPY", "asset_type": "ETF"}],
            "idx": [], "crypto": [], "commodity": [], "fx": []
        }), encoding="utf-8")
        old_stamp = (dt.datetime.now(UTC) - dt.timedelta(days=2)).replace(microsecond=0).isoformat().replace("+00:00", "Z")
        old_record = {
            "instrument": "SPY", "provider_symbol": "SPY", "asset_type": "ETF",
            "price": 499.0, "currency": "USD", "provider_timestamp": old_stamp,
            "provider": "YAHOO", "source": {"http_status": 200}, "received_at": old_stamp,
            "age_seconds_at_collection": 0.0, "validation": "VALID_EXECUTION_REFERENCE",
            "predictor_eligible": False, "capital_eligible": False,
        }
        old_record["record_hash"] = digest(old_record)
        previous = {
            "schema": "warroom.v98.execution_quotes.v1", "generated_at": old_stamp,
            "universe_hash": "0" * 64, "markets": {"us": {"SPY": old_record}, "idx": {}, "crypto": {}, "commodity": {}, "fx": {}},
            "failures": [], "markets_with_quote": 1, "markets_with_fresh_quote": 1,
            "quote_count": 1, "fresh_quote_count": 1, "proof_status": "EXECUTION_REFERENCE_ONLY",
            "predictor_eligible": False, "capital_permission": "BLOCKED_PENDING_DECISION_AND_RISK_GATE",
        }
        previous["manifest_hash"] = digest(previous)
        output_path.write_text(json.dumps(previous), encoding="utf-8")
        original_yahoo = EQ._yahoo_quote
        EQ._yahoo_quote = lambda symbol: (_ for _ in ()).throw(RuntimeError("forced refresh failure"))
        try:
            preserved = EQ.collect(universe_path=universe_path, output_path=output_path)
        finally:
            EQ._yahoo_quote = original_yahoo
        stale = preserved["markets"]["us"].get("SPY", {})
        check("failed quote refresh preserves last-known context", lambda: stale.get("price") == 499.0 and stale.get("validation") == "STALE_LAST_KNOWN_REFERENCE", results)
        check("preserved last-known quote is never execution fresh", lambda: preserved.get("fresh_quote_count") == 0 and preserved.get("markets_with_fresh_quote") == 0, results)
    check("Python modules compile", lambda: subprocess.run(["python", "-m", "py_compile", "app.py", "run.py", "data_layer.py", "research_kernel.py", "decision_packet_v98.py", "public_snapshot_reader_v98.py", "public_context_collector_v98.py", "warroom_data_worker.py", "trading_control_plane_v98.py", "execution_reconciliation_v98.py"], cwd=HERE, capture_output=True).returncode == 0, results)
    js_path = HERE / "runtime" / "v98_dashboard_validation.js"
    script_start = dashboard.rfind("<script>") + len("<script>"); script_end = dashboard.rfind("</script>")
    js_path.parent.mkdir(parents=True, exist_ok=True); js_path.write_text(dashboard[script_start:script_end].replace("/*__INJECT_DATA__*/", "window.DASHBOARD_DATA={};"), encoding="utf-8")
    check("dashboard JavaScript parses", lambda: subprocess.run(["node", "--check", str(js_path)], capture_output=True).returncode == 0, results)
    js_path.unlink(missing_ok=True)

    payload = {
        "schema": "warroom.v98.unified_packet_validation.v1",
        "release": "War Room OS V9.8 Unified Decision Packet",
        "generated_at": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "tests": results,
        "passed": sum(bool(x["passed"]) for x in results),
        "total": len(results),
        "all_passed": all(bool(x["passed"]) for x in results),
        "capital_claim": "NO_ALPHA_CLAIM; UNIFIED_CONTEXT_AND_FAIL_CLOSED_EXECUTION_ONLY",
    }
    payload["validation_hash"] = digest({k: v for k, v in payload.items() if k != "validation_hash"})
    (HERE / "V98_UNIFIED_VALIDATION.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return payload


if __name__ == "__main__":
    main()
