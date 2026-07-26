"""Cross-market position lifecycle diagnostics.

This module classifies *observable state*, not investor identity and not future return.
It intentionally keeps missing inputs as missing. Price/volume/open-interest geometry alone
is labelled ambiguous; a directional build requires signed participant-position changes.

Every output is research context only until a market/horizon-specific prospective protocol
promotes the exact implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any, Iterable, Mapping


VERSION = "V59_POSITION_LIFECYCLE_1"
LIVE_DECISION_WEIGHT = 0.0
CAPITAL_PERMISSION = "BLOCKED"


def _num(value: Any) -> float | None:
    try:
        if value is None or isinstance(value, bool):
            return None
        out = float(value)
        return out if isfinite(out) else None
    except (TypeError, ValueError):
        return None


def _first(obs: Mapping[str, Any], names: Iterable[str]) -> float | None:
    for name in names:
        value = _num(obs.get(name))
        if value is not None:
            return value
    return None


def _truth(obs: Mapping[str, Any], names: Iterable[str]) -> bool | None:
    for name in names:
        if name in obs and obs.get(name) is not None:
            value = obs.get(name)
            if isinstance(value, str):
                s = value.strip().lower()
                if s in {"true", "yes", "1", "tightening", "strong", "positive"}:
                    return True
                if s in {"false", "no", "0", "weakening", "negative"}:
                    return False
            return bool(value)
    return None


def _significant(value: float | None, threshold: float) -> bool:
    return value is not None and abs(value) >= threshold


def _state_confidence(required: list[str], observed: Mapping[str, Any]) -> tuple[str, list[str]]:
    missing = [name for name in required if observed.get(name) is None]
    if not required:
        return "LOW", missing
    completeness = 1.0 - len(missing) / len(required)
    if completeness >= 0.8:
        return "HIGH", missing
    if completeness >= 0.5:
        return "MEDIUM", missing
    return "LOW", missing


_MARKET_CONTRACTS: dict[str, dict[str, Any]] = {
    "commodity": {
        "signed": ["participant_long_change", "participant_short_change"],
        "physical": ["curve_change", "physical_basis_change", "inventory_surprise"],
        "notes": "Use disaggregated COT/TFF participant changes plus curve, inventory and physical basis. Weekly COT cannot be an intraday trigger.",
    },
    "fx": {
        "signed": ["participant_long_change", "participant_short_change"],
        "physical": ["rate_path_surprise", "cross_currency_basis_change", "risk_reversal_change"],
        "notes": "Use TFF participant buckets, policy-path surprise, funding basis and options skew. Spot plus OI alone remains ambiguous.",
    },
    "crypto": {
        "signed": ["aggressor_flow", "liquidation_imbalance"],
        "physical": ["funding_change", "basis_change", "exchange_netflow"],
        "notes": "Venue price/OI geometry distinguishes build-versus-deleveraging only ambiguously unless aggressor/liquidation data resolve the side.",
    },
    "us": {
        "signed": ["signed_flow", "borrow_demand_change"],
        "physical": ["revision_change", "etf_flow", "next_day_oi_change"],
        "notes": "Volume, ownership level and gross option OI do not identify beneficial owner or intent. Point-in-time revisions and signed/settled flows are required.",
    },
    "idx": {
        "signed": ["broker_net_flow", "foreign_net_flow"],
        "physical": ["broker_inventory_persistence", "free_float_turnover", "crossing_share"],
        "notes": "Broker/foreign flow must be persistent and adjusted for crossings, controller/free-float structure and broker reclassification risk.",
    },
}

_ALIASES = {
    "stock": "us", "stocks": "us", "equity": "us", "equities": "us",
    "ihsg": "idx", "indonesia": "idx", "commodities": "commodity",
    "forex": "fx", "digital_asset": "crypto",
}


def normalize_market(market: str | None) -> str:
    value = str(market or "unknown").strip().lower()
    return _ALIASES.get(value, value)


def _position_state(obs: Mapping[str, Any]) -> tuple[str, list[str], str]:
    """Return position state, evidence list, and claim boundary."""
    p = _first(obs, ["price_change_pct", "price_change", "return_pct"])
    oi = _first(obs, ["open_interest_change_pct", "oi_change_pct", "oi_change"])
    long_chg = _first(obs, ["participant_long_change", "long_change", "managed_money_long_change", "leveraged_long_change"])
    short_chg = _first(obs, ["participant_short_change", "short_change", "managed_money_short_change", "leveraged_short_change"])
    signed = _first(obs, ["signed_flow", "aggressor_flow", "broker_net_flow", "foreign_net_flow"])
    liquidation = _first(obs, ["liquidation_imbalance", "net_liquidations"])

    ev: list[str] = []
    if p is not None:
        ev.append(f"price_change={p:.2f}%")
    if oi is not None:
        ev.append(f"open_interest_change={oi:.2f}%")
    if long_chg is not None:
        ev.append(f"participant_long_change={long_chg:.0f}")
    if short_chg is not None:
        ev.append(f"participant_short_change={short_chg:.0f}")
    if signed is not None:
        ev.append(f"signed_flow={signed:.3g}")

    # Signed participant changes have precedence over price/OI geometry.
    # Opposite-direction changes are resolved by dominance before assigning a pure-build label.
    # This prevents a small long increase from disguising a much larger short-covering impulse.
    if long_chg is not None or short_chg is not None:
        l = long_chg or 0.0
        s = short_chg or 0.0
        scale = max(abs(l), abs(s), 1.0)
        supplied_threshold = _first(obs, ["participant_change_threshold", "position_change_threshold"])
        material = max(1.0, supplied_threshold if supplied_threshold is not None else scale * 0.10)
        l_mat, s_mat = abs(l) >= material, abs(s) >= material

        if l_mat and s_mat and l > 0 and s < 0:
            if abs(s) >= 2.0 * abs(l):
                return "SHORT_COVERING", ev, "Short reduction dominates a smaller long addition; rally is covering-led, not clean new-long accumulation."
            if abs(l) >= 2.0 * abs(s):
                return "LONG_BUILDING", ev, "Long addition dominates a smaller short reduction; not proof of informed intent."
            return "BULLISH_REPOSITIONING", ev, "Material long addition and short covering both observed."
        if l_mat and s_mat and l < 0 and s > 0:
            if abs(l) >= 2.0 * abs(s):
                return "LONG_LIQUIDATION", ev, "Long reduction dominates a smaller short addition; decline is liquidation-led."
            if abs(s) >= 2.0 * abs(l):
                return "SHORT_BUILDING", ev, "Short addition dominates a smaller long reduction; not proof of informed intent."
            return "BEARISH_REPOSITIONING", ev, "Material long liquidation and short addition both observed."
        if l_mat and s_mat and l > 0 and s > 0:
            return "MIXED_RISK_BUILD", ev, "Long and short books both expanded; directional accumulation is not established."
        if l_mat and s_mat and l < 0 and s < 0:
            return "MIXED_DELEVERAGING", ev, "Long and short books both contracted; directional intent is not established."
        if l_mat and l > 0:
            return "LONG_BUILDING", ev, "Observed participant long increase; not proof of informed intent."
        if s_mat and s > 0:
            return "SHORT_BUILDING", ev, "Observed participant short increase; not proof of informed intent."
        if s_mat and s < 0:
            return "SHORT_COVERING", ev, "Observed participant short reduction; rally need not represent new long demand."
        if l_mat and l < 0:
            return "LONG_LIQUIDATION", ev, "Observed participant long reduction; decline need not represent new short demand."
        return "MIXED_PARTICIPANT_CHANGE", ev, "Signed bucket changes are below the disclosed materiality threshold."

    if signed is not None and abs(signed) > 0:
        return ("SIGNED_BUYING" if signed > 0 else "SIGNED_SELLING"), ev, "Signed flow is observed, but persistence and beneficial-owner identity may remain unknown."

    if liquidation is not None and abs(liquidation) > 0:
        if liquidation > 0:
            return "LONG_LIQUIDATION", ev, "Liquidation imbalance indicates forced long reduction."
        return "SHORT_COVERING", ev, "Liquidation imbalance indicates forced short reduction."

    # Price × OI is useful geometry, but does not reveal the initiating side.
    if p is not None and oi is not None:
        if p > 0 and oi > 0:
            return "LONG_BUILD_OR_NEW_RISK", ev, "Ambiguous price/OI geometry; cannot prove long accumulation."
        if p > 0 and oi < 0:
            return "SHORT_COVERING_OR_DELEVERAGING", ev, "Price up with OI down; covering/deleveraging context, not new-long proof."
        if p < 0 and oi > 0:
            return "SHORT_BUILD_OR_NEW_RISK", ev, "Ambiguous price/OI geometry; cannot prove short accumulation."
        if p < 0 and oi < 0:
            return "LONG_LIQUIDATION_OR_DELEVERAGING", ev, "Price down with OI down; liquidation/deleveraging context."
        return "FLAT_OR_MIXED_POSITIONING", ev, "No material price/OI quadrant."

    if p is not None:
        return "PRICE_ONLY_CONTEXT", ev, "No position data; price action cannot identify accumulation or distribution."
    return "NO_POSITION_DATA", ev, "No signed positioning or price/OI geometry."


def classify_position_lifecycle(market: str, observations: Mapping[str, Any] | None) -> dict[str, Any]:
    """Classify position, surge and topping states without creating a trading signal.

    Input values should be changes over an explicitly disclosed horizon. Percent fields are in
    percentage points (e.g. 3.2 means +3.2%). Signed participant changes may be contracts or
    provider-native units, provided long and short changes use the same unit.
    """
    obs = dict(observations or {})
    mkt = normalize_market(market)
    contract = _MARKET_CONTRACTS.get(mkt, {"signed": [], "physical": [], "notes": "No market-specific contract registered."})
    position_state, evidence, boundary = _position_state(obs)

    p = _first(obs, ["price_change_pct", "price_change", "return_pct"])
    accel = _first(obs, ["price_acceleration", "return_acceleration", "breakout_z"])
    volume_z = _first(obs, ["volume_z", "volume_change_z", "turnover_z"])
    curve = _first(obs, ["curve_change", "backwardation_change", "term_structure_tightening"])
    basis = _first(obs, ["physical_basis_change", "basis_change", "cash_premium_change"])
    inventory = _first(obs, ["inventory_surprise", "inventory_change_z"])
    supply = _truth(obs, ["supply_constraint", "logistics_constraint", "physical_tightening"])
    price_surge_flag = _truth(obs, ["price_surge_confirmed", "material_breakout", "surge_event_confirmed"])
    continuation = _first(obs, ["continuation_return_pct", "post_breakout_return_pct"])
    failed_high = _truth(obs, ["failed_high", "failed_breakout", "price_rejection"])
    signed_selling = position_state in {"SIGNED_SELLING", "LONG_LIQUIDATION", "BEARISH_REPOSITIONING", "SHORT_BUILDING"}
    signed_buying = position_state in {"SIGNED_BUYING", "LONG_BUILDING", "BULLISH_REPOSITIONING"}

    physical_votes = 0
    weakening_votes = 0
    for value in (curve, basis):
        if value is not None:
            physical_votes += 1 if value > 0 else 0
            weakening_votes += 1 if value < 0 else 0
    if inventory is not None:
        # Negative inventory surprise/change is tightening; positive is loosening.
        physical_votes += 1 if inventory < 0 else 0
        weakening_votes += 1 if inventory > 0 else 0
    if supply is True:
        physical_votes += 1
    elif supply is False:
        weakening_votes += 1

    price_surge = bool(price_surge_flag is True or (p is not None and p >= 3.0) or (accel is not None and accel >= 1.0))
    participation_surge = signed_buying or (volume_z is not None and volume_z >= 1.5)
    if price_surge and physical_votes >= 1:
        surge_state = "ACTIVE_PHYSICAL_SURGE"
    elif price_surge and participation_surge:
        surge_state = "ACTIVE_POSITIONING_SURGE"
    elif physical_votes >= 2 and (p is None or p < 3.0):
        surge_state = "PRE_SURGE_TIGHTENING"
    elif position_state in {"LONG_BUILDING", "BULLISH_REPOSITIONING", "SIGNED_BUYING"} and (p is None or p < 2.0):
        surge_state = "POSITION_BUILDING_PRE_MOVE"
    elif price_surge:
        surge_state = "PRICE_SURGE_UNATTRIBUTED"
    else:
        surge_state = "NO_CONFIRMED_SURGE"

    # A top is never confirmed from overbought/crowding alone.
    crowd = _first(obs, ["crowding_percentile", "crowding", "rsi"])
    exhaustion_flags: list[str] = []
    if crowd is not None and crowd >= 85:
        exhaustion_flags.append("crowded_or_overbought")
    if failed_high is True:
        exhaustion_flags.append("failed_high")
    if continuation is not None and continuation < 0:
        exhaustion_flags.append("negative_follow_through")
    if weakening_votes >= 1:
        exhaustion_flags.append("fundamental_or_curve_weakening")
    if signed_selling:
        exhaustion_flags.append("signed_distribution_or_bearish_repositioning")

    top_confirmed = bool(
        (failed_high is True or (continuation is not None and continuation < 0))
        and signed_selling
        and weakening_votes >= 1
    )
    if top_confirmed:
        top_state = "DISTRIBUTION_TOP_CONFIRMED"
    elif len(exhaustion_flags) >= 2:
        top_state = "EXHAUSTION_RISK"
    elif exhaustion_flags:
        top_state = "EARLY_TOP_RISK_ONLY"
    else:
        top_state = "NO_TOP_EVIDENCE"

    observed_for_conf = {
        "price_change": p,
        "signed_position": 1 if position_state not in {"NO_POSITION_DATA", "PRICE_ONLY_CONTEXT", "LONG_BUILD_OR_NEW_RISK", "SHORT_BUILD_OR_NEW_RISK", "SHORT_COVERING_OR_DELEVERAGING", "LONG_LIQUIDATION_OR_DELEVERAGING", "FLAT_OR_MIXED_POSITIONING"} else None,
        "physical_or_fundamental": 1 if physical_votes or weakening_votes else None,
        "follow_through": continuation if continuation is not None else (1 if failed_high is not None else None),
    }
    confidence, missing = _state_confidence(["price_change", "signed_position", "physical_or_fundamental", "follow_through"], observed_for_conf)

    try:
        from mechanical_flow_driver import classify_mechanical_driver
        mechanical_driver = classify_mechanical_driver(mkt, obs)
    except Exception as exc:
        mechanical_driver = {"driver_state":"ERROR_FAIL_CLOSED","error":type(exc).__name__,"live_decision_weight":0.0,"capital_permission":"BLOCKED"}

    return {
        "version": VERSION,
        "market": mkt,
        "position_state": position_state,
        "surge_state": surge_state,
        "top_state": top_state,
        "confidence": confidence,
        "evidence": evidence,
        "exhaustion_flags": exhaustion_flags,
        "physical_tightening_votes": physical_votes,
        "weakening_votes": weakening_votes,
        "missing_for_full_lifecycle": missing,
        "claim_boundary": boundary,
        "market_contract": contract,
        "live_decision_weight": LIVE_DECISION_WEIGHT,
        "capital_permission": CAPITAL_PERMISSION,
        "proof_state": "NOT_PROVEN",
        "semantics": "Descriptive lifecycle context only; no calibrated probability, target, or expected-return claim.",
        "mechanical_driver": mechanical_driver,
    }


def classify_many(rows: Mapping[str, Mapping[str, Any]], market_by_ticker: Mapping[str, str] | None = None) -> dict[str, dict[str, Any]]:
    markets = market_by_ticker or {}
    return {str(t): classify_position_lifecycle(markets.get(t, "unknown"), obs) for t, obs in rows.items()}
