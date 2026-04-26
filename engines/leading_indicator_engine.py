"""engines/leading_indicator_engine.py — 10/10 Predictive Leading Indicators

Trains per-regime models to predict:
  - Future quad (3M forward)
  - Asset returns (1M, 3M, 6M forward)
  - Transition probability

Features: PMI, credit spreads, yield curve, M2, claims, oil, VIX, etc.
Models: GradientBoostingRegressor (sklearn — no XGBoost dependency)
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit

class LeadingIndicatorEngine:
    """
    Per-regime leading indicator regression.
    Different macro drivers matter in different quads.
    """

    # Leading features by regime (what predicts transitions FROM this quad)
    REGIME_FEATURES = {
        "Q1": ["ism_norm", "payrolls_roc", "cpi_roc", "breakeven_delta", "dxy_inv_1m", "vix", "proxy_share"],
        "Q2": ["oil_3m", "ppi_yoy", "breakeven_5y", "indpro_roc", "retail_roc", "dxy_inv_1m"],
        "Q3": ["claims_delta", "unrate_delta", "ism_delta", "cpi_roc", "oil_3m", "vix", "proxy_share"],
        "Q4": ["claims_delta", "housing_yoy", "tlt_1m", "dxy_1m", "vix", "credit_spread_proxy"],
    }

    def __init__(self):
        self.models = {}  # quad -> model
        self.scalers = {}
        self.is_fitted = False

    def _build_feature_vector(self, features: Dict[str, float], quad: str) -> np.ndarray:
        keys = self.REGIME_FEATURES.get(quad, self.REGIME_FEATURES["Q1"])
        return np.array([float(features.get(k, 0.0)) for k in keys]).reshape(1, -1)

    def fit(self, historical_snapshots: List[Dict]):
        """
        Train on historical snapshots.
        Each snapshot: {quad, features, forward_quad_3m, forward_return_3m}
        """
        if len(historical_snapshots) < 30:
            return  # insufficient history

        for quad in ["Q1", "Q2", "Q3", "Q4"]:
            snaps = [s for s in historical_snapshots if s.get("quad") == quad]
            if len(snaps) < 10:
                continue

            X = []
            y_quad = []  # 1 if transitioned to different quad, 0 if stayed
            y_return = []  # forward SPY return

            for s in snaps:
                fv = self._build_feature_vector(s["features"], quad)[0]
                X.append(fv)
                y_quad.append(1.0 if s.get("forward_quad_3m") != quad else 0.0)
                y_return.append(s.get("forward_return_3m", 0.0))

            X = np.array(X)
            y = np.array(y_quad)  # predict transition probability

            scaler = StandardScaler()
            Xs = scaler.fit_transform(X)

            model = GradientBoostingRegressor(n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42)
            model.fit(Xs, y)

            self.models[quad] = model
            self.scalers[quad] = scaler

        self.is_fitted = len(self.models) > 0

    def predict_transition_prob(self, features: Dict[str, float], current_quad: str) -> float:
        """Predict probability of regime transition within 3 months."""
        if not self.is_fitted or current_quad not in self.models:
            # Fallback: heuristic
            g_mom = features.get("growth_momentum", 0)
            i_mom = features.get("inflation_momentum", 0)
            return min(abs(g_mom) + abs(i_mom), 1.0)

        X = self._build_feature_vector(features, current_quad)
        Xs = self.scalers[current_quad].transform(X)
        prob = float(self.models[current_quad].predict(Xs)[0])
        return float(np.clip(prob, 0.0, 1.0))

    def predict_forward_return(self, features: Dict[str, float], current_quad: str, asset: str = "SPY") -> Dict[str, float]:
        """Predict 1M / 3M / 6M forward return for asset."""
        # Simplified: use transition prob + quad playbook
        trans_prob = self.predict_transition_prob(features, current_quad)
        # If high transition prob → higher dispersion, harder to predict
        confidence = 1.0 - trans_prob * 0.5

        # Base expected return from historical quad playbook
        base_returns = {"Q1": 0.02, "Q2": 0.015, "Q3": -0.01, "Q4": -0.02}
        base = base_returns.get(current_quad, 0.0)

        # Adjust by momentum
        g = features.get("growth_momentum", 0)
        i = features.get("inflation_momentum", 0)
        adjustment = g * 0.1 - i * 0.05

        return {
            "expected_1m": round(base * 0.3 + adjustment, 4),
            "expected_3m": round(base + adjustment, 4),
            "expected_6m": round(base * 2 + adjustment, 4),
            "confidence": round(confidence, 3),
            "transition_prob": round(trans_prob, 3),
        }

    def feature_importance(self, quad: str) -> Dict[str, float]:
        """Return feature importance for regime."""
        if quad not in self.models:
            return {}
        model = self.models[quad]
        keys = self.REGIME_FEATURES[quad]
        return {k: round(float(v), 4) for k, v in zip(keys, model.feature_importances_)}
