"""Dated market-development inventory and primary-source radar attachment.

This module never converts a headline or changed web page into trade direction. It only
surfaces fresh structural changes, staleness, and pages that require human review.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
DEVELOPMENTS_FILE = HERE / "data" / "current_developments.json"
RADAR_STATUS_FILE = HERE / "runtime" / "official_source_status.json"


def _parse_date(value: Any) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        if len(text) == 10:
            return datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
        return datetime.fromisoformat(text.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return deepcopy(default)


def load_current_developments(now: datetime | None = None) -> dict:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    raw = _read_json(DEVELOPMENTS_FILE, {"entries": []})
    entries: list[dict] = []
    for item in raw.get("entries", []):
        if not isinstance(item, dict):
            continue
        row = deepcopy(item)
        event_dt = _parse_date(row.get("date"))
        age_days = (now - event_dt).total_seconds() / 86400 if event_dt else None
        stale_after = int(row.get("stale_after_days") or 90)
        stale = age_days is None or age_days > stale_after
        row["age_days"] = round(age_days, 1) if age_days is not None else None
        row["freshness"] = "STALE" if stale else "FRESH"
        row["directional_semantics"] = "NONE"
        entries.append(row)
    entries.sort(key=lambda x: str(x.get("date") or ""), reverse=True)

    radar = _read_json(RADAR_STATUS_FILE, {"sources": [], "state": "NOT_RUN"})
    sources = [x for x in radar.get("sources", []) if isinstance(x, dict)]
    changed = [x for x in sources if str(x.get("state") or "").upper() == "CHANGED_UNREVIEWED"]
    errors = [x for x in sources if str(x.get("state") or "").upper() in {"ERROR", "ACTION_REQUIRED"}]
    fresh_entries = [x for x in entries if x.get("freshness") == "FRESH"]
    return {
        "schema_version": raw.get("schema_version", "1.0"),
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "semantics": raw.get("semantics"),
        "entries": entries,
        "fresh_count": len(fresh_entries),
        "stale_count": len(entries) - len(fresh_entries),
        "by_market": {
            market: [x for x in entries if x.get("market") == market]
            for market in ("us", "idx", "crypto", "commodity", "fx")
        },
        "official_source_radar": {
            "state": radar.get("state", "NOT_RUN"),
            "updated_at": radar.get("updated_at"),
            "changed_unreviewed": len(changed),
            "errors_or_action_required": len(errors),
            "sources": sources,
            "semantics": "Changed pages require review; no directional signal is inferred.",
        },
    }


def attach_current_developments(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["current_developments"] = load_current_developments()
    return out
