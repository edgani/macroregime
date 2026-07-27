"""War Room OS V7.9 exact-scope final trading core.

The system is a monthly long/cash policy for a dedicated broad-US-equity strategy sleeve.
It does not select stocks, short, use leverage, set price targets, or trade other markets.
The predictive claim is deliberately narrow: historically robust left-tail/drawdown reduction,
not guaranteed future profit or advance crash prediction.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Iterable, Mapping
import hashlib
import json
import math

from us_equity_risk_cap_v66 import evaluate_monthly_risk_cap

SYSTEM_ID = "US_BROAD_EQUITY_SMA10_LONG_CASH_V79"
PROOF_COMPONENT_ID = "US_SMA10_MONTHLY_RISK_CAP"
ALLOWED_EQUITY_INSTRUMENTS = ("SPY", "VOO", "IVV")
ALLOWED_DEFENSIVE_INSTRUMENTS = ("CASH",)


@dataclass(frozen=True)
class CoreConfig:
    equity_instrument: str = "SPY"
    defensive_instrument: str = "CASH"
    sleeve_fraction_of_account: float = 1.0
    baseline_authorized: bool = False
    maximum_one_way_cost_bps: float = 25.0
    max_staleness_months: int = 1


@dataclass(frozen=True)
class TradeInstruction:
    system_id: str
    status: str
    ready_to_execute: bool
    observed_month: str | None
    signal: str
    equity_instrument: str
    defensive_instrument: str
    target_equity_weight_in_sleeve: float
    target_defensive_weight_in_sleeve: float
    target_equity_weight_of_account: float
    target_defensive_weight_of_account: float
    action: str
    execution_window: str
    maximum_one_way_cost_bps: float
    close: float | None
    sma10: float | None
    data_freshness_months: int | None
    proof_component_id: str
    proof_scope: str
    ticker_selection_permission: bool
    short_permission: bool
    leverage_permission: bool
    intramonth_override_permission: bool
    target_price_permission: bool
    stop_price_permission: bool
    input_sha256: str | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _blocked(config: CoreConfig, status: str, reason: str) -> TradeInstruction:
    return TradeInstruction(
        system_id=SYSTEM_ID,
        status=status,
        ready_to_execute=False,
        observed_month=None,
        signal="NO_TRADE",
        equity_instrument=config.equity_instrument,
        defensive_instrument=config.defensive_instrument,
        target_equity_weight_in_sleeve=0.0,
        target_defensive_weight_in_sleeve=1.0,
        target_equity_weight_of_account=0.0,
        target_defensive_weight_of_account=config.sleeve_fraction_of_account,
        action="NO_ORDER",
        execution_window="Wait for a valid completed-month signal and all execution guards.",
        maximum_one_way_cost_bps=config.maximum_one_way_cost_bps,
        close=None,
        sma10=None,
        data_freshness_months=None,
        proof_component_id=PROOF_COMPONENT_ID,
        proof_scope="HISTORICALLY_CONFIRMED_MONTHLY_US_BROAD_EQUITY_LEFT_TAIL_REDUCTION",
        ticker_selection_permission=False,
        short_permission=False,
        leverage_permission=False,
        intramonth_override_permission=False,
        target_price_permission=False,
        stop_price_permission=False,
        input_sha256=None,
        reason=reason,
    )


def _validate_config(config: CoreConfig) -> str | None:
    if config.equity_instrument.upper() not in ALLOWED_EQUITY_INSTRUMENTS:
        return f"equity instrument must be one of {ALLOWED_EQUITY_INSTRUMENTS}"
    if config.defensive_instrument.upper() not in ALLOWED_DEFENSIVE_INSTRUMENTS:
        return "defensive instrument must be CASH; bond-duration substitutions are not in proof scope"
    if not math.isfinite(config.sleeve_fraction_of_account) or not (0 < config.sleeve_fraction_of_account <= 1):
        return "sleeve_fraction_of_account must be in (0, 1]"
    if not math.isfinite(config.maximum_one_way_cost_bps) or not (0 <= config.maximum_one_way_cost_bps <= 25):
        return "maximum_one_way_cost_bps must be between 0 and the tested 25 bps stress ceiling"
    if config.max_staleness_months not in (0, 1):
        return "max_staleness_months must be 0 or 1"
    return None


def build_trade_instruction(
    observations: Iterable[Mapping[str, Any]],
    *,
    config: CoreConfig,
    as_of: str | date | datetime | None = None,
    current_equity_weight_in_sleeve: float | None = None,
    estimated_one_way_cost_bps: float | None = None,
    verified_live_feed: bool = False,
) -> TradeInstruction:
    """Convert a valid completed-month signal into one exact-scope manual instruction.

    ``baseline_authorized`` is an explicit user policy choice to dedicate a sleeve to this
    strategy. Without that authorization, the risk control cannot create equity exposure.
    """
    error = _validate_config(config)
    if error:
        return _blocked(config, "CONFIGURATION_BLOCKED", error)
    if not verified_live_feed:
        return _blocked(
            config,
            "DATA_SOURCE_UNVERIFIED",
            "An executable instruction requires a dual-source-confirmed live completed-month feed; manual or bundled observations are audit-only.",
        )
    if not config.baseline_authorized:
        return _blocked(
            config,
            "BASELINE_AUTHORIZATION_REQUIRED",
            "The proven component may manage only a strategy sleeve that the user has explicitly authorized; it cannot allocate the account by itself.",
        )
    if estimated_one_way_cost_bps is not None:
        if not math.isfinite(float(estimated_one_way_cost_bps)) or float(estimated_one_way_cost_bps) < 0:
            return _blocked(config, "COST_INPUT_INVALID", "estimated execution cost is invalid")
        if float(estimated_one_way_cost_bps) > config.maximum_one_way_cost_bps:
            return _blocked(
                config,
                "COST_GUARD_BLOCKED",
                f"estimated one-way execution cost {estimated_one_way_cost_bps:.2f} bps exceeds the {config.maximum_one_way_cost_bps:.2f} bps tested ceiling",
            )
    risk = evaluate_monthly_risk_cap(
        observations,
        as_of=as_of,
        max_staleness_months=config.max_staleness_months,
    )
    if risk.status == "NO_PERMISSION_FAIL_CLOSED":
        blocked = _blocked(config, "DATA_FAIL_CLOSED", risk.reason)
        payload = blocked.to_dict()
        payload["data_freshness_months"] = risk.data_freshness_months
        return TradeInstruction(**payload)

    target_equity = float(risk.max_broad_us_equity_multiplier)
    target_defensive = 1.0 - target_equity
    current = None if current_equity_weight_in_sleeve is None else max(0.0, min(1.0, float(current_equity_weight_in_sleeve)))
    if target_equity == 1.0:
        signal = "EQUITY"
        if current is None:
            action = f"SET {config.equity_instrument.upper()} TO 100% OF THE AUTHORIZED SLEEVE"
        elif current >= 0.995:
            action = "HOLD_EQUITY"
        else:
            action = f"BUY {config.equity_instrument.upper()} TO 100% OF THE AUTHORIZED SLEEVE"
    else:
        signal = "CASH"
        if current is None:
            action = "SET THE AUTHORIZED SLEEVE TO CASH"
        elif current <= 0.005:
            action = "HOLD_CASH"
        else:
            action = f"SELL {config.equity_instrument.upper()} AND MOVE THE AUTHORIZED SLEEVE TO CASH"

    canonical = {
        "risk": risk.to_dict(),
        "config": asdict(config),
        "current_equity_weight_in_sleeve": current,
        "estimated_one_way_cost_bps": estimated_one_way_cost_bps,
        "verified_live_feed": verified_live_feed,
    }
    instruction_hash = hashlib.sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return TradeInstruction(
        system_id=SYSTEM_ID,
        status="READY_EXACT_SCOPE",
        ready_to_execute=True,
        observed_month=risk.observed_month,
        signal=signal,
        equity_instrument=config.equity_instrument.upper(),
        defensive_instrument="CASH",
        target_equity_weight_in_sleeve=target_equity,
        target_defensive_weight_in_sleeve=target_defensive,
        target_equity_weight_of_account=target_equity * config.sleeve_fraction_of_account,
        target_defensive_weight_of_account=target_defensive * config.sleeve_fraction_of_account,
        action=action,
        execution_window="Execute once during the first regular US market session after the completed month; do not react intramonth.",
        maximum_one_way_cost_bps=config.maximum_one_way_cost_bps,
        close=risk.close,
        sma10=risk.sma10,
        data_freshness_months=risk.data_freshness_months,
        proof_component_id=PROOF_COMPONENT_ID,
        proof_scope="HISTORICALLY_CONFIRMED_MONTHLY_US_BROAD_EQUITY_LEFT_TAIL_REDUCTION",
        ticker_selection_permission=False,
        short_permission=False,
        leverage_permission=False,
        intramonth_override_permission=False,
        target_price_permission=False,
        stop_price_permission=False,
        input_sha256=instruction_hash,
        reason=(
            "Completed monthly close is at/above SMA10, so the authorized sleeve participates in broad US equity."
            if signal == "EQUITY"
            else "Completed monthly close is below SMA10, so the authorized sleeve stays in cash until a later completed-month signal."
        ),
    )


__all__ = [
    "SYSTEM_ID",
    "CoreConfig",
    "TradeInstruction",
    "build_trade_instruction",
    "ALLOWED_EQUITY_INSTRUMENTS",
]
