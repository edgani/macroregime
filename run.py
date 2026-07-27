"""War Room OS v9.7 — causal anti-overfit research factory and proof-firewall runtime.

This runtime intentionally does not import or execute chart-derived signal engines. Market prices
may be retained only as current execution references and as future realized outcomes. All capital
remains blocked until an exact-scope point-in-time model has independently passed the frozen proof
protocol and prospective promotion gate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
from typing import Any, Mapping

import data_layer as DL
from research_kernel import attach_research_kernel
from proof_readiness_audit import audit as audit_real_data
from audit_all_markets_v91 import audit as audit_v91_readiness

HERE = Path(__file__).resolve().parent
MARKETS = ("us", "idx", "crypto", "commodity", "fx")


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _last_value(series: Any) -> tuple[str | None, float | None]:
    try:
        import pandas as pd
        s = pd.to_numeric(series, errors="coerce").dropna().sort_index()
        if s.empty:
            return None, None
        index_value = s.index[-1]
        observed = index_value.isoformat() if hasattr(index_value, "isoformat") else str(index_value)
        return observed, float(s.iloc[-1])
    except Exception:
        return None, None


def _macro_observations(data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    source = str(data.get("fred_source") or "UNAVAILABLE")
    for series_id, series in (data.get("fred") or {}).items():
        observed_at, value = _last_value(series)
        out[str(series_id)] = {
            "value": value,
            "observation_timestamp": observed_at,
            "available_at": None,
            "source": source,
            "point_in_time_eligible": False,
            "availability_semantics": "CURRENT_VINTAGE_ONLY; historical release timestamp not supplied",
        }
    return out


def _latest_execution_references(data: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    """Latest prices only. No changes, averages, ranks, patterns, or directional state."""
    out: dict[str, dict[str, float]] = {}
    for market, rows in (data.get("prices") or {}).items():
        current: dict[str, float] = {}
        for ticker, series in (rows or {}).items():
            _, value = _last_value(series)
            if value is not None:
                current[str(ticker)] = value
        out[str(market)] = current
    return out


def _feed_status(data: Mapping[str, Any]) -> dict[str, Any]:
    feeds = data.get("feeds") or {}
    return dict(feeds.get("_status") or {})


def _evidence_domain(state: str, source: str, note: str, *, pit: bool = False) -> dict[str, Any]:
    return {
        "state": state,
        "source": source,
        "note": note,
        "point_in_time_eligible": bool(pit),
        "capital_eligible": False,
    }


def _market_evidence(data: Mapping[str, Any], market: str) -> dict[str, dict[str, Any]]:
    feeds = data.get("feeds") or {}
    statuses = _feed_status(data)
    fred_live = bool(data.get("fred"))
    macro_state = "OBSERVED_CURRENT_VINTAGE" if fred_live else "NO_DATA"
    macro = _evidence_domain(
        macro_state,
        str(data.get("fred_source") or "FRED"),
        "Useful for current context only until release vintages and available_at are reconstructed.",
        pit=False,
    )

    no_data = lambda name: _evidence_domain("NO_DATA", name, "Required point-in-time dataset is not loaded.")
    if market == "us":
        return {
            "economic_origin": macro,
            "filing_fundamentals": no_data("SEC dissemination-time filings"),
            "expectations": no_data("point-in-time estimates/guidance"),
            "bottleneck_transmission": no_data("capacity/qualification/customer-supplier panel"),
            "positioning_amplification": _evidence_domain(
                "PARTIAL_UNVERIFIED" if feeds.get("finra") else "NO_DATA",
                "FINRA/borrow/options",
                str(statuses.get("finra") or "No validated signed positioning panel."),
            ),
            "cost_capacity": no_data("historical spreads, impact, borrow and security master"),
        }
    if market == "idx":
        return {
            "economic_origin": macro,
            "filing_fundamentals": no_data("IDX point-in-time filings"),
            "controller_free_float": no_data("historical controller/free-float/corporate actions"),
            "broker_inventory": no_data("crossing-adjusted ticker-by-broker inventory"),
            "foreign_flow": no_data("point-in-time foreign flow"),
            "cost_capacity": no_data("done-detail liquidity and impact"),
        }
    if market == "commodity":
        cot_present = bool(feeds.get("cot"))
        return {
            "stock_flow_origin": no_data("release-vintage stock-flow balances"),
            "inventory_surprise": no_data("as-released inventory expectations and actuals"),
            "physical_transmission": no_data("grade/location basis, freight, storage and capacity"),
            "positioning_amplification": _evidence_domain(
                "OBSERVED_RELEASE_LAGGED" if cot_present else "NO_DATA",
                "CFTC COT",
                str(statuses.get("cot") or "COT snapshot unavailable."),
                pit=cot_present,
            ),
            "expectations": no_data("curve and consensus supply-demand gap"),
            "cost_capacity": no_data("contract roll, spread, depth and impact"),
        }
    if market == "fx":
        cot_present = bool(feeds.get("cot"))
        carry_present = bool(feeds.get("fx_carry"))
        return {
            "relative_macro_origin": macro,
            "policy_and_bop_transmission": no_data("point-in-time policy, BOP, reserves and intervention"),
            "expectations": no_data("pair-specific consensus and option-implied distribution"),
            "positioning_amplification": _evidence_domain(
                "PARTIAL" if cot_present else "NO_DATA",
                "CFTC TFF/COT",
                str(statuses.get("cot") or "Release-lagged financial positioning unavailable."),
                pit=cot_present,
            ),
            "carry_funding": _evidence_domain(
                "OBSERVED" if carry_present else "NO_DATA",
                "FX carry/funding",
                str(statuses.get("fx_carry") or "Funding/carry panel unavailable."),
                pit=False,
            ),
            "cost_capacity": no_data("pair-specific spread, carry and market impact"),
        }
    if market == "crypto":
        onchain_present = bool(feeds.get("onchain"))
        return {
            "protocol_origin": _evidence_domain(
                "PARTIAL" if onchain_present else "NO_DATA",
                "on-chain/protocol records",
                str(statuses.get("onchain") or "Entity-adjusted protocol data unavailable."),
                pit=False,
            ),
            "stablecoin_and_unlocks": no_data("as-known stablecoin impulse and unlock schedule"),
            "venue_transmission": no_data("venue collateral and entity-adjusted flows"),
            "positioning_amplification": no_data("venue-specific funding, basis, OI and liquidations"),
            "expectations": no_data("adoption/value-capture expectation gap"),
            "cost_capacity": no_data("depth, slippage, custody and counterparty risk"),
        }
    raise ValueError(f"Unsupported market: {market}")


def _data_health(data: Mapping[str, Any]) -> dict[str, Any]:
    sources = []
    for market, raw in (data.get("sources") or {}).items():
        text = str(raw)
        state = "OBSERVED" if "LIVE" in text.upper() else "NO_DATA"
        sources.append({
            "provider": str(market),
            "dataset": "execution_reference_prices",
            "state": state,
            "capital_eligible": False,
            "note": "Price is retained only as an execution reference and future outcome measure.",
        })
    fred_live = bool(data.get("fred"))
    sources.append({
        "provider": "FRED",
        "dataset": "economic_context",
        "state": "OBSERVED_CURRENT_VINTAGE" if fred_live else "NO_DATA",
        "capital_eligible": False,
        "note": "Historical capital proof requires vintage and release timestamps.",
    })
    return {
        "overall": "RESEARCH_DATA_ONLY" if any(x["state"] != "NO_DATA" for x in sources) else "NO_DATA",
        "sources": sources,
        "checked_at": _utc_now(),
    }


def build_desk(data: Mapping[str, Any], top_per_market: int = 0) -> dict[str, Any]:
    del top_per_market
    markets: dict[str, Any] = {}
    for market in data.get("markets") or MARKETS:
        evidence = _market_evidence(data, str(market))
        complete = sum(1 for item in evidence.values() if item.get("point_in_time_eligible"))
        markets[str(market)] = {
            "label": {
                "us": "US Stocks", "idx": "IHSG", "crypto": "Crypto",
                "commodity": "Commodities", "fx": "FX",
            }.get(str(market), str(market)),
            "evidence_domains": evidence,
            "point_in_time_domains_ready": complete,
            "projection_status": "NO_PROJECTION",
            "capital_permission": "BLOCKED",
            "decision_reason": "Exact-scope data, model proof and prospective receipts are incomplete.",
        }

    desk = {
        "meta": {
            "generated": _utc_now(),
            "source": str(data.get("overall_source") or "RESEARCH_DATA_ONLY"),
            "sources": dict(data.get("sources") or {}),
            "fred_source": str(data.get("fred_source") or "NO_DATA"),
            "universe_n": 0,
            "note": "Nontechnical runtime: economic, fundamental, narrative, bottleneck, valuation, positioning, flow and causal evidence only.",
        },
        "systemic": {
            "state": "CURRENT_CONTEXT_ONLY" if data.get("fred") else "NO_DATA",
            "capital_permission": "BLOCKED",
            "claim": "No calibrated macro projection exists until point-in-time vintages pass frozen validation.",
        },
        "macro_observations": _macro_observations(data),
        "markets": markets,
        "execution_reference": _latest_execution_references(data),
        "data_health": _data_health(data),
        "alpha": [],
        "desk_picks": {"picks": [], "state": "BLOCKED", "reason": "No proven market-specific bottleneck projection selector."},
        "feeds": {k: v for k, v in (data.get("feeds") or {}).items() if k != "_status"},
        "feed_status": _feed_status(data),
        "reference": {},
        "institutional": {"overall_state": "NOT_LOADED", "events": [], "statuses": []},
    }
    desk = attach_research_kernel(desk)
    desk["v89_real_data_readiness"] = audit_real_data(HERE / "runtime" / "market_evidence")
    desk["v91_readiness_audit"] = audit_v91_readiness(HERE / "runtime" / "market_evidence")
    status_path = HERE / "V97_CURRENT_STATUS.json"
    try:
        desk["v97_status"] = json.loads(status_path.read_text(encoding="utf-8"))
    except Exception:
        desk["v97_status"] = {"operational_permission": "LIMITED_PRODUCTION_CONTROL_PLANE_READY", "capital_permission": "BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL"}
    research_status_path = HERE / "runtime" / "v96_research" / "V96_RESEARCH_STATUS.json"
    try:
        desk["v96_research_status"] = json.loads(research_status_path.read_text(encoding="utf-8"))
    except Exception:
        desk["v96_research_status"] = {
            "pipeline_ready_markets": 0,
            "historical_statistical_pass_markets": 0,
            "historical_blind_proven_markets": 0,
            "live_capital_ready_markets": 0,
            "capital_permission": "BLOCKED",
        }
    try:
        from trading_readiness_v97 import audit as audit_trading_v97
        desk["v97_trading_readiness"] = audit_trading_v97()
    except Exception as exc:
        desk["v97_trading_readiness"] = {
            "software_state": "INCOMPLETE", "operational_control_plane_ready_markets": 0,
            "limited_production_signal_ready_markets": 0, "capital_permission": "BLOCKED",
            "error": f"{type(exc).__name__}: {exc}",
        }
    try:
        quotes_path = HERE / "runtime" / "v97_trading" / "execution_quotes.json"
        desk["v97_execution_quotes"] = json.loads(quotes_path.read_text(encoding="utf-8"))
    except Exception:
        desk["v97_execution_quotes"] = {"markets": {}, "quote_count": 0, "markets_with_quote": 0}
    return desk


def build_fast_desk(data: Mapping[str, Any], top_per_market: int = 0) -> dict[str, Any]:
    return build_desk(data, top_per_market=top_per_market)


def render_dashboard(desk: Mapping[str, Any], template_path: str, out_path: str) -> bool:
    template = Path(template_path)
    if not template.exists():
        return False
    html = template.read_text(encoding="utf-8")
    payload = "window.DASHBOARD_DATA=" + json.dumps(desk, default=str, separators=(",", ":"), ensure_ascii=False) + ";"
    if "/*__INJECT_DATA__*/" in html:
        html = html.replace("/*__INJECT_DATA__*/", payload)
    else:
        html = html.replace("<body>", "<body><script>" + payload.replace("</", "<\\/") + "</script>", 1)
    Path(out_path).write_text(html, encoding="utf-8")
    return True


def print_summary(desk: Mapping[str, Any]) -> None:
    print("WAR ROOM OS V9.7 — LIMITED-PRODUCTION TRADING CONTROL PLANE")
    print("Capital permission: BLOCKED UNTIL EXACT PROOF + HUMAN APPROVAL")
    for market, row in (desk.get("markets") or {}).items():
        print(f"{market}: {row.get('point_in_time_domains_ready', 0)} PIT domains ready; {row.get('projection_status')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="War Room OS V9.7 limited-production trading control and proof-firewall runtime")
    parser.add_argument("--synthetic", action="store_true")
    parser.add_argument("--markets", default=None)
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--out", default=str(HERE / "desk_data.json"))
    parser.add_argument("--template", default=str(HERE / "dashboard.html"))
    parser.add_argument("--html", default=str(HERE / "dashboard_live.html"))
    args = parser.parse_args()
    markets = args.markets.split(",") if args.markets else None
    data = DL.load_all(
        markets=markets,
        start=args.start,
        allow_live=not args.synthetic,
        fetch_live_feeds=not args.synthetic,
        allow_synthetic=False,
        fast_core=True,
        skip_slow_context=False,
    )
    desk = build_desk(data)
    Path(args.out).write_text(json.dumps(desk, indent=2, default=str), encoding="utf-8")
    render_dashboard(desk, args.template, args.html)
    print_summary(desk)


if __name__ == "__main__":
    main()
