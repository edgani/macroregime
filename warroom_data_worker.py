"""Stable staged collector for War Room OS v2.8.

Design goals:
- one worker process only;
- independent schedules for core, event/derivatives and slow enrichment planes;
- no intermediate core-only/final state flapping;
- last-good retention on transient provider failure;
- bounded child processes around third-party libraries;
- one atomic snapshot commit after each completed plane batch.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
import argparse
import multiprocessing as mp
import os
import pickle
import signal
import sys
import tempfile
import time
import threading
import logging
from logging.handlers import RotatingFileHandler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
try:
    from dotenv import load_dotenv
    load_dotenv(HERE / ".env", override=False)
except Exception:
    pass

from runtime_store import (
    PID, claim_worker_instance, consume_force_refresh, force_refresh_requested, now_iso,
    read_snapshot, read_status, release_worker_instance, write_snapshot, write_status,
)

STOP = False
_ACTIVE_CHILDREN: dict[int, mp.Process] = {}
_ACTIVE_CHILDREN_LOCK = threading.Lock()
MARKETS = ["us", "idx", "crypto", "commodity", "fx"]
CORE_SECONDS = max(60, int(os.getenv("WARROOM_CORE_REFRESH_SECONDS", "300")))
EVENT_SECONDS = max(15, int(os.getenv("WARROOM_EVENT_REFRESH_SECONDS", "45")))
SLOW_SECONDS = max(300, int(os.getenv("WARROOM_SLOW_REFRESH_SECONDS", "1800")))
EXPANDED_SECONDS = max(SLOW_SECONDS, int(os.getenv("WARROOM_EXPANDED_REFRESH_SECONDS", "3600")))
CONTEXT_SECONDS = max(300, int(os.getenv("WARROOM_CONTEXT_REFRESH_SECONDS", "900")))

LOG_PATH = HERE / "runtime" / "worker.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
LOGGER = logging.getLogger("warroom.worker")
if not LOGGER.handlers:
    LOGGER.setLevel(logging.INFO)
    handler = RotatingFileHandler(LOG_PATH, maxBytes=1_500_000, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    LOGGER.addHandler(handler)


def _terminate_child(process: mp.Process, grace: float = 1.0) -> None:
    try:
        if not process.is_alive():
            return
        process.terminate()
        process.join(grace)
        if process.is_alive():
            try:
                process.kill()
            except AttributeError:
                if process.pid:
                    os.kill(process.pid, signal.SIGKILL)
            process.join(grace)
    except Exception:
        pass


def _stop(*_):
    global STOP
    STOP = True
    with _ACTIVE_CHILDREN_LOCK:
        children = list(_ACTIVE_CHILDREN.values())
    for process in children:
        _terminate_child(process)


def _install_signal_handlers() -> None:
    """Install process signal handlers only from the real main thread.

    Streamlit executes app code in a ScriptRunner thread. Importing this module from an
    embedded fallback worker must therefore never call signal.signal() at import time.
    """
    if threading.current_thread() is not threading.main_thread():
        return
    try:
        signal.signal(signal.SIGTERM, _stop)
        if hasattr(signal, "SIGINT"):
            signal.signal(signal.SIGINT, _stop)
    except (ValueError, OSError):
        pass


def build_core(fast: bool = True, bootstrap: bool = False, refresh_context: bool = False) -> dict:
    import data_layer as DL
    from run import build_desk, build_fast_desk

    prior_bootstrap = os.environ.get("WARROOM_BOOTSTRAP_CORE")
    prior_price_first = os.environ.get("WARROOM_FAST_CORE_PRICE_FIRST")
    if bootstrap:
        os.environ["WARROOM_BOOTSTRAP_CORE"] = "1"
    if refresh_context:
        os.environ["WARROOM_FAST_CORE_PRICE_FIRST"] = "0"
    try:
        data = DL.load_all(
            markets=MARKETS,
            allow_live=True,
            allow_synthetic=False,
            fast_core=fast,
            skip_slow_context=fast,
            bootstrap_core=bootstrap,
        )
    finally:
        if prior_bootstrap is None:
            os.environ.pop("WARROOM_BOOTSTRAP_CORE", None)
        else:
            os.environ["WARROOM_BOOTSTRAP_CORE"] = prior_bootstrap
        if prior_price_first is None:
            os.environ.pop("WARROOM_FAST_CORE_PRICE_FIRST", None)
        else:
            os.environ["WARROOM_FAST_CORE_PRICE_FIRST"] = prior_price_first
    desk = (build_fast_desk(data, top_per_market=(8 if bootstrap else 20)) if fast else build_desk(data, top_per_market=40))
    runtime = desk.setdefault("runtime", {})
    runtime["core_collected_at"] = now_iso()
    runtime["core_profile"] = "BOOTSTRAP" if bootstrap else ("CONTEXT" if refresh_context else ("FAST" if fast else "EXPANDED"))
    return desk


def collect_event_planes(core: dict) -> dict:
    from institutional_data import collect_institutional_data
    from live_market_intelligence import collect_live_market_intelligence

    institutional = collect_institutional_data(core)
    live = collect_live_market_intelligence(core, institutional)
    return {"institutional": institutional, "live_intelligence": live}


def collect_slow_plane(core: dict) -> dict:
    from full_live_data_hub import collect_full_live_data
    return collect_full_live_data(core)


def _child_call(kind: str, payload: Any, result_path: str) -> None:
    """Collector child writes its result to a file, avoiding multiprocessing Queue deadlocks.

    Several War Room planes are multi-megabyte dictionaries. Waiting for a child to exit before
    draining a Queue can block forever when the pipe buffer fills. A temporary pickle is bounded,
    atomic enough for a private child result, and works on Windows spawn as well as POSIX fork.
    """
    # The parent installs a graceful SIGTERM handler for the long-running loop. A bounded child must
    # restore the default handler or process.terminate() only flips STOP and leaves it orphaned.
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
    if hasattr(signal, "SIGINT"):
        signal.signal(signal.SIGINT, signal.SIG_DFL)
    packet: tuple[bool, Any]
    try:
        if kind == "core_bootstrap":
            value = build_core(True, bootstrap=True)
        elif kind == "core_fast":
            value = build_core(True)
        elif kind == "core_context":
            value = build_core(True, refresh_context=True)
        elif kind == "core_expanded":
            value = build_core(False)
        elif kind == "events":
            value = collect_event_planes(payload)
        elif kind == "slow":
            value = collect_slow_plane(payload)
        elif kind == "_test_blob" and os.getenv("WARROOM_TEST_MODE", "0") == "1":
            value = {"blob": "x" * int(payload or 0)}
        elif kind == "_test_sleep" and os.getenv("WARROOM_TEST_MODE", "0") == "1":
            time.sleep(float(payload or 0))
            value = {"slept": float(payload or 0)}
        else:
            raise ValueError(f"unknown collector kind {kind}")
        packet = (True, value)
    except BaseException as exc:
        packet = (False, f"{type(exc).__name__}: {exc}")
    try:
        tmp = result_path + f".{os.getpid()}.tmp"
        with open(tmp, "wb") as fh:
            pickle.dump(packet, fh, protocol=pickle.HIGHEST_PROTOCOL)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass
        os.replace(tmp, result_path)
    except BaseException:
        # Parent will report the missing result file. Never keep a half-written packet.
        pass


def _direct_collect(kind: str, payload: Any) -> dict:
    """Single-process fallback for hosts that disallow child processes.

    This path is used only when explicitly requested or when process creation itself fails.
    Provider adapters still carry their own HTTP timeouts, and the plane remains isolated in the
    worker executor so the Streamlit render thread is never blocked.
    """
    if kind == "core_bootstrap":
        value = build_core(True, bootstrap=True)
    elif kind == "core_fast":
        value = build_core(True)
    elif kind == "core_context":
        value = build_core(True, refresh_context=True)
    elif kind == "core_expanded":
        value = build_core(False)
    elif kind == "events":
        value = collect_event_planes(payload)
    elif kind == "slow":
        value = collect_slow_plane(payload)
    elif kind == "_test_blob" and os.getenv("WARROOM_TEST_MODE", "0") == "1":
        value = {"blob": "x" * int(payload or 0)}
    elif kind == "_test_sleep" and os.getenv("WARROOM_TEST_MODE", "0") == "1":
        time.sleep(float(payload or 0))
        value = {"slept": float(payload or 0)}
    else:
        raise ValueError(f"unknown collector kind {kind}")
    if not isinstance(value, dict):
        raise TypeError(f"{kind} returned {type(value).__name__}, expected dict")
    return value


def run_bounded(kind: str, payload: Any, timeout: int) -> dict:
    """Run a collector in a killable child process, with a hosted single-process fallback."""
    if os.getenv("WARROOM_INPROCESS_COLLECTORS", "0").strip().lower() in {"1", "true", "yes"}:
        return _direct_collect(kind, payload)
    # Always use spawn. Forking from a ThreadPoolExecutor thread can deadlock on Linux
    # after requests/pandas/OpenBLAS have created locks, which was the v2.6 permanent R1 failure.
    start_method = os.getenv("WARROOM_MP_START_METHOD", "spawn").strip().lower()
    if start_method not in {"spawn", "forkserver"}:
        start_method = "spawn"
    try:
        context = mp.get_context(start_method)
    except ValueError:
        context = mp.get_context("spawn")
    fd, result_path = tempfile.mkstemp(prefix=f"warroom_{kind}_", suffix=".pkl", dir=str(HERE / "runtime"))
    os.close(fd)
    try:
        os.unlink(result_path)
    except OSError:
        pass
    process = context.Process(target=_child_call, args=(kind, payload, result_path), daemon=True)
    try:
        process.start()
        if process.pid:
            with _ACTIVE_CHILDREN_LOCK:
                _ACTIVE_CHILDREN[process.pid] = process
    except (OSError, RuntimeError, PermissionError) as exc:
        LOGGER.warning("child process unavailable for %s: %s", kind, exc)
        for path in (result_path,):
            try:
                os.unlink(path)
            except OSError:
                pass
        if os.getenv("WARROOM_ALLOW_INPROCESS_FALLBACK", "0").strip().lower() in {"1", "true", "yes"}:
            return _direct_collect(kind, payload)
        raise RuntimeError(f"child process unavailable for {kind}: {type(exc).__name__}: {exc}") from exc
    try:
        process.join(timeout=max(3, int(timeout)))
        if process.is_alive():
            _terminate_child(process, grace=2.0)
            for path in (result_path, result_path + f".{process.pid}.tmp"):
                try:
                    os.unlink(path)
                except OSError:
                    pass
            raise TimeoutError(f"{kind} exceeded {timeout}s hard timeout")
        if STOP and not os.path.exists(result_path):
            raise RuntimeError(f"{kind} cancelled during worker shutdown")
        if not os.path.exists(result_path):
            raise RuntimeError(f"{kind} child exited with code {process.exitcode} without a result")
        try:
            with open(result_path, "rb") as fh:
                ok, value = pickle.load(fh)
        except Exception as exc:
            raise RuntimeError(f"{kind} produced an unreadable result: {type(exc).__name__}: {exc}") from exc
        finally:
            try:
                os.unlink(result_path)
            except OSError:
                pass
        if not ok:
            raise RuntimeError(str(value))
        if not isinstance(value, dict):
            raise TypeError(f"{kind} returned {type(value).__name__}, expected dict")
        return value
    finally:
        if process.pid:
            with _ACTIVE_CHILDREN_LOCK:
                _ACTIVE_CHILDREN.pop(process.pid, None)


def _overall_state(plane: dict | None) -> str:
    return str((plane or {}).get("overall_state") or (plane or {}).get("state") or "").upper()


def _record_count(plane: dict | None) -> int:
    """Count actual observations, not configuration dictionaries or coverage metadata."""
    if not isinstance(plane, dict):
        return 0
    keys = (
        "events", "options_flow", "dark_pool", "sec_filings", "smart_money",
        "arkham_transfers", "crypto_derivatives", "crypto_options", "us_options",
        "us_short_interest", "us_squeeze", "options_sector_rotation", "sec_fundamentals",
        "intrinio_companies", "etf_flows", "eia", "databento", "idx_live",
    )
    total = 0
    for key in keys:
        value = plane.get(key)
        if isinstance(value, list):
            total += len(value)
        elif isinstance(value, dict):
            total += len(value)
    # Structured public datasets such as CFTC/DeFiLlama may be dictionaries.
    for key in ("cftc", "defillama"):
        value = plane.get(key)
        if isinstance(value, dict):
            total += len(value)
    return total


def _retain_plane(name: str, new: dict | None, old: dict | None) -> tuple[dict, dict | None]:
    """Keep last-good plane when a transient refresh returns an unusable empty/error payload."""
    old = deepcopy(old or {})
    new = deepcopy(new or {})
    bad_states = {"ERROR", "NO_DATA", "OFFLINE", "INITIALIZING", "NOT_CONFIGURED", "NOT_ENTITLED", "ACTION_REQUIRED"}
    new_state = _overall_state(new)
    old_records = _record_count(old)
    new_records = _record_count(new)
    if old_records and new_state in bad_states:
        old.setdefault("runtime", {})["last_refresh_error"] = new.get("note") or new_state or "empty refresh"
        old["runtime"]["retained_last_good"] = True
        old["runtime"]["last_refresh_attempt_at"] = now_iso()
        if old.get("overall_state") == "LIVE":
            old["overall_state"] = "STALE"
        return old, {"plane": name, "action": "RETAINED_LAST_GOOD", "reason": new_state or "EMPTY"}
    new.setdefault("runtime", {})["retained_last_good"] = False
    return new, None


def _market_universe(desk: dict, market: str) -> int:
    return int((((desk.get("markets") or {}).get(market) or {}).get("funnel") or {}).get("universe") or 0)


def _stabilize_core(new: dict, old: dict | None) -> tuple[dict, list[dict]]:
    """Reject catastrophic coverage drops and preserve isolated market/macro last-good data."""
    old = old or {}
    result = deepcopy(new)
    retained: list[dict] = []
    if not old.get("markets"):
        return result, retained

    old_total = sum(_market_universe(old, m) for m in MARKETS)
    new_total = sum(_market_universe(result, m) for m in MARKETS)
    if old_total >= 10 and new_total < max(3, int(old_total * 0.35)):
        # Catastrophic provider outage: reject the whole core refresh.
        kept = deepcopy(old)
        kept.setdefault("runtime", {})["core_last_refresh_error"] = (
            f"coverage collapse {old_total}→{new_total}; retained prior core"
        )
        kept["runtime"]["core_retained_last_good"] = True
        return kept, [{"plane": "core", "action": "REJECTED_COVERAGE_COLLAPSE", "old": old_total, "new": new_total}]

    for market in MARKETS:
        old_n, new_n = _market_universe(old, market), _market_universe(result, market)
        if old_n and new_n < max(1, int(old_n * 0.25)):
            result.setdefault("markets", {})[market] = deepcopy((old.get("markets") or {}).get(market))
            result["markets"][market]["data_state"] = "STALE"
            for row in result["markets"][market].get("setups") or []:
                row["data_state"] = "STALE"
            if (old.get("market_breadth") or {}).get(market):
                result.setdefault("market_breadth", {})[market] = deepcopy(old["market_breadth"][market])
                result["market_breadth"][market]["state"] = "STALE"
            retained.append({"plane": "core", "market": market, "action": "RETAINED_MARKET", "old": old_n, "new": new_n})

    if not result.get("macro_observations") and old.get("macro_observations"):
        result["macro_observations"] = deepcopy(old["macro_observations"])
        retained.append({"plane": "core", "dataset": "macro_observations", "action": "RETAINED_LAST_GOOD"})
    new_sys, old_sys = result.setdefault("systemic", {}), old.get("systemic") or {}
    if str(new_sys.get("liquidity") or "").upper() in {"", "NO_DATA", "INITIALIZING", "NONE"} and old_sys.get("liquidity"):
        for key in ("liquidity", "liquidity_detail"):
            if key in old_sys:
                new_sys[key] = deepcopy(old_sys[key])
        new_sys["liquidity_state"] = "STALE"
        retained.append({"plane": "core", "dataset": "liquidity", "action": "RETAINED_LAST_GOOD"})

    result.setdefault("runtime", {})["core_retained_items"] = retained
    result["runtime"]["core_retained_last_good"] = bool(retained)
    return result, retained


def _dedupe_statuses(rows: list[dict]) -> list[dict]:
    """One newest status per provider+dataset prevents duplicate source counts and status flapping."""
    out: dict[tuple[str, str], dict] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        key = (str(row.get("provider") or ""), str(row.get("dataset") or ""))
        out[key] = row
    return list(out.values())


def _degraded_core_snapshot(error: str, previous: dict | None = None) -> dict:
    """Produce a complete NO_DATA desk when the first live core attempt fails.

    The UI must never remain INITIALIZING forever. Building the normal desk in explicit offline
    mode gives every market/tab a truthful missing-data state and preserves the collector error.
    """
    previous = previous or {}
    old_mode = os.environ.get("WARROOM_NETWORK_MODE")
    try:
        os.environ["WARROOM_NETWORK_MODE"] = "offline"
        desk = build_core(True)
    except Exception:
        desk = {
            "meta": {"source": "NO_DATA", "note": "Initial core collection failed."},
            "systemic": {"liquidity": "NO_DATA", "quad_name": "NO_DATA"},
            "markets": {}, "alpha": [], "reference": {}, "macro_observations": {},
            "market_breadth": {}, "rotation_snapshot": {},
            "data_health": {"overall": "NO_DATA", "sources": [], "live_count": 0, "total_count": 0},
        }
    finally:
        if old_mode is None:
            os.environ.pop("WARROOM_NETWORK_MODE", None)
        else:
            os.environ["WARROOM_NETWORK_MODE"] = old_mode
    runtime = desk.setdefault("runtime", {})
    runtime.update({
        "worker_state": "CORE_ERROR",
        "initial_core_error": error,
        "core_collected_at": now_iso(),
        "core_profile": "DEGRADED_OFFLINE_STATUS",
    })
    desk.setdefault("meta", {})["note"] = f"Live core failed; showing explicit NO_DATA states. {error}"
    health = desk.setdefault("data_health", {})
    health["overall"] = "NO_DATA"
    health["initial_core_error"] = error
    return desk


def merge_snapshot(core: dict, institutional: dict | None, live: dict | None,
                   full: dict | None, previous: dict | None, diagnostics: list[dict] | None = None) -> dict:
    previous = previous or {}
    desk, core_retained = _stabilize_core(core, previous)
    inst, inst_diag = _retain_plane("institutional", institutional, previous.get("institutional"))
    live_plane, live_diag = _retain_plane("live_intelligence", live, previous.get("live_intelligence"))
    full_plane, full_diag = _retain_plane("full_live_data", full, previous.get("full_live_data"))
    desk["institutional"] = inst
    desk["live_intelligence"] = live_plane
    desk["full_live_data"] = full_plane

    health = dict(desk.get("data_health") or {})
    sources = _dedupe_statuses(
        list(health.get("sources") or [])
        + list((inst or {}).get("statuses") or [])
        + list((live_plane or {}).get("statuses") or [])
        + list((full_plane or {}).get("statuses") or [])
    )
    health["sources"] = sources
    health["total_count"] = len(sources)
    health["live_count"] = sum(1 for row in sources if row.get("state") in {"LIVE", "PARTIAL", "STALE", "NO_SIGNAL", "CASH_ONLY"})
    core_observations = sum(_market_universe(desk, m) for m in MARKETS)
    macro_observations = len(desk.get("macro_observations") or {})
    if core_observations == 0 and macro_observations == 0:
        health["overall"] = "NO_DATA"
    else:
        health["overall"] = (
            "LIVE" if sources and all(row.get("state") in {"LIVE", "STANDBY", "NO_SIGNAL", "CASH_ONLY"} for row in sources)
            else "PARTIAL" if health["live_count"] else "NO_DATA"
        )
    health["core_observations"] = core_observations
    health["macro_observations"] = macro_observations
    desk["data_health"] = health

    coverage = dict((full_plane or {}).get("tab_coverage") or {})
    valid = {"LIVE", "STALE", "PARTIAL", "NO_SIGNAL"}
    derivative_records = sum(
        len([x for x in (live_plane.get(key) or []) if x.get("state") in valid])
        for key in ("crypto_derivatives", "crypto_options", "us_options")
    )
    if "derivatives_squeeze" in coverage and derivative_records:
        coverage["derivatives_squeeze"]["state"] = "LIVE" if derivative_records >= 3 else "PARTIAL"
        coverage["derivatives_squeeze"]["cross_plane_records"] = derivative_records
    if "us_stocks" in coverage and any(x.get("state") in {"LIVE", "STALE"} for x in live_plane.get("us_options") or []):
        if coverage["us_stocks"].get("state") == "NO_DATA":
            coverage["us_stocks"]["state"] = "PARTIAL"
    if "institutional" in coverage:
        inst_state = str(inst.get("overall_state") or "").upper()
        inst_records = len(inst.get("events") or [])
        if inst_records:
            coverage["institutional"]["state"] = "LIVE" if inst_state == "LIVE" else "PARTIAL"
            coverage["institutional"]["cross_plane_records"] = inst_records
        elif inst_state in {"NO_SIGNAL", "LIVE", "STALE"}:
            coverage["institutional"]["state"] = "NO_SIGNAL" if inst_state == "NO_SIGNAL" else inst_state
        elif inst_state in {"ACTION_REQUIRED", "NOT_ENTITLED", "NOT_CONFIGURED"} and coverage["institutional"].get("state") == "NO_DATA":
            coverage["institutional"]["state"] = inst_state
    if full_plane is not None:
        full_plane["tab_coverage"] = coverage

    all_diag = list(diagnostics or []) + core_retained + [x for x in (inst_diag, live_diag, full_diag) if x]
    runtime = desk.setdefault("runtime", {})
    health_state = str(health.get("overall") or "").upper()
    merged_worker_state = (
        "CORE_ERROR" if runtime.get("initial_core_error") and health_state == "NO_DATA"
        else "NO_DATA" if health_state == "NO_DATA"
        else "LIVE"
    )
    runtime.update({
        "worker_state": merged_worker_state,
        "worker_heartbeat_at": now_iso(),
        "stability_events": all_diag[-30:],
        "institutional_collected_at": (inst.get("generated") or runtime.get("institutional_collected_at")),
        "derivatives_collected_at": (live_plane.get("generated") or runtime.get("derivatives_collected_at")),
        "slow_plane_collected_at": (full_plane.get("generated") or runtime.get("slow_plane_collected_at")),
    })
    return desk


def _current_core(snapshot: dict) -> dict:
    """The merged snapshot itself is a valid core base for event/slow collectors."""
    return deepcopy(snapshot)


def bootstrap_snapshot_once(*, direct: bool = False, previous: dict | None = None, commit: bool = True) -> dict:
    """Commit the first non-initializing snapshot and return a compact result.

    Hosted Streamlit calls this once before embedding the dashboard.  It deliberately collects only
    the small market bootstrap universe; macro/liquidity and paid enrichment arrive on later planes.
    A failed public fetch still commits an explicit R2 NO_DATA snapshot, so the browser can never
    remain on bootstrap revision R1 indefinitely.
    """
    previous = previous or read_snapshot() or {}
    timeout = int(os.getenv("WARROOM_BOOTSTRAP_HARD_TIMEOUT", "22"))
    write_status(state="BOOTSTRAP_CORE", pid=os.getpid(), pending=["bootstrap"], error=None)
    try:
        value = build_core(True, bootstrap=True) if direct else run_bounded("core_bootstrap", None, timeout)
        core, diagnostics = _stabilize_core(value, previous)
        snapshot = merge_snapshot(core, previous.get("institutional"), previous.get("live_intelligence"), previous.get("full_live_data"), previous, diagnostics)
        result = write_snapshot(snapshot, force=True) if commit else {"revision": int(((previous.get("runtime") or {}).get("snapshot_sequence") or 1)) + 1}
        if commit:
            write_status(
                state="BOOTSTRAP_READY" if sum(_market_universe(core, m) for m in MARKETS) else "BOOTSTRAP_NO_DATA",
                pid=os.getpid(), pending=[], error=None,
                snapshot_revision=result.get("revision"), last_success=now_iso(),
            )
        return {
            "ok": bool(sum(_market_universe(core, m) for m in MARKETS)),
            "revision": result.get("revision"),
            "observations": sum(_market_universe(core, m) for m in MARKETS),
            "health": (snapshot.get("data_health") or {}).get("overall"),
            "snapshot": snapshot if not commit else None,
        }
    except BaseException as exc:
        error_text = f"{type(exc).__name__}: {exc}"
        LOGGER.exception("inline/bootstrap core failed: %s", exc)
        core = _degraded_core_snapshot(error_text, previous)
        snapshot = merge_snapshot(core, previous.get("institutional"), previous.get("live_intelligence"), previous.get("full_live_data"), previous, [{"plane": "bootstrap", "action": "REFRESH_ERROR", "error": error_text, "at": now_iso()}])
        result = write_snapshot(snapshot, force=True) if commit else {"revision": int(((previous.get("runtime") or {}).get("snapshot_sequence") or 1)) + 1}
        if commit:
            write_status(state="BOOTSTRAP_ERROR", pid=os.getpid(), pending=[], error=error_text, snapshot_revision=result.get("revision"))
        return {"ok": False, "revision": result.get("revision"), "observations": 0, "health": "NO_DATA", "error": error_text, "snapshot": snapshot if not commit else None}


def loop() -> None:
    """Long-running collector with fatal-error reporting and guaranteed lease cleanup."""
    _install_signal_handlers()
    claimed = False
    executor: ThreadPoolExecutor | None = None
    try:
        # Atomic lease prevents simultaneous Streamlit sessions/manual launches from racing.
        if not claim_worker_instance():
            LOGGER.info("collector start skipped: another worker owns the instance lease")
            return
        claimed = True
        LOGGER.info("collector started pid=%s", os.getpid())
        write_status(state="BOOTING", pid=os.getpid(), pending=[], error=None)

        previous = read_snapshot() or {}
        previous_has_core = (
            sum(_market_universe(previous, market) for market in MARKETS) > 0
            or len(previous.get("macro_observations") or {}) > 0
        )
        core = _current_core(previous) if previous_has_core else None
        institutional = previous.get("institutional")
        live = previous.get("live_intelligence")
        full = previous.get("full_live_data")
        startup_now = time.time()
        last_started = {
            "core": startup_now - max(0, CORE_SECONDS - int(os.getenv("WARROOM_POST_BOOTSTRAP_CORE_DELAY", "20"))),
            "context": 0.0,
            "events": startup_now - max(0, EVENT_SECONDS - int(os.getenv("WARROOM_POST_BOOTSTRAP_EVENT_DELAY", "15"))),
            "slow": startup_now,
            "expanded": startup_now,
        }
        pending: dict[str, Future] = {}
        diagnostics: list[dict] = []
        last_success = str((read_status() or {}).get("last_success") or "")
        # Commit a small market-only snapshot synchronously before background planes start.
        # This removes the all-or-nothing R1 bootstrap and makes startup deterministic.
        if core is None:
            bootstrap_timeout = int(os.getenv("WARROOM_BOOTSTRAP_HARD_TIMEOUT", "28"))
            write_status(state="BOOTSTRAP_CORE", pid=os.getpid(), pending=["bootstrap"], error=None)
            try:
                bootstrap_value = run_bounded("core_bootstrap", None, bootstrap_timeout)
                core, bootstrap_diag = _stabilize_core(bootstrap_value, previous)
                diagnostics.extend(bootstrap_diag)
                last_success = now_iso()
                bootstrap_snapshot = merge_snapshot(core, institutional, live, full, previous, diagnostics)
                bootstrap_result = write_snapshot(bootstrap_snapshot, force=True)
                previous = read_snapshot() or bootstrap_snapshot
                LOGGER.info("bootstrap commit revision=%s observations=%s", bootstrap_result.get("revision"), sum(_market_universe(core, m) for m in MARKETS))
            except Exception as exc:
                error_text = f"{type(exc).__name__}: {exc}"
                LOGGER.exception("bootstrap core failed: %s", exc)
                core = _degraded_core_snapshot(error_text, previous)
                diagnostics.append({"plane": "bootstrap", "action": "REFRESH_ERROR", "error": error_text, "at": now_iso()})
                bootstrap_snapshot = merge_snapshot(core, institutional, live, full, previous, diagnostics)
                write_snapshot(bootstrap_snapshot, force=True)
                previous = read_snapshot() or bootstrap_snapshot
                write_status(state="BOOTSTRAP_ERROR", pid=os.getpid(), pending=[], error=error_text)

        executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="warroom-plane")

        timeouts = {
            "core": int(os.getenv("WARROOM_FAST_CORE_HARD_TIMEOUT", "90")),
            "context": int(os.getenv("WARROOM_CONTEXT_HARD_TIMEOUT", "90")),
            "events": int(os.getenv("WARROOM_EVENT_HARD_TIMEOUT", "75")),
            "slow": int(os.getenv("WARROOM_SLOW_HARD_TIMEOUT", "120")),
            "expanded": int(os.getenv("WARROOM_EXPANDED_CORE_HARD_TIMEOUT", "240")),
        }

        def schedule(name: str, kind: str, payload: dict | None = None) -> None:
            if name in pending:
                return
            write_status(state=f"COLLECTING_{name.upper()}", pid=os.getpid(), pending=sorted([*pending, name]))
            LOGGER.info("schedule %s kind=%s", name, kind)
            pending[name] = executor.submit(run_bounded, kind, payload, timeouts[name])
            last_started[name] = time.time()

        try:
            while not STOP:
                force = consume_force_refresh()
                now = time.time()
                core_retry_seconds = min(CORE_SECONDS, max(30, int(os.getenv("WARROOM_INITIAL_CORE_RETRY_SECONDS", "60"))))
                core_due = (core is None and now - last_started["core"] >= core_retry_seconds) or (core is not None and now - last_started["core"] >= CORE_SECONDS)
                if (force or core_due) and "core" not in pending:
                    schedule("core", "core_fast")
                context_due = now - last_started["context"] >= CONTEXT_SECONDS
                if (force or context_due) and "context" not in pending:
                    schedule("context", "core_context")
                core_ready = bool(core) and (
                    sum(_market_universe(core, m) for m in MARKETS) > 0
                    or len((core or {}).get("macro_observations") or {}) > 0
                )
                if core_ready and (force or now - last_started["events"] >= EVENT_SECONDS) and "events" not in pending:
                    schedule("events", "events", core)
                if core_ready and (force or now - last_started["slow"] >= SLOW_SECONDS) and "slow" not in pending:
                    schedule("slow", "slow", core)
                if core_ready and (force or now - last_started["expanded"] >= EXPANDED_SECONDS) and "expanded" not in pending:
                    schedule("expanded", "core_expanded")

                changed = False
                for name, future in list(pending.items()):
                    if not future.done():
                        continue
                    pending.pop(name, None)
                    try:
                        value = future.result()
                        if name in {"core", "context"}:
                            core, core_diag = _stabilize_core(value, core or previous)
                            diagnostics.extend(core_diag)
                        elif name == "expanded":
                            candidate, core_diag = _stabilize_core(value, core or previous)
                            if sum(_market_universe(candidate, m) for m in MARKETS) >= sum(_market_universe(core or {}, m) for m in MARKETS):
                                core = candidate
                            diagnostics.extend(core_diag)
                        elif name == "events":
                            institutional = value.get("institutional")
                            live = value.get("live_intelligence")
                        elif name == "slow":
                            full = value
                        last_success = now_iso()
                        diagnostics.append({"plane": name, "action": "REFRESH_OK", "at": last_success})
                        LOGGER.info("refresh ok plane=%s", name)
                        changed = True
                    except Exception as exc:
                        error_text = f"{type(exc).__name__}: {exc}"
                        diagnostics.append({"plane": name, "action": "REFRESH_ERROR", "error": error_text, "at": now_iso()})
                        LOGGER.exception("refresh error plane=%s: %s", name, exc)
                        write_status(state=f"{name.upper()}_ERROR", pid=os.getpid(), error=error_text)
                        if name == "core" and core is None:
                            core = _degraded_core_snapshot(error_text, previous)
                            changed = True

                if changed and core is not None:
                    snapshot = merge_snapshot(core, institutional, live, full, previous, diagnostics)
                    result = write_snapshot(snapshot)
                    previous = read_snapshot() or snapshot
                    LOGGER.info("snapshot commit written=%s changed=%s revision=%s", result.get("written"), result.get("changed"), result.get("revision"))

                if pending:
                    loop_state = "COLLECTING"
                elif core is not None and str(((core.get("data_health") or {}).get("overall") or "")).upper() == "NO_DATA":
                    loop_state = "DEGRADED"
                else:
                    loop_state = "IDLE"
                write_status(
                    state=loop_state,
                    pid=os.getpid(), pending=sorted(pending), last_success=last_success or None,
                    snapshot_revision=int(((previous.get("runtime") or {}).get("snapshot_sequence") or 0)),
                    force_pending=force_refresh_requested(),
                )
                for _ in range(10):
                    if STOP or force_refresh_requested():
                        break
                    time.sleep(0.5)
        finally:
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)
    except BaseException as exc:
        LOGGER.exception("collector fatal error: %s", exc)
        try:
            write_status(state="WORKER_FATAL", pid=os.getpid(), pending=[], error=f"{type(exc).__name__}: {exc}")
        except Exception:
            pass
        raise
    finally:
        if claimed:
            release_worker_instance()
        LOGGER.info("collector stopped pid=%s", os.getpid())
        current_state = str((read_status() or {}).get("state") or "")
        if current_state != "WORKER_FATAL":
            write_status(state="STOPPED" if STOP else current_state or "STOPPED", pid=os.getpid(), pending=[])

def run_once(previous: dict | None = None) -> dict:
    previous = previous or read_snapshot() or {}
    core = run_bounded("core_fast", None, int(os.getenv("WARROOM_FAST_CORE_HARD_TIMEOUT", "90")))
    with ThreadPoolExecutor(max_workers=2) as pool:
        event_future = pool.submit(run_bounded, "events", core, int(os.getenv("WARROOM_EVENT_HARD_TIMEOUT", "75")))
        slow_future = pool.submit(run_bounded, "slow", core, int(os.getenv("WARROOM_SLOW_HARD_TIMEOUT", "120")))
        event_value = event_future.result()
        full = slow_future.result()
    snapshot = merge_snapshot(core, event_value.get("institutional"), event_value.get("live_intelligence"), full, previous)
    write_snapshot(snapshot, force=True)
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        if not claim_worker_instance():
            raise SystemExit("another War Room worker is already running")
        try:
            run_once()
        finally:
            release_worker_instance()
    else:
        loop()


if __name__ == "__main__":
    main()
