"""Background data collector for War Room OS.

Core, institutional, derivatives and slow specialist planes refresh independently. The worker
always writes the newest complete/partial snapshot atomically and retains prior plane data when a
provider fails. The Streamlit process never waits on these network calls.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any
import argparse
import multiprocessing as mp
import queue as queue_mod
import os
import signal
import sys
import time

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env", override=False)
except Exception:
    pass

from runtime_store import PID, consume_force_refresh, now_iso, read_snapshot, write_snapshot, write_status

STOP = False

def _stop(*_):
    global STOP
    STOP = True

signal.signal(signal.SIGTERM, _stop)
if hasattr(signal, "SIGINT"):
    signal.signal(signal.SIGINT, _stop)

MARKETS = ["us", "idx", "crypto", "commodity", "fx"]
CORE_SECONDS = max(60, int(os.getenv("WARROOM_CORE_REFRESH_SECONDS", "300")))
EVENT_SECONDS = max(10, int(os.getenv("WARROOM_EVENT_REFRESH_SECONDS", "30")))
SLOW_SECONDS = max(300, int(os.getenv("WARROOM_SLOW_REFRESH_SECONDS", "1800")))


def _safe_plane(name: str, fn, fallback: dict) -> dict:
    try:
        value = fn()
        if isinstance(value, dict):
            return value
        return {**fallback, "overall_state": "ERROR", "note": f"{name} returned non-dict"}
    except Exception as exc:
        return {**fallback, "overall_state": "ERROR", "note": f"{type(exc).__name__}: {exc}"}


def build_core(fast: bool = True) -> dict:
    import data_layer as DL
    from run import build_desk
    data = DL.load_all(markets=MARKETS, allow_live=True, allow_synthetic=False, fast_core=fast, skip_slow_context=fast)
    desk = build_desk(data, top_per_market=40)
    desk.setdefault("runtime", {})["core_collected_at"] = now_iso()
    desk["runtime"]["core_profile"] = "FAST" if fast else "EXPANDED"
    return desk


def _core_child(fast: bool, output) -> None:
    try:
        output.put((True, build_core(fast=fast)))
    except Exception as exc:
        output.put((False, f"{type(exc).__name__}: {exc}"))


def build_core_bounded(fast: bool = True) -> dict:
    """Hard wall-clock boundary around third-party loaders.

    yfinance/curl/network DNS failures can outlive their nominal request timeout. Running the whole
    core collector in a child process lets the worker retain last-good data instead of hanging.
    """
    timeout = int(os.getenv("WARROOM_FAST_CORE_HARD_TIMEOUT", "75") if fast else os.getenv("WARROOM_EXPANDED_CORE_HARD_TIMEOUT", "240"))
    context = mp.get_context("spawn" if os.name == "nt" else "fork")
    output = context.Queue(maxsize=1)
    process = context.Process(target=_core_child, args=(fast, output), daemon=True)
    process.start(); process.join(timeout=max(10, timeout))
    if process.is_alive():
        process.terminate(); process.join(5)
        raise TimeoutError(f"{'fast' if fast else 'expanded'} core exceeded {timeout}s hard timeout")
    try:
        ok, value = output.get_nowait()
    except queue_mod.Empty:
        raise RuntimeError(f"core child exited with code {process.exitcode} without a result")
    if not ok:
        raise RuntimeError(value)
    return value


def collect_event_planes(core: dict) -> tuple[dict, dict]:
    from institutional_data import collect_institutional_data
    from live_market_intelligence import collect_live_market_intelligence
    institutional = _safe_plane("institutional", lambda: collect_institutional_data(core),
                                {"statuses": [], "events": []})
    live = _safe_plane("live_intelligence", lambda: collect_live_market_intelligence(core, institutional),
                       {"statuses": [], "events": [], "crypto_derivatives": [], "crypto_options": [],
                        "us_options": [], "us_squeeze": []})
    return institutional, live


def collect_slow_plane(core: dict) -> dict:
    from full_live_data_hub import collect_full_live_data
    return _safe_plane("full_live_data", lambda: collect_full_live_data(core),
                       {"statuses": [], "tab_coverage": {}})


def merge_snapshot(core: dict, institutional: dict | None = None, live: dict | None = None,
                   full: dict | None = None, previous: dict | None = None) -> dict:
    desk = deepcopy(core)
    previous = previous or {}
    desk["institutional"] = institutional if institutional is not None else previous.get("institutional", {"overall_state":"INITIALIZING","statuses":[],"events":[]})
    desk["live_intelligence"] = live if live is not None else previous.get("live_intelligence", {"overall_state":"INITIALIZING","statuses":[],"events":[],"crypto_derivatives":[],"crypto_options":[],"us_options":[],"us_squeeze":[]})
    desk["full_live_data"] = full if full is not None else previous.get("full_live_data", {"overall_state":"INITIALIZING","statuses":[],"tab_coverage":{}})
    health = dict(desk.get("data_health") or {})
    extra = list((desk["institutional"] or {}).get("statuses") or []) + list((desk["live_intelligence"] or {}).get("statuses") or []) + list((desk["full_live_data"] or {}).get("statuses") or [])
    health["sources"] = list(health.get("sources") or []) + extra
    health["total_count"] = len(health["sources"])
    health["live_count"] = sum(1 for row in health["sources"] if row.get("state") in {"LIVE","PARTIAL","STALE"})
    health["overall"] = "LIVE" if health["total_count"] and health["live_count"] == health["total_count"] else "PARTIAL" if health["live_count"] else "NO_DATA"
    desk["data_health"] = health
    # Reconcile cross-plane coverage after the event/derivatives plane is available. The slow hub
    # cannot know about public crypto derivatives or delayed US option chains by itself.
    coverage = dict((desk.get("full_live_data") or {}).get("tab_coverage") or {})
    live_rows = desk.get("live_intelligence") or {}
    valid_derivative_states={"LIVE","STALE","PARTIAL"}
    derivative_records = (len([x for x in (live_rows.get("crypto_derivatives") or []) if x.get("state") in valid_derivative_states]) +
                          len([x for x in (live_rows.get("crypto_options") or []) if x.get("state") in valid_derivative_states]) +
                          len([x for x in (live_rows.get("us_options") or []) if x.get("state") in valid_derivative_states]))
    if "derivatives_squeeze" in coverage and derivative_records:
        coverage["derivatives_squeeze"]["state"] = "LIVE" if derivative_records >= 3 else "PARTIAL"
        coverage["derivatives_squeeze"]["cross_plane_records"] = derivative_records
    if "us_stocks" in coverage and any(x.get("state") in {"LIVE","STALE"} for x in (live_rows.get("us_options") or [])):
        if coverage["us_stocks"].get("state") == "NO_DATA": coverage["us_stocks"]["state"] = "PARTIAL"
    inst_events = len((desk.get("institutional") or {}).get("events") or [])
    if "institutional" in coverage and inst_events:
        coverage["institutional"]["state"] = "LIVE"
        coverage["institutional"]["cross_plane_records"] = inst_events
    if desk.get("full_live_data") is not None:
        desk["full_live_data"]["tab_coverage"] = coverage
    desk.setdefault("runtime", {}).update({
        "worker_state": "LIVE",
        "institutional_collected_at": now_iso() if institutional is not None else (previous.get("runtime") or {}).get("institutional_collected_at"),
        "derivatives_collected_at": now_iso() if live is not None else (previous.get("runtime") or {}).get("derivatives_collected_at"),
        "slow_plane_collected_at": now_iso() if full is not None else (previous.get("runtime") or {}).get("slow_plane_collected_at"),
    })
    return desk


def run_once(previous: dict | None = None) -> dict:
    write_status(state="COLLECTING_CORE", pid=os.getpid())
    core = build_core_bounded(fast=True)
    # Publish core immediately, so first paint does not wait for slow/paid providers.
    partial = merge_snapshot(core, previous=previous)
    write_snapshot(partial)
    write_status(state="COLLECTING_EVENT_AND_SLOW_PLANES", pid=os.getpid())
    with ThreadPoolExecutor(max_workers=2) as pool:
        event_future = pool.submit(collect_event_planes, core)
        slow_future = pool.submit(collect_slow_plane, core)
        institutional, live = event_future.result()
        full = slow_future.result()
    final = merge_snapshot(core, institutional, live, full, partial)
    write_snapshot(final)
    write_status(state="IDLE", pid=os.getpid(), last_success=now_iso())
    return final


def loop() -> None:
    PID.write_text(str(os.getpid()), encoding="utf-8")
    previous = read_snapshot() or {}
    core = None
    institutional = previous.get("institutional")
    live = previous.get("live_intelligence")
    full = previous.get("full_live_data")
    last_core = last_event = last_slow = 0.0
    try:
        while not STOP:
            force = consume_force_refresh()
            now = time.time()
            if force or core is None or now - last_core >= CORE_SECONDS:
                write_status(state="COLLECTING_CORE", pid=os.getpid())
                try:
                    core = build_core_bounded(fast=True)
                    last_core = now
                    snap = merge_snapshot(core, institutional, live, full, previous)
                    write_snapshot(snap); previous = snap
                except Exception as exc:
                    write_status(state="CORE_ERROR", pid=os.getpid(), error=f"{type(exc).__name__}: {exc}")
            if core is not None and (force or now - last_event >= EVENT_SECONDS):
                write_status(state="COLLECTING_EVENTS", pid=os.getpid())
                institutional, live = collect_event_planes(core)
                last_event = now
                snap = merge_snapshot(core, institutional, live, full, previous)
                write_snapshot(snap); previous = snap
            if core is not None and (force or now - last_slow >= SLOW_SECONDS):
                write_status(state="COLLECTING_SLOW_PLANE", pid=os.getpid())
                # Try an expanded universe after a fast snapshot already exists. Failure/timeout in
                # this enrichment cannot remove the usable fast core.
                try:
                    expanded = build_core_bounded(fast=False)
                    if sum(int((v.get("funnel") or {}).get("universe") or 0) for v in (expanded.get("markets") or {}).values()) >= sum(int((v.get("funnel") or {}).get("universe") or 0) for v in (core.get("markets") or {}).values()):
                        core = expanded
                except Exception:
                    pass
                full = collect_slow_plane(core)
                last_slow = now
                snap = merge_snapshot(core, institutional, live, full, previous)
                write_snapshot(snap); previous = snap
            write_status(state="IDLE", pid=os.getpid(), last_success=now_iso())
            for _ in range(10):
                if STOP or consume_force_refresh():
                    # Recreate flag for next outer loop when consumed during sleep.
                    from runtime_store import request_force_refresh
                    request_force_refresh()
                    break
                time.sleep(1)
    finally:
        try: PID.unlink()
        except Exception: pass
        write_status(state="STOPPED", pid=os.getpid())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    PID.write_text(str(os.getpid()), encoding="utf-8")
    try:
        if args.once:
            run_once(read_snapshot() or {})
        else:
            loop()
    finally:
        if args.once:
            try: PID.unlink()
            except Exception: pass

if __name__ == "__main__":
    main()
