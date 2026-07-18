"""Databento Live-to-HTTP snapshot bridge for futures/options statistics.

Runs separately from Streamlit. Subscriptions are configured through JSON so the
War Room never silently assumes a dataset, schema, symbol type or entitlement.
Open-interest statistics are observation records; they are not trade direction.
"""
from __future__ import annotations

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse
import dataclasses
import json
import os
import signal
import time

HOST = os.getenv("DATABENTO_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("DATABENTO_BRIDGE_PORT", "8767"))
TOKEN = os.getenv("DATABENTO_STREAM_BRIDGE_TOKEN", "")
MAX_EVENTS = int(os.getenv("DATABENTO_BRIDGE_MAX_EVENTS", "10000"))
EVENTS = deque(maxlen=MAX_EVENTS)
LOCK = Lock()
RUNNING = True
CLIENT = None
LAST_ERROR = None
STARTED_AT = time.time()

DEFAULT_SUBSCRIPTIONS = [
    {"dataset": "GLBX.MDP3", "schema": "statistics", "stype_in": "parent", "symbols": ["ES.FUT", "NQ.FUT", "CL.FUT", "GC.FUT"]},
    {"dataset": "GLBX.MDP3", "schema": "trades", "stype_in": "parent", "symbols": ["ES.FUT", "NQ.FUT", "CL.FUT", "GC.FUT"]},
]


def subscriptions():
    raw = os.getenv("DATABENTO_SUBSCRIPTIONS_JSON", "")
    if not raw:
        return DEFAULT_SUBSCRIPTIONS
    try:
        obj = json.loads(raw)
        if isinstance(obj, list) and obj:
            return [x for x in obj if isinstance(x, dict)]
    except Exception as exc:
        raise SystemExit(f"Invalid DATABENTO_SUBSCRIPTIONS_JSON: {exc}")
    raise SystemExit("DATABENTO_SUBSCRIPTIONS_JSON must be a non-empty JSON list")


def plain_record(record):
    if dataclasses.is_dataclass(record):
        raw = dataclasses.asdict(record)
    elif hasattr(record, "to_dict"):
        try:
            raw = record.to_dict()
        except Exception:
            raw = {}
    elif hasattr(record, "__dict__"):
        raw = {k: v for k, v in vars(record).items() if not k.startswith("_")}
    else:
        raw = {}
    raw = raw if isinstance(raw, dict) else {}
    for key, value in list(raw.items()):
        if isinstance(value, bytes):
            raw[key] = value.decode(errors="replace").rstrip("\x00")
        elif hasattr(value, "isoformat"):
            try: raw[key] = value.isoformat()
            except Exception: raw[key] = str(value)
        elif not isinstance(value, (str, int, float, bool, type(None), list, dict)):
            raw[key] = str(value)
    return raw


def normalize(record):
    raw = plain_record(record)
    cls = type(record).__name__
    stat_type = raw.get("stat_type") or raw.get("stat_type_raw") or raw.get("stat_type_id")
    value = raw.get("quantity")
    if value is None: value = raw.get("price")
    if value is None: value = raw.get("value")
    return {
        "provider": "Databento",
        "record_type": cls,
        "dataset": raw.get("dataset"),
        "instrument_id": raw.get("instrument_id"),
        "publisher_id": raw.get("publisher_id"),
        "symbol": raw.get("symbol") or raw.get("raw_symbol") or raw.get("stype_in_symbol"),
        "stat_type": stat_type,
        "value": value,
        "price": raw.get("price"),
        "quantity": raw.get("quantity"),
        "sequence": raw.get("sequence"),
        "timestamp": raw.get("ts_event") or raw.get("ts_recv") or raw.get("timestamp"),
        "received_at": time.time(),
        "observed": True,
        "semantics": "Statistics records may include open interest or settlement values. They do not identify long versus short initiators.",
        "raw": raw,
    }


def on_record(record):
    global LAST_ERROR
    row = normalize(record)
    if row["record_type"].lower().startswith("err"):
        LAST_ERROR = str(row.get("raw"))[:500]
    with LOCK:
        EVENTS.appendleft(row)


def on_exception(exc):
    global LAST_ERROR
    LAST_ERROR = f"{type(exc).__name__}: {exc}"


def run_client():
    global CLIENT, LAST_ERROR, RUNNING
    try:
        import databento as db
        CLIENT = db.Live(key=os.getenv("DATABENTO_API_KEY") or None)
        specs = subscriptions()
        datasets = {str(x.get("dataset") or "") for x in specs}
        if len(datasets) != 1:
            raise RuntimeError("One Databento live session supports one dataset; run another worker for another dataset.")
        for spec in specs:
            kwargs = {
                "dataset": spec["dataset"],
                "schema": spec["schema"],
                "symbols": spec.get("symbols") or "ALL_SYMBOLS",
            }
            if spec.get("stype_in"): kwargs["stype_in"] = spec["stype_in"]
            if "start" in spec: kwargs["start"] = spec["start"]
            if spec.get("snapshot") is not None: kwargs["snapshot"] = bool(spec["snapshot"])
            CLIENT.subscribe(**kwargs)
        CLIENT.add_callback(on_record, exception_callback=on_exception)
        CLIENT.start()
        CLIENT.block_for_close()
    except Exception as exc:
        LAST_ERROR = f"{type(exc).__name__}: {exc}"
    finally:
        RUNNING = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): return
    def do_GET(self):
        if TOKEN and self.headers.get("Authorization", "") != f"Bearer {TOKEN}":
            self.send_response(401); self.end_headers(); return
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            body = {"state": "LIVE" if RUNNING and LAST_ERROR is None else "DEGRADED" if RUNNING else "STOPPED",
                    "events": len(EVENTS), "last_error": LAST_ERROR, "uptime_seconds": time.time()-STARTED_AT}
        elif parsed.path == "/snapshot":
            q = parse_qs(parsed.query)
            symbols = {x.upper() for x in ",".join(q.get("symbols", [])).split(",") if x}
            record_type = (q.get("record_type") or [""])[0].lower()
            limit = min(5000, max(1, int((q.get("limit") or ["1500"])[0])))
            with LOCK: out = list(EVENTS)
            if symbols:
                out = [x for x in out if str(x.get("symbol") or "").upper() in symbols]
            if record_type:
                out = [x for x in out if record_type in str(x.get("record_type") or "").lower()]
            body = {"state": "LIVE" if RUNNING else "STOPPED", "generated": time.time(), "data": out[:limit],
                    "last_error": LAST_ERROR}
        else:
            self.send_response(404); self.end_headers(); return
        raw = json.dumps(body, default=str, separators=(",", ":")).encode()
        self.send_response(200); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)


def stop(*_):
    global RUNNING
    RUNNING = False
    try:
        if CLIENT is not None: CLIENT.stop()
    except Exception: pass


def main():
    if not os.getenv("DATABENTO_API_KEY", "").strip():
        raise SystemExit("DATABENTO_API_KEY is required")
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)
    Thread(target=run_client, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Databento bridge listening on http://{HOST}:{PORT}/snapshot", flush=True)
    try:
        while RUNNING: server.handle_request()
    finally:
        server.server_close(); stop()


if __name__ == "__main__": main()
