from __future__ import annotations
from pathlib import Path
import json
from runtime_store import STATIC_SNAPSHOT, STATIC_STATUS, read_snapshot, read_status, now_iso

HERE = Path(__file__).resolve().parent
snapshot = read_snapshot() or {}
worker = read_status() or {}


def read_static(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def tail(path: Path, lines: int = 60) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
    except Exception:
        return []


static_snapshot = read_static(STATIC_SNAPSHOT)
static_status = read_static(STATIC_STATUS)
runtime_revision = int(((snapshot.get("runtime") or {}).get("snapshot_sequence") or 0))
static_revision = int(((static_snapshot.get("runtime") or {}).get("snapshot_sequence") or 0))
health = str((snapshot.get("data_health") or {}).get("overall") or "NO_DATA")

report = {
    "generated": now_iso(),
    "worker": worker,
    "static_worker": static_status,
    "snapshot_present": bool(snapshot),
    "runtime_revision": runtime_revision,
    "static_revision": static_revision,
    "revision_match": runtime_revision == static_revision,
    "overall_health": health,
    "startup_interpretation": (
        "PERMANENT_R1_BUG" if runtime_revision <= 1 and health == "INITIALIZING"
        else "EXPLICIT_NO_DATA" if health == "NO_DATA"
        else "DATA_COMMITTED"
    ),
    "worker_log_tail": tail(HERE / "runtime" / "worker.log"),
    "worker_boot_log_tail": tail(HERE / "runtime" / "worker_boot.log"),
}
report["markets"] = {}
for market in ("us", "idx", "crypto", "commodity", "fx"):
    row = (snapshot.get("markets") or {}).get(market) or {}
    loaded = int((row.get("funnel") or {}).get("universe") or 0)
    report["markets"][market] = {
        "bias": row.get("bias"),
        "data_state": row.get("data_state"),
        "loaded": loaded,
        "setups": len(row.get("setups") or []),
        "note": row.get("note"),
        "interpretation": "NO_SIGNAL" if loaded > 0 and not row.get("setups") else row.get("data_state") or row.get("bias") or "NO_DATA",
    }
report["liquidity"] = {
    "state": (snapshot.get("systemic") or {}).get("liquidity"),
    "detail": (snapshot.get("systemic") or {}).get("liquidity_detail"),
}
report["planes"] = {
    "institutional": (snapshot.get("institutional") or {}).get("overall_state"),
    "derivatives": (snapshot.get("live_intelligence") or {}).get("overall_state"),
    "full_live_data": (snapshot.get("full_live_data") or {}).get("overall_state"),
}
report["tabs"] = {}
for tab, coverage in ((snapshot.get("full_live_data") or {}).get("tab_coverage") or {}).items():
    failures = []
    for status in coverage.get("provider_statuses") or []:
        if status.get("state") not in {"LIVE", "STALE", "PARTIAL", "NO_SIGNAL", "CASH_ONLY"}:
            failures.append({k: status.get(k) for k in ("provider", "dataset", "state", "note")})
    report["tabs"][tab] = {
        "state": coverage.get("state"),
        "core_datasets": coverage.get("core_datasets"),
        "optional_missing": coverage.get("optional_missing"),
        "failures": failures,
    }
report["exact_sources"] = [
    {k: status.get(k) for k in ("provider", "dataset", "state", "records", "note")}
    for status in (snapshot.get("data_health") or {}).get("sources") or []
]
out = HERE / "runtime" / "NO_DATA_DIAGNOSTIC.json"
out.parent.mkdir(exist_ok=True)
out.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
print(json.dumps(report, indent=2, default=str))
print(f"\nSaved: {out}")
