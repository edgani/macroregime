from __future__ import annotations

import math
import time
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import requests

INDEX_ALPHA_BASE = "https://api.indexalpha.id"
INVEZGO_BASE = "https://api.invezgo.com"
JAKARTA = ZoneInfo("Asia/Jakarta")

DEFAULT_HEADERS = {
    "Accept": "application/json",
    "User-Agent": "OpportunityIntelligence-IHSG/2.6",
}


def _f(x: Any) -> float:
    try:
        v = float(x)
        return v if math.isfinite(v) else math.nan
    except Exception:
        return math.nan


def _ticker(symbol: str) -> str:
    s = str(symbol or "").strip().upper()
    return s[:-3] if s.endswith(".JK") else s


def _unwrap(payload: Any) -> Any:
    if isinstance(payload, dict):
        if payload.get("success") is False:
            return None
        if "data" in payload:
            return payload.get("data")
    return payload


def _get_json(
    url: str,
    token: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    timeout: float = 8.0,
    session: Any = requests,
) -> Tuple[Any, str]:
    if not token:
        return None, "API key not configured"
    headers = dict(DEFAULT_HEADERS)
    headers["Authorization"] = f"Bearer {token}"
    try:
        r = session.get(url, headers=headers, params=params or {}, timeout=timeout)
        if r.status_code >= 400:
            detail = ""
            try:
                body = r.json()
                detail = str(body.get("message") or body.get("error") or "")
            except Exception:
                detail = r.text[:180]
            return None, f"HTTP {r.status_code}" + (f": {detail}" if detail else "")
        return r.json(), ""
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def effective_eod_date(now: Optional[datetime] = None) -> pd.Timestamp:
    """Latest date likely to have broker attribution available.

    Index Alpha documents EOD refresh around 19:00 Asia/Jakarta. On weekdays before
    19:15 we use the prior business day. Holidays can still return empty and are
    handled fail-closed by the caller.
    """
    now = now or datetime.now(JAKARTA)
    d = pd.Timestamp(now.date())
    if d.weekday() >= 5:
        return d - pd.offsets.BDay(1)
    if (now.hour, now.minute) < (19, 15):
        return d - pd.offsets.BDay(1)
    return d


def recent_business_dates(end: Optional[pd.Timestamp] = None, periods: int = 5) -> List[str]:
    end = pd.Timestamp(end or effective_eod_date()).normalize()
    periods = max(2, min(int(periods), 10))
    return [x.strftime("%Y-%m-%d") for x in pd.bdate_range(end=end, periods=periods)]


def fetch_indexalpha_broker_summary(
    token: str,
    symbol: str,
    from_date: str,
    to_date: str,
    *,
    investor: str = "all",
    market: str = "RG",
    session: Any = requests,
) -> Tuple[List[Dict[str, Any]], str]:
    payload, err = _get_json(
        f"{INDEX_ALPHA_BASE}/stocks/broker-summary",
        token,
        params={
            "ticker": _ticker(symbol),
            "from": from_date,
            "to": to_date,
            "investor": investor,
            "market": market,
        },
        session=session,
    )
    data = _unwrap(payload)
    return (data if isinstance(data, list) else []), err


def fetch_indexalpha_foreign_flow(
    token: str,
    symbol: str,
    from_date: str,
    to_date: str,
    *,
    market: str = "RG",
    session: Any = requests,
) -> Tuple[Dict[str, Any], str]:
    payload, err = _get_json(
        f"{INDEX_ALPHA_BASE}/foreign-flow",
        token,
        params={"ticker": _ticker(symbol), "from": from_date, "to": to_date, "market": market},
        session=session,
    )
    data = _unwrap(payload)
    return (data if isinstance(data, dict) else {}), err


def fetch_invezgo_intraday(
    token: str,
    symbol: str,
    *,
    market: str = "RG",
    session: Any = requests,
) -> Tuple[Dict[str, Any], str]:
    payload, err = _get_json(
        f"{INVEZGO_BASE}/analysis/intraday-data/{_ticker(symbol)}",
        token,
        params={"market": market},
        session=session,
    )
    data = _unwrap(payload)
    if isinstance(data, list) and data:
        data = data[0]
    return (data if isinstance(data, dict) else {}), err


