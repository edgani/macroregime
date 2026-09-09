from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import pandas as pd


LIFECYCLE_ORDER = [
    "DISCOVERED", "EMERGING", "PROVING", "HIGH_CONVICTION",
    "PRICING_IN", "MATURE", "CROWDED", "INVALIDATED", "RESOLVED",
]

OUTCOME_HORIZONS = {
    "1D": 1, "3D": 3, "1W": 7, "2W": 14,
    "1M": 30, "3M": 91, "6M": 182, "12M": 365,
}

SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS opportunity_events (
    event_id TEXT PRIMARY KEY,
    event_key TEXT NOT NULL UNIQUE,
    first_seen_time TEXT NOT NULL,
    first_seen_price REAL,
    first_seen_mcap REAL,
    first_unusual_time TEXT,
    first_high_conviction_time TEXT,
    price_at_high_conviction REAL,
    mcap_at_high_conviction REAL,
    asset TEXT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    asset_class TEXT,
    country TEXT,
    sector TEXT,
    industry TEXT,
    benchmark TEXT,
    theme TEXT,
    archetypes_json TEXT NOT NULL,
    time_horizon TEXT,
    driver TEXT,
    first_order_effect TEXT,
    second_order_effect TEXT,
    bottleneck TEXT,
    beneficiary TEXT,
    revenue_link TEXT,
    margin_link TEXT,
    catalyst TEXT,
    invalidation TEXT,
    thesis TEXT,
    macro_context_json TEXT NOT NULL,
    fundamental_change_json TEXT NOT NULL,
    expectation_json TEXT NOT NULL,
    scores_json TEXT NOT NULL,
    snapshot_json TEXT NOT NULL,
    source_quality TEXT,
    created_at_utc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_opp_event_symbol_market ON opportunity_events(symbol, market, first_seen_time);

CREATE TABLE IF NOT EXISTS opportunity_state_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    observed_at_utc TEXT NOT NULL,
    lifecycle_state TEXT NOT NULL,
    price REAL,
    market_cap REAL,
    reason TEXT,
    snapshot_json TEXT NOT NULL,
    UNIQUE(event_id, observed_at_utc, lifecycle_state)
);
CREATE INDEX IF NOT EXISTS idx_opp_state_event_time ON opportunity_state_history(event_id, observed_at_utc);

CREATE TABLE IF NOT EXISTS opportunity_watch_registry (
    event_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    last_seen_utc TEXT,
    last_state TEXT,
    alert_level TEXT,
    updated_at_utc TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunity_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    horizon TEXT NOT NULL,
    horizon_end_utc TEXT,
    absolute_return REAL,
    benchmark_return REAL,
    sector_return REAL,
    relative_return REAL,
    alpha_vs_benchmark REAL,
    alpha_vs_sector REAL,
    mfe REAL,
    mae REAL,
    time_to_mfe_days REAL,
    time_to_mae_days REAL,
    peak_return REAL,
    max_drawdown REAL,
    time_to_peak_days REAL,
    completed INTEGER NOT NULL DEFAULT 0,
    outcome_json TEXT NOT NULL,
    updated_at_utc TEXT NOT NULL,
    UNIQUE(event_id, horizon)
);
CREATE INDEX IF NOT EXISTS idx_opp_outcome_event ON opportunity_outcomes(event_id, horizon);

CREATE TABLE IF NOT EXISTS opportunity_failures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    observed_at_utc TEXT NOT NULL,
    failure_code TEXT NOT NULL,
    details TEXT,
    UNIQUE(event_id, observed_at_utc, failure_code)
);

CREATE TABLE IF NOT EXISTS missed_runner_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    market TEXT NOT NULL,
    anchor_at_utc TEXT NOT NULL,
    runner_definition TEXT NOT NULL,
    future_return REAL,
    classification TEXT NOT NULL,
    observable_then INTEGER,
    evidence_json TEXT NOT NULL,
    UNIQUE(symbol, market, anchor_at_utc, runner_definition)
);

