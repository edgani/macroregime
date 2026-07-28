"""Fast, resilient official/public context collector for War Room OS V9.8.

This plane is intentionally small enough to refresh in a desktop app. Each source is isolated,
atomically stored and hash-recorded. A successful source fetch never grants capital permission.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
UTC = dt.timezone.utc
USER_AGENT = "WarRoomOS/9.8 public-context"
DEFAULT_OUT = HERE / "runtime" / "v98_public_acquisition"


def _now() -> dt.datetime:
    return dt.datetime.now(UTC)


def _iso(value: dt.datetime | None = None) -> str:
    return (value or _now()).astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fetch(url: str, path: Path, *, headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.part")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*", **(headers or {})})
    started = time.monotonic()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read()
            meta = {"http_status": int(getattr(response, "status", 200)), "content_type": response.headers.get("Content-Type"), "final_url": response.geturl(), "latency_ms": round((time.monotonic() - started) * 1000, 2)}
        if not raw.strip():
            raise ValueError("blank payload")
        temp.write_bytes(raw); os.replace(temp, path)
        return {"path": path, "bytes": len(raw), "sha256": _sha(path), "downloaded_at": _iso(), "metadata": meta, "is_evidence": True}
    finally:
        temp.unlink(missing_ok=True)


def _item(root: Path, market: str, source_id: str, url: str, filename: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> dict[str, Any]:
    try:
        result = _fetch(url, root / market / filename, headers=headers, timeout=timeout)
        path = result.pop("path")
        return {"id": source_id, "url": url, "path": path.relative_to(root).as_posix(), **result}
    except Exception as exc:
        return {"id": source_id, "url": url, "error": f"{type(exc).__name__}: {exc}"}


def _cftc_url(dataset: str) -> str:
    query = urllib.parse.urlencode({"$limit": 250, "$order": "report_date_as_yyyy_mm_dd DESC"})
    return f"https://publicreporting.cftc.gov/resource/{dataset}.json?{query}"


def collect(output: Path = DEFAULT_OUT) -> dict[str, Any]:
    from concurrent.futures import ThreadPoolExecutor, as_completed

    root = output / _now().strftime("%Y%m%dT%H%M%SZ")
    root.mkdir(parents=True, exist_ok=False)
    sec_ua = os.getenv("WARROOM_SEC_USER_AGENT", "").strip()
    end = _now(); start = end - dt.timedelta(days=31)
    deribit_query = urllib.parse.urlencode({"instrument_name": "BTC-PERPETUAL", "start_timestamp": int(start.timestamp() * 1000), "end_timestamp": int(end.timestamp() * 1000)})
    cm_query = urllib.parse.urlencode({"assets": "btc,eth", "metrics": "PriceUSD,CapMrktCurUSD,SplyCur,FeeTotUSD,RevUSD,TxCnt,AdrActCnt", "frequency": "1d", "start_time": start.date().isoformat(), "end_time": end.date().isoformat(), "format": "json"})

    specs: list[tuple[str, str, str, str, dict[str, str] | None, int]] = [
        ("us", "NASDAQ_LISTED", "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "nasdaqlisted.txt", None, 18),
        ("us", "NASDAQ_OTHER_LISTED", "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "otherlisted.txt", None, 18),
        ("us", "NASDAQ_TRADED", "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt", "nasdaqtraded.txt", None, 18),
        ("idx", "IDX_COMPANY_PROFILES", "https://www.idx.co.id/primary/ListedCompany/GetCompanyProfiles?emitenType=s&start=0&length=9999", "company_profiles.json", {"Referer": "https://www.idx.co.id/", "Accept": "application/json,text/plain,*/*"}, 20),
        ("commodity", "EIA_BULK_MANIFEST", "https://api.eia.gov/bulk/manifest.txt", "eia_manifest.json", None, 20),
        ("commodity", "CFTC_DISAGGREGATED", _cftc_url("72hh-3qpy"), "cftc_disaggregated_latest.json", None, 25),
        ("fx", "BIS_DATAFLOW_CATALOG", "https://stats.bis.org/api/v2/dataflow/all/all/latest", "bis_dataflow.xml", {"Accept": "application/xml,text/xml,*/*"}, 30),
        ("fx", "CFTC_TFF", _cftc_url("udgc-27he"), "cftc_tff_latest.json", None, 25),
        ("crypto", "BINANCE_EXCHANGE_INFO", "https://data-api.binance.vision/api/v3/exchangeInfo", "binance_exchange_info.json", None, 18),
        ("crypto", "DERIBIT_FUNDING", "https://www.deribit.com/api/v2/public/get_funding_rate_history?" + deribit_query, "deribit_btc_funding.json", None, 20),
        ("crypto", "COIN_METRICS_COMMUNITY", "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics?" + cm_query, "coinmetrics_btc_eth.json", None, 30),
    ]
    results: dict[str, list[dict[str, Any]]] = {m: [] for m in ("us", "idx", "commodity", "fx", "crypto")}
    if sec_ua and "@" in sec_ua:
        specs.append(("us", "SEC_COMPANY_TICKERS", "https://www.sec.gov/files/company_tickers.json", "company_tickers.json", {"User-Agent": sec_ua}, 20))
    else:
        results["us"].append({"id": "SEC_COMPANY_TICKERS", "error": "Set WARROOM_SEC_USER_AGENT to a name/contact email for SEC fair-access collection."})

    def run_spec(spec: tuple[str, str, str, str, dict[str, str] | None, int]) -> tuple[str, dict[str, Any]]:
        market, source_id, url, filename, headers, timeout = spec
        return market, _item(root, market, source_id, url, filename, headers=headers, timeout=timeout)

    with ThreadPoolExecutor(max_workers=min(12, len(specs))) as pool:
        futures = [pool.submit(run_spec, spec) for spec in specs]
        for future in as_completed(futures):
            market, item = future.result()
            results[market].append(item)
    for market in results:
        results[market].sort(key=lambda x: str(x.get("id") or ""))

    normalized = {}
    for market, items in results.items():
        success = sum(item.get("is_evidence") is True for item in items)
        normalized[market] = {"status": "COLLECTED" if success == len(items) else "COLLECTED_WITH_ERRORS" if success else "BLOCKED", "items": items}
    payload = {
        "schema": "warroom.v98.public_context_acquisition.v1",
        "generated_at": _iso(),
        "snapshot_root": root.name,
        "results": normalized,
        "markets_with_at_least_one_real_snapshot": sum(any(item.get("is_evidence") is True for item in rows) for rows in results.values()),
        "proof_status": "PUBLIC_CONTEXT_ONLY",
        "capital_permission": "BLOCKED",
        "claim_limit": "Source hashes establish acquisition identity only. They do not prove direction, target, timing or profitability.",
    }
    payload["manifest_hash"] = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()
    (root / "v98_public_acquisition_manifest.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


if __name__ == "__main__":
    print(json.dumps(collect(), indent=2))
