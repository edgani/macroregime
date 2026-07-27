from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from final_trading_core_v79 import CoreConfig, build_trade_instruction
from release_contract_v79 import SYSTEM_ID, release_contract, validate_runtime_desk
from research_evidence_v79 import load_research_evidence_v79
from us_broad_equity_live_feed_v79 import _completed_monthly, _consensus, _parse_fred_csv, _parse_yahoo_payload


def rows(values, start="2025-07-01"):
    dates = pd.date_range(start, periods=len(values), freq="MS")
    return [{"observed_month": x.date().isoformat(), "close": float(v)} for x, v in zip(dates, values)]


def main():
    checks = {}

    def ck(name, condition, detail=None):
        checks[name] = bool(condition)
        if not condition:
            raise AssertionError(f"{name}: {detail}")

    contract = release_contract()
    ck("contract_final_exact_scope", contract["final_trading_system"] is True and contract["decision_active_systems"] == [SYSTEM_ID])
    ck("contract_no_ticker_selector", contract["decision_active_ticker_selectors"] == 0)
    ck("contract_no_cross_market_direction", contract["decision_active_cross_market_directional_components"] == 0)

    on_rows = rows([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111])
    no_auth = build_trade_instruction(on_rows, config=CoreConfig(baseline_authorized=False), as_of="2026-07-26", verified_live_feed=True)
    ck("baseline_authorization_required", no_auth.status == "BASELINE_AUTHORIZATION_REQUIRED" and not no_auth.ready_to_execute)

    manual = build_trade_instruction(
        on_rows,
        config=CoreConfig(baseline_authorized=True),
        as_of="2026-07-26",
        verified_live_feed=False,
    )
    ck("manual_data_never_executable", manual.status == "DATA_SOURCE_UNVERIFIED" and not manual.ready_to_execute)

    on = build_trade_instruction(
        on_rows,
        config=CoreConfig(baseline_authorized=True, sleeve_fraction_of_account=0.25),
        as_of="2026-07-26",
        current_equity_weight_in_sleeve=0.0,
        estimated_one_way_cost_bps=10,
        verified_live_feed=True,
    )
    ck("risk_on_ready", on.ready_to_execute and on.signal == "EQUITY")
    ck("risk_on_action", on.action.startswith("BUY SPY"), on.to_dict())
    ck("account_sleeve_math", abs(on.target_equity_weight_of_account - 0.25) < 1e-12)

    off_rows = rows([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 70])
    off = build_trade_instruction(
        off_rows,
        config=CoreConfig(baseline_authorized=True),
        as_of="2026-07-26",
        current_equity_weight_in_sleeve=1.0,
        estimated_one_way_cost_bps=10,
        verified_live_feed=True,
    )
    ck("risk_off_ready", off.ready_to_execute and off.signal == "CASH")
    ck("risk_off_action", off.action.startswith("SELL SPY"), off.to_dict())

    costly = build_trade_instruction(
        on_rows,
        config=CoreConfig(baseline_authorized=True),
        as_of="2026-07-26",
        estimated_one_way_cost_bps=25.01,
        verified_live_feed=True,
    )
    ck("cost_guard", costly.status == "COST_GUARD_BLOCKED" and not costly.ready_to_execute)

    stale = build_trade_instruction(
        on_rows,
        config=CoreConfig(baseline_authorized=True),
        as_of="2026-10-01",
        verified_live_feed=True,
    )
    ck("stale_fail_closed", stale.status == "DATA_FAIL_CLOSED" and stale.signal == "NO_TRADE")

    bad_instrument = build_trade_instruction(
        on_rows,
        config=CoreConfig(equity_instrument="QQQ", baseline_authorized=True),
        as_of="2026-07-26",
        verified_live_feed=True,
    )
    ck("unproven_instrument_blocked", bad_instrument.status == "CONFIGURATION_BLOCKED")

    for inst in (on, off):
        ck(f"no_short_{inst.signal}", inst.short_permission is False)
        ck(f"no_leverage_{inst.signal}", inst.leverage_permission is False)
        ck(f"no_ticker_{inst.signal}", inst.ticker_selection_permission is False)
        ck(f"no_intramonth_{inst.signal}", inst.intramonth_override_permission is False)
        ck(f"no_target_stop_{inst.signal}", inst.target_price_permission is False and inst.stop_price_permission is False)

    daily = pd.DataFrame({
        "Date": pd.to_datetime(["2026-05-29", "2026-06-29", "2026-06-30", "2026-07-01", "2026-07-24"], utc=True),
        "Close": [7300, 7440, 7499.36, 7483, 7411.98],
    })
    # Add enough earlier completed months for the feed contract.
    older = pd.DataFrame({
        "Date": pd.date_range("2025-07-31", periods=10, freq="ME", tz="UTC"),
        "Close": range(6500, 6510),
    })
    completed = _completed_monthly(pd.concat([older, daily], ignore_index=True), as_of="2026-07-26")
    ck("current_month_excluded", completed[-1]["observed_month"] == "2026-06-01")
    ck("actual_completed_month_close_kept", abs(completed[-1]["close"] - 7499.36) < 1e-9)

    fred_rows = rows([100, 101, 102, 103, 104, 105, 106, 107, 108, 109], start="2025-09-01")
    yahoo_rows = [{**r, "close": r["close"] + 0.01} for r in fred_rows]
    canonical, consensus = _consensus(fred_rows, yahoo_rows)
    ck("dual_source_consensus_pass", canonical[-1]["observed_month"] == yahoo_rows[-1]["observed_month"] and consensus["months_compared"] == 10)
    mismatch_blocked = False
    try:
        bad_yahoo = [dict(r) for r in yahoo_rows]
        bad_yahoo[-1]["close"] += 25.0
        _consensus(fred_rows, bad_yahoo)
    except ValueError:
        mismatch_blocked = True
    ck("dual_source_mismatch_blocked", mismatch_blocked)

    fixture_dates = pd.date_range("2025-09-30", periods=10, freq="ME", tz="UTC")
    fixture_closes = [6800.0 + i for i in range(10)]
    fred_text = "observation_date,SP500\n" + "\n".join(f"{d.date().isoformat()},{v}" for d, v in zip(fixture_dates, fixture_closes)) + "\n"
    fred_parsed = _parse_fred_csv(fred_text, as_of="2026-07-26")
    ck("fred_parser_fixture", len(fred_parsed) == 10 and fred_parsed[-1]["close"] == fixture_closes[-1])
    yahoo_payload = {"chart": {"result": [{"timestamp": [int(d.timestamp()) for d in fixture_dates], "indicators": {"quote": [{"close": fixture_closes}]}}], "error": None}}
    yahoo_parsed = _parse_yahoo_payload(yahoo_payload, as_of="2026-07-26")
    ck("yahoo_parser_fixture", yahoo_parsed == fred_parsed)

    ev = load_research_evidence_v79(live=False)
    ck("proof_receipt_pass", ev["proof"]["status"] == "PASS", ev["proof"])
    ck("evidence_final_exact_scope", ev["final_trading_system"] is True and ev["system_id"] == SYSTEM_ID)
    ck("offline_validation_no_order", ev["current_instruction"]["ready_to_execute"] is False)
    ck("other_markets_no_trade", all(v == "NO_TRADE_RESEARCH_ONLY" for v in ev["all_other_markets"].values()))

    runtime = validate_runtime_desk({"release_contract_v79": contract, "research_evidence_v79": ev})
    ck("runtime_contract_pass", runtime["status"] == "PASS", runtime)

    print(json.dumps({"status": "PASS", "passed": sum(checks.values()), "total": len(checks), "checks": checks}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
