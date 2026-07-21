"""Bounded official-source change detector for War Room OS.

It hashes normalized public page text. A hash change is *not* a market signal; it becomes
CHANGED_UNREVIEWED until a human checks the source and updates the dated development inventory.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any

import requests

HERE = Path(__file__).resolve().parent
WATCHLIST = HERE / "data" / "source_watchlist.json"
STATUS_FILE = HERE / "runtime" / "official_source_status.json"
CACHE_FILE = HERE / "runtime" / "official_source_hashes.json"


def _read(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _atomic_write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name, suffix=".tmp", dir=str(path.parent))
    os.close(fd)
    tmp = Path(name)
    try:
        tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _normalize_html(text: str) -> str:
    text = re.sub(r"(?is)<script.*?</script>|<style.*?</style>|<!--.*?-->", " ", text)
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:2_000_000]


def run_once(timeout: float = 8.0) -> dict:
    watch = _read(WATCHLIST, {"sources": []})
    previous = _read(CACHE_FILE, {})
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    rows: list[dict] = []
    new_hashes = dict(previous)
    ua = os.environ.get("WARROOM_SEC_USER_AGENT", "").strip()

    for source in watch.get("sources", []):
        if not isinstance(source, dict):
            continue
        sid = str(source.get("id") or "unknown")
        url = str(source.get("url") or "")
        row = {
            "id": sid,
            "url": url,
            "markets": source.get("markets", []),
            "checked_at": now,
            "state": "ERROR",
            "note": "",
            "directional_semantics": "NONE",
        }
        if "sec.gov" in url and not ua:
            row.update(state="ACTION_REQUIRED", note="Set WARROOM_SEC_USER_AGENT before polling SEC pages.")
            rows.append(row)
            continue
        headers = {
            "User-Agent": ua if "sec.gov" in url else "WarRoomOS-Research/3.3 (+local research dashboard)",
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            response = requests.get(url, timeout=timeout, headers=headers, allow_redirects=True)
            response.raise_for_status()
            normalized = _normalize_html(response.text)
            digest = hashlib.sha256(normalized.encode("utf-8", errors="ignore")).hexdigest()
            old = previous.get(sid)
            state = "BASELINED" if not old else ("UNCHANGED" if old == digest else "CHANGED_UNREVIEWED")
            row.update(
                state=state,
                note=("First observed hash stored." if state == "BASELINED" else
                      "Official page content changed; review required." if state == "CHANGED_UNREVIEWED" else
                      "No content change detected."),
                sha256=digest,
                http_status=response.status_code,
                final_url=response.url,
            )
            new_hashes[sid] = digest
        except Exception as exc:
            row.update(state="ERROR", note=f"{type(exc).__name__}: {exc}"[:300])
        rows.append(row)

    overall = "REVIEW_REQUIRED" if any(x["state"] == "CHANGED_UNREVIEWED" for x in rows) else (
        "PARTIAL" if any(x["state"] in {"ERROR", "ACTION_REQUIRED"} for x in rows) else "OK"
    )
    payload = {
        "schema_version": "1.0",
        "state": overall,
        "updated_at": now,
        "semantics": "Change detection only. Never auto-translates into market direction or trade action.",
        "sources": rows,
    }
    _atomic_write(CACHE_FILE, new_hashes)
    _atomic_write(STATUS_FILE, payload)
    return payload


if __name__ == "__main__":
    print(json.dumps(run_once(), indent=2))
