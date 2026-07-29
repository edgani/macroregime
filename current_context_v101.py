"""Current non-technical market context for War Room OS V10.1.

The collector is intentionally split from the decision engine. It records source identity, acquisition
and freshness. Price is an execution/valuation reference only. It never computes chart indicators.
All providers are optional and failures retain the last valid snapshot as stale context.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import statistics
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE / "runtime" / "v101_current"
UTC = dt.timezone.utc
USER_AGENT = "curl/8.5.0 WarRoomOS/10.1"
MARKETS = ("us", "idx", "crypto", "commodity", "fx")

FRED_SERIES: dict[str, dict[str, str]] = {
    # US macro/liquidity/credit
    "INDPRO": {"market": "us", "role": "growth", "label": "US industrial production"},
    "PAYEMS": {"market": "us", "role": "growth", "label": "US nonfarm payrolls"},
    "CPIAUCSL": {"market": "us", "role": "inflation", "label": "US CPI"},
    "PCEPI": {"market": "us", "role": "inflation", "label": "US PCE price index"},
    "WALCL": {"market": "us", "role": "liquidity", "label": "Federal Reserve total assets"},
    "RRPONTSYD": {"market": "us", "role": "liquidity", "label": "Overnight reverse repo"},
    "WTREGEN": {"market": "us", "role": "liquidity", "label": "Treasury General Account"},
    "DFII10": {"market": "us", "role": "real_rate", "label": "US 10-year real yield"},
    "T10YIE": {"market": "us", "role": "inflation_expectation", "label": "US 10-year breakeven"},
    "BAMLH0A0HYM2": {"market": "us", "role": "credit", "label": "US high-yield OAS"},
    "DFF": {"market": "us", "role": "policy", "label": "Effective federal funds rate"},
    "VIXCLS": {"market": "us", "role": "option_implied_stress", "label": "CBOE VIX close"},
    "DGS2": {"market": "us", "role": "policy", "label": "US 2-year yield"},
    "DGS10": {"market": "us", "role": "policy", "label": "US 10-year yield"},
    "DTWEXBGS": {"market": "fx", "role": "usd", "label": "Trade-weighted US dollar"},
    # FX policy anchors
    "ECBDFR": {"market": "fx", "role": "eur_policy", "label": "ECB deposit facility rate"},
    "IRSTCI01JPM156N": {"market": "fx", "role": "jpy_policy", "label": "Japan short-term interest rate"},
    "IRSTCI01GBM156N": {"market": "fx", "role": "gbp_policy", "label": "United Kingdom short-term interest rate"},
    "IRSTCI01AUM156N": {"market": "fx", "role": "aud_policy", "label": "Australia short-term interest rate"},
    "IRSTCI01CAM156N": {"market": "fx", "role": "cad_policy", "label": "Canada short-term interest rate"},
    # Commodity prices and physical proxies (economic/physical context, not alpha from chart patterns)
    "DCOILWTICO": {"market": "commodity", "role": "wti_spot", "label": "WTI spot price"},
    "PCOPPUSDM": {"market": "commodity", "role": "copper_global", "label": "Global copper price"},
    "PWHEAMTUSDM": {"market": "commodity", "role": "wheat_global", "label": "Global wheat price"},
    # US fiscal channel (reverse-engineered thesis: deficit + debt level pressure long yields)
    "FYFSD": {"market": "us", "role": "fiscal_deficit", "label": "US federal surplus or deficit"},
    "GFDEBTN": {"market": "us", "role": "fiscal_debt", "label": "US federal debt total public debt"},
    "DHHNGSP": {"market": "commodity", "role": "natgas_spot", "label": "Henry Hub natural gas"},
}


def now() -> dt.datetime:
    return dt.datetime.now(UTC)


def iso(value: dt.datetime | None = None) -> str:
    return (value or now()).astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def atomic_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False, default=str), encoding="utf-8")
    os.replace(temp, path)


def read_valid(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        expected = str(data.get("manifest_hash") or "")
        actual = digest({k: v for k, v in data.items() if k != "manifest_hash"})
        return data if len(expected) == 64 and expected == actual else None
    except Exception:
        return None


def get_json(url: str, *, timeout: float = 10.0, headers: Mapping[str, str] | None = None) -> tuple[Any, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json", **dict(headers or {})})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        meta = {
            "http_status": int(getattr(response, "status", 200)),
            "content_type": response.headers.get("Content-Type"),
            "final_url": response.geturl(),
            "latency_ms": round((time.monotonic() - started) * 1000, 2),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
        }
    return json.loads(raw.decode("utf-8")), meta


def get_bytes(url: str, *, timeout: float = 10.0, headers: Mapping[str, str] | None = None) -> tuple[bytes, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", **dict(headers or {})})
    started = time.monotonic()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read()
        meta = {
            "http_status": int(getattr(response, "status", 200)),
            "content_type": response.headers.get("Content-Type"),
            "final_url": response.geturl(),
            "latency_ms": round((time.monotonic() - started) * 1000, 2),
            "raw_sha256": hashlib.sha256(raw).hexdigest(),
        }
    return raw, meta


def _parse_yahoo(payload: Any, meta: dict[str, Any]) -> dict[str, Any]:
    results = (((payload or {}).get("chart") or {}).get("result") or []) if isinstance(payload, dict) else []
    if not results:
        raise ValueError(f"Yahoo returned no result: {((payload or {}).get('chart') or {}).get('error') if isinstance(payload, dict) else None}")
    result = results[0]; md = result.get("meta") or {}
    price = md.get("regularMarketPrice"); stamp = md.get("regularMarketTime")
    if price is None or stamp is None:
        timestamps = result.get("timestamp") or []
        closes = ((((result.get("indicators") or {}).get("quote") or [{}])[0]).get("close") or [])
        candidates = [(int(t), float(v)) for t, v in zip(timestamps, closes) if v is not None and math.isfinite(float(v)) and float(v) > 0]
        if not candidates:
            raise ValueError("Yahoo payload has no positive price")
        stamp, price = candidates[-1]
    record = {
        "price": float(price), "currency": str(md.get("currency") or ""),
        "provider_timestamp": iso(dt.datetime.fromtimestamp(int(stamp), tz=UTC)),
        "provider": "YAHOO_CHART", "source": meta,
        "exchange_name": md.get("exchangeName"), "instrument_type": md.get("instrumentType"),
        "market_state": md.get("marketState"), "predictor_eligible": False,
    }
    return record


def yahoo_quote(symbol: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(symbol, safe="")
    failures: list[str] = []
    for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
        url = f"https://{host}/v8/finance/chart/{encoded}?range=5d&interval=1d&includePrePost=true&events=div%2Csplits"
        try:
            payload, meta = get_json(url, timeout=8.0)
            result = _parse_yahoo(payload, meta); result["source"]["route"] = host
            return result
        except Exception as exc:
            failures.append(f"{host}: {type(exc).__name__}: {exc}")
    raise RuntimeError(" | ".join(failures))


def yahoo_quotes_batch(symbols: list[str], *, chunk_size: int = 40) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    """Batch current quotes via v7/finance/quote (~40 symbols/request).

    Returns (records, errors) keyed by symbol. Per-symbol v8 chart remains the
    fallback for symbols the batch does not return. This cuts per-build Yahoo
    traffic ~70x and is the primary defense against 429 IP throttling.
    """
    records: dict[str, dict[str, Any]] = {}
    errors: dict[str, str] = {}
    for start in range(0, len(symbols), chunk_size):
        chunk = symbols[start:start + chunk_size]
        joined = urllib.parse.quote(",".join(chunk))
        chunk_ok = False
        for host in ("query1.finance.yahoo.com", "query2.finance.yahoo.com"):
            url = f"https://{host}/v7/finance/quote?symbols={joined}"
            try:
                payload, meta = get_json(url, timeout=20.0)
                rows = (((payload or {}).get("quoteResponse") or {}).get("result")) or []
                for q in rows:
                    sym = str(q.get("symbol") or "")
                    price = q.get("regularMarketPrice")
                    stamp = q.get("regularMarketTime")
                    if not sym or price is None or stamp is None:
                        continue
                    try:
                        price = float(price)
                    except (TypeError, ValueError):
                        continue
                    if not math.isfinite(price) or price <= 0:
                        continue
                    records[sym] = {
                        "price": price, "currency": str(q.get("currency") or ""),
                        "provider_timestamp": iso(dt.datetime.fromtimestamp(int(stamp), tz=UTC)),
                        "provider": "YAHOO_QUOTE_BATCH", "source": {**meta, "route": host},
                        "exchange_name": q.get("fullExchangeName") or q.get("exchangeName"),
                        "instrument_type": q.get("instrumentType") or q.get("quoteType"),
                        "market_state": q.get("marketState"), "predictor_eligible": False,
                    }
                chunk_ok = True
                break
            except Exception as exc:
                errors[f"chunk@{start}:{host}"] = f"{type(exc).__name__}: {exc}"
        if not chunk_ok:
            for sym in chunk:
                errors.setdefault(sym, "batch failed on all hosts")
        time.sleep(0.4)  # gentle pacing between chunks
    return records, errors


def binance_quote(symbol: str) -> dict[str, Any]:
    urls = [
        "https://data-api.binance.vision/api/v3/ticker/price?" + urllib.parse.urlencode({"symbol": symbol}),
        "https://api.binance.com/api/v3/ticker/price?" + urllib.parse.urlencode({"symbol": symbol}),
    ]
    failures: list[str] = []
    for url in urls:
        try:
            payload, meta = get_json(url, timeout=8.0)
            price = float(payload["price"])
            if not math.isfinite(price) or price <= 0:
                raise ValueError("non-positive Binance price")
            return {"price": price, "currency": "USDT", "provider_timestamp": iso(), "provider": "BINANCE_SPOT", "source": meta, "predictor_eligible": False}
        except Exception as exc:
            failures.append(f"{type(exc).__name__}: {exc}")
    raise RuntimeError(" | ".join(failures))


def coingecko_quote(symbol: str) -> dict[str, Any]:
    mapping = {"BTCUSDT": "bitcoin", "ETHUSDT": "ethereum", "SOLUSDT": "solana", "BNBUSDT": "binancecoin", "XRPUSDT": "ripple", "ADAUSDT": "cardano", "DOGEUSDT": "dogecoin", "TRXUSDT": "tron", "LINKUSDT": "chainlink", "AVAXUSDT": "avalanche-2"}
    asset = mapping.get(symbol.upper())
    if not asset:
        raise ValueError("CoinGecko mapping missing")
    url = "https://api.coingecko.com/api/v3/simple/price?" + urllib.parse.urlencode({"ids": asset, "vs_currencies": "usd", "include_last_updated_at": "true"})
    payload, meta = get_json(url, timeout=8.0)
    row = payload.get(asset) if isinstance(payload, dict) else None
    if not isinstance(row, dict):
        raise ValueError("CoinGecko asset missing")
    price = float(row["usd"]); stamp = int(row.get("last_updated_at") or int(now().timestamp()))
    return {"price": price, "currency": "USD", "provider_timestamp": iso(dt.datetime.fromtimestamp(stamp, tz=UTC)), "provider": "COINGECKO_CONTEXT", "source": meta, "predictor_eligible": False}


def prioritized_universe(max_symbols: int | None = None) -> dict[str, list[dict[str, Any]]]:
    from bundled_research_reader_v99 import packet_universe, ticker_context_map
    core = json.loads((HERE / "V99_EXECUTION_REFERENCE_UNIVERSE.json").read_text(encoding="utf-8"))
    research = packet_universe(); contexts = ticker_context_map()
    limit = max_symbols or max(20, int(os.getenv("WARROOM_SCAN_MAX_SYMBOLS", "4000")))
    out: dict[str, list[dict[str, Any]]] = {m: [] for m in MARKETS}; seen: dict[str, set[str]] = {m: set() for m in MARKETS}
    for market in MARKETS:
        for row in core.get(market) or []:
            t = str(row.get("instrument") or "")
            if t and t not in seen[market]:
                out[market].append(dict(row)); seen[market].add(t)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for market in MARKETS:
        for row in research.get(market) or []:
            ticker = str(row.get("instrument") or "")
            context = contexts.get(ticker) or contexts.get(ticker + ".JK") or {}
            score = 0
            score += 40 if context.get("chains") else 0
            score += 35 if context.get("bottleneck_reference") else 0
            score += 30 if context.get("idx_groups") else 0
            score += 15 if context.get("alpha_context") else 0
            score += 5 if ticker in {"SPY", "QQQ", "BBCA", "BMRI", "TLKM", "HUMI", "BTCUSDT", "ETHUSDT"} else 0
            scored.append((score, market, dict(row)))
    scored.sort(key=lambda x: (-x[0], x[1], str(x[2].get("instrument"))))
    total = sum(len(v) for v in out.values())
    for _, market, row in scored:
        ticker = str(row.get("instrument") or "")
        if not ticker or ticker in seen[market] or total >= limit:
            continue
        out[market].append(row); seen[market].add(ticker); total += 1

    # Expanded bundled universe (universe_full.json): full IDX list, S&P500+NDX,
    # top-100 crypto, 28 FX pairs, liquid futures. IDX listings misbucketed as
    # US by the research layer are reclassified so quotes resolve via .JK.
    try:
        expanded = (json.loads((HERE / "universe_full.json").read_text(encoding="utf-8")).get("markets")) or {}
    except Exception:
        expanded = {}
    idx_codes = {str(r.get("instrument") or "") for r in expanded.get("idx") or []}
    if idx_codes:
        rebucketed = []
        for row in out["us"]:
            t = str(row.get("instrument") or "")
            if t in idx_codes:
                if t not in seen["idx"] and total < limit:
                    new = dict(row); new["instrument"] = t; new["provider_symbol"] = t + ".JK"; new["provider"] = "YAHOO"; new["asset_type"] = "EQUITY"
                    out["idx"].append(new); seen["idx"].add(t); total += 1
                seen["us"].discard(t)
            else:
                rebucketed.append(row)
        out["us"] = rebucketed
    for market in MARKETS:
        for row in expanded.get(market) or []:
            t = str(row.get("instrument") or "")
            if t and t not in seen[market] and total < limit:
                out[market].append(dict(row)); seen[market].add(t); total += 1
    return out


def collect_quotes(output: Path = ROOT / "quotes.json", *, max_symbols: int | None = None, fast: bool = False) -> dict[str, Any]:
    universe = prioritized_universe(max_symbols)
    previous = read_valid(output) or {"markets": {m: {} for m in MARKETS}}
    previous_markets = previous.get("markets") if isinstance(previous.get("markets"), Mapping) else {}
    collected_at = now(); results: dict[str, dict[str, Any]] = {m: {} for m in MARKETS}; failures: list[dict[str, str]] = []

    # Fast-cycle TTL reuse: quotes younger than the TTL are kept as-is instead
    # of refetching the whole universe every 15 minutes (Yahoo 429 defense).
    quote_ttl_hours = max(1.0, float(os.getenv("WARROOM_QUOTE_TTL_HOURS", "6")))
    reused = 0
    tasks: list[tuple[str, dict[str, Any]]] = []
    for m, rows in universe.items():
        for r in rows:
            instrument = str(r.get("instrument") or "")
            old = ((previous_markets.get(m) or {}).get(instrument)) if isinstance(previous_markets, Mapping) else None
            if fast and isinstance(old, Mapping) and old.get("validation") == "VALID_CURRENT_REFERENCE":
                try:
                    received = dt.datetime.fromisoformat(str(old.get("received_at") or old.get("provider_timestamp") or "").replace("Z", "+00:00")).astimezone(UTC)
                    if (collected_at - received).total_seconds() < quote_ttl_hours * 3600:
                        results[m][instrument] = dict(old); reused += 1
                        continue
                except Exception:
                    pass
            tasks.append((m, r))

    # Batch-first for YAHOO providers: ~7 requests instead of ~270.
    yahoo_tasks = [(m, r) for m, r in tasks if str(r.get("provider") or "YAHOO").upper() != "BINANCE"]
    batch_records: dict[str, dict[str, Any]] = {}
    if yahoo_tasks:
        symbol_map = {str(r.get("provider_symbol") or r.get("instrument")): (m, r) for m, r in yahoo_tasks}
        batch_records, batch_errors = yahoo_quotes_batch(sorted(symbol_map))
        for sym, err in batch_errors.items():
            if sym in symbol_map:
                failures.append({"market": symbol_map[sym][0], "instrument": str(symbol_map[sym][1].get("instrument") or ""), "error": f"batch: {err}"})

    def fetch(market: str, row: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None, str | None]:
        instrument = str(row.get("instrument") or ""); symbol = str(row.get("provider_symbol") or instrument); provider = str(row.get("provider") or "YAHOO").upper()
        try:
            if provider == "BINANCE":
                try: record = binance_quote(symbol)
                except Exception as first:
                    record = coingecko_quote(symbol); record["fallback_reason"] = f"Binance failed: {type(first).__name__}: {first}"
            else:
                record = batch_records.get(symbol) or yahoo_quote(symbol)
            provider_time = dt.datetime.fromisoformat(str(record["provider_timestamp"]).replace("Z", "+00:00")).astimezone(UTC)
            record.update({
                "instrument": instrument, "provider_symbol": symbol, "asset_type": row.get("asset_type"),
                "received_at": iso(collected_at), "age_seconds_at_collection": round(max(0.0, (collected_at - provider_time).total_seconds()), 2),
                "validation": "VALID_CURRENT_REFERENCE", "capital_eligible": False,
            })
            record["record_hash"] = digest({k: v for k, v in record.items() if k != "record_hash"})
            return market, instrument, record, None
        except Exception as exc:
            return market, instrument, None, f"{type(exc).__name__}: {exc}"

    # Every task goes through fetch() for uniform enrichment; batch-covered
    # symbols short-circuit on batch_records without any network call, so only
    # batch-missed and BINANCE symbols actually hit the network.
    remaining = tasks
    workers = min(max(1, int(os.getenv("WARROOM_QUOTE_WORKERS", "10"))), 16)
    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_map = [pool.submit(fetch, m, dict(r)) for m, r in remaining]
        for future in as_completed(future_map):
            market, instrument, record, error = future.result()
            if record is not None:
                results[market][instrument] = record
            else:
                failures.append({"market": market, "instrument": instrument, "error": str(error)})
                old = ((previous_markets.get(market) or {}).get(instrument)) if isinstance(previous_markets, Mapping) else None
                if isinstance(old, Mapping) and float(old.get("price") or 0) > 0:
                    stale = dict(old); stale.update({"validation": "STALE_LAST_KNOWN_REFERENCE", "last_refresh_attempt_at": iso(collected_at), "refresh_error": error, "capital_eligible": False})
                    stale["record_hash"] = digest({k: v for k, v in stale.items() if k != "record_hash"})
                    results[market][instrument] = stale
    for market in results:
        results[market] = dict(sorted(results[market].items()))
    payload: dict[str, Any] = {
        "schema": "warroom.v101.current_quotes.v1", "generated_at": iso(collected_at), "markets": results,
        "failures": sorted(failures, key=lambda x: (x["market"], x["instrument"])),
        "quote_count": sum(len(x) for x in results.values()),
        "fresh_quote_count": sum(row.get("validation") == "VALID_CURRENT_REFERENCE" for rows in results.values() for row in rows.values()),
        "markets_with_quote": sum(bool(x) for x in results.values()),
        "markets_with_fresh_quote": sum(any(r.get("validation") == "VALID_CURRENT_REFERENCE" for r in rows.values()) for rows in results.values()),
        "universe_count": sum(len(x) for x in universe.values()), "predictor_eligible": False,
        "claim_limit": "Current prices are valuation/execution references only; no chart-derived signal is calculated.",
    }
    payload["manifest_hash"] = digest({k: v for k, v in payload.items() if k != "manifest_hash"}); atomic_json(output, payload); return payload


def _fred_series(series_id: str) -> tuple[str, dict[str, Any] | None, str | None]:
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={urllib.parse.quote(series_id)}"
    raw = None; meta: dict[str, Any] = {}; last_exc: Exception | None = None
    for attempt in range(3):
        try:
            raw, meta = get_bytes(url, timeout=30.0)
            break
        except Exception as exc:  # noqa: PERF203 - retry whole fetch on timeout/throttle
            last_exc = exc
            time.sleep(2.0 * (attempt + 1))
    if raw is None:
        return series_id, None, f"{type(last_exc).__name__}: {last_exc}"
    try:
        frame = pd.read_csv(io.BytesIO(raw))
        if frame.shape[1] < 2:
            raise ValueError("malformed FRED CSV")
        frame = frame.iloc[:, :2].copy(); frame.columns = ["date", "value"]
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce"); frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        frame = frame.dropna().sort_values("date")
        if frame.empty:
            raise ValueError("empty FRED series")
        values = frame["value"].tolist(); dates = frame["date"].tolist()
        latest = float(values[-1]); prev = float(values[-2]) if len(values) > 1 else None
        def ago(n: int) -> float | None:
            return float(values[-1-n]) if len(values) > n else None
        row = {
            "series_id": series_id, **FRED_SERIES[series_id], "value": latest, "previous": prev,
            "change_1": latest - prev if prev is not None else None,
            "change_3": latest - ago(3) if ago(3) is not None else None,
            "change_12": latest - ago(12) if ago(12) is not None else None,
            "pct_change_3": (latest / ago(3) - 1.0) if ago(3) not in {None, 0} else None,
            "pct_change_12": (latest / ago(12) - 1.0) if ago(12) not in {None, 0} else None,
            "observation_timestamp": pd.Timestamp(dates[-1]).isoformat(), "collected_at": iso(), "source": meta,
            "point_in_time_eligible": False, "availability_semantics": "Current-vintage context; historical proof requires vintages/available_at.",
        }
        return series_id, row, None
    except Exception as exc:
        return series_id, None, f"{type(exc).__name__}: {exc}"


def collect_macro(output: Path = ROOT / "macro.json", *, ttl_hours: float | None = None) -> dict[str, Any]:
    previous = read_valid(output) or {}
    # FRED series are daily/monthly — refetching every 15 minutes is pure
    # throttle pressure. Skip the fetch when the manifest is fresh enough.
    ttl = ttl_hours if ttl_hours is not None else max(1.0, float(os.getenv("WARROOM_MACRO_TTL_HOURS", "12")))
    if isinstance(previous.get("series"), Mapping) and previous.get("series"):
        try:
            generated = dt.datetime.fromisoformat(str(previous.get("generated_at") or "").replace("Z", "+00:00")).astimezone(UTC)
            if (now() - generated).total_seconds() < ttl * 3600:
                return previous
        except Exception:
            pass
    old_rows = previous.get("series") if isinstance(previous.get("series"), Mapping) else {}
    rows: dict[str, Any] = {}; failures: list[dict[str, str]] = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(_fred_series, sid) for sid in FRED_SERIES]
        for f in as_completed(futures):
            sid, row, error = f.result()
            if row: rows[sid] = row
            else:
                failures.append({"series_id": sid, "error": str(error)})
                if isinstance(old_rows.get(sid), Mapping):
                    stale = dict(old_rows[sid]); stale["state"] = "STALE_LAST_KNOWN"; stale["refresh_error"] = error; rows[sid] = stale
    payload: dict[str, Any] = {
        "schema": "warroom.v101.current_macro.v1", "generated_at": iso(), "series": dict(sorted(rows.items())),
        "series_count": len(rows), "failures": sorted(failures, key=lambda x: x["series_id"]),
        "claim_limit": "Current-vintage macro/physical observations are research context, not reconstructed historical release evidence.",
    }
    payload["manifest_hash"] = digest({k: v for k, v in payload.items() if k != "manifest_hash"}); atomic_json(output, payload); return payload


def _series_value(frame: pd.DataFrame | None, names: Iterable[str], *, sum_four: bool = False) -> float | None:
    if frame is None or frame.empty:
        return None
    for name in names:
        if name in frame.index:
            values = pd.to_numeric(frame.loc[name], errors="coerce").dropna()
            if values.empty: continue
            count = min(4, len(values)) if sum_four else 1
            value = float(values.iloc[:count].sum() if sum_four else values.iloc[0])
            return value if math.isfinite(value) else None
    return None


def _quarter_growth(frame: pd.DataFrame | None, names: Iterable[str]) -> float | None:
    if frame is None or frame.empty:
        return None
    for name in names:
        if name in frame.index:
            values = pd.to_numeric(frame.loc[name], errors="coerce").dropna()
            if len(values) >= 5 and float(values.iloc[4]) != 0:
                return float(values.iloc[0] / values.iloc[4] - 1.0)
    return None


def _fundamental_one(market: str, instrument: str, symbol: str) -> tuple[str, str, dict[str, Any] | None, str | None]:
    try:
        import yfinance as yf  # optional, installed by SETUP_V100
        ticker = yf.Ticker(symbol)
        income = ticker.quarterly_income_stmt
        cashflow = ticker.quarterly_cashflow
        balance = ticker.quarterly_balance_sheet
        fast = dict(ticker.fast_info or {})
        revenue = _series_value(income, ("Total Revenue", "Operating Revenue"), sum_four=True)
        net_income = _series_value(income, ("Net Income", "Net Income Common Stockholders"), sum_four=True)
        operating_income = _series_value(income, ("Operating Income",), sum_four=True)
        ocf = _series_value(cashflow, ("Operating Cash Flow", "Total Cash From Operating Activities"), sum_four=True)
        capex = _series_value(cashflow, ("Capital Expenditure", "Capital Expenditures"), sum_four=True)
        fcf = _series_value(cashflow, ("Free Cash Flow",), sum_four=True)
        if fcf is None and ocf is not None and capex is not None:
            fcf = ocf + capex if capex < 0 else ocf - capex
        cash = _series_value(balance, ("Cash Cash Equivalents And Short Term Investments", "Cash And Cash Equivalents", "Cash"))
        debt = _series_value(balance, ("Total Debt", "Long Term Debt And Capital Lease Obligation"))
        equity = _series_value(balance, ("Stockholders Equity", "Total Stockholder Equity"))
        shares = fast.get("shares") or fast.get("shares_outstanding")
        price = fast.get("last_price") or fast.get("lastPrice")
        market_cap = fast.get("market_cap") or fast.get("marketCap")
        shares = float(shares) if shares is not None and math.isfinite(float(shares)) else None
        price = float(price) if price is not None and math.isfinite(float(price)) else None
        market_cap = float(market_cap) if market_cap is not None and math.isfinite(float(market_cap)) else (price * shares if price and shares else None)
        row = {
            "market": market, "instrument": instrument, "provider_symbol": symbol, "provider": "YFINANCE_CURRENT_FILINGS_ADAPTER",
            "collected_at": iso(), "revenue_ttm": revenue, "net_income_ttm": net_income, "operating_income_ttm": operating_income,
            "operating_cash_flow_ttm": ocf, "capex_ttm": capex, "free_cash_flow_ttm": fcf,
            "cash": cash, "total_debt": debt, "stockholders_equity": equity, "shares_outstanding": shares,
            "provider_price": price, "market_cap": market_cap,
            "revenue_yoy": _quarter_growth(income, ("Total Revenue", "Operating Revenue")),
            "net_income_yoy": _quarter_growth(income, ("Net Income", "Net Income Common Stockholders")),
            "filing_semantics": "Latest provider-normalized public financial statements. Current research input; not historical point-in-time proof.",
            "predictor_domain": "fundamentals", "technical_features": 0,
        }
        if not any(row.get(k) is not None for k in ("revenue_ttm", "net_income_ttm", "free_cash_flow_ttm", "market_cap")):
            raise ValueError("no usable current fundamental fields")
        row["record_hash"] = digest({k: v for k, v in row.items() if k != "record_hash"})
        return market, instrument, row, None
    except Exception as exc:
        return market, instrument, None, f"{type(exc).__name__}: {exc}"


def collect_fundamentals(output: Path = ROOT / "fundamentals.json", *, max_equities: int | None = None) -> dict[str, Any]:
    previous = read_valid(output) or {}; old = previous.get("markets") if isinstance(previous.get("markets"), Mapping) else {}
    universe = prioritized_universe(max_symbols=max_equities or int(os.getenv("WARROOM_FUNDAMENTAL_MAX_SYMBOLS", "60")))
    tasks: list[tuple[str, str, str]] = []
    for market in ("us", "idx"):
        for row in universe.get(market) or []:
            if "EQUITY" not in str(row.get("asset_type") or "") and market == "us" and str(row.get("instrument")) in {"SPY", "QQQ"}:
                continue
            tasks.append((market, str(row["instrument"]), str(row.get("provider_symbol") or row["instrument"])))
    markets: dict[str, dict[str, Any]] = {m: {} for m in ("us", "idx")}; failures: list[dict[str, str]] = []
    workers = min(6, max(1, int(os.getenv("WARROOM_FUNDAMENTAL_WORKERS", "4"))))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_fundamental_one, *task) for task in tasks]
        for future in as_completed(futures):
            market, instrument, row, error = future.result()
            if row: markets[market][instrument] = row
            else:
                failures.append({"market": market, "instrument": instrument, "error": str(error)})
                prior = ((old.get(market) or {}).get(instrument)) if isinstance(old, Mapping) else None
                if isinstance(prior, Mapping):
                    stale = dict(prior); stale["state"] = "STALE_LAST_KNOWN"; stale["refresh_error"] = error; markets[market][instrument] = stale
    payload: dict[str, Any] = {
        "schema": "warroom.v101.current_fundamentals.v1", "generated_at": iso(), "markets": markets,
        "record_count": sum(len(v) for v in markets.values()), "failures": sorted(failures, key=lambda x: (x["market"], x["instrument"])),
        "technical_features": 0, "claim_limit": "Current normalized public financials; no historical point-in-time proof is inferred.",
    }
    payload["manifest_hash"] = digest({k: v for k, v in payload.items() if k != "manifest_hash"}); atomic_json(output, payload); return payload


def collect_crypto_network(output: Path = ROOT / "crypto_network.json") -> dict[str, Any]:
    previous = read_valid(output) or {}; old_assets = previous.get("assets") if isinstance(previous.get("assets"), Mapping) else {}
    assets = ["btc", "eth", "sol", "bnb", "xrp", "ada", "doge", "trx", "link", "avax"]
    end = now(); start = end - dt.timedelta(days=45)
    query = urllib.parse.urlencode({
        "assets": ",".join(assets), "metrics": "PriceUSD,CapMrktCurUSD,SplyCur,FeeTotUSD,RevUSD,TxCnt,AdrActCnt",
        "frequency": "1d", "start_time": start.date().isoformat(), "end_time": end.date().isoformat(), "page_size": 10000,
    })
    try:
        payload, meta = get_json("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?" + query, timeout=30.0)
        rows = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            raise ValueError("Coin Metrics data missing")
        grouped: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            if isinstance(row, dict) and row.get("asset"):
                grouped.setdefault(str(row["asset"]).lower(), []).append(row)
        result: dict[str, Any] = {}
        for asset, values in grouped.items():
            values.sort(key=lambda x: str(x.get("time") or ""))
            latest = values[-1]
            def num(v: Any) -> float | None:
                try:
                    f = float(v); return f if math.isfinite(f) else None
                except Exception: return None
            def series(metric: str) -> list[float]:
                return [x for x in (num(v.get(metric)) for v in values) if x is not None]
            fees = series("FeeTotUSD"); revenue = series("RevUSD"); addresses = series("AdrActCnt"); tx = series("TxCnt")
            def growth(vals: list[float]) -> float | None:
                return vals[-1] / vals[-31] - 1.0 if len(vals) >= 31 and vals[-31] != 0 else None
            result[asset.upper() + "USDT"] = {
                "asset": asset, "collected_at": iso(), "provider": "COIN_METRICS_COMMUNITY", "source": meta,
                "price_usd": num(latest.get("PriceUSD")), "market_cap_usd": num(latest.get("CapMrktCurUSD")), "supply": num(latest.get("SplyCur")),
                "fees_30d_usd": sum(fees[-30:]) if fees else None, "revenue_30d_usd": sum(revenue[-30:]) if revenue else None,
                "active_addresses_latest": addresses[-1] if addresses else None, "active_addresses_30d_growth": growth(addresses),
                "transactions_latest": tx[-1] if tx else None, "transactions_30d_growth": growth(tx),
                "network_value_capture_semantics": "Current public network activity/value-capture context; not proof of token return.",
                "technical_features": 0,
            }
        if not result:
            raise ValueError("no supported Coin Metrics assets returned")
        out: dict[str, Any] = {"schema": "warroom.v101.crypto_network.v1", "generated_at": iso(), "assets": result, "record_count": len(result), "failures": [], "claim_limit": "Network activity and value capture are research inputs; venue leverage and unlock data are separate."}
    except Exception as exc:
        result = {k: {**dict(v), "state": "STALE_LAST_KNOWN", "refresh_error": f"{type(exc).__name__}: {exc}"} for k, v in old_assets.items()} if old_assets else {}
        out = {"schema": "warroom.v101.crypto_network.v1", "generated_at": iso(), "assets": result, "record_count": len(result), "failures": [{"error": f"{type(exc).__name__}: {exc}"}], "claim_limit": "Network collector unavailable; last-known records, if any, remain stale research context."}
    out["manifest_hash"] = digest({k: v for k, v in out.items() if k != "manifest_hash"}); atomic_json(output, out); return out


def _cftc_dataset(dataset: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    query = urllib.parse.urlencode({"$limit": 1000, "$order": "report_date_as_yyyy_mm_dd DESC"})
    payload, meta = get_json(f"https://publicreporting.cftc.gov/resource/{dataset}.json?{query}", timeout=30.0)
    if not isinstance(payload, list): raise ValueError("CFTC response is not a list")
    return [x for x in payload if isinstance(x, dict)], meta


def collect_positioning(output: Path = ROOT / "positioning.json") -> dict[str, Any]:
    previous = read_valid(output) or {}; old = previous.get("datasets") if isinstance(previous.get("datasets"), Mapping) else {}
    datasets: dict[str, Any] = {}; failures: list[dict[str, str]] = []
    for name, dataset in (("disaggregated", "72hh-3qpy"), ("tff", "udgc-27he")):
        try:
            rows, meta = _cftc_dataset(dataset)
            latest_date = max((str(r.get("report_date_as_yyyy_mm_dd") or r.get("report_date") or "") for r in rows), default="")
            latest = [r for r in rows if str(r.get("report_date_as_yyyy_mm_dd") or r.get("report_date") or "") == latest_date]
            datasets[name] = {"provider": "CFTC_PUBLIC_REPORTING", "dataset_id": dataset, "latest_report_date": latest_date, "rows": latest, "row_count": len(latest), "source": meta, "release_lag_semantics": "COT positions are release-lagged and must not be treated as real-time."}
        except Exception as exc:
            failures.append({"dataset": name, "error": f"{type(exc).__name__}: {exc}"})
            if isinstance(old.get(name), Mapping):
                datasets[name] = {**dict(old[name]), "state": "STALE_LAST_KNOWN", "refresh_error": failures[-1]["error"]}
    payload: dict[str, Any] = {"schema": "warroom.v101.positioning.v1", "generated_at": iso(), "datasets": datasets, "failures": failures, "claim_limit": "Release-lagged positioning is an amplification/context input, never a standalone signal."}
    payload["manifest_hash"] = digest({k: v for k, v in payload.items() if k != "manifest_hash"}); atomic_json(output, payload); return payload



def _official_rate_from_html(url: str, label: str, patterns: list[str]) -> dict[str, Any]:
    raw, meta = get_bytes(url, timeout=15.0)
    text = raw.decode("utf-8", errors="ignore")
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean)
    value = None
    for pattern in patterns:
        match = re.search(pattern, clean, flags=re.I)
        if match:
            value = float(match.group(1)); break
    if value is None:
        raise ValueError(f"{label} not found in official page")
    return {"label": label, "value": value, "collected_at": iso(), "source": meta, "point_in_time_eligible": False, "availability_semantics": "Current official policy-rate page; historical proof requires decision-date archive."}

def collect_official_policy_rates(output: Path = ROOT / "official_policy_rates.json") -> dict[str, Any]:
    previous = read_valid(output) or {}; old = previous.get("rates") if isinstance(previous.get("rates"), Mapping) else {}
    rates: dict[str, Any] = {}; failures: list[dict[str, str]] = []
    routes = [
        ("BI_7DRR", "https://www.bi.go.id/en/statistik/indikator/bi-rate.aspx", "Bank Indonesia 7-Day Reverse Repo Rate", [r"BI-Rate.{0,200}?(\d+(?:\.\d+)?)\s*%", r"7 Day RR.{0,200}?(\d+(?:\.\d+)?)\s*%"]),
        ("SNB_POLICY_RATE", "https://www.snb.ch/en/the-snb/mandates-goals/statistics/statistics-pub/current_interest_exchange_rates", "SNB policy rate", [r"SNB policy rate\s*(-?\d+(?:\.\d+)?)\s*%"]),
    ]
    for key, url, label, patterns in routes:
        try: rates[key] = _official_rate_from_html(url, label, patterns)
        except Exception as exc:
            failures.append({"rate": key, "error": f"{type(exc).__name__}: {exc}"})
            if isinstance(old.get(key), Mapping): rates[key] = {**dict(old[key]), "state": "STALE_LAST_KNOWN", "refresh_error": failures[-1]["error"]}
    payload: dict[str, Any] = {"schema":"warroom.v101.official_policy_rates.v1","generated_at":iso(),"rates":rates,"record_count":len(rates),"failures":failures,"claim_limit":"Current policy anchors only; no historical point-in-time proof is inferred."}
    payload["manifest_hash"] = digest({k:v for k,v in payload.items() if k!="manifest_hash"}); atomic_json(output,payload); return payload

def collect_all(*, fast: bool = False) -> dict[str, Any]:
    ROOT.mkdir(parents=True, exist_ok=True)
    quotes = collect_quotes(fast=fast)
    macro = collect_macro()
    crypto = collect_crypto_network()
    positioning = collect_positioning()
    official_policy_rates = collect_official_policy_rates()
    fundamentals = read_valid(ROOT / "fundamentals.json") or {"markets": {"us": {}, "idx": {}}, "record_count": 0, "state": "NOT_REFRESHED_IN_FAST_CYCLE"}
    if not fast:
        fundamentals = collect_fundamentals()
    payload: dict[str, Any] = {
        "schema": "warroom.v101.current_context_manifest.v1", "generated_at": iso(),
        "paths": {"quotes": "runtime/v101_current/quotes.json", "macro": "runtime/v101_current/macro.json", "fundamentals": "runtime/v101_current/fundamentals.json", "crypto_network": "runtime/v101_current/crypto_network.json", "positioning": "runtime/v101_current/positioning.json", "official_policy_rates": "runtime/v101_current/official_policy_rates.json"},
        "counts": {"quotes": quotes.get("quote_count", 0), "fresh_quotes": quotes.get("fresh_quote_count", 0), "macro": macro.get("series_count", 0), "fundamentals": fundamentals.get("record_count", 0), "crypto_network": crypto.get("record_count", 0), "positioning_datasets": len(positioning.get("datasets") or {}), "official_policy_rates": official_policy_rates.get("record_count", 0)},
        "markets_with_current_quote": quotes.get("markets_with_quote", 0), "markets_with_fresh_quote": quotes.get("markets_with_fresh_quote", 0),
        "claim_limit": "Acquisition completeness is not profitability proof. Decision and permission layers remain separate.",
    }
    payload["manifest_hash"] = digest({k: v for k, v in payload.items() if k != "manifest_hash"}); atomic_json(ROOT / "manifest.json", payload); return payload


def load_all() -> dict[str, Any]:
    def load(name: str, fallback: dict[str, Any]) -> dict[str, Any]:
        return read_valid(ROOT / name) or fallback
    return {
        "manifest": load("manifest.json", {}),
        "quotes": load("quotes.json", {"markets": {m: {} for m in MARKETS}, "quote_count": 0}),
        "macro": load("macro.json", {"series": {}, "series_count": 0}),
        "fundamentals": load("fundamentals.json", {"markets": {"us": {}, "idx": {}}, "record_count": 0}),
        "crypto_network": load("crypto_network.json", {"assets": {}, "record_count": 0}),
        "positioning": load("positioning.json", {"datasets": {}}),
        "official_policy_rates": load("official_policy_rates.json", {"rates": {}, "record_count": 0}),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["all", "fast", "quotes", "macro", "fundamentals", "crypto", "positioning", "official_rates", "show"])
    args = parser.parse_args()
    mapping = {"all": lambda: collect_all(fast=False), "fast": lambda: collect_all(fast=True), "quotes": collect_quotes, "macro": collect_macro, "fundamentals": collect_fundamentals, "crypto": collect_crypto_network, "positioning": collect_positioning, "official_rates": collect_official_policy_rates, "show": load_all}
    print(json.dumps(mapping[args.command](), indent=2, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
