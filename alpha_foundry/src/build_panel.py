from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from .common import PROCESSED, ROOT, business_day_after, sha256_file, write_json

PRICE_PATH = PROCESSED / "prices_sp500_pit.parquet"
FEATURE_PATH = PROCESSED / "sec_filing_features.parquet"

FUNDAMENTAL_FEATURES = [
    "revenue_growth_yoy",
    "operating_margin",
    "operating_margin_change_yoy",
    "net_margin",
    "cash_conversion",
    "accrual_quality",
    "leverage",
    "shares_growth_yoy",
]
MARKET_FEATURES = [
    "momentum_252_21",
    "reversal_20",
    "volatility_63",
    "drawdown_252",
    "log_dollar_volume_63",
]


def last_trading_days(dates: pd.Series) -> pd.DatetimeIndex:
    calendar = pd.DatetimeIndex(pd.to_datetime(dates).dropna().sort_values().unique())
    monthly = pd.Series(calendar, index=calendar).groupby(calendar.to_period("M")).max()
    return pd.DatetimeIndex(monthly.values)


def build_panel(max_staleness_days: int = 200) -> Path:
    if not PRICE_PATH.exists() or not FEATURE_PATH.exists():
        raise FileNotFoundError("Run build_prices and build_sec_features first.")
    prices = pd.read_parquet(PRICE_PATH)
    features = pd.read_parquet(FEATURE_PATH)
    prices["date"] = pd.to_datetime(prices["date"])
    features["decision_available_date_raw"] = pd.to_datetime(features["decision_available_date_raw"])
    calendar = pd.DatetimeIndex(prices["date"].sort_values().unique())
    features["decision_available_date"] = features["decision_available_date_raw"].map(
        lambda value: business_day_after(calendar, value)
    )
    features = features.dropna(subset=["decision_available_date", "ticker"])

    decision_dates = last_trading_days(prices["date"])
    market_monthly = prices[prices["date"].isin(decision_dates)].copy()

    feature_parts = []
    keep_columns = [
        "ticker", "cik", "company_name", "sic2", "adsh", "form", "fy", "fp",
        "filed", "decision_available_date", "fundamental_feature_count"
    ] + FUNDAMENTAL_FEATURES
    for ticker, group in features[keep_columns].groupby("ticker", sort=False):
        left = pd.DataFrame({"decision_date": decision_dates})
        joined = pd.merge_asof(
            left,
            group.sort_values("decision_available_date"),
            left_on="decision_date",
            right_on="decision_available_date",
            direction="backward",
            tolerance=pd.Timedelta(days=max_staleness_days),
        )
        joined["ticker"] = ticker
        feature_parts.append(joined)
    latest = pd.concat(feature_parts, ignore_index=True)

    panel = market_monthly.merge(latest, left_on=["ticker", "date"], right_on=["ticker", "decision_date"], how="inner")
    panel = panel.drop(columns=["decision_date"]).rename(columns={"date": "decision_date"})
    panel = panel[
        panel["adj_close"].ge(3.0)
        & panel["dollar_volume_63"].ge(5_000_000)
        & panel["fundamental_feature_count"].ge(3)
        & panel["sic2"].notna()
    ].copy()

    for target in ["T20", "T63", "T126", "T252"]:
        sector_median = panel.groupby(["decision_date", "sic2"])[f"return_{target}"].transform("median")
        panel[f"sector_excess_{target}"] = panel[f"return_{target}"] - sector_median

    # Deterministic simple quality baseline. Direction signs are frozen here.
    quality_signs = {
        "revenue_growth_yoy": 1,
        "operating_margin": 1,
        "operating_margin_change_yoy": 1,
        "net_margin": 1,
        "cash_conversion": 1,
        "accrual_quality": 1,
        "leverage": -1,
        "shares_growth_yoy": -1,
    }
    quality_components = []
    for feature, sign in quality_signs.items():
        ranked = panel.groupby(["decision_date", "sic2"])[feature].rank(pct=True)
        quality_components.append(sign * (ranked - 0.5))
    panel["simple_quality"] = pd.concat(quality_components, axis=1).mean(axis=1, skipna=True)
    panel["size_proxy"] = np.log1p(panel["adj_close"] * panel.get("shares", np.nan)) if "shares" in panel else np.nan

    panel = panel.sort_values(["decision_date", "ticker"]).reset_index(drop=True)
    target = PROCESSED / "us_monthly_research_panel.parquet"
    panel.to_parquet(target, index=False)
    write_json(
        PROCESSED / "panel_build_receipt.json",
        {
            "rows": len(panel),
            "tickers": int(panel["ticker"].nunique()),
            "months": int(panel["decision_date"].nunique()),
            "date_min": str(panel["decision_date"].min().date()),
            "date_max": str(panel["decision_date"].max().date()),
            "median_names_per_month": float(panel.groupby("decision_date")["ticker"].nunique().median()),
            "fundamental_input_sha256": sha256_file(FEATURE_PATH),
            "price_input_sha256": sha256_file(PRICE_PATH),
            "output_sha256": sha256_file(target),
        },
    )
    print(f"Research panel: {len(panel):,} rows, {panel['decision_date'].nunique()} months, {panel['ticker'].nunique()} tickers.")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-staleness-days", type=int, default=200)
    args = parser.parse_args()
    build_panel(args.max_staleness_days)


if __name__ == "__main__":
    main()
