"""Current execution-reference quote collector for War Room OS V9.7.

Quotes are never used as predictors. They are collected only after a causal decision exists so the
risk engine can reject stale or impossible orders. Every quote records provider time, receive time,
source URL, payload hash and validation state. A failed refresh never turns an old quote into fresh
market data.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from concurrent.futures import ThreadPoolExecutor, as_completed

HERE = Path(__file__).resolve().parent
UNIVERSE_PATH = HERE / "V97_EXECUTION_REFERENCE_UNIVERSE.json"
DEFAULT_OUT = HERE / "runtime" / "v97_trading" / "execution_quotes.json"
UTC = dt.timezone.utc
USER_AGENT = "WarRoomOS/9.7 execution-reference-only"


def _utc_now() -> dt.datetime:
    return dt.datetime.now(UTC)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _get_json(url: str, *, timeout: float = 6.0) -> tuple[Any, dict[str, Any]]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
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


def _yahoo_quote(symbol: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d&includePrePost=true&events=div%2Csplits"
    payload, meta = _get_json(url)
    results = (((payload or {}).get("chart") or {}).get("result") or []) if isinstance(payload, dict) else []
    if not results:
        error = ((payload or {}).get("chart") or {}).get("error") if isinstance(payload, dict) else None
        raise ValueError(f"Yahoo returned no result: {error}")
    result = results[0]
    meta = result.get("meta") or {}
    meta_price = meta.get("regularMarketPrice")
    meta_time = meta.get("regularMarketTime")
    if meta_price is not None and meta_time is not None and math.isfinite(float(meta_price)) and float(meta_price) > 0:
        provider_ts, price = int(meta_time), float(meta_price)
    else:
        timestamps = result.get("timestamp") or []
        quotes = (((result.get("indicators") or {}).get("quote") or [{}])[0])
        closes = quotes.get("close") or []
        candidates = [(int(ts), float(px)) for ts, px in zip(timestamps, closes) if px is not None and math.isfinite(float(px)) and float(px) > 0]
        if not candidates:
            raise ValueError("Yahoo payload contains no positive quote")
        provider_ts, price = candidates[-1]
    currency = str(meta.get("currency") or "")
    return {
        "price": price,
        "currency": currency,
        "provider_timestamp": _iso(dt.datetime.fromtimestamp(provider_ts, tz=UTC)),
        "provider": "YAHOO",
        "source": meta,
    }


def _binance_quote(symbol: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"symbol": symbol})
    # Binance documents data-api.binance.vision as the market-data-only endpoint.
    url = "https://data-api.binance.vision/api/v3/ticker/price?" + query
    payload, meta = _get_json(url)
    if not isinstance(payload, dict) or "price" not in payload:
        raise ValueError("Binance payload missing price")
    price = float(payload["price"])
    if not math.isfinite(price) or price <= 0:
        raise ValueError("Binance price must be positive and finite")
    received = _utc_now()
    return {
        "price": price,
        "currency": "USDT",
        "provider_timestamp": _iso(received),
        "provider": "BINANCE",
        "source": meta,
    }


def collect(*, universe_path: Path = UNIVERSE_PATH, output_path: Path = DEFAULT_OUT) -> dict[str, Any]:
    universe = json.loads(universe_path.read_text(encoding="utf-8"))
    received_at = _utc_now()
    quotes: dict[str, dict[str, Any]] = {m: {} for m in ("us", "idx", "commodity", "fx", "crypto")}
    failures: list[dict[str, str]] = []

    def fetch_one(market: str, row: dict[str, Any]) -> tuple[str, str, dict[str, Any] | None, dict[str, str] | None]:
        instrument = str(row["instrument"]); provider = str(row["provider"]).upper(); symbol = str(row["provider_symbol"])
        try:
            quote = _yahoo_quote(symbol) if provider == "YAHOO" else _binance_quote(symbol) if provider == "BINANCE" else None
            if quote is None:
                raise ValueError(f"unsupported provider: {provider}")
            provider_time = dt.datetime.fromisoformat(str(quote["provider_timestamp"]).replace("Z", "+00:00")).astimezone(UTC)
            age = max(0.0, (received_at - provider_time).total_seconds())
            record = {
                "instrument": instrument, "provider_symbol": symbol, "asset_type": row.get("asset_type"),
                **quote, "received_at": _iso(received_at), "age_seconds_at_collection": round(age, 3),
                "validation": "VALID_EXECUTION_REFERENCE", "predictor_eligible": False, "capital_eligible": False,
            }
            record["record_hash"] = _hash({k: v for k, v in record.items() if k != "record_hash"})
            return market, instrument, record, None
        except Exception as exc:
            return market, instrument, None, {"market": market, "instrument": instrument, "provider": provider, "error": f"{type(exc).__name__}: {exc}"}

    tasks = [(market, dict(row)) for market in quotes for row in (universe.get(market) or [])]
    with ThreadPoolExecutor(max_workers=min(16, max(1, len(tasks)))) as pool:
        futures = [pool.submit(fetch_one, market, row) for market, row in tasks]
        for future in as_completed(futures):
            market, instrument, record, error = future.result()
            if record is not None:
                quotes[market][instrument] = record
            if error is not None:
                failures.append(error)
    for market in quotes:
        quotes[market] = dict(sorted(quotes[market].items()))
    failures.sort(key=lambda x: (x["market"], x["instrument"]))
    payload = {
        "schema": "warroom.v97.execution_quotes.v1", "generated_at": _iso(received_at),
        "universe_hash": hashlib.sha256(universe_path.read_bytes()).hexdigest(), "markets": quotes,
        "failures": failures, "markets_with_quote": sum(bool(quotes[m]) for m in quotes),
        "quote_count": sum(len(rows) for rows in quotes.values()), "proof_status": "EXECUTION_REFERENCE_ONLY",
        "predictor_eligible": False, "capital_permission": "BLOCKED_PENDING_DECISION_AND_RISK_GATE",
    }
    payload["manifest_hash"] = _hash({k: v for k, v in payload.items() if k != "manifest_hash"})
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_suffix(output_path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(payload, indent=2, allow_nan=False), encoding="utf-8")
    os.replace(temp, output_path)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", default=str(UNIVERSE_PATH))
    parser.add_argument("--output", default=str(DEFAULT_OUT))
    args = parser.parse_args()
    print(json.dumps(collect(universe_path=Path(args.universe), output_path=Path(args.output)), indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