CREATE TABLE IF NOT EXISTS opportunity_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    observed_at_utc TEXT NOT NULL,
    message TEXT NOT NULL,
    dedupe_key TEXT NOT NULL UNIQUE,
    acknowledged INTEGER NOT NULL DEFAULT 0
);
"""


def _finite(x: Any) -> Optional[float]:
    try:
        v = float(x)
        return v if math.isfinite(v) else None
    except Exception:
        return None


def _json(v: Any) -> str:
    def clean(x):
        if isinstance(x, dict): return {str(k):clean(val) for k,val in x.items()}
        if isinstance(x, (list,tuple,set)): return [clean(i) for i in x]
        try:
            if pd.isna(x): return None
        except Exception:
            pass
        if isinstance(x, float) and not math.isfinite(x): return None
        return x
    return json.dumps(clean(v), sort_keys=True, default=str, allow_nan=False)


def _utc(value: Any = None) -> str:
    if value is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
    t = pd.Timestamp(value)
    if t.tzinfo is None:
        t = t.tz_localize("UTC")
    else:
        t = t.tz_convert("UTC")
    return t.isoformat()


def make_event_key(symbol: str, market: str, theme: str, archetypes: Sequence[str]) -> str:
    # Archetypes can accumulate as evidence matures; keep the first event identity stable.
    return "|".join([str(market).upper(), str(symbol).upper(), str(theme).strip().upper()])


def make_event_id(event_key: str, first_seen_time: str) -> str:
    raw = f"{event_key}|{first_seen_time}".encode("utf-8")
    return "OE-" + hashlib.sha256(raw).hexdigest()[:16].upper()


class OpportunityMemory:
    """Immutable first-detection memory plus append-only lifecycle/outcome learning.

    Event rows are never updated with future fundamental information. Only explicitly
    longitudinal fields (first high-conviction timestamp, watch status, outcomes) are
    allowed to mature later.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as cx:
            cx.executescript(SCHEMA)

    def _connect(self):
        cx = sqlite3.connect(str(self.path))
        cx.row_factory = sqlite3.Row
        return cx

    def get_event_by_key(self, event_key: str) -> Optional[Dict[str, Any]]:
        with self._connect() as cx:
            r = cx.execute("SELECT * FROM opportunity_events WHERE event_key=?", (str(event_key),)).fetchone()
        return dict(r) if r else None

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as cx:
            r = cx.execute("SELECT * FROM opportunity_events WHERE event_id=?", (str(event_id),)).fetchone()
        return dict(r) if r else None

    def get_latest_episode(self, symbol: str, market: str, theme: str) -> Optional[Dict[str, Any]]:
        """Return the newest episode for a symbol/theme, including watch-state metadata.

        A resolved/invalidated episode must never be silently resurrected.  A new
        detection after terminal state is a new episode with a new immutable first-seen.
        """
        with self._connect() as cx:
            r = cx.execute(
                """SELECT e.*,w.active,w.last_state,w.last_seen_utc
                   FROM opportunity_events e
                   LEFT JOIN opportunity_watch_registry w ON e.event_id=w.event_id
                   WHERE UPPER(e.symbol)=UPPER(?) AND UPPER(e.market)=UPPER(?) AND UPPER(e.theme)=UPPER(?)
                   ORDER BY e.first_seen_time DESC LIMIT 1""",
                (str(symbol),str(market),str(theme)),
            ).fetchone()
        return dict(r) if r else None

    def create_event(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        now = _utc(payload.get("first_seen_time") or payload.get("timestamp"))
        arch = list(payload.get("archetypes") or [])
        base_key = make_event_key(payload.get("symbol", ""), payload.get("market", ""), payload.get("theme", ""), arch)
        latest = self.get_latest_episode(payload.get("symbol", ""), payload.get("market", ""), payload.get("theme", ""))
        if latest and int(latest.get("active") or 0) == 1:
            return latest
        # Preserve the historical base key for the first episode.  Later episodes get
        # a deterministic timestamp suffix so the UNIQUE(event_key) constraint does
        # not revive a terminal episode.
        key = base_key if latest is None else f"{base_key}|EP|{now}"
        event_id = make_event_id(base_key, now)
        snap = dict(payload.get("snapshot") or {})
        with self._connect() as cx:
            cx.execute(
                """INSERT INTO opportunity_events(
                    event_id,event_key,first_seen_time,first_seen_price,first_seen_mcap,
                    first_unusual_time,first_high_conviction_time,price_at_high_conviction,mcap_at_high_conviction,
                    asset,symbol,market,asset_class,country,sector,industry,benchmark,theme,archetypes_json,time_horizon,
                    driver,first_order_effect,second_order_effect,bottleneck,beneficiary,revenue_link,margin_link,catalyst,
                    invalidation,thesis,macro_context_json,fundamental_change_json,expectation_json,scores_json,snapshot_json,
                    source_quality,created_at_utc
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    event_id,key,now,_finite(payload.get("price")),_finite(payload.get("market_cap")),
                    _utc(payload.get("first_unusual_time")) if payload.get("first_unusual_time") else None,
                    None,None,None,
                    str(payload.get("asset") or payload.get("name") or payload.get("symbol") or ""),
                    str(payload.get("symbol") or ""),str(payload.get("market") or ""),str(payload.get("asset_class") or ""),
                    str(payload.get("country") or ""),str(payload.get("sector") or ""),str(payload.get("industry") or ""),
                    str(payload.get("benchmark") or ""),str(payload.get("theme") or ""),_json(arch),str(payload.get("time_horizon") or ""),
                    str(payload.get("driver") or ""),str(payload.get("first_order_effect") or ""),str(payload.get("second_order_effect") or ""),
                    str(payload.get("bottleneck") or ""),str(payload.get("beneficiary") or ""),str(payload.get("revenue_link") or ""),
                    str(payload.get("margin_link") or ""),str(payload.get("catalyst") or ""),str(payload.get("invalidation") or ""),
                    str(payload.get("thesis") or ""),_json(dict(payload.get("macro_context") or {})),
                    _json(dict(payload.get("fundamental_change") or {})),_json(dict(payload.get("expectation") or {})),
                    _json(dict(payload.get("scores") or {})),_json(snap),str(payload.get("source_quality") or ""),_utc(),
                ),
            )
            cx.execute(
                "INSERT OR REPLACE INTO opportunity_watch_registry(event_id,symbol,market,active,last_seen_utc,last_state,alert_level,updated_at_utc) VALUES(?,?,?,?,?,?,?,?)",
                (event_id,str(payload.get("symbol") or ""),str(payload.get("market") or ""),1,now,"DISCOVERED","WATCH",_utc()),
            )
        self.record_state(event_id, "DISCOVERED", observed_at_utc=now, price=payload.get("price"), market_cap=payload.get("market_cap"), reason="first meaningful detection", snapshot=snap)
        self.add_alert(event_id, "NEW_OPPORTUNITY", f"New opportunity detected: {payload.get('symbol','')} · {payload.get('theme','')}", now)
        return self.get_event(event_id) or {"event_id": event_id}

    def record_state(self, event_id: str, lifecycle_state: str, *, observed_at_utc: Any = None,
                     price: Any = None, market_cap: Any = None, reason: str = "", snapshot: Optional[Mapping[str, Any]] = None) -> bool:
        state = str(lifecycle_state or "DISCOVERED").upper()
        if state not in LIFECYCLE_ORDER:
            state = "DISCOVERED"
        ts = _utc(observed_at_utc)
        with self._connect() as cx:
            last = cx.execute("SELECT lifecycle_state FROM opportunity_state_history WHERE event_id=? ORDER BY observed_at_utc DESC,id DESC LIMIT 1", (event_id,)).fetchone()
            if last and str(last[0]).upper() == state:
                cx.execute("UPDATE opportunity_watch_registry SET last_seen_utc=?,last_state=?,updated_at_utc=? WHERE event_id=?", (ts,state,_utc(),event_id))
                return False
            cx.execute(
                "INSERT OR IGNORE INTO opportunity_state_history(event_id,observed_at_utc,lifecycle_state,price,market_cap,reason,snapshot_json) VALUES(?,?,?,?,?,?,?)",
                (event_id,ts,state,_finite(price),_finite(market_cap),str(reason),_json(dict(snapshot or {}))),
            )
            active = 0 if state in {"INVALIDATED", "RESOLVED"} else 1
            cx.execute("UPDATE opportunity_watch_registry SET active=?,last_seen_utc=?,last_state=?,updated_at_utc=? WHERE event_id=?", (active,ts,state,_utc(),event_id))
            if state == "HIGH_CONVICTION":
                cx.execute(
                    "UPDATE opportunity_events SET first_high_conviction_time=COALESCE(first_high_conviction_time,?), price_at_high_conviction=COALESCE(price_at_high_conviction,?), mcap_at_high_conviction=COALESCE(mcap_at_high_conviction,?) WHERE event_id=?",
                    (ts,_finite(price),_finite(market_cap),event_id),
                )
        if state in {"PROVING", "HIGH_CONVICTION", "PRICING_IN", "CROWDED", "INVALIDATED"}:
            typ = "STATE_CHANGE"
            self.add_alert(event_id, typ, f"Opportunity state changed → {state.replace('_',' ')}", ts)
        return True

    def add_alert(self, event_id: str, alert_type: str, message: str, observed_at_utc: Any = None) -> bool:
        ts = _utc(observed_at_utc)
        bucket = pd.Timestamp(ts).floor("h").isoformat()
        key = hashlib.sha256(f"{event_id}|{alert_type}|{message}|{bucket}".encode()).hexdigest()
        with self._connect() as cx:
            cur = cx.execute(
                "INSERT OR IGNORE INTO opportunity_alerts(event_id,alert_type,observed_at_utc,message,dedupe_key) VALUES(?,?,?,?,?)",
                (str(event_id),str(alert_type),ts,str(message),key),
            )
            return cur.rowcount > 0

    def label_failure(self, event_id: str, failure_code: str, details: str = "", observed_at_utc: Any = None) -> bool:
        with self._connect() as cx:
            cur = cx.execute(
                "INSERT OR IGNORE INTO opportunity_failures(event_id,observed_at_utc,failure_code,details) VALUES(?,?,?,?)",
                (event_id,_utc(observed_at_utc),str(failure_code).upper(),str(details)),
            )
            return cur.rowcount > 0

    def upsert_outcome(self, event_id: str, horizon: str, values: Mapping[str, Any], *, completed: bool, horizon_end_utc: Any = None) -> bool:
        fields = {k:_finite(values.get(k)) for k in [
            "absolute_return","benchmark_return","sector_return","relative_return","alpha_vs_benchmark","alpha_vs_sector",
            "mfe","mae","time_to_mfe_days","time_to_mae_days","peak_return","max_drawdown","time_to_peak_days",
        ]}
        with self._connect() as cx:
            cx.execute(
                """INSERT INTO opportunity_outcomes(event_id,horizon,horizon_end_utc,absolute_return,benchmark_return,sector_return,
                relative_return,alpha_vs_benchmark,alpha_vs_sector,mfe,mae,time_to_mfe_days,time_to_mae_days,peak_return,max_drawdown,
                time_to_peak_days,completed,outcome_json,updated_at_utc)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(event_id,horizon) DO UPDATE SET
                horizon_end_utc=excluded.horizon_end_utc,absolute_return=excluded.absolute_return,benchmark_return=excluded.benchmark_return,
                sector_return=excluded.sector_return,relative_return=excluded.relative_return,alpha_vs_benchmark=excluded.alpha_vs_benchmark,
                alpha_vs_sector=excluded.alpha_vs_sector,mfe=excluded.mfe,mae=excluded.mae,time_to_mfe_days=excluded.time_to_mfe_days,
                time_to_mae_days=excluded.time_to_mae_days,peak_return=excluded.peak_return,max_drawdown=excluded.max_drawdown,
                time_to_peak_days=excluded.time_to_peak_days,completed=excluded.completed,outcome_json=excluded.outcome_json,updated_at_utc=excluded.updated_at_utc""",
                (event_id,str(horizon),_utc(horizon_end_utc) if horizon_end_utc else None,fields["absolute_return"],fields["benchmark_return"],
                 fields["sector_return"],fields["relative_return"],fields["alpha_vs_benchmark"],fields["alpha_vs_sector"],fields["mfe"],fields["mae"],
                 fields["time_to_mfe_days"],fields["time_to_mae_days"],fields["peak_return"],fields["max_drawdown"],fields["time_to_peak_days"],
                 1 if completed else 0,_json(dict(values)),_utc()),
            )
        return True

    def record_missed_runner(self, *, symbol: str, market: str, anchor_at_utc: Any, runner_definition: str,
                             future_return: Any, classification: str, observable_then: Optional[bool], evidence: Mapping[str, Any]) -> bool:
        with self._connect() as cx:
            cur = cx.execute(
                "INSERT OR IGNORE INTO missed_runner_analysis(symbol,market,anchor_at_utc,runner_definition,future_return,classification,observable_then,evidence_json) VALUES(?,?,?,?,?,?,?,?)",
                (str(symbol),str(market),_utc(anchor_at_utc),str(runner_definition),_finite(future_return),str(classification).upper(),
                 None if observable_then is None else int(bool(observable_then)),_json(dict(evidence))),
            )
            return cur.rowcount > 0

    def opportunity_status_at(self, symbol: str, market: str, observed_at_utc: Any) -> Dict[str, Any]:
        """Point-in-time status of the newest episode known by `observed_at_utc`."""
        ts=_utc(observed_at_utc)
        with self._connect() as cx:
            ev=cx.execute(
                "SELECT * FROM opportunity_events WHERE UPPER(symbol)=UPPER(?) AND UPPER(market)=UPPER(?) AND first_seen_time<=? ORDER BY first_seen_time DESC LIMIT 1",
                (str(symbol),str(market),ts),
            ).fetchone()
            if not ev:
                return {"found":False,"active":False,"event_id":None,"state":None}
            eid=str(ev["event_id"])
            st=cx.execute(
                "SELECT lifecycle_state,observed_at_utc FROM opportunity_state_history WHERE event_id=? AND observed_at_utc<=? ORDER BY observed_at_utc DESC,id DESC LIMIT 1",
                (eid,ts),
            ).fetchone()
        state=str(st["lifecycle_state"]).upper() if st else "DISCOVERED"
        return {"found":True,"active":state not in {"INVALIDATED","RESOLVED"},"event_id":eid,"state":state,"first_seen_time":ev["first_seen_time"]}

    def events_due_for_outcome_update(self, limit: int = 8) -> pd.DataFrame:
        """Fair bounded scheduler: never-updated / least-recently-updated events first.

        This prevents old 12M episodes from monopolising every bounded refresh and
        starving newer events from receiving 1D/3D labels.
        """
        q = """
        SELECT e.*, w.active, w.last_state,
               MAX(o.updated_at_utc) AS last_outcome_update_utc
        FROM opportunity_events e
        LEFT JOIN opportunity_watch_registry w ON e.event_id=w.event_id
        LEFT JOIN opportunity_outcomes o ON e.event_id=o.event_id
        GROUP BY e.event_id
        ORDER BY (MAX(o.updated_at_utc) IS NOT NULL) ASC, MAX(o.updated_at_utc) ASC, e.first_seen_time ASC
        LIMIT ?
        """
        with self._connect() as cx:
            rows=cx.execute(q,(int(limit),)).fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def events_frame(self, *, active_only: bool = False, limit: int = 500) -> pd.DataFrame:
        q = """SELECT e.*,w.active,w.last_seen_utc,w.last_state,w.alert_level
               FROM opportunity_events e LEFT JOIN opportunity_watch_registry w ON e.event_id=w.event_id"""
        args: List[Any] = []
        if active_only:
            q += " WHERE COALESCE(w.active,1)=1"
        q += " ORDER BY e.first_seen_time DESC LIMIT ?"
        args.append(int(limit))
        with self._connect() as cx:
            rows = cx.execute(q, args).fetchall()
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame([dict(x) for x in rows])
        for c in ["archetypes_json","macro_context_json","fundamental_change_json","expectation_json","scores_json","snapshot_json"]:
            if c in df:
                df[c] = df[c].map(lambda x: json.loads(x) if x else {})
        return df

    def states_frame(self, event_id: Optional[str] = None, limit: int = 500) -> pd.DataFrame:
        with self._connect() as cx:
            if event_id:
                rows = cx.execute("SELECT * FROM opportunity_state_history WHERE event_id=? ORDER BY observed_at_utc DESC,id DESC LIMIT ?", (event_id,int(limit))).fetchall()
            else:
                rows = cx.execute("SELECT * FROM opportunity_state_history ORDER BY observed_at_utc DESC,id DESC LIMIT ?", (int(limit),)).fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def outcomes_frame(self, event_id: Optional[str] = None) -> pd.DataFrame:
        with self._connect() as cx:
            if event_id:
                rows = cx.execute("SELECT * FROM opportunity_outcomes WHERE event_id=? ORDER BY id", (event_id,)).fetchall()
            else:
                rows = cx.execute("SELECT * FROM opportunity_outcomes ORDER BY updated_at_utc DESC").fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def failures_frame(self) -> pd.DataFrame:
        with self._connect() as cx:
            rows = cx.execute("SELECT * FROM opportunity_failures ORDER BY observed_at_utc DESC").fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def missed_frame(self) -> pd.DataFrame:
        with self._connect() as cx:
            rows = cx.execute("SELECT * FROM missed_runner_analysis ORDER BY anchor_at_utc DESC").fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def alerts_frame(self, limit: int = 100) -> pd.DataFrame:
        with self._connect() as cx:
            rows = cx.execute("SELECT * FROM opportunity_alerts ORDER BY observed_at_utc DESC,id DESC LIMIT ?", (int(limit),)).fetchall()
        return pd.DataFrame([dict(x) for x in rows]) if rows else pd.DataFrame()

    def counts(self) -> Dict[str, int]:
        with self._connect() as cx:
            return {
                "events": int(cx.execute("SELECT COUNT(*) FROM opportunity_events").fetchone()[0]),
                "active": int(cx.execute("SELECT COUNT(*) FROM opportunity_watch_registry WHERE active=1").fetchone()[0]),
                "outcomes": int(cx.execute("SELECT COUNT(*) FROM opportunity_outcomes WHERE completed=1").fetchone()[0]),
                "failures": int(cx.execute("SELECT COUNT(*) FROM opportunity_failures").fetchone()[0]),
                "missed": int(cx.execute("SELECT COUNT(*) FROM missed_runner_analysis").fetchone()[0]),
            }
