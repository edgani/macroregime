"""warroom/market_contracts.py — five independent market contracts (R6, master prompt §1).

Markets share the OUTPUT SCHEMA only. Raw metrics, weights, thresholds, formulas,
horizons, costs, and proof protocols are market-specific. A metric proven in one
market has weight zero in every other market until separately proven there.

No universal score may combine markets. Cross-market ranking happens only after
each market emits a calibrated lower-confidence-bound opportunity estimate (R10).
"""
from __future__ import annotations

SCHEMA = "warroom.market_contract.v1"

FORBIDDEN_ACTIVATION_INPUTS = [
    "RSI", "MACD", "SMA", "EMA", "VWAP", "chart_pattern", "momentum", "breakout",
]

ACTIVATION_STATES = [
    "RED_NOT_READY", "YELLOW_ARMING", "GREEN_ACTIVATE",
    "GREEN_ACTIVE_HOLD_ADD", "AMBER_LATE_TRIM", "BLACK_INVALIDATED_EXIT",
]

US_STOCKS_CONTRACT = {
    "schema": SCHEMA,
    "market": "us",
    "decision_purpose": "long/short cash equity + options expression of bottleneck, expectation-gap, and margin-convexity theses",
    "universe": {"master": "data/universe/us.json", "size": 13021,
                 "tier_a": "price-fed sleeve", "delisted": "S&P 500 membership history; full-market delisted = LICENSE_REQUIRED (CRSP)"},
    "venue": "NYSE/NASDAQ/Cboe",
    "instruments": ["common stock", "REIT", "listed options (licensed data gated)", "ETF as labelled execution/hedge proxy"],
    "source_country_liquidity": "USD; deepest global liquidity; Fed/FRED macro origin",
    "causal_map": "origin -> demand/supply change -> constrained resource -> transmission -> real value recipient -> expectations gap -> activation -> monetization -> invalidation",
    "bottleneck_archetypes": ["physical_capacity", "qualified_capacity", "production_yield", "lead_time",
                              "inventory_depletion", "order_backlog_growth", "utilization", "supplier_concentration",
                              "customer_concentration", "component_dependency", "power_availability",
                              "memory_storage_capacity", "regulatory_approval", "labor_skills", "options_dealer_capacity"],
    "metrics": {
        "stock": ["capacity", "inventory_days", "backlog", "book_to_bill"],
        "flow": ["order_growth", "estimate_revisions", "institutional_flow"],
        "surprise": ["guidance_vs_consensus", "asp_vs_cost_spread", "inventory_surprise"],
        "state": ["utilization", "qualification_status", "refinancing_wall"],
    },
    "expectations_source": "consensus estimates + guidance (LICENSE_REQUIRED for PIT); SEC EDGAR filings",
    "positioning_source": "options/borrow/institutional (LICENSE_REQUIRED); CFTC n/a",
    "valuation_method": "expectation-gap: implied vs reasonable market cap via low/base/high scenarios on revenue/margin/FCF",
    "target_method": "scenario-weighted implied value; lower-confidence-bound return",
    "activation_inputs": ["backlog_acceleration", "inventory_depletion", "capacity_utilization",
                          "qualification_design_wins", "lead_time_changes", "asp_cost_spread",
                          "signed_contracts", "customer_mix", "guidance_vs_consensus",
                          "estimate_revisions", "capex_response", "regulatory_permit",
                          "institutional_borrow_options_confirmation", "catalyst_proximity"],
    "forbidden_activation_inputs": FORBIDDEN_ACTIVATION_INPUTS,
    "invalidation": "pre-defined per thesis (supply response, demand rollover, qualification loss, estimate reversal)",
    "liquidity_capacity": "ADV-based; small-cap capacity limits explicit",
    "costs": {"commission_bps": 1, "spread_bps_smallcap": 25, "borrow_bps_short": "per-name, licensed", "slippage_model": "sqrt impact"},
    "execution_path": "order review -> manual export; auto-submit OFF",
    "benchmark": "S&P 500 total return",
    "horizon": "1-8 quarters",
    "proof_protocol": "survivor-safe cohort, purged walk-forward, lockbox, PBO/DSR, Recall@K/Precision@K, remaining return, MAE/MFE",
    "claim_limit": "expectation-gap theses require PIT fundamentals (LICENSE_REQUIRED gap); options confirmation requires licensed flow data",
}

