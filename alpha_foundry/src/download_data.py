from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
from typing import Iterable

import requests

from .common import RAW, ROOT, sha256_file, utc_now, write_json

SEC_DIR = RAW / "sec_fsd"
PRICE_DIR = RAW / "prices"
REFERENCE_DIR = RAW / "reference"
RECEIPT_DIR = RAW / "receipts"
for path in (SEC_DIR, PRICE_DIR, REFERENCE_DIR, RECEIPT_DIR):
    path.mkdir(parents=True, exist_ok=True)


def parse_period(value: str) -> tuple[int, int]:
    year, quarter = value.lower().replace("q", "-").split("-")
    return int(year), int(quarter)


def iter_quarters(start: str, end: str) -> Iterable[tuple[int, int]]:
    start_y, start_q = parse_period(start)
    end_y, end_q = parse_period(end)
    year, quarter = start_y, start_q
    while (year, quarter) <= (end_y, end_q):
        yield year, quarter
        quarter += 1
        if quarter == 5:
            year += 1
            quarter = 1


def download(
    session: requests.Session,
    url: str,
    target: Path,
    user_agent: str,
    expected_prefix: bytes | None = None,
    retries: int = 4,
) -> Path:
    if target.exists() and target.stat().st_size > 0:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_suffix(target.suffix + ".part")
    headers = {"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"}
    for attempt in range(retries):
        try:
            with session.get(url, headers=headers, timeout=(30, 300), stream=True) as response:
                response.raise_for_status()
                with partial.open("wb") as output:
                    for block in response.iter_content(chunk_size=1024 * 1024):
                        if block:
                            output.write(block)
            if partial.stat().st_size == 0:
                raise RuntimeError(f"empty response: {url}")
            if expected_prefix:
                with partial.open("rb") as f:
                    prefix = f.read(len(expected_prefix))
                if prefix != expected_prefix:
                    raise RuntimeError(f"unexpected file signature for {url}: {prefix!r}")
            partial.replace(target)
            write_json(
                RECEIPT_DIR / f"{target.name}.json",
                {
                    "source_url": url,
                    "retrieved_at_utc": utc_now(),
                    "path": str(target.relative_to(ROOT)),
                    "size_bytes": target.stat().st_size,
                    "sha256": sha256_file(target),
                },
            )
            return target
        except Exception:
            if partial.exists():
                partial.unlink()
            if attempt + 1 == retries:
                raise
            time.sleep(2**attempt)
    raise AssertionError("unreachable")


def download_sec(session: requests.Session, start: str, end: str, user_agent: str) -> list[Path]:
    paths = []
    for year, quarter in iter_quarters(start, end):
        url = f"https://www.sec.gov/files/dera/data/financial-statement-data-sets/{year}q{quarter}.zip"
        target = SEC_DIR / f"{year}q{quarter}.zip"
        paths.append(download(session, url, target, user_agent, expected_prefix=b"PK"))
        time.sleep(0.15)
    mapping_url = "https://www.sec.gov/files/company_tickers_exchange.json"
    paths.append(
        download(
            session,
            mapping_url,
            REFERENCE_DIR / "company_tickers_exchange.json",
            user_agent,
        )
    )
    return paths


def download_prices(session: requests.Session, user_agent: str) -> list[Path]:
    api = "https://huggingface.co/api/datasets/paperswithbacktest/Stocks-Daily-Price/parquet/default/train"
    response = session.get(api, headers={"User-Agent": user_agent}, timeout=60)
    response.raise_for_status()
    urls = response.json()
    if not isinstance(urls, list) or not urls:
        raise RuntimeError(f"unexpected parquet API response: {type(urls)}")
    paths = []
    for index, url in enumerate(urls):
        target = PRICE_DIR / f"stocks_daily_{index:02d}.parquet"
        paths.append(download(session, str(url), target, user_agent, expected_prefix=b"PAR1"))
    return paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the frozen free-data inputs.")
    parser.add_argument("--sec-start", default="2018q1")
    parser.add_argument("--sec-end", default="2026q1")
    parser.add_argument("--skip-sec", action="store_true")
    parser.add_argument("--skip-prices", action="store_true")
    args = parser.parse_args()

    user_agent = os.environ.get("SEC_USER_AGENT", "").strip()
    if not user_agent or "@" not in user_agent:
        raise RuntimeError(
            "Set SEC_USER_AGENT to a real contact string, e.g. "
            "Edward Gani edward@example.com, before downloading SEC data."
        )

    session = requests.Session()
    downloaded: list[Path] = []
    if not args.skip_sec:
        downloaded.extend(download_sec(session, args.sec_start, args.sec_end, user_agent))
    if not args.skip_prices:
        downloaded.extend(download_prices(session, user_agent))

    write_json(
        RAW / "DOWNLOAD_COMPLETION.json",
        {
            "completed_at_utc": utc_now(),
            "sec_start": args.sec_start,
            "sec_end": args.sec_end,
            "files": [
                {
                    "path": str(path.relative_to(ROOT)),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256_file(path),
                }
                for path in downloaded
            ],
        },
    )
    print(f"Downloaded/verified {len(downloaded)} files.")


if __name__ == "__main__":
    main()
