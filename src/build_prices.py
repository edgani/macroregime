from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.dataset as ds

from .common import PROCESSED, RAW, ROOT, load_membership_intervals, normalize_ticker, sha256_file, write_json

PRICE_DIR = RAW / "prices"
MEMBERSHIP_PATH = ROOT / "data" / "reference" / "sp500_ticker_start_end.csv"


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    lower = {column.lower().strip(): column for column in frame.columns}
    aliases = {
        "ticker": ["ticker", "symbol"],
        "date": ["date", "datetime", "timestamp"],
        "open": ["open"],
        "high": ["high"],
        "low": ["low"],
        "close": ["close"],
        "adj_close": ["adj_close", "adj close", "adjusted_close", "adjusted close"],
        "volume": ["volume"],
    }
    selected = {}
    for canonical, candidates in aliases.items():
        for candidate in candidates:
            if candidate in lower:
                selected[canonical] = lower[candidate]
                break
    required = {"ticker", "date", "close", "volume"}
    missing = required - set(selected)
    if missing:
        raise ValueError(f"price data missing required columns {sorted(missing)}; got {list(frame.columns)}")
    out = pd.DataFrame({canonical: frame[source] for canonical, source in selected.items()})
    if "adj_close" not in out:
        out["adj_close"] = out["close"]
    for column in ["open", "high", "low"]:
        if column not in out:
            out[column] = out["close"]
    return out[["ticker", "date", "open", "high", "low", "close", "adj_close", "volume"]]


def build_prices(start_date: str = "2016-01-01") -> Path:
    files = sorted(PRICE_DIR.glob("*.parquet"))
    if not files:
        raise FileNotFoundError(f"No price parquet files in {PRICE_DIR}. Run download_data first.")
    membership = load_membership_intervals(MEMBERSHIP_PATH)
    wanted = set(membership["ticker"])
    dataset = ds.dataset([str(path) for path in files], format="parquet")
    chunks = []
    for batch in dataset.to_batches(batch_size=250_000):
        chunk = normalize_columns(batch.to_pandas())
        chunk["ticker_raw"] = chunk["ticker"].astype(str)
        chunk["ticker"] = chunk["ticker"].map(normalize_ticker)
        chunk["date"] = pd.to_datetime(chunk["date"], errors="coerce").dt.tz_localize(None).dt.normalize()
        for column in ["open", "high", "low", "close", "adj_close", "volume"]:
            chunk[column] = pd.to_numeric(chunk[column], errors="coerce")
        chunk = chunk[
            chunk["ticker"].isin(wanted)
            & chunk["date"].ge(pd.Timestamp(start_date))
            & chunk["adj_close"].gt(0)
            & chunk["volume"].ge(0)
        ]
        if not chunk.empty:
            chunks.append(chunk)
    if not chunks:
        raise RuntimeError("No price rows survived ticker/date filters.")
    frame = pd.concat(chunks, ignore_index=True).drop_duplicates(["ticker", "date"], keep="last")

    # Membership is checked row-by-row by merging intervals. This keeps delisted symbols rather than current survivors only.
    parts = []
    for row in membership.itertuples(index=False):
        end = row.end_date if pd.notna(row.end_date) else frame["date"].max()
        part = frame[
            frame["ticker"].eq(row.ticker)
            & frame["date"].between(row.start_date, end, inclusive="both")
        ]
        if not part.empty:
            parts.append(part)
    if not parts:
        raise RuntimeError("No price rows matched historical membership intervals.")
    frame = pd.concat(parts, ignore_index=True).drop_duplicates(["ticker", "date"])
    frame = frame.sort_values(["ticker", "date"]).reset_index(drop=True)

    group = frame.groupby("ticker", sort=False)
    frame["return_1d"] = group["adj_close"].pct_change(fill_method=None)
    frame["momentum_252_21"] = group["adj_close"].transform(lambda s: s.shift(21) / s.shift(252) - 1)
    frame["reversal_20"] = -(group["adj_close"].transform(lambda s: s / s.shift(20) - 1))
    frame["volatility_63"] = group["return_1d"].transform(lambda s: s.rolling(63, min_periods=42).std())
    rolling_max = group["adj_close"].transform(lambda s: s.rolling(252, min_periods=126).max())
    frame["drawdown_252"] = frame["adj_close"] / rolling_max - 1
    dollar_volume = frame["adj_close"] * frame["volume"]
    frame["dollar_volume_63"] = dollar_volume.groupby(frame["ticker"]).transform(
        lambda s: s.rolling(63, min_periods=42).median()
    )
    frame["log_dollar_volume_63"] = np.log1p(frame["dollar_volume_63"])

    targets = {"T20": 20, "T63": 63, "T126": 126, "T252": 252}
    for name, horizon in targets.items():
        frame[f"return_{name}"] = group["adj_close"].transform(lambda s, h=horizon: s.shift(-h) / s - 1)
        frame[f"outcome_date_{name}"] = group["date"].shift(-horizon)

    target = PROCESSED / "prices_sp500_pit.parquet"
    frame.to_parquet(target, index=False)
    write_json(
        PROCESSED / "prices_build_receipt.json",
        {
            "source_files": [{"name": p.name, "sha256": sha256_file(p), "size_bytes": p.stat().st_size} for p in files],
            "membership_file_sha256": sha256_file(MEMBERSHIP_PATH),
            "rows": len(frame),
            "tickers": int(frame["ticker"].nunique()),
            "date_min": str(frame["date"].min().date()),
            "date_max": str(frame["date"].max().date()),
            "output_sha256": sha256_file(target),
        },
    )
    print(f"Price panel: {len(frame):,} rows, {frame['ticker'].nunique():,} tickers -> {target}")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2016-01-01")
    args = parser.parse_args()
    build_prices(args.start_date)


if __name__ == "__main__":
    main()
