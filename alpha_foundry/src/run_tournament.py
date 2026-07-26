from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

from .common import (
    OUTPUTS,
    PROCESSED,
    ROOT,
    append_csv,
    bh_qvalues,
    ensure_no_future_information,
    package_version_hash,
    sha256_file,
    sha256_json,
    utc_now,
    write_json,
    year_block_bootstrap_mean,
)

PANEL_PATH = PROCESSED / "us_monthly_research_panel.parquet"
CONTRACT_PATH = ROOT / "config" / "freeze_contract.json"
TRIAL_LEDGER = OUTPUTS / "discovery" / "TRIAL_GRAVEYARD.csv"

FUNDAMENTAL_FEATURES = [
    "revenue_growth_yoy", "operating_margin", "operating_margin_change_yoy",
    "net_margin", "cash_conversion", "accrual_quality", "leverage", "shares_growth_yoy"
]
MARKET_FEATURES = ["momentum_252_21", "reversal_20", "volatility_63", "drawdown_252", "log_dollar_volume_63"]


def monthly_rank_ic(frame: pd.DataFrame, score: str, target: str) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby("decision_date"):
        valid = group[[score, target]].dropna()
        if len(valid) < 20 or valid[score].nunique() < 3:
            continue
        ic = spearmanr(valid[score], valid[target]).statistic
        rows.append({"decision_date": date, "rank_ic": float(ic), "n": len(valid)})
    return pd.DataFrame(rows)


def monthly_topk(frame: pd.DataFrame, score: str, target: str, k: int = 20) -> pd.DataFrame:
    rows = []
    for date, group in frame.groupby("decision_date"):
        valid = group[["ticker", score, target]].dropna().sort_values(score, ascending=False)
        if len(valid) < max(40, k * 2):
            continue
        top = valid.head(k)
        bottom = valid.tail(k)
        rows.append(
            {
                "decision_date": date,
                "top_k_excess": float(top[target].mean()),
                "top_bottom_spread": float(top[target].mean() - bottom[target].mean()),
                "positive_top_k": bool(top[target].mean() > 0),
                "n": len(valid),
            }
        )
    return pd.DataFrame(rows)


def equal_weight_score(frame: pd.DataFrame, features: list[str]) -> pd.Series:
    parts = []
    signs = {"leverage": -1, "shares_growth_yoy": -1, "volatility_63": -1, "drawdown_252": 1}
    for feature in features:
        ranked = frame.groupby(["decision_date", "sic2"])[feature].rank(pct=True)
        parts.append(signs.get(feature, 1) * (ranked - 0.5))
    return pd.concat(parts, axis=1).mean(axis=1, skipna=True)


def ridge_wfa(frame: pd.DataFrame, features: list[str], target_id: str, period_end: str) -> pd.DataFrame:
    target = f"sector_excess_{target_id}"
    frame = frame[pd.to_datetime(frame["decision_date"]).le(pd.Timestamp(period_end))].copy()
    years = sorted(frame["decision_date"].dt.year.unique())
    predictions = []
    for test_year in years:
        test_start = pd.Timestamp(f"{test_year}-01-01")
        test_end = pd.Timestamp(f"{test_year}-12-31")
        test = frame[frame["decision_date"].between(test_start, test_end)]
        if test.empty or test_year < min(years) + 3:
            continue
        train = frame[
            frame["decision_date"].lt(test_start)
            & frame[f"outcome_date_{target_id}"].lt(test_start)
            & frame[target].notna()
        ].copy()
        if len(train) < 1000:
            continue
        ensure_no_future_information(train, test_start, target_id)
        model = Pipeline(
            [
                ("imputer", SimpleImputer(strategy="median", add_indicator=True)),
                ("scale", StandardScaler()),
                ("ridge", Ridge(alpha=10.0)),
            ]
        )
        model.fit(train[features], train[target])
        out = test[["decision_date", "ticker", "sic2", target, f"outcome_date_{target_id}"]].copy()
        out["score"] = model.predict(test[features])
        out["test_year"] = test_year
        predictions.append(out)
    return pd.concat(predictions, ignore_index=True) if predictions else pd.DataFrame()


