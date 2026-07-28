"""Fail-closed Parquet compatibility adapter for bundled War Room research files."""
from __future__ import annotations
from pathlib import Path
from typing import Iterable
import numpy as np
import pandas as pd
from research_v55.flat_parquet_snappy import read_flat_parquet


def _normalize_datetime_units(frame: pd.DataFrame) -> pd.DataFrame:
    """Coerce every datetime64 column to nanoseconds.

    pyarrow-backed reads may yield datetime64[us] or datetime64[ms] depending on
    the installed pyarrow/pandas version, while the pure-Python fallback reader
    (research_v55.flat_parquet_snappy) always yields datetime64[ns]. Without
    normalization the two backends are not interchangeable: DataFrame.equals
    and dtype-sensitive consumers fail on an artifact of the backend, not the
    data. Nanoseconds are the canonical pandas unit.
    """
    for column in frame.columns:
        dtype = frame[column].dtype
        if pd.api.types.is_datetime64_any_dtype(dtype) and np.datetime_data(dtype)[0] != "ns":
            frame[column] = frame[column].astype("datetime64[ns]")
    return frame


def read_parquet_compat(path: str | Path, columns: Iterable[str] | None = None) -> pd.DataFrame:
    try:
        frame = pd.read_parquet(path, columns=None if columns is None else list(columns))
    except ImportError:
        frame = read_flat_parquet(path, columns=columns, restore_pandas_index=True)
    return _normalize_datetime_units(frame)
