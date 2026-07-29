"""V10.1 prospective shadow outcome recorder.

Matures prospective shadow forecasts recorded by shadow_runner_v101.py:
for every FORECAST that has a SHADOW_FILL, has no OUTCOME yet, and whose
outcome_end has been reached, this recorder fetches realized daily bars from
the same public providers used by the live collectors (Yahoo chart API for
equities/IDX/commodity/FX, Binance klines for crypto), computes
realized_return / max_adverse_excursion / max_favorable_excursion against the
shadow fill price, and appends an OUTCOME record to the append-only
hash-chained ledger.

Honesty rules (fail-closed):
- No price data, insufficient bars, or a stale exit bar -> honest skip with a
  machine-readable reason. Nothing is ever fabricated or interpolated.
- The price evidence used is hashed into outcome_source_hash so every outcome
  is independently reproducible from public data.
- append_outcome() enforces maturity (now >= horizon_end >= outcome_end), so
  backfill of unmatured forecasts is impossible by construction.

Usage:
    python shadow_outcome_recorder_v101.py [--ledger PATH] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Callable, Mapping

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from shadow_execution_ledger_v95 import append_outcome, verify  # noqa: E402

UTC = dt.timezone.utc
LEDGER = HERE / "runtime" / "v101_shadow" / "shadow_ledger.jsonl"
RUN_REPORT = HERE / "runtime" / "v101_shadow" / "last_outcome_run.json"
USER_AGENT = "warroom-outcome-recorder/1.0 (+https://localhost)"
MIN_BARS_DEFAULT = 20
MAX_EXIT_GAP_DAYS_DEFAULT = 10

Fetcher = Callable[[str, str, dt.datetime, dt.datetime], list[dict[str, Any]]]


def _parse(ts: str) -> dt.datetime:
    return dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(UTC)


def _iso(value: dt.datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _http_json(url: str, *, timeout: float = 30.0) -> Any:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310 - public market data only
        return json.loads(response.read().decode("utf-8"))


def fetch_yahoo_daily(symbol: str, start: dt.datetime, end: dt.datetime) -> list[dict[str, Any]]:
    """Daily OHLC bars from the Yahoo chart API (same provider as live quotes)."""
    period1 = int(start.timestamp())
    period2 = int((end + dt.timedelta(days=1)).timestamp())
    query = urllib.parse.urlencode(
        {"period1": period1, "period2": period2, "interval": "1d", "events": "div,splits"}
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}?{query}"
    payload = _http_json(url)
    results = ((payload or {}).get("chart") or {}).get("result") or []
    if not results:
        raise ValueError(f"Yahoo returned no chart result for {symbol}")
    result = results[0]
    timestamps = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    opens, highs, lows, closes = (quote.get(k) or [] for k in ("open", "high", "low", "close"))
    bars: list[dict[str, Any]] = []
    for index, stamp in enumerate(timestamps):
        try:
            o, h, l, c = opens[index], highs[index], lows[index], closes[index]
        except IndexError:
            continue
        if o is None or h is None or l is None or c is None:
            continue
        bars.append(
            {
                "date": dt.datetime.fromtimestamp(stamp, UTC).date().isoformat(),
                "open": float(o),
                "high": float(h),
                "low": float(l),
                "close": float(c),
            }
        )
    if not bars:
        raise ValueError(f"Yahoo returned zero usable daily bars for {symbol}")
    return bars


def fetch_binance_daily(symbol: str, start: dt.datetime, end: dt.datetime) -> list[dict[str, Any]]:
    """Daily OHLC bars from Binance spot klines (same provider as live crypto quotes)."""
    query = urllib.parse.urlencode(
        {
            "symbol": symbol,
            "interval": "1d",
            "startTime": int(start.timestamp() * 1000),
            "endTime": int((end + dt.timedelta(days=1)).timestamp() * 1000),
            "limit": 1000,
        }
    )
    payload = _http_json(f"https://api.binance.com/api/v3/klines?{query}")
    if not isinstance(payload, list):
        raise ValueError(f"Binance returned unexpected klines payload for {symbol}")
    bars = [
        {
            "date": dt.datetime.fromtimestamp(int(row[0]) / 1000, UTC).date().isoformat(),
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
        }
        for row in payload
        if isinstance(row, list) and len(row) >= 5
    ]
    if not bars:
        raise ValueError(f"Binance returned zero usable daily bars for {symbol}")
    return bars


def _universe_provider_symbol(market: str, ticker: str) -> str | None:
    for name in ("V99_EXECUTION_REFERENCE_UNIVERSE.json", "V97_EXECUTION_REFERENCE_UNIVERSE.json"):
        path = HERE / name
        if not path.exists():
            continue
        try:
            universe = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for row in universe.get(market) or []:
            if str(row.get("instrument") or "") == ticker and row.get("provider_symbol"):
                return str(row["provider_symbol"])
    return None


def resolve_provider(market: str, ticker: str) -> tuple[str, str]:
    """Map (market, security_id) to (provider, provider_symbol) for bar fetches."""
    market = str(market or "").lower()
    if market == "crypto":
        return "BINANCE", ticker
    explicit = _universe_provider_symbol(market, ticker)
    if explicit:
        return "YAHOO", explicit
    if market == "idx":
        if ticker.startswith("^") or ticker.endswith(".JK"):
            return "YAHOO", ticker
        return "YAHOO", f"{ticker}.JK"
    return "YAHOO", ticker


def default_fetcher(provider: str, symbol: str, start: dt.datetime, end: dt.datetime) -> list[dict[str, Any]]:
    if provider == "BINANCE":
        return fetch_binance_daily(symbol, start, end)
    return fetch_yahoo_daily(symbol, start, end)


def compute_excursions(
    direction: str, entry: float, bars: list[dict[str, Any]]
) -> tuple[float, float, float, dict[str, Any]]:
    """(realized_return, MAE, MFE, exit_bar) for a filled shadow position.

    LONG:  realized = exit/entry - 1; MAE = min(low)/entry - 1; MFE = max(high)/entry - 1
    SHORT: realized = entry/exit - 1; MAE = entry/max(high) - 1; MFE = entry/min(low) - 1
    MAE is <= 0 on the adverse side by construction; MFE >= 0 on the favorable side.
    """
    ordered = sorted(bars, key=lambda b: b["date"])
    exit_bar = ordered[-1]
    exit_price = float(exit_bar["close"])
    highest = max(float(b["high"]) for b in ordered)
    lowest = min(float(b["low"]) for b in ordered)
    if direction == "SHORT":
        realized = entry / exit_price - 1.0
        mae = entry / highest - 1.0
        mfe = entry / lowest - 1.0
    else:
        realized = exit_price / entry - 1.0
        mae = lowest / entry - 1.0
        mfe = highest / entry - 1.0
    return realized, mae, mfe, exit_bar


def _source_hash(provider: str, symbol: str, bars: list[dict[str, Any]]) -> str:
    canonical = json.dumps(
        {
            "provider": provider,
            "symbol": symbol,
            "interval": "1d",
            "bars": [[b["date"], b["open"], b["high"], b["low"], b["close"]] for b in bars],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def record_outcomes(
    ledger: str | Path = LEDGER,
    *,
    now: dt.datetime | None = None,
    fetcher: Fetcher | None = None,
    min_bars: int = MIN_BARS_DEFAULT,
    max_exit_gap_days: int = MAX_EXIT_GAP_DAYS_DEFAULT,
    dry_run: bool = False,
) -> dict[str, Any]:
    ledger = Path(ledger)
    now = (now or dt.datetime.now(UTC)).astimezone(UTC)
    fetch = fetcher or default_fetcher
    rows = _read_rows(ledger)
    forecasts = {r["forecast_id"]: r for r in rows if r.get("record_type") == "FORECAST"}
    fills = {r["forecast_id"]: r for r in rows if r.get("record_type") == "SHADOW_FILL"}
    outcomes = {r["forecast_id"] for r in rows if r.get("record_type") == "OUTCOME"}

    created: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    pending: list[str] = []

    for forecast_id, forecast in sorted(forecasts.items()):
        if forecast_id in outcomes:
            continue
        fill = fills.get(forecast_id)
        if fill is None:
            skipped.append({"forecast_id": forecast_id, "reason": "NO_SHADOW_FILL"})
            continue
        outcome_end = _parse(forecast["outcome_end"])
        if outcome_end > now:
            pending.append(forecast_id)
            continue

        market = str(forecast.get("market") or "")
        ticker = str(forecast.get("security_id") or "")
        direction = str(forecast.get("direction") or "LONG").upper()
        entry = float(fill.get("price") or 0.0)
        if entry <= 0:
            skipped.append({"forecast_id": forecast_id, "reason": "INVALID_FILL_PRICE"})
            continue
        provider, symbol = resolve_provider(market, ticker)
        window_start = _parse(forecast.get("outcome_start") or forecast["decision_at"])
        try:
            raw_bars = fetch(provider, symbol, window_start, outcome_end)
        except Exception as exc:
            skipped.append(
                {"forecast_id": forecast_id, "reason": f"PROVIDER_DATA_UNAVAILABLE: {type(exc).__name__}: {exc}"}
            )
            continue
        bars = [
            b
            for b in raw_bars
            if window_start.date() <= dt.date.fromisoformat(b["date"]) <= outcome_end.date()
        ]
        if len(bars) < min_bars:
            skipped.append(
                {"forecast_id": forecast_id, "reason": f"INSUFFICIENT_BARS: {len(bars)} < {min_bars}"}
            )
            continue
        realized, mae, mfe, exit_bar = compute_excursions(direction, entry, bars)
        exit_gap_days = (outcome_end.date() - dt.date.fromisoformat(exit_bar["date"])).days
        if exit_gap_days > max_exit_gap_days:
            skipped.append(
                {
                    "forecast_id": forecast_id,
                    "reason": f"EXIT_DATA_GAP: last bar {exit_bar['date']} is {exit_gap_days}d before outcome_end",
                }
            )
            continue

        outcome = {
            "forecast_id": forecast_id,
            "horizon_end": _iso(outcome_end),
            "realized_return": realized,
            "max_adverse_excursion": mae,
            "max_favorable_excursion": mfe,
            "outcome_source_hash": _source_hash(provider, symbol, bars),
            "exit_reason": "HORIZON_REACHED",
            "later_revision_impact": "NONE_RECORDED",
            "exit_reference_price": float(exit_bar["close"]),
            "exit_date": exit_bar["date"],
            "bars_used": len(bars),
            "outcome_provider": provider,
            "outcome_provider_symbol": symbol,
        }
        if not dry_run:
            append_outcome(ledger, outcome, now=now)
        created.append(
            {
                "forecast_id": forecast_id,
                "direction": direction,
                "entry": entry,
                "exit": float(exit_bar["close"]),
                "realized_return": realized,
                "dry_run": dry_run,
            }
        )

    result = {
        "schema": "warroom.v101.shadow_outcome_run.v1",
        "generated_at": _iso(now),
        "ledger": str(ledger),
        "dry_run": dry_run,
        "created": len(created),
        "created_rows": created,
        "skipped": skipped,
        "pending_unmatured": len(pending),
        "verification": verify(ledger),
        "claim_limit": "Prospective shadow outcomes only; not live performance. Capital remains BLOCKED.",
    }
    if not dry_run:
        RUN_REPORT.parent.mkdir(parents=True, exist_ok=True)
        RUN_REPORT.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ledger", default=str(LEDGER))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-bars", type=int, default=MIN_BARS_DEFAULT)
    parser.add_argument("--max-exit-gap-days", type=int, default=MAX_EXIT_GAP_DAYS_DEFAULT)
    args = parser.parse_args()
    result = record_outcomes(
        args.ledger,
        dry_run=args.dry_run,
        min_bars=args.min_bars,
        max_exit_gap_days=args.max_exit_gap_days,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