def summarize_score(frame: pd.DataFrame, score: str, target: str, seed: int) -> dict[str, Any]:
    ic = monthly_rank_ic(frame, score, target)
    top = monthly_topk(frame, score, target)
    if ic.empty or top.empty:
        return {"months": 0}
    iterations = int(os.environ.get("WARROOM_BOOTSTRAPS", "3000"))
    ic_boot = year_block_bootstrap_mean(ic["rank_ic"], ic["decision_date"].dt.year, iterations, seed)
    top_boot = year_block_bootstrap_mean(top["top_k_excess"], top["decision_date"].dt.year, iterations, seed + 1)
    return {
        "months": len(ic),
        "mean_rank_ic": float(ic["rank_ic"].mean()),
        "rank_ic_positive_fraction": float((ic["rank_ic"] > 0).mean()),
        "rank_ic_bootstrap_low": ic_boot["low"],
        "rank_ic_bootstrap_high": ic_boot["high"],
        "rank_ic_p_gt_zero": ic_boot["p_gt_zero"],
        "mean_top20_excess": float(top["top_k_excess"].mean()),
        "top20_positive_fraction": float((top["top_k_excess"] > 0).mean()),
        "top20_bootstrap_low": top_boot["low"],
        "top20_bootstrap_high": top_boot["high"],
        "top20_p_gt_zero": top_boot["p_gt_zero"],
        "mean_top_bottom_spread": float(top["top_bottom_spread"].mean()),
    }


def log_trial(row: dict[str, Any]) -> None:
    fields = [
        "trial_id", "registered_at_utc", "target_id", "candidate", "candidate_family",
        "feature_bundle_hash", "period", "baseline", "months", "mean_rank_ic",
        "mean_top20_excess", "p_value", "q_value", "status", "claim_ceiling", "notes"
    ]
    if TRIAL_LEDGER.exists():
        existing = pd.read_csv(TRIAL_LEDGER, dtype=str)
        matched = existing[existing["trial_id"].eq(str(row["trial_id"]))]
        if not matched.empty:
            prior = matched.iloc[-1]
            identity_fields = ["target_id", "candidate", "candidate_family", "feature_bundle_hash", "period", "baseline"]
            if all(str(prior[field]) == str(row[field]) for field in identity_fields):
                return
            raise RuntimeError(f"trial_id collision with changed specification: {row['trial_id']}")
    append_csv(TRIAL_LEDGER, row, fields)


