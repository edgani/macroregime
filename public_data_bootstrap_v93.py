"""V9.3 official/public evidence bootstrap.

This module only downloads and hashes raw official/public records. It never creates signals,
price targets, recommendations, or trading permission. Paid/licensed datasets and account fills
remain separate mandatory evidence roles.
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


class BootstrapError(RuntimeError):
    pass


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(url: str, destination: Path, *, headers: dict[str, str] | None = None, timeout: int = 60) -> dict[str, Any]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers=headers or {})
    temp = destination.with_suffix(destination.suffix + ".part")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response, temp.open("wb") as output:
            if getattr(response, "status", 200) != 200:
                raise BootstrapError(f"HTTP {response.status} for {url}")
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
        temp.replace(destination)
    except Exception:
        temp.unlink(missing_ok=True)
        raise
    return {
        "url": url,
        "path": str(destination.resolve()),
        "bytes": destination.stat().st_size,
        "sha256": sha256_file(destination),
    }


def fetch_json(url: str, *, headers: dict[str, str] | None = None, timeout: int = 60) -> Any:
    request = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if getattr(response, "status", 200) != 200:
            raise BootstrapError(f"HTTP {response.status} for {url}")
        return json.loads(response.read().decode("utf-8"))


def write_json(path: Path, payload: Any) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"path": str(path.resolve()), "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def month_range(start: str, end: str) -> Iterable[str]:
    sy, sm = map(int, start.split("-"))
    ey, em = map(int, end.split("-"))
    year, month = sy, sm
    while (year, month) <= (ey, em):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            month = 1
            year += 1


def collect_sec(output: Path, *, bulk: bool) -> list[dict[str, Any]]:
    agent = os.getenv("WARROOM_SEC_USER_AGENT", "").strip()
    if not agent or "@" not in agent:
        raise BootstrapError("WARROOM_SEC_USER_AGENT must contain app identity and contact email")
    headers = {"User-Agent": agent, "Accept-Encoding": "gzip, deflate"}
    artifacts = []
    artifacts.append(download("https://www.sec.gov/files/company_tickers.json", output / "company_tickers.json", headers=headers))
    if bulk:
        artifacts.append(download("https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip", output / "submissions.zip", headers=headers, timeout=300))
        artifacts.append(download("https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip", output / "companyfacts.zip", headers=headers, timeout=600))
    return artifacts


def collect_cftc(output: Path, *, limit: int = 50000) -> list[dict[str, Any]]:
    token = os.getenv("CFTC_APP_TOKEN", "").strip()
    headers = {"X-App-Token": token} if token else {}
    datasets = {
        "disaggregated_futures_only": "72hh-3qpy",
        "tff_all": "udgc-27he",
    }
    artifacts = []
    for name, dataset_id in datasets.items():
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            query = urllib.parse.urlencode({"$limit": min(limit, 50000), "$offset": offset})
            url = f"https://publicreporting.cftc.gov/resource/{dataset_id}.json?{query}"
            batch = fetch_json(url, headers=headers, timeout=120)
            if not isinstance(batch, list):
                raise BootstrapError(f"Malformed CFTC response for {dataset_id}")
            rows.extend(x for x in batch if isinstance(x, dict))
            if len(batch) < min(limit, 50000):
                break
            offset += len(batch)
            time.sleep(0.25)
        result = write_json(output / f"{name}.json", rows)
        result.update({"dataset_id": dataset_id, "rows": len(rows), "source": "CFTC_PUBLIC_REPORTING"})
        artifacts.append(result)
    return artifacts


def collect_binance(output: Path, start_month: str, end_month: str) -> list[dict[str, Any]]:
    artifacts = []
    products = [
        ("spot", "BTCUSDT"), ("spot", "ETHUSDT"),
        ("futures/um", "BTCUSDT"), ("futures/um", "ETHUSDT"),
    ]
    for market_path, symbol in products:
        for month in month_range(start_month, end_month):
            if market_path == "spot":
                relative = f"data/spot/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
            else:
                relative = f"data/futures/um/monthly/klines/{symbol}/1d/{symbol}-1d-{month}.zip"
            url = "https://data.binance.vision/" + relative
            destination = output / relative
            try:
                item = download(url, destination, timeout=120)
                item.update({"market": market_path, "symbol": symbol, "month": month})
                artifacts.append(item)
            except Exception as exc:
                artifacts.append({"url": url, "market": market_path, "symbol": symbol, "month": month, "error": f"{type(exc).__name__}: {exc}"})
    return artifacts


def collect_deribit(output: Path, start_ms: int, end_ms: int) -> list[dict[str, Any]]:
    artifacts = []
    for instrument in ("BTC-PERPETUAL", "ETH-PERPETUAL"):
        params = urllib.parse.urlencode({"instrument_name": instrument, "start_timestamp": start_ms, "end_timestamp": end_ms})
        url = "https://www.deribit.com/api/v2/public/get_funding_rate_history?" + params
        payload = fetch_json(url, timeout=120)
        if not isinstance(payload, dict) or not isinstance(payload.get("result"), list):
            raise BootstrapError(f"Malformed Deribit funding history for {instrument}")
        result = write_json(output / f"{instrument}_funding.json", payload)
        result.update({"instrument": instrument, "rows": len(payload["result"]), "source": "DERIBIT_PUBLIC_API"})
        artifacts.append(result)
    return artifacts


def run(args: argparse.Namespace) -> dict[str, Any]:
    root = Path(args.output)
    stamp = dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    session = root / stamp
    session.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "schema": "warroom.v93.public_bootstrap.v1",
        "collected_at": dt.datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "capital_permission": "BLOCKED",
        "sources": {},
        "errors": [],
        "claim_limit": "Raw public/official evidence only. No historical edge, fill quality, or trading readiness is implied.",
    }
    tasks = [
        ("sec", lambda: collect_sec(session / "us" / "sec", bulk=args.sec_bulk)),
        ("cftc", lambda: collect_cftc(session / "cftc")),
        ("binance", lambda: collect_binance(session / "crypto" / "binance", args.start_month, args.end_month)),
        ("deribit", lambda: collect_deribit(session / "crypto" / "deribit", args.start_ms, args.end_ms)),
    ]
    for name, task in tasks:
        if name in args.skip:
            continue
        try:
            manifest["sources"][name] = task()
        except Exception as exc:
            manifest["errors"].append({"source": name, "error": f"{type(exc).__name__}: {exc}"})
    manifest["complete"] = not manifest["errors"]
    manifest["manifest_hash"] = hashlib.sha256(canonical(manifest)).hexdigest()
    write_json(session / "public_bootstrap_manifest.json", manifest)
    return manifest


def main() -> None:
    now = dt.datetime.now(UTC)
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="runtime/v93_public_bootstrap")
    parser.add_argument("--start-month", default=f"{now.year - 2:04d}-{now.month:02d}")
    parser.add_argument("--end-month", default=f"{now.year:04d}-{max(1, now.month - 1):02d}")
    parser.add_argument("--start-ms", type=int, default=int((now - dt.timedelta(days=365 * 2)).timestamp() * 1000))
    parser.add_argument("--end-ms", type=int, default=int(now.timestamp() * 1000))
    parser.add_argument("--sec-bulk", action="store_true")
    parser.add_argument("--skip", action="append", default=[])
    args = parser.parse_args()
    result = run(args)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["complete"] else 2)


if __name__ == "__main__":
    main()
