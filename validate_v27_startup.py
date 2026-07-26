from __future__ import annotations

import json
import os
import pickle
import signal
import subprocess
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
STATIC = HERE / "static"
CACHE = HERE / ".cache" / "price_cache.pkl"

BOOT = {
    "meta": {"source": "INITIALIZING", "generated": "—", "note": "startup validation boot"},
    "runtime": {
        "worker_state": "STARTING", "architecture": "background-worker/static-json-polling",
        "snapshot_sequence": 1, "content_hash": "boot-v27-test",
    },
    "data_health": {"overall": "INITIALIZING", "sources": [], "live_count": 0, "total_count": 0},
    "systemic": {"liquidity": "INITIALIZING", "quad_name": "INITIALIZING"},
    "markets": {}, "alpha": [], "reference": {}, "macro_observations": {},
    "market_breadth": {}, "rotation_snapshot": {},
    "institutional": {"overall_state": "INITIALIZING", "statuses": [], "events": []},
    "live_intelligence": {
        "overall_state": "INITIALIZING", "statuses": [], "events": [],
        "crypto_derivatives": [], "crypto_options": [], "us_options": [], "us_squeeze": [],
    },
    "full_live_data": {"overall_state": "INITIALIZING", "statuses": [], "tab_coverage": {}},
}

RUNTIME_FILES = [
    RUNTIME / "desk_snapshot.json", RUNTIME / "worker_status.json", RUNTIME / "worker.pid",
    RUNTIME / "worker.instance.lock", RUNTIME / "worker_start.lock", RUNTIME / "force_refresh.flag",
    RUNTIME / "worker.log", RUNTIME / "worker_boot.log",
    STATIC / "desk_snapshot.json", STATIC / "worker_status.json", CACHE,
]


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


@contextmanager
def preserve_runtime():
    saved = {path: _read(path) for path in RUNTIME_FILES}
    try:
        yield
    finally:
        for path in RUNTIME_FILES:
            try:
                path.unlink()
            except OSError:
                pass
        for path, data in saved.items():
            if data is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)


def reset_boot() -> None:
    RUNTIME.mkdir(exist_ok=True)
    STATIC.mkdir(exist_ok=True)
    for path in RUNTIME_FILES:
        try:
            path.unlink()
        except OSError:
            pass
    payload = json.dumps(BOOT, separators=(",", ":")).encode()
    (RUNTIME / "desk_snapshot.json").write_bytes(payload)
    (STATIC / "desk_snapshot.json").write_bytes(payload)


def make_price_fixture() -> None:
    from data.loader import YAHOO_ALIASES

    names = [
        "SPY", "QQQ", "IWM", "NVDA", "AMD", "MSFT",
        "^JKSE", "BBCA.JK", "BMRI.JK", "BBRI.JK",
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "DOGE-USD",
        "CL=F", "BZ=F", "GC=F", "SI=F", "HG=F", "NG=F",
        "EURUSD=X", "JPY=X", "GBPUSD=X", "AUDUSD=X", "IDR=X", "DX-Y.NYB",
    ]
    index = pd.date_range(end=pd.Timestamp.today().normalize(), periods=520, freq="B")
    cache = {}
    for i, name in enumerate(names):
        base = 40.0 + i * 2.7
        wave = np.sin(np.arange(len(index)) / 19.0 + i) * 0.00045
        close = base * np.exp(np.cumsum(0.00018 + wave))
        frame = pd.DataFrame(
            {
                "Open": close * 0.997,
                "High": close * 1.009,
                "Low": close * 0.991,
                "Close": close,
                "Volume": 1_000_000.0 + i * 10_000,
            },
            index=index,
        )
        cache[YAHOO_ALIASES.get(name, name)] = (time.time(), frame)
    CACHE.parent.mkdir(exist_ok=True)
    CACHE.write_bytes(pickle.dumps(cache, protocol=pickle.HIGHEST_PROTOCOL))


def launch(extra_env: dict[str, str]) -> subprocess.Popen:
    env = os.environ.copy()
    env.update(
        {
            "WARROOM_HOSTED_MODE": "1",
            "WARROOM_PRICE_BACKEND": "http",
            "WARROOM_ENABLE_YFINANCE_FALLBACK": "0",
            "WARROOM_PRICE_HTTP_TIMEOUT": "2",
            "WARROOM_PRICE_HTTP_WORKERS": "8",
            "WARROOM_BOOTSTRAP_HARD_TIMEOUT": "18",
            "WARROOM_FAST_CORE_HARD_TIMEOUT": "30",
            "WARROOM_FAST_CORE_PRICE_FIRST": "1",
            "WARROOM_MP_START_METHOD": "spawn",
            "WARROOM_POST_BOOTSTRAP_CORE_DELAY": "300",
        }
    )
    env.update(extra_env)
    return subprocess.Popen(
        [sys.executable, str(HERE / "warroom_data_worker.py")], cwd=HERE, env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )


def wait_snapshot(timeout: float) -> tuple[dict, float]:
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        try:
            snap = json.loads((RUNTIME / "desk_snapshot.json").read_text())
        except Exception:
            time.sleep(0.2)
            continue
        if int((snap.get("runtime") or {}).get("snapshot_sequence") or 0) >= 2:
            return snap, time.monotonic() - start
        time.sleep(0.2)
    raise TimeoutError(f"snapshot remained at R1 for {timeout:.1f}s")


def stop(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.send_signal(signal.SIGTERM)
        proc.wait(timeout=8)
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass


def market_counts(snapshot: dict) -> dict[str, int]:
    return {
        market: int((((snapshot.get("markets") or {}).get(market) or {}).get("funnel") or {}).get("universe") or 0)
        for market in ("us", "idx", "crypto", "commodity", "fx")
    }


def main() -> int:
    report: dict = {"version": "2.7", "tests": []}
    with preserve_runtime():
        reset_boot()
        make_price_fixture()
        proc = launch({})
        try:
            snap, elapsed = wait_snapshot(18)
            counts = market_counts(snap)
            ok = all(counts[name] > 0 for name in counts)
            report["tests"].append(
                {
                    "name": "staged_bootstrap_fixture",
                    "ok": ok,
                    "elapsed_seconds": round(elapsed, 3),
                    "revision": (snap.get("runtime") or {}).get("snapshot_sequence"),
                    "health": (snap.get("data_health") or {}).get("overall"),
                    "counts": counts,
                }
            )
        finally:
            stop(proc)

        reset_boot()
        proc = launch({"WARROOM_NETWORK_MODE": "offline"})
        try:
            snap, elapsed = wait_snapshot(12)
            state = str((snap.get("data_health") or {}).get("overall") or "")
            ok = state == "NO_DATA" and str((snap.get("meta") or {}).get("source") or "") != "INITIALIZING"
            report["tests"].append(
                {
                    "name": "offline_exits_initializing",
                    "ok": ok,
                    "elapsed_seconds": round(elapsed, 3),
                    "revision": (snap.get("runtime") or {}).get("snapshot_sequence"),
                    "health": state,
                    "counts": market_counts(snap),
                }
            )
        finally:
            stop(proc)

    report["ok"] = all(test["ok"] for test in report["tests"])
    output = HERE / "V27_STARTUP_VALIDATION_REPORT.json"
    output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
