"""War Room OS V8.8 market-specific bottleneck-to-price projection engine.

This module contains no chart-derived predictors.  A current price may be supplied only as the
valuation denominator and execution reference.  All projection drivers must be point-in-time,
nontechnical evidence already available at ``as_of``.

The engine is deliberately transparent: each market has a different value bridge and every target
is returned with a component-level explanation.  It is a research calculator, not capital proof.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping
import hashlib
import json
import math
import re

from warroom.no_technical_policy import validate_feature_names

HEX64 = re.compile(r"^[0-9a-f]{64}$")
MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
EQUITY_MARKETS = {"us", "idx"}
METHODS_BY_MARKET = {
    "us": {"equity_earnings_bridge", "equity_sales_bridge", "equity_fcf_bridge"},
    "idx": {"equity_earnings_bridge", "equity_sales_bridge", "equity_fcf_bridge"},
    "commodity": {"commodity_scarcity_bridge"},
    "fx": {"fx_external_balance_bridge"},
    "crypto": {"crypto_value_capture_bridge"},
}
SCENARIO_NAMES = ("low", "base", "high")
READY_NARRATIVE_STATES = {"REPRICING_READY_RESEARCH_CANDIDATE"}
ALLOWED_DOMAINS = {
    "economics", "fundamentals", "expectations", "liquidity", "credit", "valuation",
    "positioning", "signed_flow", "physical_market", "bottleneck", "causal_transmission",
    "corporate_actions", "market_structure", "supply_chain", "customer_qualification",
    "protocol_value_capture", "controller_free_float", "broker_inventory", "policy",
    "balance_of_payments", "inventory", "capacity", "orders_backlog", "guidance",
    "analyst_estimates", "unit_economics", "customer_concentration", "regulatory",
    "freight", "storage", "reserves", "intervention", "token_supply", "network_usage",
}
COMMON_HASHES = (
    "feature_snapshot_hash", "evidence_lineage_hash", "universe_snapshot_hash",
    "model_hash", "trial_ledger_hash", "narrative_state_hash",
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def _ts(value: Any):
    import pandas as pd
    return pd.to_datetime(value, utc=True, errors="coerce")


def _finite(value: Any, name: str, errors: list[str], *, positive: bool = False, nonnegative: bool = False) -> float | None:
    try:
        x = float(value)
    except (TypeError, ValueError):
        errors.append(f"invalid {name}")
        return None
    if not math.isfinite(x):
        errors.append(f"non-finite {name}")
        return None
    if positive and x <= 0:
        errors.append(f"{name} must be positive")
        return None
    if nonnegative and x < 0:
        errors.append(f"{name} must be nonnegative")
        return None
    return x


def _domains(value: Any) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw = value
    else:
        raw = str(value or "").replace("|", ",").split(",")
    return sorted({str(x).strip().lower() for x in raw if str(x).strip()})


def _require_driver(drivers: Mapping[str, Any], name: str, errors: list[str], **kwargs: Any) -> float | None:
    if name not in drivers:
        errors.append(f"missing driver {name}")
        return None
    return _finite(drivers.get(name), f"driver {name}", errors, **kwargs)


@dataclass(frozen=True)
class ScenarioProjection:
    name: str
    probability: float
    target_price: float
    implied_return: float
    bridge: dict[str, Any]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class ProjectionResult:
    valid: bool
    projection_status: str
    market: str | None
    instrument_id: str | None
    ticker: str | None
    method: str | None
    current_price: float | None
    horizon_days: int | None
    expected_target_price: float | None
    expected_return: float | None
    target_low: float | None
    target_base: float | None
    target_high: float | None
    narrative_state: str | None
    timing_ready: bool
    scenarios: tuple[dict[str, Any], ...]
    capital_permission: str
    errors: tuple[str, ...]
    claim_limit: str
    projection_hash: str


def validate_projection_request(row: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for field in (
        "projection_id", "narrative_id", "market", "instrument_id", "ticker", "as_of",
        "availability_max", "currency", "quote_convention", "method", "bottleneck_claim",
        "beneficiary_value_capture", "projection_reason", "invalidation_rule", "feature_domains",
        "narrative_state",
    ):
        if not str(row.get(field) or "").strip():
            errors.append(f"missing {field}")

    market = str(row.get("market") or "").strip().lower()
    method = str(row.get("method") or "").strip().lower()
    if market not in MARKETS:
        errors.append("unsupported market")
    elif method not in METHODS_BY_MARKET[market]:
        errors.append(f"method {method or 'NONE'} not allowed for {market}")

    as_of = _ts(row.get("as_of"))
    available = _ts(row.get("availability_max"))
    if str(as_of) == "NaT":
        errors.append("invalid as_of")
    if str(available) == "NaT":
        errors.append("invalid availability_max")
    if str(as_of) != "NaT" and str(available) != "NaT" and available > as_of:
        errors.append("future information: availability_max exceeds as_of")

    try:
        horizon_days = int(row.get("horizon_days"))
        if horizon_days <= 0:
            errors.append("horizon_days must be positive")
    except (TypeError, ValueError):
        horizon_days = None
        errors.append("invalid horizon_days")

    current_price = _finite(row.get("current_price"), "current_price", errors, positive=True)
    for field in COMMON_HASHES:
        value = str(row.get(field) or "").lower()
        if not HEX64.fullmatch(value):
            errors.append(f"invalid {field}")

    domains = _domains(row.get("feature_domains"))
    if not domains:
        errors.append("feature_domains empty")
    violations = validate_feature_names(domains)
    if violations:
        errors.append("technical or chart-derived predictor domain prohibited")
    unknown = sorted(set(domains) - ALLOWED_DOMAINS)
    if unknown:
        errors.append("unknown feature domains: " + ",".join(unknown))

    scenarios_raw = row.get("scenarios")
    if not isinstance(scenarios_raw, list) or len(scenarios_raw) != 3:
        errors.append("exactly three scenarios are required: low, base, high")
        scenarios_raw = []
    names: list[str] = []
    probabilities: list[float] = []
    normalized: list[dict[str, Any]] = []
    for i, scenario in enumerate(scenarios_raw):
        if not isinstance(scenario, Mapping):
            errors.append(f"scenario {i} must be an object")
            continue
        name = str(scenario.get("name") or "").strip().lower()
        names.append(name)
        probability = _finite(scenario.get("probability"), f"scenario {name or i} probability", errors, nonnegative=True)
        if probability is not None and probability > 1:
            errors.append(f"scenario {name or i} probability above one")
        probabilities.append(probability if probability is not None else float("nan"))
        drivers = scenario.get("drivers")
        if not isinstance(drivers, Mapping):
            errors.append(f"scenario {name or i} drivers missing")
            drivers = {}
        evidence_ids = scenario.get("evidence_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids or any(not str(x).strip() for x in evidence_ids):
            errors.append(f"scenario {name or i} evidence_ids missing")
        assumptions = scenario.get("assumptions")
        if not isinstance(assumptions, list) or not assumptions:
            errors.append(f"scenario {name or i} assumptions missing")
        normalized.append({"name": name, "probability": probability, "drivers": dict(drivers), "evidence_ids": evidence_ids or [], "assumptions": assumptions or []})

    if len(names) != 3 or set(names) != set(SCENARIO_NAMES):
        errors.append("scenario names must be unique low, base and high")
    if probabilities and all(math.isfinite(x) for x in probabilities) and abs(sum(probabilities) - 1.0) > 1e-8:
        errors.append("scenario probabilities must sum to one")

    return {
        "valid": not errors,
        "errors": sorted(set(errors)),
        "market": market,
        "method": method,
        "horizon_days": horizon_days,
        "current_price": current_price,
        "domains": domains,
        "scenarios": normalized,
        "schema": "warroom.v88.projection_request_validation.v1",
    }


def _equity_bridge(method: str, drivers: Mapping[str, Any], errors: list[str]) -> tuple[float | None, dict[str, Any], list[str]]:
    reasons: list[str] = []
    incremental_revenue = _require_driver(drivers, "bottleneck_incremental_revenue", errors, nonnegative=True)
    baseline_revenue = _require_driver(drivers, "baseline_revenue", errors, nonnegative=True)
    net_debt = _require_driver(drivers, "net_debt", errors)
    non_operating_assets = _require_driver(drivers, "non_operating_assets", errors, nonnegative=True)
    diluted_shares = _require_driver(drivers, "diluted_shares", errors, positive=True)
    if any(x is None for x in (incremental_revenue, baseline_revenue, net_debt, non_operating_assets, diluted_shares)):
        return None, {}, reasons
    total_revenue = baseline_revenue + incremental_revenue
    bridge: dict[str, Any] = {
        "baseline_revenue": baseline_revenue,
        "bottleneck_incremental_revenue": incremental_revenue,
        "total_revenue": total_revenue,
        "net_debt": net_debt,
        "non_operating_assets": non_operating_assets,
        "diluted_shares": diluted_shares,
    }
    reasons.append(f"Bottleneck adds {incremental_revenue:,.2f} of scenario revenue to a {baseline_revenue:,.2f} baseline.")

    if method == "equity_earnings_bridge":
        gross_margin = _require_driver(drivers, "gross_margin", errors, nonnegative=True)
        operating_expense = _require_driver(drivers, "operating_expense", errors, nonnegative=True)
        tax_rate = _require_driver(drivers, "tax_rate", errors, nonnegative=True)
        multiple = _require_driver(drivers, "earnings_multiple", errors, positive=True)
        if any(x is None for x in (gross_margin, operating_expense, tax_rate, multiple)):
            return None, bridge, reasons
        if gross_margin > 1 or tax_rate > 1:
            errors.append("gross_margin and tax_rate must be between zero and one")
            return None, bridge, reasons
        operating_profit = total_revenue * gross_margin - operating_expense
        after_tax_earnings = operating_profit * (1.0 - tax_rate)
        equity_value = after_tax_earnings * multiple + non_operating_assets - net_debt
        bridge.update({
            "gross_margin": gross_margin,
            "operating_expense": operating_expense,
            "operating_profit": operating_profit,
            "tax_rate": tax_rate,
            "after_tax_earnings": after_tax_earnings,
            "earnings_multiple": multiple,
            "equity_value": equity_value,
            "formula": "((baseline revenue + bottleneck revenue) × gross margin − operating expense) × (1 − tax) × earnings multiple + non-operating assets − net debt",
        })
        reasons.append(f"Scenario after-tax earnings are {after_tax_earnings:,.2f}; the frozen valuation multiple is {multiple:.2f}×.")
    elif method == "equity_sales_bridge":
        multiple = _require_driver(drivers, "sales_multiple", errors, positive=True)
        if multiple is None:
            return None, bridge, reasons
        enterprise_value = total_revenue * multiple
        equity_value = enterprise_value + non_operating_assets - net_debt
        bridge.update({
            "sales_multiple": multiple,
            "enterprise_value": enterprise_value,
            "equity_value": equity_value,
            "formula": "(baseline revenue + bottleneck revenue) × sales multiple + non-operating assets − net debt",
        })
        reasons.append(f"Scenario revenue is valued at a frozen {multiple:.2f}× sales multiple.")
    else:  # equity_fcf_bridge
        baseline_fcf = _require_driver(drivers, "baseline_fcf", errors)
        incremental_fcf = _require_driver(drivers, "bottleneck_incremental_fcf", errors)
        multiple = _require_driver(drivers, "fcf_multiple", errors, positive=True)
        if any(x is None for x in (baseline_fcf, incremental_fcf, multiple)):
            return None, bridge, reasons
        total_fcf = baseline_fcf + incremental_fcf
        equity_value = total_fcf * multiple + non_operating_assets - net_debt
        bridge.update({
            "baseline_fcf": baseline_fcf,
            "bottleneck_incremental_fcf": incremental_fcf,
            "total_fcf": total_fcf,
            "fcf_multiple": multiple,
            "equity_value": equity_value,
            "formula": "(baseline FCF + bottleneck incremental FCF) × FCF multiple + non-operating assets − net debt",
        })
        reasons.append(f"Bottleneck value capture changes scenario FCF by {incremental_fcf:,.2f}, valued at {multiple:.2f}×.")
    if equity_value <= 0:
        errors.append("scenario equity value is not positive")
        return None, bridge, reasons
    target = equity_value / diluted_shares
    bridge["target_price"] = target
    reasons.append(f"Equity value divided by {diluted_shares:,.2f} diluted shares produces the scenario price.")
    return target, bridge, reasons


def _commodity_bridge(drivers: Mapping[str, Any], errors: list[str]) -> tuple[float | None, dict[str, Any], list[str]]:
    marginal_cost = _require_driver(drivers, "marginal_supply_cost", errors, positive=True)
    cover = _require_driver(drivers, "inventory_cover_days", errors, positive=True)
    normal_cover = _require_driver(drivers, "normal_inventory_cover_days", errors, positive=True)
    sensitivity = _require_driver(drivers, "scarcity_sensitivity", errors, nonnegative=True)
    quality = _require_driver(drivers, "quality_basis", errors)
    location = _require_driver(drivers, "location_basis", errors)
    freight = _require_driver(drivers, "freight_insurance", errors)
    policy = _require_driver(drivers, "policy_premium", errors)
    if any(x is None for x in (marginal_cost, cover, normal_cover, sensitivity, quality, location, freight, policy)):
        return None, {}, []
    scarcity_gap = max(0.0, (normal_cover - cover) / normal_cover)
    scarcity_rent = marginal_cost * math.expm1(sensitivity * scarcity_gap)
    target = marginal_cost + scarcity_rent + quality + location + freight + policy
    bridge = {
        "marginal_supply_cost": marginal_cost,
        "inventory_cover_days": cover,
        "normal_inventory_cover_days": normal_cover,
        "scarcity_gap": scarcity_gap,
        "scarcity_sensitivity": sensitivity,
        "scarcity_rent": scarcity_rent,
        "quality_basis": quality,
        "location_basis": location,
        "freight_insurance": freight,
        "policy_premium": policy,
        "target_price": target,
        "formula": "marginal supply cost + scarcity rent(inventory cover) + quality/location basis + freight/insurance + policy premium",
    }
    reasons = [
        f"Inventory cover of {cover:.2f} days is compared with a normal {normal_cover:.2f}-day buffer.",
        f"The frozen scarcity sensitivity converts that deficit into a {scarcity_rent:,.2f} scarcity rent.",
        "Quality, location, freight/insurance and policy premia bridge the physical bottleneck to the quoted contract or grade.",
    ]
    if target <= 0:
        errors.append("scenario commodity target is not positive")
        return None, bridge, reasons
    return target, bridge, reasons


def _fx_bridge(drivers: Mapping[str, Any], errors: list[str]) -> tuple[float | None, dict[str, Any], list[str]]:
    anchor = _require_driver(drivers, "fundamental_anchor_rate", errors, positive=True)
    adjustments = drivers.get("log_adjustments")
    required = ("policy_path", "balance_of_payments", "terms_of_trade", "global_liquidity", "funding_stress", "intervention")
    if not isinstance(adjustments, Mapping):
        errors.append("missing driver log_adjustments")
        return None, {}, []
    clean: dict[str, float] = {}
    for name in required:
        value = _finite(adjustments.get(name), f"driver log_adjustments.{name}", errors)
        if value is not None:
            if abs(value) > 2.0:
                errors.append(f"log_adjustments.{name} outside allowed range")
            clean[name] = value
    if anchor is None or len(clean) != len(required):
        return None, {}, []
    total_adjustment = sum(clean.values())
    target = anchor * math.exp(total_adjustment)
    bridge = {
        "fundamental_anchor_rate": anchor,
        "log_adjustments": clean,
        "total_log_adjustment": total_adjustment,
        "target_rate": target,
        "formula": "fundamental anchor × exp(policy + BOP + terms-of-trade + global-liquidity + funding + intervention adjustments)",
    }
    reasons = [
        f"The pair starts from a frozen fundamental anchor of {anchor:,.6f}.",
        "Each macro adjustment is supplied by the separately validated pair-specific model; positive values raise the quoted exchange rate and negative values lower it.",
        f"The combined log adjustment is {total_adjustment:+.4f}, producing the scenario rate.",
    ]
    if target <= 0:
        errors.append("scenario FX target is not positive")
        return None, bridge, reasons
    return target, bridge, reasons


def _crypto_bridge(drivers: Mapping[str, Any], errors: list[str]) -> tuple[float | None, dict[str, Any], list[str]]:
    baseline = _require_driver(drivers, "baseline_annual_value_capture", errors, nonnegative=True)
    incremental = _require_driver(drivers, "bottleneck_incremental_value_capture", errors)
    multiple = _require_driver(drivers, "value_capture_multiple", errors, positive=True)
    treasury = _require_driver(drivers, "treasury_value", errors, nonnegative=True)
    monetary = _require_driver(drivers, "monetary_premium", errors, nonnegative=True)
    liabilities = _require_driver(drivers, "net_liabilities", errors, nonnegative=True)
    supply = _require_driver(drivers, "projected_diluted_token_supply", errors, positive=True)
    if any(x is None for x in (baseline, incremental, multiple, treasury, monetary, liabilities, supply)):
        return None, {}, []
    annual_value_capture = baseline + incremental
    network_value = annual_value_capture * multiple + treasury + monetary - liabilities
    target = network_value / supply
    bridge = {
        "baseline_annual_value_capture": baseline,
        "bottleneck_incremental_value_capture": incremental,
        "annual_value_capture": annual_value_capture,
        "value_capture_multiple": multiple,
        "treasury_value": treasury,
        "monetary_premium": monetary,
        "net_liabilities": liabilities,
        "projected_diluted_token_supply": supply,
        "network_value": network_value,
        "target_price": target,
        "formula": "(annual protocol value capture × multiple + treasury + monetary premium − liabilities) ÷ projected diluted token supply",
    }
    reasons = [
        f"The bottleneck changes annual token-required value capture by {incremental:,.2f}.",
        f"The scenario applies a frozen {multiple:.2f}× value-capture multiple and explicitly includes treasury, liabilities and future dilution.",
        f"Network value is divided by {supply:,.2f} projected diluted tokens, not current circulating supply alone.",
    ]
    if network_value <= 0 or target <= 0:
        errors.append("scenario crypto network value or target is not positive")
        return None, bridge, reasons
    return target, bridge, reasons


def _calculate_scenario(market: str, method: str, scenario: Mapping[str, Any], current_price: float, errors: list[str]) -> ScenarioProjection | None:
    local_errors: list[str] = []
    drivers = scenario["drivers"]
    if market in EQUITY_MARKETS:
        target, bridge, reasons = _equity_bridge(method, drivers, local_errors)
    elif market == "commodity":
        target, bridge, reasons = _commodity_bridge(drivers, local_errors)
    elif market == "fx":
        target, bridge, reasons = _fx_bridge(drivers, local_errors)
    else:
        target, bridge, reasons = _crypto_bridge(drivers, local_errors)
    if local_errors or target is None:
        errors.extend(f"scenario {scenario['name']}: {message}" for message in local_errors)
        return None
    return ScenarioProjection(
        name=str(scenario["name"]),
        probability=float(scenario["probability"]),
        target_price=float(target),
        implied_return=float(target / current_price - 1.0),
        bridge=bridge,
        reasons=tuple(reasons),
    )


def project_payload(row: Mapping[str, Any]) -> dict[str, Any]:
    validation = validate_projection_request(row)
    if not validation["valid"]:
        payload = {
            "valid": False,
            "projection_status": "INVALID_INPUT",
            "errors": validation["errors"],
            "capital_permission": "BLOCKED",
        }
        payload["projection_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
        return asdict(ProjectionResult(
            valid=False, projection_status="INVALID_INPUT", market=validation.get("market") or None,
            instrument_id=str(row.get("instrument_id") or "") or None, ticker=str(row.get("ticker") or "") or None,
            method=validation.get("method") or None, current_price=validation.get("current_price"),
            horizon_days=validation.get("horizon_days"), expected_target_price=None, expected_return=None,
            target_low=None, target_base=None, target_high=None, narrative_state=str(row.get("narrative_state") or "") or None,
            timing_ready=False, scenarios=tuple(), capital_permission="BLOCKED", errors=tuple(validation["errors"]),
            claim_limit="Invalid input; no projection.", projection_hash=payload["projection_hash"],
        )) | {"schema": "warroom.v88.market_projection.v1"}

    errors: list[str] = []
    projections: list[ScenarioProjection] = []
    for scenario in validation["scenarios"]:
        result = _calculate_scenario(validation["market"], validation["method"], scenario, validation["current_price"], errors)
        if result is not None:
            projections.append(result)
    ordered = {item.name: item for item in projections}
    if len(ordered) == 3 and not (ordered["low"].target_price <= ordered["base"].target_price <= ordered["high"].target_price):
        errors.append("calculated targets must be ordered low <= base <= high")
    if errors or len(projections) != 3:
        payload = {"valid": False, "projection_status": "CALCULATION_FAILED", "errors": sorted(set(errors)), "capital_permission": "BLOCKED"}
        payload["projection_hash"] = hashlib.sha256(_canonical(payload)).hexdigest()
        return asdict(ProjectionResult(
            valid=False, projection_status="CALCULATION_FAILED", market=validation["market"],
            instrument_id=str(row.get("instrument_id")), ticker=str(row.get("ticker")), method=validation["method"],
            current_price=validation["current_price"], horizon_days=validation["horizon_days"],
            expected_target_price=None, expected_return=None, target_low=None, target_base=None, target_high=None,
            narrative_state=str(row.get("narrative_state")), timing_ready=False, scenarios=tuple(asdict(x) for x in projections),
            capital_permission="BLOCKED", errors=tuple(sorted(set(errors))), claim_limit="Calculation failed; no projection.",
            projection_hash=payload["projection_hash"],
        )) | {"schema": "warroom.v88.market_projection.v1"}

    expected_target = sum(item.probability * item.target_price for item in projections)
    current_price = validation["current_price"]
    narrative_state = str(row.get("narrative_state"))
    timing_ready = narrative_state in READY_NARRATIVE_STATES
    status = "RESEARCH_PROJECTION_TIMING_READY" if timing_ready else "RESEARCH_PROJECTION_NOT_TIMING_READY"
    payload_for_hash = {
        "projection_id": row["projection_id"], "market": validation["market"], "method": validation["method"],
        "as_of": str(row["as_of"]), "current_price": current_price, "horizon_days": validation["horizon_days"],
        "narrative_state": narrative_state, "scenarios": [asdict(x) for x in projections],
        "expected_target_price": expected_target,
    }
    digest = hashlib.sha256(_canonical(payload_for_hash)).hexdigest()
    result = ProjectionResult(
        valid=True, projection_status=status, market=validation["market"], instrument_id=str(row["instrument_id"]),
        ticker=str(row["ticker"]), method=validation["method"], current_price=current_price,
        horizon_days=validation["horizon_days"], expected_target_price=expected_target,
        expected_return=expected_target / current_price - 1.0,
        target_low=ordered["low"].target_price, target_base=ordered["base"].target_price,
        target_high=ordered["high"].target_price, narrative_state=narrative_state, timing_ready=timing_ready,
        scenarios=tuple(asdict(x) for x in projections), capital_permission="BLOCKED", errors=tuple(),
        claim_limit=(
            "Scenario valuation only. It becomes tradable only after the exact market, universe, horizon and execution method "
            "pass blind point-in-time target calibration, narrative timing, realized profit factor, drawdown, cost/capacity and prospective gates."
        ),
        projection_hash=digest,
    )
    return asdict(result) | {
        "schema": "warroom.v88.market_projection.v1",
        "projection_reason": str(row.get("projection_reason")),
        "bottleneck_claim": str(row.get("bottleneck_claim")),
        "beneficiary_value_capture": str(row.get("beneficiary_value_capture")),
        "invalidation_rule": str(row.get("invalidation_rule")),
        "quote_convention": str(row.get("quote_convention")),
        "currency": str(row.get("currency")),
    }
