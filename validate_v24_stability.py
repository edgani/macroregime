"""Deterministic regression checks for War Room OS v2.4 stability architecture.

Default mode avoids external network and credentials. Use --stress for the killable-child tests.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

RESULTS: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append({"name": name, "pass": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def static_checks() -> None:
    app = (HERE / "app.py").read_text(encoding="utf-8")
    html = (HERE / "dashboard.html").read_text(encoding="utf-8")
    config = (HERE / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    worker = (HERE / "warroom_data_worker.py").read_text(encoding="utf-8")
    runtime = (HERE / "runtime_store.py").read_text(encoding="utf-8")
    run = (HERE / "run.py").read_text(encoding="utf-8")

    check("single static iframe shell", not re.search(r"\bst\.fragment\s*\(", app) and not re.search(r"\bcomponents\.html\s*\(", app) and "st.iframe" in app,
          "Streamlit must not remount HTML on refresh")
    check("static serving enabled", "enableStaticServing = true" in config and "dashboard_live.html" in app)
    check("browser polls atomic static snapshot", "desk_snapshot.json" in html and "pollSnapshot" in html and "pollInFlight" in html)
    check("content hash gates redraw", "hash===lastContentHash" in html and "requestAnimationFrame(render)" in html)
    check("section DOM diffing", "el&&el.innerHTML!==html" in html)
    check("visual motion disabled", ".edge.active" in html and "animation:none" in html and ".tape-track" in html)
    check("no generic rerun timer", "st_autorefresh" not in app and "run_every" not in app)
    check("one worker instance lease", "claim_worker_instance" in worker and "worker.instance.lock" in runtime)
    check("atomic snapshot writes", "os.replace(tmp, path)" in runtime and "STATIC_SNAPSHOT" in runtime)
    check("heartbeat excluded from snapshot hash", "if key == \"runtime\"" in runtime and "worker_status.json" in runtime)
    check("large child payload avoids queue", "pickle.dump(packet" in worker and not re.search(r"\b(?:mp\.)?Queue\s*\(", worker))
    check("bounded child restores terminate semantics", "signal.SIG_DFL" in worker and "process.kill" in worker)
    check("no-data status derives from records", "records = len((price_markets.get(name) or {}))" in run)
    check("synthetic-disabled is not synthetic-test", '"synthetic disabled" not in low' in run)
    check("inactive nodes cannot emit arrows", all(x in html for x in ["not_entitled","action_required","offline","initializing","no_signal"]))
    check("market arrow lineage has no modulo routing", "% l2.length" not in html and "parent=l2.find(m=>m.market===c.market)" in html)

    # JavaScript parse test.
    script = html[html.rfind("<script>") + len("<script>"):html.rfind("</script>")]
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
        fh.write(script)
        js_path = fh.name
    try:
        proc = subprocess.run(["node", "--check", js_path], capture_output=True, text=True, timeout=30)
        check("dashboard JavaScript syntax", proc.returncode == 0, proc.stderr.strip())
    finally:
        Path(js_path).unlink(missing_ok=True)


def semantic_checks() -> None:
    from runtime_store import content_hash
    from run import _data_health
    from gcfis.markets import market_of

    base = {
        "meta": {"generated": "2026-01-01T00:00:00Z", "source": "LIVE"},
        "runtime": {"worker_heartbeat_at": "a", "snapshot_sequence": 1},
        "markets": {"us": {"bias": "NEUTRAL"}},
        "data_health": {"sources": [
            {"provider": "B", "dataset": "x", "state": "LIVE", "fetched_at": "a"},
            {"provider": "A", "dataset": "y", "state": "NO_SIGNAL", "fetched_at": "a"},
        ]},
    }
    changed_only_volatile = copy.deepcopy(base)
    changed_only_volatile["meta"]["generated"] = "2026-01-02T00:00:00Z"
    changed_only_volatile["runtime"] = {"worker_heartbeat_at": "b", "snapshot_sequence": 99}
    changed_only_volatile["data_health"]["sources"].reverse()
    changed_only_volatile["data_health"]["sources"][0]["fetched_at"] = "b"
    check("stable hash ignores heartbeat/timestamp/order", content_hash(base) == content_hash(changed_only_volatile))
    meaningful = copy.deepcopy(base)
    meaningful["markets"]["us"]["bias"] = "LEAN_SHORT"
    check("stable hash changes on visible state", content_hash(base) != content_hash(meaningful))

    empty_data = {
        "sources": {"us": "per-market fallback · NO_DATA (live source unavailable; synthetic disabled)"},
        "prices": {"us": {}}, "fred": {}, "fred_source": "OFFLINE", "feeds": {"_status": {}},
    }
    h = _data_health(empty_data)
    check("empty market never labeled live", h["sources"][0]["state"] in {"NO_DATA", "OFFLINE"}, str(h["sources"][0]))
    synthetic_data = {
        "sources": {"us": "synthetic (explicit test-only)"}, "prices": {"us": {"SPY": [1,2]}},
        "fred": {}, "fred_source": "OFFLINE", "feeds": {"_status": {}},
    }
    hs = _data_health(synthetic_data)
    check("explicit synthetic remains test-only", hs["sources"][0]["state"] == "SYNTHETIC_TEST")

    expected = {
        "STRK-USD": "crypto", "TAO-USD": "crypto", "SI=F": "commodity", "^JKSE": "idx",
        "BBCA.JK": "idx", "JPY=X": "fx", "IDR=X": "fx", "DX-Y.NYB": "fx", "AMD": "us",
    }
    actual = {ticker: market_of(ticker) for ticker in expected}
    check("market symbol routing", actual == expected, json.dumps(actual, sort_keys=True))


def app_test() -> None:
    old = os.environ.get("WARROOM_DISABLE_AUTOSTART")
    os.environ["WARROOM_DISABLE_AUTOSTART"] = "1"
    try:
        from streamlit.testing.v1 import AppTest
        at = AppTest.from_file(str(HERE / "app.py"), default_timeout=30).run(timeout=30)
        check("Streamlit app has no exception", len(at.exception) == 0,
              "; ".join(str(e.value) for e in at.exception))
        check("Streamlit mounts exactly one iframe", len(at.get("iframe")) == 1, str(len(at.get("iframe"))))
    finally:
        if old is None:
            os.environ.pop("WARROOM_DISABLE_AUTOSTART", None)
        else:
            os.environ["WARROOM_DISABLE_AUTOSTART"] = old


def stress_checks() -> None:
    import multiprocessing as mp
    import warroom_data_worker as w

    original = w.build_core
    try:
        w.build_core = lambda fast=True: {"blob": "x" * 5_000_000, "markets": {}}
        started = time.time()
        out = w.run_bounded("core_fast", None, 15)
        check("large child payload transport", len(out.get("blob", "")) == 5_000_000,
              f"elapsed={time.time()-started:.2f}s")

        def sleepy(fast=True):
            time.sleep(30)
            return {}
        w.build_core = sleepy
        started = time.time()
        timed_out = False
        try:
            w.run_bounded("core_fast", None, 10)
        except TimeoutError:
            timed_out = True
        time.sleep(0.3)
        check("hard timeout terminates collector", timed_out and not mp.active_children(),
              f"elapsed={time.time()-started:.2f}s children={[(c.pid,c.is_alive()) for c in mp.active_children()]}")
    finally:
        w.build_core = original


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stress", action="store_true")
    parser.add_argument("--write-report", default="")
    args = parser.parse_args()
    started = time.time()
    try:
        static_checks()
        semantic_checks()
        app_test()
        if args.stress:
            stress_checks()
        status = "PASS"
        error = None
    except Exception as exc:
        status = "FAIL"
        error = f"{type(exc).__name__}: {exc}"
    report = {
        "status": status,
        "version": "2.4",
        "offline_deterministic": True,
        "stress_enabled": args.stress,
        "elapsed_seconds": round(time.time() - started, 3),
        "checks": RESULTS,
        "error": error,
        "not_verified_here": [
            "authenticated provider credentials and paid entitlements",
            "external endpoint reachability from the user's machine",
            "exchange/provider schema changes after packaging",
            "full browser E2E rendering (container Chromium blocks local/file navigation by administrator policy)",
        ],
    }
    text = json.dumps(report, indent=2)
    print(text)
    if args.write_report:
        Path(args.write_report).write_text(text + "\n", encoding="utf-8")
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
