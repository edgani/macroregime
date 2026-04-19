"""position_tracker_engine.py

Active position lifecycle tracker.
Tracks entry → current → exit signals for active trades.

Answers: "Gw masuk ADRO di 2800, sekarang +18%, kapan trim?
          Exit signal sudah berapa % terpenuhi?"

Storage: SQLite (same DB as signal_strength, separate table)
"""
from __future__ import annotations
import json
import math
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

_DB_PATH = Path(".cache/position_tracker.db")
_QUAD_STOP_PCT = {"Q1": 7.0, "Q2": 8.0, "Q3": 6.0, "Q4": 9.0}
_QUAD_TARGET_PCT = {"Q1": 20.0, "Q2": 25.0, "Q3": 15.0, "Q4": 18.0}


@dataclass
class ActivePosition:
    id: int
    ticker: str
    market: str              # us | ihsg | fx | commodities | crypto
    side: str                # long | short
    entry_price: float
    entry_date: str
    entry_quad: str
    size_pct: float          # % of portfolio
    current_price: float = 0.0
    pnl_pct: float = 0.0
    days_held: int = 0
    stop_price: float = 0.0
    target_price: float = 0.0
    stop_hit: bool = False
    target_hit: bool = False
    exit_signal_score: float = 0.0   # 0-1: how close to exit
    notes: str = ""
    tags: List[str] = field(default_factory=list)


@dataclass
class ExitSignal:
    position_id: int
    ticker: str
    urgency: str             # "act_now" | "watch" | "hold"
    reason: str
    action: str              # "close" | "trim_50" | "trim_25" | "tighten_stop"
    price_target: Optional[float] = None