IHSG_CONTRACT = {
    "schema": SCHEMA,
    "market": "ihsg",
    "decision_purpose": "long-only alpha on IDX; controller/flow/structure-driven theses",
    "universe": {"master": "data/universe/ihsg.json", "size": 15,
                 "note": "full IDX ~900 issuers = LICENSE_REQUIRED gap; missing data never silently removes a ticker"},
    "venue": "IDX",
    "instruments": ["cash equity (long-only by default; short requires proven borrow)"],
    "source_country_liquidity": "IDR; Indonesia local liquidity; BI policy + commodity terms-of-trade origin",
    "causal_map": "origin -> controller/policy/commodity change -> constrained resource (float, broker inventory, import cost) -> transmission -> value recipient -> expectation gap -> activation -> monetization -> invalidation",
    "bottleneck_archetypes": ["freefloat_controller", "supplier_concentration", "regulatory_approval",
                              "permits", "logistics_freight_storage", "refining_processing", "reserves_intervention_capacity"],
    "metrics": {
        "stock": ["free_float", "controller_stake", "broker_inventory"],
        "flow": ["foreign_flow", "crossing_adjusted_accumulation", "done_detail_volume"],
        "surprise": ["contract_award", "corporate_action", "policy_change"],
        "state": ["import_cost_pressure", "commodity_pass_through", "liquidity_impact"],
    },
    "expectations_source": "issuer disclosures + local research (limited); no liquid consensus PIT source",
    "positioning_source": "broker summary/done-detail/foreign flow (LICENSE_REQUIRED)",
    "valuation_method": "relative value vs local peers + dividend/FCF where disclosed",
    "target_method": "scenario bridge on earnings + re-rating band; conservative due to data limits",
    "activation_inputs": ["controller_action", "free_float_change", "corporate_action",
                          "crossing_adjusted_broker_inventory", "broker_persistence", "foreign_flow",
                          "done_detail_volume", "institutional_vs_retail", "import_cost",
                          "commodity_pass_through", "government_policy", "project_contract_award",
                          "issuer_disclosure", "liquidity_impact"],
    "forbidden_activation_inputs": FORBIDDEN_ACTIVATION_INPUTS,
    "invalidation": "controller distribution, flow reversal, policy reversal, liquidity collapse",
    "liquidity_capacity": "thin; impact cost dominates; capacity per name explicit",
    "costs": {"commission_bps": 15, "spread_bps": 30, "impact_model": "ADV-participation capped"},
    "execution_path": "order review -> manual export; auto-submit OFF",
    "benchmark": "JCI (Jakarta Composite Index)",
    "horizon": "1-6 quarters",
    "proof_protocol": "full-universe cohort (LICENSE_REQUIRED), purged walk-forward, lockbox; long-only metrics",
    "claim_limit": "flow-based activation unproven until licensed broker-summary data admitted; long-only constraint binding",
}

CRYPTO_CONTRACT = {
    "schema": SCHEMA,
    "market": "crypto",
    "decision_purpose": "spot long/short + venue-exact derivatives where data exists; value-capture theses only",
    "universe": {"master": "data/universe/crypto.json", "size": 103,
                 "note": "top-100 CoinGecko discovery; venue-exact listings require venue APIs (gap)"},
    "venue": "venue-specific (Coinbase spot via yahoo; perps/options = LICENSE_REQUIRED venue APIs)",
    "instruments": ["spot", "perpetual (venue-gated)", "futures (venue-gated)", "options (Deribit-gated)"],
    "source_country_liquidity": "global 24/7; USD/USDT/USDC quote; stablecoin liquidity origin",
    "causal_map": "origin -> protocol usage/supply change -> constrained resource (block space, token-required access) -> transmission -> value recipient (fee burn/stakers) -> expectation gap -> activation -> monetization -> invalidation",
    "bottleneck_archetypes": ["protocol_resource_capacity", "token_required_access", "regulatory_approval"],
    "metrics": {
        "stock": ["exchange_reserves", "locked_supply", "treasury_balances"],
        "flow": ["fee_revenue", "stablecoin_liquidity", "venue_flows"],
        "surprise": ["unlock_schedule", "governance_milestone", "upgrade"],
        "state": ["funding_basis_oi", "liquidation_crowding", "adoption_vs_valuation"],
    },
    "expectations_source": "no consensus; adoption-vs-valuation gap via on-chain usage (LICENSE_REQUIRED analytics)",
    "positioning_source": "venue funding/basis/OI/liquidations (LICENSE_REQUIRED venue APIs)",
    "valuation_method": "value-capture: fees x capture rate vs market cap; default skeptical (most tokens fail capture test)",
    "target_method": "scenario on fee growth x capture multiple; wide intervals",
    "activation_inputs": ["protocol_activity", "fee_revenue", "token_required_usage",
                          "stablecoin_liquidity", "unlock_emission_schedule", "treasury_entity_flow",
                          "exchange_reserves", "venue_funding_basis_oi", "liquidations",
                          "governance_upgrade_milestone", "protocol_resource_bottleneck",
                          "adoption_vs_valuation_gap"],
    "forbidden_activation_inputs": FORBIDDEN_ACTIVATION_INPUTS,
    "invalidation": "usage decouples from token, unlock flood, venue/counterparty failure, regulatory action",
    "liquidity_capacity": "venue-depth specific; counterparty/custody risk explicit",
    "costs": {"taker_bps": 10, "funding_8h_bps": "venue-specific", "withdrawal": "per-chain"},
    "execution_path": "order review -> manual export; auto-submit OFF",
    "benchmark": "BTC + ETH equal weight",
    "horizon": "1-4 quarters",
    "proof_protocol": "venue-specific cohorts, purged walk-forward, lockbox; wash-filtered on-chain data only",
    "claim_limit": "value-capture claims UNAVAILABLE until on-chain analytics admitted; positioning claims gated on venue APIs",
}

