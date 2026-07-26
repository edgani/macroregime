from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import logsumexp
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, log_loss, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

EPS = 1e-12


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def trailing_rms_prior(x: pd.Series, window: int) -> pd.Series:
    return x.shift(1).pow(2).rolling(window, min_periods=window).mean().pow(0.5)


def future_min_return(price: pd.Series, horizon: int) -> pd.Series:
    arr = price.to_numpy(dtype=float)
    out = np.full(len(arr), np.nan)
    for i in range(len(arr) - horizon):
        out[i] = np.nanmin(arr[i + 1 : i + horizon + 1]) / arr[i] - 1.0
    return pd.Series(out, index=price.index)


def build_monthly_frame(macro: pd.DataFrame) -> pd.DataFrame:
    df = macro.copy().sort_index()
    df = df.loc["1972-01-01":"2023-09-01"].copy()
    log_spx = np.log(df["spx"].astype(float))
    ret1 = log_spx.diff()
    rms12 = trailing_rms_prior(ret1, 12)
    out = pd.DataFrame(index=df.index)
    out["ret1"] = ret1
    out["rv12"] = rms12 * math.sqrt(12.0)
    out["state_z"] = (ret1 / (rms12 + EPS)).clip(-5.0, 5.0)
    out["drawdown12"] = df["spx"] / df["spx"].rolling(12, min_periods=12).max() - 1.0
    out["trend12"] = log_spx - log_spx.shift(12)
    out["log_cape"] = np.log(df["cape"].clip(lower=EPS))
    out["real_rate"] = df["rate10"] - df["cpi_yoy"]
    out["cpi_yoy_change12"] = df["cpi_yoy"] - df["cpi_yoy"].shift(12)
    out["dxy12"] = np.log(df["dxy"] / df["dxy"].shift(12))
    out["gold12"] = np.log(df["gold"] / df["gold"].shift(12))
    out["gold_minus_dxy_12"] = out["gold12"] - out["dxy12"]
    out["fwd_min_6m"] = future_min_return(df["spx"].astype(float), 6)
    out["target"] = (out["fwd_min_6m"] <= -0.10).astype(float)
    out.loc[out["fwd_min_6m"].isna(), "target"] = np.nan
    return out.loc["1973-01-01":"2023-03-01"]


