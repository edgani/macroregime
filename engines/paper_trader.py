"""engines/paper_trader.py — Paper Trading & Performance Audit

Auto-execute paper trades from engine signals. Track PnL per regime.
NO hardcoded strategies. Signal-driven from bottleneck + narrative engines.
"""
from __future__ import annotations
import math
from typing import Dict, List, Optional
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from datetime import datetime


@dataclass
class PaperTrade:
    trade_id: str
    ticker: str
    entry_date: str
    entry_price: float
    signal_source: str          # "bottleneck", "narrative", "discovery_v3"
    signal_mode: str            # "reactive", "proactive", "adaptive"
    regime_at_entry: str
    level: str                  # "watch", "level_1", "level_2"
    ev_at_entry: float
    brewing_score: float
    narrative_tag: str
    exit_date: Optional[str] = None
    exit_price: Optional[float] = None
    pnl_pct: Optional[float] = None
    status: str = "open"
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    tp3: Optional[float] = None
    stop: Optional[float] = None


class PaperTrader:
    """Execute and track paper trades from engine signals."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.trades: List[PaperTrade] = []
        self.closed_trades: List[PaperTrade] = []

    def enter_trade(
        self,
        ticker: str,
        price: float,
        signal_source: str,
        signal_mode: str,
        regime: str,
        level: str,
        ev: float,
        brewing_score: float,
        narrative_tag: str = "",
        tp_levels: Optional[Dict[str, float]] = None,
        stop_loss: Optional[float] = None,
    ) -> PaperTrade:
        """Record new paper trade entry."""
        trade = PaperTrade(
            trade_id=f"{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            ticker=ticker,
            entry_date=datetime.now().strftime("%Y-%m-%d"),
            entry_price=price,
            signal_source=signal_source,
            signal_mode=signal_mode,
            regime_at_entry=regime,
            level=level,
            ev_at_entry=ev,
            brewing_score=brewing_score,
            narrative_tag=narrative_tag,
            tp1=tp_levels.get("T1") if tp_levels else None,
            tp2=tp_levels.get("T2") if tp_levels else None,
            tp3=tp_levels.get("T3") if tp_levels else None,
            stop=stop_loss,
        )
        self.trades.append(trade)
        return trade

    def exit_trade(
        self,
        trade_id: str,
        exit_price: float,
    ) -> Optional[PaperTrade]:
        """Close a paper trade."""
        for trade in self.trades:
            if trade.trade_id == trade_id and trade.status == "open":
                trade.exit_date = datetime.now().strftime("%Y-%m-%d")
                trade.exit_price = exit_price
                trade.pnl_pct = round((exit_price - trade.entry_price) / trade.entry_price, 4)
                trade.status = "closed"
                self.closed_trades.append(trade)
                self.trades = [t for t in self.trades if t.trade_id != trade_id]
                return trade
        return None

    def auto_exit_scan(
        self,
        prices: Dict[str, pd.Series],
        ranges: Optional[Dict[str, Dict]] = None,
    ) -> List[PaperTrade]:
        """Auto-exit trades that hit TP or stop."""
        exited = []

        for trade in list(self.trades):
            close = pd.to_numeric(prices.get(trade.ticker), errors="coerce")
            if close is None or close.empty:
                continue
            current_price = float(close.iloc[-1])

            # Check stops
            if trade.stop and current_price <= trade.stop:
                exited.append(self.exit_trade(trade.trade_id, current_price))
                continue

            # Check TPs
            if trade.tp3 and current_price >= trade.tp3:
                exited.append(self.exit_trade(trade.trade_id, current_price))
            elif trade.tp2 and current_price >= trade.tp2:
                # Partial exit logic could go here
                pass

        return [e for e in exited if e is not None]

    def performance_by_regime(
        self,
        trades: Optional[List[PaperTrade]] = None,
    ) -> Dict:
        """Audit performance per quad regime."""
        trades = trades or self.closed_trades
        if not trades:
            return {}

        by_regime: Dict[str, List[float]] = {}
        by_source: Dict[str, List[float]] = {}
        by_mode: Dict[str, List[float]] = {}
        by_level: Dict[str, List[float]] = {}

        for t in trades:
            pnl = t.pnl_pct or 0
            by_regime.setdefault(t.regime_at_entry, []).append(pnl)
            by_source.setdefault(t.signal_source, []).append(pnl)
            by_mode.setdefault(t.signal_mode, []).append(pnl)
            by_level.setdefault(t.level, []).append(pnl)

        def stats(pnls):
            if not pnls:
                return {}
            return {
                "trades": len(pnls),
                "winrate": round(sum(1 for p in pnls if p > 0) / len(pnls), 3),
                "avg_pnl": round(np.mean(pnls), 4),
                "median_pnl": round(np.median(pnls), 4),
                "max_gain": round(max(pnls), 4),
                "max_loss": round(min(pnls), 4),
                "sharpe_approx": round(np.mean(pnls) / (np.std(pnls) + 1e-10), 2),
            }

        return {
            "by_regime": {k: stats(v) for k, v in by_regime.items()},
            "by_source": {k: stats(v) for k, v in by_source.items()},
            "by_mode": {k: stats(v) for k, v in by_mode.items()},
            "by_level": {k: stats(v) for k, v in by_level.items()},
            "overall": stats([t.pnl_pct for t in trades if t.pnl_pct is not None]),
        }

    def generate_monthly_report(
        self,
        month: Optional[str] = None,  # "YYYY-MM"
    ) -> Dict:
        """Generate monthly performance report."""
        month = month or datetime.now().strftime("%Y-%m")
        month_trades = [t for t in self.closed_trades if t.entry_date.startswith(month)]

        if not month_trades:
            return {"month": month, "status": "no_trades"}

        pnls = [t.pnl_pct for t in month_trades if t.pnl_pct is not None]
        cumulative = float(np.prod([1 + p for p in pnls]) - 1)

        return {
            "month": month,
            "trades": len(month_trades),
            "winrate": round(sum(1 for p in pnls if p > 0) / len(pnls), 3),
            "avg_pnl": round(np.mean(pnls), 4),
            "cumulative_return": round(cumulative, 4),
            "max_drawdown": round(min(pnls), 4),
            "best_trade": max(month_trades, key=lambda t: t.pnl_pct or 0).ticker if month_trades else None,
            "worst_trade": min(month_trades, key=lambda t: t.pnl_pct or 0).ticker if month_trades else None,
            "regime_breakdown": self.performance_by_regime(month_trades)["by_regime"],
        }

    def run(
        self,
        prices: Dict[str, pd.Series],
        new_signals: Optional[List[Dict]] = None,
        ranges: Optional[Dict[str, Dict]] = None,
    ) -> Dict:
        """Full paper trading pipeline."""
        # Auto-exit existing trades
        exited = self.auto_exit_scan(prices, ranges)

        # Enter new trades from signals
        entered = []
        if new_signals:
            for sig in new_signals:
                close = pd.to_numeric(prices.get(sig["ticker"]), errors="coerce")
                if close is None or close.empty:
                    continue
                price = float(close.iloc[-1])

                trade = self.enter_trade(
                    ticker=sig["ticker"],
                    price=price,
                    signal_source=sig.get("source", "discovery_v3"),
                    signal_mode=sig.get("mode", "reactive"),
                    regime=sig.get("regime", "Q3"),
                    level=sig.get("level", "watch"),
                    ev=sig.get("ev", 0),
                    brewing_score=sig.get("brewing_score", 0),
                    narrative_tag=sig.get("narrative_tag", ""),
                    tp_levels=sig.get("tp"),
                    stop_loss=sig.get("stop"),
                )
                entered.append(trade)

        # Performance audit
        perf = self.performance_by_regime()
        report = self.generate_monthly_report()

        return {
            "entered_today": len(entered),
            "exited_today": len(exited),
            "open_positions": len(self.trades),
            "closed_positions": len(self.closed_trades),
            "performance_audit": perf,
            "monthly_report": report,
            "open_trades": [
                {"id": t.trade_id, "ticker": t.ticker, "entry": t.entry_price,
                 "ev": t.ev_at_entry, "regime": t.regime_at_entry}
                for t in self.trades
            ],
        }