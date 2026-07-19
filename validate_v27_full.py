from __future__ import annotations

import copy
import json
import multiprocessing as mp
import os
import pickle
import re
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RUNTIME = HERE / "runtime"
STATIC = HERE / "static"
CACHE = HERE / ".cache" / "price_cache.pkl"
FRED_CACHE = HERE / ".cache" / "fred_v3"
LIQ_CACHE = HERE / ".cache" / "treasury_liquidity.json"
RESULTS: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    row = {"name": name, "passed": bool(condition), "detail": detail}
    RESULTS.append(row)
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def _read(path: Path) -> bytes | None:
    return path.read_bytes() if path.exists() else None


@contextmanager
def preserve_paths(paths: list[Path]):
    saved = {path: _read(path) for path in paths}
    try:
        yield
    finally:
        for path in paths:
            try:
                path.unlink()
            except OSError:
                pass
        for path, data in saved.items():
            if data is not None:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)


def reset_runtime() -> None:
    for folder in (RUNTIME, STATIC):
        folder.mkdir(parents=True, exist_ok=True)
    for path in list(RUNTIME.glob("*")) + [STATIC / "desk_snapshot.json", STATIC / "worker_status.json"]:
        if path.name == ".gitkeep":
            continue
        try:
            path.unlink()
        except OSError:
            pass
    boot = {
        "meta": {"source": "INITIALIZING", "generated": "—", "note": "v2.7 validation boot"},
        "runtime": {"worker_state": "STARTING", "snapshot_sequence": 1, "content_hash": "boot-v27"},
        "data_health": {"overall": "INITIALIZING", "sources": [], "live_count": 0, "total_count": 0},
        "systemic": {"liquidity": "INITIALIZING", "quad_name": "INITIALIZING"},
        "markets": {}, "alpha": [], "reference": {}, "macro_observations": {},
        "market_breadth": {}, "rotation_snapshot": {},
        "institutional": {"overall_state": "INITIALIZING", "statuses": [], "events": []},
        "live_intelligence": {"overall_state": "INITIALIZING", "statuses": [], "events": [],
                              "crypto_derivatives": [], "crypto_options": [], "us_options": [], "us_squeeze": []},
        "full_live_data": {"overall_state": "INITIALIZING", "statuses": [], "tab_coverage": {}},
    }
    payload = json.dumps(boot, separators=(",", ":")).encode()
    (RUNTIME / "desk_snapshot.json").write_bytes(payload)
    (STATIC / "desk_snapshot.json").write_bytes(payload)


def make_price_fixture() -> None:
    from data.loader import YAHOO_ALIASES

    names = [
        # hosted fast market anchors
        "SPY", "QQQ", "IWM", "NVDA", "AMD", "MSFT", "AAPL", "AMZN", "META", "SMH", "AVGO", "MRVL",
        "^JKSE", "BBCA.JK", "BMRI.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "ANTM.JK", "ADRO.JK",
        "BTC-USD", "ETH-USD", "SOL-USD", "XRP-USD", "BNB-USD", "DOGE-USD", "ADA-USD", "TRX-USD", "AVAX-USD", "LINK-USD",
        "CL=F", "BZ=F", "GC=F", "SI=F", "HG=F", "NG=F",
        "EURUSD=X", "JPY=X", "GBPUSD=X", "AUDUSD=X", "IDR=X", "DX-Y.NYB",
        # fast cross-asset proxies
        "GLD", "TLT", "UUP", "DBC", "USO", "EEM", "EIDO",
    ]
    index = pd.date_range(end=pd.Timestamp.today().normalize(), periods=560, freq="B")
    cache: dict = {}
    for i, name in enumerate(names):
        base = 35.0 + i * 2.5
        change = 0.00016 + np.sin(np.arange(len(index)) / 17.0 + i) * 0.00055
        close = base * np.exp(np.cumsum(change))
        frame = pd.DataFrame({
            "Open": close * 0.997, "High": close * 1.009, "Low": close * 0.991,
            "Close": close, "Volume": 900_000.0 + i * 13_000,
        }, index=index)
        cache[YAHOO_ALIASES.get(name, name)] = (time.time(), frame)
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_bytes(pickle.dumps(cache, protocol=pickle.HIGHEST_PROTOCOL))


