"""Adversarial integrity checks for War Room OS V9.9 Actual Data Integration.

The validator proves wiring, state separation, package integrity and fail-closed behavior.  It does
not claim that any market strategy is profitable or live-proven.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent


def load_json(name: str) -> dict[str, Any]:
    raw = json.loads((HERE / name).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise AssertionError(f"{name} root is not an object")
    return raw


def main() -> int:
    from bundled_research_reader_v99 import inventory, all_context
    from runtime_store import read_snapshot, snapshot_integrity_valid
    from trading_readiness_v99 import audit as readiness_audit
    from warroom.no_technical_policy import enforce_payload, assert_registry_has_no_active_technical_components

    desk = load_json("desk_data.json")
    inv = inventory()
    context = all_context()
    readiness = readiness_audit()
    registry = load_json("component_registry_v99.json")
    html = (HERE / "dashboard.html").read_text(encoding="utf-8")
    app = (HERE / "app.py").read_text(encoding="utf-8")
    quote_collector = (HERE / "execution_quote_collector_v99.py").read_text(encoding="utf-8")
    public_collector = (HERE / "public_context_collector_v99.py").read_text(encoding="utf-8")
    req = (HERE / "requirements.txt").read_text(encoding="utf-8").lower()

    checks: list[tuple[str, Callable[[], None]]] = []

    def check(name: str):
        def deco(fn: Callable[[], None]):
            checks.append((name, fn)); return fn
        return deco

    @check("release identity is V9.9")
    def _(): assert str(desk.get("meta", {}).get("version")) == "9.9"

    @check("fourteen real bundled datasets are inventoried")
    def _(): assert int(inv.get("datasets_present", 0)) >= 14

    @check("every inventoried bundled file exists and is nonempty")
    def _():
        for row in inv.get("datasets", []):
            path = HERE / str(row["path"])
            assert path.is_file() and path.stat().st_size > 0, path
            assert len(str(row.get("sha256") or "")) == 64

    @check("S&P historical panel is physically bundled")
    def _(): assert (HERE / "research/sp500_panel.parquet").stat().st_size > 10_000_000

    @check("VIX history is loaded with expected long coverage")
    def _():
        row = next(x for x in inv["datasets"] if x["dataset"] == "vix_history")
        assert row["state"] == "LOADED" and row["rows"] >= 9_000 and str(row["date_min"]).startswith("1990")

    @check("Shiller history is loaded with expected long coverage")
    def _():
        row = next(x for x in inv["datasets"] if x["dataset"] == "shiller_history")
        assert row["state"] == "LOADED" and row["rows"] >= 1_800 and str(row["date_min"]).startswith("1871")

    @check("Parquet dependency is declared")
    def _(): assert "pyarrow" in req

    @check("bundled causal-chain references are present")
    def _(): assert int(context.get("reference_counts", {}).get("chains", 0)) >= 10

    @check("IHSG conglomerate/controller references are present")
    def _(): assert int(context.get("reference_counts", {}).get("ihsg_conglomerates", 0)) >= 20

    @check("bottleneck heatmap references are present")
    def _(): assert int(context.get("reference_counts", {}).get("bottleneck_heatmap", 0)) >= 60

    @check("research data and capital permission are separate states")
    def _():
        mc = desk["mission_control"]
        assert mc["research_data_status"] == "AVAILABLE"
        assert mc["capital_permission"] == "BLOCKED"

    @check("all five markets expose bundled research context")
    def _(): assert int(desk["mission_control"]["research_markets"]) == 5

    @check("US historical research is not mislabeled NO_DATA")
    def _(): assert desk["markets"]["us"]["research_data_status"] == "AVAILABLE_HISTORICAL_RESEARCH"

    @check("other markets expose partial context instead of false completeness")
    def _():
        for market in ("idx", "crypto", "commodity", "fx"):
            assert desk["markets"][market]["research_data_status"] == "PARTIAL_RESEARCH_CONTEXT"

    @check("research packet universe is materially populated")
    def _():
        expected = {"us": 100, "idx": 80, "crypto": 8, "commodity": 5, "fx": 5}
        for market, minimum in expected.items():
            assert len(desk["ticker_packets"][market]) >= minimum

    @check("HUMI is available as an IHSG research packet")
    def _(): assert "HUMI" in desk["ticker_packets"]["idx"]

    @check("every packet keeps thesis projection flow risk execution and proof together")
    def _():
        required = {"decision", "quote", "research_context", "causal_chain", "flow_positioning", "projection", "risk_execution", "proof_data"}
        for packets in desk["ticker_packets"].values():
            for packet in packets.values(): assert required.issubset(packet)

    @check("research context score is not exposed as trade readiness")
    def _():
        assert "Research-context score" in html
        assert "Readiness score" not in html

    @check("ticker projection is withheld without proven value bridge")
    def _():
        for packets in desk["ticker_packets"].values():
            for packet in packets.values():
                p = packet["projection"]
                if p.get("valid") is not True:
                    assert p.get("expected_target_price") is None
                    assert packet["risk_execution"].get("position_size") == 0.0

    @check("no packet is promoted without bound proof")
    def _():
        assert not desk["alpha_center"]["promoted"]
        for packets in desk["ticker_packets"].values():
            for packet in packets.values(): assert packet["decision"]["capital_permission"] == "BLOCKED"

    @check("missing live quote never erases bundled research")
    def _():
        assert desk["mission_control"]["quote_markets"] == 0
        assert desk["mission_control"]["research_markets"] == 5
        assert desk["markets"]["us"]["observed_domains"] > 0

    @check("synthetic evidence is absent from active payload")
    def _(): assert "SYNTHETIC" not in json.dumps(desk).upper()

    @check("technical analysis is not active")
    def _():
        assert_registry_has_no_active_technical_components(registry)
        enforce_payload(desk)

    @check("V9.9 proof registry is active")
    def _(): assert desk["proof_registry"]["schema"] == "warroom.v99.component_registry.v1"

    @check("V9.9 execution policy is fail closed")
    def _():
        policy = load_json("V99_LIMITED_PRODUCTION_POLICY.json")
        rules = policy["execution_rules"]
        assert rules["auto_submit_enabled"] is False and rules["require_human_approval"] is True and rules["require_bound_proof_run"] is True

    @check("five market execution control routes are defined")
    def _(): assert readiness["operational_control_plane_ready_markets"] == 5

    @check("trading readiness remains honest")
    def _():
        assert readiness["bound_proof_markets"] == 0
        assert readiness["limited_production_signal_ready_markets"] == 0
        assert readiness["capital_permission"].startswith("BLOCKED")

    @check("dashboard has exactly eight primary tabs")
    def _():
        start = html.index("const TABS=")
        segment = html[start:html.index(";", start)]
        assert segment.count("['") == 8
        for removed in ("Price Projection'],", "Flow & Positioning'],", "Execution Control'],", "Validation'],"):
            assert removed not in segment

    @check("data and proof remain an advanced drawer")
    def _(): assert "Data & Proof — file, source, state, dan claim limit" in html

    @check("dashboard wording distinguishes data from capital")
    def _():
        assert "DATA ${mc.research_data_status" in html
        assert "CAPITAL ${mc.capital_permission" in html

    @check("app seeds offline bundled data before network worker")
    def _():
        assert "allow_live=False" in app and "component_registry_v99.json" in app

    @check("V9.9 quote collector writes V9.9 runtime and universe")
    def _(): assert "runtime\" / \"v99_trading" in quote_collector and "V99_EXECUTION_REFERENCE_UNIVERSE.json" in quote_collector

    @check("V9.9 public collector writes V9.9 acquisition runtime")
    def _(): assert "v99_public_acquisition" in public_collector

    @check("runtime snapshot integrity is valid")
    def _():
        snap = read_snapshot(); assert snap is not None and snapshot_integrity_valid(snap)
        assert snap["meta"]["version"] == "9.9" and snap["mission_control"]["research_data_status"] == "AVAILABLE"

    @check("static mirror contains V9.9 data rather than stale V9.8 snapshot")
    def _():
        snap = load_json("static/desk_snapshot.json")
        assert snap["meta"]["version"] == "9.9" and snap["mission_control"]["bundled_datasets_present"] >= 14

    @check("all Python source files compile")
    def _():
        files = [str(p) for p in HERE.rglob("*.py") if "__pycache__" not in p.parts]
        proc = subprocess.run([sys.executable, "-m", "py_compile", *files], capture_output=True, text=True)
        assert proc.returncode == 0, proc.stderr

    @check("dashboard JavaScript parses")
    def _():
        start = html.index("<script>", html.index("</div>")) + len("<script>")
        end = html.rindex("</script>")
        js = html[start:end]
        tmp = HERE / ".v99_dashboard_check.js"; tmp.write_text(js, encoding="utf-8")
        try:
            proc = subprocess.run(["node", "--check", str(tmp)], capture_output=True, text=True)
            assert proc.returncode == 0, proc.stderr
        finally:
            tmp.unlink(missing_ok=True)

    results = []
    for name, fn in checks:
        try:
            fn(); results.append({"name": name, "status": "PASS"})
        except Exception as exc:
            results.append({"name": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})

    failures = [x for x in results if x["status"] != "PASS"]
    payload = {
        "schema": "warroom.v99.actual_data_validation.v1",
        "release": "War Room OS V9.9 Actual Data Integration",
        "passed": len(results) - len(failures),
        "total": len(results),
        "all_pass": not failures,
        "results": results,
        "claim_limit": "These checks validate data wiring, state separation, fail-closed controls and package integrity. They do not prove trading profitability.",
    }
    (HERE / "V99_FINAL_VALIDATION.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
