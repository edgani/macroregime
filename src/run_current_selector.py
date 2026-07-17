from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .common import OUTPUTS, PROCESSED, ROOT, package_version_hash, sha256_file, sha256_json, utc_now, write_json

PANEL_PATH = PROCESSED / "us_monthly_research_panel.parquet"
CONTRACT_PATH = ROOT / "config" / "freeze_contract.json"
FEATURES = [
    "revenue_growth_yoy", "operating_margin", "operating_margin_change_yoy", "net_margin",
    "cash_conversion", "accrual_quality", "leverage", "shares_growth_yoy",
    "momentum_252_21", "reversal_20", "volatility_63", "drawdown_252", "log_dollar_volume_63"
]


def train_current(target_id: str = "T63", top_k: int = 20) -> Path:
    if not PANEL_PATH.exists():
        raise FileNotFoundError(PANEL_PATH)
    panel = pd.read_parquet(PANEL_PATH)
    panel["decision_date"] = pd.to_datetime(panel["decision_date"])
    panel[f"outcome_date_{target_id}"] = pd.to_datetime(panel[f"outcome_date_{target_id}"])
    latest_date = panel["decision_date"].max()
    target = f"sector_excess_{target_id}"
    train = panel[
        panel[f"outcome_date_{target_id}"].lt(latest_date)
        & panel[target].notna()
        & panel["decision_date"].lt(latest_date)
    ].copy()
    current = panel[panel["decision_date"].eq(latest_date)].copy()
    if len(train) < 1000 or len(current) < 40:
        raise RuntimeError(f"insufficient current selector data: train={len(train)}, current={len(current)}")

    model = Pipeline([
        ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
        ("scale", StandardScaler()),
        ("ridge", Ridge(alpha=10.0)),
    ])
    model.fit(train[FEATURES], train[target])
    current["selector_score"] = model.predict(current[FEATURES])
    current["sector_rank_pct"] = current.groupby("sic2")["selector_score"].rank(pct=True)
    current["overall_rank"] = current["selector_score"].rank(method="first", ascending=False).astype(int)
    current["why_in"] = current.apply(
        lambda row: "; ".join(
            name for name, value in sorted(
                {
                    "revenue_growth": row.get("revenue_growth_yoy"),
                    "margin": row.get("operating_margin_change_yoy"),
                    "cash_quality": row.get("accrual_quality"),
                    "momentum": row.get("momentum_252_21"),
                }.items(),
                key=lambda item: (-999 if pd.isna(item[1]) else item[1]),
                reverse=True,
            )[:3]
        ),
        axis=1,
    )
    output_columns = [
        "decision_date", "ticker", "company_name", "sic2", "overall_rank", "sector_rank_pct",
        "selector_score", "adj_close", "dollar_volume_63", "revenue_growth_yoy",
        "operating_margin", "operating_margin_change_yoy", "cash_conversion", "accrual_quality",
        "leverage", "shares_growth_yoy", "momentum_252_21", "volatility_63", "drawdown_252",
        "why_in", "adsh", "filed"
    ]
    shortlist = current.sort_values("selector_score", ascending=False).head(top_k)[output_columns].copy()
    out_dir = OUTPUTS / "current"
    out_dir.mkdir(parents=True, exist_ok=True)
    target_path = out_dir / "US_TOP20_SHADOW_SHORTLIST.csv"
    shortlist.to_csv(target_path, index=False)

    model_identity = {
        "class": "Ridge",
        "alpha": 10.0,
        "features": FEATURES,
        "target": target_id,
        "train_rows": len(train),
        "train_date_min": str(train["decision_date"].min().date()),
        "train_date_max": str(train["decision_date"].max().date()),
        "latest_date": str(latest_date.date()),
    }
    receipt = {
        "created_at_utc": utc_now(),
        "decision_date": str(latest_date.date()),
        "status": "SHADOW_RESEARCH_ONLY",
        "claim_ceiling": "NOT_PROVEN_NOT_PAPER_NOT_LIVE",
        "panel_sha256": sha256_file(PANEL_PATH),
        "contract_sha256": package_version_hash(),
        "model_hash": sha256_json(model_identity),
        "shortlist_sha256": sha256_file(target_path),
        "top_k": top_k,
        "tickers": shortlist["ticker"].tolist(),
        "warning": "This is an operational shadow shortlist. It is not proven alpha until lockbox and prospective gates pass.",
    }
    write_json(out_dir / "US_TOP20_SHADOW_RECEIPT.json", receipt)
    print(json.dumps(receipt, indent=2))
    return target_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", default="T63", choices=["T20", "T63", "T126", "T252"])
    parser.add_argument("--top-k", type=int, default=20)
    args = parser.parse_args()
    train_current(args.target, args.top_k)


if __name__ == "__main__":
    main()
