"""Resilient, provider-labelled public market observations for EROS.

These feeds are suitable for monitoring, not execution. A price observation never
sets a causal regime state or grants capital permission.
"""

from __future__ import annotations

import csv
import io
import json
import os
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Lock
from typing import Literal
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen
from uuid import uuid4

from pydantic import BaseModel, Field, FiniteFloat

MarketGroup = Literal[
    "US",
    "IHSG",
    "Crypto",
    "FX",
    "Commodities",
    "Rates & Volatility",
]
MARKET_GROUPS = (
    "US",
    "IHSG",
    "Crypto",
    "FX",
    "Commodities",
    "Rates & Volatility",
)
EXPECTED_SYMBOLS_BY_GROUP: dict[str, frozenset[str]] = {
    "US": frozenset({"^GSPC", "^IXIC"}),
    "IHSG": frozenset({"^JKSE"}),
    "Crypto": frozenset({"BTC-USD", "ETH-USD"}),
    "FX": frozenset({"USDIDR", "EURUSD", "USDJPY"}),
    "Commodities": frozenset({"GC=F", "CL=F"}),
    "Rates & Volatility": frozenset({"DGS10", "^VIX"}),
}
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_CACHE_PATH = Path(__file__).resolve().parents[3] / "runtime" / "public_market_snapshot.json"
_CACHE_LOCK = Lock()

YAHOO_INSTRUMENTS: dict[str, tuple[MarketGroup, str]] = {
    "^GSPC": ("US", "S&P 500"),
    "^IXIC": ("US", "Nasdaq Composite"),
    "^JKSE": ("IHSG", "Jakarta Composite"),
    "GC=F": ("Commodities", "Gold futures"),
    "CL=F": ("Commodities", "WTI crude futures"),
    "^VIX": ("Rates & Volatility", "CBOE VIX"),
}

# Canonical FX symbol -> (Yahoo quote symbol, instrument label). Used only when the
# primary Frankfurter/ECB request fails, so a single-provider outage cannot blank FX.
YAHOO_FX_FALLBACK: dict[str, tuple[str, str]] = {
    "USDIDR": ("IDR=X", "USD/IDR"),
    "EURUSD": ("EURUSD=X", "EUR/USD"),
    "USDJPY": ("JPY=X", "USD/JPY"),
}

RequestBytes = Callable[[str], bytes]
Sleep = Callable[[float], None]


class MarketPoint(BaseModel):
    """One provider-sourced point retained for short live market paths."""

    observed_at: str
    value: FiniteFloat


class MarketObservation(BaseModel):
    """One provider-labelled market observation with explicit freshness state."""

    market_group: MarketGroup
    instrument: str
    symbol: str
    value: FiniteFloat
    currency: str
    change_pct: FiniteFloat | None = None
    observed_at: str
    fetched_at: str
    provider: str
    status: Literal["LIVE", "STALE"]
    history: list[MarketPoint] = Field(default_factory=list)


class MarketSnapshot(BaseModel):
    """Cross-market public-data result; provider failures remain visible."""

    fetched_at: str
    observations: list[MarketObservation] = Field(default_factory=list)
    failures: dict[str, str] = Field(default_factory=dict)


def _load_cache(path: Path | None) -> MarketSnapshot | None:
    if path is None or not path.exists():
        return None
    try:
        with _CACHE_LOCK:
            content = path.read_text(encoding="utf-8")
        return MarketSnapshot.model_validate_json(content)
    except (OSError, ValueError):
        return None


def _write_cache(path: Path | None, snapshot: MarketSnapshot) -> str | None:
    if path is None or not snapshot.observations:
        return None
    temporary: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
        with _CACHE_LOCK:
            temporary.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
            os.replace(temporary, path)
    except OSError as exc:
        return f"{type(exc).__name__}: {exc}"
    finally:
        if temporary is not None:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
    return None


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _request_with_retry(
    request: RequestBytes,
    url: str,
    *,
    attempts: int = 3,
    sleep: Sleep = time.sleep,
) -> bytes:
    """Retry transient provider transport failures with bounded exponential backoff."""

    if attempts < 1:
        raise ValueError("attempts must be at least one")
    for attempt in range(attempts):
        try:
            return request(url)
        except HTTPError as exc:
            if exc.code != 429 and not 500 <= exc.code < 600:
                raise
            error: OSError = exc
        except OSError as exc:
            error = exc
        if attempt == attempts - 1:
            raise error
        sleep(0.25 * (2**attempt))
    raise RuntimeError("unreachable retry state")


def _request_once(url: str) -> bytes:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) EROS/3.0",
            "Accept": "application/json,text/csv,*/*",
        },
    )
    with urlopen(request, timeout=12) as response:
        data: bytes = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise ValueError("Provider response exceeds 5 MiB safety limit")
    return data


def _default_request(url: str) -> bytes:
    return _request_with_retry(_request_once, url)


