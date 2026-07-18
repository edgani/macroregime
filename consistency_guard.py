from __future__ import annotations
import math

CANONICAL_MARKETS = {"idx": "ihsg", "commodity": "commod"}


def _number(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except Exception:
        return None


def enforce_desk(desk: dict) -> dict:
    """Sanitize locally. One malformed ticker must never erase unrelated valid markets."""
    desk = dict(desk or {})
    meta = desk.setdefault("meta", {})
    warnings, critical, quarantined = [], [], []

    # Canonicalize old internal keys instead of blocking the whole desk.
    markets = dict(desk.get("markets") or {})
    for old, new in CANONICAL_MARKETS.items():
        if old in markets:
            if new in markets:
                warnings.append(f"duplicate market keys {old}/{new}; canonical key retained")
            else:
                markets[new] = markets[old]
            markets.pop(old, None)
            warnings.append(f"market key {old} canonicalized to {new}")
    desk["markets"] = markets

    source = str(meta.get("source") or "NO_DATA").upper()
    if source.startswith("SYNTHETIC") or source in {"NO_DATA", "DATA_UNAVAILABLE"}:
        # Offline data may support engine tests, but never user-facing decisions.
        for market in markets.values():
            market["setups"] = []
            market.setdefault("funnel", {})["setups"] = 0
        desk["alpha"] = []
        desk.setdefault("systemic", {})["rotation_in"] = []
        desk.setdefault("systemic", {})["rotation_out"] = []
        meta["source"] = "DATA_UNAVAILABLE"
        warnings.append("decision outputs withheld because no live/approved data source is available")

    surfaced = set()
    for market_id, market in markets.items():
        clean = []
        for row in market.get("setups") or []:
            ticker = str(row.get("tk") or "").upper()
            if not ticker or ticker == "—":
                clean.append(row)
                continue
            if row.get("valid"):
                entry, stop, target = map(_number, (row.get("e"), row.get("s"), row.get("t")))
                direction = str(row.get("dir") or "").lower()
                geometry_ok = (
                    entry is not None and stop is not None and target is not None and
                    ((direction == "long" and stop < entry < target) or
                     (direction == "short" and target < entry < stop))
                )
                if not geometry_ok:
                    quarantined.append({"market": market_id, "ticker": ticker, "reason": "invalid directional level geometry"})
                    continue
            clean.append(row)
            surfaced.add(ticker)
        market["setups"] = clean
        market.setdefault("funnel", {})["setups"] = len(clean)

    state = desk.get("alpha_foundry") or {}
    for row in state.get("shortlist") or []:
        ticker = str(row.get("ticker") or "").upper()
        if ticker:
            surfaced.add(ticker)
    for row in desk.get("alpha") or []:
        ticker = str(row.get("tk") or "").upper()
        if ticker:
            surfaced.add(ticker)

    systemic = desk.setdefault("systemic", {})
    raw_in = [str(value).upper() for value in systemic.get("rotation_in_raw") or []]
    raw_out = [str(value).upper() for value in systemic.get("rotation_out_raw") or []]
    requested_in = [str(value).upper() for value in systemic.get("rotation_in") or []]
    requested_out = [str(value).upper() for value in systemic.get("rotation_out") or []]
    confirmed_in = [value for value in requested_in if value in surfaced and value in raw_in]
    confirmed_out = [value for value in requested_out if value in surfaced and value in raw_out]
    withheld = sorted(set(requested_in) - set(confirmed_in))
    if withheld:
        warnings.append("Mission rotation names withheld because they are not cross-confirmed: " + ", ".join(withheld))
    systemic["rotation_in"] = confirmed_in
    systemic["rotation_out"] = confirmed_out
    systemic["rotation_unconfirmed"] = sorted(set(raw_in) - set(confirmed_in))

    if quarantined:
        warnings.append(f"{len(quarantined)} malformed setup row(s) quarantined; unaffected outputs retained")
        meta["integrity_state"] = "PARTIAL_QUARANTINE"
    else:
        meta["integrity_state"] = "PASS" if meta.get("source") == "LIVE" else "NO_DECISION_DATA"

    audit = {
        "ok": not critical,
        "critical_errors": critical,
        "errors": critical,
        "warnings": warnings,
        "quarantined_setups": quarantined,
        "quarantined_count": len(quarantined),
        "surfaced_tickers": sorted(surfaced),
    }
    desk["consistency_audit"] = audit
    if critical:
        for market in markets.values():
            market["setups"] = []
            market.setdefault("funnel", {})["setups"] = 0
        desk["alpha"] = []
        systemic["rotation_in"] = []
        systemic["rotation_out"] = []
        meta["source"] = "CONSISTENCY_BLOCKED"
        meta["integrity_state"] = "BLOCKED"
    return desk