def run(period: str = "validation") -> dict[str, Any]:
    if not PANEL_PATH.exists():
        raise FileNotFoundError(PANEL_PATH)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    period_map = {
        "discovery": contract["discovery_period"][1],
        "validation": contract["validation_period"][1],
        "lockbox": contract["lockbox_period"][1],
    }
    period_end = period_map[period]
    frame = pd.read_parquet(PANEL_PATH)
    frame["decision_date"] = pd.to_datetime(frame["decision_date"])
    for target in contract["targets"]:
        frame[f"outcome_date_{target}"] = pd.to_datetime(frame[f"outcome_date_{target}"])

    candidates: dict[str, tuple[str, list[str] | None]] = {
        "momentum_baseline": ("baseline", None),
        "simple_quality": ("baseline", None),
    }
    for feature in FUNDAMENTAL_FEATURES:
        candidates[f"component__{feature}"] = ("component", [feature])
    candidates["equal_weight_quality"] = ("selector", FUNDAMENTAL_FEATURES)
    candidates["ridge_quality_plus_market"] = ("selector", FUNDAMENTAL_FEATURES + MARKET_FEATURES)

    result_rows: list[dict[str, Any]] = []
    prediction_dir = OUTPUTS / "discovery" / "predictions"
    prediction_dir.mkdir(parents=True, exist_ok=True)

    for target_index, target_id in enumerate(contract["targets"]):
        target = f"sector_excess_{target_id}"
        for candidate_index, (candidate, (family, features)) in enumerate(candidates.items()):
            if candidate == "momentum_baseline":
                evaluated = frame[frame["decision_date"].le(pd.Timestamp(period_end))].copy()
                evaluated["score_eval"] = evaluated["momentum_252_21"]
                score_column = "score_eval"
            elif candidate == "simple_quality":
                evaluated = frame[frame["decision_date"].le(pd.Timestamp(period_end))].copy()
                evaluated["score_eval"] = evaluated["simple_quality"]
                score_column = "score_eval"
            elif candidate.startswith("component__"):
                evaluated = frame[frame["decision_date"].le(pd.Timestamp(period_end))].copy()
                feature = features[0]
                direction = -1 if feature in {"leverage", "shares_growth_yoy"} else 1
                evaluated["score_eval"] = direction * evaluated.groupby(["decision_date", "sic2"])[feature].rank(pct=True)
                score_column = "score_eval"
            elif candidate == "equal_weight_quality":
                evaluated = frame[frame["decision_date"].le(pd.Timestamp(period_end))].copy()
                evaluated["score_eval"] = equal_weight_score(evaluated, features)
                score_column = "score_eval"
            else:
                evaluated = ridge_wfa(frame, features, target_id, period_end)
                if evaluated.empty:
                    summary = {"months": 0}
                    score_column = "score"
                else:
                    score_column = "score"
                    evaluated.to_parquet(prediction_dir / f"{candidate}__{target_id}.parquet", index=False)
            summary = summarize_score(evaluated, score_column, target, 20260717 + target_index * 100 + candidate_index)
            row = {
                "target_id": target_id,
                "candidate": candidate,
                "candidate_family": family,
                "feature_bundle_hash": sha256_json(features or [candidate]),
                "period": period,
                "period_end": period_end,
                **summary,
            }
            result_rows.append(row)

    results = pd.DataFrame(result_rows)
    valid = results["months"].fillna(0).gt(0)
    results["p_value"] = np.nan
    results.loc[valid, "p_value"] = results.loc[valid, ["rank_ic_p_gt_zero", "top20_p_gt_zero"]].max(axis=1)
    results["q_value"] = np.nan
    if valid.any():
        results.loc[valid, "q_value"] = bh_qvalues(results.loc[valid, "p_value"].fillna(1.0))

    momentum = results[results["candidate"].eq("momentum_baseline")][["target_id", "mean_rank_ic", "mean_top20_excess"]].rename(
        columns={"mean_rank_ic": "momentum_rank_ic", "mean_top20_excess": "momentum_top20_excess"}
    )
    results = results.merge(momentum, on="target_id", how="left")
    results["incremental_rank_ic_vs_momentum"] = results["mean_rank_ic"] - results["momentum_rank_ic"]
    results["incremental_top20_vs_momentum"] = results["mean_top20_excess"] - results["momentum_top20_excess"]
    results["promotion_pass"] = (
        results["months"].ge(24)
        & results["rank_ic_positive_fraction"].ge(0.55)
        & results["top20_positive_fraction"].ge(0.55)
        & results["q_value"].lt(0.10)
        & results["incremental_rank_ic_vs_momentum"].gt(0)
        & results["incremental_top20_vs_momentum"].gt(0)
        & ~results["candidate"].eq("momentum_baseline")
    )
    results["maximum_status"] = np.where(results["promotion_pass"], "HISTORICAL_CANDIDATE", "DROP_OR_CONTEXT")

    out_dir = OUTPUTS / ("lockbox" if period == "lockbox" else "discovery")
    out_dir.mkdir(parents=True, exist_ok=True)
    result_path = out_dir / f"COMPONENT_SELECTOR_TOURNAMENT__{period.upper()}.csv"
    results.to_csv(result_path, index=False)

    for index, row in results.iterrows():
        log_trial(
            {
                "trial_id": f"US-{period.upper()}-{row['target_id']}-{index:03d}",
                "registered_at_utc": utc_now(),
                "target_id": row["target_id"],
                "candidate": row["candidate"],
                "candidate_family": row["candidate_family"],
                "feature_bundle_hash": row["feature_bundle_hash"],
                "period": period,
                "baseline": "momentum_baseline",
                "months": row.get("months", 0),
                "mean_rank_ic": row.get("mean_rank_ic", np.nan),
                "mean_top20_excess": row.get("mean_top20_excess", np.nan),
                "p_value": row.get("p_value", np.nan),
                "q_value": row.get("q_value", np.nan),
                "status": row["maximum_status"],
                "claim_ceiling": "HISTORICAL_CANDIDATE_MAX",
                "notes": "All registered candidates remain in the graveyard regardless of result.",
            }
        )

    summary = {
        "run_at_utc": utc_now(),
        "period": period,
        "panel_sha256": sha256_file(PANEL_PATH),
        "contract_sha256": package_version_hash(),
        "registered_trials": len(results),
        "historical_candidates": int(results["promotion_pass"].sum()),
        "proven_components": 0,
        "proven_selectors": 0,
        "claim_ceiling": "HISTORICAL_CANDIDATE",
        "results_file": str(result_path.relative_to(ROOT)),
    }
    write_json(out_dir / f"TOURNAMENT_SUMMARY__{period.upper()}.json", summary)
    print(json.dumps(summary, indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", choices=["discovery", "validation", "lockbox"], default="validation")
    args = parser.parse_args()
    run(args.period)


if __name__ == "__main__":
    main()