def _freshness_status(
    observed_at: datetime,
    now: datetime,
    market_group: MarketGroup,
    *,
    allowed_completed_business_dates: int = 0,
) -> Literal["LIVE", "STALE"]:
    age_hours = (now - observed_at).total_seconds() / 3600
    if age_hours < -(5 / 60):
        return "STALE"
    if market_group == "Crypto":
        return "LIVE" if age_hours <= 3 else "STALE"

    completed_business_dates = 0
    cursor = observed_at.date() + timedelta(days=1)
    while cursor < now.date():
        if cursor.weekday() < 5:
            completed_business_dates += 1
        cursor += timedelta(days=1)
    # Holidays are not assumed without an exchange calendar. The conservative fallback
    # can mark a holiday-delayed observation stale, but never promotes an older session.
    return (
        "LIVE"
        if completed_business_dates <= allowed_completed_business_dates
        else "STALE"
    )


def _yahoo_observation(
    symbol: str,
    market_group: MarketGroup,
    instrument: str,
    request: RequestBytes,
    now: datetime,
) -> MarketObservation:
    encoded = quote(symbol, safe="")
    url = f"https://query2.finance.yahoo.com/v8/finance/chart/{encoded}?range=5d&interval=1d"
    payload = json.loads(request(url))
    result = payload["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    valid = [
        (timestamp, float(close))
        for timestamp, close in zip(timestamps, closes, strict=True)
        if close
    ]
    if not valid:
        raise ValueError(f"No usable close for {symbol}")
    observed_at = datetime.fromtimestamp(valid[-1][0], tz=UTC)
    previous = valid[-2][1] if len(valid) > 1 else None
    change_pct = None if previous is None or previous == 0 else (valid[-1][1] / previous - 1) * 100
    history = [
        MarketPoint(
            observed_at=_iso(datetime.fromtimestamp(timestamp, tz=UTC)),
            value=close,
        )
        for timestamp, close in valid
    ]
    return MarketObservation(
        market_group=market_group,
        instrument=instrument,
        symbol=symbol,
        value=valid[-1][1],
        currency=str(result.get("meta", {}).get("currency") or "UNKNOWN"),
        change_pct=change_pct,
        observed_at=_iso(observed_at),
        fetched_at=_iso(now),
        provider="Yahoo Finance chart",
        status=_freshness_status(observed_at, now, market_group),
        history=history,
    )


def _fetch_yahoo(
    request: RequestBytes, now: datetime
) -> tuple[list[MarketObservation], dict[str, str]]:
    observations: list[MarketObservation] = []
    failures: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(YAHOO_INSTRUMENTS)) as pool:
        futures = {
            pool.submit(_yahoo_observation, symbol, group, instrument, request, now): symbol
            for symbol, (group, instrument) in YAHOO_INSTRUMENTS.items()
        }
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                observations.append(future.result())
            except Exception as exc:
                failures[f"Yahoo {symbol}"] = f"{type(exc).__name__}: {exc}"
    return observations, failures


def _fetch_crypto(request: RequestBytes, now: datetime) -> list[MarketObservation]:
    url = (
        "https://api.coingecko.com/api/v3/simple/price"
        "?ids=bitcoin,ethereum&vs_currencies=usd"
        "&include_24hr_change=true&include_last_updated_at=true"
    )
    payload = json.loads(request(url))
    instruments = {
        "bitcoin": ("Bitcoin", "BTC-USD"),
        "ethereum": ("Ethereum", "ETH-USD"),
    }
    observations = []
    for key, (instrument, symbol) in instruments.items():
        row = payload[key]
        observed_at = datetime.fromtimestamp(int(row["last_updated_at"]), tz=UTC)
        observations.append(
            MarketObservation(
                market_group="Crypto",
                instrument=instrument,
                symbol=symbol,
                value=float(row["usd"]),
                currency="USD",
                change_pct=float(row["usd_24h_change"]),
                observed_at=_iso(observed_at),
                fetched_at=_iso(now),
                provider="CoinGecko public API",
                status=_freshness_status(observed_at, now, "Crypto"),
            )
        )
    return observations


def _fetch_fx(request: RequestBytes, now: datetime) -> list[MarketObservation]:
    url = "https://api.frankfurter.app/latest?from=USD&to=IDR,EUR,JPY"
    payload = json.loads(request(url))
    observed_at = datetime.fromisoformat(payload["date"]).replace(tzinfo=UTC)
    rates = payload["rates"]
    rows = (
        ("USD/IDR", "USDIDR", float(rates["IDR"]), "IDR"),
        ("EUR/USD", "EURUSD", 1.0 / float(rates["EUR"]), "USD"),
        ("USD/JPY", "USDJPY", float(rates["JPY"]), "JPY"),
    )
    return [
        MarketObservation(
            market_group="FX",
            instrument=instrument,
            symbol=symbol,
            value=value,
            currency=currency,
            observed_at=_iso(observed_at),
            fetched_at=_iso(now),
            provider="Frankfurter / ECB reference rates",
            status=_freshness_status(observed_at, now, "FX"),
        )
        for instrument, symbol, value, currency in rows
    ]


