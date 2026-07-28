from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from cusp_fragility_v73 import (
    CuspEstimator,
    build_monthly_frame,
    cusp_geometry,
    decision_metrics,
    fit_logistic,
    gaussian_fit,
    gaussian_logpdf,
    probability_metrics,
    quadratic_expand,
    sha256_file,
    simultaneous_bootstrap_lower,
)
from research_v55.flat_parquet_snappy import read_flat_parquet

PROTOCOL = ROOT / "research_v57/V73_CUSP_STRUCTURAL_FRAGILITY_PROTOCOL_FROZEN.json"
SPEC = ROOT / "research_v57/V73_IMPLEMENTATION_SPEC_FROZEN.json"
RECEIPT = ROOT / "research_v57/V73_LOCKBOX_OPEN_RECEIPT.json"
RESULT = ROOT / "research_v57/results/V73_CUSP_HISTORICAL_RESULTS.json"
PREDICTIONS = ROOT / "research_v57/results/V73_MONTHLY_PREDICTIONS.csv"

BASE = ["rv12", "drawdown12", "trend12", "log_cape", "real_rate", "dxy12", "gold12"]
ALPHA = ["real_rate", "drawdown12", "cpi_yoy_change12"]
BETA = ["log_cape", "trend12", "gold_minus_dxy_12"]


def per_obs_logloss(y: np.ndarray, p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 0.999999)
    return -(y * np.log(p) + (1 - y) * np.log(1 - p))


def split_mask(index: pd.DatetimeIndex, start: str, end: str) -> np.ndarray:
    return (index >= pd.Timestamp(start)) & (index <= pd.Timestamp(end))


def model_eval(name: str, model, x_train, y_train, splits: Dict[str, tuple[np.ndarray, np.ndarray]]):
    p_train = model.predict_proba(x_train)[:, 1]
    out = {"train": {"probability": probability_metrics(y_train, p_train)}}
    probs = {"train": p_train}
    for s, (x, y) in splits.items():
        p = model.predict_proba(x)[:, 1]
        probs[s] = p
        out[s] = {
            "probability": probability_metrics(y, p),
            "decision": decision_metrics(y_train, p_train, y, p, len(y)),
        }
    return out, probs


def gate_for_probs(yv, yl, pbv, pbl, pcv, pcl):
    arrays = [
        (yv - pbv) ** 2 - (yv - pcv) ** 2,
        per_obs_logloss(yv, pbv) - per_obs_logloss(yv, pcv),
        (yl - pbl) ** 2 - (yl - pcl) ** 2,
        per_obs_logloss(yl, pbl) - per_obs_logloss(yl, pcl),
    ]
    boot = simultaneous_bootstrap_lower(arrays, resamples=4000, block=12, seed=730073)
    return arrays, boot


