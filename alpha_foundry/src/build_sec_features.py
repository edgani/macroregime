from __future__ import annotations

import argparse
import zipfile
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

from .common import PROCESSED, RAW, sha256_file, write_json
from .build_entity_master import read_member

SEC_DIR = RAW / "sec_fsd"
ENTITY_PATH = PROCESSED / "entity_filing_master.parquet"

TAG_PRIORITY: dict[str, list[str]] = {
    "revenue": [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
    ],
    "gross_profit": ["GrossProfit"],
    "operating_income": ["OperatingIncomeLoss"],
    "net_income": ["NetIncomeLoss", "ProfitLoss"],
    "cfo": ["NetCashProvidedByUsedInOperatingActivities"],
    "capex": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsForAdditionsToPropertyPlantAndEquipment",
    ],
    "assets": ["Assets"],
    "liabilities": ["Liabilities"],
    "equity": ["StockholdersEquity", "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest"],
    "shares": ["EntityCommonStockSharesOutstanding", "CommonStockSharesOutstanding"],
}
TAG_TO_METRIC = {tag: metric for metric, tags in TAG_PRIORITY.items() for tag in tags}


def choose_metric_values(frame: pd.DataFrame) -> pd.DataFrame:
    priority = {tag: rank for metric, tags in TAG_PRIORITY.items() for rank, tag in enumerate(tags)}
    frame = frame.copy()
    frame["metric"] = frame["tag"].map(TAG_TO_METRIC)
    frame["tag_priority"] = frame["tag"].map(priority)
    frame = frame.sort_values(["adsh", "metric", "tag_priority", "ddate"], ascending=[True, True, True, False])
    return frame.drop_duplicates(["adsh", "metric"], keep="first")


def load_numeric_facts(entity: pd.DataFrame) -> pd.DataFrame:
    adsh_set = set(entity.loc[entity["ticker"].notna(), "adsh"].astype(str))
    pieces: list[pd.DataFrame] = []
    tags = set(TAG_TO_METRIC)
    usecols = {"adsh", "tag", "version", "ddate", "qtrs", "uom", "value", "coreg", "segments"}
    for path in sorted(SEC_DIR.glob("*.zip")):
        with zipfile.ZipFile(path) as archive:
            names = {name.lower(): name for name in archive.namelist()}
            member = names.get("num.txt") or names.get("num.tsv")
            if not member:
                raise KeyError(f"num file missing in {path}")
            for chunk in pd.read_csv(
                archive.open(member),
                sep="\t",
                low_memory=False,
                chunksize=500_000,
                usecols=lambda column: column in usecols,
            ):
                chunk = chunk[
                    chunk["adsh"].astype(str).isin(adsh_set)
                    & chunk["tag"].isin(tags)
                    & chunk["value"].notna()
                ]
                if "coreg" in chunk:
                    chunk = chunk[chunk["coreg"].isna() | chunk["coreg"].astype(str).eq("")]
                if "segments" in chunk:
                    chunk = chunk[chunk["segments"].isna() | chunk["segments"].astype(str).isin(["", "0"])]
                if not chunk.empty:
                    chunk["source_zip"] = path.name
                    pieces.append(chunk)
    if not pieces:
        raise RuntimeError("No relevant SEC numeric facts found.")
    facts = pd.concat(pieces, ignore_index=True)
    facts["ddate"] = pd.to_datetime(facts["ddate"].astype(str), errors="coerce")
    facts["qtrs"] = pd.to_numeric(facts["qtrs"], errors="coerce")
    facts["value"] = pd.to_numeric(facts["value"], errors="coerce")
    return facts.dropna(subset=["ddate", "value"])


def select_period_facts(entity: pd.DataFrame, facts: pd.DataFrame) -> pd.DataFrame:
    merged = facts.merge(
        entity[["adsh", "ticker", "cik", "company_name", "sic2", "form", "period", "fy", "fp", "filed", "accepted", "mapping_confidence"]],
        on="adsh",
        how="inner",
    )
    merged["period"] = pd.to_datetime(merged["period"].astype(str), errors="coerce")
    merged = merged[merged["ddate"].eq(merged["period"]) | merged["ddate"].between(merged["period"] - pd.Timedelta(days=10), merged["period"] + pd.Timedelta(days=10))]
    merged["metric"] = merged["tag"].map(TAG_TO_METRIC)

    instant = merged[merged["metric"].isin(["assets", "liabilities", "equity", "shares"]) & merged["qtrs"].eq(0)]
    duration = merged[~merged["metric"].isin(["assets", "liabilities", "equity", "shares"])]
    # Primary comparable periods: discrete quarter for 10-Q and full-year for 10-K.
    duration = duration[
        ((duration["form"].eq("10-Q")) & duration["qtrs"].eq(1))
        | ((duration["form"].eq("10-K")) & duration["qtrs"].eq(4))
    ]
    selected = choose_metric_values(pd.concat([instant, duration], ignore_index=True))
    wide = selected.pivot(index="adsh", columns="metric", values="value").reset_index()
    meta = entity[entity["ticker"].notna()].drop_duplicates("adsh")
    result = meta.merge(wide, on="adsh", how="left")
    return result


def safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denom = pd.to_numeric(denominator, errors="coerce")
    num = pd.to_numeric(numerator, errors="coerce")
    return (num / denom.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)


def calculate_features(frame: pd.DataFrame) -> pd.DataFrame:
    frame = frame.copy().sort_values(["ticker", "form", "fp", "fy", "filed"])
    for column in TAG_PRIORITY:
        if column not in frame:
            frame[column] = np.nan
    frame["operating_margin"] = safe_ratio(frame["operating_income"], frame["revenue"])
    frame["net_margin"] = safe_ratio(frame["net_income"], frame["revenue"])
    frame["cash_conversion"] = safe_ratio(frame["cfo"], frame["net_income"].abs())
    frame["accrual_quality"] = -safe_ratio(frame["net_income"] - frame["cfo"], frame["assets"])
    frame["leverage"] = safe_ratio(frame["liabilities"], frame["assets"])
    frame["capex_intensity"] = safe_ratio(frame["capex"], frame["revenue"])

    comparable_keys = ["ticker", "form", "fp"]
    previous = frame[comparable_keys + ["fy", "revenue", "operating_margin", "shares", "assets"]].copy()
    previous["fy"] = pd.to_numeric(previous["fy"], errors="coerce") + 1
    previous = previous.rename(
        columns={
            "revenue": "revenue_prior_year",
            "operating_margin": "operating_margin_prior_year",
            "shares": "shares_prior_year",
            "assets": "assets_prior_year",
        }
    )
    frame["fy"] = pd.to_numeric(frame["fy"], errors="coerce")
    frame = frame.merge(previous, on=comparable_keys + ["fy"], how="left")
    frame["revenue_growth_yoy"] = safe_ratio(frame["revenue"], frame["revenue_prior_year"]) - 1
    frame["operating_margin_change_yoy"] = frame["operating_margin"] - frame["operating_margin_prior_year"]
    frame["shares_growth_yoy"] = safe_ratio(frame["shares"], frame["shares_prior_year"]) - 1
    frame["assets_growth_yoy"] = safe_ratio(frame["assets"], frame["assets_prior_year"]) - 1

    feature_columns = [
        "revenue_growth_yoy", "operating_margin", "operating_margin_change_yoy",
        "net_margin", "cash_conversion", "accrual_quality", "leverage",
        "shares_growth_yoy", "capex_intensity", "assets_growth_yoy"
    ]
    frame["fundamental_feature_count"] = frame[feature_columns].notna().sum(axis=1)
    frame["decision_available_date_raw"] = pd.to_datetime(frame["filed"], errors="coerce") + pd.Timedelta(days=2)
    return frame


def build_sec_features() -> Path:
    if not ENTITY_PATH.exists():
        raise FileNotFoundError(f"Missing {ENTITY_PATH}; run build_entity_master first.")
    entity = pd.read_parquet(ENTITY_PATH)
    facts = load_numeric_facts(entity)
    filing = select_period_facts(entity, facts)
    features = calculate_features(filing)
    features = features[features["fundamental_feature_count"].ge(3)].copy()
    target = PROCESSED / "sec_filing_features.parquet"
    features.to_parquet(target, index=False)
    write_json(
        PROCESSED / "sec_features_receipt.json",
        {
            "rows": len(features),
            "tickers": int(features["ticker"].nunique()),
            "date_min": str(pd.to_datetime(features["filed"]).min().date()),
            "date_max": str(pd.to_datetime(features["filed"]).max().date()),
            "median_feature_count": float(features["fundamental_feature_count"].median()),
            "feature_coverage": {column: float(features[column].notna().mean()) for column in [
                "revenue_growth_yoy", "operating_margin", "operating_margin_change_yoy",
                "net_margin", "cash_conversion", "accrual_quality", "leverage", "shares_growth_yoy"
            ]},
            "input_entity_sha256": sha256_file(ENTITY_PATH),
            "output_sha256": sha256_file(target),
        },
    )
    print(f"SEC features: {len(features):,} filing observations across {features['ticker'].nunique():,} tickers.")
    return target


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    build_sec_features()


if __name__ == "__main__":
    main()