COMMODITIES_CONTRACT = {
    "schema": SCHEMA,
    "market": "commodities",
    "decision_purpose": "exact-contract long/short on stock-flow and physical-bottleneck theses; WTI/Gold/Copper initial scope",
    "universe": {"master": "data/universe/commodities.json", "size": 11,
                 "exact_contracts": ["CL (NYMEX WTI)", "GC (COMEX Gold)", "HG (COMEX Copper)"],
                 "note": "ETF proxies labelled; exact continuous series = LICENSE_REQUIRED"},
    "venue": "NYMEX/COMEX",
    "instruments": ["futures (exact month, multiplier, delivery registered)", "labelled ETF proxies"],
    "source_country_liquidity": "USD; global physical + financial liquidity; EIA/USDA/LME physical origin",
    "causal_map": "origin -> physical balance change -> constrained resource (spare capacity, processing, freight, grade/location) -> transmission -> value recipient -> expectation gap -> activation -> monetization -> invalidation",
    "bottleneck_archetypes": ["physical_capacity", "inventory_depletion", "utilization", "lead_time",
                              "logistics_freight_storage", "grade_location_basis", "refining_processing",
                              "permits", "power_availability"],
    "metrics": {
        "stock": ["inventories", "spare_capacity", "storage_utilization"],
        "flow": ["production_response", "imports_exports", "hedging_flows"],
        "surprise": ["inventory_surprise", "weather_geopolitical_shock"],
        "state": ["curve_structure", "basis", "cftc_positioning"],
    },
    "expectations_source": "EIA/USDA consensus surveys (release-lagged); curve-implied expectations",
    "positioning_source": "CFTC COT (public, release-lagged); options (licensed)",
    "valuation_method": "stock-flow balance vs curve-implied price; cost-curve anchoring",
    "target_method": "balance-deficit bridge to price via historical elasticity; curve-adjusted",
    "activation_inputs": ["inventory_surprise", "stock_flow_balance", "spare_capacity",
                          "grade_location_basis", "freight", "storage", "processing_refinery",
                          "weather_geopolitical", "production_response", "futures_curve",
                          "producer_consumer_hedging", "cftc_positioning", "contract_expiry_liquidity"],
    "forbidden_activation_inputs": FORBIDDEN_ACTIVATION_INPUTS,
    "invalidation": "inventory rebuild, demand destruction, spare-capacity return, curve normalization",
    "liquidity_capacity": "contract-month specific; roll/expiry handling explicit",
    "costs": {"commission_per_contract": 2.5, "roll_cost": "curve-dependent", "slippage": "depth-based"},
    "execution_path": "order review -> manual export; auto-submit OFF",
    "benchmark": "BCOM total return",
    "horizon": "1-4 quarters",
    "proof_protocol": "exact-contract backtests with roll rules, purged walk-forward, lockbox",
    "claim_limit": "physical-balance activation UNAVAILABLE until EIA/USDA/LME PIT feeds admitted; curve signals gated on exact-contract history",
}

