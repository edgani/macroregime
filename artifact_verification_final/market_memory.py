from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

import pandas as pd


SCHEMA = """
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT NOT NULL,
    market TEXT NOT NULL,
    observed_at_utc TEXT NOT NULL,
    features_json TEXT NOT NULL,
    state TEXT,
    source_quality TEXT,
    UNIQUE(entity, market, observed_at_utc)
);
CREATE INDEX IF NOT EXISTS idx_snapshots_entity_time ON snapshots(entity, market, observed_at_utc);
CREATE TABLE IF NOT EXISTS outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity TEXT NOT NULL,
    market TEXT NOT NULL,
    anchor_at_utc TEXT NOT NULL,
    horizon TEXT NOT NULL,
    return_value REAL,
    max_upside REAL,
    max_drawdown REAL,
    outcome_json TEXT NOT NULL,
    UNIQUE(entity, market, anchor_at_utc, horizon)
);
"""


class MarketMemory:
    """Append-only local memory. It records what was known then; it never backfills features into old snapshots."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as cx:
            cx.executescript(SCHEMA)

    def _connect(self):
        return sqlite3.connect(str(self.path))

    @staticmethod
    def _ts(value: Optional[Any] = None) -> str:
        if value is None:
            return datetime.now(timezone.utc).isoformat(timespec="seconds")
        t = pd.Timestamp(value)
        if t.tzinfo is None:
            t = t.tz_localize("UTC")
        else:
            t = t.tz_convert("UTC")
        return t.isoformat()

    def record_snapshot(self, entity: str, market: str, features: Mapping[str, Any], *, state: str = "", source_quality: str = "", observed_at_utc: Any = None) -> bool:
        ts = self._ts(observed_at_utc)
        payload = json.dumps(dict(features), sort_keys=True, default=str, allow_nan=True)
        with self._connect() as cx:
            cur = cx.execute(
                "INSERT OR IGNORE INTO snapshots(entity,market,observed_at_utc,features_json,state,source_quality) VALUES(?,?,?,?,?,?)",
                (str(entity), str(market), ts, payload, str(state), str(source_quality)),
            )
            return cur.rowcount > 0

    def history(self, entity: str, market: str, *, limit: int = 120) -> pd.DataFrame:
        with self._connect() as cx:
            rows = cx.execute(
                "SELECT observed_at_utc,features_json,state,source_quality FROM snapshots WHERE entity=? AND market=? ORDER BY observed_at_utc DESC LIMIT ?",
                (str(entity), str(market), int(limit)),
            ).fetchall()
        records: List[Dict[str, Any]] = []
        for ts, payload, state, quality in reversed(rows):
            try:
                d = json.loads(payload)
            except Exception:
                d = {}
            d.update({"observed_at_utc": ts, "memory_state": state, "memory_source_quality": quality})
            records.append(d)
        return pd.DataFrame(records)

    def states(self, entity: str, market: str, *, limit: int = 30) -> List[str]:
        with self._connect() as cx:
            rows = cx.execute(
                "SELECT state FROM snapshots WHERE entity=? AND market=? ORDER BY observed_at_utc DESC LIMIT ?",
                (str(entity), str(market), int(limit)),
            ).fetchall()
        return [str(x[0]) for x in reversed(rows) if x and x[0]]

    def record_outcome(self, entity: str, market: str, anchor_at_utc: Any, horizon: str, *, return_value: float = None, max_upside: float = None, max_drawdown: float = None, extra: Optional[Mapping[str, Any]] = None) -> bool:
        payload = json.dumps(dict(extra or {}), sort_keys=True, default=str, allow_nan=True)
        with self._connect() as cx:
            cur = cx.execute(
                "INSERT OR REPLACE INTO outcomes(entity,market,anchor_at_utc,horizon,return_value,max_upside,max_drawdown,outcome_json) VALUES(?,?,?,?,?,?,?,?)",
                (str(entity), str(market), self._ts(anchor_at_utc), str(horizon), return_value, max_upside, max_drawdown, payload),
            )
            return cur.rowcount > 0

    def counts(self) -> Dict[str, int]:
        with self._connect() as cx:
            s = int(cx.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
            e = int(cx.execute("SELECT COUNT(DISTINCT market || ':' || entity) FROM snapshots").fetchone()[0])
            o = int(cx.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0])
        return {"snapshots": s, "entities": e, "outcomes": o}
