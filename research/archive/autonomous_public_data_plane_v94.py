"""War Room OS V9.4 autonomous public-data acquisition plane.

This module discovers and downloads public/official evidence for all five market
scopes. It never treats a successful download as trading proof. Licensed data,
private account fills, blind outcomes, and elapsed prospective evidence remain
separate gates.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Iterable

UTC = dt.timezone.utc

BANNED_DECISION_TERMS = {
    "sma", "ema", "rsi", "macd", "stochastic", "bollinger", "breakout",
    "moving_average", "vwap_signal", "candlestick", "chart_pattern",
    "price_momentum", "support_resistance",
}

SOURCE_REGISTRY: dict[str, dict[str, Any]] = {
    "us": {
        "scope": "US common stocks and REITs; monthly and filing-event decisions",
        "public_core": [
            {"id": "SEC_COMPANY_TICKERS", "url": "https://www.sec.gov/files/company_tickers.json", "format": "json"},
            {"id": "SEC_SUBMISSIONS_BULK", "url": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip", "format": "zip", "large": True},
            {"id": "SEC_COMPANYFACTS_BULK", "url": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip", "format": "zip", "large": True},
            {"id": "NASDAQ_LISTED", "url": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "format": "text"},
            {"id": "NASDAQ_OTHER_LISTED", "url": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "format": "text"},
            {"id": "NASDAQ_TRADED", "url": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt", "format": "text"},
        ],
        "nonpublic_required_for_full_proof": ["survivor-free historical prices and delistings", "point-in-time expectations history", "actual broker fills"],
    },
    "idx": {
        "scope": "IDX cash equities; long-only until short availability is proven",
        "public_core": [
            {"id": "IDX_STOCK_LIST_PAGE", "url": "https://www.idx.co.id/en/market-data/stocks-data/stock-list/", "format": "browser"},
            {"id": "IDX_COMPANY_PROFILE_ENDPOINT", "url": "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles?emitenType=s&start=0&length=9999", "format": "browser_json"},
            {"id": "IDX_STOCK_SUMMARY_ENDPOINT", "url_template": "https://www.idx.co.id/umbraco/Surface/TradingSummary/GetStockSummary?Length=9999&date={YYYYMMDD}", "format": "browser_json"},
        ],
        "nonpublic_required_for_full_proof": ["historical EOD/log reference bundle", "survivor-free lifecycle and corporate actions", "broker fills"],
        "note": "Cloudflare may require a real browser session; the collector records this as browser-required rather than fabricating data.",
    },
    "commodity": {
        "scope": "WTI, gold, and copper; exact instrument scope recorded per proof receipt",
        "public_core": [
            {"id": "EIA_BULK_MANIFEST", "url": "https://api.eia.gov/bulk/manifest.txt", "format": "text"},
            {"id": "CFTC_DISAGGREGATED", "dataset_id": "72hh-3qpy", "format": "socrata"},
            {"id": "CFTC_TFF", "dataset_id": "udgc-27he", "format": "socrata"},
        ],
        "nonpublic_required_for_full_proof": ["exact futures contract history and roll metadata", "physical basis/freight where applicable", "broker fills"],
    },
    "fx": {
        "scope": "EUR, JPY, GBP, AUD, CAD; exact spot or futures venue locked per model",
        "public_core": [
            {"id": "ALFRED_VINTAGES", "format": "fred_api", "env": "FRED_API_KEY"},
            {"id": "BIS_SDMX", "url": "https://stats.bis.org/api/v2/", "format": "sdmx"},
            {"id": "CFTC_TFF", "dataset_id": "udgc-27he", "format": "socrata"},
        ],
        "nonpublic_required_for_full_proof": ["exact execution venue history", "historical spreads/financing", "broker fills"],
    },
    "crypto": {
        "scope": "BTC and ETH; Binance and Deribit kept venue-specific",
        "public_core": [
            {"id": "BINANCE_PUBLIC_ARCHIVE", "url": "https://data.binance.vision/", "format": "archive"},
            {"id": "DERIBIT_PUBLIC_API", "url": "https://www.deribit.com/api/v2/", "format": "json_rpc"},
            {"id": "COIN_METRICS_COMMUNITY", "url": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics", "format": "json"},
        ],
        "nonpublic_required_for_full_proof": ["historical L2 depth for capacity claims", "account fills", "complete unlock/entity-labelled flow history where used"],
    },
}


class AcquisitionError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")


def download(url: str, destination: Path, *, headers: dict[str, str] | None = None,
             timeout: int = 120, attempts: int = 3) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        temp = destination.with_suffix(destination.suffix + ".part")
        temp.unlink(missing_ok=True)
        try:
            request = urllib.request.Request(url, headers=headers or {})
            with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as output:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
            temp.replace(destination)
            return {
                "url": url,
                "path": str(destination.resolve()),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "downloaded_at": utc_now(),
            }
        except Exception as exc:  # network errors must remain visible in manifest
            last = exc
            temp.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise AcquisitionError(f"{type(last).__name__}: {last}")


def socrata_pages(dataset_id: str, destination: Path, *, app_token: str = "",
                   page_size: int = 50000) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    headers = {"X-App-Token": app_token} if app_token else {}
    offset = 0
    while True:
        query = urllib.parse.urlencode({"$limit": page_size, "$offset": offset})
        url = f"https://publicreporting.cftc.gov/resource/{dataset_id}.json?{query}"
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=180) as response:
            batch = json.loads(response.read().decode("utf-8"))
        if not isinstance(batch, list):
            raise AcquisitionError(f"Malformed Socrata payload for {dataset_id}")
        rows.extend(item for item in batch if isinstance(item, dict))
        if len(batch) < page_size:
            break
        offset += len(batch)
        time.sleep(0.2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
    return {
        "dataset_id": dataset_id,
        "path": str(destination.resolve()),
        "rows": len(rows),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
        "downloaded_at": utc_now(),
    }


def month_range(start: str, end: str) -> Iterable[str]:
    sy, sm = map(int, start.split("-")); ey, em = map(int, end.split("-"))
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13:
            y += 1; m = 1


def collect_us(root: Path, *, include_large_sec: bool) -> dict[str, Any]:
    user_agent = os.getenv("WARROOM_SEC_USER_AGENT", "").strip()
    if not user_agent or "@" not in user_agent:
        return {"status": "BLOCKED_CONFIGURATION", "reason": "WARROOM_SEC_USER_AGENT with contact email is required by SEC fair-access policy"}
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    items = []
    for source in SOURCE_REGISTRY["us"]["public_core"]:
        if source.get("large") and not include_large_sec:
            continue
        suffix = Path(urllib.parse.urlparse(source["url"]).path).name
        try:
            items.append({"id": source["id"], **download(source["url"], root / suffix, headers=headers if source["id"].startswith("SEC_") else {})})
        except Exception as exc:
            items.append({"id": source["id"], "error": f"{type(exc).__name__}: {exc}"})
    return {"status": "COLLECTED_WITH_ERRORS" if any("error" in x for x in items) else "COLLECTED", "items": items}


def collect_idx(root: Path) -> dict[str, Any]:
    # Direct non-browser requests are frequently blocked by Cloudflare. We record the exact
    # browser endpoints and provide a browser-session handoff instead of bypassing controls.
    root.mkdir(parents=True, exist_ok=True)
    handoff = {
        "schema": "warroom.v94.idx_browser_handoff.v1",
        "generated_at": utc_now(),
        "status": "BROWSER_SESSION_REQUIRED",
        "endpoints": SOURCE_REGISTRY["idx"]["public_core"],
        "instruction": "Open the official IDX page in Chrome, export the JSON response from DevTools Network, then import it through V94_BROWSER_EXPORT_IMPORT.py. Do not alter timestamps or rows.",
    }
    path = root / "idx_browser_handoff.json"
    path.write_text(json.dumps(handoff, indent=2), encoding="utf-8")
    return {"status": handoff["status"], "handoff": str(path.resolve()), "sha256": sha256_file(path)}


def collect_commodity(root: Path) -> dict[str, Any]:
    items = []
    try:
        items.append({"id": "EIA_BULK_MANIFEST", **download("https://api.eia.gov/bulk/manifest.txt", root / "eia_bulk_manifest.txt")})
    except Exception as exc:
        items.append({"id": "EIA_BULK_MANIFEST", "error": f"{type(exc).__name__}: {exc}"})
    for dataset_id, name in (("72hh-3qpy", "cftc_disaggregated.json"), ("udgc-27he", "cftc_tff.json")):
        try:
            items.append({"id": dataset_id, **socrata_pages(dataset_id, root / name, app_token=os.getenv("CFTC_APP_TOKEN", ""))})
        except Exception as exc:
            items.append({"id": dataset_id, "error": f"{type(exc).__name__}: {exc}"})
    return {"status": "COLLECTED_WITH_ERRORS" if any("error" in x for x in items) else "COLLECTED", "items": items}


def collect_fx(root: Path, series_ids: list[str]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        items.append({"id": "ALFRED_VINTAGES", "error": "FRED_API_KEY missing"})
    else:
        for series_id in series_ids:
            params = urllib.parse.urlencode({
                "series_id": series_id,
                "api_key": api_key,
                "file_type": "json",
                "output_type": 4,
                "observation_start": "1990-01-01",
            })
            try:
                items.append({"id": f"ALFRED_{series_id}", **download(
                    "https://api.stlouisfed.org/fred/series/observations?" + params,
                    root / "alfred" / f"{series_id}.json",
                )})
            except Exception as exc:
                items.append({"id": f"ALFRED_{series_id}", "error": f"{type(exc).__name__}: {exc}"})
    # The BIS catalog endpoint is lightweight and establishes live API reachability. Exact
    # datasets/keys remain model-scoped and are supplied in config rather than guessed.
    try:
        items.append({"id": "BIS_API_ROOT", **download("https://stats.bis.org/api/v2/", root / "bis_api_root.txt")})
    except Exception as exc:
        items.append({"id": "BIS_API_ROOT", "error": f"{type(exc).__name__}: {exc}"})
    try:
        items.append({"id": "CFTC_TFF", **socrata_pages("udgc-27he", root / "cftc_tff.json", app_token=os.getenv("CFTC_APP_TOKEN", ""))})
    except Exception as exc:
        items.append({"id": "CFTC_TFF", "error": f"{type(exc).__name__}: {exc}"})
    return {"status": "COLLECTED_WITH_ERRORS" if any("error" in x for x in items) else "COLLECTED", "items": items}


def collect_crypto(root: Path, start_month: str, end_month: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for market_path in ("spot", "futures/um"):
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for month in month_range(start_month, end_month):
                if market_path == "spot":
                    rel = f"data/spot/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
                else:
                    rel = f"data/futures/um/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
                try:
                    items.append({"id": f"BINANCE_{market_path}_{symbol}_{month}", **download("https://data.binance.vision/" + rel, root / "binance" / rel, attempts=2)})
                except Exception as exc:
                    items.append({"id": f"BINANCE_{market_path}_{symbol}_{month}", "error": f"{type(exc).__name__}: {exc}"})
    metrics = "PriceUSD,CapMrktCurUSD,SplyCur,FeeTotUSD,RevUSD,TxCnt,AdrActCnt"
    params = urllib.parse.urlencode({"assets": "btc,eth", "metrics": metrics, "frequency": "1d", "start_time": start_month + "-01", "end_time": end_month + "-28", "format": "json"})
    try:
        items.append({"id": "COIN_METRICS_COMMUNITY", **download("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?" + params, root / "coinmetrics_btc_eth.json")})
    except Exception as exc:
        items.append({"id": "COIN_METRICS_COMMUNITY", "error": f"{type(exc).__name__}: {exc}"})
    return {"status": "COLLECTED_WITH_ERRORS" if any("error" in x for x in items) else "COLLECTED", "items": items}


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.output) / dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    root.mkdir(parents=True, exist_ok=False)
    results = {
        "us": collect_us(root / "us", include_large_sec=args.include_large_sec),
        "idx": collect_idx(root / "idx"),
        "commodity": collect_commodity(root / "commodity"),
        "fx": collect_fx(root / "fx", args.fx_series),
        "crypto": collect_crypto(root / "crypto", args.start_month, args.end_month),
    }
    payload = {
        "schema": "warroom.v94.autonomous_public_data_plane.v1",
        "generated_at": utc_now(),
        "source_routes_defined": len(SOURCE_REGISTRY),
        "results": results,
        "proof_status": "PUBLIC_EVIDENCE_ONLY",
        "capital_permission": "BLOCKED",
        "claim_limit": "Downloads and hashes prove source acquisition only; they do not prove prediction, price targets, profit factor, drawdown, or trading readiness.",
    }
    payload["manifest_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    path = root / "v94_public_acquisition_manifest.json"
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    now = dt.datetime.now(UTC)
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runtime/v94_public_acquisition")
    parser.add_argument("--include-large-sec", action="store_true")
    parser.add_argument("--start-month", default=f"{now.year - 2:04d}-{now.month:02d}")
    parser.add_argument("--end-month", default=f"{now.year:04d}-{max(1, now.month - 1):02d}")
    parser.add_argument("--fx-series", nargs="*", default=["DEXUSEU", "DEXJPUS", "DEXUSUK", "DEXUSAL", "DEXCAUS"])
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
