"""War Room OS V9.5 resilient public/official data acquisition.

Acquisition is per source, atomic, hashed, freshness-aware and portable. Missing SEC credentials do
not block Nasdaq collection; an IDX browser handoff is emitted only after a normal official request
fails. Successful acquisition remains evidence only and never grants capital permission.
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
import zipfile
from pathlib import Path
from typing import Any, Iterable

UTC = dt.timezone.utc
DEFAULT_HEADERS = {"User-Agent": "WarRoomOS/9.5 public-data-collector", "Accept": "*/*"}

SOURCE_REGISTRY: dict[str, dict[str, Any]] = {
    "us": {
        "scope": "US common stocks and REITs; monthly and filing-event decisions",
        "sources": [
            {"id": "SEC_COMPANY_TICKERS", "url": "https://www.sec.gov/files/company_tickers.json", "kind": "json", "requires_sec_ua": True},
            {"id": "SEC_SUBMISSIONS_BULK", "url": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip", "kind": "zip", "large": True, "requires_sec_ua": True},
            {"id": "SEC_COMPANYFACTS_BULK", "url": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip", "kind": "zip", "large": True, "requires_sec_ua": True},
            {"id": "NASDAQ_LISTED", "url": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "kind": "text"},
            {"id": "NASDAQ_OTHER_LISTED", "url": "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "kind": "text"},
            {"id": "NASDAQ_TRADED", "url": "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt", "kind": "text"},
        ],
    },
    "idx": {
        "scope": "IDX cash equities; long-only until short availability is proven",
        "sources": [
            {"id": "IDX_COMPANY_PROFILES", "url": "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles?emitenType=s&start=0&length=9999", "kind": "json"},
            {"id": "IDX_STOCK_LIST_PAGE", "url": "https://www.idx.co.id/en/market-data/stocks-data/stock-list/", "kind": "html"},
        ],
    },
    "commodity": {
        "scope": "WTI, gold and copper; instrument locked per receipt",
        "sources": [
            {"id": "EIA_BULK_MANIFEST", "url": "https://api.eia.gov/bulk/manifest.txt", "kind": "json"},
            {"id": "CFTC_DISAGGREGATED", "dataset_id": "72hh-3qpy", "kind": "socrata"},
            {"id": "CFTC_TFF", "dataset_id": "udgc-27he", "kind": "socrata"},
        ],
    },
    "fx": {
        "scope": "EUR, JPY, GBP, AUD and CAD; venue locked per receipt",
        "sources": [
            {"id": "ALFRED_INITIAL_RELEASE", "kind": "fred", "env": "FRED_API_KEY"},
            {"id": "BIS_DATAFLOW_CATALOG", "url": "https://stats.bis.org/api/v2/dataflow/all/all/latest", "kind": "sdmx"},
            {"id": "CFTC_TFF", "dataset_id": "udgc-27he", "kind": "socrata"},
        ],
    },
    "crypto": {
        "scope": "BTC and ETH; Binance and Deribit venue-specific",
        "sources": [
            {"id": "BINANCE_PUBLIC_ARCHIVE", "url": "https://data.binance.vision/", "kind": "archive"},
            {"id": "DERIBIT_FUNDING", "url": "https://www.deribit.com/api/v2/public/get_funding_rate_history", "kind": "json"},
            {"id": "COIN_METRICS_COMMUNITY", "url": "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics", "kind": "json"},
        ],
    },
}


class AcquisitionError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(UTC).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _validate_payload(path: Path, kind: str) -> dict[str, Any]:
    if path.stat().st_size == 0:
        raise AcquisitionError("empty payload")
    validation: dict[str, Any] = {"kind": kind, "validated": True}
    if kind == "json":
        with path.open("r", encoding="utf-8") as f:
            value = json.load(f)
        validation["root_type"] = type(value).__name__
    elif kind == "zip":
        with zipfile.ZipFile(path) as archive:
            bad = archive.testzip()
            if bad:
                raise AcquisitionError(f"corrupt zip member: {bad}")
            validation["members"] = len(archive.infolist())
    elif kind in {"text", "html", "sdmx"}:
        head = path.read_bytes()[:256]
        if not head.strip():
            raise AcquisitionError("blank text payload")
    return validation


def download(url: str, destination: Path, *, package_root: Path, kind: str,
             headers: dict[str, str] | None = None, timeout: int = 120, attempts: int = 3) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    last: Exception | None = None
    for attempt in range(1, attempts + 1):
        temp = destination.with_suffix(destination.suffix + ".part")
        temp.unlink(missing_ok=True)
        try:
            request = urllib.request.Request(url, headers={**DEFAULT_HEADERS, **(headers or {})})
            with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as out:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    out.write(block)
                metadata = {
                    "http_status": int(getattr(response, "status", 200)),
                    "final_url": response.geturl(),
                    "content_type": response.headers.get("Content-Type"),
                    "etag": response.headers.get("ETag"),
                    "last_modified": response.headers.get("Last-Modified"),
                }
            temp.replace(destination)
            validation = _validate_payload(destination, kind)
            return {
                "url": url,
                "path": _relative(destination, package_root),
                "bytes": destination.stat().st_size,
                "sha256": sha256_file(destination),
                "downloaded_at": utc_now(),
                "metadata": metadata,
                "validation": validation,
                "is_evidence": True,
            }
        except Exception as exc:
            last = exc; temp.unlink(missing_ok=True); destination.unlink(missing_ok=True)
            if attempt < attempts:
                time.sleep(1.5 * attempt)
    raise AcquisitionError(f"{type(last).__name__}: {last}")


def socrata_pages(dataset_id: str, destination: Path, *, package_root: Path, app_token: str = "",
                   page_size: int = 50000, max_rows: int | None = None) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_suffix(destination.suffix + ".part"); temp.unlink(missing_ok=True)
    offset = 0; rows = 0
    headers = {**DEFAULT_HEADERS, **({"X-App-Token": app_token} if app_token else {})}
    try:
        with temp.open("w", encoding="utf-8") as out:
            while True:
                limit = page_size if max_rows is None else min(page_size, max_rows - rows)
                if limit <= 0:
                    break
                query = urllib.parse.urlencode({"$limit": limit, "$offset": offset, "$order": ":id"})
                url = f"https://publicreporting.cftc.gov/resource/{dataset_id}.json?{query}"
                request = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(request, timeout=180) as response:
                    batch = json.loads(response.read().decode("utf-8"))
                if not isinstance(batch, list):
                    raise AcquisitionError("malformed Socrata payload")
                for row in batch:
                    if isinstance(row, dict):
                        out.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"); rows += 1
                if len(batch) < limit:
                    break
                offset += len(batch); time.sleep(0.2)
        temp.replace(destination)
        if rows == 0:
            raise AcquisitionError("Socrata returned zero rows")
        return {
            "dataset_id": dataset_id,
            "path": _relative(destination, package_root),
            "rows": rows,
            "bytes": destination.stat().st_size,
            "sha256": sha256_file(destination),
            "downloaded_at": utc_now(),
            "format": "jsonl",
            "is_evidence": True,
        }
    except Exception:
        temp.unlink(missing_ok=True); destination.unlink(missing_ok=True); raise


def month_range(start: str, end: str) -> Iterable[str]:
    sy, sm = map(int, start.split("-")); ey, em = map(int, end.split("-"))
    if not (1 <= sm <= 12 and 1 <= em <= 12) or (sy, sm) > (ey, em):
        raise ValueError("invalid month range")
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m == 13: y += 1; m = 1


def _status(items: list[dict[str, Any]]) -> str:
    successes = sum(item.get("is_evidence") is True and "sha256" in item for item in items)
    failures = sum("error" in item for item in items)
    if successes and not failures:
        return "COLLECTED"
    if successes:
        return "COLLECTED_WITH_ERRORS"
    return "BLOCKED"


def collect_us(root: Path, package_root: Path, *, include_large_sec: bool) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    sec_ua = os.getenv("WARROOM_SEC_USER_AGENT", "").strip()
    for source in SOURCE_REGISTRY["us"]["sources"]:
        if source.get("large") and not include_large_sec:
            items.append({"id": source["id"], "status": "SKIPPED_LARGE_BY_DEFAULT"}); continue
        if source.get("requires_sec_ua") and (not sec_ua or "@" not in sec_ua):
            items.append({"id": source["id"], "error": "WARROOM_SEC_USER_AGENT with contact email is required"}); continue
        name = Path(urllib.parse.urlparse(source["url"]).path).name
        headers = {"User-Agent": sec_ua, "Accept-Encoding": "gzip, deflate"} if source.get("requires_sec_ua") else {}
        try:
            items.append({"id": source["id"], **download(source["url"], root / name, package_root=package_root, kind=source["kind"], headers=headers)})
        except Exception as exc:
            items.append({"id": source["id"], "error": f"{type(exc).__name__}: {exc}"})
    return {"status": _status(items), "items": items}


def collect_idx(root: Path, package_root: Path) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    headers = {"Accept": "application/json,text/html", "Referer": "https://www.idx.co.id/"}
    for source in SOURCE_REGISTRY["idx"]["sources"]:
        suffix = ".json" if source["kind"] == "json" else ".html"
        try:
            items.append({"id": source["id"], **download(source["url"], root / (source["id"].lower() + suffix), package_root=package_root, kind=source["kind"], headers=headers, attempts=1)})
        except Exception as exc:
            items.append({"id": source["id"], "error": f"{type(exc).__name__}: {exc}"})
    if not any("sha256" in item for item in items):
        handoff = {
            "schema": "warroom.v95.idx_browser_handoff.v1",
            "generated_at": utc_now(),
            "status": "BROWSER_SESSION_REQUIRED",
            "official_sources": SOURCE_REGISTRY["idx"]["sources"],
            "instruction": "Export the unmodified official IDX Network response and import it with IDX_BROWSER_EXPORT_IMPORT_V95.py.",
        }
        path = root / "idx_browser_handoff.json"; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(handoff, indent=2), encoding="utf-8")
        items.append({"id": "IDX_BROWSER_HANDOFF", "status": "CREATED", "path": _relative(path, package_root), "sha256": sha256_file(path), "is_evidence": False})
    return {"status": _status(items), "items": items}


def collect_commodity(root: Path, package_root: Path, *, max_cftc_rows: int | None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    try:
        items.append({"id": "EIA_BULK_MANIFEST", **download("https://api.eia.gov/bulk/manifest.txt", root / "eia_bulk_manifest.json", package_root=package_root, kind="json")})
    except Exception as exc:
        items.append({"id": "EIA_BULK_MANIFEST", "error": f"{type(exc).__name__}: {exc}"})
    for dataset_id, name in (("72hh-3qpy", "cftc_disaggregated.jsonl"), ("udgc-27he", "cftc_tff.jsonl")):
        try:
            items.append({"id": dataset_id, **socrata_pages(dataset_id, root / name, package_root=package_root, app_token=os.getenv("CFTC_APP_TOKEN", ""), max_rows=max_cftc_rows)})
        except Exception as exc:
            items.append({"id": dataset_id, "error": f"{type(exc).__name__}: {exc}"})
    return {"status": _status(items), "items": items}


def collect_fx(root: Path, package_root: Path, series_ids: list[str], *, max_cftc_rows: int | None) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    api_key = os.getenv("FRED_API_KEY", "").strip()
    if not api_key:
        items.append({"id": "ALFRED_INITIAL_RELEASE", "error": "FRED_API_KEY missing"})
    else:
        for series_id in series_ids:
            params = urllib.parse.urlencode({"series_id": series_id, "api_key": api_key, "file_type": "json", "output_type": 4, "observation_start": "1990-01-01"})
            try:
                items.append({"id": f"ALFRED_{series_id}", **download("https://api.stlouisfed.org/fred/series/observations?" + params, root / "alfred" / f"{series_id}.json", package_root=package_root, kind="json")})
            except Exception as exc:
                items.append({"id": f"ALFRED_{series_id}", "error": f"{type(exc).__name__}: {exc}"})
    try:
        items.append({"id": "BIS_DATAFLOW_CATALOG", **download("https://stats.bis.org/api/v2/dataflow/all/all/latest", root / "bis_dataflows.xml", package_root=package_root, kind="sdmx", headers={"Accept": "application/vnd.sdmx.structure+xml;version=2.1"})})
    except Exception as exc:
        items.append({"id": "BIS_DATAFLOW_CATALOG", "error": f"{type(exc).__name__}: {exc}"})
    try:
        items.append({"id": "CFTC_TFF", **socrata_pages("udgc-27he", root / "cftc_tff.jsonl", package_root=package_root, app_token=os.getenv("CFTC_APP_TOKEN", ""), max_rows=max_cftc_rows)})
    except Exception as exc:
        items.append({"id": "CFTC_TFF", "error": f"{type(exc).__name__}: {exc}"})
    return {"status": _status(items), "items": items}


def collect_crypto(root: Path, package_root: Path, start_month: str, end_month: str) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for market_path in ("spot", "futures/um"):
        for symbol in ("BTCUSDT", "ETHUSDT"):
            for month in month_range(start_month, end_month):
                rel = (f"data/spot/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip" if market_path == "spot" else f"data/futures/um/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip")
                try:
                    items.append({"id": f"BINANCE_{market_path}_{symbol}_{month}", **download("https://data.binance.vision/" + rel, root / "binance" / rel, package_root=package_root, kind="zip", attempts=2)})
                except Exception as exc:
                    items.append({"id": f"BINANCE_{market_path}_{symbol}_{month}", "error": f"{type(exc).__name__}: {exc}"})
    now_ms = int(dt.datetime.now(UTC).timestamp() * 1000); start_ms = int((dt.datetime.now(UTC) - dt.timedelta(days=30)).timestamp() * 1000)
    for symbol in ("BTC-PERPETUAL", "ETH-PERPETUAL"):
        params = urllib.parse.urlencode({"instrument_name": symbol, "start_timestamp": start_ms, "end_timestamp": now_ms})
        try:
            items.append({"id": f"DERIBIT_{symbol}", **download("https://www.deribit.com/api/v2/public/get_funding_rate_history?" + params, root / "deribit" / f"{symbol}.json", package_root=package_root, kind="json")})
        except Exception as exc:
            items.append({"id": f"DERIBIT_{symbol}", "error": f"{type(exc).__name__}: {exc}"})
    params = urllib.parse.urlencode({"assets": "btc,eth", "metrics": "PriceUSD,CapMrktCurUSD,SplyCur,FeeTotUSD,RevUSD,TxCnt,AdrActCnt", "frequency": "1d", "start_time": start_month + "-01", "end_time": end_month + "-28", "format": "json"})
    try:
        items.append({"id": "COIN_METRICS_COMMUNITY", **download("https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?" + params, root / "coinmetrics_btc_eth.json", package_root=package_root, kind="json")})
    except Exception as exc:
        items.append({"id": "COIN_METRICS_COMMUNITY", "error": f"{type(exc).__name__}: {exc}"})
    return {"status": _status(items), "items": items}


def run(args: argparse.Namespace) -> dict[str, Any]:
    package_root = Path(args.output).resolve(); snapshot_root = package_root / dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    snapshot_root.mkdir(parents=True, exist_ok=False)
    results = {
        "us": collect_us(snapshot_root / "us", snapshot_root, include_large_sec=args.include_large_sec),
        "idx": collect_idx(snapshot_root / "idx", snapshot_root),
        "commodity": collect_commodity(snapshot_root / "commodity", snapshot_root, max_cftc_rows=args.max_cftc_rows),
        "fx": collect_fx(snapshot_root / "fx", snapshot_root, args.fx_series, max_cftc_rows=args.max_cftc_rows),
        "crypto": collect_crypto(snapshot_root / "crypto", snapshot_root, args.start_month, args.end_month),
    }
    payload = {
        "schema": "warroom.v95.autonomous_public_data_plane.v1",
        "generated_at": utc_now(),
        "snapshot_root": snapshot_root.name,
        "source_routes_defined": len(SOURCE_REGISTRY),
        "results": results,
        "markets_with_at_least_one_real_snapshot": sum(any(item.get("is_evidence") is True and "sha256" in item for item in result.get("items", [])) for result in results.values()),
        "proof_status": "PUBLIC_EVIDENCE_ONLY",
        "capital_permission": "BLOCKED",
        "claim_limit": "Acquisition and hashes prove source identity only; not prediction, target, profit factor, drawdown or trading readiness.",
    }
    payload["manifest_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    (snapshot_root / "v95_public_acquisition_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def main() -> None:
    now = dt.datetime.now(UTC); previous = (now.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runtime/v95_public_acquisition")
    parser.add_argument("--include-large-sec", action="store_true")
    parser.add_argument("--start-month", default=previous)
    parser.add_argument("--end-month", default=previous)
    parser.add_argument("--fx-series", nargs="*", default=["DEXUSEU", "DEXJPUS", "DEXUSUK", "DEXUSAL", "DEXCAUS"])
    parser.add_argument("--max-cftc-rows", type=int, default=None)
    args = parser.parse_args(); print(json.dumps(run(args), indent=2))


if __name__ == "__main__":
    main()
