from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd

from options_volatility_flow import (
    analyze_options_volatility_flow,
    simulate_delta_hedged_option,
    validate_option_rows,
)
from gcfis.engines.dealer import run_dealer
from live_market_intelligence import summarize_option_chain

NOW = datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc)
NOW_ISO = "2026-07-24T12:00:00Z"
EXPIRY = "2026-08-21"


def row(strike=100.0, typ="call", *, venue="CBOE", bid=2.0, ask=2.2, oi=100.0):
    return {
        "state": "LIVE",
        "provider": "TEST_OFFICIAL",
        "venue": venue,
        "contract": f"XYZ-{EXPIRY}-{strike}-{typ[0].upper()}",
        "underlying": "XYZ",
        "expiration": EXPIRY,
        "strike": strike,
        "option_type": typ,
        "multiplier": 100.0,
        "observed_at": NOW_ISO,
        "bid": bid,
        "ask": ask,
        "underlying_price": 100.0,
        "implied_volatility": 0.25,
        "open_interest": oi,
        "open_interest_observed_at": NOW_ISO,
        "oi_reporting_note": "Prior-cleared OI observed at snapshot time.",
    }


def chain():
    return [row(95, "call"), row(100, "call"), row(105, "call"), row(95, "put"), row(100, "put"), row(105, "put")]


checks = []

def check(name, condition, detail=None):
    checks.append({"check": name, "status": "PASS" if condition else "FAIL", "detail": detail})


# Row-level product and lineage gates.
valid = validate_option_rows(chain(), "us", now=NOW)
check("exact_us_rows_accepted", len(valid.accepted) == 6 and not valid.rejected, valid.as_dict())

bad = chain(); bad[0].pop("contract")
r = validate_option_rows(bad, "us", now=NOW)
check("missing_exact_contract_rejected", any(x["reason"] == "EXACT_CONTRACT_MISSING" for x in r.rejected))

bad = chain(); bad[0]["bid"] = 3; bad[0]["ask"] = 2
r = validate_option_rows(bad, "us", now=NOW)
check("crossed_quote_rejected", any(x["reason"] == "NONCROSSED_QUOTE_MISSING" for x in r.rejected))

bad = chain(); bad[0]["observed_at"] = "2026-07-20T00:00:00Z"
r = validate_option_rows(bad, "us", now=NOW)
check("stale_quote_rejected", any(x["reason"] == "QUOTE_STALE_OR_UNTIMESTAMPED" for x in r.rejected))

r = validate_option_rows(chain(), "idx", now=NOW)
check("ihsg_direct_options_disabled", not r.accepted and len(r.rejected) == 6)

bad = chain();
for x in bad: x["venue"] = ""
r = validate_option_rows(bad, "crypto", now=NOW)
check("crypto_venue_required", not r.accepted and any(x["reason"] == "VENUE_MISSING" for x in r.rejected))

bad = chain()
for x in bad: x["venue"] = "CME"
r = validate_option_rows(bad, "commodity", now=NOW)
check("commodity_exact_futures_contract_required", not r.accepted and any(x["reason"] == "EXACT_FUTURES_CONTRACT_MISSING" for x in r.rejected))

bad = chain()
for x in bad:
    x["venue"] = "CME"; x["product_type"] = "SPOT"; x["underlying"] = "EURUSD"
r = validate_option_rows(bad, "fx", now=NOW)
check("fx_spot_cannot_enable_options", not r.accepted and any(x["reason"] == "FX_SPOT_CANNOT_ENABLE_OPTIONS" for x in r.rejected))

# Public OI can create unsigned magnitude only.
base = analyze_options_volatility_flow(chain(), "us", underlying_prices=[100 + i * 0.1 for i in range(30)], now=NOW)
check("gross_oi_never_signed_inventory", base["mechanical_flow"]["dealer_sign_state"] == "UNKNOWN" and base["mechanical_flow"]["signed_gamma"] is None)
check("standalone_direction_withheld", base["standalone_direction"] == "WITHHELD" and base["live_decision_weight"] == 0.0 and base["capital_permission"] == "BLOCKED")
check("expected_move_from_tradable_mid", abs(base["volatility_pricing"]["expected_move_mid"] - 4.2) < 1e-12, base["volatility_pricing"])
check("rv_iv_gap_is_hypothesis_only", base["volatility_pricing"]["gamma_scalping_edge_state"] == "UNPROVEN_COST_MODEL_REQUIRED")

wide = chain()
for x in wide:
    if x["strike"] == 100:
        x["bid"] = 0.1; x["ask"] = 4.0
wide_out = analyze_options_volatility_flow(wide, "us", now=NOW)
check("wide_spread_withholds_expected_move", wide_out["volatility_pricing"]["expected_move_mid"] is None)

no_oi_stamp = chain()
for x in no_oi_stamp: x.pop("open_interest_observed_at")
no_oi = analyze_options_volatility_flow(no_oi_stamp, "us", now=NOW)
check("untimestamped_oi_excluded", no_oi["mechanical_flow"]["oi_rows_with_fresh_lineage"] == 0 and no_oi["mechanical_flow"]["unsigned_gamma_magnitude"] == 0.0)
check("fresh_oi_included", base["mechanical_flow"]["oi_rows_with_fresh_lineage"] == 6 and base["mechanical_flow"]["unsigned_gamma_magnitude"] > 0)