def make_context_fixture() -> None:
    FRED_CACHE.mkdir(parents=True, exist_ok=True)
    idx = pd.date_range(end=pd.Timestamp.today().normalize(), periods=180, freq="MS")
    keys = ["INDPRO", "RSAFS", "PAYEMS", "UNRATE", "ICSA", "CPI", "CORECPI", "FEDFUNDS",
            "DGS2", "DGS10", "DFII10", "T10YIE", "HYOAS", "WALCL", "RRPONTSYD", "WTREGEN"]
    for i, key in enumerate(keys):
        values = 80 + i + np.linspace(0, 12, len(idx)) + np.sin(np.arange(len(idx)) / 9.0 + i)
        pd.DataFrame({"value": values}, index=idx).to_pickle(FRED_CACHE / f"{key}.pkl")
    LIQ_CACHE.write_text(json.dumps({
        "ok": True, "state": "LIVE", "coverage": 3, "bias": "IMPROVING",
        "signals": ["fixture"], "generated": "2026-07-20T00:00:00Z",
    }), encoding="utf-8")


def static_checks() -> None:
    app = (HERE / "app.py").read_text(encoding="utf-8")
    worker = (HERE / "warroom_data_worker.py").read_text(encoding="utf-8")
    loader = (HERE / "data" / "loader.py").read_text(encoding="utf-8")
    fred = (HERE / "data" / "fred_loader.py").read_text(encoding="utf-8")
    liq = (HERE / "engines" / "treasury_liquidity.py").read_text(encoding="utf-8")
    runtime = (HERE / "runtime_store.py").read_text(encoding="utf-8")
    html = (HERE / "dashboard.html").read_text(encoding="utf-8")

    check("hosted default is embedded collector", 'WARROOM_WORKER_MODE", "embedded"' in app)
    check("inline bootstrap precedes worker and iframe", app.index("INITIAL_BOOTSTRAP = _ensure_initial_snapshot()") < app.index("SUPERVISOR = _ensure_worker()") < app.index("_render_dashboard()"))
    check("inline bootstrap guarantees terminal R2", "Guarantee R2 before the iframe" in app and "BOOTSTRAP_TIMEOUT" in app)
    check("worker uses staged market bootstrap", "core_bootstrap" in worker and "bootstrap_snapshot_once" in worker)
    check("no fork from executor thread", 'start_method not in {"spawn", "forkserver"}' in worker and 'mp.get_context("fork")' not in worker)
    check("context plane starts independently", '"context": 0.0' in worker and 'schedule("context", "core_context")' in worker)
    check("prior R1/empty snapshot is not valid core", "sum(_market_universe(previous, market)" in worker)
    check("public price fallback is multi-provider", all(token in loader for token in ["query1.finance.yahoo.com", "query2.finance.yahoo.com", "stooq.com", "api.binance.com", "www.okx.com"]))
    check("FX aliases corrected", '"USDJPY=X": "JPY=X"' in loader and '"USDIDR=X": "IDR=X"' in loader)
    check("price cache writes atomically", "os.replace(tmp, _CACHE_PATH)" in loader)
    check("FRED cache has pickle fallback", ".pkl" in fred and "pd.read_pickle" in fred and "os.replace(tmp, fallback)" in fred)
    check("liquidity cache writes unique atomic temp", 'f"{CACHE.name}.{os.getpid()}.tmp"' in liq and "os.replace(tmp, CACHE)" in liq)
    check("worker heartbeat is not PID-only", "max_heartbeat_age" in runtime and "_file_age_seconds" in runtime)
    check("dashboard polls static snapshot without iframe remount", "pollSnapshot" in html and "acceptSnapshot" in html and "setInterval(pollSnapshot" in html)
    check("dashboard version is v2.7", "v2.7 STAGED LIVE" in html)

    # All Python compiles.
    compile_failures = []
    for py in HERE.rglob("*.py"):
        if any(part in {".venv", "venv"} for part in py.parts):
            continue
        try:
            compile(py.read_text(encoding="utf-8"), str(py), "exec")
        except Exception as exc:
            compile_failures.append(f"{py.relative_to(HERE)}: {exc}")
    check("all Python files compile", not compile_failures, "; ".join(compile_failures[:8]))

    scripts = "\n".join(re.findall(r"<script[^>]*>(.*?)</script>", html, re.S))
    with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
        fh.write(scripts)
        js_path = Path(fh.name)
    try:
        proc = subprocess.run(["node", "--check", str(js_path)], capture_output=True, text=True, timeout=30)
        check("dashboard JavaScript parses", proc.returncode == 0, proc.stderr.strip())
    finally:
        js_path.unlink(missing_ok=True)


