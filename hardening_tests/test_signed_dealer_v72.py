from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
import hashlib
import json
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd

from dealer_gamma_research_v72 import (
    V72DataError,
    aggregate_exposure,
    aggregate_quote_surface_exposure,
    build_formatted_symbol,
    join_tbt_grk,
    reconstruct_omm_positions,
    reconstruct_positions_from_tbt,
    research_status,
    validate_grk,
    validate_option_quotes,
    validate_source_manifest,
    validate_tbt,
    validate_underlier,
)

REPORT = ROOT / "V72_SIGNED_DEALER_VALIDATION.json"


def tbt_fixture(trading_dt: str = "2020-07-02") -> pd.DataFrame:
    rows = [
        {
            "transact_time": f"{trading_dt}T13:30:01Z", "trading_dt": trading_dt,
            "floor_action_ts": f"{trading_dt}T13:30:01Z", "underlying": "SPX", "osi_root": "SPXW",
            "expire_date": "2020-07-02", "call_put_flag": "C", "strike_price": 3100.0,
            "size": 10, "price": 12.5, "nbbo_bid": 12.4, "nbbo_ask": 12.6,
            "bbo_bid": 12.4, "bbo_ask": 12.6, "side": "B", "open_close": "O",
            "capacity": "M", "trade_type": "45", "exec_id": "E1", "complex_exec_id": "",
            "session": "RTH", "trading_segment": 2,
        },
        {
            "transact_time": f"{trading_dt}T13:30:01Z", "trading_dt": trading_dt,
            "floor_action_ts": f"{trading_dt}T13:30:01Z", "underlying": "SPX", "osi_root": "SPXW",
            "expire_date": "2020-07-02", "call_put_flag": "C", "strike_price": 3100.0,
            "size": 10, "price": 12.5, "nbbo_bid": 12.4, "nbbo_ask": 12.6,
            "bbo_bid": 12.4, "bbo_ask": 12.6, "side": "S", "open_close": "O",
            "capacity": "C", "trade_type": "45", "exec_id": "E1", "complex_exec_id": "",
            "session": "RTH", "trading_segment": 2,
        },
        {
            "transact_time": f"{trading_dt}T13:31:01Z", "trading_dt": trading_dt,
            "floor_action_ts": f"{trading_dt}T13:31:01Z", "underlying": "SPX", "osi_root": "SPXW",
            "expire_date": "2020-07-02", "call_put_flag": "C", "strike_price": 3100.0,
            "size": 4, "price": 13.0, "nbbo_bid": 12.9, "nbbo_ask": 13.1,
            "bbo_bid": 12.9, "bbo_ask": 13.1, "side": "B", "open_close": "C",
            "capacity": "C", "trade_type": "45", "exec_id": "E2", "complex_exec_id": "",
            "session": "RTH", "trading_segment": 2,
        },
        {
            "transact_time": f"{trading_dt}T13:31:01Z", "trading_dt": trading_dt,
            "floor_action_ts": f"{trading_dt}T13:31:01Z", "underlying": "SPX", "osi_root": "SPXW",
            "expire_date": "2020-07-02", "call_put_flag": "C", "strike_price": 3100.0,
            "size": 4, "price": 13.0, "nbbo_bid": 12.9, "nbbo_ask": 13.1,
            "bbo_bid": 12.9, "bbo_ask": 13.1, "side": "S", "open_close": "C",
            "capacity": "N", "trade_type": "45", "exec_id": "E2", "complex_exec_id": "",
            "session": "RTH", "trading_segment": 2,
        },
    ]
    return pd.DataFrame(rows)


