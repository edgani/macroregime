"""Offline validation for the War Room live-data overlay.

This does not claim provider credentials or network reachability. It validates parsers,
semantics, failover behavior, Python compilation and dashboard JavaScript syntax.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch
import json
import os
import py_compile
import subprocess
import time

import live_market_intelligence as L
import full_live_data_hub as F

HERE = Path(__file__).resolve().parent


def assert_true(value, message):
    if not value:
        raise AssertionError(message)


def option_fixture():
    spot = 100.0
    rows = []
    for expiry in ("2026-08-21", "2026-09-18"):
        for strike in (90, 95, 100, 105, 110):
            rows.append({"provider":"Massive","underlying":"TEST","contract":f"C{strike}","option_type":"call","strike":strike,"expiration":expiry,"open_interest":1000+(strike-90)*20,"volume":200,"implied_volatility":0.30,"delta":0.25 if strike>=105 else 0.55,"gamma":0.03,"theta":-0.04,"vega":0.12,"bid":max(0.2, 11-(strike-90)*0.9),"ask":max(0.3, 11.4-(strike-90)*0.9),"last_price":1.0,"underlying_price":spot})
            rows.append({"provider":"Massive","underlying":"TEST","contract":f"P{strike}","option_type":"put","strike":strike,"expiration":expiry,"open_interest":900+(110-strike)*25,"volume":180,"implied_volatility":0.34,"delta":-0.25 if strike<=95 else -0.50,"gamma":0.028,"theta":-0.04,"vega":0.11,"bid":max(0.2, 1+(strike-90)*0.9),"ask":max(0.3, 1.4+(strike-90)*0.9),"last_price":1.0,"underlying_price":spot})
    return rows


def validate_options():
    flow = [{"ticker":"TEST","option_type":"CALL","premium":1_000_000,"ask_side_pct":0.8}]
    summary = L.summarize_option_chain("TEST", option_fixture(), flow)
    assert_true(summary["state"] == "LIVE", "option summary did not load")
    assert_true(summary["zones"]["call_wall"] is not None, "call wall missing")
    assert_true(summary["zones"]["put_wall"] is not None, "put wall missing")
    assert_true(summary["zones"]["expected_move"] is not None, "expected move missing")
    assert_true(summary["calibrated_probability"] is None, "context was mislabeled as probability")
    assert_true("not dealer inventory" in summary["semantics"]["gamma"].lower(), "gamma caveat missing")
    return summary


def validate_crypto():
    rows = [
        {"provider":"Binance","asset":"BTC","state":"LIVE","mark_price":100_000,"open_interest_value":20_000_000_000,"funding_rate":-0.00015,"global_long_short_ratio":0.75,"taker_buy_sell_ratio":1.25},
        {"provider":"Bybit","asset":"BTC","state":"LIVE","mark_price":100_100,"open_interest_value":8_000_000_000,"funding_rate":-0.00010,"global_long_short_ratio":0.80,"taker_buy_sell_ratio":None},
        {"provider":"OKX","asset":"BTC","state":"LIVE","mark_price":99_950,"open_interest_value":5_000_000_000,"funding_rate":-0.00012,"global_long_short_ratio":None,"taker_buy_sell_ratio":None},
    ]
    out = L.aggregate_crypto_asset("BTC", rows)
    assert_true(out["state"] == "LIVE", "crypto aggregate not live")
    assert_true(out["short_squeeze_pressure"] > out["long_squeeze_pressure"], "negative funding/short crowd did not raise short-squeeze context")
    assert_true(out["calibrated_probability"] is None, "squeeze index was mislabeled as probability")
    return out



def validate_uw_integrated_context():
    rows = [
        {"topic":"greek-flow","ticker":"TEST","received_at":1784419200,"payload":{"dir_delta_flow":"1500000","total_delta_flow":"2100000","dir_vega_flow":"300000","total_vega_flow":"450000"}},
        {"topic":"greek-flow","ticker":"TEST","received_at":1784419500,"payload":{"dir_delta_flow":"1200000","dir_vega_flow":"250000"}},
        {"topic":"live-gex","ticker":"TEST","received_at":1784419501,"payload":{"strike":"105","net_gex":"2000000","zero_gamma_level":"99"}},
        {"topic":"option-states","ticker":"TEST","received_at":1784419502,"payload":{"option_symbol":"TEST260821C00100000","open_interest":"2500","volume":"800","implied_volatility":"0.32"}},
        {"topic":"interpolated-iv","ticker":"TEST","received_at":1784419503,"payload":{"expected_move":"6.5","days":"7","atm_iv":"0.31"}},
        {"topic":"net-flow","ticker":"__GLOBAL__","received_at":1784419504,"payload":{"key":"Technology","net_call_premium":"5000000","net_put_premium":"1000000"}},
    ]
    live = L.summarize_uw_live_rows(rows)
    assert_true(live["directional_delta_flow"] == 2700000, "UW directional delta aggregation failed")
    assert_true(live["directional_delta_persistence_5m"] == 1.0, "UW persistence failed")
    assert_true(live["option_state_open_interest"] == 2500, "UW option-state OI failed")
    assert_true(live["sector_rotation"][0]["key"] == "Technology", "UW sector rotation failed")
    chain = L.summarize_option_chain("TEST", option_fixture(), ())
    integrated = L.integrate_option_context(chain, live)
    assert_true(integrated["directional_context"] == "UPSIDE_PRESSURE_CONTEXT", "integrated direction failed")
    assert_true(integrated["calibrated_probability"] is None, "integrated context mislabeled as probability")
    assert_true(integrated["reference_zones"].get("stream_zero_gamma_level") == 99, "streamed gamma level missing")
    return integrated


def validate_full_hub_offline():
    desk={"markets":{},"alpha":[],"macro_observations":{},"market_breadth":{},"rotation_snapshot":{},"meta":{"generated":"2026-07-19T00:00:00Z"}}
    with patch.dict(os.environ, {"WARROOM_NETWORK_MODE":"offline"}, clear=False):
        out=F.collect_full_live_data(desk)
    assert_true(len(out["tab_coverage"]) == len(F.REQUIREMENTS), "full-hub tab coverage incomplete")
    assert_true(out["rules"]["no_synthetic"] is True, "full hub no-synthetic rule missing")
    assert_true(not any(x.get("state") == "LIVE" and x.get("provider") in {"SEC EDGAR","EIA","CFTC","DeFiLlama"} for x in out["statuses"]), "offline mode emitted public network data")
    return out

def validate_stale_failover():
    key = "offline_failover_test"
    path = L._cache_path(key)
    L._write_cache(key, {"payload":{"ok":1},"fetched_at":"2026-07-19T00:00:00Z"})
    old = time.time() - 120
    os.utime(path, (old, old))
    with patch.object(L.HTTP, "get", side_effect=RuntimeError("offline")):
        result = L._request_json(provider="TEST",dataset="FAILOVER",cache_key=key,url="https://invalid.example",ttl_seconds=1,stale_after_seconds=60,timeout=0.1)
    assert_true(result["state"] == "STALE", "last-good cache was not returned as STALE")
    assert_true(result["payload"] == {"ok":1}, "stale payload changed")
    path.unlink(missing_ok=True)



def validate_provider_parsers():
    now = 1784419200000
    def fake_request(**kwargs):
        url = kwargs["url"]
        if "binance.com" in url and "premiumIndex" in url:
            payload = {"markPrice":"100","indexPrice":"99.9","lastFundingRate":"-0.0001","nextFundingTime":now,"time":now}
        elif "binance.com" in url and "openInterest" in url:
            payload = {"openInterest":"1000","time":now}
        elif "globalLongShortAccountRatio" in url:
            payload = [{"longShortRatio":"0.8","longAccount":"0.444","shortAccount":"0.556","timestamp":now}]
        elif "takerlongshortRatio" in url:
            payload = [{"buySellRatio":"1.2","buyVol":"12","sellVol":"10","timestamp":now}]
        elif "bybit.com" in url and "tickers" in url:
            payload = {"result":{"list":[{"markPrice":"100","indexPrice":"99.9","fundingRate":"-0.0001","nextFundingTime":str(now),"openInterest":"1000","turnover24h":"1000000","volume24h":"10000"}]}}
        elif "bybit.com" in url and "open-interest" in url:
            payload = {"result":{"list":[{"openInterest":"1000","timestamp":str(now)}]}}
        elif "bybit.com" in url and "account-ratio" in url:
            payload = {"result":{"list":[{"buyRatio":"0.45","sellRatio":"0.55","timestamp":str(now)}]}}
        elif "okx.com" in url and "/ticker" in url:
            payload = {"data":[{"last":"100","ts":str(now),"vol24h":"100","volCcy24h":"10000"}]}
        elif "okx.com" in url and "open-interest" in url:
            payload = {"data":[{"oi":"1000","oiUsd":"100000","ts":str(now)}]}
        elif "okx.com" in url and "funding-rate" in url:
            payload = {"data":[{"fundingRate":"-0.0001","fundingTime":str(now),"nextFundingTime":str(now+28800000),"markPx":"100","indexPx":"99.9"}]}
        elif "deribit.com" in url:
            payload = {"result":[{"instrument_name":"BTC-21AUG26-100000-C","open_interest":100,"volume":20,"mark_price":0.03,"bid_price":0.02,"ask_price":0.04,"mark_iv":60,"underlying_price":100000,"creation_timestamp":now},{"instrument_name":"BTC-21AUG26-100000-P","open_interest":120,"volume":18,"mark_price":0.04,"bid_price":0.03,"ask_price":0.05,"mark_iv":64,"underlying_price":100000,"creation_timestamp":now}]}
        elif "massive.com" in url:
            payload = {"results":[{"details":{"ticker":"O:TEST260821C00100000","contract_type":"call","strike_price":100,"expiration_date":"2026-08-21"},"greeks":{"delta":0.5,"gamma":0.02,"theta":-0.03,"vega":0.1},"last_quote":{"bid":4.8,"ask":5.2,"last_updated":now*1000000},"last_trade":{"price":5,"size":10,"sip_timestamp":now*1000000},"day":{"volume":1000},"underlying_asset":{"price":100},"open_interest":2000,"implied_volatility":0.3}]}
        elif "coinglass.com" in url and "open-interest" in url:
            payload = {"data":[{"exchange":"All","symbol":"BTC","open_interest_usd":1000000,"open_interest_change_percent_15m":2}]}
        elif "coinglass.com" in url and "funding-rate" in url:
            payload = {"data":[{"symbol":"BTC","stablecoin_margin_list":[{"exchange":"Binance","funding_rate":-0.001}]}]}
        elif "coinglass.com" in url and "exchange-list" in url:
            payload = {"data":[{"exchange":"All","liquidation_usd":100000,"long_liquidation_usd":20000,"short_liquidation_usd":80000}]}
        elif "aggregated-heatmap" in url:
            payload = {"data":{"y_axis":[95000,100000,105000],"liquidation_leverage_data":[[0,0,100],[0,2,200]],"price_candlesticks":[]}}
        elif "aggregated-map" in url:
            payload = {"data":{"data":{"95000":[[95000,500,25,None]],"105000":[[105000,800,25,None]]}}}
        else:
            raise AssertionError(f"unhandled fixture URL {url}")
        return {"ok":True,"state":"LIVE","payload":payload,"fetched_at":"2026-07-19T00:00:00Z","age_seconds":0,"note":"fixture"}

    with patch.object(L, "_request_json", side_effect=fake_request):
        b = L.fetch_binance_symbol("BTCUSDT")
        y = L.fetch_bybit_symbol("BTCUSDT")
        o = L.fetch_okx_symbol("BTC")
        d = L.fetch_deribit_currency("BTC")
        with patch.dict(os.environ, {"MASSIVE_API_KEY":"fixture", "COINGLASS_API_KEY":"fixture"}, clear=False):
            m = L.fetch_massive_option_chain("TEST")
            c = L.fetch_coinglass_asset("BTC")
    assert_true(b["row"]["open_interest_value"] == 100000, "Binance parser failed")
    assert_true(y["row"]["global_long_short_ratio"] is not None, "Bybit ratio parser failed")
    assert_true(o["row"]["open_interest_value"] == 100000, "OKX parser failed")
    assert_true(len(d["data"]) == 2, "Deribit parser failed")
    assert_true(len(m["data"]) == 1 and m["data"][0]["gamma"] == 0.02, "Massive option parser failed")
    zones = L.derive_liquidation_zones(c["row"], 100000)
    assert_true(zones["nearest_above"]["price"] == 105000 and zones["nearest_below"]["price"] == 95000, "CoinGlass liquidation-zone parser failed")


def validate_files():
    files = ["app.py","institutional_data.py","live_market_intelligence.py","run.py","data_layer.py"]
    for name in files:
        py_compile.compile(str(HERE/name), doraise=True)
    html = (HERE/"dashboard.html").read_text(encoding="utf-8")
    js = html.split("<script>")[-1].split("</script>")[0]
    js_path = HERE/".cache"/"dashboard_validate.js"
    js_path.parent.mkdir(exist_ok=True)
    js_path.write_text(js, encoding="utf-8")
    node = subprocess.run(["node","--check",str(js_path)],capture_output=True,text=True)
    assert_true(node.returncode == 0, f"dashboard JavaScript invalid: {node.stderr}")
    assert_true("DERIVATIVES / SQUEEZE" in html, "derivatives workspace missing")
    source = (HERE/"live_market_intelligence.py").read_text(encoding="utf-8").lower()
    assert_true("synthetic" in source and "no synthetic" in source, "no-synthetic contract missing")


def main():
    options = validate_options()
    crypto = validate_crypto()
    integrated = validate_uw_integrated_context()
    full_hub = validate_full_hub_offline()
    validate_stale_failover()
    validate_provider_parsers()
    validate_files()
    result = {
        "status":"PASS",
        "offline_scope":["options analytics","streamed Greek-flow integration","sector options rotation","crypto pressure context","full tab-coverage hub","provider payload parsers","liquidation zones","stale last-good failover","Python compile","dashboard JS syntax"],
        "not_verified_without_credentials_or_network":["provider authentication","entitlements","exchange reachability","live payload schema changes"],
        "sample":{"options_context":options["directional_context"],"integrated_context":integrated["directional_context"],"evidence_completeness_pct":integrated["evidence_completeness_pct"],"gamma_context":options["gamma_context"],"crypto_short_squeeze_pressure":crypto["short_squeeze_pressure"],"tab_coverage_count":len(full_hub["tab_coverage"])}
    }
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
