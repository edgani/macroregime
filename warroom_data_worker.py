"""Bounded collector for War Room OS v9.7 all-market bottleneck projection runtime."""
from __future__ import annotations

import argparse
import os
import signal
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env", override=False)
except Exception:
    pass

from runtime_sanitizer import sanitize_runtime_payload
from runtime_store import (
    claim_worker_instance, consume_force_refresh, force_refresh_requested, now_iso,
    release_worker_instance, write_snapshot, write_status,
)

STOP = False
MARKETS = ["us", "idx", "crypto", "commodity", "fx"]
REFRESH_SECONDS = max(300, int(os.getenv("WARROOM_CORE_REFRESH_SECONDS", "900")))


def _stop(*_args) -> None:
    global STOP
    STOP = True


def _install_signals() -> None:
    try:
        signal.signal(signal.SIGTERM, _stop)
        signal.signal(signal.SIGINT, _stop)
    except (ValueError, OSError):
        pass


def build_core(fast: bool = True, bootstrap: bool = False, refresh_context: bool = False) -> dict:
    del refresh_context
    import data_layer as DL
    from run import build_fast_desk

    data = DL.load_all(
        markets=MARKETS,
        allow_live=True,
        fetch_live_feeds=not bootstrap,
        allow_synthetic=False,
        fast_core=fast,
        skip_slow_context=False,
        bootstrap_core=bootstrap,
    )
    try:
        from execution_quote_collector_v97 import collect as collect_execution_quotes
        collect_execution_quotes()
    except Exception as exc:
        # Quote failure is visible and fail-closed; macro/evidence refresh still survives.
        from runtime_store import write_status
        write_status(quote_refresh_error=f"{type(exc).__name__}: {exc}")
    desk = build_fast_desk(data)
    desk.setdefault("runtime", {}).update({
        "core_collected_at": now_iso(),
        "core_profile": "BOOTSTRAP" if bootstrap else "NONTECHNICAL_EVIDENCE_AND_EXECUTION_REFERENCE_REFRESH",
    })
    return sanitize_runtime_payload(desk)


def collect_event_planes(core: dict) -> dict:
    del core
    return {
        "institutional": {
            "overall_state": "DISABLED_PENDING_NONTECHNICAL_SOURCE_AUDIT",
            "statuses": [], "events": [],
        },
        "live_intelligence": {
            "overall_state": "DISABLED_PENDING_NONTECHNICAL_SOURCE_AUDIT",
            "statuses": [], "events": [],
        },
    }


def collect_slow_plane(core: dict) -> dict:
    del core
    return {
        "overall_state": "DISABLED_PENDING_NONTECHNICAL_SOURCE_AUDIT",
        "statuses": [], "tab_coverage": {},
    }


def run_once(*, bootstrap: bool = False) -> dict:
    write_status(state="COLLECTING", last_attempt_at=now_iso(), error=None)
    try:
        desk = build_core(True, bootstrap=bootstrap)
        result = write_snapshot(desk, force=True)
        write_status(
            state="READY_EVIDENCE_PRODUCTION",
            last_success=now_iso(),
            revision=result.get("revision"),
            content_hash=result.get("content_hash"),
            capital_permission="BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL",
            error=None,
        )
        return desk
    except BaseException as exc:
        write_status(state="WORKER_FATAL", error=f"{type(exc).__name__}: {exc}", capital_permission="BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL")
        raise


def loop() -> None:
    _install_signals()
    if not claim_worker_instance():
        write_status(state="ALREADY_RUNNING", capital_permission="BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL")
        return
    try:
        run_once(bootstrap=True)
        next_run = time.monotonic() + REFRESH_SECONDS
        while not STOP:
            if force_refresh_requested():
                consume_force_refresh()
                next_run = 0.0
            if time.monotonic() >= next_run:
                run_once(bootstrap=False)
                next_run = time.monotonic() + REFRESH_SECONDS
            write_status(state="READY_EVIDENCE_PRODUCTION", heartbeat_at=now_iso(), capital_permission="BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL")
            time.sleep(2.0)
    finally:
        release_worker_instance()
        write_status(state="STOPPED", capital_permission="BLOCKED_UNTIL_EXACT_PROOF_AND_HUMAN_APPROVAL")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--bootstrap", action="store_true")
    args = parser.parse_args()
    if args.once:
        run_once(bootstrap=args.bootstrap)
    else:
        loop()


if __name__ == "__main__":
    main()
