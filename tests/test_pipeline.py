from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from src.build_entity_master import instance_ticker
from src.common import ensure_no_future_information, load_membership_intervals, normalize_ticker
from src.run_tournament import equal_weight_score, ridge_wfa


def synthetic_panel() -> pd.DataFrame:
    rng = np.random.default_rng(20260717)
    dates = pd.date_range("2016-01-29", "2024-12-31", freq="ME")
    tickers = [f"T{i:03d}" for i in range(70)]
    rows = []
    for date in dates:
        macro = rng.normal(scale=0.01)
        for index, ticker in enumerate(tickers):
            sector = index % 7
            quality = rng.normal()
            momentum = rng.normal()
            noise = rng.normal(scale=0.05)
            target = 0.025 * quality + 0.006 * momentum + macro + noise
            rows.append(
                {
                    "decision_date": date,
                    "ticker": ticker,
                    "sic2": sector,
                    "revenue_growth_yoy": quality + rng.normal(scale=0.3),
                    "operating_margin": quality + rng.normal(scale=0.3),
                    "operating_margin_change_yoy": quality + rng.normal(scale=0.3),
                    "net_margin": quality + rng.normal(scale=0.3),
                    "cash_conversion": quality + rng.normal(scale=0.4),
                    "accrual_quality": quality + rng.normal(scale=0.4),
                    "leverage": -quality + rng.normal(scale=0.4),
                    "shares_growth_yoy": -quality + rng.normal(scale=0.4),
                    "momentum_252_21": momentum,
                    "reversal_20": rng.normal(),
                    "volatility_63": rng.uniform(0.01, 0.06),
                    "drawdown_252": -rng.uniform(0, 0.5),
                    "log_dollar_volume_63": rng.normal(16, 1),
                    "sector_excess_T63": target,
                    "outcome_date_T63": date + pd.offsets.BDay(63),
                }
            )
    return pd.DataFrame(rows)


def test_ticker_normalization() -> None:
    assert normalize_ticker(" brk-b ") == "BRK.B"
    assert instance_ticker("aapl-20240928.htm") == "AAPL"
    assert instance_ticker("0000320193-24-000123.htm") is None


def test_no_future_information_rejects_overlap() -> None:
    frame = pd.DataFrame({"outcome_date_T63": [pd.Timestamp("2022-12-30"), pd.Timestamp("2023-01-03")]})
    with pytest.raises(RuntimeError):
        ensure_no_future_information(frame, pd.Timestamp("2023-01-01"), "T63")


def test_equal_weight_score_is_cross_sectional() -> None:
    frame = synthetic_panel().head(140).copy()
    score = equal_weight_score(frame, ["revenue_growth_yoy", "operating_margin"])
    assert score.notna().sum() == len(frame)
    assert score.between(-0.5, 0.5).all()


def test_ridge_wfa_purges_overlapping_labels() -> None:
    frame = synthetic_panel()
    features = [
        "revenue_growth_yoy", "operating_margin", "operating_margin_change_yoy",
        "net_margin", "cash_conversion", "accrual_quality", "leverage",
        "shares_growth_yoy", "momentum_252_21", "reversal_20",
        "volatility_63", "drawdown_252", "log_dollar_volume_63",
    ]
    predictions = ridge_wfa(frame, features, "T63", "2024-12-31")
    assert not predictions.empty
    assert predictions["test_year"].min() >= 2019
    assert predictions["score"].notna().all()


def test_freeze_contract_has_fail_closed_claims() -> None:
    root = Path(__file__).resolve().parents[1]
    contract = json.loads((root / "config/freeze_contract.json").read_text())
    assert contract["claim_ceiling"] == "HISTORICAL_CANDIDATE_UNTIL_LOCKBOX_AND_PROSPECTIVE_PASS"
    assert contract["lockbox"]["retuning_after_open"] is False
    assert contract["prospective"]["proven_label_requires_future_receipts"] is True


def test_membership_reference_has_delisted_names() -> None:
    root = Path(__file__).resolve().parents[1]
    membership = load_membership_intervals(root / "data/reference/sp500_ticker_start_end.csv")
    assert len(membership) > 1000
    assert membership["end_date"].notna().sum() > 500