def grk_fixture(trading_dt: str = "2020-07-02") -> pd.DataFrame:
    return pd.DataFrame([
        {
            "transact_time": f"{trading_dt}T13:30:03Z", "trading_dt": trading_dt,
            "formatted_symbol": "SPXW200702C3100", "price": 12.5,
            "delta": 0.52, "gamma": 0.0010, "vega": 1.2, "rho": 0.1, "theta": -2.0, "theo_price": 12.55,
        },
        {
            "transact_time": f"{trading_dt}T13:31:03Z", "trading_dt": trading_dt,
            "formatted_symbol": "SPXW200702C3100", "price": 13.0,
            "delta": 0.55, "gamma": 0.0011, "vega": 1.1, "rho": 0.1, "theta": -1.9, "theo_price": 13.02,
        },
    ])


def quote_fixture(trading_dt: str = "2020-07-02") -> pd.DataFrame:
    return pd.DataFrame([
        {"underlying_symbol": "^SPX", "quote_datetime": f"{trading_dt}T13:30:30Z", "root": "SPXW",
         "expiration": trading_dt, "strike": 3100.0, "option_type": "C", "bid_size": 20, "bid": 12.4,
         "ask_size": 22, "ask": 12.6, "open_interest": 1200, "active_underlying_price": 3102.0, "implied_volatility": 0.22,
         "delta": 0.52, "gamma": 0.0010, "theta": -2.0, "vega": 1.2, "rho": 0.1},
        {"underlying_symbol": "^SPX", "quote_datetime": f"{trading_dt}T13:31:30Z", "root": "SPXW",
         "expiration": trading_dt, "strike": 3100.0, "option_type": "C", "bid_size": 18, "bid": 12.9,
         "ask_size": 20, "ask": 13.1, "open_interest": 1210, "active_underlying_price": 3104.0, "implied_volatility": 0.21,
         "delta": 0.55, "gamma": 0.0011, "theta": -1.9, "vega": 1.1, "rho": 0.1},
        {"underlying_symbol": "^SPX", "quote_datetime": f"{trading_dt}T13:30:30Z", "root": "SPXW",
         "expiration": trading_dt, "strike": 3000.0, "option_type": "P", "bid_size": 10, "bid": 1.0,
         "ask_size": 12, "ask": 1.2, "open_interest": 800, "active_underlying_price": 3102.0, "implied_volatility": 0.25,
         "delta": -0.08, "gamma": 0.0003, "theta": -0.4, "vega": 0.4, "rho": -0.1},
        {"underlying_symbol": "^SPX", "quote_datetime": f"{trading_dt}T13:31:30Z", "root": "SPXW",
         "expiration": trading_dt, "strike": 3000.0, "option_type": "P", "bid_size": 11, "bid": 0.9,
         "ask_size": 12, "ask": 1.1, "open_interest": 805, "active_underlying_price": 3104.0, "implied_volatility": 0.24,
         "delta": -0.07, "gamma": 0.00028, "theta": -0.35, "vega": 0.38, "rho": -0.1},
    ])


def underlier_fixture(trading_dt: str = "2020-07-02") -> pd.DataFrame:
    return pd.DataFrame([
        {"transact_time": f"{trading_dt}T13:30:00Z", "trading_dt": trading_dt, "spot": 3102.0, "es_traded_notional": 2.0e9, "es_depth_notional": 5.0e8},
        {"transact_time": f"{trading_dt}T13:31:00Z", "trading_dt": trading_dt, "spot": 3104.0, "es_traded_notional": 2.2e9, "es_depth_notional": 5.1e8},
    ])


def must_raise(fn, contains: str | None = None) -> None:
    try:
        fn()
    except V72DataError as exc:
        if contains and contains.lower() not in str(exc).lower():
            raise AssertionError(f"wrong error: {exc}")
        return
    raise AssertionError("expected V72DataError")


