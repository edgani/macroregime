from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from src.run_tournament import equal_weight_score, ridge_wfa

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs" / "synthetic_demo"
OUT.mkdir(parents=True, exist_ok=True)

rng = np.random.default_rng(20260717)
dates = pd.date_range("2016-01-29", "2024-12-31", freq="ME")
tickers = [f"SYN{i:03d}" for i in range(70)]
rows = []
for date in dates:
    for index, ticker in enumerate(tickers):
        latent = rng.normal()
        target = 0.03 * latent + rng.normal(scale=0.05)
        rows.append(
            {
                "decision_date": date,
                "ticker": ticker,
                "sic2": index % 7,
                "revenue_growth_yoy": latent + rng.normal(scale=0.3),
                "operating_margin": latent + rng.normal(scale=0.3),
                "operating_margin_change_yoy": latent + rng.normal(scale=0.3),
                "net_margin": latent + rng.normal(scale=0.4),
                "cash_conversion": latent + rng.normal(scale=0.4),
                "accrual_quality": latent + rng.normal(scale=0.4),
                "leverage": -latent + rng.normal(scale=0.4),
                "shares_growth_yoy": -latent + rng.normal(scale=0.4),
                "momentum_252_21": rng.normal(),
                "reversal_20": rng.normal(),
                "volatility_63": rng.uniform(0.01, 0.06),
                "drawdown_252": -rng.uniform(0, 0.5),
                "log_dollar_volume_63": rng.normal(16, 1),
                "sector_excess_T63": target,
                "outcome_date_T63": date + pd.offsets.BDay(63),
            }
        )
panel = pd.DataFrame(rows)
quality_features = [
    "revenue_growth_yoy", "operating_margin", "operating_margin_change_yoy", "net_margin",
    "cash_conversion", "accrual_quality", "leverage", "shares_growth_yoy",
]
panel["equal_weight_score"] = equal_weight_score(panel, quality_features)
preds = ridge_wfa(panel, quality_features + ["momentum_252_21", "reversal_20", "volatility_63", "drawdown_252", "log_dollar_volume_63"], "T63", "2024-12-31")
monthly = []
for date, group in preds.groupby("decision_date"):
    monthly.append({"decision_date": date, "rank_ic": spearmanr(group["score"], group["sector_excess_T63"]).statistic})
monthly_frame = pd.DataFrame(monthly)
preds.to_csv(OUT / "SYNTHETIC_WFA_PREDICTIONS.csv", index=False)
monthly_frame.to_csv(OUT / "SYNTHETIC_MONTHLY_IC.csv", index=False)
summary = {
    "status": "SYNTHETIC_ENGINEERING_ONLY",
    "rows": len(panel),
    "oos_predictions": len(preds),
    "oos_months": len(monthly_frame),
    "mean_rank_ic": float(monthly_frame["rank_ic"].mean()),
    "purpose": "Proves the pipeline can recover an injected causal signal without granting any real-market claim.",
}
(OUT / "SYNTHETIC_DEMO_SUMMARY.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
print(json.dumps(summary, indent=2))