def fixture_checks() -> None:
    env_before = os.environ.copy()
    try:
        os.environ.update({
            "WARROOM_HOSTED_MODE": "1", "WARROOM_PRICE_BACKEND": "http",
            "WARROOM_ENABLE_YFINANCE_FALLBACK": "0", "WARROOM_PRICE_HTTP_TIMEOUT": "2",
            "WARROOM_FAST_US_NAMES": "12", "WARROOM_FAST_IDX_NAMES": "8",
            "WARROOM_FAST_CRYPTO_NAMES": "10", "WARROOM_INPROCESS_COLLECTORS": "1",
            "WARROOM_NETWORK_MODE": "live", "WARROOM_FAST_CORE_PRICE_FIRST": "1",
        })
        reset_runtime(); make_price_fixture()
        from warroom_data_worker import bootstrap_snapshot_once, build_core
        started = time.monotonic()
        result = bootstrap_snapshot_once(direct=True)
        elapsed = time.monotonic() - started
        snapshot = json.loads((RUNTIME / "desk_snapshot.json").read_text(encoding="utf-8"))
        counts = {m: int((((snapshot.get("markets") or {}).get(m) or {}).get("funnel") or {}).get("universe") or 0)
                  for m in ("us", "idx", "crypto", "commodity", "fx")}
        check("direct hosted bootstrap commits R2", int((snapshot.get("runtime") or {}).get("snapshot_sequence") or 0) >= 2, str(result))
        check("direct hosted bootstrap fills every core market", all(v > 0 for v in counts.values()), json.dumps(counts))
        check("direct hosted bootstrap is bounded", elapsed < 18, f"elapsed={elapsed:.3f}s")

        make_context_fixture()
        os.environ["WARROOM_FAST_CORE_PRICE_FIRST"] = "0"
        started = time.monotonic()
        context = build_core(True, refresh_context=True)
        elapsed = time.monotonic() - started
        check("background context loads macro observations", len(context.get("macro_observations") or {}) >= 10, str(len(context.get("macro_observations") or {})))
        check("background context loads liquidity", str((context.get("systemic") or {}).get("liquidity") or "").upper() not in {"", "NO_DATA", "INITIALIZING", "PENDING"}, str(context.get("systemic")))
        check("background context remains bounded from cache", elapsed < 30, f"elapsed={elapsed:.3f}s")

        reset_runtime()
        os.environ["WARROOM_NETWORK_MODE"] = "offline"
        result = bootstrap_snapshot_once(direct=True)
        snapshot = json.loads((RUNTIME / "desk_snapshot.json").read_text(encoding="utf-8"))
        check("offline bootstrap exits INITIALIZING", str((snapshot.get("data_health") or {}).get("overall")) == "NO_DATA", str(result))
        check("offline bootstrap commits explicit R2", int((snapshot.get("runtime") or {}).get("snapshot_sequence") or 0) >= 2)
    finally:
        os.environ.clear(); os.environ.update(env_before)


def process_checks() -> None:
    env_before = os.environ.copy()
    try:
        os.environ.update({"WARROOM_TEST_MODE": "1", "WARROOM_INPROCESS_COLLECTORS": "0", "WARROOM_MP_START_METHOD": "spawn"})
        import warroom_data_worker as worker
        started = time.monotonic()
        blob = worker.run_bounded("_test_blob", 5_000_000, 15)
        check("spawn transports large plane without queue deadlock", len(blob.get("blob", "")) == 5_000_000, f"elapsed={time.monotonic()-started:.3f}s")
        timed_out = False
        started = time.monotonic()
        try:
            worker.run_bounded("_test_sleep", 10, 2)
        except TimeoutError:
            timed_out = True
        time.sleep(0.2)
        check("hard timeout kills child", timed_out, f"elapsed={time.monotonic()-started:.3f}s")
        check("no orphan collector children", not mp.active_children(), str([(p.pid, p.is_alive()) for p in mp.active_children()]))
    finally:
        os.environ.clear(); os.environ.update(env_before)


