"""engines/trend_signal_engine.py — Historical TREND Signal & Chart Data Builder
Generates Hedgeye-style color-coded historical signal lines for ANY ticker.
Output ready for Plotly/Streamlit.
"""
from __future__ import annotations
import math
import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
from .pvv_engine import PVVEngine, DURATIONS

logger = logging.getLogger(__name__)

SIGNAL_COLORS = {
    "BULLISH": "#3FB950",
    "BEARISH": "#F85149",
    "NEUTRAL": "#8B949E",
}

class TrendSignalEngine:
    """
    Build historical TREND signal series for charting.
    For each date, compute TRADE/TREND/TAIL signal and store.
    """

    def __init__(self):
        self.pvv = PVVEngine()

    def build_history(self, price: pd.Series, volume: Optional[pd.Series] = None,
                      duration: str = "TREND",
                      min_bars: int = 200) -> pd.DataFrame:
        """
        Returns DataFrame with columns:
          [date, price, signal, vasp_score, pvv_score, lrr, trr, position_pct]
        Signal is recomputed on a rolling basis (expanding then rolling window).
        """
        price = pd.to_numeric(price, errors="coerce").dropna()
        if volume is not None:
            volume = pd.to_numeric(volume, errors="coerce").dropna()
        if len(price) < min_bars:
            return pd.DataFrame()

        days = DURATIONS[duration]["days"]
        records = []
        # Use expanding window until we have enough, then rolling
        for i in range(days + 20, len(price)):
            px_window = price.iloc[:i]
            vol_window = volume.iloc[:i] if volume is not None else None
            res = self.pvv._compute_duration(px_window, vol_window, duration)
            if not res.get("ok"):
                continue
            records.append({
                "date": price.index[i],
                "price": float(price.iloc[i]),
                "signal": res["signal"],
                "vasp_score": res["vasp_score"],
                "pvv_score": res["pvv_score"],
                "price_roc": res["price_roc"],
                "vol_of_vol": res["vol_of_vol"],
                "realized_vol": res["realized_vol"],
                "hurst": res["hurst"],
                "lrr": res["lrr"],
                "trr": res["trr"],
                "position_pct": res["position_pct"],
                "above_trend_sma": res["above_trend_sma"],
            })
        df = pd.DataFrame(records)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df

    def build_all_durations(self, price: pd.Series, volume: Optional[pd.Series] = None) -> Dict[str, pd.DataFrame]:
        """Build history for TRADE, TREND, TAIL."""
        return {
            "TRADE": self.build_history(price, volume, "TRADE"),
            "TREND": self.build_history(price, volume, "TREND"),
            "TAIL":  self.build_history(price, volume, "TAIL"),
        }

    @staticmethod
    def to_plotly_segments(df: pd.DataFrame, ticker: str = "Asset",
                           duration: str = "TREND") -> List[Dict]:
        """
        Convert signal history into Plotly line segments with color.
        Returns list of dicts ready for fig.add_trace(go.Scatter(...)).
        """
        if df.empty or "signal" not in df.columns:
            return []

        segments = []
        current_signal = df["signal"].iloc[0]
        start_idx = 0

        for i in range(1, len(df)):
            if df["signal"].iloc[i] != current_signal or i == len(df) - 1:
                seg_df = df.iloc[start_idx:i]
                color = SIGNAL_COLORS.get(current_signal, "#8B949E")
                segments.append({
                    "x": seg_df["date"].tolist(),
                    "y": seg_df["price"].tolist(),
                    "mode": "lines",
                    "line": {"color": color, "width": 2.5},
                    "name": f"{ticker} {duration} {current_signal}",
                    "showlegend": False,
                    "hoverinfo": "skip",
                })
                current_signal = df["signal"].iloc[i]
                start_idx = i
        return segments

    @staticmethod
    def to_plotly_figure(df: pd.DataFrame, ticker: str = "Asset",
                         duration: str = "TREND", height: int = 420) -> Dict:
        """
        Returns a Plotly Figure dict (can be used with go.Figure(data=...)).
        """
        import plotly.graph_objects as go
        segments = TrendSignalEngine.to_plotly_segments(df, ticker, duration)
        fig = go.Figure()
        for seg in segments:
            fig.add_trace(go.Scatter(
                x=seg["x"], y=seg["y"],
                mode=seg["mode"],
                line=seg["line"],
                showlegend=seg["showlegend"],
                hoverinfo=seg["hoverinfo"],
            ))
        # Legend traces (dummy)
        for sig, color in SIGNAL_COLORS.items():
            fig.add_trace(go.Scatter(
                x=[None], y=[None],
                mode="lines",
                line={"color": color, "width": 3},
                name=sig,
            ))
        # Add LRR/TRR ribbon if available
        if not df.empty and "lrr" in df.columns and df["lrr"].notna().any():
            fig.add_trace(go.Scatter(
                x=df["date"].tolist() + df["date"].tolist()[::-1],
                y=df["trr"].tolist() + df["lrr"].tolist()[::-1],
                fill="toself",
                fillcolor="rgba(255,255,255,0.03)",
                line={"color": "rgba(255,255,255,0)"},
                name="Risk Range",
                showlegend=True,
            ))
        fig.update_layout(
            title=f"{ticker}: HISTORICAL {duration} SIGNAL",
            height=height,
            margin=dict(t=40, b=20, l=40, r=20),
            paper_bgcolor="#161B22",
            plot_bgcolor="#161B22",
            font=dict(color="#E6EDF3", family="Inter, sans-serif"),
            xaxis=dict(showgrid=True, gridcolor="#21262D", tickfont=dict(size=11)),
            yaxis=dict(showgrid=True, gridcolor="#21262D", tickfont=dict(size=11),
                       tickformat=",.0f" if df["price"].max() > 10 else ",.4f"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                        font=dict(size=11)),
        )
        return fig


class TrendSignalScanner:
    """Batch historical TREND signal for many tickers."""

    def __init__(self):
        self.engine = TrendSignalEngine()

    def build_multi(self, prices: Dict[str, pd.Series],
                    volumes: Optional[Dict[str, pd.Series]] = None,
                    duration: str = "TREND") -> Dict[str, pd.DataFrame]:
        volumes = volumes or {}
        out = {}
        for ticker, px in prices.items():
            if px is None or len(px) < 200:
                continue
            try:
                out[ticker] = self.engine.build_history(px, volumes.get(ticker), duration)
            except Exception as e:
                logger.warning(f"Trend history failed for {ticker}: {e}")
        return out

    def build_figures(self, histories: Dict[str, pd.DataFrame],
                      duration: str = "TREND") -> Dict[str, Dict]:
        """Return dict of Plotly figure dicts per ticker."""
        out = {}
        for ticker, df in histories.items():
            if not df.empty:
                out[ticker] = TrendSignalEngine.to_plotly_figure(df, ticker, duration)
        return out