def _fetch_rates(request: RequestBytes, now: datetime) -> list[MarketObservation]:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS10"
    records = [
        row
        for row in csv.DictReader(io.StringIO(request(url).decode("utf-8")))
        if row.get("DGS10") not in (None, "", ".")
    ]
    if not records:
        raise ValueError("FRED DGS10 returned no usable observation")
    latest = records[-1]
    observed_at = datetime.fromisoformat(latest["observation_date"]).replace(tzinfo=UTC)
    return [
        MarketObservation(
            market_group="Rates & Volatility",
            instrument="US 10Y Treasury yield",
            symbol="DGS10",
            value=float(latest["DGS10"]),
            currency="%",
            observed_at=_iso(observed_at),
            fetched_at=_iso(now),
            provider="FRED / Federal Reserve Board",
            status=_freshness_status(
                observed_at,
                now,
                "Rates & Volatility",
                allowed_completed_business_dates=1,
            ),
        )
    ]


def fetch_public_market_snapshot(
    request: RequestBytes = _default_request,
    now: datetime | None = None,
    cache_path: Path | None = DEFAULT_CACHE_PATH,
) -> MarketSnapshot:
    """Fetch all public market groups with provider-level failure isolation."""
    fetched_at = now or datetime.now(UTC)
    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=UTC)
    observations: list[MarketObservation] = []
    failures: dict[str, str] = {}

    provider_jobs = {
        "Yahoo markets": lambda: _fetch_yahoo(request, fetched_at),
        "CoinGecko crypto": lambda: (_fetch_crypto(request, fetched_at), {}),
        "Frankfurter FX": lambda: (_fetch_fx(request, fetched_at), {}),
        "FRED rates": lambda: (_fetch_rates(request, fetched_at), {}),
    }
    with ThreadPoolExecutor(max_workers=len(provider_jobs)) as pool:
        futures = {pool.submit(job): name for name, job in provider_jobs.items()}
        for future in as_completed(futures):
            name = futures[future]
            try:
                rows, row_failures = future.result()
                observations.extend(rows)
                failures.update(row_failures)
            except Exception as exc:
                failures[name] = f"{type(exc).__name__}: {exc}"

    if "CoinGecko crypto" in failures:
        for symbol, instrument in (("BTC-USD", "Bitcoin"), ("ETH-USD", "Ethereum")):
            try:
                fallback = _yahoo_observation(symbol, "Crypto", instrument, request, fetched_at)
                observations.append(
                    fallback.model_copy(update={"provider": "Yahoo Finance chart fallback"})
                )
            except Exception as exc:
                failures[f"Yahoo crypto fallback {symbol}"] = f"{type(exc).__name__}: {exc}"

    if "Frankfurter FX" in failures:
        for symbol, (yahoo_symbol, instrument) in YAHOO_FX_FALLBACK.items():
            try:
                fallback = _yahoo_observation(
                    yahoo_symbol, "FX", instrument, request, fetched_at
                )
                observations.append(
                    fallback.model_copy(
                        update={
                            "symbol": symbol,
                            "provider": "Yahoo Finance chart fallback",
                        }
                    )
                )
            except Exception as exc:
                failures[f"Yahoo FX fallback {symbol}"] = f"{type(exc).__name__}: {exc}"

    if "FRED rates" in failures:
        try:
            fallback = _yahoo_observation(
                "^TNX", "Rates & Volatility", "US 10Y Treasury yield", request, fetched_at
            )
            observations.append(
                fallback.model_copy(
                    update={
                        "symbol": "DGS10",
                        "currency": "%",
                        "provider": "Yahoo Finance chart fallback",
                    }
                )
            )
        except Exception as exc:
            failures["Yahoo rates fallback ^TNX"] = f"{type(exc).__name__}: {exc}"

    if failures:
        cached = _load_cache(cache_path)
        if cached is not None:
            current_keys = {(item.market_group, item.symbol) for item in observations}
            for item in cached.observations:
                key = (item.market_group, item.symbol)
                if key not in current_keys:
                    observations.append(
                        item.model_copy(
                            update={
                                "status": "STALE",
                                "provider": f"{item.provider} (last good cache)",
                            }
                        )
                    )

    observations.sort(key=lambda item: (MARKET_GROUPS.index(item.market_group), item.instrument))
    snapshot = MarketSnapshot(
        fetched_at=_iso(fetched_at),
        observations=observations,
        failures=failures,
    )
    cache_snapshot = MarketSnapshot(
        fetched_at=snapshot.fetched_at,
        observations=[
            item.model_copy(
                update={"provider": item.provider.removesuffix(" (last good cache)")}
            )
            for item in snapshot.observations
        ],
        failures={},
    )
    cache_failure = _write_cache(cache_path, cache_snapshot)
    if cache_failure is not None:
        snapshot.failures["Last-good cache"] = cache_failure
    return snapshot
