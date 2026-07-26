from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

import pandas as pd

from .common import PROCESSED, RAW, ROOT, load_membership_intervals, normalize_ticker, sha256_file, write_json

SEC_DIR = RAW / "sec_fsd"
MEMBERSHIP_PATH = ROOT / "data" / "reference" / "sp500_ticker_start_end.csv"
CURRENT_MAP = RAW / "reference" / "company_tickers_exchange.json"

INSTANCE_PATTERN = re.compile(r"^([a-z][a-z0-9.\-]{0,9})[-_](?:19|20)\d{2}", re.IGNORECASE)


def read_member(zip_file: zipfile.ZipFile, candidates: list[str], **kwargs) -> pd.DataFrame:
    names = {name.lower(): name for name in zip_file.namelist()}
    for candidate in candidates:
        if candidate.lower() in names:
            return pd.read_csv(zip_file.open(names[candidate.lower()]), sep="\t", low_memory=False, **kwargs)
    raise KeyError(f"none of {candidates} found in {zip_file.filename}")


def instance_ticker(instance: str) -> str | None:
    name = Path(str(instance or "")).name
    match = INSTANCE_PATTERN.match(name)
    if not match:
        return None
    ticker = normalize_ticker(match.group(1))
    if not ticker or ticker.isdigit() or len(ticker) > 10:
        return None
    return ticker


def active_on(ticker: str, filed: pd.Timestamp, membership: pd.DataFrame) -> bool:
    intervals = membership[membership["ticker"].eq(normalize_ticker(ticker))]
    if intervals.empty:
        return False
    end = intervals["end_date"].fillna(pd.Timestamp.max.normalize())
    return bool(((intervals["start_date"] <= filed) & (end >= filed)).any())


def load_current_map() -> dict[int, list[str]]:
    if not CURRENT_MAP.exists():
        return {}
    payload = json.loads(CURRENT_MAP.read_text(encoding="utf-8"))
    fields = payload.get("fields", [])
    data = payload.get("data", [])
    index = {name: i for i, name in enumerate(fields)}
    result: dict[int, list[str]] = {}
    for row in data:
        cik = int(row[index["cik"]])
        ticker = normalize_ticker(row[index["ticker"]])
        result.setdefault(cik, []).append(ticker)
    return result


def build_entity_master() -> Path:
    membership = load_membership_intervals(MEMBERSHIP_PATH)
    current_map = load_current_map()
    rows = []
    for path in sorted(SEC_DIR.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            sub = read_member(
                archive,
                ["sub.txt", "sub.tsv"],
                usecols=lambda column: column in {
                    "adsh", "cik", "name", "sic", "form", "period", "fy", "fp",
                    "filed", "accepted", "instance", "prevrpt"
                },
            )
        sub["filed"] = pd.to_datetime(sub["filed"].astype(str), errors="coerce")
        sub = sub[sub["form"].isin(["10-Q", "10-K"]) & sub["filed"].notna()]
        for record in sub.itertuples(index=False):
            candidate = instance_ticker(getattr(record, "instance", ""))
            method = "INSTANCE_PREFIX"
            confidence = "HIGH"
            if not candidate or not active_on(candidate, record.filed, membership):
                active_current = [ticker for ticker in current_map.get(int(record.cik), []) if active_on(ticker, record.filed, membership)]
                if len(active_current) == 1:
                    candidate = active_current[0]
                    method = "CURRENT_SEC_MAP_ACTIVE_INTERVAL"
                    confidence = "MEDIUM"
                else:
                    candidate = None
                    method = "UNMATCHED_QUARANTINE"
                    confidence = "NONE"
            rows.append(
                {
                    "adsh": record.adsh,
                    "cik": int(record.cik),
                    "company_name": record.name,
                    "sic": getattr(record, "sic", None),
                    "form": record.form,
                    "period": getattr(record, "period", None),
                    "fy": getattr(record, "fy", None),
                    "fp": getattr(record, "fp", None),
                    "filed": record.filed,
                    "accepted": getattr(record, "accepted", None),
                    "instance": getattr(record, "instance", None),
                    "ticker": candidate,
                    "mapping_method": method,
                    "mapping_confidence": confidence,
                    "source_zip": path.name,
                }
            )
    frame = pd.DataFrame(rows).drop_duplicates("adsh", keep="last")
    if frame.empty:
        raise RuntimeError("No SEC submissions parsed.")
    frame["sic2"] = pd.to_numeric(frame["sic"], errors="coerce").floordiv(100).astype("Int64")
    target = PROCESSED / "entity_filing_master.parquet"
    frame.to_parquet(target, index=False)
    unmatched = frame[frame["ticker"].isna()].copy()
    unmatched.to_csv(PROCESSED / "entity_mapping_quarantine.csv", index=False)
    write_json(
        PROCESSED / "entity_master_receipt.json",
        {
            "rows": len(frame),
            "mapped_rows": int(frame["ticker"].notna().sum()),
            "unmatched_rows": int(frame["ticker"].isna().sum()),
            "mapped_ciks": int(frame.loc[frame["ticker"].notna(), "cik"].nunique()),
            "methods": frame["mapping_method"].value_counts(dropna=False).to_dict(),
            "source_zips": [{"name": p.name, "sha256": sha256_file(p)} for p in sorted(SEC_DIR.glob("*.zip"))],
            "output_sha256": sha256_file(target),
        },
    )
    print(f"Entity master: {len(frame):,} filings; {frame['ticker'].notna().mean():.1%} mapped; unmatched quarantined.")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    build_entity_master()


if __name__ == "__main__":
    main()