def main() -> None:
    if RESULT.exists():
        raise SystemExit("V73 real outcome already exists; one-time lockbox cannot be rerun or overwritten")
    if not RECEIPT.exists():
        raise SystemExit("Missing one-time V73 lockbox receipt")
    receipt = json.loads(RECEIPT.read_text())
    checks = {
        "protocol_hash": sha256_file(PROTOCOL) == receipt["protocol_sha256"],
        "implementation_hash": sha256_file(SPEC) == receipt["implementation_sha256"],
        "runner_hash": sha256_file(__file__) == receipt["runner_sha256"],
        "macro_hash": sha256_file(ROOT / "research/macro_panel.parquet") == receipt["macro_panel_sha256"],
    }
    if not all(checks.values()):
        raise SystemExit(f"Lockbox receipt mismatch: {checks}")

    macro = read_flat_parquet(ROOT / "research/macro_panel.parquet")
    frame = build_monthly_frame(macro)
    needed = ["state_z", "target"] + BASE + ALPHA + BETA
    frame = frame.dropna(subset=sorted(set(needed))).copy()

    masks = {
        "train": split_mask(frame.index, "1973-01-01", "1999-12-01"),
        "validation": split_mask(frame.index, "2000-07-01", "2011-12-01"),
        "lockbox": split_mask(frame.index, "2012-07-01", "2023-03-01"),
    }
    for k, m in masks.items():
        if int(m.sum()) < 50:
            raise RuntimeError(f"Insufficient {k} rows: {m.sum()}")
    train = frame.loc[masks["train"]]
    validation = frame.loc[masks["validation"]]
    lockbox = frame.loc[masks["lockbox"]]

    ztr = train["state_z"].to_numpy(float)
    xa_tr = train[ALPHA].to_numpy(float)
    xb_tr = train[BETA].to_numpy(float)
    estimator = CuspEstimator()
    fit = estimator.fit(ztr, xa_tr, xb_tr, starts=(0, 1, 2, 3))

    all_xa = frame[ALPHA].to_numpy(float)
    all_xb = frame[BETA].to_numpy(float)
    alpha, beta = estimator.alpha_beta(fit, all_xa, all_xb)
    xa_std, xb_std = estimator.transform_controls(fit, all_xa, all_xb)
    omega0, logw = fit.params[0], fit.params[1]
    state_y = omega0 + math.exp(logw) * frame["state_z"].to_numpy(float)
    geometry = cusp_geometry(alpha, beta, state_y)
    geometry_names = ["inside_bifurcation", "signed_fold_distance", "inverse_stability_margin", "stable_mode_separation"]
    for i, n in enumerate(geometry_names):
        frame[n] = geometry[:, i]
    frame["cusp_alpha"] = alpha
    frame["cusp_beta"] = beta

    # Structural predictive density against smooth alternatives, fitted on training only.
    controls = np.column_stack([all_xa, all_xb])
    tr_ix = np.where(masks["train"])[0]
    va_ix = np.where(masks["validation"])[0]
    lo_ix = np.where(masks["lockbox"])[0]
    cusp_lp = estimator.score_samples(fit, frame["state_z"].to_numpy(float), all_xa, all_xb)
    lin_coef, lin_sig = gaussian_fit(controls[tr_ix], frame["state_z"].to_numpy(float)[tr_ix])
    lin_lp = gaussian_logpdf(controls, frame["state_z"].to_numpy(float), lin_coef, lin_sig)
    q_controls = quadratic_expand(controls)
    quad_coef, quad_sig = gaussian_fit(q_controls[tr_ix], frame["state_z"].to_numpy(float)[tr_ix])
    quad_lp = gaussian_logpdf(q_controls, frame["state_z"].to_numpy(float), quad_coef, quad_sig)
    k_cusp = len(fit.params)
    k_lin = len(lin_coef) + 1
    k_quad = len(quad_coef) + 1
    structural = {
        "train": {
            "cusp_mean_log_density": float(cusp_lp[tr_ix].mean()),
            "linear_mean_log_density": float(lin_lp[tr_ix].mean()),
            "quadratic_mean_log_density": float(quad_lp[tr_ix].mean()),
            "cusp_bic": float(-2 * cusp_lp[tr_ix].sum() + k_cusp * math.log(len(tr_ix))),
            "linear_bic": float(-2 * lin_lp[tr_ix].sum() + k_lin * math.log(len(tr_ix))),
            "quadratic_bic": float(-2 * quad_lp[tr_ix].sum() + k_quad * math.log(len(tr_ix))),
        },
        "validation": {
            "cusp_mean_log_density": float(cusp_lp[va_ix].mean()),
            "linear_mean_log_density": float(lin_lp[va_ix].mean()),
            "quadratic_mean_log_density": float(quad_lp[va_ix].mean()),
        },
        "lockbox": {
            "cusp_mean_log_density": float(cusp_lp[lo_ix].mean()),
            "linear_mean_log_density": float(lin_lp[lo_ix].mean()),
            "quadratic_mean_log_density": float(quad_lp[lo_ix].mean()),
        },
    }
    structural_pass = all(
        structural[s]["cusp_mean_log_density"] > structural[s][chall]
        for s in ("validation", "lockbox")
        for chall in ("linear_mean_log_density", "quadratic_mean_log_density")
    )

    x_base = frame[BASE].to_numpy(float)
    x_cusp = np.column_stack([x_base, geometry])
    x_smooth = np.column_stack([x_base, alpha, beta, alpha**2, beta**2, alpha * beta])
    y = frame["target"].to_numpy(int)

    rng = np.random.default_rng(730074)
    perm = rng.permutation(len(frame))
    geo_shuffle = geometry[perm]
    geo_shift = np.roll(geometry, 60, axis=0)
    x_shuffle = np.column_stack([x_base, geo_shuffle])
    x_shift = np.column_stack([x_base, geo_shift])

    models = {
        "baseline": (fit_logistic(x_base[tr_ix], y[tr_ix]), x_base),
        "cusp": (fit_logistic(x_cusp[tr_ix], y[tr_ix]), x_cusp),
        "smooth": (fit_logistic(x_smooth[tr_ix], y[tr_ix]), x_smooth),
        "shuffle_placebo": (fit_logistic(x_shuffle[tr_ix], y[tr_ix]), x_shuffle),
        "shift60_placebo": (fit_logistic(x_shift[tr_ix], y[tr_ix]), x_shift),
    }

    metrics = {}
    probs = {}
    split_y = {"validation": y[va_ix], "lockbox": y[lo_ix]}
    for name, (model, xx) in models.items():
        m, p = model_eval(
            name,
            model,
            xx[tr_ix],
            y[tr_ix],
            {"validation": (xx[va_ix], y[va_ix]), "lockbox": (xx[lo_ix], y[lo_ix])},
        )
        metrics[name] = m
        probs[name] = p

    _, boot = gate_for_probs(split_y["validation"], split_y["lockbox"], probs["baseline"]["validation"], probs["baseline"]["lockbox"], probs["cusp"]["validation"], probs["cusp"]["lockbox"])
    _, boot_shuffle = gate_for_probs(split_y["validation"], split_y["lockbox"], probs["baseline"]["validation"], probs["baseline"]["lockbox"], probs["shuffle_placebo"]["validation"], probs["shuffle_placebo"]["lockbox"])
    _, boot_shift = gate_for_probs(split_y["validation"], split_y["lockbox"], probs["baseline"]["validation"], probs["baseline"]["lockbox"], probs["shift60_placebo"]["validation"], probs["shift60_placebo"]["lockbox"])

    point_positive = all(v > 0 for v in boot["observed"])
    simultaneous_positive = all(v > 0 for v in boot["simultaneous_lower"])
    smooth_not_better = True
    for s in ("validation", "lockbox"):
        for metric in ("brier", "log_loss"):
            if metrics["cusp"][s]["probability"][metric] > metrics["smooth"][s]["probability"][metric] + 1e-12:
                smooth_not_better = False
    ece_ok = all(metrics["cusp"][s]["probability"]["ece"] <= metrics["baseline"][s]["probability"]["ece"] + 0.01 for s in ("validation", "lockbox"))
    decision_ok = all(metrics["cusp"][s]["decision"]["cluster_recall"] >= metrics["baseline"][s]["decision"]["cluster_recall"] for s in ("validation", "lockbox"))
    placebo_shuffle_pass = all(v > 0 for v in boot_shuffle["simultaneous_lower"])
    placebo_shift_pass = all(v > 0 for v in boot_shift["simultaneous_lower"])

    gates = {
        "structural_density_pass": structural_pass,
        "all_four_point_improvements_positive": point_positive,
        "simultaneous_adjusted_lower_bounds_positive": simultaneous_positive,
        "cusp_not_worse_than_smooth_challenger": smooth_not_better,
        "ece_not_worse_by_more_than_0_01": ece_ok,
        "equal_burden_cluster_recall_not_lower": decision_ok,
        "shuffle_placebo_does_not_pass": not placebo_shuffle_pass,
        "shift60_placebo_does_not_pass": not placebo_shift_pass,
    }
    promoted = all(gates.values())

    pred = pd.DataFrame(index=frame.index)
    pred["target"] = y
    pred["fwd_min_6m"] = frame["fwd_min_6m"]
    pred["alpha"] = alpha
    pred["beta"] = beta
    pred["cardan_delta"] = alpha**2 / 4.0 - beta**3 / 27.0
    for i, n in enumerate(geometry_names):
        pred[n] = geometry[:, i]
    for name in models:
        fullp = np.full(len(frame), np.nan)
        fullp[tr_ix] = probs[name]["train"]
        fullp[va_ix] = probs[name]["validation"]
        fullp[lo_ix] = probs[name]["lockbox"]
        pred[f"p_{name}"] = fullp
    pred.to_csv(PREDICTIONS, index_label="date")

    result = {
        "study_id": "V73_CUSP_STRUCTURAL_FRAGILITY_HISTORICAL",
        "receipt_checks": checks,
        "source_rows": int(len(frame)),
        "split_rows": {k: int(v.sum()) for k, v in masks.items()},
        "split_positive_months": {"train": int(y[tr_ix].sum()), "validation": int(y[va_ix].sum()), "lockbox": int(y[lo_ix].sum())},
        "cusp_fit": {
            "success": fit.success,
            "nll": fit.nll,
            "message": fit.message,
            "params": fit.params.tolist(),
            "starts": fit.starts,
            "alpha_standardizer": {"mean": fit.alpha_std.mean.tolist(), "std": fit.alpha_std.std.tolist()},
            "beta_standardizer": {"mean": fit.beta_std.mean.tolist(), "std": fit.beta_std.std.tolist()},
        },
        "structural_fit": structural,
        "metrics": metrics,
        "simultaneous_bootstrap": boot,
        "placebo_bootstrap": {"shuffle": boot_shuffle, "shift60": boot_shift},
        "gates": gates,
        "promoted_historical": promoted,
        "live_decision_weight": 0.0,
        "capital_permission": "BLOCKED",
        "verdict": "NARROW_HISTORICAL_SUPPORT_ONLY" if promoted else "NOT_PROVEN",
        "limitations": [
            "Monthly data and bundled proxies are not an exact replication of intraday realized-volatility cusp literature.",
            "No historical credit-spread, signed dealer-position, or broad-market breadth series is added after outcome opening.",
            "Even a historical pass cannot authorize live capital without matured prospective evidence.",
        ],
        "artifacts": {"predictions": str(PREDICTIONS.relative_to(ROOT)), "protocol": str(PROTOCOL.relative_to(ROOT)), "implementation": str(SPEC.relative_to(ROOT))},
    }
    RESULT.write_text(json.dumps(result, indent=2, sort_keys=True))
    print(json.dumps({"verdict": result["verdict"], "promoted_historical": promoted, "gates": gates, "split_rows": result["split_rows"], "split_positive_months": result["split_positive_months"], "bootstrap": boot}, indent=2))


if __name__ == "__main__":
    main()
