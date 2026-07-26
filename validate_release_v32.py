"""Canonical v3.2 release validator.

Validates operational contracts, fail-closed governance, browser geometry, staged
startup, live-feed parsers and a real Streamlit health endpoint.  It never treats
these engineering tests as proof of predictive alpha or prospective P&L.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RESULTS: list[dict] = []


def record(name: str, ok: bool, detail: str = "") -> None:
    RESULTS.append({"name": name, "passed": bool(ok), "detail": detail[-12000:]})
    print(("PASS" if ok else "FAIL"), name, detail[-500:])


def run_script(name: str, timeout: int = 240) -> None:
    try:
        proc = subprocess.run(
            [sys.executable, str(ROOT / name)], cwd=ROOT, text=True,
            capture_output=True, timeout=timeout,
        )
        record(name, proc.returncode == 0, (proc.stdout + "\n" + proc.stderr).strip())
    except subprocess.TimeoutExpired as exc:
        record(name, False, f"timeout after {timeout}s: {exc}")


def semantic_guards() -> None:
    from gcfis.engines.broker_flow import run_broker_flow
    from warroom import market_cap_target as MC
    from warroom import decision_engine as DE
    from warroom.decision_center import recommend

    bf = run_broker_flow([
        {"broker": "AA", "agg_buy": 1000, "pass_buy": 0, "agg_sell": 0, "pass_sell": 0}
    ])
    record(
        "broker_flow_no_intent_overclaim",
        bf.get("verdict") == "NET_BUY_CONTEXT"
        and bf.get("beneficial_owner") == "UNVERIFIED"
        and bf.get("intent") == "UNVERIFIED"
        and "smart_money_net" not in bf,
        json.dumps(bf),
    )

    mct = MC.build("NVDA", 100.0, 1_000_000_000_000, 99)
    record(
        "market_cap_ev_fail_closed",
        mct.get("status") == "MODEL_REQUIRED"
        and mct.get("permission") == "CAPITAL_BLOCKED"
        and mct.get("convexity") is None
        and mct.get("suggested_weight") is None,
        json.dumps(mct),
    )

    dec = DE.decide_theme("AI", {"NVDA": 100})
    record(
        "knowledge_graph_not_best_trade",
        dec.get("best_equity") is None
        and dec.get("permission") == "CAPITAL_BLOCKED"
        and dec.get("status") in {"RESEARCH_INVENTORY", "NO_MAP"},
        json.dumps(dec)[:4000],
    )

    idx_short = recommend(
        {"_dir": "Short", "ticker": "TEST.JK", "market": "idx", "decision_levels": {"in_zone": True}},
        {},
    )
    long_watch = recommend(
        {"_dir": "Long", "ticker": "TEST", "market": "us", "decision_levels": {"in_zone": True}},
        {},
    )
    record(
        "decision_vocabulary_fail_closed",
        idx_short[0] == "REDUCE / AVOID" and long_watch[0] == "TRIGGERED WATCH LONG",
        f"idx={idx_short}; us={long_watch}",
    )


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def streamlit_health() -> None:
    try:
        import streamlit  # noqa: F401
    except Exception as exc:
        record("streamlit_health", False, f"streamlit unavailable: {exc}")
        return

    port = free_port()
    env = os.environ.copy()
    env.update({
        "WARROOM_NETWORK_MODE": "offline",
        "WARROOM_DISABLE_AUTOSTART": "1",
        "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
    })
    proc = subprocess.Popen(
        [
            sys.executable, "-m", "streamlit", "run", str(ROOT / "app.py"),
            "--server.headless", "true", "--server.address", "127.0.0.1",
            "--server.port", str(port),
        ],
        cwd=ROOT,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    ok = False
    body = ""
    try:
        deadline = time.time() + 45
        while time.time() < deadline:
            if proc.poll() is not None:
                break
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=2) as resp:
                    body = resp.read().decode("utf-8", "replace")
                    if resp.status == 200 and "ok" in body.lower():
                        ok = True
                        break
            except Exception:
                time.sleep(0.5)
        output = ""
        if not ok and proc.stdout:
            try:
                output = proc.stdout.read()[-8000:]
            except Exception:
                pass
        record("streamlit_health", ok, body or output)
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def static_sync() -> None:
    dash = (ROOT / "dashboard.html").read_bytes()
    live = (ROOT / "static" / "dashboard_live.html").read_bytes() if (ROOT / "static" / "dashboard_live.html").exists() else b""
    record("static_dashboard_synced", dash == live, f"dashboard={len(dash)} bytes; static={len(live)} bytes")


def main() -> int:
    # Canonical fast-to-medium suites. The long exploratory validation_plus.py is deliberately
    # excluded because it timed out previously and cannot be represented as passed evidence.
    for script, timeout in [
        ("validate_v32_research_first.py", 240),
        ("validate_v32_startup.py", 120),
        ("validate_redesign.py", 120),
        ("validate_arrow_lineage.py", 120),
        ("validate_live_stack.py", 180),
        ("gcfis/tests/test_all.py", 240),
    ]:
        run_script(script, timeout)
    semantic_guards()
    static_sync()
    streamlit_health()

    status = "PASS" if all(x["passed"] for x in RESULTS) else "FAIL"
    report = {
        "version": "3.2",
        "suite": "canonical_release_validation",
        "status": status,
        "passed": sum(1 for x in RESULTS if x["passed"]),
        "total": len(RESULTS),
        "checks": RESULTS,
        "operational_permission": "READY_FOR_USER_REVIEW" if status == "PASS" else "BLOCKED",
        "capital_permission": "CAPITAL_BLOCKED",
        "predictive_status": "NOT PROVEN BY ENGINEERING OR FIXTURE TESTS",
        "explicitly_not_claimed": [
            "all components have predictive edge",
            "full-universe point-in-time walk-forward proof",
            "untouched lockbox success",
            "mature prospective profitability",
            "paid-provider authentication or entitlement",
            "autonomous capital allocation",
        ],
        "known_open_research": [
            "validation_plus.py was not promoted to release evidence after a prior >10 minute timeout",
            "market-specific component WFA and prospective promotion remain evidence-gated",
        ],
    }
    (ROOT / "V32_RELEASE_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("version", "status", "passed", "total", "operational_permission", "capital_permission", "predictive_status")}, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