@dataclass
class TrainStandardizer:
    mean: np.ndarray
    std: np.ndarray

    @classmethod
    def fit(cls, x: np.ndarray) -> "TrainStandardizer":
        mean = np.nanmean(x, axis=0)
        std = np.nanstd(x, axis=0, ddof=0)
        std = np.where(std < 1e-8, 1.0, std)
        return cls(mean=mean, std=std)

    def transform(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / self.std


@dataclass
class CuspFit:
    params: np.ndarray
    alpha_std: TrainStandardizer
    beta_std: TrainStandardizer
    success: bool
    nll: float
    message: str
    starts: list[dict[str, Any]]


class CuspEstimator:
    def __init__(self, grid_low: float = -8.0, grid_high: float = 8.0, grid_points: int = 801):
        self.grid = np.linspace(grid_low, grid_high, grid_points)
        dx = (grid_high - grid_low) / (grid_points - 1)
        weights = np.ones(grid_points) * dx
        weights[0] *= 0.5
        weights[-1] *= 0.5
        self.log_weights = np.log(weights)

    @staticmethod
    def _unpack(p: np.ndarray, xa: np.ndarray, xb: np.ndarray, z: np.ndarray):
        omega0 = p[0]
        logw = p[1]
        w = math.exp(logw)
        na = xa.shape[1]
        ac = p[2 : 2 + na]
        bc = p[2 + na : 2 + na + xb.shape[1]]
        alpha = xa @ ac
        beta = xb @ bc
        y = omega0 + w * z
        return omega0, logw, w, ac, bc, alpha, beta, y

    def objective_grad(self, p: np.ndarray, z: np.ndarray, xa: np.ndarray, xb: np.ndarray) -> Tuple[float, np.ndarray]:
        _, logw, w, _, _, alpha, beta, y = self._unpack(p, xa, xb, z)
        g = self.grid[None, :]
        exponent = -0.25 * g**4 + 0.5 * beta[:, None] * g**2 + alpha[:, None] * g
        log_terms = exponent + self.log_weights[None, :]
        logz = logsumexp(log_terms, axis=1)
        probs = np.exp(log_terms - logz[:, None])
        ey = probs @ self.grid
        ey2 = probs @ (self.grid**2)
        phi = -0.25 * y**4 + 0.5 * beta * y**2 + alpha * y
        ll = phi - logz + logw
        nll = -float(np.sum(ll))
        drift = -y**3 + beta * y + alpha
        grad = np.zeros_like(p)
        grad[0] = -np.sum(drift)
        grad[1] = -np.sum(drift * (w * z) + 1.0)
        na = xa.shape[1]
        grad[2 : 2 + na] = -(xa.T @ (y - ey))
        grad[2 + na :] = -(xb.T @ (0.5 * (y**2 - ey2)))
        if not np.isfinite(nll) or not np.all(np.isfinite(grad)):
            return 1e100, np.zeros_like(p)
        return nll, grad

    def fit(self, z: np.ndarray, xa_raw: np.ndarray, xb_raw: np.ndarray, starts: Iterable[int] = (0, 1, 2, 3)) -> CuspFit:
        astd = TrainStandardizer.fit(xa_raw)
        bstd = TrainStandardizer.fit(xb_raw)
        xa = np.column_stack([np.ones(len(z)), astd.transform(xa_raw)])
        xb = np.column_stack([np.ones(len(z)), bstd.transform(xb_raw)])
        k = 2 + xa.shape[1] + xb.shape[1]
        bounds = [(-2, 2), (-2, 2)] + [(-4, 4)] * (k - 2)
        records: list[dict[str, Any]] = []
        best = None
        for seed in starts:
            rng = np.random.default_rng(730000 + int(seed))
            p0 = np.zeros(k)
            p0[1] = 0.0
            if seed:
                p0 += rng.normal(0, 0.08, k)
                p0[1] = rng.normal(0, 0.03)
            res = minimize(
                lambda p: self.objective_grad(p, z, xa, xb),
                p0,
                method="L-BFGS-B",
                jac=True,
                bounds=bounds,
                options={"maxiter": 1200, "ftol": 1e-12, "gtol": 1e-7, "maxls": 40},
            )
            rec = {"seed": int(seed), "success": bool(res.success), "fun": float(res.fun), "message": str(res.message), "nit": int(res.nit)}
            records.append(rec)
            if best is None or res.fun < best.fun:
                best = res
        assert best is not None
        return CuspFit(np.asarray(best.x), astd, bstd, bool(best.success), float(best.fun), str(best.message), records)

    def transform_controls(self, fit: CuspFit, xa_raw: np.ndarray, xb_raw: np.ndarray):
        xa = np.column_stack([np.ones(len(xa_raw)), fit.alpha_std.transform(xa_raw)])
        xb = np.column_stack([np.ones(len(xb_raw)), fit.beta_std.transform(xb_raw)])
        return xa, xb

    def score_samples(self, fit: CuspFit, z: np.ndarray, xa_raw: np.ndarray, xb_raw: np.ndarray) -> np.ndarray:
        xa, xb = self.transform_controls(fit, xa_raw, xb_raw)
        _, logw, _, _, _, alpha, beta, y = self._unpack(fit.params, xa, xb, z)
        g = self.grid[None, :]
        exponent = -0.25 * g**4 + 0.5 * beta[:, None] * g**2 + alpha[:, None] * g
        logz = logsumexp(exponent + self.log_weights[None, :], axis=1)
        return -0.25 * y**4 + 0.5 * beta * y**2 + alpha * y - logz + logw

    def alpha_beta(self, fit: CuspFit, xa_raw: np.ndarray, xb_raw: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        xa, xb = self.transform_controls(fit, xa_raw, xb_raw)
        na = xa.shape[1]
        alpha = xa @ fit.params[2 : 2 + na]
        beta = xb @ fit.params[2 + na :]
        return alpha, beta


def stable_roots(alpha: float, beta: float) -> list[float]:
    roots = np.roots([1.0, 0.0, -beta, -alpha])
    real = sorted(float(r.real) for r in roots if abs(float(r.imag)) < 1e-7)
    return [r for r in real if 3.0 * r * r - beta > 1e-9]


def cusp_geometry(alpha: np.ndarray, beta: np.ndarray, state_y: np.ndarray) -> np.ndarray:
    out = np.zeros((len(alpha), 4), dtype=float)
    for i, (a, b, y) in enumerate(zip(alpha, beta, state_y)):
        delta = a * a / 4.0 - b**3 / 27.0
        roots = stable_roots(float(a), float(b))
        if roots:
            near = min(roots, key=lambda r: abs(r - y))
            margin = max(3.0 * near * near - b, 0.0)
        else:
            margin = 0.0
        sep = roots[-1] - roots[0] if len(roots) >= 2 else 0.0
        out[i] = [1.0 if delta < 0 else 0.0, -delta / (1.0 + abs(delta)), 1.0 / (1.0 + margin), sep]
    return out


def gaussian_fit(train_x: np.ndarray, train_y: np.ndarray):
    X = np.column_stack([np.ones(len(train_x)), train_x])
    coef, *_ = np.linalg.lstsq(X, train_y, rcond=None)
    resid = train_y - X @ coef
    sigma = max(float(np.sqrt(np.mean(resid**2))), 1e-6)
    return coef, sigma


def gaussian_logpdf(x: np.ndarray, y: np.ndarray, coef: np.ndarray, sigma: float) -> np.ndarray:
    X = np.column_stack([np.ones(len(x)), x])
    mu = X @ coef
    return -0.5 * ((y - mu) / sigma) ** 2 - math.log(sigma) - 0.5 * math.log(2 * math.pi)


def quadratic_expand(x: np.ndarray) -> np.ndarray:
    cols = [x]
    for i in range(x.shape[1]):
        for j in range(i, x.shape[1]):
            cols.append((x[:, i] * x[:, j])[:, None])
    return np.column_stack(cols)


def fit_logistic(x: np.ndarray, y: np.ndarray) -> Pipeline:
    model = Pipeline([
        ("scale", StandardScaler()),
        ("logit", LogisticRegression(C=1.0, penalty="l2", solver="lbfgs", max_iter=10000, random_state=73)),
    ])
    model.fit(x, y.astype(int))
    return model


def ece_score(y: np.ndarray, p: np.ndarray, bins: int = 10) -> float:
    edges = np.linspace(0.0, 1.0, bins + 1)
    total = len(y)
    score = 0.0
    for i in range(bins):
        if i == bins - 1:
            mask = (p >= edges[i]) & (p <= edges[i + 1])
        else:
            mask = (p >= edges[i]) & (p < edges[i + 1])
        if mask.any():
            score += mask.mean() * abs(float(y[mask].mean()) - float(p[mask].mean()))
    return float(score)


def probability_metrics(y: np.ndarray, p: np.ndarray) -> Dict[str, float]:
    p = np.clip(p, 1e-6, 0.999999)
    result = {
        "brier": float(brier_score_loss(y, p)),
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "pr_auc": float(average_precision_score(y, p)),
        "ece": ece_score(y, p, 10),
    }
    result["roc_auc"] = float(roc_auc_score(y, p)) if len(np.unique(y)) == 2 else float("nan")
    return result


def cluster_recall(y: np.ndarray, alarm: np.ndarray) -> Tuple[int, int, float]:
    starts = []
    in_run = False
    for i, v in enumerate(y.astype(int)):
        if v and not in_run:
            starts.append(i)
            in_run = True
        elif not v:
            in_run = False
    hit = 0
    for s in starts:
        e = s
        while e + 1 < len(y) and y[e + 1] == 1:
            e += 1
        hit += int(alarm[s : e + 1].any())
    return hit, len(starts), float(hit / len(starts)) if starts else float("nan")


def decision_metrics(y_train: np.ndarray, p_train: np.ndarray, y: np.ndarray, p: np.ndarray, months: int) -> Dict[str, float]:
    threshold = float(np.quantile(p_train, 0.90))
    alarm = p >= threshold
    positives = y == 1
    recall = float(alarm[positives].mean()) if positives.any() else float("nan")
    false_months = int(np.sum(alarm & ~positives))
    hit, clusters, cr = cluster_recall(y.astype(int), alarm)
    return {
        "training_threshold": threshold,
        "alarm_months": int(alarm.sum()),
        "positive_month_recall": recall,
        "false_defensive_months_per_year": float(false_months / (months / 12.0)),
        "cluster_hits": hit,
        "clusters": clusters,
        "cluster_recall": cr,
    }


def circular_block_indices(n: int, block: int, rng: np.random.Generator) -> np.ndarray:
    idx = []
    while len(idx) < n:
        start = int(rng.integers(0, n))
        idx.extend((start + np.arange(block)) % n)
    return np.asarray(idx[:n], dtype=int)


def simultaneous_bootstrap_lower(diff_arrays: list[np.ndarray], resamples: int = 4000, block: int = 12, seed: int = 730073):
    obs = np.asarray([np.mean(d) for d in diff_arrays])
    rng = np.random.default_rng(seed)
    boot = np.empty((resamples, len(diff_arrays)))
    for b in range(resamples):
        for j, d in enumerate(diff_arrays):
            ix = circular_block_indices(len(d), block, rng)
            boot[b, j] = np.mean(d[ix])
    sd = np.std(boot, axis=0, ddof=1)
    sd = np.where(sd < 1e-12, 1e-12, sd)
    t = (obs[None, :] - boot) / sd[None, :]
    critical = float(np.quantile(np.max(t, axis=1), 0.95))
    lower = obs - critical * sd
    return {"observed": obs.tolist(), "bootstrap_sd": sd.tolist(), "critical": critical, "simultaneous_lower": lower.tolist()}
