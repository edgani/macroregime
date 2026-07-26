"""Numerically safe primitives used by strict warning-as-error validation."""
from __future__ import annotations
import numpy as np
import pandas as pd


def numeric_series(values) -> pd.Series:
    return pd.to_numeric(pd.Series(values), errors="coerce").replace([np.inf, -np.inf], np.nan)


def positive_series(values) -> pd.Series:
    s = numeric_series(values)
    return s.where(s > 0)


def log_returns(values) -> pd.Series:
    """Log returns with non-positive and non-finite observations treated as missing, never warnings."""
    return np.log(positive_series(values)).diff()
