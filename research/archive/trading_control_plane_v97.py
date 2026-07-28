"""Fail-closed limited-production control plane for War Room OS V9.7.

This module is intentionally broker-neutral. It can size, approve and export an order ticket, but it
cannot transmit an order to a broker. Auto-submission remains disabled in the frozen policy. A ticket
exists only when: exact-scope proof is valid, a current quote is fresh, causal decision fields are
complete, all portfolio limits pass, and a human approval is bound with HMAC to the exact decision,
account state, quote set and policy.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import hmac
import json
import math
import os
import re
from pathlib import Path
from typing import Any, Mapping

from warroom.no_technical_policy import contains_forbidden_decision_term, validate_feature_names

HERE = Path(__file__).resolve().parent
POLICY_PATH = HERE / "V97_LIMITED_PRODUCTION_POLICY.json"
REGISTRY_PATH = HERE / "component_registry_v97.json"
QUOTE_PATH = HERE / "runtime" / "v97_trading" / "execution_quotes.json"
RUNTIME = HERE / "runtime" / "v97_trading"
LEDGER_PATH = RUNTIME / "order_ledger.jsonl"
KILL_SWITCH_PATH = RUNTIME / "KILL_SWITCH.json"
UTC = dt.timezone.utc
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MARKETS = {"us", "idx", "commodity", "fx", "crypto"}
DIRECTIONS = {"LONG", "SHORT", "FLAT"}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"{p.name} root must be an object")
    return raw


def _time(value: Any) -> dt.datetime:
    parsed = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timestamp must include timezone")
    return parsed.astimezone(UTC)


def _now() -> dt.datetime:
    return dt.datetime.now(UTC)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _finite(value: Any, name: str, *, positive: bool = False) -> float:
    number = float(value)
    if not math.isfinite(number) or (positive and number <= 0):
        raise ValueError(f"{name} must be {'positive and ' if positive else ''}finite")
    return number


def _strict_bool(value: Any) -> bool:
    if value is True or value == 1:
        return True
    if value is False or value == 0:
        return False
    raise ValueError("boolean field must be a real boolean")


def _policy(path: Path = POLICY_PATH) -> dict[str, Any]:
    policy = _load(path)
    if policy.get("schema") != "warroom.v97.limited_production_policy.v1":
        raise ValueError("wrong policy schema")
    rules = policy.get("execution_rules") or {}
    if _strict_bool(rules.get("auto_submit_enabled")) is not False:
        raise ValueError("V9.7 frozen policy must keep auto-submit disabled")
    return policy


def _safe_local(relative: str) -> Path:
    candidate = (HERE / relative).resolve()
    candidate.relative_to(HERE.resolve())
    return candidate


def _verify_proof(decision: Mapping[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    binding = decision.get("proof_binding") if isinstance(decision.get("proof_binding"), Mapping) else {}
    relative = str(binding.get("proof_run_path") or "")
    expected = str(binding.get("proof_run_sha256") or "").lower()
    required = str(binding.get("required_state") or "LIMITED_PRODUCTION_ELIGIBLE")
    proof: dict[str, Any] | None = None
    try:
        path = _safe_local(relative)
    except Exception:
        path = Path("/__invalid__")
        errors.append("proof path escapes package")
    if not relative or not path.is_file():
        errors.append("bound proof run is missing")
        return None, errors
    if not HEX64.fullmatch(expected) or _sha_file(path) != expected:
        errors.append("proof-run hash missing or mismatched")
        return None, errors
    try:
        proof = _load(path)
    except Exception as exc:
        errors.append(f"proof run unreadable: {type(exc).__name__}: {exc}")
        return None, errors
    if proof.get("schema") not in {"warroom.v96.blind_proof_run.v1", "warroom.v97.blind_proof_run.v1"}:
        errors.append("unsupported proof-run schema")
    try:
        registry = _load(REGISTRY_PATH)
        rows = registry.get("components") if isinstance(registry.get("components"), Mapping) else {}
        bound = [row for row in rows.values() if isinstance(row, Mapping) and str(row.get("market") or "").lower() == str(decision.get("market") or "").lower() and str(row.get("proof_run_path") or "") == relative and str(row.get("proof_run_sha256") or "").lower() == expected]
        if len(bound) != 1:
            errors.append("proof run is not uniquely bound in component_registry_v97.json")
    except Exception as exc:
        errors.append(f"V9.7 component registry invalid: {type(exc).__name__}: {exc}")
    if str(proof.get("market") or "").lower() != str(decision.get("market") or "").lower():
        errors.append("proof market mismatch")
    if proof.get("trading_ready") is not True:
        errors.append("proof run is not trading-ready")
    if str(proof.get("capital_permission") or "") != required:
        errors.append("proof permission does not match required state")
    if (proof.get("signed_receipt_verification") or {}).get("valid") is not True:
        errors.append("proof signed receipt is invalid")
    if proof.get("errors"):
        errors.append("proof run contains errors")
    return proof, errors


def _quote_for(decision: Mapping[str, Any], quotes: Mapping[str, Any], *, now: dt.datetime, max_age: float) -> tuple[dict[str, Any] | None, list[str]]:
    market = str(decision.get("market") or "").lower()
    instrument = str(decision.get("instrument") or "")
    quote = (((quotes.get("markets") or {}).get(market) or {}).get(instrument)) if isinstance(quotes, Mapping) else None
    errors: list[str] = []
    if not isinstance(quote, Mapping):
        return None, ["current execution quote is missing"]
    try:
        provider_time = _time(quote.get("provider_timestamp"))
        age = (now - provider_time).total_seconds()
        if age < -5:
            errors.append("quote timestamp is in the future")
        if age > max_age:
            errors.append(f"quote is stale: {round(age, 1)} seconds")
        _finite(quote.get("price"), "quote price", positive=True)
        if quote.get("validation") != "VALID_EXECUTION_REFERENCE":
            errors.append("quote validation state is invalid")
        base = {k: v for k, v in quote.items() if k != "record_hash"}
        if str(quote.get("record_hash") or "") != _hash(base):
            errors.append("quote record hash mismatch")
        if quote.get("predictor_eligible") is not False:
            errors.append("execution quote cannot be predictor-eligible")
    except Exception as exc:
        errors.append(f"quote invalid: {type(exc).__name__}: {exc}")
    return dict(quote), errors


def _causal_errors(decision: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    feature_names = decision.get("feature_names") or []
    if not isinstance(feature_names, list):
        return ["feature_names must be a list"]
    violations = validate_feature_names([str(x) for x in feature_names])
    errors.extend("forbidden technical feature: " + item for item in violations)
    thesis = decision.get("causal_thesis") if isinstance(decision.get("causal_thesis"), Mapping) else {}
    required = ("trigger", "direct_effect", "transmission", "value_recipient", "timing", "interaction_conditions", "claim_limit")
    for field in required:
        value = thesis.get(field)
        if value is None or value == "" or value == []:
            errors.append(f"causal thesis missing {field}")
    if not isinstance(thesis.get("transmission"), list) or len(thesis.get("transmission") or []) < 2:
        errors.append("causal transmission must have at least two links")
    if not isinstance(thesis.get("interaction_conditions"), list):
        errors.append("interaction_conditions must be a list")
    text = _canonical(thesis).decode("utf-8") + " " + " ".join(str(x) for x in feature_names)
    hits = contains_forbidden_decision_term(text)
    if hits:
        errors.append("technical decision semantics detected: " + ",".join(hits))
    if not HEX64.fullmatch(str(decision.get("causal_map_hash") or "")):
        errors.append("causal_map_hash must be SHA-256")
    if not str(decision.get("invalidation") or "").strip():
        errors.append("observable invalidation is required")
    return errors


def _position_metrics(account: Mapping[str, Any]) -> dict[str, float]:
    gross = 0.0; net = 0.0; open_risk = 0.0; positions = 0
    for row in account.get("open_positions") or []:
        if not isinstance(row, Mapping):
            continue
        notional = abs(float(row.get("notional") or 0.0))
        direction = str(row.get("direction") or "LONG").upper()
        gross += notional
        net += notional if direction == "LONG" else -notional
        open_risk += max(0.0, float(row.get("open_risk") or 0.0))
        positions += 1
    return {"gross_notional": gross, "net_notional": net, "open_risk": open_risk, "open_positions": float(positions)}


def _quantize_down(value: float, step: float) -> float:
    if step <= 0:
        raise ValueError("quantity step must be positive")
    return math.floor((value + 1e-12) / step) * step


def evaluate(decision: Mapping[str, Any], account: Mapping[str, Any], quotes: Mapping[str, Any], *, now: dt.datetime | None = None, policy: Mapping[str, Any] | None = None) -> dict[str, Any]:
    now = (now or _now()).astimezone(UTC)
    policy = dict(policy or _policy())
    limits = policy["hard_limits"]; rules = policy["execution_rules"]
    errors: list[str] = []; warnings: list[str] = []
    if decision.get("schema") != "warroom.v97.trade_decision.v1":
        errors.append("wrong decision schema")
    if account.get("schema") != "warroom.v97.account_state.v1":
        errors.append("wrong account-state schema")
    market = str(decision.get("market") or "").lower()
    direction = str(decision.get("direction") or "").upper()
    if market not in MARKETS:
        errors.append("unsupported market")
    if direction not in DIRECTIONS:
        errors.append("unsupported direction")
    if direction == "FLAT":
        return {
            "schema": "warroom.v97.pretrade_evaluation.v1", "evaluated_at": _iso(now),
            "decision_id": decision.get("decision_id"), "market": market, "instrument": decision.get("instrument"),
            "state": "NO_TRADE", "exportable": False, "capital_permission": "BLOCKED",
            "errors": [], "warnings": ["Decision direction is FLAT."], "sizing": None,
            "inputs_hash": _hash({"decision": decision, "account": account, "quotes_manifest": quotes.get("manifest_hash"), "policy_id": policy.get("policy_id")}),
        }
    try:
        created = _time(decision.get("created_at"))
        age = (now - created).total_seconds()
        if age < -5:
            errors.append("decision timestamp is in the future")
        if age > float(limits["max_decision_age_seconds"]):
            errors.append("decision is stale")
    except Exception as exc:
        errors.append(f"decision timestamp invalid: {type(exc).__name__}: {exc}")
    errors.extend(_causal_errors(decision))
    proof, proof_errors = _verify_proof(decision)
    errors.extend(proof_errors)
    quote, quote_errors = _quote_for(decision, quotes, now=now, max_age=float(limits["max_quote_age_seconds"]))
    errors.extend(quote_errors)

    try:
        equity = _finite(account.get("equity"), "account equity", positive=True)
        peak = _finite(account.get("peak_equity"), "peak equity", positive=True)
        if equity < float(limits["minimum_account_equity"]):
            errors.append("account equity below frozen pilot minimum")
        account_asof = _time(account.get("as_of"))
        if account_asof > now + dt.timedelta(seconds=5):
            errors.append("account state is from the future")
        elif (now - account_asof).total_seconds() > float(limits["max_account_state_age_seconds"]):
            errors.append("account state is stale")
        daily_pnl = _finite(account.get("daily_realized_pnl"), "daily realized P&L")
        weekly_pnl = _finite(account.get("weekly_realized_pnl"), "weekly realized P&L")
        orders_today = int(account.get("orders_today") or 0)
        drawdown_pct = max(0.0, (peak - equity) / peak * 100.0)
        if daily_pnl <= -equity * float(limits["max_daily_realized_loss_pct_equity"]) / 100.0:
            errors.append("daily loss kill threshold reached")
        if weekly_pnl <= -equity * float(limits["max_weekly_realized_loss_pct_equity"]) / 100.0:
            errors.append("weekly loss kill threshold reached")
        if drawdown_pct >= float(limits["max_rolling_drawdown_pct_equity"]):
            errors.append("rolling drawdown kill threshold reached")
        if orders_today >= int(limits["max_orders_per_day"]):
            errors.append("daily order-count limit reached")
    except Exception as exc:
        equity = 0.0; drawdown_pct = None
        errors.append(f"account state invalid: {type(exc).__name__}: {exc}")

    if KILL_SWITCH_PATH.is_file():
        try:
            kill = _load(KILL_SWITCH_PATH)
            if kill.get("engaged") is True:
                errors.append("manual kill switch is engaged")
        except Exception:
            errors.append("kill-switch file is unreadable; fail closed")

    sizing: dict[str, Any] | None = None
    try:
        entry = _finite(decision.get("entry_limit"), "entry", positive=True)
        stop = _finite(decision.get("stop_price"), "stop", positive=True)
        target = _finite(decision.get("target_price"), "target", positive=True)
        expected = _finite(decision.get("expected_net_return_pct"), "expected net return")
        lower = _finite(decision.get("confidence_lower_bound_return_pct"), "confidence lower-bound return")
        quote_price = _finite((quote or {}).get("price"), "quote price", positive=True)
        if expected < float(limits["minimum_expected_net_return_pct"]):
            errors.append("expected net return below frozen minimum")
        if lower <= 0:
            errors.append("confidence lower-bound return must be positive")
        distance_quote = abs(entry - quote_price) / quote_price * 100.0
        if distance_quote > float(limits["max_entry_distance_from_quote_pct"]):
            errors.append("entry limit is too far from current quote")
        if direction == "LONG":
            if not (stop < entry < target):
                errors.append("LONG requires stop < entry < target")
        elif direction == "SHORT":
            if not (target < entry < stop):
                errors.append("SHORT requires target < entry < stop")
            route = (policy.get("market_routes") or {}).get(market) or {}
            if "SHORT" not in (route.get("directions") or []) and "SHORT_WITH_BORROW_RECEIPT" not in (route.get("directions") or []):
                errors.append("short direction is not allowed for this market")
            if market == "us" and not decision.get("borrow_receipt_hash"):
                errors.append("US short requires bound borrow receipt")
        stop_distance = abs(entry - stop)
        target_distance = abs(target - entry)
        stop_pct = stop_distance / entry * 100.0
        target_pct = target_distance / entry * 100.0
        reward_to_risk = target_distance / stop_distance
        if stop_pct > float(limits["max_stop_distance_pct"]):
            errors.append("stop distance exceeds frozen maximum")
        if target_pct > float(limits["max_target_distance_pct"]):
            errors.append("target distance exceeds frozen maximum")
        if reward_to_risk < float(limits["minimum_reward_to_risk"]):
            errors.append("reward-to-risk below frozen minimum")
        spec = decision.get("instrument_spec") if isinstance(decision.get("instrument_spec"), Mapping) else {}
        multiplier = _finite(spec.get("contract_multiplier"), "contract multiplier", positive=True)
        step = _finite(spec.get("quantity_step"), "quantity step", positive=True)
        minimum = _finite(spec.get("minimum_quantity"), "minimum quantity", positive=True)
        maximum = spec.get("maximum_quantity")
        maximum_f = _finite(maximum, "maximum quantity", positive=True) if maximum not in (None, "") else math.inf
        if market in {"commodity", "fx"}:
            for field in ("expiry", "tick_size"):
                if spec.get(field) in (None, ""):
                    errors.append(f"{market} instrument spec requires {field}")
        risk_budget = equity * float(limits["max_risk_per_trade_pct_equity"]) / 100.0
        unit_risk = stop_distance * multiplier
        unit_notional = entry * multiplier
        by_risk = risk_budget / unit_risk
        by_position = equity * float(limits["max_single_position_notional_pct_equity"]) / 100.0 / unit_notional
        quantity = _quantize_down(min(by_risk, by_position, maximum_f), step)
        if quantity + 1e-12 < minimum:
            errors.append("frozen risk limits size the order below minimum tradable quantity")
        quantity = max(0.0, quantity)
        notional = quantity * unit_notional
        trade_risk = quantity * unit_risk
        positions = _position_metrics(account)
        market_notional = sum(abs(float(row.get("notional") or 0.0)) for row in account.get("open_positions") or [] if str(row.get("market") or "").lower() == market)
        new_gross = positions["gross_notional"] + notional
        new_net = positions["net_notional"] + (notional if direction == "LONG" else -notional)
        new_open_risk = positions["open_risk"] + trade_risk
        if positions["open_positions"] >= int(limits["max_open_positions"]):
            errors.append("maximum open positions reached")
        if market_notional + notional > equity * float(limits["max_market_notional_pct_equity"]) / 100.0 + 1e-9:
            errors.append("market notional cap exceeded")
        if new_gross > equity * float(limits["max_portfolio_gross_notional_pct_equity"]) / 100.0 + 1e-9:
            errors.append("portfolio gross-notional cap exceeded")
        if abs(new_net) > equity * float(limits["max_portfolio_net_notional_pct_equity"]) / 100.0 + 1e-9:
            errors.append("portfolio net-notional cap exceeded")
        if new_open_risk > equity * float(limits["max_total_open_risk_pct_equity"]) / 100.0 + 1e-9:
            errors.append("total open-risk cap exceeded")
        leverage = new_gross / equity if equity else math.inf
        if leverage > float(limits["maximum_leverage"]) + 1e-9:
            errors.append("maximum leverage exceeded")
        sizing = {
            "quantity": quantity,
            "quantity_step": step,
            "entry_limit": entry,
            "stop_price": stop,
            "target_price": target,
            "quote_price": quote_price,
            "unit_notional": unit_notional,
            "unit_risk": unit_risk,
            "trade_notional": notional,
            "trade_risk": trade_risk,
            "risk_pct_equity": trade_risk / equity * 100.0 if equity else None,
            "notional_pct_equity": notional / equity * 100.0 if equity else None,
            "reward_to_risk": reward_to_risk,
            "post_trade_gross_pct_equity": new_gross / equity * 100.0 if equity else None,
            "post_trade_net_pct_equity": new_net / equity * 100.0 if equity else None,
            "post_trade_open_risk_pct_equity": new_open_risk / equity * 100.0 if equity else None,
            "drawdown_pct": drawdown_pct,
        }
    except Exception as exc:
        errors.append(f"sizing invalid: {type(exc).__name__}: {exc}")

    route = (policy.get("market_routes") or {}).get(market) or {}
    if decision.get("asset_type") not in (route.get("asset_types") or []):
        errors.append("asset type not allowed by market route")
    if decision.get("venue") not in (route.get("execution_venues") or []):
        errors.append("venue not allowed by market route")
    if str(decision.get("order_type") or rules.get("default_order_type")) not in rules.get("allowed_order_types", []):
        errors.append("order type not allowed")
    if str(decision.get("time_in_force") or "DAY") not in rules.get("allowed_time_in_force", []):
        errors.append("time in force not allowed")

    inputs_hash = _hash({
        "decision": decision,
        "account": account,
        "quote_manifest_hash": quotes.get("manifest_hash"),
        "proof_hash": ((decision.get("proof_binding") or {}).get("proof_run_sha256")),
        "policy_hash": _hash(policy),
    })
    exportable = not errors and sizing is not None and sizing.get("quantity", 0) > 0
    return {
        "schema": "warroom.v97.pretrade_evaluation.v1",
        "evaluated_at": _iso(now),
        "decision_id": decision.get("decision_id"),
        "market": market,
        "instrument": decision.get("instrument"),
        "direction": direction,
        "state": "AWAITING_HUMAN_APPROVAL" if exportable else "BLOCKED",
        "exportable": False,
        "pretrade_pass": exportable,
        "capital_permission": "LIMITED_PRODUCTION_ELIGIBLE" if exportable else "BLOCKED",
        "errors": sorted(set(errors)),
        "warnings": sorted(set(warnings)),
        "sizing": sizing,
        "proof_run_hash": ((decision.get("proof_binding") or {}).get("proof_run_sha256")) if proof else None,
        "quote_record_hash": (quote or {}).get("record_hash"),
        "policy_id": policy.get("policy_id"),
        "policy_hash": _hash(policy),
        "inputs_hash": inputs_hash,
        "auto_submit": False,
    }


def _approval_payload(evaluation: Mapping[str, Any], account: Mapping[str, Any], *, approved_by: str, now: dt.datetime) -> dict[str, Any]:
    return {
        "schema": "warroom.v97.human_approval.v1",
        "approval_id": "apr-" + _hash({"inputs_hash": evaluation.get("inputs_hash"), "approved_at": _iso(now), "approved_by": approved_by})[:20],
        "approved_at": _iso(now),
        "approved_by": approved_by,
        "decision_id": evaluation.get("decision_id"),
        "account_id_hash": account.get("account_id_hash"),
        "inputs_hash": evaluation.get("inputs_hash"),
        "policy_hash": evaluation.get("policy_hash"),
        "pretrade_state": evaluation.get("state"),
        "explicit_acknowledgement": "I reviewed the exact instrument, direction, size, entry, stop, target, causal invalidation, account state and limited-production risk limits.",
    }


def create_approval(evaluation: Mapping[str, Any], account: Mapping[str, Any], *, approved_by: str, secret: str, now: dt.datetime | None = None) -> dict[str, Any]:
    if evaluation.get("pretrade_pass") is not True or evaluation.get("state") != "AWAITING_HUMAN_APPROVAL":
        raise ValueError("pre-trade evaluation did not pass")
    if len(secret.encode("utf-8")) < 24:
        raise ValueError("approval secret must contain at least 24 bytes")
    now = (now or _now()).astimezone(UTC)
    payload = _approval_payload(evaluation, account, approved_by=approved_by, now=now)
    payload["hmac_sha256"] = hmac.new(secret.encode("utf-8"), _canonical(payload), hashlib.sha256).hexdigest()
    return payload


def verify_approval(approval: Mapping[str, Any], evaluation: Mapping[str, Any], account: Mapping[str, Any], *, secret: str) -> list[str]:
    errors: list[str] = []
    if approval.get("schema") != "warroom.v97.human_approval.v1":
        errors.append("wrong approval schema")
    if approval.get("inputs_hash") != evaluation.get("inputs_hash"):
        errors.append("approval is not bound to this pre-trade evaluation")
    if approval.get("policy_hash") != evaluation.get("policy_hash"):
        errors.append("approval policy hash mismatch")
    if approval.get("account_id_hash") != account.get("account_id_hash"):
        errors.append("approval account mismatch")
    provided = str(approval.get("hmac_sha256") or "")
    base = {k: v for k, v in approval.items() if k != "hmac_sha256"}
    expected = hmac.new(secret.encode("utf-8"), _canonical(base), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(provided, expected):
        errors.append("approval HMAC is invalid")
    try:
        if (_now() - _time(approval.get("approved_at"))).total_seconds() > 900:
            errors.append("approval is older than 15 minutes")
    except Exception:
        errors.append("approval timestamp invalid")
    return errors


def _last_ledger_hash() -> str:
    if not LEDGER_PATH.is_file():
        return "0" * 64
    lines = [line for line in LEDGER_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not lines:
        return "0" * 64
    try:
        return str(json.loads(lines[-1]).get("event_hash") or "")
    except Exception:
        return "INVALID"


def _append_ledger(event: dict[str, Any]) -> dict[str, Any]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    previous = _last_ledger_hash()
    if not HEX64.fullmatch(previous):
        raise RuntimeError("order ledger chain is invalid")
    row = {**event, "previous_hash": previous}
    row["event_hash"] = _hash(row)
    with LEDGER_PATH.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False) + "\n")
        f.flush(); os.fsync(f.fileno())
    return row


def export_order(decision: Mapping[str, Any], account: Mapping[str, Any], evaluation: Mapping[str, Any], approval: Mapping[str, Any], *, secret: str, output_dir: Path | None = None) -> dict[str, Any]:
    approval_errors = verify_approval(approval, evaluation, account, secret=secret)
    if approval_errors:
        raise ValueError("; ".join(approval_errors))
    if evaluation.get("pretrade_pass") is not True:
        raise ValueError("pre-trade evaluation is not a pass")
    if KILL_SWITCH_PATH.is_file() and (_load(KILL_SWITCH_PATH).get("engaged") is True):
        raise ValueError("kill switch is engaged")
    sizing = evaluation.get("sizing") or {}
    order = {
        "schema": "warroom.v97.broker_neutral_order.v1",
        "order_id": "ord-" + _hash({"inputs_hash": evaluation.get("inputs_hash"), "approval_id": approval.get("approval_id")})[:24],
        "created_at": _iso(_now()),
        "status": "READY_FOR_MANUAL_SUBMISSION",
        "auto_submit": False,
        "account_id_hash": account.get("account_id_hash"),
        "decision_id": decision.get("decision_id"),
        "market": decision.get("market"),
        "instrument": decision.get("instrument"),
        "asset_type": decision.get("asset_type"),
        "venue": decision.get("venue"),
        "side": "BUY" if decision.get("direction") == "LONG" else "SELL",
        "quantity": sizing.get("quantity"),
        "order_type": decision.get("order_type") or "LIMIT",
        "limit_price": sizing.get("entry_limit"),
        "time_in_force": decision.get("time_in_force") or "DAY",
        "protective_stop": sizing.get("stop_price"),
        "target_price": sizing.get("target_price"),
        "trade_notional": sizing.get("trade_notional"),
        "trade_risk": sizing.get("trade_risk"),
        "risk_pct_equity": sizing.get("risk_pct_equity"),
        "invalidation": decision.get("invalidation"),
        "proof_run_sha256": (decision.get("proof_binding") or {}).get("proof_run_sha256"),
        "quote_record_hash": evaluation.get("quote_record_hash"),
        "policy_hash": evaluation.get("policy_hash"),
        "inputs_hash": evaluation.get("inputs_hash"),
        "approval_id": approval.get("approval_id"),
        "approval_hmac_sha256": approval.get("hmac_sha256"),
        "claim_limit": "Manual submission only. Re-check broker contract specs, available cash/margin, price bands, borrow and venue status immediately before entry.",
    }
    order["order_hash"] = _hash({k: v for k, v in order.items() if k != "order_hash"})
    out = output_dir or (RUNTIME / "orders" / "pending")
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / f"{order['order_id']}.json"
    csv_path = out / f"{order['order_id']}.csv"
    if json_path.exists() or csv_path.exists():
        raise ValueError("duplicate order export rejected")
    temp = json_path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(order, indent=2, allow_nan=False), encoding="utf-8"); os.replace(temp, json_path)
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        fields = ["order_id", "market", "instrument", "asset_type", "venue", "side", "quantity", "order_type", "limit_price", "time_in_force", "protective_stop", "target_price", "trade_notional", "trade_risk", "risk_pct_equity", "status"]
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader(); writer.writerow({k: order.get(k) for k in fields})
    ledger = _append_ledger({"event_type": "ORDER_EXPORTED", "event_at": _iso(_now()), "order_id": order["order_id"], "order_hash": order["order_hash"], "inputs_hash": order["inputs_hash"], "approval_id": order["approval_id"]})
    return {"order": order, "json_path": json_path.relative_to(HERE).as_posix(), "csv_path": csv_path.relative_to(HERE).as_posix(), "ledger_event_hash": ledger["event_hash"]}


def engage_kill_switch(reason: str, *, actor: str) -> dict[str, Any]:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    payload = {"schema": "warroom.v97.kill_switch.v1", "engaged": True, "engaged_at": _iso(_now()), "actor": actor, "reason": reason.strip() or "manual operator action"}
    payload["record_hash"] = _hash({k: v for k, v in payload.items() if k != "record_hash"})
    KILL_SWITCH_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _append_ledger({"event_type": "KILL_SWITCH_ENGAGED", "event_at": payload["engaged_at"], "record_hash": payload["record_hash"], "actor": actor})
    return payload


def release_kill_switch(*, actor: str, explicit_text: str) -> dict[str, Any]:
    if explicit_text != "RELEASE V97 KILL SWITCH":
        raise ValueError("exact release acknowledgement required")
    previous = _load(KILL_SWITCH_PATH) if KILL_SWITCH_PATH.is_file() else {"engaged": False}
    payload = {"schema": "warroom.v97.kill_switch_release.v1", "released_at": _iso(_now()), "actor": actor, "previous_hash": previous.get("record_hash"), "explicit_text": explicit_text}
    payload["record_hash"] = _hash({k: v for k, v in payload.items() if k != "record_hash"})
    KILL_SWITCH_PATH.unlink(missing_ok=True)
    _append_ledger({"event_type": "KILL_SWITCH_RELEASED", "event_at": payload["released_at"], "record_hash": payload["record_hash"], "actor": actor})
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    p_eval = sub.add_parser("evaluate"); p_eval.add_argument("--decision", required=True); p_eval.add_argument("--account", required=True); p_eval.add_argument("--quotes", default=str(QUOTE_PATH)); p_eval.add_argument("--output")
    p_approve = sub.add_parser("approve"); p_approve.add_argument("--evaluation", required=True); p_approve.add_argument("--account", required=True); p_approve.add_argument("--approved-by", required=True); p_approve.add_argument("--output", required=True)
    p_export = sub.add_parser("export"); p_export.add_argument("--decision", required=True); p_export.add_argument("--account", required=True); p_export.add_argument("--evaluation", required=True); p_export.add_argument("--approval", required=True); p_export.add_argument("--output-dir")
    p_kill = sub.add_parser("kill"); p_kill.add_argument("--reason", required=True); p_kill.add_argument("--actor", required=True)
    p_release = sub.add_parser("release-kill"); p_release.add_argument("--actor", required=True); p_release.add_argument("--ack", required=True)
    args = parser.parse_args()
    if args.command == "evaluate":
        result = evaluate(_load(args.decision), _load(args.account), _load(args.quotes))
        if args.output: Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    elif args.command == "approve":
        secret = os.getenv("WARROOM_HUMAN_APPROVAL_SECRET", "")
        result = create_approval(_load(args.evaluation), _load(args.account), approved_by=args.approved_by, secret=secret)
        Path(args.output).write_text(json.dumps(result, indent=2, allow_nan=False), encoding="utf-8")
    elif args.command == "export":
        secret = os.getenv("WARROOM_HUMAN_APPROVAL_SECRET", "")
        result = export_order(_load(args.decision), _load(args.account), _load(args.evaluation), _load(args.approval), secret=secret, output_dir=Path(args.output_dir) if args.output_dir else None)
    elif args.command == "kill": result = engage_kill_switch(args.reason, actor=args.actor)
    else: result = release_kill_switch(actor=args.actor, explicit_text=args.ack)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