def semantic_checks() -> None:
    from runtime_store import content_hash
    base = {"meta": {"source": "LIVE", "generated": "a"}, "runtime": {"worker_state": "A"}, "markets": {"us": {"bias": "NEUTRAL"}}}
    volatile = copy.deepcopy(base)
    volatile["meta"]["generated"] = "b"
    volatile["runtime"] = {"worker_state": "B", "snapshot_sequence": 99}
    check("heartbeat/timestamps do not trigger redraw", content_hash(base) == content_hash(volatile))
    meaningful = copy.deepcopy(base); meaningful["markets"]["us"]["bias"] = "LEAN_SHORT"
    check("meaningful state changes revision hash", content_hash(base) != content_hash(meaningful))

    proc = subprocess.run([sys.executable, str(HERE / "validate_arrow_lineage.py")], cwd=HERE, capture_output=True, text=True, timeout=60)
    check("arrow lineage audit passes", proc.returncode == 0, (proc.stdout + proc.stderr)[-1200:])
    proc = subprocess.run([sys.executable, str(HERE / "validate_live_stack.py")], cwd=HERE, capture_output=True, text=True, timeout=120)
    check("live stack fixture audit passes", proc.returncode == 0, (proc.stdout + proc.stderr)[-1200:])


def app_shell_check() -> None:
    """Import app.py with a tiny Streamlit stub and a ready R2 snapshot."""
    script = r'''
import json, os, sys, types
from pathlib import Path
root=Path(sys.argv[1]); os.chdir(root); sys.path.insert(0,str(root))
os.environ['WARROOM_DISABLE_AUTOSTART']='1'
ready={"meta":{"source":"NO_DATA"},"runtime":{"snapshot_sequence":2,"content_hash":"ready"},"data_health":{"overall":"NO_DATA"},"systemic":{"liquidity":"NO_DATA","quad_name":"NO_DATA"},"markets":{}}
(root/'runtime').mkdir(exist_ok=True);(root/'static').mkdir(exist_ok=True)
(root/'runtime/desk_snapshot.json').write_text(json.dumps(ready));(root/'static/desk_snapshot.json').write_text(json.dumps(ready))
calls=[]
mod=types.ModuleType('streamlit')
mod.set_page_config=lambda **k: None
mod.markdown=lambda *a,**k: None
mod.error=lambda *a,**k: calls.append(('error',a))
mod.code=lambda *a,**k: None
mod.iframe=lambda *a,**k: calls.append(('iframe',a,k))
def cache_resource(*a,**k):
 def deco(fn):
  cache={}
  def wrapped(*args,**kwargs):
   if 'v' not in cache: cache['v']=fn(*args,**kwargs)
   return cache['v']
  return wrapped
 return deco
mod.cache_resource=cache_resource
sys.modules['streamlit']=mod
import app
print(json.dumps({"iframes":sum(1 for c in calls if c[0]=='iframe'),"errors":sum(1 for c in calls if c[0]=='error')}))
'''
    proc = subprocess.run([sys.executable, "-c", script, str(HERE)], cwd=HERE, capture_output=True, text=True, timeout=40)
    detail = (proc.stdout + proc.stderr).strip()
    ok = False
    if proc.returncode == 0:
        try:
            obj = json.loads(proc.stdout.strip().splitlines()[-1])
            ok = obj.get("iframes") == 1 and obj.get("errors") == 0
        except Exception:
            pass
    check("Streamlit shell mounts one dashboard", ok, detail[-1500:])



