from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable, Mapping
import json
import math
import os

from .hashing import canonical_hash
from .storage import GENESIS, append_line, atomic_write, load_jsonl, verify_chain


class TradeDirection(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class PaperTradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class StructuralTemplate:
    asset: str
    timeframe: str
    direction: TradeDirection
    source_snapshot_hash: str
    entry_zone: tuple[float, float]
    invalidation_price: float
    targets: tuple[float, ...]
    template_label: str = "UNVALIDATED_STRUCTURAL_TEMPLATE"
    claim_ceiling: str = "OPERATOR_PLANNING_ONLY"

    def __post_init__(self) -> None:
        _validate_geometry(self.direction, self.entry_zone, self.invalidation_price, self.targets)
        if self.claim_ceiling != "OPERATOR_PLANNING_ONLY":
            raise ValueError("structural template must remain OPERATOR_PLANNING_ONLY")


@dataclass(frozen=True)
class ManualTradePlan:
    plan_id: str
    created_at: str
    asset: str
    timeframe: str
    direction: TradeDirection
    source_snapshot_hash: str
    entry_zone: tuple[float, float]
    invalidation_price: float
    targets: tuple[float, ...]
    account_equity: float
    risk_budget_pct: float
    estimated_roundtrip_cost_bps: float
    max_leverage: float
    quantity: float
    notional: float
    margin_required: float
    cash_risk_budget: float
    estimated_loss_at_invalidation: float
    reward_r_multiples: tuple[float, ...]
    notes: str = ""
    mode: str = "DISCRETIONARY_PAPER_ONLY"
    claim_ceiling: str = "OPERATOR_PLANNING_ONLY"

    def __post_init__(self) -> None:
        _validate_geometry(self.direction, self.entry_zone, self.invalidation_price, self.targets)
        numeric = (
            self.account_equity,
            self.risk_budget_pct,
            self.estimated_roundtrip_cost_bps,
            self.max_leverage,
            self.quantity,
            self.notional,
            self.margin_required,
            self.cash_risk_budget,
            self.estimated_loss_at_invalidation,
            *self.reward_r_multiples,
        )
        if not all(math.isfinite(float(v)) for v in numeric):
            raise ValueError("trade plan contains non-finite numbers")
        if self.account_equity <= 0:
            raise ValueError("account_equity must be positive")
        if not 0 < self.risk_budget_pct <= 2.0:
            raise ValueError("risk_budget_pct must be in (0, 2]")
        if not 0 <= self.estimated_roundtrip_cost_bps <= 500:
            raise ValueError("estimated_roundtrip_cost_bps must be in [0, 500]")
        if not 0 < self.max_leverage <= 5.0:
            raise ValueError("max_leverage must be in (0, 5]")
        if self.quantity <= 0 or self.notional <= 0 or self.margin_required <= 0:
            raise ValueError("quantity, notional, and margin must be positive")
        if self.estimated_loss_at_invalidation > self.cash_risk_budget * 1.000001:
            raise ValueError("estimated loss exceeds cash risk budget")
        if self.mode != "DISCRETIONARY_PAPER_ONLY":
            raise ValueError("only discretionary paper mode is allowed")
        if self.claim_ceiling != "OPERATOR_PLANNING_ONLY":
            raise ValueError("manual plan claim ceiling cannot be promoted")

    @property
    def entry_midpoint(self) -> float:
        return (self.entry_zone[0] + self.entry_zone[1]) / 2.0


@dataclass(frozen=True)
class PaperTradeView:
    trade_id: str
    status: PaperTradeStatus
    plan: Mapping[str, Any]
    opened_at: str
    closed_at: str | None
    exit_price: float | None
    realized_pnl: float | None
    realized_r: float | None
    close_reason: str | None
    event_count: int


def _validate_geometry(
    direction: TradeDirection,
    entry_zone: tuple[float, float],
    invalidation_price: float,
    targets: Iterable[float],
) -> None:
    e0, e1 = (float(entry_zone[0]), float(entry_zone[1]))
    t = tuple(float(v) for v in targets)
    values = (e0, e1, float(invalidation_price), *t)
    if not all(math.isfinite(v) and v > 0 for v in values):
        raise ValueError("execution geometry must contain finite positive prices")
    if e1 < e0:
        raise ValueError("entry zone upper must be >= lower")
    if not t:
        raise ValueError("at least one target is required")
    if direction == TradeDirection.LONG:
        if invalidation_price >= e0:
            raise ValueError("LONG invalidation must be below entry zone")
        if any(v <= e1 for v in t):
            raise ValueError("LONG targets must be above entry zone")
    elif direction == TradeDirection.SHORT:
        if invalidation_price <= e1:
            raise ValueError("SHORT invalidation must be above entry zone")
        if any(v >= e0 for v in t):
            raise ValueError("SHORT targets must be below entry zone")
    else:
        raise ValueError("unsupported direction")


def build_structural_template(
    *,
    asset: str,
    timeframe: str,
    direction: TradeDirection,
    source_snapshot_hash: str,
    mqa_state: Mapping[str, Any],
    entry_half_width_atr: float = 0.05,
) -> StructuralTemplate:
    """Build an unvalidated arithmetic template from descriptive MQA boundaries.

    This function does not infer direction or probability. The operator supplies direction.
    """
    close = float(mqa_state["close"])
    atr = mqa_state.get("atr")
    if atr is None or not math.isfinite(float(atr)) or float(atr) <= 0:
        raise ValueError("ATR_UNAVAILABLE")
    atr = float(atr)
    half = max(atr * float(entry_half_width_atr), close * 0.0001)
    entry = (close - half, close + half)

    lower_candidates = [
        mqa_state.get("fixed_lower"),
        mqa_state.get("conformal_lower"),
        close - 1.5 * atr,
    ]
    upper_candidates = [
        mqa_state.get("fixed_upper"),
        mqa_state.get("conformal_upper"),
        close + 1.5 * atr,
    ]
    lowers = sorted({float(v) for v in lower_candidates if v is not None and math.isfinite(float(v)) and 0 < float(v) < entry[0]})
    uppers = sorted({float(v) for v in upper_candidates if v is not None and math.isfinite(float(v)) and float(v) > entry[1]})

    if direction == TradeDirection.LONG:
        invalidation = max(lowers) if lowers else close - 1.5 * atr
        risk = (entry[0] + entry[1]) / 2.0 - invalidation
        boundary_target = min(uppers) if uppers else close + 1.5 * atr
        targets = tuple(sorted({boundary_target, close + 2.0 * risk}))
    else:
        invalidation = min(uppers) if uppers else close + 1.5 * atr
        risk = invalidation - (entry[0] + entry[1]) / 2.0
        boundary_target = max(lowers) if lowers else close - 1.5 * atr
        targets = tuple(sorted({boundary_target, close - 2.0 * risk}, reverse=True))

    return StructuralTemplate(
        asset=asset.upper(),
        timeframe=timeframe,
        direction=direction,
        source_snapshot_hash=source_snapshot_hash,
        entry_zone=(round(entry[0], 10), round(entry[1], 10)),
        invalidation_price=round(invalidation, 10),
        targets=tuple(round(v, 10) for v in targets if v > 0),
    )


def calculate_manual_trade_plan(
    *,
    asset: str,
    timeframe: str,
    direction: TradeDirection,
    source_snapshot_hash: str,
    entry_zone: tuple[float, float],
    invalidation_price: float,
    targets: tuple[float, ...],
    account_equity: float,
    risk_budget_pct: float,
    estimated_roundtrip_cost_bps: float = 12.0,
    max_leverage: float = 1.0,
    notes: str = "",
    created_at: datetime | None = None,
) -> ManualTradePlan:
    _validate_geometry(direction, entry_zone, invalidation_price, targets)
    created_at = created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None or created_at.utcoffset() is None:
        raise ValueError("created_at must be timezone-aware")
    equity = float(account_equity)
    risk_pct = float(risk_budget_pct)
    costs_bps = float(estimated_roundtrip_cost_bps)
    leverage = float(max_leverage)
    if equity <= 0 or not 0 < risk_pct <= 2.0 or not 0 <= costs_bps <= 500 or not 0 < leverage <= 5.0:
        raise ValueError("invalid risk inputs")

    e0, e1 = map(float, entry_zone)
    entry_mid = (e0 + e1) / 2.0
    stop_distance = abs(entry_mid - float(invalidation_price))
    roundtrip_cost_per_unit = entry_mid * costs_bps / 10_000.0
    risk_per_unit = stop_distance + roundtrip_cost_per_unit
    if risk_per_unit <= 0:
        raise ValueError("risk per unit must be positive")
    cash_budget = equity * risk_pct / 100.0
    qty_by_risk = cash_budget / risk_per_unit
    qty_by_leverage = equity * leverage / entry_mid
    quantity = min(qty_by_risk, qty_by_leverage)
    if quantity <= 0:
        raise ValueError("calculated quantity is zero")
    notional = quantity * entry_mid
    margin = notional / leverage
    estimated_loss = quantity * risk_per_unit
    r_values = []
    for target in targets:
        gross_reward = abs(float(target) - entry_mid)
        net_reward = max(0.0, gross_reward - roundtrip_cost_per_unit)
        r_values.append(net_reward / risk_per_unit)

    identity = {
        "created_at": created_at.astimezone(timezone.utc).isoformat(),
        "asset": asset.upper(),
        "timeframe": timeframe,
        "direction": direction.value,
        "source_snapshot_hash": source_snapshot_hash,
        "entry_zone": [e0, e1],
        "invalidation_price": float(invalidation_price),
        "targets": list(map(float, targets)),
        "risk": [equity, risk_pct, costs_bps, leverage],
        "notes": notes,
    }
    return ManualTradePlan(
        plan_id=canonical_hash(identity),
        created_at=identity["created_at"],
        asset=asset.upper(),
        timeframe=timeframe,
        direction=direction,
        source_snapshot_hash=source_snapshot_hash,
        entry_zone=(e0, e1),
        invalidation_price=float(invalidation_price),
        targets=tuple(map(float, targets)),
        account_equity=equity,
        risk_budget_pct=risk_pct,
        estimated_roundtrip_cost_bps=costs_bps,
        max_leverage=leverage,
        quantity=quantity,
        notional=notional,
        margin_required=margin,
        cash_risk_budget=cash_budget,
        estimated_loss_at_invalidation=estimated_loss,
        reward_r_multiples=tuple(r_values),
        notes=notes.strip(),
    )


def _jsonable_plan(plan: ManualTradePlan) -> dict[str, Any]:
    payload = asdict(plan)
    payload["direction"] = plan.direction.value
    payload["entry_zone"] = list(plan.entry_zone)
    payload["targets"] = list(plan.targets)
    payload["reward_r_multiples"] = list(plan.reward_r_multiples)
    return payload


@contextmanager
def _journal_lock(path: Path):
    lock_path = path.with_suffix(path.suffix + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fh = lock_path.open("a+")
    try:
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        except (ImportError, OSError):
            pass
        yield
    finally:
        try:
            import fcntl
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
        except (ImportError, OSError):
            pass
        fh.close()


def _append_trade_event(root: Path, payload: dict[str, Any]) -> dict[str, Any]:
    journal = root / "runtime/trading/paper_events.jsonl"
    with _journal_lock(journal):
        entries = load_jsonl(journal)
        errors = verify_chain(entries)
        if errors:
            raise ValueError("PAPER_TRADE_JOURNAL_INVALID:" + ",".join(errors))
        trade_id = str(payload["trade_id"])
        existing_scope = [e for e in entries if e.get("scope_id") == trade_id]
        if payload.get("event_type") == "OPEN" and existing_scope:
            first = existing_scope[0]
            if first.get("plan_id") == payload.get("plan_id"):
                return first
            raise ValueError("trade_id already bound to a different plan")
        previous = entries[-1]["entry_hash"] if entries else GENESIS
        scope_previous = next((e["entry_hash"] for e in reversed(entries) if e["scope_id"] == trade_id), GENESIS)
        row = {
            **payload,
            "sequence": len(entries) + 1,
            "scope_id": trade_id,
            "previous_entry_hash": previous,
            "previous_scope_hash": scope_previous,
        }
        row["entry_hash"] = canonical_hash(row)
        append_line(journal, json.dumps(row, sort_keys=True, separators=(",", ":")))
        return row


def open_paper_trade(root: str | Path, *, plan: ManualTradePlan, opened_at: datetime | None = None) -> dict[str, Any]:
    root = Path(root)
    opened_at = opened_at or datetime.now(timezone.utc)
    if opened_at.tzinfo is None or opened_at.utcoffset() is None:
        raise ValueError("opened_at must be timezone-aware")
    plan_payload = _jsonable_plan(plan)
    trade_id = canonical_hash({"plan_id": plan.plan_id, "opened_at": opened_at.astimezone(timezone.utc).isoformat()})
    immutable = {"trade_id": trade_id, "plan": plan_payload, "opened_at": opened_at.astimezone(timezone.utc).isoformat()}
    atomic_write(root / f"runtime/trading/plans/{trade_id}.json", json.dumps(immutable, indent=2, sort_keys=True).encode())
    event = {
        "trade_id": trade_id,
        "event_type": "OPEN",
        "recorded_at": opened_at.astimezone(timezone.utc).isoformat(),
        "plan_id": plan.plan_id,
        "plan_path": f"trading/plans/{trade_id}.json",
        "claim_ceiling": "PAPER_JOURNAL_ONLY",
    }
    return _append_trade_event(root, event)


def close_paper_trade(
    root: str | Path,
    *,
    trade_id: str,
    exit_price: float,
    reason: str,
    closed_at: datetime | None = None,
) -> dict[str, Any]:
    root = Path(root)
    current = {v.trade_id: v for v in list_paper_trades(root)}.get(trade_id)
    if current is None:
        raise KeyError(trade_id)
    if current.status != PaperTradeStatus.OPEN:
        raise ValueError("paper trade is not open")
    price = float(exit_price)
    if not math.isfinite(price) or price <= 0:
        raise ValueError("exit_price must be finite and positive")
    closed_at = closed_at or datetime.now(timezone.utc)
    plan = current.plan
    entry = (float(plan["entry_zone"][0]) + float(plan["entry_zone"][1])) / 2.0
    qty = float(plan["quantity"])
    direction = TradeDirection(plan["direction"])
    gross = (price - entry) * qty if direction == TradeDirection.LONG else (entry - price) * qty
    costs = entry * qty * float(plan["estimated_roundtrip_cost_bps"]) / 10_000.0
    pnl = gross - costs
    risk = float(plan["estimated_loss_at_invalidation"])
    event = {
        "trade_id": trade_id,
        "event_type": "CLOSE",
        "recorded_at": closed_at.astimezone(timezone.utc).isoformat(),
        "exit_price": price,
        "realized_pnl": pnl,
        "realized_r": 0.0 if risk == 0 else pnl / risk,
        "reason": reason.strip() or "MANUAL_CLOSE",
        "claim_ceiling": "PAPER_JOURNAL_ONLY",
    }
    return _append_trade_event(root, event)


def cancel_paper_trade(root: str | Path, *, trade_id: str, reason: str, recorded_at: datetime | None = None) -> dict[str, Any]:
    root = Path(root)
    current = {v.trade_id: v for v in list_paper_trades(root)}.get(trade_id)
    if current is None:
        raise KeyError(trade_id)
    if current.status != PaperTradeStatus.OPEN:
        raise ValueError("paper trade is not open")
    recorded_at = recorded_at or datetime.now(timezone.utc)
    return _append_trade_event(root, {
        "trade_id": trade_id,
        "event_type": "CANCEL",
        "recorded_at": recorded_at.astimezone(timezone.utc).isoformat(),
        "reason": reason.strip() or "MANUAL_CANCEL",
        "claim_ceiling": "PAPER_JOURNAL_ONLY",
    })


def list_paper_trades(root: str | Path) -> list[PaperTradeView]:
    root = Path(root)
    journal = root / "runtime/trading/paper_events.jsonl"
    entries = load_jsonl(journal)
    errors = verify_chain(entries)
    if errors:
        raise ValueError("PAPER_TRADE_JOURNAL_INVALID:" + ",".join(errors))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in entries:
        grouped.setdefault(row["trade_id"], []).append(row)
    out: list[PaperTradeView] = []
    for trade_id, events in grouped.items():
        first = events[0]
        if first["event_type"] != "OPEN":
            raise ValueError(f"trade {trade_id} does not start with OPEN")
        plan_path = root / "runtime" / first["plan_path"]
        if not plan_path.exists():
            raise ValueError(f"missing paper plan: {plan_path}")
        immutable = json.loads(plan_path.read_text(encoding="utf-8"))
        status = PaperTradeStatus.OPEN
        closed_at = None
        exit_price = None
        pnl = None
        realized_r = None
        reason = None
        for event in events[1:]:
            if status != PaperTradeStatus.OPEN:
                raise ValueError(f"event after terminal state for {trade_id}")
            if event["event_type"] == "CLOSE":
                status = PaperTradeStatus.CLOSED
                closed_at = event["recorded_at"]
                exit_price = float(event["exit_price"])
                pnl = float(event["realized_pnl"])
                realized_r = float(event["realized_r"])
                reason = event.get("reason")
            elif event["event_type"] == "CANCEL":
                status = PaperTradeStatus.CANCELLED
                closed_at = event["recorded_at"]
                reason = event.get("reason")
            else:
                raise ValueError(f"unknown paper event: {event['event_type']}")
        out.append(PaperTradeView(
            trade_id=trade_id,
            status=status,
            plan=immutable["plan"],
            opened_at=immutable["opened_at"],
            closed_at=closed_at,
            exit_price=exit_price,
            realized_pnl=pnl,
            realized_r=realized_r,
            close_reason=reason,
            event_count=len(events),
        ))
    return sorted(out, key=lambda x: x.opened_at, reverse=True)


def paper_journal_summary(root: str | Path) -> dict[str, Any]:
    trades = list_paper_trades(root)
    closed = [t for t in trades if t.status == PaperTradeStatus.CLOSED]
    open_trades = [t for t in trades if t.status == PaperTradeStatus.OPEN]
    pnls = [float(t.realized_pnl or 0.0) for t in closed]
    rs = [float(t.realized_r or 0.0) for t in closed]
    wins = sum(1 for p in pnls if p > 0)
    return {
        "total": len(trades),
        "open": len(open_trades),
        "closed": len(closed),
        "cancelled": sum(1 for t in trades if t.status == PaperTradeStatus.CANCELLED),
        "realized_pnl": sum(pnls),
        "average_r": None if not rs else sum(rs) / len(rs),
        "win_rate": None if not closed else wins / len(closed),
        "claim_ceiling": "PAPER_JOURNAL_ONLY",
    }


def verify_paper_journal(root: str | Path) -> tuple[str, ...]:
    root = Path(root)
    entries = load_jsonl(root / "runtime/trading/paper_events.jsonl")
    errors = list(verify_chain(entries))
    try:
        list_paper_trades(root)
    except Exception as exc:  # pragma: no cover - defensive aggregation
        errors.append(f"RECONSTRUCTION:{type(exc).__name__}:{exc}")
    return tuple(errors)
