"""warroom/research/walkforward.py — purged walk-forward splits with embargo (R7).

Expanding-window walk-forward:
  - purge gap between train end and test start (removes boundary leakage)
  - embargo after test before next train window
  - final lockbox segment never touched until R10/R11 unlocks it
"""
from __future__ import annotations

import pandas as pd


def expanding_splits(index: pd.DatetimeIndex, n_splits: int = 4, min_train: int = 126,
                     test_size: int = 63, purge: int = 5, embargo: int = 5,
                     lockbox_size: int = 126) -> dict:
    """Return {'splits': [(train_idx, test_idx)], 'lockbox': idx}.

    index: sorted DatetimeIndex of available bars.
    """
    n = len(index)
    if n < min_train + test_size + lockbox_size + purge + embargo:
        return {"splits": [], "lockbox": index[-lockbox_size:] if n > lockbox_size else index,
                "error": "insufficient history"}
    usable_end = n - lockbox_size
    splits = []
    start_test = min_train
    while start_test + purge + test_size <= usable_end:
        train = index[0:start_test]
        test_start = start_test + purge
        test_end = min(test_start + test_size, usable_end)
        test = index[test_start:test_end]
        if len(test) == 0:
            break
        splits.append((train, test))
        start_test = test_end + embargo
    return {"splits": splits, "lockbox": index[usable_end:], "purge": purge,
            "embargo": embargo, "lockbox_size": lockbox_size}
