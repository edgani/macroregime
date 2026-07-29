"""War Room OS V10.1 — operational research + shadow-trading runtime.

The runtime exposes real bundled historical/reference data even when live capital is blocked.  It keeps bundled evidence, current research actions, shadow permission and proof-gated systematic live permission as separate states.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path
from typing import Any, Mapping

import data_layer_v101 as DL
from decision_packet_v101 import MARKET_LABELS, build_packets
from bundled_research_reader_v99 import packet_universe
from research_kernel import attach_research_kernel

HERE = Path(__file__).resolve().parent
MARKETS = ("us", "idx", "crypto", "commodity", "fx")


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _last_value(series: Any) -> tuple[str | None, float | None]:
    try:
        import pandas as pd
        values = pd.to_numeric(series, errors="coerce").dropna().sort_index()
        if values.empty: return None, None
        iv = values.index[-1]; observed = iv.isoformat() if hasattr(iv, "isoformat") else str(iv)
        return observed, float(values.iloc[-1])
    except Exception:
        return None, None


def _macro_observations(data: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    source = str(data.get("fred_source") or "NO_DATA")
    for series_id, series in (data.get("fred") or {}).items():
        observed_at, value = _last_value(series)
        out[str(series_id)] = {
            "label": DL.FRED_SERIES.get(str(series_id), str(series_id)), "value": value,
            "observation_timestamp": observed_at, "available_at": None, "source": source,
            "point_in_time_eligible": False,
            "availability_semantics": "Current-vintage observation only; historical release timestamp not reconstructed.",
            "context_type": "CURRENT",
        }
    bundled = (((data.get("bundled_research") or {}).get("macro") or {}).get("observations") or {})
    for key, row in bundled.items():
        if isinstance(row, Mapping):
            out[str(key)] = {**dict(row), "context_type": "BUNDLED_HISTORICAL"}
    return out


def _domain(state: str, source: str, note: str, *, pit: bool = False, capital: bool = False, count: int | None = None) -> dict[str, Any]:
    row = {"state": state, "source": source, "note": note, "point_in_time_eligible": pit, "capital_eligible": capital}
    if count is not None: row["valid_items"] = count
    return row


def _source_ids(data: Mapping[str, Any], market: str) -> set[str]:
    row = (((data.get("public_sources") or {}).get("markets") or {}).get(market) or {})
    return {str(item.get("id") or "").upper() for item in (row.get("items") or []) if isinstance(item, Mapping) and item.get("hash_valid") is True}


def _has(ids: set[str], *parts: str) -> bool:
    needles = tuple(p.upper() for p in parts)
    return any(any(n in item for n in needles) for item in ids)


def _quote_count(data: Mapping[str, Any], market: str) -> int:
    rows = (((data.get("quotes") or {}).get("markets") or {}).get(market) or {})
    return len(rows) if isinstance(rows, Mapping) else 0


def _coverage(data: Mapping[str, Any], market: str) -> dict[str, Any]:
    return ((((data.get("bundled_research") or {}).get("market_coverage") or {}).get(market)) or {})


def _market_evidence(data: Mapping[str, Any], market: str) -> dict[str, dict[str, Any]]:
    ids = _source_ids(data, market); fred = bool(data.get("fred")); cov = _coverage(data, market); domains = cov.get("domains") or {}
    macro_bundle = bool((((data.get("bundled_research") or {}).get("macro") or {}).get("observations") or {}))
    macro = _domain(
        "CURRENT_AND_HISTORICAL_CONTEXT" if fred and macro_bundle else "CURRENT_CONTEXT_OBSERVED" if fred else "BUNDLED_HISTORICAL_CONTEXT" if macro_bundle else "NO_DATA",
        "FRED current-vintage + bundled macro/VIX/Shiller",
        "Macro context is visible. Historical capital proof still requires release-vintage/available-at reconstruction.",
    )
    quote = _domain("EXECUTION_REFERENCE_AVAILABLE" if _quote_count(data, market) else "NO_CURRENT_QUOTE", "venue-specific quote route", "Quote is execution context only and never a directional predictor.", count=_quote_count(data, market))
    missing = lambda source, note="Required point-in-time dataset is not loaded.": _domain("NO_DATA", source, note)
    bundled = lambda source, note, count=None: _domain("BUNDLED_RESEARCH_AVAILABLE", source, note, count=count)
    current = lambda source, note, count=None: _domain("CURRENT_PUBLIC_SNAPSHOT", source, note, count=count)

    if market == "us":
        filings = current("SEC", "Official current SEC snapshot is present; issuer-level temporal admission remains required.") if _has(ids, "SEC_COMPANY") else missing("SEC dissemination-time filings")
        historical = bundled("research/sp500_panel.parquet", "Real S&P historical OHLCV research panel is bundled. It ends in 2018 and is fixed-constituent/survivor-biased, so it is not current proof.") if domains.get("historical_equity_panel") else missing("historical US panel")
        causal = bundled("extended_universe + chain_reactions + bottleneck_reference", "Causal universe, chain and bottleneck references are bundled; expectations gap and issuer value capture remain unproven.") if domains.get("causal_universe") else missing("causal universe")
        validation = bundled("factor_ic + validated_tickers + metric_grades", "Saved OOS/validation artefacts are bundled. Claims are limited to the tested metric and sample.") if domains.get("saved_validation_results") else missing("saved validation results")
        return {
            "economic_origin": macro, "historical_equity_context": historical, "filing_fundamentals": filings,
            "causal_bottleneck_reference": causal, "saved_validation_evidence": validation,
            "expectations": missing("point-in-time estimates and guidance"),
            "positioning_amplification": missing("signed institutional, borrow and option positioning"),
            "cost_capacity": quote,
        }
    if market == "idx":
        controller = bundled("data/ihsg_conglomerates.json", "Controller/conglomerate and affiliation map is bundled. It is reference context, not signed broker inventory.") if domains.get("controller_conglomerate_reference") else missing("controller map")
        directory = current("IDX official company profiles", "Current issuer directory is present; point-in-time filings and corporate-action history remain required.") if _has(ids, "IDX_COMPANY", "IDX_STOCK") else missing("IDX official issuer records")
        return {
            "economic_origin": macro, "issuer_reference": directory, "controller_free_float": controller,
            "broker_inventory": missing("crossing-adjusted ticker-by-broker inventory"),
            "foreign_flow": missing("point-in-time foreign flow"),
            "filing_fundamentals": missing("IDX dissemination-time issuer filings"), "cost_capacity": quote,
        }
    if market == "commodity":
        hist = bundled("research/macro_panel.parquet", "Historical gold/oil/gas/DXY macro panel is bundled; it is context, not exact contract/roll or current physical-market proof.") if domains.get("historical_macro_cross_asset_file") else missing("historical macro cross-asset panel")
        eia = current("EIA", "Official EIA snapshot exists; series-specific release-vintage admission is pending.") if _has(ids, "EIA") else missing("release-vintage stock-flow balances")
        cot = current("CFTC COT", "Official positioning snapshot exists; publication lag and contract mapping must be admitted.") if _has(ids, "CFTC") else missing("CFTC COT")
        return {"macro_cross_asset_context": hist, "stock_flow_origin": eia, "inventory_surprise": missing("as-released inventory expectations and actuals"), "physical_transmission": missing("grade, location, freight, storage and capacity"), "positioning_amplification": cot, "cost_capacity": quote}
    if market == "fx":
        hist = bundled("research/macro_panel.parquet", "Historical DXY/rates/inflation cross-asset context is bundled; it is not pair-specific point-in-time proof.") if domains.get("historical_macro_cross_asset_file") else missing("historical macro panel")
        official = current("ALFRED / BIS", "Official macro snapshot exists; pair-specific as-of joins remain pending.") if _has(ids, "ALFRED", "BIS") else macro
        cot = current("CFTC TFF", "Official financial positioning exists; pair/contract mapping and publication lag remain required.") if _has(ids, "CFTC") else missing("CFTC TFF/COT")
        cc=data.get("current_context") or {}; ms=((cc.get("macro") or {}).get("series") or {}); ors=((cc.get("official_policy_rates") or {}).get("rates") or {})
        rate_ids=("DFF","ECBDFR","IRSTCI01JPM156N","IRSTCI01GBM156N","IRSTCI01AUM156N","IRSTCI01CAM156N")
        rate_count=sum(isinstance(ms.get(x),Mapping) and ms.get(x,{}).get("value") is not None for x in rate_ids)+sum(isinstance(v,Mapping) and v.get("value") is not None for v in ors.values())
        carry=current("V10.1 policy-rate differential + current FX reference", "Current carry direction can be mapped when pair rates and quote are present. Cross-currency basis, reserves and point-in-time history still cap confidence.", count=rate_count) if rate_count>=2 else missing("current pair policy rates plus forward/basis history")
        return {"historical_cross_asset_context": hist, "relative_macro_origin": official, "policy_and_bop_transmission": official, "expectations": missing("pair-specific consensus and option-implied distribution"), "positioning_amplification": cot, "carry_funding": carry, "cost_capacity": quote}
    if market == "crypto":
        causal = bundled("data/chain_reactions.json", "Cross-market causal-chain references are bundled, but protocol value capture is not proven.") if domains.get("causal_reference") else missing("causal reference")
        protocol = current("Coin Metrics Community", "Protocol records exist; entity adjustment and token-value attribution remain pending.") if _has(ids, "COIN_METRICS") else missing("on-chain and protocol records")
        venue = current("Binance / Deribit", "Venue records exist; collateral, depth and counterparty joins remain incomplete.") if _has(ids, "BINANCE", "DERIBIT") else missing("venue-specific derivatives and flow records")
        return {"causal_reference": causal, "protocol_origin": protocol, "stablecoin_and_unlocks": missing("as-known stablecoin impulse and unlock schedule"), "venue_transmission": venue, "positioning_amplification": venue, "expectations": missing("adoption and value-capture expectations gap"), "cost_capacity": quote}
    raise ValueError(f"Unsupported market: {market}")


def _data_health(data: Mapping[str, Any]) -> dict[str, Any]:
    sources: list[dict[str, Any]] = []
    inv = (((data.get("bundled_research") or {}).get("inventory") or {}).get("datasets") or [])
    for row in inv:
        if isinstance(row, Mapping):
            sources.append({
                "provider": row.get("market", "bundled"), "dataset": row.get("dataset"), "state": row.get("state"),
                "valid_items": row.get("rows", row.get("valid_items", 0)), "capital_eligible": False,
                "note": row.get("note"), "path": row.get("path"), "sha256": row.get("sha256"),
            })
    public = data.get("public_sources") if isinstance(data.get("public_sources"), Mapping) else {}
    for market in MARKETS:
        row = (((public.get("markets") or {}).get(market)) or {})
        sources.append({"provider": market, "dataset": "official_current_snapshot", "state": row.get("state", "ROUTE_ONLY"), "valid_items": row.get("valid_items", 0), "capital_eligible": False, "note": "Current source identity does not prove prediction quality."})
        sources.append({"provider": market, "dataset": "execution_reference_quotes", "state": "AVAILABLE" if _quote_count(data, market) else "NO_CURRENT_QUOTE", "valid_items": _quote_count(data, market), "capital_eligible": False, "note": "Current quote is for valuation/execution context only."})
    sources.append({"provider": "macro", "dataset": "current_fred", "state": "CURRENT_VINTAGE_OBSERVED" if data.get("fred") else "NO_CURRENT_DATA", "valid_items": len(data.get("fred") or {}), "capital_eligible": False, "note": "Historical proof requires release vintages and available_at timestamps."})
    observed = sum(str(x.get("state")) not in {"NO_DATA", "NO_CURRENT_DATA", "NO_CURRENT_QUOTE", "ROUTE_ONLY", "MISSING"} for x in sources)
    return {"overall": "RESEARCH_DATA_AVAILABLE" if observed else "NO_RESEARCH_DATA", "sources": sources, "checked_at": _utc_now()}


def _validation_summary(data: Mapping[str, Any]) -> dict[str, Any]:
    return (((data.get("bundled_research") or {}).get("validation")) or {})


def build_desk(data: Mapping[str, Any], top_per_market: int = 0) -> dict[str, Any]:
    del top_per_market
    markets: dict[str, Any] = {}; coverage = ((data.get("bundled_research") or {}).get("market_coverage") or {})
    for market in data.get("markets") or MARKETS:
        market = str(market); evidence = _market_evidence(data, market); cov = coverage.get(market) or {}
        markets[market] = {
            "label": MARKET_LABELS[market], "evidence_domains": evidence,
            "observed_domains": sum(item.get("state") not in {"NO_DATA", "ROUTE_ONLY", "MISSING", "NO_CURRENT_QUOTE"} for item in evidence.values()),
            "point_in_time_domains_ready": sum(item.get("point_in_time_eligible") is True for item in evidence.values()),
            "quote_count": _quote_count(data, market), "research_data_status": cov.get("state", "NO_DATA"),
            "research_packet_count": cov.get("packet_universe_count", 0), "capital_permission": "PROOF_GATED",
            "decision_reason": "Research data is available and displayed. Capital remains blocked because current quote, exact point-in-time evidence, ticker value bridge and proof are separate requirements.",
        }
    bundled = data.get("bundled_research") or {}; inv = bundled.get("inventory") or {}; refs = bundled.get("reference_counts") or {}
    desk = {
        "meta": {
            "release": "War Room OS V10.1 Carry-Aware Operational Research and Shadow Trading", "version": "10.1", "generated": _utc_now(),
            "source": str(data.get("overall_source") or "BUNDLED_RESEARCH_AVAILABLE"), "sources": dict(data.get("sources") or {}),
            "fred_source": str(data.get("fred_source") or "NO_CURRENT_FRED"),
            "universe_n": sum(len(v) for v in packet_universe().values()),
            "note": "Real bundled research is shown even when capital is blocked. Economics, fundamentals, expectations, flow, positioning, bottlenecks, valuation and causal transmission only; price is reference/outcome, never the active predictor.",
        },
        "systemic": {
            "state": "RESEARCH_CONTEXT_AVAILABLE", "research_data_status": "AVAILABLE" if (inv.get("datasets_present") or 0) else "MISSING",
            "capital_permission": "PROOF_GATED", "claim": "Bundled VIX, Shiller, macro and validation context is visible. No current calibrated regime/trade call is inferred without point-in-time inputs.",
            "validated_metrics": (_validation_summary(data).get("validated_metrics") or []),
            "partial_metrics": (_validation_summary(data).get("partial_metrics") or []),
            "rejected_metrics": (_validation_summary(data).get("rejected_metrics") or []),
        },
        "macro_observations": _macro_observations(data), "markets": markets,
        "execution_quotes": data.get("quotes") or {}, "public_sources": data.get("public_sources") or {},
        "bundled_research": bundled, "universe_summary": {"research_universe": {m: len(v) for m, v in packet_universe().items()}, "reference_counts": refs},
        "data_health": {}, "validation_context": _validation_summary(data),
    }
    desk["data_health"] = _data_health(data); desk = attach_research_kernel(desk)
    packets, alpha_center, action_state = build_packets(markets=markets, quotes=desk.get("execution_quotes") or {}, universe=packet_universe(), proof_registry=desk.get("proof_registry") or {}, current_context=data.get("current_context") or {})
    desk["ticker_packets"] = packets; desk["alpha_center"] = alpha_center; desk["current_action_state"] = action_state; desk["carry_trade"] = action_state.get("carry_trade") or {}; desk["current_context"] = data.get("current_context") or {}
    try:
        from trading_readiness_v99 import audit as audit_trading
        desk["trading_readiness"] = audit_trading()
    except Exception as exc:
        desk["trading_readiness"] = {"software_state": "INCOMPLETE", "capital_permission": "PROOF_GATED", "error": f"{type(exc).__name__}: {exc}"}
    if isinstance(desk.get("trading_readiness"), dict) and desk["trading_readiness"].get("capital_permission") == "BLOCKED":
        desk["trading_readiness"]["capital_permission"] = "PROOF_GATED"
    current_context = data.get("current_context") or {}
    current_quotes = current_context.get("quotes") or {}
    quote_markets = int(current_quotes.get("markets_with_quote") or 0)
    fresh_quote_markets = int(current_quotes.get("markets_with_fresh_quote") or 0)
    research_markets = sum((markets[m].get("research_data_status") or "NO_DATA") != "NO_DATA" for m in markets)
    shadow_count = len(alpha_center.get("shadow_candidates") or [])
    bias_count = len(alpha_center.get("research_biases") or [])
    promoted = len(alpha_center.get("promoted") or [])
    for market, row in (desk.get("markets") or {}).items():
        market_packets = packets.get(market) or {}
        row["research_actions"] = sum(p.get("current_action", {}).get("direction") in {"LONG_BIAS", "SHORT_BIAS"} for p in market_packets.values())
        row["shadow_candidates"] = sum(p.get("current_action", {}).get("permissions", {}).get("shadow_trading") == "ELIGIBLE" for p in market_packets.values())
        row["current_quote_count"] = len(((current_quotes.get("markets") or {}).get(market) or {}))
        row["research_permission"] = "ACTIVE"
        row["shadow_permission"] = "ACTIVE" if row["shadow_candidates"] else "WATCH_ONLY"
        row["systematic_live_permission"] = "ELIGIBLE_REQUIRES_HUMAN_APPROVAL" if any(p.get("current_action", {}).get("permissions", {}).get("systematic_live", "").startswith("ELIGIBLE") for p in market_packets.values()) else "PROOF_GATED"
        row["capital_permission"] = row["systematic_live_permission"]
    desk["mission_control"] = {
        "decision": "SHADOW_CANDIDATES_AVAILABLE" if shadow_count else "CURRENT_RESEARCH_ACTIONS_AVAILABLE" if bias_count else "RESEARCH_CONTEXT_AVAILABLE_REFRESH_CURRENT_DATA",
        "plain_language": "War Room sekarang memisahkan output riset, shadow trading, dan systematic live. LONG/SHORT bias serta rencana entry-target-stop dapat muncul tanpa mengklaim alpha proven; live sistematis tetap terikat proof.",
        "research_data_status": "AVAILABLE", "research_permission": "ACTIVE",
        "research_markets": research_markets, "current_context_markets": int((desk.get("public_sources") or {}).get("markets_with_real_snapshot") or 0),
        "quote_markets": quote_markets, "fresh_quote_markets": fresh_quote_markets,
        "research_biases": bias_count, "shadow_candidates": shadow_count, "promoted_tickers": promoted,
        "shadow_permission": "ACTIVE" if shadow_count else "WATCH_ONLY",
        "systematic_live_permission": "ELIGIBLE_REQUIRES_HUMAN_APPROVAL" if promoted else "PROOF_GATED",
        "capital_permission": "MANUAL_REVIEW_REQUIRED" if promoted else "PROOF_GATED",
        "bundled_datasets_present": inv.get("datasets_present", 0), "bundled_datasets_loaded": inv.get("datasets_loaded", 0),
        "carry_state": (desk.get("carry_trade") or {}).get("state", "INCOMPLETE"), "carry_top_trade": (((desk.get("carry_trade") or {}).get("top_carry_trades") or [{}])[0]).get("trade_expression"),
        "next_actions": ["Refresh current context", "Review carry direction and unwind risk", "Review current LONG/SHORT biases", "Record eligible shadow trades prospectively", "Promote systematic live only after exact proof"],
    }
    desk["data_and_proof"] = {"source_health": desk["data_health"], "public_source_summary": desk["public_sources"], "bundled_inventory": inv, "validation_context": desk["validation_context"], "proof_registry": desk.get("proof_registry") or {}, "trading_readiness": desk.get("trading_readiness") or {}, "claim_limit": "Data availability and capital permission are intentionally separate."}
    return desk


def build_fast_desk(data: Mapping[str, Any], top_per_market: int = 0) -> dict[str, Any]:
    return build_desk(data, top_per_market=top_per_market)


def render_dashboard(desk: Mapping[str, Any], template_path: str, out_path: str) -> bool:
    template = Path(template_path)
    if not template.exists(): return False
    html = template.read_text(encoding="utf-8")
    payload = "window.DASHBOARD_DATA=" + json.dumps(desk, default=str, separators=(",", ":"), ensure_ascii=False).replace("</", "<\\/") + ";"
    html = html.replace("/*__INJECT_DATA__*/", payload, 1) if "/*__INJECT_DATA__*/" in html else html.replace("<body>", "<body><script>" + payload + "</script>", 1)
    Path(out_path).write_text(html, encoding="utf-8"); return True


def print_summary(desk: Mapping[str, Any]) -> None:
    mc = desk.get("mission_control") or {}
    print("WAR ROOM OS V10.1 — OPERATIONAL RESEARCH + SHADOW TRADING")
    print(f"Research: {mc.get('research_permission')} · shadow: {mc.get('shadow_permission')} · systematic live: {mc.get('systematic_live_permission')}")
    for market, row in (desk.get("markets") or {}).items():
        print(f"{market}: {row.get('research_data_status')} · {row.get('observed_domains', 0)} observed domains · {row.get('research_packet_count', 0)} packets · {row.get('quote_count', 0)} current quotes")


def main() -> None:
    parser = argparse.ArgumentParser(description="War Room OS V10.1 operational runtime")
    parser.add_argument("--offline", action="store_true"); parser.add_argument("--markets", default=None)
    parser.add_argument("--out", default=str(HERE / "desk_data.json")); parser.add_argument("--template", default=str(HERE / "dashboard.html")); parser.add_argument("--html", default=str(HERE / "dashboard_live.html"))
    args = parser.parse_args(); markets = args.markets.split(",") if args.markets else None
    data = DL.load_all(markets=markets, allow_live=not args.offline, allow_synthetic=False); desk = build_desk(data)
    Path(args.out).write_text(json.dumps(desk, indent=2, default=str), encoding="utf-8"); render_dashboard(desk, args.template, args.html); print_summary(desk)


if __name__ == "__main__": main()