# A bare sign is forbidden; provenance-complete inventory may enable a mechanical regime.
bare = chain()
for x in bare: x["dealer_sign"] = 1
bare_out = analyze_options_volatility_flow(bare, "us", now=NOW)
check("bare_dealer_sign_rejected", bare_out["mechanical_flow"]["dealer_sign_state"] == "UNKNOWN")

verified = chain()
for x in verified:
    x.update({
        "dealer_sign": 1,
        "dealer_inventory_verified": True,
        "dealer_sign_confidence": 0.95,
        "dealer_sign_source": "AUDITED_POSITION_RECEIPT",
        "inventory_observed_at": NOW_ISO,
    })
verified_out = analyze_options_volatility_flow(verified, "us", liquidity={"adv_notional": 10_000_000}, now=NOW)
check("verified_sign_enables_damping_context", verified_out["mechanical_flow"]["hedge_regime"] == "DAMPING_CONTEXT")
check("liquidity_normalization_requires_verified_sign", base["mechanical_flow"]["liquidity_normalized_impact"] is None)
check("liquidity_normalized_impact_computed", verified_out["mechanical_flow"]["liquidity_normalized_impact"] is not None)

partial = deepcopy(verified); partial[0].pop("dealer_inventory_verified")
partial_out = analyze_options_volatility_flow(partial, "us", now=NOW)
check("partial_sign_provenance_withholds_whole_regime", partial_out["mechanical_flow"]["dealer_sign_state"] == "UNKNOWN")

# Determinism and source immutability.
source = chain(); before = json.dumps(source, sort_keys=True)
a = analyze_options_volatility_flow(source, "us", now=NOW)
b = analyze_options_volatility_flow(source, "us", now=NOW)
a_cmp = dict(a); b_cmp = dict(b)
check("deterministic_content_hash", a["content_sha256"] == b["content_sha256"])
check("input_rows_not_mutated", before == json.dumps(source, sort_keys=True))

# Gamma-scalping diagnostics: path matters, and costs can erase an apparent volatility edge.
osc = simulate_delta_hedged_option([100, 103, 98, 104, 100], strike=100, maturity_days=20, implied_vol=0.20)
flat = simulate_delta_hedged_option([100, 101, 99, 101, 100], strike=100, maturity_days=20, implied_vol=0.20)
flat_costly = simulate_delta_hedged_option([100, 101, 99, 101, 100], strike=100, maturity_days=20, implied_vol=0.20,
                                          stock_spread_bps=50, option_spread_bps=50)
check("same_terminal_price_different_path_pnl", osc["terminal_price"] == flat["terminal_price"] and osc["pnl"] != flat["pnl"])
check("transaction_costs_can_erase_edge", flat_costly["pnl"] < flat["pnl"] < 0)
check("gamma_scalping_diagnostic_never_predictive", not osc["predictive_evidence"] and osc["capital_permission"] == "BLOCKED")

# Existing live summarizer carries the new module without upgrading it into direction.
summary_rows = chain()
summary = summarize_option_chain("XYZ", summary_rows, (), observed_at=NOW_ISO, feed_state="LIVE", venue="CBOE", market="us")
check("live_summary_embeds_v70_module", summary.get("options_volatility_flow", {}).get("schema") == "warroom.options_volatility_flow.v70")
check("live_summary_direction_weight_zero", summary.get("standalone_direction") == "WITHHELD" and summary.get("live_decision_weight") == 0.0)

# GCFIS dealer engine must enforce the same provenance rule.
df = pd.DataFrame({
    "strike": [95, 100, 105], "oi": [100, 100, 100], "iv": [0.25, 0.25, 0.25],
    "type": ["C", "C", "P"], "T": [30/365] * 3,
})
bare_df = df.copy(); bare_df["dealer_sign"] = 1
check("gcfis_bare_sign_rejected", run_dealer(bare_df, 100)["dealer_sign_state"] == "UNKNOWN")
verified_df = bare_df.copy()
verified_df["dealer_inventory_verified"] = True
verified_df["dealer_sign_confidence"] = 0.95
verified_df["dealer_sign_source"] = "AUDITED_POSITION_RECEIPT"
verified_df["inventory_observed_at"] = datetime.now(timezone.utc).isoformat()
check("gcfis_verified_sign_accepted", run_dealer(verified_df, 100)["dealer_sign_state"] == "VERIFIED_PROVENANCE")

failed = [x for x in checks if x["status"] != "PASS"]
report = {
    "schema": "warroom.validation.options_gamma_v70",
    "status": "PASS" if not failed else "FAIL",
    "checks_total": len(checks),
    "checks_passed": len(checks) - len(failed),
    "checks": checks,
    "predictive_components_promoted": 0,
    "live_decision_weight": 0.0,
    "capital_permission": "BLOCKED",
}
print(json.dumps(report, indent=2, default=str))
raise SystemExit(0 if not failed else 1)
