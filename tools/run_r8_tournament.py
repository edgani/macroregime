"""tools/run_r8_tournament.py — R8 extreme winner/loser tournament.

Runs ONLY the pre-registered baseline (baseline_momentum_topk) as a measurement
reference. Causal discovery families are DATA_GATED (see prereg_r8.json) — they
produce no rankings. SNDK/PLTR/SPXC are never inputs to the ranker.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

CASE_TICKERS = {"SNDK", "PLTR", "SPXC"}  # evaluation-only; excluded from ranker inputs


def load_closes() -> pd.DataFrame:
    px = pd.read_parquet(ROOT / "cache" / "prices.parquet")
    closes = px.xs("Close", axis=1, level=1) if isinstance(px.columns, pd.MultiIndex) else px
    closes = closes.drop(columns=[c for c in CASE_TICKERS if c in closes.columns], errors="ignore")
    # tolerate NaN gaps (different listing ages); drop columns with non-positive values
    # or insufficient history for a 63d signal + 12m outcome
    keep = [c for c in closes.columns
            if closes[c].notna().sum() >= 126 and (closes[c].dropna() > 0).all()]
    return closes[keep]


def decision_grid(closes: pd.DataFrame) -> list:
    idx = closes.index
    months = pd.date_range(idx[0] + pd.Timedelta(days=63), idx[-1] - pd.Timedelta(days=366), freq="MS")
    return [idx[idx >= m][0] for m in months if (idx >= m).any()]


def run_trial(closes: pd.DataFrame, k: int, horizon_days: int = 252) -> dict:
    rets63 = closes.pct_change(63)
    per_date = []
    for d in decision_grid(closes):
        sig = rets63.loc[d].dropna().sort_values(ascending=False)
        topk = list(sig.index[:k])
        future = closes.loc[d:].iloc[1:horizon_days + 1]
        if future.empty:
            continue
        fwd = future / closes.loc[d] - 1.0
        win_mask = (fwd >= 1.0).any(axis=0)          # +100% within horizon
        winners = set(win_mask[win_mask].index)
        hits = [t for t in topk if t in winners]
        base_rate = float(win_mask.mean())
        precision = len(hits) / k
        recall = len(hits) / max(len(winners), 1)
        # MAE/MFE/lead/remaining for picks
        mae, mfe, lead, remaining = [], [], [], []
        for t in topk:
            path = fwd[t].dropna()
            if path.empty:
                continue
            mae.append(float(path.min()) * 100)
            mfe.append(float(path.max()) * 100)
            cross = path[path >= 1.0]
            if not cross.empty:
                lead.append((cross.index[0] - d).days)
                remaining.append((float(path.max()) - 1.0) * 100)  # peak above the +100% crossing
        per_date.append({
            "date": str(d.date()), "k": k,
            "precision_at_k": round(precision, 4), "recall_at_k": round(recall, 4),
            "base_rate": round(base_rate, 4),
            "lift_vs_random": round(precision / base_rate, 3) if base_rate > 0 else None,
            "winners_total": len(winners),
            "mae_pct": round(float(np.mean(mae)), 2) if mae else None,
            "mfe_pct": round(float(np.mean(mfe)), 2) if mfe else None,
            "lead_time_days": round(float(np.mean(lead)), 1) if lead else None,
            "remaining_return_pct": round(float(np.mean(remaining)), 2) if remaining else None,
            "false_discovery_rate": round(1 - precision, 4),
        })
    if not per_date:
        return {"k": k, "error": "no decision dates"}
    agg = {m: round(float(np.nanmean([r[m] for r in per_date if r[m] is not None])), 4)
           for m in ("precision_at_k", "recall_at_k", "lift_vs_random", "mae_pct", "mfe_pct",
                     "lead_time_days", "remaining_return_pct", "false_discovery_rate")}
    # regime stability: half-year buckets
    regimes = {}
    for r in per_date:
        y, mo = int(r["date"][:4]), int(r["date"][5:7])
        key = f"{y}H{1 if mo <= 6 else 2}"
        regimes.setdefault(key, []).append(r["precision_at_k"])
    agg["regime_precision"] = {k2: round(float(np.mean(v)), 3) for k2, v in sorted(regimes.items())}
    agg["n_decision_dates"] = len(per_date)
    return {"k": k, "aggregate": agg, "per_decision_date": per_date}


def main():
    from warroom.research.ledger import TrialLedger
    prereg = json.loads((ROOT / "data/research/prereg_r8.json").read_text())
    closes = load_closes()
    print(f"universe {len(closes.columns)} tickers (case tickers excluded), "
          f"{closes.index[0].date()}..{closes.index[-1].date()}")
    ledger = TrialLedger(ROOT / "data/research/trial_ledger.jsonl")
    results = []
    for k in prereg["top_k"]:
        r = run_trial(closes, k)
        results.append(r)
        verdict = ("BASELINE_MEASURED — reference only; not alpha; precision/lift are the bar "
                   "any causal family must beat with admitted data")
        ledger.record({"market": "us", "family": "us.baseline_momentum_topk",
                       "parameters": {"K": k, "horizon_days": 252, "signal": "63d return rank"},
                       "results": r.get("aggregate", {}),
                       "sample": {"decision_dates": r.get("aggregate", {}).get("n_decision_dates")},
                       "verdict": verdict,
                       "notes": f"R8 measurement baseline; case tickers excluded; prereg hash {prereg['frozen_hash'][:12]}",
                       "lockbox_touched": False,
                       "honest_limits": ["active-only universe (survivor bias, see R8_UNIVERSE_REPORT)",
                                         "measurement baseline only; weight 0; not alpha"]})
        print(f"K={k}: P@K={r['aggregate']['precision_at_k']} R@K={r['aggregate']['recall_at_k']} "
              f"lift={r['aggregate']['lift_vs_random']} lead={r['aggregate']['lead_time_days']}d "
              f"FDR={r['aggregate']['false_discovery_rate']}")
    out = {"schema": "warroom.r8_tournament.v1", "prereg_hash": prereg["frozen_hash"],
           "universe": {"size": len(closes.columns),
                        "range": [str(closes.index[0].date()), str(closes.index[-1].date())],
                        "case_tickers_excluded": sorted(CASE_TICKERS)},
           "baseline_results": results,
           "causal_families": [{"family_id": f["family_id"], "status": f["status"],
                                "reason": f.get("reason")}
                               for f in prereg["candidate_families"] if f["status"] == "DATA_GATED"],
           "honesty_note": ("momentum baseline is measurement-only (weight 0). Causal extreme-winner "
                            "detection is DATA_GATED: no Top-K causal ranking exists, so no detection "
                            "claim is made for SNDK/PLTR/SPXC or any cohort member.")}
    (ROOT / "data/research/r8_tournament_results.json").write_text(json.dumps(out, indent=1))
    print("results -> data/research/r8_tournament_results.json")


if __name__ == "__main__":
    main()
