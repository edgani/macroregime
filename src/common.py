from __future__ import annotations

import csv
import hashlib
import json
import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
PROCESSED = DATA / "processed"
OUTPUTS = ROOT / "outputs"
LOGS = ROOT / "logs"

for path in (RAW, PROCESSED, OUTPUTS, LOGS):
    path.mkdir(parents=True, exist_ok=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def sha256_json(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def append_csv(path: Path, row: dict[str, Any], fields: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    if fields is None:
        fields = list(row.keys())
    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        if not exists:
            writer.writeheader()
        writer.writerow({field: row.get(field, "") for field in fields})


def normalize_ticker(value: str) -> str:
    text = str(value or "").strip().upper()
    text = text.replace("/", ".").replace("-", ".")
    text = re.sub(r"\s+", "", text)
    return text


def price_ticker_candidates(ticker: str) -> list[str]:
    normalized = normalize_ticker(ticker)
    candidates = [normalized, normalized.replace(".", "-"), normalized.replace(".", "")]
    return list(dict.fromkeys(candidates))


def safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)


def rank_percentile(series: pd.Series) -> pd.Series:
    return series.rank(method="average", pct=True)


def robust_zscore(series: pd.Series) -> pd.Series:
    values = safe_numeric(series)
    median = values.median()
    mad = (values - median).abs().median()
    if not np.isfinite(mad) or mad <= 1e-12:
        std = values.std(ddof=0)
        if not np.isfinite(std) or std <= 1e-12:
            return pd.Series(0.0, index=series.index)
        return (values - values.mean()) / std
    return 0.67448975 * (values - median) / mad


def winsorize_cross_section(series: pd.Series, lower: float = 0.01, upper: float = 0.99) -> pd.Series:
    values = safe_numeric(series)
    if values.notna().sum() < 10:
        return values
    low, high = values.quantile([lower, upper])
    return values.clip(low, high)


def business_day_after(calendar: pd.DatetimeIndex, timestamp: pd.Timestamp) -> pd.Timestamp | pd.NaT:
    pos = calendar.searchsorted(pd.Timestamp(timestamp).normalize(), side="right")
    if pos >= len(calendar):
        return pd.NaT
    return calendar[pos]


def latest_available_before(frame: pd.DataFrame, decision_dates: pd.DatetimeIndex, max_age_days: int) -> pd.DataFrame:
    """As-of join per ticker. Assumes decision_available_date is already conservative."""
    pieces: list[pd.DataFrame] = []
    for ticker, group in frame.groupby("ticker", sort=False):
        group = group.sort_values("decision_available_date")
        left = pd.DataFrame({"decision_date": decision_dates})
        joined = pd.merge_asof(
            left.sort_values("decision_date"),
            group,
            left_on="decision_date",
            right_on="decision_available_date",
            direction="backward",
            tolerance=pd.Timedelta(days=max_age_days),
        )
        joined["ticker"] = ticker
        pieces.append(joined)
    if not pieces:
        return pd.DataFrame()
    return pd.concat(pieces, ignore_index=True)


@dataclass(frozen=True)
class MembershipInterval:
    ticker: str
    start_date: pd.Timestamp
    end_date: pd.Timestamp | None


def load_membership_intervals(path: Path) -> pd.DataFrame:
    frame = pd.read_csv(path)
    frame["ticker"] = frame["ticker"].map(normalize_ticker)
    frame["start_date"] = pd.to_datetime(frame["start_date"], errors="coerce")
    frame["end_date"] = pd.to_datetime(frame["end_date"], errors="coerce")
    frame = frame.dropna(subset=["ticker", "start_date"]).sort_values(["ticker", "start_date"])
    return frame


def active_membership_mask(ticker: str, timestamps: pd.Series, membership: pd.DataFrame) -> pd.Series:
    intervals = membership[membership["ticker"].eq(normalize_ticker(ticker))]
    result = pd.Series(False, index=timestamps.index)
    for row in intervals.itertuples(index=False):
        end = row.end_date if pd.notna(row.end_date) else pd.Timestamp.max.normalize()
        result |= timestamps.between(row.start_date, end, inclusive="both")
    return result


def bh_qvalues(pvalues: Iterable[float]) -> np.ndarray:
    p = np.asarray(list(pvalues), dtype=float)
    n = len(p)
    if n == 0:
        return p
    order = np.argsort(p)
    ranked = p[order]
    q = ranked * n / np.arange(1, n + 1)
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.clip(q, 0.0, 1.0)
    out = np.empty(n)
    out[order] = q
    return out


def year_block_bootstrap_mean(values: pd.Series, years: pd.Series, iterations: int, seed: int) -> dict[str, float]:
    data = pd.DataFrame({"value": safe_numeric(values), "year": years}).dropna()
    unique_years = np.sort(data["year"].unique())
    if len(data) == 0 or len(unique_years) == 0:
        return {"mean": np.nan, "low": np.nan, "high": np.nan, "p_gt_zero": np.nan}
    grouped = {year: data.loc[data["year"].eq(year), "value"].to_numpy() for year in unique_years}
    rng = np.random.default_rng(seed)
    samples = np.empty(iterations)
    for i in range(iterations):
        selected = rng.choice(unique_years, size=len(unique_years), replace=True)
        sample = np.concatenate([grouped[year] for year in selected])
        samples[i] = np.mean(sample)
    observed = float(data["value"].mean())
    low, high = np.quantile(samples, [0.025, 0.975])
    p_gt_zero = float((1 + np.sum(samples <= 0.0)) / (iterations + 1))
    return {"mean": observed, "low": float(low), "high": float(high), "p_gt_zero": p_gt_zero}


def ensure_no_future_information(frame: pd.DataFrame, test_start: pd.Timestamp, target: str) -> None:
    outcome_column = f"outcome_date_{target}"
    if outcome_column not in frame:
        raise KeyError(outcome_column)
    invalid = frame[outcome_column].notna() & (frame[outcome_column] >= test_start)
    if invalid.any():
        raise RuntimeError(
            f"purge violation: {int(invalid.sum())} training rows have {outcome_column} >= {test_start.date()}"
        )


def package_version_hash() -> str:
    contract = ROOT / "config" / "freeze_contract.json"
    return sha256_file(contract) if contract.exists() else "MISSING"