FX_CONTRACT = {
    "schema": SCHEMA,
    "market": "fx",
    "decision_purpose": "pair-specific long/short on relative macro, policy, BOP, carry, and funding theses",
    "universe": {"master": "data/universe/fx.json", "size": 6,
                 "pairs": ["EURUSD", "USDJPY", "GBPUSD", "AUDUSD", "USDIDR", "DXY"],
                 "note": "forwards/options/TFF = LICENSE_REQUIRED"},
    "venue": "OTC spot (ecn-composite via yahoo); CME futures where relevant",
    "instruments": ["spot pairs", "NDF region (USDIDR)", "index (DXY)", "futures/options (licensed-gated)"],
    "source_country_liquidity": "USD-centric; pair-specific two-country macro origin",
    "causal_map": "origin -> relative macro/policy change -> constrained resource (reserves, funding, basis) -> transmission -> value recipient -> expectation gap -> activation -> monetization -> invalidation",
    "bottleneck_archetypes": ["reserves_intervention_capacity", "collateral_capacity", "financing_access"],
    "metrics": {
        "stock": ["reserves_months", "external_debt", "net_international_position"],
        "flow": ["current_account", "capital_flows", "intervention_pace"],
        "surprise": ["policy_surprise", "inflation_surprise", "growth_surprise"],
        "state": ["carry", "cross_currency_basis", "crowding_tff", "funding_stress"],
    },
    "expectations_source": "policy-path pricing (OIS/forward, licensed); survey consensus",
    "positioning_source": "CFTC TFF/COT (public, lagged); FX options (licensed)",
    "valuation_method": "relative macro + policy differential + BOP sustainability; carry-adjusted",
    "target_method": "policy-path bridge + carry-adjusted expected spot; intervention-risk scenarios",
    "activation_inputs": ["relative_growth_inflation", "policy_differential", "expected_policy_path",
                          "bop_current_account", "reserves", "intervention", "fiscal_credibility",
                          "dollar_liquidity", "cross_currency_basis", "carry", "cftc_tff_cot",
                          "options", "funding_stress", "external_vulnerability"],
    "forbidden_activation_inputs": FORBIDDEN_ACTIVATION_INPUTS,
    "invalidation": "policy path reversal, reserve stabilization, intervention, terms-of-trade shock",
    "liquidity_capacity": "majors deep; EM (IDR) limited hours + NDF basis",
    "costs": {"spread_bps_major": 1, "spread_bps_em": 10, "carry_cost": "rate differential", "ndf_basis": "pair-specific"},
    "execution_path": "order review -> manual export; auto-submit OFF",
    "benchmark": "cash (USD short-duration)",
    "horizon": "1-4 quarters",
    "proof_protocol": "pair-specific cohorts, carry-inclusive returns, purged walk-forward, lockbox",
    "claim_limit": "crowding/options activation gated on TFF/options data; policy-path pricing gated on OIS feed",
}

CONTRACTS = {
    "us": US_STOCKS_CONTRACT,
    "ihsg": IHSG_CONTRACT,
    "crypto": CRYPTO_CONTRACT,
    "commodities": COMMODITIES_CONTRACT,
    "fx": FX_CONTRACT,
}

REQUIRED_FIELDS = ["schema", "market", "decision_purpose", "universe", "venue", "instruments",
                   "source_country_liquidity", "causal_map", "bottleneck_archetypes", "metrics",
                   "expectations_source", "positioning_source", "valuation_method", "target_method",
                   "activation_inputs", "forbidden_activation_inputs", "invalidation",
                   "liquidity_capacity", "costs", "execution_path", "benchmark", "horizon",
                   "proof_protocol", "claim_limit"]


def validate() -> list:
    """Contract completeness + separation checks. Returns error list."""
    errors = []
    for name, c in CONTRACTS.items():
        for f in REQUIRED_FIELDS:
            if f not in c:
                errors.append(f"{name}: missing field {f}")
        if c.get("schema") != SCHEMA:
            errors.append(f"{name}: bad schema")
        for banned in FORBIDDEN_ACTIVATION_INPUTS:
            tokens = set()
            for inp in c.get("activation_inputs", []):
                tokens.update(inp.lower().split("_"))
            if banned.lower() in tokens:
                errors.append(f"{name}: forbidden activation input token {banned}")
        for group in ("stock", "flow", "surprise", "state"):
            if group not in c.get("metrics", {}):
                errors.append(f"{name}: metrics missing {group} group")
    # separation: activation input sets must differ across markets
    sets = {n: set(c["activation_inputs"]) for n, c in CONTRACTS.items()}
    names = list(sets)
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if sets[names[i]] == sets[names[j]]:
                errors.append(f"{names[i]} and {names[j]} share identical activation inputs")
    return errors
