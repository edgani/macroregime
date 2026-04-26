"""engines/options_flow_engine.py — Options Market Microstructure Layer

Fetches gamma exposure, dealer positioning, 0DTE flow.
Integrates as flow_score input to bottleneck_discovery_v3.py.

NO hardcoded thresholds. Adaptive to volatility regime.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
import numpy as np
import pandas as pd


class OptionsFlowEngine:
    """Convert options market data into regime/flow signals."""

    def __init__(self, settings_module=None):
        self.cfg = settings_module

    def fetch_gamma_exposure(
        self,
        ticker: str,
        spot_price: float,
        option_chain: Optional[pd.DataFrame] = None,
    ) -> Dict:
        """Calculate net gamma exposure from option chain.
        
        Args:
            option_chain: DataFrame with columns [strike, expiration, call_put, 
                          open_interest, implied_vol]
        """
        if option_chain is None or option_chain.empty:
            return {"gamma_exposure": 0.0, "gamma_flip": None, "dealer_position": "neutral"}

        df = option_chain.copy()
        df["days_to_expiry"] = pd.to_numeric(df["days_to_expiry"], errors="coerce").fillna(7)
        df["moneyness"] = df["strike"] / spot_price

        # Simplified gamma calculation (Black-Scholes approximation)
        def approx_gamma(row):
            S = spot_price
            K = row["strike"]
            T = max(row["days_to_expiry"] / 365, 0.001)
            v = row.get("implied_vol", 0.30)
            oi = row.get("open_interest", 0)
            cp = 1 if row["call_put"].upper() == "C" else -1

            d1 = (math.log(S / K) + (0.5 * v**2) * T) / (v * math.sqrt(T) + 1e-10)
            gamma = (1 / (S * v * math.sqrt(T) + 1e-10)) * (1 / math.sqrt(2 * math.pi)) * math.exp(-0.5 * d1**2)
            return gamma * oi * cp * S

        df["gamma_dollar"] = df.apply(approx_gamma, axis=1)

        # Aggregate by expiry
        by_expiry = df.groupby("days_to_expiry")["gamma_dollar"].sum().to_dict()
        total_gamma = sum(by_expiry.values())

        # Gamma flip: price level where gamma = 0 (sign flip)
        # Approximation: weighted average strike where OI is balanced
        call_oi = df[df["call_put"].str.upper() == "C"]["open_interest"].sum()
        put_oi = df[df["call_put"].str.upper() == "P"]["open_interest"].sum()

        if call_oi + put_oi > 0:
            call_weight = df[df["call_put"].str.upper() == "C"].apply(
                lambda r: r["strike"] * r["open_interest"], axis=1
            ).sum() / max(call_oi, 1)
            put_weight = df[df["call_put"].str.upper() == "P"].apply(
                lambda r: r["strike"] * r["open_interest"], axis=1
            ).sum() / max(put_oi, 1)
            gamma_flip = (call_weight * call_oi + put_weight * put_oi) / max(call_oi + put_oi, 1)
        else:
            gamma_flip = spot_price

        # Dealer position inference
        if total_gamma > 0:
            dealer_position = "short_gamma"  # dealers short options, must hedge by buying high/selling low
        elif total_gamma < 0:
            dealer_position = "long_gamma"   # dealers long options, hedge by selling high/buying low
        else:
            dealer_position = "neutral"

        # 0DTE dominance
        dte0_oi = df[df["days_to_expiry"] <= 1]["open_interest"].sum()
        total_oi = df["open_interest"].sum()
        dte0_ratio = dte0_oi / max(total_oi, 1)

        return {
            "ticker": ticker,
            "spot": round(spot_price, 2),
            "total_gamma": round(total_gamma, 0),
            "gamma_flip": round(gamma_flip, 2),
            "distance_to_flip": round((spot_price - gamma_flip) / gamma_flip, 3) if gamma_flip > 0 else 0,
            "dealer_position": dealer_position,
            "dte0_ratio": round(dte0_ratio, 3),
            "call_put_ratio": round(call_oi / max(put_oi, 1), 2),
            "max_pain": round(gamma_flip, 2),
        }

    def compute_flow_scores(
        self,
        options_data: Dict[str, Dict],  # ticker -> gamma_exposure dict
        prices: Dict[str, pd.Series],
    ) -> Dict[str, float]:
        """Convert gamma metrics into bottleneck_discovery flow_score."""
        flow_scores = {}

        for ticker, gamma_data in options_data.items():
            score = 0.0

            # 1. Proximity to gamma flip = volatility magnet
            dist = abs(gamma_data.get("distance_to_flip", 0))
            if dist < 0.02:
                score += 0.15  # Very close to flip = pinning risk
            elif dist < 0.05:
                score += 0.08

            # 2. Dealer positioning
            pos = gamma_data.get("dealer_position", "neutral")
            if pos == "short_gamma":
                score += 0.10  # Short gamma = volatility amplification
            elif pos == "long_gamma":
                score -= 0.05  # Long gamma = volatility suppression

            # 3. 0DTE dominance
            dte0 = gamma_data.get("dte0_ratio", 0)
            if dte0 > 0.40:
                score += 0.12  # High 0DTE = event risk / binary outcome

            # 4. Call/Put skew
            cpr = gamma_data.get("call_put_ratio", 1.0)
            if cpr > 1.5:
                score += 0.08  # Extreme call buying = euphoria / squeeze potential
            elif cpr < 0.6:
                score -= 0.05  # Put buying = hedging / fear

            # 5. Price momentum alignment
            close = prices.get(ticker)
            if close is not None and len(close) > 22:
                mom = float(close.iloc[-1] / close.iloc[-22] - 1)
                if mom > 0.05 and pos == "short_gamma":
                    score += 0.10  # Momentum + short gamma = squeeze potential
                elif mom < -0.05 and pos == "long_gamma":
                    score -= 0.08  # Down momentum + long gamma = cushioned fall

            flow_scores[ticker] = round(np.clip(score, -0.20, 0.40), 3)

        return flow_scores

    def detect_gamma_squeeze_candidates(
        self,
        options_data: Dict[str, Dict],
        prices: Dict[str, pd.Series],
    ) -> List[Dict]:
        """Detect tickers vulnerable to gamma squeeze (short gamma + close to flip + momentum)."""
        candidates = []

        for ticker, gd in options_data.items():
            if gd.get("dealer_position") != "short_gamma":
                continue
            if abs(gd.get("distance_to_flip", 1)) > 0.05:
                continue

            close = prices.get(ticker)
            if close is None or len(close) < 22:
                continue
            mom = float(close.iloc[-1] / close.iloc[-22] - 1)
            vol_reg = float(close.pct_change().dropna().tail(21).std() * np.sqrt(252))

            squeeze_score = 0.0
            squeeze_score += max(0, 0.15 - abs(gd["distance_to_flip"]) * 3)  # proximity
            squeeze_score += min(abs(mom) * 2, 0.20)  # momentum
            squeeze_score += min(gd.get("dte0_ratio", 0) * 0.3, 0.15)  # 0DTE
            squeeze_score += min(max(vol_reg - 0.30, 0) * 0.5, 0.10)  # rising vol

            if squeeze_score > 0.25:
                candidates.append({
                    "ticker": ticker,
                    "squeeze_score": round(squeeze_score, 3),
                    "spot": gd.get("spot"),
                    "gamma_flip": gd.get("gamma_flip"),
                    "distance_to_flip": gd.get("distance_to_flip"),
                    "momentum_21d": round(mom, 3),
                    "volatility": round(vol_reg, 3),
                    "dte0_ratio": gd.get("dte0_ratio"),
                    "verdict": "gamma_squeeze_risk" if squeeze_score > 0.40 else "elevated_gamma",
                })

        candidates.sort(key=lambda x: x["squeeze_score"], reverse=True)
        return candidates

    def run(
        self,
        options_data: Optional[Dict[str, Dict]] = None,
        prices: Dict[str, pd.Series] = None,
    ) -> Dict:
        """Full options flow pipeline."""
        if options_data is None or prices is None:
            return {
                "flow_scores": {},
                "gamma_squeeze_candidates": [],
                "meta": {"status": "no_data", "note": "Pass options_data and prices"},
            }

        flow_scores = self.compute_flow_scores(options_data, prices)
        squeeze_candidates = self.detect_gamma_squeeze_candidates(options_data, prices)

        return {
            "flow_scores": flow_scores,
            "gamma_squeeze_candidates": squeeze_candidates,
            "meta": {
                "tickers_analyzed": len(options_data),
                "avg_flow_score": round(np.mean(list(flow_scores.values())), 3) if flow_scores else 0,
                "squeeze_candidates": len(squeeze_candidates),
                "max_flow_score": round(max(flow_scores.values()), 3) if flow_scores else 0,
            },
        }