def _init_db() -> None:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(_DB_PATH)) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            market TEXT NOT NULL,
            side TEXT NOT NULL,
            entry_price REAL NOT NULL,
            entry_date TEXT NOT NULL,
            entry_quad TEXT,
            size_pct REAL DEFAULT 5.0,
            stop_pct REAL DEFAULT 7.0,
            target_pct REAL DEFAULT 20.0,
            notes TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            status TEXT DEFAULT 'active',
            created_at TEXT,
            closed_at TEXT,
            close_price REAL,
            close_reason TEXT
        )""")
        conn.commit()


def add_position(
    ticker: str,
    market: str,
    side: str,
    entry_price: float,
    entry_quad: str,
    size_pct: float = 5.0,
    stop_pct: float = 0.0,
    target_pct: float = 0.0,
    notes: str = "",
    tags: List[str] | None = None,
) -> int:
    """Add a new active position. Returns the position ID."""
    _init_db()
    stop = stop_pct if stop_pct > 0 else _QUAD_STOP_PCT.get(entry_quad, 7.0)
    target = target_pct if target_pct > 0 else _QUAD_TARGET_PCT.get(entry_quad, 20.0)
    now = datetime.now(timezone.utc).isoformat()
    tags_json = json.dumps(tags or [])
    with sqlite3.connect(str(_DB_PATH)) as conn:
        cur = conn.execute(
            """INSERT INTO positions (ticker,market,side,entry_price,entry_date,entry_quad,
               size_pct,stop_pct,target_pct,notes,tags,status,created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,'active',?)""",
            (ticker, market, side, entry_price, now[:10], entry_quad,
             size_pct, stop, target, notes, tags_json, now)
        )
        return int(cur.lastrowid)


def close_position(
    position_id: int,
    close_price: float,
    reason: str = "manual",
) -> bool:
    """Mark a position as closed."""
    _init_db()
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(str(_DB_PATH)) as conn:
        conn.execute(
            "UPDATE positions SET status='closed',closed_at=?,close_price=?,close_reason=? WHERE id=?",
            (now, close_price, reason, position_id)
        )
        return True


def get_active_positions() -> List[Dict]:
    """Return all active positions as list of dicts."""
    _init_db()
    with sqlite3.connect(str(_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM positions WHERE status='active' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_position_history(limit: int = 20) -> List[Dict]:
    """Return closed positions for P&L review."""
    _init_db()
    with sqlite3.connect(str(_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM positions WHERE status='closed' ORDER BY closed_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
    results = []
    for r in rows:
        d = dict(r)
        try:
            ep = float(d.get("entry_price", 0))
            cp = float(d.get("close_price", 0) or 0)
            side = str(d.get("side", "long"))
            if ep > 0 and cp > 0:
                if side == "long":
                    d["pnl_pct"] = round((cp / ep - 1) * 100, 2)
                else:
                    d["pnl_pct"] = round((ep / cp - 1) * 100, 2)
            else:
                d["pnl_pct"] = None
        except Exception:
            d["pnl_pct"] = None
        results.append(d)
    return results


def enrich_positions_with_prices(
    positions: List[Dict],
    prices: Dict[str, pd.Series],
) -> List[ActivePosition]:
    """
    Enrich raw position dicts with current price, P&L, exit signal score.
    """
    enriched = []
    today = datetime.now(timezone.utc).date()

    for pos in positions:
        ticker = str(pos.get("ticker", ""))
        entry_price = float(pos.get("entry_price", 0))
        entry_quad = str(pos.get("entry_quad", "Q?"))
        side = str(pos.get("side", "long"))
        size_pct = float(pos.get("size_pct", 5.0))
        stop_pct = float(pos.get("stop_pct", _QUAD_STOP_PCT.get(entry_quad, 7.0)))
        target_pct = float(pos.get("target_pct", _QUAD_TARGET_PCT.get(entry_quad, 20.0)))
        entry_date_str = str(pos.get("entry_date", ""))

        # Get current price from price series
        current_price = entry_price  # fallback
        s = prices.get(ticker)
        if s is not None and len(s) > 0:
            try:
                current_price = float(s.iloc[-1])
            except Exception:
                pass

        # P&L
        if entry_price > 0 and math.isfinite(current_price) and math.isfinite(entry_price):
            if side == "long":
                pnl_pct = (current_price / entry_price - 1) * 100
            else:
                pnl_pct = (entry_price / current_price - 1) * 100
        else:
            pnl_pct = 0.0

        # Days held
        try:
            entry_date = datetime.strptime(entry_date_str[:10], "%Y-%m-%d").date()
            days_held = (today - entry_date).days
        except Exception:
            days_held = 0

        # Stop and target prices
        if side == "long":
            stop_price = entry_price * (1 - stop_pct / 100)
            target_price = entry_price * (1 + target_pct / 100)
            stop_hit = current_price <= stop_price
            target_hit = current_price >= target_price
        else:
            stop_price = entry_price * (1 + stop_pct / 100)
            target_price = entry_price * (1 - target_pct / 100)
            stop_hit = current_price >= stop_price
            target_hit = current_price <= target_price

        # Exit signal score: composite of multiple exit conditions
        exit_signals = []
        # 1. Stop hit
        exit_signals.append(1.0 if stop_hit else 0.0)
        # 2. Target hit
        exit_signals.append(0.80 if target_hit else 0.0)
        # 3. Time-based: held too long (beyond typical quad duration)
        max_hold = {"Q1": 84, "Q2": 70, "Q3": 42, "Q4": 56}.get(entry_quad, 70)
        time_score = min(1.0, days_held / max_hold) if max_hold > 0 else 0.0
        if time_score > 0.80:
            exit_signals.append(0.60)
        # 4. P&L extremes
        if pnl_pct >= target_pct * 0.75:
            exit_signals.append(0.55)  # near target — consider trimming
        if pnl_pct <= -stop_pct * 0.80:
            exit_signals.append(0.90)  # near stop

        exit_score = max(exit_signals) if exit_signals else 0.0

        enriched.append(ActivePosition(
            id=int(pos.get("id", 0)),
            ticker=ticker,
            market=str(pos.get("market", "?")),
            side=side,
            entry_price=entry_price,
            entry_date=entry_date_str[:10],
            entry_quad=entry_quad,
            size_pct=size_pct,
            current_price=current_price,
            pnl_pct=round(pnl_pct, 2),
            days_held=days_held,
            stop_price=round(stop_price, 4),
            target_price=round(target_price, 4),
            stop_hit=stop_hit,
            target_hit=target_hit,
            exit_signal_score=round(exit_score, 3),
            notes=str(pos.get("notes", "")),
            tags=json.loads(pos.get("tags", "[]")) if pos.get("tags") else [],
        ))

    return enriched


def generate_exit_signals(
    positions: List[ActivePosition],
    current_quad: str,
    flip_hazard: float = 0.3,
) -> List[ExitSignal]:
    """Generate exit/trim signals for active positions."""
    signals = []
    for pos in positions:
        if pos.stop_hit:
            signals.append(ExitSignal(
                position_id=pos.id, ticker=pos.ticker,
                urgency="act_now", reason=f"Stop hit ({pos.pnl_pct:.1f}%)",
                action="close", price_target=pos.stop_price,
            ))
        elif pos.target_hit:
            signals.append(ExitSignal(
                position_id=pos.id, ticker=pos.ticker,
                urgency="act_now", reason=f"Target hit (+{pos.pnl_pct:.1f}%)",
                action="trim_50",
            ))
        elif pos.exit_signal_score >= 0.70:
            signals.append(ExitSignal(
                position_id=pos.id, ticker=pos.ticker,
                urgency="watch",
                reason=f"Exit score {pos.exit_signal_score:.0%} — multiple exit conditions building",
                action="trim_25",
            ))
        elif pos.entry_quad != current_quad and flip_hazard > 0.50:
            signals.append(ExitSignal(
                position_id=pos.id, ticker=pos.ticker,
                urgency="watch",
                reason=f"Regime changed from {pos.entry_quad} → {current_quad}, flip hazard {flip_hazard:.0%}",
                action="tighten_stop",
            ))
    return sorted(signals, key=lambda s: {"act_now": 0, "watch": 1, "hold": 2}.get(s.urgency, 2))