def main() -> int:
    checks: list[dict] = []

    def check(name: str, fn) -> None:
        try:
            fn()
            checks.append({"name": name, "status": "PASS"})
        except Exception as exc:
            checks.append({"name": name, "status": "FAIL", "error": f"{type(exc).__name__}: {exc}"})

    validated = validate_tbt(tbt_fixture())
    validated_grk = validate_grk(grk_fixture())

    check("valid_tbt_schema", lambda: None if len(validated) == 4 else (_ for _ in ()).throw(AssertionError()))
    check("official_formatted_symbol", lambda: None if set(validated["formatted_symbol"]) == {"SPXW200702C3100"} else (_ for _ in ()).throw(AssertionError()))
    check("market_maker_buy_positive", lambda: None if float(validated.loc[validated["exec_id"].eq("E1") & validated["is_market_maker"], "signed_mm_contracts"].iloc[0]) == 10 else (_ for _ in ()).throw(AssertionError()))
    check("market_maker_sell_negative", lambda: None if float(validated.loc[validated["exec_id"].eq("E2") & validated["is_market_maker"], "signed_mm_contracts"].iloc[0]) == -4 else (_ for _ in ()).throw(AssertionError()))
    check("customer_flow_ignored", lambda: None if validated.loc[~validated["is_market_maker"], "signed_mm_contracts"].eq(0).all() else (_ for _ in ()).throw(AssertionError()))

    check("reject_non_spx", lambda: must_raise(lambda: validate_tbt(tbt_fixture().assign(underlying="NDX")), "non-SPX"))
    check("reject_non_spx_root", lambda: must_raise(lambda: validate_tbt(tbt_fixture().assign(osi_root="NDX")), "unsupported OSI"))
    check("reject_non_rth", lambda: must_raise(lambda: validate_tbt(tbt_fixture().assign(session="GTH")), "non-RTH"))
    crossed = tbt_fixture(); crossed.loc[0, "nbbo_ask"] = 12.0
    check("reject_crossed_quote", lambda: must_raise(lambda: validate_tbt(crossed), "crossed"))
    duplicated = pd.concat([tbt_fixture(), tbt_fixture().iloc[[0]]], ignore_index=True)
    check("reject_exact_duplicate", lambda: must_raise(lambda: validate_tbt(duplicated), "duplicate"))
    provisional = tbt_fixture(); provisional.loc[0, "trade_type"] = "57"
    check("reject_provisional_without_final_flag", lambda: must_raise(lambda: validate_tbt(provisional), "provisional"))
    check("allow_provisional_only_with_final_flag", lambda: validate_tbt(provisional, final_corrections_confirmed=True))

    dup_grk = pd.concat([grk_fixture(), grk_fixture().iloc[[0]]], ignore_index=True)
    check("reject_duplicate_grk_key", lambda: must_raise(lambda: validate_grk(dup_grk), "duplicate"))

    joined, join_diag = join_tbt_grk(validated, validated_grk)
    check("official_forward_asof_match", lambda: None if join_diag["match_rate"] == 1.0 and join_diag["maximum_join_seconds"] == 2.0 else (_ for _ in ()).throw(AssertionError(join_diag)))
    stale = grk_fixture(); stale["transact_time"] = pd.to_datetime(stale["transact_time"], utc=True) + pd.Timedelta(seconds=10)
    check("reject_stale_grk_match", lambda: must_raise(lambda: join_tbt_grk(validated, validate_grk(stale)), "match rate"))
    wrong_symbol = grk_fixture().assign(formatted_symbol="SPXW200702P3100")
    check("reject_cross_contract_grk_match", lambda: must_raise(lambda: join_tbt_grk(validated, validate_grk(wrong_symbol)), "match rate"))

    positions, position_diag = reconstruct_omm_positions(joined)
    final_mm = float(positions.sort_values("transact_time")["omm_net_contracts"].iloc[-1])
    check("position_reconstruction_known_answer", lambda: None if final_mm == 6.0 else (_ for _ in ()).throw(AssertionError(final_mm)))
    check("post_acquisition_series_eligible", lambda: None if positions["analysis_eligible"].all() else (_ for _ in ()).throw(AssertionError(position_diag)))

    legacy_tbt = validate_tbt(tbt_fixture("2019-10-07")); legacy_grk = validate_grk(grk_fixture("2019-10-07"))
    legacy_joined, _ = join_tbt_grk(legacy_tbt, legacy_grk)
    legacy_positions, legacy_diag = reconstruct_omm_positions(legacy_joined)
    check("legacy_series_quarantined", lambda: None if not legacy_positions["analysis_eligible"].any() and legacy_diag["legacy_series_quarantined"] == 1 else (_ for _ in ()).throw(AssertionError(legacy_diag)))

    underlier = validate_underlier(underlier_fixture())
    check("valid_underlier", lambda: None if len(underlier) == 2 else (_ for _ in ()).throw(AssertionError()))
    bad_underlier = underlier_fixture(); bad_underlier.loc[0, "es_depth_notional"] = 0
    check("reject_invalid_underlier_liquidity", lambda: must_raise(lambda: validate_underlier(bad_underlier), "positive"))

    exposure, exposure_diag = aggregate_exposure(positions, underlier_fixture())
    check("exposure_aggregation_nonempty", lambda: None if len(exposure) == 2 else (_ for _ in ()).throw(AssertionError(exposure_diag)))
    check("dealer_gamma_has_no_direction", lambda: None if exposure["standalone_direction"].eq("WITHHELD").all() else (_ for _ in ()).throw(AssertionError()))
    check("capital_always_blocked", lambda: None if exposure["capital_permission"].eq("BLOCKED").all() and exposure["live_decision_weight"].eq(0).all() else (_ for _ in ()).throw(AssertionError()))
    check("positive_gamma_is_damping_context", lambda: None if exposure.iloc[0]["hedge_regime"] == "DAMPING_CONTEXT" else (_ for _ in ()).throw(AssertionError(exposure.iloc[0].to_dict())))

    # Invert both MM sides so the end-state is negative; the context may amplify but still cannot predict direction.
    inverted = tbt_fixture()
    inverted.loc[inverted["capacity"].isin(["M", "N"]), "side"] = inverted.loc[inverted["capacity"].isin(["M", "N"]), "side"].map({"B": "S", "S": "B"})
    inv_valid = validate_tbt(inverted)
    inv_joined, _ = join_tbt_grk(inv_valid, validated_grk)
    inv_positions, _ = reconstruct_omm_positions(inv_joined)
    inv_exp, _ = aggregate_exposure(inv_positions, underlier_fixture())
    check("negative_gamma_is_amplification_context_only", lambda: None if inv_exp.iloc[0]["hedge_regime"] == "AMPLIFICATION_CONTEXT" and inv_exp.iloc[0]["standalone_direction"] == "WITHHELD" else (_ for _ in ()).throw(AssertionError(inv_exp.iloc[0].to_dict())))

    quotes = validate_option_quotes(quote_fixture())
    check("complete_quote_surface_schema", lambda: None if len(quotes) == 4 and quotes["formatted_symbol"].nunique() == 2 else (_ for _ in ()).throw(AssertionError()))
    missing_oi = quote_fixture().drop(columns=["open_interest"])
    check("reject_surface_without_open_interest", lambda: must_raise(lambda: validate_option_quotes(missing_oi), "open_interest"))
    negative_oi = quote_fixture(); negative_oi.loc[0, "open_interest"] = -1
    check("reject_negative_open_interest", lambda: must_raise(lambda: validate_option_quotes(negative_oi), "open_interest"))
    crossed_quotes = quote_fixture(); crossed_quotes.loc[0, "ask"] = 12.0
    check("reject_crossed_surface_quote", lambda: must_raise(lambda: validate_option_quotes(crossed_quotes), "crossed"))
    duplicate_quotes = pd.concat([quote_fixture(), quote_fixture().iloc[[0]]], ignore_index=True)
    check("reject_duplicate_surface_mark", lambda: must_raise(lambda: validate_option_quotes(duplicate_quotes), "duplicate"))
    position_only, position_only_diag = reconstruct_positions_from_tbt(validated)
    surface, surface_diag = aggregate_quote_surface_exposure(position_only, quote_fixture(), underlier_fixture())
    check("open_interest_unsigned_baseline_present", lambda: None if surface["unsigned_gamma_magnitude"].gt(0).all() and surface["gross_oi_topology"].between(0, 1).all() else (_ for _ in ()).throw(AssertionError(surface.to_dict("records"))))
    check("full_surface_marks_all_active_series", lambda: None if surface_diag["marked_series"] == 2 and surface["marked_series"].eq(2).all() else (_ for _ in ()).throw(AssertionError(surface_diag)))
    check("untraded_zero_position_series_does_not_create_gamma", lambda: None if surface.iloc[0]["signed_omm_gamma"] > 0 and surface_diag["surface_source"] == "ONE_MINUTE_OPTION_QUOTES_WITH_CALCS_AND_OPEN_INTEREST" else (_ for _ in ()).throw(AssertionError(surface.iloc[0].to_dict())))
    check("trade_grk_never_substitutes_surface", lambda: None if surface_diag["trade_level_grk_used_as_surface"] is False else (_ for _ in ()).throw(AssertionError(surface_diag)))
    check("full_surface_has_no_direction_or_capital", lambda: None if surface["standalone_direction"].eq("WITHHELD").all() and surface["capital_permission"].eq("BLOCKED").all() else (_ for _ in ()).throw(AssertionError()))

    with tempfile.TemporaryDirectory(prefix="v72_manifest_") as td:
        root = Path(td)
        files = []
        for product in ("TBT", "QUOTES", "UNDERLIER"):
            p = root / f"{product}.csv"
            p.write_text(f"{product}\n", encoding="utf-8")
            files.append({"path": p.name, "product": product, "trading_dt": "2020-07-02", "bytes": p.stat().st_size, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        manifest = {"files": files}
        manifest_result = validate_source_manifest(manifest, base_dir=root, expected_dates=[date(2020, 7, 2)])
        check("source_manifest_hash_and_calendar", lambda: None if manifest_result["status"] == "PASS" else (_ for _ in ()).throw(AssertionError(manifest_result)))
        missing = deepcopy(manifest); missing["files"] = missing["files"][:-1]
        check("reject_incomplete_product_calendar", lambda: must_raise(lambda: validate_source_manifest(missing, base_dir=root, expected_dates=[date(2020, 7, 2)]), "UNDERLIER missing"))
        unsafe = deepcopy(manifest); unsafe["files"][0]["path"] = "../escape.csv"
        check("reject_manifest_path_traversal", lambda: must_raise(lambda: validate_source_manifest(unsafe, base_dir=root), "unsafe"))
        tampered = deepcopy(manifest); tampered["files"][0]["sha256"] = "0" * 64
        check("reject_manifest_hash_tamper", lambda: must_raise(lambda: validate_source_manifest(tampered, base_dir=root), "hash mismatch"))

    status = research_status(licensed_data_present=False, historical_outcomes_evaluated=False)
    check("missing_licensed_data_is_explicit", lambda: None if status["status"] == "DATA_LICENSE_REQUIRED" else (_ for _ in ()).throw(AssertionError(status)))
    check("research_status_never_authorizes_capital", lambda: None if status["capital_permission"] == "BLOCKED" and status["live_decision_weight"] == 0.0 and status["predictive_components_promoted"] == 0 else (_ for _ in ()).throw(AssertionError(status)))
    check("prospective_zero_not_matured", lambda: None if status["prospective_profitability"] == "NOT_MATURED" else (_ for _ in ()).throw(AssertionError(status)))

    failures = [x for x in checks if x["status"] != "PASS"]
    report = {
        "schema": "warroom.v72_signed_dealer_validation",
        "status": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "failures": failures,
        "tbt_rows": len(validated),
        "grk_match_rate": join_diag["match_rate"],
        "position_known_answer_final_contracts": final_mm,
        "historical_edge": "NOT_EVALUATED_LICENSED_DATA_REQUIRED",
        "prospective_observations": 0,
        "predictive_components_promoted": 0,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    REPORT.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