def app_fresh_boot_check() -> None:
    """Exercise the exact app startup order from R1 using cached real-shaped market fixtures."""
    script = r'''
import json, os, sys, types
from pathlib import Path
root=Path(sys.argv[1]); os.chdir(root); sys.path.insert(0,str(root))
os.environ.update({'WARROOM_DISABLE_AUTOSTART':'1','WARROOM_HOSTED_MODE':'1','WARROOM_PRICE_BACKEND':'http','WARROOM_ENABLE_YFINANCE_FALLBACK':'0','WARROOM_INLINE_BOOTSTRAP_SECONDS':'12'})
from validate_v27_full import reset_runtime, make_price_fixture
reset_runtime(); make_price_fixture()
calls=[]
mod=types.ModuleType('streamlit')
mod.set_page_config=lambda **k: None
mod.markdown=lambda *a,**k: None
mod.error=lambda *a,**k: calls.append(('error',a))
mod.code=lambda *a,**k: None
mod.iframe=lambda *a,**k: calls.append(('iframe',a,k))
def cache_resource(*a,**k):
 def deco(fn):
  cache={}
  def wrapped(*args,**kwargs):
   if 'v' not in cache: cache['v']=fn(*args,**kwargs)
   return cache['v']
  return wrapped
 return deco
mod.cache_resource=cache_resource
sys.modules['streamlit']=mod
import app
snap=json.loads((root/'runtime/desk_snapshot.json').read_text())
counts={m:int((((snap.get('markets') or {}).get(m) or {}).get('funnel') or {}).get('universe') or 0) for m in ('us','idx','crypto','commodity','fx')}
iframe=[c for c in calls if c[0]=='iframe']
iframe_path=str(iframe[0][1][0]) if iframe else ''
seeded=Path(iframe_path).exists() and 'window.DASHBOARD_DATA=' in Path(iframe_path).read_text(encoding='utf-8')
print(json.dumps({'iframes':len(iframe),'errors':sum(1 for c in calls if c[0]=='error'),'revision':(snap.get('runtime') or {}).get('snapshot_sequence'),'health':(snap.get('data_health') or {}).get('overall'),'counts':counts,'seeded_first_paint':seeded}))
'''
    proc = subprocess.run([sys.executable, "-c", script, str(HERE)], cwd=HERE, capture_output=True, text=True, timeout=45)
    detail = (proc.stdout + proc.stderr).strip()
    ok = False
    if proc.returncode == 0:
        try:
            obj = json.loads(proc.stdout.strip().splitlines()[-1])
            ok = obj.get("iframes") == 1 and obj.get("errors") == 0 and int(obj.get("revision") or 0) >= 2 and bool(obj.get("seeded_first_paint")) and all(int(v)>0 for v in (obj.get("counts") or {}).values())
        except Exception:
            pass
    check("fresh app startup commits market R2 before iframe", ok, detail[-1800:])

def main() -> int:
    paths = [
        RUNTIME / "desk_snapshot.json", RUNTIME / "worker_status.json", RUNTIME / "worker.pid",
        RUNTIME / "worker.instance.lock", RUNTIME / "worker_start.lock", RUNTIME / "force_refresh.flag",
        STATIC / "desk_snapshot.json", STATIC / "worker_status.json", CACHE, LIQ_CACHE,
    ] + list(FRED_CACHE.glob("*"))
    started = time.monotonic()
    status = "PASS"
    error = None
    with preserve_paths(paths):
        try:
            for label, fn in [
                ("static", static_checks), ("fixture", fixture_checks), ("app_shell", app_shell_check),
                ("process", process_checks), ("semantic", semantic_checks),
            ]:
                print(f"[v2.7 validation] {label}...", flush=True)
                fn()
        except Exception as exc:
            status = "FAIL"
            error = f"{type(exc).__name__}: {exc}"
    report = {
        "version": "2.7",
        "status": status,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "passed": sum(1 for row in RESULTS if row["passed"]),
        "total": len(RESULTS),
        "checks": RESULTS,
        "error": error,
        "not_verified_here": [
            "authenticated paid-provider responses without the user's API keys and entitlements",
            "public internet reachability from the user's Streamlit hosting account",
            "exchange/provider schema changes after packaging",
        ],
    }
    (HERE / "V27_FULL_VALIDATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