def fetch_invezgo_order_book(
    token: str,
    symbol: str,
    *,
    market: str = "RG",
    session: Any = requests,
) -> Tuple[Dict[str, Any], str]:
    payload, err = _get_json(
        f"{INVEZGO_BASE}/analysis/order-book/{_ticker(symbol)}",
        token,
        params={"market": market},
        session=session,
    )
    data = _unwrap(payload)
    if isinstance(data, list) and data:
        data = data[0]
    return (data if isinstance(data, dict) else {}), err


def fetch_invezgo_queue(
    token: str,
    symbol: str,
    *,
    market: str = "RG",
    session: Any = requests,
) -> Tuple[Any, str]:
    """Fetch raw queue data.

    Queue schemas can vary by endpoint version/package. We intentionally retain the
    raw payload and do not invent a replenishment metric unless the necessary
    executed/outstanding fields are present and tested.
    """
    payload, err = _get_json(
        f"{INVEZGO_BASE}/analysis/queue/{_ticker(symbol)}",
        token,
        params={"market": market},
        session=session,
    )
    return _unwrap(payload), err


def broker_frame(rows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(list(rows or []))
    cols = ["code", "buy_freq", "sell_freq", "buy_volume", "sell_volume", "buy_value", "sell_value", "buy_avg", "sell_avg"]
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan if c != "code" else ""
    if df.empty:
        return df[cols + ["net_value", "net_volume", "gross_value"]]
    for c in cols[1:]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    df["code"] = df["code"].astype(str).str.upper()
    df["net_value"] = df["buy_value"] - df["sell_value"]
    df["net_volume"] = df["buy_volume"] - df["sell_volume"]
    df["gross_value"] = df["buy_value"] + df["sell_value"]
    return df


def _hhi(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").fillna(0).clip(lower=0)
    s = float(x.sum())
    if s <= 0:
        return math.nan
    shares = x / s
    return float((shares * shares).sum())


def _top_share(values: pd.Series, n: int = 3) -> float:
    x = pd.to_numeric(values, errors="coerce").fillna(0).clip(lower=0)
    s = float(x.sum())
    return float(x.nlargest(n).sum() / s) if s > 0 else math.nan


def broker_concentration_metrics(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    df = broker_frame(rows)
    if df.empty:
        return {
            "buyer_hhi": math.nan, "seller_hhi": math.nan, "concentration_edge": math.nan,
            "buyer_top3_share": math.nan, "seller_top3_share": math.nan,
            "top_accumulators": [], "top_distributors": [], "accumulator_cost": math.nan,
            "transfer_intensity_value": math.nan,
        }
    pos = df[df["net_value"] > 0].copy()
    neg = df[df["net_value"] < 0].copy()
    buyer_hhi = _hhi(pos["net_value"]) if not pos.empty else math.nan
    seller_hhi = _hhi((-neg["net_value"])) if not neg.empty else math.nan
    buyer_top3 = _top_share(pos["net_value"]) if not pos.empty else math.nan
    seller_top3 = _top_share((-neg["net_value"])) if not neg.empty else math.nan

    topa = pos.nlargest(5, "net_value")
    topd = neg.nsmallest(5, "net_value")
    # Cost basis is an execution proxy for the brokers currently accumulating, not
    # beneficial-owner inventory cost. Use actual buy value / buy volume.
    bvol = float(topa["buy_volume"].sum()) if not topa.empty else 0.0
    bval = float(topa["buy_value"].sum()) if not topa.empty else 0.0
    cost = bval / bvol if bvol > 0 else math.nan
    transfer = float(pos["net_value"].sum()) if not pos.empty else 0.0
    return {
        "buyer_hhi": buyer_hhi,
        "seller_hhi": seller_hhi,
        "concentration_edge": buyer_hhi - seller_hhi if math.isfinite(buyer_hhi) and math.isfinite(seller_hhi) else math.nan,
        "buyer_top3_share": buyer_top3,
        "seller_top3_share": seller_top3,
        "top_accumulators": topa[["code", "net_value", "net_volume", "buy_avg"]].to_dict("records"),
        "top_distributors": topd[["code", "net_value", "net_volume", "sell_avg"]].to_dict("records"),
        "accumulator_cost": cost,
        "transfer_intensity_value": transfer,
    }


def daily_persistence(daily_rows: Dict[str, Iterable[Dict[str, Any]]]) -> Dict[str, Any]:
    """Directional persistence at broker level, weighted by cumulative inventory change."""
    records: List[Dict[str, Any]] = []
    for date, rows in (daily_rows or {}).items():
        df = broker_frame(rows)
        for _, r in df.iterrows():
            records.append({"date": date, "code": r["code"], "net_value": float(r["net_value"]), "net_volume": float(r["net_volume"])})
    if not records:
        return {
            "buyer_persistence": math.nan, "seller_persistence": math.nan,
            "persistence_edge": math.nan, "persistent_buyer_count": 0, "persistent_seller_count": 0,
        }
    x = pd.DataFrame(records)
    stats = []
    for code, g in x.groupby("code"):
        vals = pd.to_numeric(g["net_value"], errors="coerce").fillna(0.0)
        den = float(vals.abs().sum())
        if den <= 0:
            continue
        cum = float(vals.sum())
        persistence = abs(cum) / den
        stats.append({"code": code, "cum": cum, "abs_cum": abs(cum), "persistence": persistence})
    s = pd.DataFrame(stats)
    if s.empty:
        return {
            "buyer_persistence": math.nan, "seller_persistence": math.nan,
            "persistence_edge": math.nan, "persistent_buyer_count": 0, "persistent_seller_count": 0,
        }

    def weighted(side: pd.DataFrame) -> float:
        if side.empty:
            return math.nan
        w = side["abs_cum"]
        return float(np.average(side["persistence"], weights=w)) if float(w.sum()) > 0 else math.nan

    buyers = s[s["cum"] > 0].nlargest(5, "abs_cum")
    sellers = s[s["cum"] < 0].nlargest(5, "abs_cum")
    bp, sp = weighted(buyers), weighted(sellers)
    return {
        "buyer_persistence": bp,
        "seller_persistence": sp,
        "persistence_edge": bp - sp if math.isfinite(bp) and math.isfinite(sp) else math.nan,
        "persistent_buyer_count": int((buyers["persistence"] >= 0.75).sum()) if not buyers.empty else 0,
        "persistent_seller_count": int((sellers["persistence"] >= 0.75).sum()) if not sellers.empty else 0,
    }


def order_book_metrics(book: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(book, dict) or not book:
        return {"order_book_imbalance": math.nan, "spread_bps": math.nan, "bid_depth": math.nan, "offer_depth": math.nan}

    bid = book.get("bid") or book.get("bids") or []
    offer = book.get("offer") or book.get("offers") or book.get("ask") or book.get("asks") or []

    def level_rows(side: Any, prefix: str) -> List[Tuple[float, float]]:
        out: List[Tuple[float, float]] = []
        if isinstance(side, dict):
            side = [side]
        for obj in side if isinstance(side, list) else []:
            if not isinstance(obj, dict):
                continue
            price, lot = math.nan, math.nan
            for k, v in obj.items():
                lk = str(k).lower()
                if "price" in lk and prefix in lk:
                    price = _f(v)
                if ("lot" in lk or "volume" in lk) and prefix in lk:
                    lot = _f(v)
            if not math.isfinite(price):
                for k, v in obj.items():
                    if "price" in str(k).lower():
                        price = _f(v); break
            if not math.isfinite(lot):
                for k, v in obj.items():
                    if "lot" in str(k).lower() or "volume" in str(k).lower():
                        lot = _f(v); break
            if math.isfinite(price) or math.isfinite(lot):
                out.append((price, lot))
        return out[:10]

    b = level_rows(bid, "bid")
    a = level_rows(offer, "offer")
    bdepth = float(sum(max(0.0, x[1]) for x in b if math.isfinite(x[1])))
    adepth = float(sum(max(0.0, x[1]) for x in a if math.isfinite(x[1])))
    den = bdepth + adepth
    obi = (bdepth - adepth) / den if den > 0 else math.nan
    best_bid = max((x[0] for x in b if math.isfinite(x[0])), default=math.nan)
    best_ask = min((x[0] for x in a if math.isfinite(x[0])), default=math.nan)
    mid = (best_bid + best_ask) / 2 if math.isfinite(best_bid) and math.isfinite(best_ask) else math.nan
    spread = (best_ask - best_bid) / mid * 10000 if math.isfinite(mid) and mid > 0 else math.nan
    return {"order_book_imbalance": obi, "spread_bps": spread, "bid_depth": bdepth, "offer_depth": adepth}


def intraday_metrics(data: Dict[str, Any], book: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    d = dict(data or {})
    close = _f(d.get("close", d.get("last", d.get("price"))))
    prev = _f(d.get("prev", d.get("previous", d.get("previous_close"))))
    ret = close / prev - 1 if math.isfinite(close) and math.isfinite(prev) and prev > 0 else math.nan
    value = _f(d.get("value"))
    volume = _f(d.get("volume"))
    freq = _f(d.get("freq", d.get("frequency")))
    haka = _f(d.get("haka_value", d.get("haka")))
    haki = _f(d.get("haki_value", d.get("haki")))
    aggr = (haka - haki) / (haka + haki) if math.isfinite(haka) and math.isfinite(haki) and (haka + haki) > 0 else math.nan

    ob = order_book_metrics(book or {})
    absorption = math.nan
    absorption_side = "GATED"
    if math.isfinite(aggr) and math.isfinite(ret):
        # Signed flow fights price: strong sell aggression with resilient price -> buy-side
        # absorption; strong buy aggression without price progress -> sell-side absorption.
        if aggr <= -0.20 and ret >= -0.002:
            absorption = min(1.0, abs(aggr) * (1.0 + max(0.0, ret) * 20.0))
            absorption_side = "BUY-SIDE ABSORPTION"
        elif aggr >= 0.20 and ret <= 0.002:
            absorption = min(1.0, abs(aggr) * (1.0 + max(0.0, -ret) * 20.0))
            absorption_side = "SELL-SIDE ABSORPTION"
        else:
            absorption = 0.0
            absorption_side = "NO CLEAR ABSORPTION"

    return {
        "intraday_close": close, "intraday_return": ret, "intraday_value": value,
        "intraday_volume": volume, "intraday_frequency": freq,
        "haka_value": haka, "haki_value": haki, "aggressive_flow_imbalance": aggr,
        "absorption_score": absorption, "absorption_side": absorption_side,
        **ob,
    }


def eod_transaction_snapshot(
    symbol: str,
    token: str,
    *,
    lookback_days: int = 5,
    price: float = math.nan,
    adv_value_20d: float = math.nan,
    session: Any = requests,
) -> Dict[str, Any]:
    if not token:
        return {"eod_status": "GATED · INDEX_ALPHA_API_KEY MISSING", "eod_errors": ["API key not configured"]}

    dates = recent_business_dates(periods=lookback_days)
    daily: Dict[str, List[Dict[str, Any]]] = {}
    errors: List[str] = []
    for d in dates:
        rows, err = fetch_indexalpha_broker_summary(token, symbol, d, d, investor="all", market="RG", session=session)
        if rows:
            daily[d] = rows
        elif err:
            errors.append(f"{d} RG: {err}")

    if not daily:
        return {"eod_status": "GATED · NO BROKER DATA", "eod_errors": errors}

    first, last = min(daily), max(daily)
    # Aggregate locally from single-day calls so persistence and totals use the same PIT records.
    all_rows = []
    for d, rows in daily.items():
        for r in rows:
            rr = dict(r); rr["_date"] = d; all_rows.append(rr)
    # Aggregate broker rows for concentration/cost.
    df = broker_frame(all_rows)
    agg_rows = []
    if not df.empty:
        for code, g in df.groupby("code"):
            bv, sv = float(g["buy_value"].sum()), float(g["sell_value"].sum())
            bvol, svol = float(g["buy_volume"].sum()), float(g["sell_volume"].sum())
            agg_rows.append({
                "code": code, "buy_value": bv, "sell_value": sv,
                "buy_volume": bvol, "sell_volume": svol,
                "buy_freq": float(g["buy_freq"].sum()), "sell_freq": float(g["sell_freq"].sum()),
                "buy_avg": bv / bvol if bvol > 0 else math.nan,
                "sell_avg": sv / svol if svol > 0 else math.nan,
            })

    conc = broker_concentration_metrics(agg_rows)
    pers = daily_persistence(daily)
    ng_rows, ng_err = fetch_indexalpha_broker_summary(token, symbol, first, last, investor="all", market="NG", session=session)
    foreign, ff_err = fetch_indexalpha_foreign_flow(token, symbol, first, last, market="RG", session=session)
    if ng_err:
        errors.append(f"NG: {ng_err}")
    if ff_err:
        errors.append(f"foreign: {ff_err}")

    ng_df = broker_frame(ng_rows)
    rg_transfer = _f(conc.get("transfer_intensity_value"))
    ng_gross = float(ng_df["gross_value"].sum() / 2.0) if not ng_df.empty else 0.0
    denom = max(0.0, rg_transfer) + max(0.0, ng_gross)
    ng_share = ng_gross / denom if denom > 0 else math.nan
    cross_risk = ng_share if math.isfinite(ng_share) else math.nan

    ff_net = _f(foreign.get("net_foreign"))
    ff_buy = _f(foreign.get("foreign_buy"))
    ff_sell = _f(foreign.get("foreign_sell"))
    ff_gross = (ff_buy + ff_sell) if math.isfinite(ff_buy) and math.isfinite(ff_sell) else math.nan
    ff_intensity = ff_net / ff_gross if math.isfinite(ff_net) and math.isfinite(ff_gross) and ff_gross > 0 else math.nan
    rg_adv = rg_transfer / adv_value_20d if math.isfinite(rg_transfer) and math.isfinite(adv_value_20d) and adv_value_20d > 0 else math.nan

    cost = _f(conc.get("accumulator_cost"))
    distance = price / cost - 1 if math.isfinite(price) and math.isfinite(cost) and cost > 0 else math.nan

    return {
        "eod_status": "READY · EOD BROKER ATTRIBUTION",
        "eod_from": first, "eod_to": last, "eod_days": len(daily), "eod_errors": errors,
        **conc, **pers,
        "ng_share": ng_share, "crossing_transfer_risk": cross_risk,
        "foreign_buy": ff_buy, "foreign_sell": ff_sell, "net_foreign": ff_net,
        "foreign_flow_intensity": ff_intensity,
        "transfer_intensity_adv": rg_adv,
        "distance_from_accumulator_cost": distance,
    }


def intraday_transaction_snapshot(
    symbol: str,
    token: str,
    *,
    session: Any = requests,
    include_queue: bool = False,
) -> Dict[str, Any]:
    if not token:
        return {"intraday_status": "GATED · INVEZGO_API_KEY MISSING", "intraday_errors": ["API key not configured"]}

    data, e1 = fetch_invezgo_intraday(token, symbol, session=session)
    book, e2 = fetch_invezgo_order_book(token, symbol, session=session)
    queue, e3 = (fetch_invezgo_queue(token, symbol, session=session) if include_queue else (None, ""))
    errors = [x for x in [e1, e2, e3] if x]
    if not data and not book:
        return {"intraday_status": "GATED · NO INTRADAY DATA", "intraday_errors": errors}
    out = intraday_metrics(data, book)
    out["queue_available"] = bool(queue)
    out["intraday_status"] = "READY · LIVE MICROSTRUCTURE"
    out["intraday_errors"] = errors
    return out


def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x)) if math.isfinite(x) else math.nan


def combine_transaction_layers(
    eod: Dict[str, Any],
    intraday: Dict[str, Any],
    *,
    price: float = math.nan,
) -> Dict[str, Any]:
    """Combine independent evidence without fabricating probability.

    Score is a bounded research state score (0-100), not a calibrated probability.
    Missing inputs reduce coverage rather than being imputed as bullish.
    """
    e = dict(eod or {})
    i = dict(intraday or {})
    out: Dict[str, Any] = {**e, **i}

    evidence: List[Tuple[str, float, float]] = []  # name, signed signal [-1,1], weight

    ce = _f(e.get("concentration_edge"))
    if math.isfinite(ce):
        # HHI edge usually small; 0.15 is already material.
        evidence.append(("broker concentration asymmetry", max(-1.0, min(1.0, ce / 0.15)), 1.1))
    pe = _f(e.get("persistence_edge"))
    if math.isfinite(pe):
        evidence.append(("broker persistence asymmetry", max(-1.0, min(1.0, pe / 0.30)), 1.3))
    ffi = _f(e.get("foreign_flow_intensity"))
    if math.isfinite(ffi):
        evidence.append(("foreign flow", max(-1.0, min(1.0, ffi / 0.20)), 0.8))

    ag = _f(i.get("aggressive_flow_imbalance"))
    if math.isfinite(ag):
        evidence.append(("aggressive trade flow", max(-1.0, min(1.0, ag)), 1.0))
    obi = _f(i.get("order_book_imbalance"))
    if math.isfinite(obi):
        evidence.append(("visible order-book balance", max(-1.0, min(1.0, obi)), 0.45))

    abs_score = _f(i.get("absorption_score"))
    abs_side = str(i.get("absorption_side", ""))
    if math.isfinite(abs_score) and abs_score > 0:
        sign = 1.0 if "BUY-SIDE" in abs_side else (-1.0 if "SELL-SIDE" in abs_side else 0.0)
        evidence.append(("flow/price absorption", sign * min(1.0, abs_score), 1.1))

    # Negotiated-market contamination reduces conviction, never flips direction.
    cross = _f(e.get("crossing_transfer_risk"))
    coverage_weight = sum(w for _, _, w in evidence)
    signed = sum(sig * w for _, sig, w in evidence)
    raw = signed / coverage_weight if coverage_weight > 0 else math.nan
    if math.isfinite(raw) and math.isfinite(cross):
        raw *= (1.0 - min(0.85, max(0.0, cross)))

    score = 50.0 + 50.0 * raw if math.isfinite(raw) else math.nan
    if math.isfinite(score):
        score = max(0.0, min(100.0, score))

    # State labels deliberately separate evidence quality from action.
    if not math.isfinite(score):
        state = "DATA GATED"
    elif cross >= 0.70 if math.isfinite(cross) else False:
        state = "TRANSFER / CROSSING DOMINATED"
    elif score >= 72:
        dist = _f(e.get("distance_from_accumulator_cost"))
        ret = _f(i.get("intraday_return"))
        if math.isfinite(dist) and dist <= 0.10 and (not math.isfinite(ret) or ret <= 0.025):
            state = "STEALTH ACCUMULATION"
        else:
            state = "MARKUP PRESSURE"
    elif score >= 58:
        state = "ACCUMULATION BIAS"
    elif score <= 28:
        state = "DISTRIBUTION"
    elif score <= 42:
        state = "DISTRIBUTION BIAS"
    else:
        state = "NEUTRAL / MIXED"

    source_count = int("READY" in str(e.get("eod_status", ""))) + int("READY" in str(i.get("intraday_status", "")))
    coverage = "HIGH" if source_count == 2 and len(evidence) >= 5 else ("MEDIUM" if source_count >= 1 and len(evidence) >= 2 else "LOW")
    out.update({
        "transaction_score": score,
        "transaction_state": state,
        "transaction_coverage": coverage,
        "transaction_components": [{"name": n, "signal": s, "weight": w} for n, s, w in evidence],
        "transaction_is_probability": False,
    })
    return out


def transaction_evidence_delta(snapshot: Dict[str, Any]) -> Tuple[int, int, str]:
    """Translate transaction state into at most one independent evidence family.

    This prevents transaction microstructure from dominating fundamentals by feature
    multiplication. The family adds one support or one deterioration vote only when
    coverage is MEDIUM/HIGH and the state is directionally strong.
    """
    s = str((snapshot or {}).get("transaction_state", "DATA GATED")).upper()
    cov = str((snapshot or {}).get("transaction_coverage", "LOW")).upper()
    if cov not in {"MEDIUM", "HIGH"}:
        return 0, 0, "IHSG transaction intelligence gated"
    if any(x in s for x in ["STEALTH ACCUMULATION", "MARKUP PRESSURE", "ACCUMULATION BIAS"]):
        return 1, 0, f"IHSG transaction intelligence: {s.lower()}"
    if any(x in s for x in ["DISTRIBUTION"]):
        return 0, 1, f"IHSG transaction intelligence: {s.lower()}"
    if "TRANSFER / CROSSING" in s:
        return 0, 0, "IHSG transaction flow discounted: negotiated/crossing contamination high"
    return 0, 0, f"IHSG transaction intelligence: {s.lower()}"


def transaction_summary_text(snapshot: Dict[str, Any]) -> str:
    s = str((snapshot or {}).get("transaction_state", "DATA GATED"))
    score = _f((snapshot or {}).get("transaction_score"))
    cov = str((snapshot or {}).get("transaction_coverage", "LOW"))
    if not math.isfinite(score):
        return f"{s} · coverage {cov}"
    return f"{s} · {score:.0f}/100 research score · coverage {cov}"
