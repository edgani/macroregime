"""Fail-closed Parquet compatibility adapter for bundled War Room research files."""
from __future__ import annotations
from pathlib import Path
from typing import Iterable
import pandas as pd
from research_v55.flat_parquet_snappy import read_flat_parquet


def read_parquet_compat(path: str | Path, columns: Iterable[str] | None = None) -> pd.DataFrame:
    try:
        return pd.read_parquet(path, columns=None if columns is None else list(columns))
    except ImportError:
        return read_flat_parquet(path, columns=columns, restore_pandas_index=True)
