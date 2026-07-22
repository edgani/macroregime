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
    """Load dated research prompts with freshness and source-review status separated.

    A recent date is not source verification.  Static entries remain REVIEW_REQUIRED unless
    the inventory explicitly records a human review.  The page-change radar only reports
    availability/change; it never auto-approves the claim.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    raw = _read_json(DEVELOPMENTS_FILE, {"entries": []})
    radar = _read_json(RADAR_STATUS_FILE, {"sources": [], "state": "NOT_RUN"})
    sources = [x for x in radar.get("sources", []) if isinstance(x, dict)]
    entries: list[dict] = []
    for item in raw.get("entries", []):
        if not isinstance(item, dict):
            continue
        row = deepcopy(item)
        event_dt = _parse_date(row.get("date"))
        age_days = (now - event_dt).total_seconds() / 86400 if event_dt else None
        stale_after = int(row.get("stale_after_days") or 90)
        stale = age_days is None or age_days > stale_after
        human = row.get("human_review") if isinstance(row.get("human_review"), dict) else {}
        approved = str(human.get("status") or "").upper() == "APPROVED" and bool(human.get("reviewed_at"))
        row["age_days"] = round(age_days, 1) if age_days is not None else None
        row["freshness"] = "STALE" if stale else "DATE_CURRENT"
        row["source_verification"] = "HUMAN_REVIEWED" if approved else "REVIEW_REQUIRED"
        row["directional_semantics"] = "NONE"
        row["capital_semantics"] = "NONE"
        entries.append(row)
    entries.sort(key=lambda x: str(x.get("date") or ""), reverse=True)

    changed = [x for x in sources if str(x.get("state") or "").upper() == "CHANGED_UNREVIEWED"]
    errors = [x for x in sources if str(x.get("state") or "").upper() in {"ERROR", "ACTION_REQUIRED"}]
    current_entries = [x for x in entries if x.get("freshness") == "DATE_CURRENT"]
    reviewed_entries = [x for x in current_entries if x.get("source_verification") == "HUMAN_REVIEWED"]
    return {
        "schema_version": "2.0",
        "generated_at": now.isoformat().replace("+00:00", "Z"),
        "semantics": "Dated research prompts. Date freshness is separate from human source verification. No entry creates direction or capital permission.",
        "entries": entries,
        "fresh_count": len(current_entries),
        "reviewed_fresh_count": len(reviewed_entries),
        "review_required_count": len(current_entries) - len(reviewed_entries),
        "stale_count": len(entries) - len(current_entries),
        "by_market": {market: [x for x in entries if x.get("market") == market] for market in ("us", "idx", "crypto", "commodity", "fx")},
        "official_source_radar": {
            "state": radar.get("state", "NOT_RUN"),
            "updated_at": radar.get("updated_at"),
            "changed_unreviewed": len(changed),
            "errors_or_action_required": len(errors),
            "sources": sources,
            "semantics": "Page reachability/hash changes require human review. Radar output never validates a claim or creates direction.",
        },
    }


def attach_current_developments(desk: dict) -> dict:
    if not isinstance(desk, dict):
        return desk
    out = deepcopy(desk)
    out["current_developments"] = load_current_developments()
    return out
