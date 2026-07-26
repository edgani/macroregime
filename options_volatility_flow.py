"""Fail-closed options volatility and mechanical-flow research module.

This module implements the mapping frozen in V69.  It intentionally separates:

* tradable volatility/range information;
* unsigned Greek magnitude from public chain data;
* signed dealer inventory, which requires explicit provenance;
* hedge-flow impact, which requires underlying liquidity inputs;
* research diagnostics from trading permission.

Nothing returned by this module is a standalone LONG/SHORT signal.  All live and capital
weights remain zero until exact-scope walk-forward, lockbox and prospective evidence exists.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from statistics import mean, pstdev
from typing import Any, Iterable, Mapping, Sequence

BAD_STATES = {"", "NO_DATA", "ERROR", "OFFLINE", "NOT_CONFIGURED", "EMPTY", "ACTION_REQUIRED"}
SUPPORTED_MARKETS = {"us", "crypto", "commodity", "fx"}
VERIFIED_SIGN_SOURCES = {
    "EXCHANGE_PARTICIPANT_OPEN_CLOSE",
    "CLEARING_MEMBER_POSITION_FILE",
    "SIGNED_DEALER_INVENTORY_FEED",
    "AUDITED_POSITION_RECEIPT",
}


def _f(value: Any, default: float | None = None) -> float | None:
    try:
        out = float(value)
        return out if math.isfinite(out) else default
    except (TypeError, ValueError):
        return default


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except Exception:
        return None


def _iso_now(now: datetime | None = None) -> str:
    dt = now or datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _fresh(value: Any, now: datetime, max_age_seconds: float) -> bool:
    dt = _parse_time(value)
    if dt is None:
        return False
    age = (now - dt.astimezone(timezone.utc)).total_seconds()
    return -300 <= age <= max_age_seconds


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _normalize_iv(value: Any) -> float | None:
    iv = _f(value)
    if iv is None or iv <= 0:
        return None
    if iv > 3.0:
        iv /= 100.0
    return iv if 0 < iv <= 5.0 else None


def _year_fraction(expiration: Any, now: datetime) -> float | None:
    dt = _parse_time(str(expiration)[:10])
    if dt is None:
        try:
            dt = datetime.strptime(str(expiration)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except Exception:
            return None
    return max(1.0 / (365.0 * 24.0), (dt - now).total_seconds() / (365.0 * 86400.0))


def _bs_greeks(spot: float, strike: float, t: float, iv: float, option_type: str,
               rate: float = 0.04, dividend: float = 0.0) -> dict[str, float]:
    if min(spot, strike, t, iv) <= 0:
        return {"delta": 0.0, "gamma": 0.0, "vega": 0.0, "vanna": 0.0, "charm": 0.0}
    root = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate - dividend + 0.5 * iv * iv) * t) / (iv * root)
    d2 = d1 - iv * root
    dq = math.exp(-dividend * t)
    dr = math.exp(-rate * t)
    call = str(option_type).lower().startswith("c")
    delta = dq * _norm_cdf(d1) if call else dq * (_norm_cdf(d1) - 1.0)
    gamma = dq * _norm_pdf(d1) / (spot * iv * root)
    vega = spot * dq * _norm_pdf(d1) * root
    vanna = -dq * _norm_pdf(d1) * d2 / iv
    common = -dq * _norm_pdf(d1) * (2.0 * (rate - dividend) * t - d2 * iv * root) / (2.0 * t * iv * root)
    charm = common - dividend * dq * _norm_cdf(d1) if call else common + dividend * dq * _norm_cdf(-d1)
    return {"delta": delta, "gamma": gamma, "vega": vega, "vanna": vanna, "charm": charm}


def _bs_price_delta(spot: float, strike: float, t: float, iv: float, option_type: str,
                    rate: float = 0.0) -> tuple[float, float]:
    call = str(option_type).lower().startswith("c")
    if t <= 0:
        payoff = max(0.0, spot - strike) if call else max(0.0, strike - spot)
        delta = 1.0 if call and spot > strike else -1.0 if (not call and spot < strike) else 0.0
        return payoff, delta
    root = math.sqrt(t)
    d1 = (math.log(spot / strike) + (rate + 0.5 * iv * iv) * t) / (iv * root)
    d2 = d1 - iv * root
    if call:
        return spot * _norm_cdf(d1) - strike * math.exp(-rate * t) * _norm_cdf(d2), _norm_cdf(d1)
    return strike * math.exp(-rate * t) * _norm_cdf(-d2) - spot * _norm_cdf(-d1), _norm_cdf(d1) - 1.0


def _mid(row: Mapping[str, Any]) -> tuple[float | None, float | None]:
    bid = _f(row.get("bid") if row.get("bid") is not None else row.get("bid_price"))
    ask = _f(row.get("ask") if row.get("ask") is not None else row.get("ask_price"))
    if bid is None or ask is None or bid < 0 or ask < bid:
        return None, None
    mid = (bid + ask) / 2.0
    spread_ratio = (ask - bid) / mid if mid > 0 else math.inf
    return mid, spread_ratio


def _concentration(values: Iterable[float]) -> tuple[float | None, float | None]:
    vals = [max(0.0, float(v)) for v in values if _f(v) is not None and float(v) >= 0]
    total = sum(vals)
    if total <= 0:
        return None, None
    shares = [v / total for v in vals]
    return sum(s * s for s in shares), max(shares)


def _rv_annualized(prices: Sequence[float], window: int = 21) -> float | None:
    clean = [float(x) for x in prices if _f(x) is not None and float(x) > 0]
    if len(clean) < max(3, window + 1):
        return None
    clean = clean[-(window + 1):]
    rets = [math.log(clean[i] / clean[i - 1]) for i in range(1, len(clean))]
    return pstdev(rets) * math.sqrt(252.0) if len(rets) >= 2 else None


@dataclass(frozen=True)
class ChainValidation:
    accepted: tuple[dict[str, Any], ...]
    rejected: tuple[dict[str, Any], ...]
    market: str
    observed_at: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "market": self.market,
            "observed_at": self.observed_at,
            "accepted_rows": len(self.accepted),
            "rejected_rows": len(self.rejected),
            "rejections": list(self.rejected)[:100],
            "row_level_validated": bool(self.accepted),
        }


def validate_option_rows(rows: Sequence[Mapping[str, Any]], market: str, *, now: datetime | None = None,
                         max_quote_age_seconds: float = 86400.0) -> ChainValidation:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    market = str(market or "").lower().strip()
    if market == "idx":
        rejected = tuple({"row": i, "reason": "IHSG_DIRECT_OPTIONS_DISABLED"} for i, _ in enumerate(rows))
        return ChainValidation((), rejected, market, _iso_now(now))
    if market not in SUPPORTED_MARKETS:
        rejected = tuple({"row": i, "reason": "UNSUPPORTED_MARKET"} for i, _ in enumerate(rows))
        return ChainValidation((), rejected, market, _iso_now(now))

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for i, raw in enumerate(rows):
        row = deepcopy(dict(raw))
        state = str(row.get("state") or "LIVE").upper()
        provider = str(row.get("provider") or "").strip()
        venue = str(row.get("venue") or "").strip()
        contract = str(row.get("contract") or row.get("symbol") or "").strip()
        underlying = str(row.get("underlying") or row.get("ticker") or row.get("asset") or "").strip().upper()
        expiry = row.get("expiration") or row.get("expiry") or row.get("expiry_code")
        strike = _f(row.get("strike"))
        typ = str(row.get("option_type") or row.get("type") or "").lower()[:1]
        multiplier = _f(row.get("multiplier"), 100.0 if market == "us" else None)
        evidence = row.get("capability_evidence") if isinstance(row.get("capability_evidence"), dict) else {}
        observed = (row.get("observed_at") or row.get("quote_observed_at") or row.get("timestamp")
                    or evidence.get("observed_at"))
        bid, spread = _mid(row)
        spot = _f(row.get("underlying_price") or row.get("spot"))
        reason = None
        if state in BAD_STATES:
            reason = "STATE_NOT_USABLE"
        elif not provider:
            reason = "PROVIDER_MISSING"
        elif market in {"crypto", "commodity", "fx"} and not venue:
            reason = "VENUE_MISSING"
        elif not contract:
            reason = "EXACT_CONTRACT_MISSING"
        elif not underlying:
            reason = "UNDERLYING_MISSING"
        elif not expiry or strike is None or strike <= 0 or typ not in {"c", "p"}:
            reason = "CONTRACT_FIELDS_INVALID"
        elif multiplier is None or multiplier <= 0:
            reason = "MULTIPLIER_MISSING"
        elif bid is None:
            reason = "NONCROSSED_QUOTE_MISSING"
        elif spot is None or spot <= 0:
            reason = "UNDERLYING_PRICE_MISSING"
        elif not _fresh(observed, now, max_quote_age_seconds):
            reason = "QUOTE_STALE_OR_UNTIMESTAMPED"
        elif market == "commodity" and not str(row.get("futures_contract") or row.get("underlying_contract") or "").strip():
            reason = "EXACT_FUTURES_CONTRACT_MISSING"
        elif market == "fx" and str(row.get("product_type") or "LISTED_OPTION").upper() not in {"LISTED_OPTION", "VOL_SURFACE"}:
            reason = "FX_SPOT_CANNOT_ENABLE_OPTIONS"
        if reason:
            rejected.append({"row": i, "contract": contract or None, "reason": reason})
            continue
        row["_normalized"] = {
            "provider": provider, "venue": venue or None, "contract": contract, "underlying": underlying,
            "expiration": str(expiry), "strike": strike, "option_type": typ, "multiplier": multiplier,
            "mid": bid, "spread_ratio": spread, "spot": spot, "observed_at": str(observed),
            "oi_lineage_ok": bool(_fresh(row.get("open_interest_observed_at") or row.get("oi_observed_at"), now, 3 * 86400.0)),
        }
        accepted.append(row)
    return ChainValidation(tuple(accepted), tuple(rejected), market, _iso_now(now))


def _verified_sign(row: Mapping[str, Any], now: datetime) -> tuple[bool, float | None, float]:
    sign = _f(row.get("dealer_sign"))
    confidence = _f(row.get("dealer_sign_confidence"), 0.0) or 0.0
    source = str(row.get("dealer_sign_source") or "").upper().strip()
    verified = row.get("dealer_inventory_verified") is True
    stamp = row.get("inventory_observed_at")
    ok = (
        verified and sign in {-1.0, 1.0} and confidence >= 0.80 and source in VERIFIED_SIGN_SOURCES
        and _fresh(stamp, now, 86400.0)
    )
    return ok, sign if ok else None, confidence if ok else 0.0


def analyze_options_volatility_flow(rows: Sequence[Mapping[str, Any]], market: str, *,
                                    underlying_prices: Sequence[float] = (),
                                    liquidity: Mapping[str, Any] | None = None,
                                    now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    validation = validate_option_rows(rows, market, now=now)
    accepted = list(validation.accepted)
    base = {
        "schema": "warroom.options_volatility_flow.v70",
        "status": "DESCRIPTIVE_ONLY" if accepted else "NO_DATA",
        "market": validation.market,
        "observed_at": _iso_now(now),
        "data_quality": validation.as_dict(),
        "decision_purposes": ["magnitude", "volatility_mispricing", "mechanical_flow", "strike_expiry_timing"],
        "standalone_direction": "WITHHELD",
        "calibrated_probability": None,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
    }
    if not accepted:
        return base

    normalized = [r["_normalized"] for r in accepted]
    spot_values = [n["spot"] for n in normalized if n["spot"] is not None]
    spot = sorted(spot_values)[len(spot_values) // 2]
    expiries = sorted({n["expiration"][:10] for n in normalized})
    nearest = expiries[0]
    near = [(r, n) for r, n in zip(accepted, normalized) if n["expiration"][:10] == nearest]

    calls = [(r, n) for r, n in near if n["option_type"] == "c"]
    puts = [(r, n) for r, n in near if n["option_type"] == "p"]
    atm_call = min(calls, key=lambda x: abs(x[1]["strike"] - spot), default=None)
    atm_put = min(puts, key=lambda x: abs(x[1]["strike"] - spot), default=None)
    tradable_expected_move = None
    expected_move_spread_ratio = None
    if atm_call and atm_put:
        cm, cs = atm_call[1]["mid"], atm_call[1]["spread_ratio"]
        pm, ps = atm_put[1]["mid"], atm_put[1]["spread_ratio"]
        expected_move_spread_ratio = max(cs or math.inf, ps or math.inf)
        if expected_move_spread_ratio <= 0.35:
            tradable_expected_move = cm + pm

    ivs = []
    for r, n in near:
        if abs(n["strike"] - spot) / spot <= 0.03:
            iv = _normalize_iv(r.get("implied_volatility") or r.get("mark_iv") or r.get("iv"))
            if iv is not None:
                ivs.append(iv)
    atm_iv = mean(ivs) if ivs else None
    rv21 = _rv_annualized(underlying_prices, 21)
    variance_gap = (rv21 * rv21 - atm_iv * atm_iv) if rv21 is not None and atm_iv is not None else None

    gamma_by_strike: dict[float, float] = {}
    oi_by_strike: dict[float, float] = {}
    unsigned_gamma = unsigned_vanna = unsigned_charm = 0.0
    signed_gamma = signed_vanna = signed_charm = 0.0
    signed_rows = 0
    confidence_weight = 0.0
    oi_rows = 0
    for r, n in zip(accepted, normalized):
        oi = _f(r.get("open_interest") or r.get("oi"), 0.0) or 0.0
        if oi > 0 and n["oi_lineage_ok"]:
            oi_rows += 1
        else:
            oi = 0.0
        iv = _normalize_iv(r.get("implied_volatility") or r.get("mark_iv") or r.get("iv"))
        t = _year_fraction(n["expiration"], now)
        greeks = _bs_greeks(spot, n["strike"], t, iv, n["option_type"]) if iv and t else {}
        gamma = abs(_f(r.get("gamma"), greeks.get("gamma", 0.0)) or 0.0)
        vanna = _f(r.get("vanna"), greeks.get("vanna", 0.0)) or 0.0
        charm = _f(r.get("charm"), greeks.get("charm", 0.0)) or 0.0
        gamma_notional = abs(gamma * oi * n["multiplier"] * spot * spot * 0.01)
        vanna_notional = abs(vanna * oi * n["multiplier"] * spot)
        charm_notional = abs(charm * oi * n["multiplier"] * spot)
        unsigned_gamma += gamma_notional
        unsigned_vanna += vanna_notional
        unsigned_charm += charm_notional
        gamma_by_strike[n["strike"]] = gamma_by_strike.get(n["strike"], 0.0) + gamma_notional
        oi_by_strike[n["strike"]] = oi_by_strike.get(n["strike"], 0.0) + oi
        ok, sign, confidence = _verified_sign(r, now)
        if ok and sign is not None:
            signed_rows += 1
            confidence_weight += confidence
            signed_gamma += sign * gamma_notional
            signed_vanna += sign * vanna * oi * n["multiplier"] * spot
            signed_charm += sign * charm * oi * n["multiplier"] * spot

    all_rows_signed = signed_rows == len(accepted) and signed_rows > 0
    sign_confidence = confidence_weight / signed_rows if all_rows_signed else 0.0
    regime = "WITHHELD_DEALER_SIGN_UNKNOWN"
    if all_rows_signed:
        regime = "DAMPING_CONTEXT" if signed_gamma > 0 else "AMPLIFICATION_CONTEXT" if signed_gamma < 0 else "NEUTRAL_CONTEXT"

    liquidity = dict(liquidity or {})
    adv = _f(liquidity.get("adv_notional"))
    depth = _f(liquidity.get("one_pct_depth_notional"))
    denom = depth if depth and depth > 0 else adv if adv and adv > 0 else None
    hedge_flow_per_1pct = abs(signed_gamma) if all_rows_signed else None
    impact_ratio = hedge_flow_per_1pct / denom if hedge_flow_per_1pct is not None and denom else None
    gamma_hhi, gamma_top_share = _concentration(gamma_by_strike.values())
    oi_hhi, oi_top_share = _concentration(oi_by_strike.values())
    gamma_zone = max(gamma_by_strike, key=gamma_by_strike.get) if gamma_by_strike else None
    oi_zone = max(oi_by_strike, key=oi_by_strike.get) if oi_by_strike else None

    base.update({
        "underlying": normalized[0]["underlying"],
        "venue_set": sorted({n["venue"] for n in normalized if n["venue"]}),
        "provider_set": sorted({n["provider"] for n in normalized}),
        "spot": spot,
        "nearest_expiry": nearest,
        "volatility_pricing": {
            "atm_iv": atm_iv,
            "realized_vol_21d": rv21,
            "realized_minus_implied_variance": variance_gap,
            "expected_move_mid": tradable_expected_move,
            "expected_move_upper": spot + tradable_expected_move if tradable_expected_move is not None else None,
            "expected_move_lower": spot - tradable_expected_move if tradable_expected_move is not None else None,
            "expected_move_spread_ratio": expected_move_spread_ratio,
            "gamma_scalping_edge_state": "UNPROVEN_COST_MODEL_REQUIRED",
            "semantics": "IV/RV difference is a volatility hypothesis, not guaranteed gamma-scalping P&L.",
        },
        "mechanical_flow": {
            "unsigned_gamma_magnitude": unsigned_gamma,
            "unsigned_vanna_magnitude": unsigned_vanna,
            "unsigned_charm_magnitude": unsigned_charm,
            "oi_rows_with_fresh_lineage": oi_rows,
            "dealer_sign_state": "VERIFIED" if all_rows_signed else "UNKNOWN",
            "dealer_sign_confidence": sign_confidence if all_rows_signed else None,
            "signed_gamma": signed_gamma if all_rows_signed else None,
            "signed_vanna": signed_vanna if all_rows_signed else None,
            "signed_charm": signed_charm if all_rows_signed else None,
            "hedge_regime": regime,
            "hedge_flow_per_1pct_spot": hedge_flow_per_1pct,
            "liquidity_normalized_impact": impact_ratio,
            "liquidity_denominator": denom,
            "semantics": "Signed hedge feedback is withheld unless every row has verified inventory provenance.",
        },
        "strike_topology": {
            "unsigned_gamma_concentration_zone": gamma_zone,
            "fresh_oi_concentration_zone": oi_zone,
            "gamma_hhi": gamma_hhi,
            "gamma_top_share": gamma_top_share,
            "oi_hhi": oi_hhi,
            "oi_top_share": oi_top_share,
            "pin_break_probability": None,
            "first_passage_probability": None,
            "semantics": "Concentration zones are mechanical references, never guaranteed support, resistance or targets.",
        },
        "forbidden_claims_enforced": [
            "gross_oi_equals_dealer_inventory", "gamma_wall_guaranteed_level",
            "rv_gt_iv_guaranteed_profit", "options_flow_standalone_direction",
        ],
    })
    canonical = json.dumps(base, sort_keys=True, separators=(",", ":"), default=str).encode()
    base["content_sha256"] = hashlib.sha256(canonical).hexdigest()
    return base


def simulate_delta_hedged_option(path: Sequence[float], *, strike: float, maturity_days: int,
                                 implied_vol: float, option_type: str = "call", multiplier: float = 100.0,
                                 stock_spread_bps: float = 0.0, option_spread_bps: float = 0.0,
                                 hedge_every: int = 1) -> dict[str, Any]:
    """Deterministic educational diagnostic for discrete gamma-scalping path dependence.

    The simulation uses a constant-IV Black-Scholes mark and discrete delta hedge.  It is a
    controlled diagnostic, not an execution-ready backtest and never grants promotion.
    """
    prices = [float(x) for x in path if _f(x) is not None and float(x) > 0]
    if len(prices) < 2 or strike <= 0 or maturity_days <= 0 or implied_vol <= 0 or hedge_every < 1:
        raise ValueError("invalid gamma-scalping diagnostic inputs")
    steps = len(prices) - 1
    t0 = maturity_days / 365.0
    option_fair, delta = _bs_price_delta(prices[0], strike, t0, implied_vol, option_type)
    option_ask = option_fair * (1.0 + option_spread_bps / 20_000.0)
    stock_position = -delta * multiplier
    stock_cost = abs(stock_position) * prices[0] * stock_spread_bps / 20_000.0
    cash = -option_ask * multiplier - stock_position * prices[0] - stock_cost
    hedge_cost = stock_cost
    hedge_trades = 1
    for i in range(1, len(prices)):
        remaining = max(0.0, t0 * (1.0 - i / steps))
        _, new_delta = _bs_price_delta(prices[i], strike, remaining, implied_vol, option_type)
        if i < len(prices) - 1 and i % hedge_every == 0:
            new_position = -new_delta * multiplier
            trade = new_position - stock_position
            cost = abs(trade) * prices[i] * stock_spread_bps / 20_000.0
            cash -= trade * prices[i] + cost
            hedge_cost += cost
            stock_position = new_position
            hedge_trades += 1
    final_option, _ = _bs_price_delta(prices[-1], strike, 0.0, implied_vol, option_type)
    pnl = cash + stock_position * prices[-1] + final_option * multiplier
    log_returns = [math.log(prices[i] / prices[i - 1]) for i in range(1, len(prices))]
    realized_vol = pstdev(log_returns) * math.sqrt(252.0 * steps / max(1, maturity_days)) if len(log_returns) >= 2 else 0.0
    return {
        "schema": "warroom.gamma_scalping_diagnostic.v70",
        "pnl": pnl,
        "initial_option_fair": option_fair,
        "option_entry_ask": option_ask,
        "hedge_cost": hedge_cost,
        "hedge_trades": hedge_trades,
        "realized_vol_annualized": realized_vol,
        "implied_vol": implied_vol,
        "terminal_price": prices[-1],
        "standalone_direction": "NONE",
        "predictive_evidence": False,
        "capital_permission": "BLOCKED",
    }
